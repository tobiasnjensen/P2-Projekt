"""
@author: Tobias Jensen
@date: 13/2/2026
This file contains a prototype for a 2D trilateration algorithm.
"""

#--------Imports--------#
import numpy as np

def tri_lat(p1, d1, p2, d2, p3, d3):
    #----Extract coordinates from points----#
    #Gemmer koordinaterne fra punkterne i nye x og y variabler
    x1, y1 = p1 
    x2, y2 = p2 
    x3, y3 = p3 

    #----Lineær algebra stuff----#   
    #Matrix A (Koefficienterne x, y and z)
    A = np.array([
        [2*(x2 - x1), 2*(y2 - y1)],
        [2*(x3 - x1), 2*(y3 - y1)]
    ])
    
    #Vector b (Højre side)
    b = np.array([
        x2**2 - x1**2 + y2**2 - y1**2 + d1**2 - d2**2,
        x3**2 - x1**2 + y3**2 - y1**2 + d1**2 - d3**2
    ]) #
    
    # Solve Ax = b for [x, y]
    solution = np.linalg.solve(A, b) #Løser det lineære ligningssystem for at finde x og y koordinaterne for den ukendte position
    
    return solution  #Returnerer løsning som et array (vektor) med x og y koordinater

#Test med tilfældig data. (Skal tage data fra RSSI converter senere)
p1 = (0, 3)
d1 = 3.16
p2 = (-3, 0)
d2 = 4
p3 = (0, 6)
d3 = 5

#Kald trilateration funktionen med testdata og print resultatet (Skal plottes laves et live plot senere, når vi kan måle i realtid)
result = tri_lat(p1, d1, p2, d2, p3, d3)
print(f"Position: x={result[0]}, y={result[1]}")

