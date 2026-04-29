"""
@Author: Tobias Jensen
@Date: 29/4/2026
Beregningsserver der modtager afstandsmålinger fra Raspberry Pi'erne og estimerer positionen af den detekterede enhed ved hjælp af trilateration.
Serveren lytter på en UDP-port for indkommende data, som forventes at være i JSON-format med følgende struktur:
{
    "bssid": "string",
    "anchor_id": "string",
    "distance": float,
    "timestamp": "string"
}
Når serveren modtager data, gemmer den afstandsmålingerne for hver BSSID og forsøger at udføre trilateration, hvis der er nok data til rådighed (mindst 4 målinger fra forskellige anchors).
Serveren bruger en ikke-lineær mindste kvadraters metode (scipy's least_squares) til at estimere positionen baseret på de modtagne afstande og de kendte koordinater for anchors, da systemet ikke er overbestemt.
"""

#NOTE: THREADING MANGLER :(

#--------Imports--------#
import json
from socket import *
from Non_linear_LSQ import tri_lat

#-----------------------------------------#
#              Configuration              #
#-----------------------------------------#

#--------Server Configuration--------#
HOST = "0.0.0.0"
UDP_PORT = 6769
BUFFER_SIZE = 1024

#--------General Configuration--------#
ANCHORS = { #Koordinater i grupperum Ca.
    "anchor_1": (0.5, 2, 1), 
    "anchor_2": (1, 1, 0),
    "anchor_3": (3, 1, 0),
    "anchor_4": (3, 3, 0),
}
# { bssid: { anchor_id: distance } }
measurements = {}

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
        1. Tjekker om der er målinger fra alle 4 anchors for den givne BSSID.
        2. Hvis der mangler målinger, udskriver den hvilke anchors der mangler
        3. Hvis alle målinger er tilgængelige, kalder den tri_lat funktionen for at estimere positionen.
        4. Udskriver den estimerede position eller en fejlmeddelelse,
    """
    data = measurements[bssid] #

    if not all(a in data for a in ANCHORS):
        missing = [a for a in ANCHORS if a not in data]
        print(f"[{bssid}] Venter på: {missing}")
        return

    result = tri_lat( 
        ANCHORS["anchor_1"], data["anchor_1"],
        ANCHORS["anchor_2"], data["anchor_2"],
        ANCHORS["anchor_3"], data["anchor_3"],
        ANCHORS["anchor_4"], data["anchor_4"],
    )

    if result is None: #BURDE ALDRIG SKE, DA TRILAT BRUGET NLLS.
        print(f"[{bssid}] Ingen entydig løsning")
    else:
        print(f"[{bssid}] Position: x={result[0]:.2f}, y={result[1]:.2f}, z={result[2]:.2f}")

#--------Server kommunikation--------#
def receiver_thread():
    """
    Funktion der stater en UDP-server, som lytter på indkommende data fra måleenhederne
    Når data modtages, parses det og gemmes i measurements dict'en. Derefter forsøger den at udføre trilateration for den givne BSSID.
    Process:
        1. Opretter en UDP socket og binder den til den specificerede host og port.
        2. Starter en uendelig løkke, hvor den venter på indkommende data
    """
    sock = socket(AF_INET, SOCK_DGRAM) #Opretter en UDP socket
    sock.bind((HOST, UDP_PORT)) #Binder socketen til den specificerede host og port
    print("Server is listening...") #Udskriver at serveren er klar til at modtage data

    while True: #Starter en uendelig løkke for at modtage data
        data, addr = sock.recvfrom(BUFFER_SIZE)
        parsed = json.loads(data.decode()) #Parser den modtagne data fra JSON format

        bssid     = parsed["bssid"]        #Udtrækker BSSID fra den parsed data   
        anchor_id = parsed["anchor_id"]    #Udtrækker anchor_id fra den parsed data
        distance  = parsed["distance"]     #Udtrækker distance fra den parsed data

        if bssid not in measurements: #Hvis BSSID'en ikke allerede findes i measurements dict'en, oprettes en ny entry for den
            measurements[bssid] = {}
        measurements[bssid][anchor_id] = distance

        print(f"[{parsed['timestamp']}] {bssid} fra {anchor_id} → Afstand: {distance:.2f}m") #Printer timestamp, BSSID, anchor_id og dens afstand til objektet
        try_trilaterate(bssid)

if __name__ == "__main__":
    receiver_thread()