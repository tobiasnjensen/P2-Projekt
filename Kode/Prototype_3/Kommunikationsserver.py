"""
@Author: Tobias Jensen
@Date: 29/4/2026
Beregningsserver der modtager afstandsmålinger fra Raspberry Pi'erne og estimerer positionen af den detekterede enhed ved hjælp af trilateration.
Serveren lytter på en UDP-port for indkommende data, som forventes at være i JSON-format med følgende struktur:
{
    "bssid": "string",
    "anchor_id": "string",
    "distance": float,
}
Når serveren modtager data, gemmer den afstandsmålingerne for hver BSSID og forsøger at udføre trilateration, hvis der er nok data til rådighed (mindst 4 målinger fra forskellige anchors).
Serveren bruger en ikke-lineær mindste kvadraters metode (scipy's least_squares) til at estimere positionen baseret på de modtagne afstande og de kendte koordinater for anchors, da systemet ikke er overbestemt.
Serveren anvender threading til at adskille modtagelse og behandling af pakker, så ingen pakker går tabt under tung belastning.
"""

#--------Imports--------#
import json, time, threading, queue
from socket import *
from IRLS import tri_lat_irls

#-----------------------------------------#
#              Konfiguration              #
#-----------------------------------------#

#--------Server Konfiguration--------#
HOST = "0.0.0.0"
UDP_PORT = 6769
BUFFER_SIZE = 1024

#--------General Konfiguration--------#
ANCHORS = { #Koordinater i grupperum (øjemål)
    "anchor_1": (0.5, 2, 1),
    "anchor_2": (1, 1, 0),
    "anchor_3": (3, 1, 0),
    "anchor_4": (3, 3, 0),
}

measurements = {} # { bssid: { anchor_id: distance } }
measurements_lock = threading.Lock() #Lock til at beskytte measurements dict'en mod race conditions ved samtidig adgang fra flere tråde

positions = {} # { bssid: {"position": (x, y, z), "timestamp": "..."} }
positions_lock = threading.Lock() #Lock til at beskytte positions dict'en

packet_queue = queue.Queue() #Kø til at buffere indkommende pakker mellem receiver- og worker-tråden

#-----------------------------------------#
#                Functions                #
#-----------------------------------------#

#--------Trilateration--------#
def try_trilaterate(bssid):
    """
    Funktion der forsøger at udføre trilateration for en given BSSID, hvis der er nok data til rådighed.
    args:
        bssid (str): BSSID'en for den enhed, hvis position skal beregnes.
        Process:
        1. Låser measurements dict'en og tjekker om der er målinger fra alle 4 anchors for den givne BSSID.
        2. Hvis der mangler målinger, udskriver den hvilke anchors der mangler og returnerer.
        3. Kopierer de relevante afstande og frigiver låsen, inden trilateration kaldes.
        4. Kalder tri_lat_irls funktionen for at estimere positionen.
        5. Gemmer positionen med timestamp og øger tæller.
        6. Udskriver den estimerede position eller en fejlmeddelelse.
    """
    timestamp = time.strftime("%H:%M:%S") #Opretter et tidsstempel for den aktuelle position
    with measurements_lock: #Låser measurements dict'en for sikker læsning
        data = measurements.get(bssid, {}) #Henter målinger for den givne BSSID, eller en tom dict hvis den ikke findes
        if not all(a in data for a in ANCHORS): #Tjekker om der er målinger fra alle 4 anchors
            missing = [a for a in ANCHORS if a not in data]
            print(f"[{bssid}] Venter på: {missing}") #Printer hivilke anchors der mangler målinger. De har en hardcoded værdi
            return
        distances = {a: data[a] for a in ANCHORS} #Kopierer afstandene mens låsen holdes
