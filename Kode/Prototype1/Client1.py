"""
@Author: Tobias Jensen
@Date: 16/2/2026
This file contains a prototype for an RSSI buffer that stores the most recent RSSI readings and calculates the average.
This buffer is then sent to a server via UDP
"""

#--------Imports--------#
from collections import deque
import random, time
from socket import *

#--------Configuration--------#
SERVER_IP = "127.0.0.1"
SERVER_PORT = 8787
BUFFER_SIZE = 1024
s = socket(AF_INET, SOCK_DGRAM) 

MAX_SIZE = 10
rssi_buffer = deque(maxlen=MAX_SIZE) #Opretter en deque, med en maks længde på 10. Når det overskrides vil den aldste fjernes

#--------Functions--------#
def add_rssi_value(rssi_value):
    """
    Add a new RSSi reading to the buffer.
    If the buffer exceeds the maximum size, the oldest value will be automatically removed.
    """
    rssi_buffer.append(rssi_value)

def get_average_rssi():
    """
    Calculate and return the average RSSI value from the buffer.
    If the buffer is empty, return None.
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