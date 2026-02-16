"""
@author: Tobias Jensen
@date: 13/2/2026
This file contains a prototype for a 3D trilateration algorithm.
"""

#--------Imports--------#
import numpy as np

def tri_lat(p1, d1, p2, d2, p3, d3, p4, d4):
    #----Extract coordinates from points----#
    #Gemmer koordinaterne fra punkterne i nye x og y variabler
    x1, y1, z1 = p1 
    x2, y2, z2 = p2 
    x3, y3, z3 = p3 
    x4, y4, z4 = p4

    #----Lineær algebra stuff----#   
    #Matrix A (Koefficienterne x, y and z)
    A = np.array([
        [2*(x2 - x1), 2*(y2 - y1), 2*(z2 - z1)],
        [2*(x3 - x1), 2*(y3 - y1), 2*(z3 - z1)],
        [2*(x4 - x1), 2*(y4 - y1), 2*(z4 - z1)]
    ])
    
    #Vector b (Højre side)
    b = np.array([
        x2**2 - x1**2 + y2**2 - y1**2 + z2**2 - z1**2 + d1**2 - d2**2,
        x3**2 - x1**2 + y3**2 - y1**2 + z3**2 - z1**2 + d1**2 - d3**2,
        x4**2 - x1**2 + y4**2 - y1**2 + z4**2 - z1**2 + d1**2 - d4**2
    ]) #
    
    #Solve
    solution = np.linalg.solve(A, b) #Løser det lineære ligningssystem for at finde x, y og z koordinaterne for den ukendte position
    
    return solution  #Returnerer løsning som et array (vektor) med x, y og z koordinater

#--------Test med tilfældig data. (Skal tage data fra RSSI converter senere)--------#
p1 = (0, 3, 0)
d1 = 3.16
p2 = (-3, 0, 0)
d2 = 4
p3 = (0, 6, 0)
d3 = 5
p4 = (3, 0, 2)
d4 = 4.24
#Kald trilateration funktionen med testdata og print resultatet (Skal plottes laves et live plot senere, når vi kan måle i realtid)
result = tri_lat(p1, d1, p2, d2, p3, d3, p4, d4)
print(f"Position: x={result[0]}, y={result[1]}, z={result[2]}")

