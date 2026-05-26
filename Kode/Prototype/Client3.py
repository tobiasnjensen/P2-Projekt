"""
@Author: Tobias Jensen
@Date: 16/2/2026
Klientprogram som skal forestille sig en måleenhed, som genererer tilfældige RSSI-værdier og sender dem til lokal server.
Fil nr 3 af 4. De er identiske
"""
#--------Imports--------#
from collections import deque
import random, time
from socket import *

#----------------------------------#
#          Konfiguration           #
#----------------------------------#

#--------Server Konfiguration--------#
SERVER_IP = "127.0.0.1"
SERVER_PORT = 8787
BUFFER_SIZE = 1024
s = socket(AF_INET, SOCK_DGRAM) 

#--------RSSI Buffer Konfiguration--------#
MAX_SIZE = 10
rssi_buffer = deque(maxlen=MAX_SIZE) #Opretter en deque, med en maks længde på 10. Når det overskrides vil den aldste fjernes

#----------------------------------#
#            Functions             #
#----------------------------------#

def add_rssi_value(rssi_value) -> None:
    """
    Tilføjer en RSSI-værdi til buffer.
    Det er en form for FIFO buffer, så den gamle værdi vil blive fjernet, hvis buffer er fuld.
    """
    rssi_buffer.append(rssi_value)

def get_average_rssi() -> float|None:
    """
    Regner gennemsnittet af RSSI-værdierne i buffer. Hvis buffer er tom, returneres None.
    """
    if len(rssi_buffer) == 0:
        return None
    
    return sum(rssi_buffer) / len(rssi_buffer)

#--------Main--------#
if __name__ == "__main__":
    while True:
        add_rssi_value(random.randint(-100, -30))  
        s.sendto(str(get_average_rssi()).encode(), (SERVER_IP, SERVER_PORT))  
        time.sleep(1)