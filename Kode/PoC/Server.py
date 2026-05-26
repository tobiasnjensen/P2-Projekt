"""
@Author: Tobias Jensen
@Date: 12/5/2026.
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
from identify import update_history, is_drone, _first_seen
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
    "anchor_1": (19.5, 8, 2),
    "anchor_2": (30, 1, 0),  
    "anchor_3": (7.5, 12.2, 1.3),
    "anchor_4": (1, 1, 0.6),
}

#--------Database Konfiguration--------#
DB_CONFIG = {
    "host": "localhost",         #Skift til ip-adressen på PostgreSQL eller localhost hvis det er på samme maskine
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
alarmed_bssids    = set()

#-----------------------------------------#
#               Funktioner                #
#-----------------------------------------#

#--------Terminal UI funktioner--------#
def build_table() -> Table:
    """
    Bygger en rich-tabel med de seneste positioner for alle kendte BSSID'er.
    Kaldes hver gang UI-tråden opdaterer visningen.
    """
    table = Table(title="Trilateration — live'ish positioner", border_style="grey50")   #Opretter en rich Table med en titel og grå kant
    table.add_column("BSSID",     style="cyan", no_wrap=True) #kolonne for BSSID, i cyan
    table.add_column("x (m)",     justify="right")
    table.add_column("y (m)",     justify="right")
    table.add_column("z (m)",     justify="right")
    table.add_column("Anchors",   justify="center")
    table.add_column("Timestamp", style="grey50")

    with positions_lock: #Låser positions_lock for at sikre trådsikker adgang til positions-dictionaryen
        if not positions:
            table.add_row("—", "—", "—", "—", "—", "—") #Hvis positions er tom tilføjes der blot en række streger
        for bssid, info in positions.items(): #Itererer gennem alle kendte BSSID'er og deres tilhørende information i positions-dict
            pos = info["position"] #Henter positionen (x, y, z) for denne BSSID
            with measurements_lock: #låser measurement ligesom positions
                n_anchors = len(measurements.get(bssid, {})) #Tjekker hvor mange anchors der har målinger for denne BSSID
                #Hvis der er mindre end 4 anchors, kan trilateration ikke udføres, og tabellen opdateres ikke
            table.add_row( #
                bssid,
                f"{pos[0]:.2f}",
                f"{pos[1]:.2f}",
                f"{pos[2]:.2f}",
                f"{n_anchors}/4",
                info["timestamp"],
            )
    return table

def ui_thread()-> None: 
    """
    Kører Live-tabellen i sin egen tråd.
    Hvis UI'en crasher fortsætter receiver og worker upåvirket, samt databaseoperationer og derved også det reelle web-UI.
    """
    with Live(build_table(), refresh_per_second=1, console=console) as live: #Opdaterer hver 1s selv om krav spec siger 150ms. Den rigtige UI er sat til 150ms
        while True:
            time.sleep(1)
            live.update(build_table()) #Opdaterer tabellen ved at kalde build_table() igen, hvilket henter de seneste positioner og målinger

#--------Database funktioner--------#
def test_forbindelse():
    """
    Test at vi kan oprette forbindelse til databasen.
    Returnerer conn
    """
    print(colored("Tester forbindelse...", "yellow"))
    conn = psycopg2.connect(**DB_CONFIG) #Forsøger at oprette forbindelse til PostgreSQL-databasen 
    print(colored("Forbindelse oprettet!", "green"))
    return conn

def gem_position(conn, bssid, x, y, z)-> None: 
    """
    Gemmer eller opdaterer device og indsætter en ny position i databasen.
    args:
        conn: Databaseforbindelse
        bssid: MAC-adressen på den detekterede enhed
        x, y, z: De estimerede koordinater for enheden
    returns:
        None
    """
    now = datetime.now() #Henter det aktuelle tidspunkt for at kunne gemme det i databasen og vise det i UI'en
    if conn is None:
        print(colored("Ingen databaseforbindelse!", "red"))
        return
    with conn.cursor() as cur: #Opretter en cursor for at kunne udføre SQL-kommandoer
        #Indsæt device
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

        #Indsæt position
        cur.execute(
            """
            INSERT INTO positions (device_id, x, y, z, timestamp)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (device_id, x, y, z, now)
        )
    conn.commit()

#--------Databehandlingsfunktioner--------#
def try_trilaterate(bssid)-> None:
    """
    Forsøger at udføre trilateration for en given BSSID, hvis der er målinger fra alle 4 anchors.
    """
    timestamp = time.strftime("%H:%M:%S") #Henter det aktuelle tidspunkt i formatet "HH:MM:SS" for at kunne vise det i UI'en
    with measurements_lock: #Låser measurements_lock 
        data = measurements.get(bssid, {}) #
        if not all(a in data for a in ANCHORS): #Tjekker om der er målinger for alle 4 anchors for denne BSSID. Hvis ikke, returneres None og trilateration udføres ikke
            return
        distances = {a: data[a] for a in ANCHORS} #Hvis der er målinger for alle anchors, oprettes en dictionary med afstandene for hver anchor
        #Ligner noget alla det her: distances = {
        #    "anchor_1": 3.16,
        #    "anchor_2": 4,
        #    "anchor_3": 5,
        #    "anchor_4": 4.24,
        #}

    x_hat, converged = tri_lat_irls( #Kalder irls 
        ANCHORS["anchor_1"], distances["anchor_1"],
        ANCHORS["anchor_2"], distances["anchor_2"],
        ANCHORS["anchor_3"], distances["anchor_3"],
        ANCHORS["anchor_4"], distances["anchor_4"],
    )

    if converged == True: #Tjekker om IRLS konvergerede
        with positions_lock: #Låser positions_lock
            positions[bssid] = {"position": x_hat, "timestamp": timestamp}
        gem_position(db_conn, bssid, float(x_hat[0]), float(x_hat[1]), float(x_hat[2])) #Gemmer den estimerede position i databasen
        update_history(bssid, float(x_hat[0]), float(x_hat[1]), float(x_hat[2]), time.time()) #Opdaterer historikken for denne BSSID i identik.py
        if is_drone(bssid) and bssid not in alarmed_bssids: #Tjekker om enheden opfører sig som en drone og om der ikke allerede er sendt en alarm for denne BSSID
            alarmed_bssids.add(bssid) 
            elapsed = time.time() - _first_seen[bssid]
            send_discord_alarm(bssid, x_hat) #Sender en alarm til Discord med BSSID og position #NOTE Husk at tilføje webhook
            console.print(f"[bold red]DRONE DETEKTERET: {bssid}[/bold red]")
            print(f"Tid fra første måling til klassificering: {elapsed:.2f} sekunder")

        with measurements_lock:
            measurements[bssid] = {}  # Ryd op i målinger for denne BSSID efter trilateration

def receiver_thread()-> None:
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


def worker_thread()-> None:
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