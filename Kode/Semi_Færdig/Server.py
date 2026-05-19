"""
@Author: Tobias Jensen
@Date: 12/5/2026
Beregningsserver der modtager afstandsmålinger fra Raspberry Pi'erne og estimerer positionen af den detekterede enhed ved hjælp af trilateration.
Serveren lytter på en UDP-port for indkommende data, som forventes at være i JSON-format med følgende struktur:
{
    "bssid": "string",
    "anchor_id": "string",
    "distance": float,
}
Når serveren modtager data, gemmer den afstandsmålingerne for hver BSSID og forsøger at udføre trilateration, hvis der er nok data til rådighed (mindst 4 målinger fra forskellige anchors).
"""

#--------Imports--------#
import json, time, threading, queue, psycopg2
from datetime import datetime
from socket import *
from rich.console import Console
from rich.table import Table
from rich.live import Live
from IRLS import tri_lat_irls
from termcolor import colored
from identify import update_history, is_drone    
from discord_alarm import send_discord_alarm

#-----------------------------------------#
#              Konfiguration              #
#-----------------------------------------#

#--------Server Konfiguration--------#
HOST        = "0.0.0.0"
UDP_PORT    = 6769
BUFFER_SIZE = 1024

#--------Anchor Konfiguration--------#
ANCHORS = {
    "anchor_1": (0.5, 2, 1),
    "anchor_2": (1, 1, 0),  
    "anchor_3": (3, 1, 0),
    "anchor_4": (3, 3, 0),
}

#--------Database Konfiguration--------#
DB_CONFIG = {
    "host": "192.168.0.102",     #Skift til ip-adressen på din PostgreSQL server, eller localhost hvis det er på samme maskine
    "port": 5432,                
    "database": "DroneDatabase", 
    "user": "tobi",              #Tobias username = tobi
    "password": "6769"           #Tobias password = 6769
}
db_conn = None  # Initialiseres ved opstart

#--------Diverse variabler--------#
measurements      = {}
measurements_lock = threading.Lock()
positions         = {}
positions_lock    = threading.Lock()
packet_queue      = queue.Queue()
console           = Console()


#-----------------------------------------#
#                Functions                #
#-----------------------------------------#

#--------Terminal UI funktioner--------#
def build_table() -> Table:
    """
    Bygger en rich-tabel med de seneste positioner for alle kendte BSSID'er.
    Kaldes hver gang UI-tråden opdaterer visningen.
    """
    table = Table(title="Trilateration — live'ish positioner", border_style="grey50")
    table.add_column("BSSID",     style="cyan", no_wrap=True)
    table.add_column("x (m)",     justify="right")
    table.add_column("y (m)",     justify="right")
    table.add_column("z (m)",     justify="right")
    table.add_column("Anchors",   justify="center")
    table.add_column("Timestamp", style="grey50")

    with positions_lock:
        if not positions:
            table.add_row("—", "—", "—", "—", "—", "—")
        for bssid, info in positions.items():
            pos = info["position"]
            with measurements_lock:
                n_anchors = len(measurements.get(bssid, {}))
            table.add_row(
                bssid,
                f"{pos[0]:.2f}",
                f"{pos[1]:.2f}",
                f"{pos[2]:.2f}",
                f"{n_anchors}/4",
                info["timestamp"],
            )
    return table

def ui_thread():
    """
    Kører Live-tabellen i sin egen tråd, adskilt fra server-logikken.
    Hvis UI'en crasher fortsætter receiver og worker upåvirket.
    """
    with Live(build_table(), refresh_per_second=1, console=console) as live:
        while True:
            time.sleep(1)
            live.update(build_table())

#--------Database funktioner--------#
def test_forbindelse():
    """Test at vi kan oprette forbindelse til databasen."""
    print(colored("Tester forbindelse...", "yellow"))
    conn = psycopg2.connect(**DB_CONFIG)
    print(colored("Forbindelse oprettet!", "green"))
    return conn

