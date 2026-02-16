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
    rssi_values = [-50, -55, -60, -65]               #En liste af RSSI-værdier i dBm. Dette burde normalt komme fra reale målinger.
    average_rssi_value = average_rssi(rssi_values)   #Gemmer gennemsnittet af RSSI-værdierne i en variabel
    print(f"Average RSSI: {average_rssi_value} dBm") #Udskriver gennemsnittet af RSSI-værdierne i dBm. Dette er den værdi, der vil blive brugt til at estimere afstanden.

    A = -40  #RSSI ved 1 meter
    n = 2    #Path loss exponent, for frit rum er typisk 2
    distance = rssi_to_distance(average_rssi_value, A, n) #Smider de forskellige værdier ind i funktionen for at få den estimerede afstand
    print(f"Estimated distance: {distance:.2f} meters")   #Printer den estimerede afstand i meter, afrundet til to decimaler.
