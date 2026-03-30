"""
@author: Tobias Jensen
@date: 13/2/2026
This file contains a prototype for a RSSI converter
"""

#--------Imports--------#
from socket import *
import threading, time
from Trilateration import tri_lat

HOST = '0.0.0.0' #Lytter til alle interfaces. Kan ændres til specifik IP (UDP)
UDP_PORT = 8787
BUFFER_SIZE = 1024
"""TCP_HOST = '0.0.0.0' #Lytter til alle interfaces. Kan ændres til specifik IP (TCP)
TCP_PORT = 6767"""

#--------Global variables--------#
pos_dict = {"p1": (0,3,0), "p2": (-3,0,0), "p3": (0,6,0), "p4": (0,3,2)} #Dict til at gemme de kendte punkters positioner
distances = {"d1": None, "d2": None, "d3": None, "d4": None} #Dict til at gemme de 4 afstande i
client_slots = {}

#--------Functions--------#
def rssi_to_distance(rssi, A, n):
    """
    Estimerer afstanden baseret på RSSI-værdien
    
    Parameters:
    rssi (float): The received signal strength indicator (in dBm).
    A (float): The RSSI value at a reference distance (usually 1 meter).
    n (float): The path loss exponent, which varies based on the environment. #For free space, n is typically 2.
    
    Returns:
    float: The estimated distance in meters.
    """
    distance = 10 ** ((A - rssi) / (10 * n))
    return distance

def receiver_thread():
    """
    Modtager RSSI-værdier fra klienterne via UDP, konverterer dem til afstande og opdaterer den delte distances dict.
    Hver klient tildeles en "slot" (d1, d2, d3, d4) baseret på rækkefølgen af tilslutning. Hvis der er mere end 4 klienter, vil yderligere klienter blive ignoreret.
    """
    global distances, client_slots
    s = socket(AF_INET, SOCK_DGRAM)
    s.bind((HOST, UDP_PORT)) 
    print("Server listening...")

    while True:
        r, addr = s.recvfrom(BUFFER_SIZE)

        #----Slot management----#
        if addr not in client_slots and len(client_slots) < 4: #Tjekker om klienten allerede har en slot, og om der er ledige slots
            client_slots[addr] = len(client_slots) + 1 #Tildeler klienten en slot baseret på hvor mange klienter der allerede er tilsluttet
            print(f"New client → slot {client_slots[addr]}")

        slot = client_slots.get(addr)
        if not slot: 
            continue

        #----RSSI processing----#
        rssi_value = float(r.decode()) #Dekoder den modtagne RSSI-værdi fra bytes til float
        distance = round(rssi_to_distance(rssi_value, -40, 2), 2) #Konverterer RSSI-værdi til afstand og afrunder til 2 decimaler

        #--------Update distances dict--------#
        distances[f"d{slot}"] = distance #Opdaterer afstanden for den pågældende slot/klient

        #----Debugging----#
        debug = False #Sæt til True for at se opdateringer i distances dict
        if debug == True:
            print("Updated:", distances)
            time.sleep(0.01)

if __name__ == "__main__":
    threading.Thread(target=receiver_thread, daemon=True).start()

    while True:
        #Vent til alle afstande er modtaget, før trilateration udføres
        if any(d is None for d in distances.values()):
            time.sleep(0.1)
            continue
        #----Trilateration----#
        result = tri_lat(
            pos_dict["p1"], distances["d1"],
            pos_dict["p2"], distances["d2"],
            pos_dict["p3"], distances["d3"],
            pos_dict["p4"], distances["d4"]
        )
        time.sleep(1) #Tilføj en lille forsinkelse for at undgå at spamme outputtet
        print(f"Estimated Position: x={result[0]}, y={result[1]}, z={result[2]}")