#Unlocker låsen så trilateration kan læse measurements uden at blokere receiver-tråden
    result = tri_lat_irls( #Kalder trilateration funktionen med de kendte anchor-koordinater og de målte afstande
        ANCHORS["anchor_1"], distances["anchor_1"],
        ANCHORS["anchor_2"], distances["anchor_2"],
        ANCHORS["anchor_3"], distances["anchor_3"],
        ANCHORS["anchor_4"], distances["anchor_4"],
    )

    if result is None: #BURDE ALDRIG SKE, DA TRILAT BRUGER NLLS. Det er skrevet før NLLS blev implementeret
        print(f"[{bssid}] Ingen entydig løsning")
    else:
        with positions_lock: #Låser positions dict'en for skrivning
            if bssid not in positions:
                positions[bssid] = {"position": result, "timestamp": timestamp}
            else:
                positions[bssid]["position"] = result #Opdaterer position
                positions[bssid]["timestamp"] = timestamp #Opdaterer timestamp
        print(f"[{bssid}] Position: x={result[0]:.2f}, y={result[1]:.2f}, z={result[2]:.2f}")

#--------Server kommunikation--------#
def receiver_thread():
    """
    Funktion der starter en UDP-server, som lytter på indkommende data fra måleenhederne.
    Modtagne pakker lægges i packet_queue og overlades til worker-tråden for behandling,
    så receiver-tråden aldrig blokeres af databehandling.
    Process:
        1. Opretter en UDP socket og binder den til den specificerede host og port.
        2. Starter en uendelig løkke, hvor den venter på indkommende data.
        3. Lægger den modtagne pakke i køen og vender straks tilbage for at modtage næste pakke.
    """
    sock = socket(AF_INET, SOCK_DGRAM) #Opretter en UDP socket
    sock.bind((HOST, UDP_PORT)) #Binder socketen til den specificerede host og port
    print("Server is listening...") #Udskriver at serveren er klar til at modtage data

    while True: #Starter en uendelig løkke for at modtage data
        data, _ = sock.recvfrom(BUFFER_SIZE)
        try:   
            parsed = json.loads(data.decode()) #Parser den modtagne data fra JSON format
            packet_queue.put(parsed) #Læg pakken i køen og returner straks, så ingen pakker går tabt
        except json.JSONDecodeError:
            print(f"[!] Malformet pakke ignoreret")

#--------Worker--------#
def worker_thread():
    """
    Funktion der behandler pakker fra packet_queue i en separat tråd.
    Adskillelsen fra receiver_thread sikrer, at tung databehandling ikke forsinker modtagelsen af nye pakker.
    Process:
        1. Starter en uendelig løkke, der blokerer indtil der er en pakke i køen.
        2. Udtrækker BSSID, anchor_id og distance fra pakken.
        3. Opdaterer measurements dict'en trådsikkert via measurements_lock.
        4. Printer modtagelsesinfo og forsøger trilateration for den givne BSSID.
        5. Markerer opgaven som færdig i køen.
    """
    while True:
        parsed = packet_queue.get() #Blokerer indtil der er data i køen

        bssid     = parsed["bssid"]        #Udtrækker BSSID fra den parsed data
        anchor_id = parsed["anchor_id"]    #Udtrækker anchor_id fra den parsed data
        distance  = parsed["distance"]     #Udtrækker distance fra den parsed data

        with measurements_lock: #Låser measurements dict'en for skrivning
            if bssid not in measurements: #Hvis BSSID'en ikke allerede findes i measurements dict'en, oprettes en ny entry for den
                measurements[bssid] = {} #Opretter en ny dict for den BSSID, hvis den ikke allerede findes
            measurements[bssid][anchor_id] = distance #Opdaterer målingen for den givne anchor_id under den givne BSSID

        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {bssid} fra {anchor_id} → {distance:.2f}m") #Printer timestamp, BSSID, anchor_id og dens afstand til objektet
        try_trilaterate(bssid) #Forsøger at udføre trilateration for den givne BSSID, hvis der ikke er nok måleenheder endnu, vil den blot udskrive hvilke der mangler
        packet_queue.task_done() #Markerer pakken som behandlet i køen

if __name__ == "__main__":
    t_recv = threading.Thread(target=receiver_thread, daemon=True) #Opretter receiver-tråden som daemon, så den afsluttes automatisk når main-tråden stopper
    t_work = threading.Thread(target=worker_thread, daemon=True)   #Opretter worker-tråden som daemon, så den afsluttes automatisk når main-tråden stopper

    t_recv.start() #Starter receiver-tråden
    t_work.start() #Starter worker-tråden

    t_recv.join()  #Blokerer main-tråden indtil receiver stopper (De er begge deamon, så stopper først hvis main stopper) 