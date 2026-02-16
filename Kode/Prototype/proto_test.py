"""
@author: Tobias Jensen
@date: 13/2/2026
This file contains a prototype for testing the RSSI converter and trilateration algorithm together.
"""

#--------Imports--------#

from RSSI_proto1_testing import average_rssi, rssi_to_distance
from trilat_test_3D_testing import tri_lat

if __name__ == "__main__":
    p1 = (0, 3, 0)
    p2 = (-3, 0, 0)
    p3 = (0, 6, 0)
    p4 = (3, 0, 2)
    rssi_values1 = [-50, -55, -60, -65]               #En liste af RSSI-værdier i dBm. Dette burde normalt komme fra reale målinger.
    rssi_values2 = [-45, -50, -55, -60]               #En anden liste af RSSI-værdier for at teste gennemsnitsfunktionen.
    rssi_values3 = [-40, -45, -50, -55]               #En tredje liste af RSSI-værdier for yderligere test.
    rssi_values4 = [-35, -40, -45, -50]               #En fjerde liste af RSSI-værdier for at teste funktionen med stærkere signaler.

    average_rssi_value1 = average_rssi(rssi_values1)   #Gemmer gennemsnittet af RSSI-værdierne i en variabel
    average_rssi_value2 = average_rssi(rssi_values2)   #Gemmer gennemsnittet af RSSI-værdierne i en variabel
    average_rssi_value3 = average_rssi(rssi_values3)   #Gemmer gennemsnittet af RSSI-værdierne i en variabel
    average_rssi_value4 = average_rssi(rssi_values4)   #Gemmer gennemsnittet af RSSI-værdierne i en variabel
    A = -40  #RSSI ved 1 meter
    n = 2    #Path loss exponent, for frit rum er typisk 2
    d1 = rssi_to_distance(average_rssi_value1, A, n) #Smider de forskellige værdier ind i funktionen for at få den estimerede afstand
    d2 = rssi_to_distance(average_rssi_value2, A, n)
    d3 = rssi_to_distance(average_rssi_value3, A, n)
    d4 = rssi_to_distance(average_rssi_value4, A, n)
    result = tri_lat(p1, d1, p2, d2, p3, d3, p4, d4)
    print(f"Position: x={result[0]}, y={result[1]}, z={result[2]}")