def gem_position(conn, bssid, x, y, z):
    """Gemmer eller opdaterer device og indsætter en ny position i databasen."""
    now = datetime.now()
    if conn is None:
        print(colored("Ingen databaseforbindelse!", "red"))
        return
    with conn.cursor() as cur:
        # Indsæt device hvis det ikke findes, opdater last_seen hvis det gør
        cur.execute(
            """
            INSERT INTO device (mac_adresse, last_seen)
            VALUES (%s, %s)
            ON CONFLICT (mac_adresse) DO UPDATE SET last_seen = EXCLUDED.last_seen
            RETURNING id
            """,
            (bssid, now)
        )
        device_id = cur.fetchone()[0]   

        # Indsæt position
        cur.execute(
            """
            INSERT INTO positions (device_id, x, y, z, timestamp)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (device_id, x, y, z, now)
        )
    conn.commit()

#--------Databehandlingsfunktioner--------#
def try_trilaterate(bssid):
    """
    Forsøger at udføre trilateration for en given BSSID, hvis der er målinger fra alle 4 anchors.
    """
    timestamp = time.strftime("%H:%M:%S")
    with measurements_lock:
        data = measurements.get(bssid, {})
        if not all(a in data for a in ANCHORS):
            return
        distances = {a: data[a] for a in ANCHORS}

    x_hat, converged = tri_lat_irls(
        ANCHORS["anchor_1"], distances["anchor_1"],
        ANCHORS["anchor_2"], distances["anchor_2"],
        ANCHORS["anchor_3"], distances["anchor_3"],
        ANCHORS["anchor_4"], distances["anchor_4"],
    )

    if converged == True:
        with positions_lock:
            positions[bssid] = {"position": x_hat, "timestamp": timestamp}
        gem_position(db_conn, bssid, float(x_hat[0]), float(x_hat[1]), float(x_hat[2]))
        update_history(bssid, float(x_hat[0]), float(x_hat[1]), float(x_hat[2]), time.time()) #Opdaterer historikken for denne BSSID i identik.py
        if is_drone(bssid): #Tjekker om denne BSSID opfører sig som en drone baseret på historikken i identik.py
            console.print(f"[bold red]DRONE DETEKTERET: {bssid}[/bold red]")
            send_discord_alarm(f"@Drone detekteret: {bssid} ved position ({x_hat[0]:.2f}, {x_hat[1]:.2f}, {x_hat[2]:.2f})")

        with measurements_lock:
            measurements[bssid] = {}  # Ryd op i målinger for denne BSSID efter trilateration

def receiver_thread():
    """
    Lytter på UDP-porten og lægger indkommende pakker i packet_queue.
    """
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind((HOST, UDP_PORT))

    while True:
        data, _ = sock.recvfrom(BUFFER_SIZE)
        try:
            parsed = json.loads(data.decode())
            packet_queue.put(parsed)
        except json.JSONDecodeError:
            pass


def worker_thread():
    """
    Behandler pakker fra packet_queue og opdaterer measurements og positions.
    """
    while True:
        parsed    = packet_queue.get()
        bssid     = parsed["bssid"]
        anchor_id = parsed["anchor_id"]
        distance  = parsed["distance"]

        with measurements_lock:
            if bssid not in measurements:
                measurements[bssid] = {}
            measurements[bssid][anchor_id] = distance

        try_trilaterate(bssid)
        packet_queue.task_done()

if __name__ == "__main__":
    db_conn = test_forbindelse()

    threads = [
        threading.Thread(target=receiver_thread, daemon=True),
        threading.Thread(target=worker_thread,   daemon=True),
        threading.Thread(target=ui_thread,        daemon=True),
    ]
    for t in threads:
        t.start()

    # Main-tråden holder programmet kørende og venter på Ctrl+C
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\n[*] Afslutter...")
        db_conn.close()