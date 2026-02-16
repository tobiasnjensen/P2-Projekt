"""
@author: Tobias Jensen
@date: 13/2/2026
This file contains a prototype for a RSSI converter
"""

#--------Funktioner--------#
def average_rssi(rssi_values):
    """
    Måler gennemsnittet af en liste af RSSI-værdier.

    Parameters:
    rssi_values (list af float): En liste af RSSI-værdier (i dBm).
    
    Returns:
    float: Gennemsnittet af RSSI-værdierne.
    """
    if not rssi_values:
        raise ValueError("The list of RSSI values cannot be empty.")
    
    average = sum(rssi_values) / len(rssi_values)
    return average

def rssi_to_distance(rssi, A, n):
    """
    Estimerer afstanden baseret på RSSI-værdien ved hjælp af en simpel path loss model.
    
    Parameters:
    rssi (float): The received signal strength indicator (in dBm).
    A (float): The RSSI value at a reference distance (usually 1 meter).
    n (float): The path loss exponent, which varies based on the environment. #For free space, n is typically 2.
    
    Returns:
    float: The estimated distance in meters.
    """
    distance = 10 ** ((A - rssi) / (10 * n))
    return distance

#--------Eksempel--------#
if __name__ == "__main__": 
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
    print(f"Estimated distance 1: {d1:.2f} meters")  #Printer den estimerede afstand i meter, afrundet til to decimaler.
    print(f"Estimated distance 2: {d2:.2f} meters")
    print(f"Estimated distance 3: {d3:.2f} meters")
    print(f"Estimated distance 4: {d4:.2f} meters")