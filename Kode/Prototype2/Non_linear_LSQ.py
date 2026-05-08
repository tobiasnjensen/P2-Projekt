"""
@author: Tobias Jensen
@date: 22/4/2026
Trilateration med ikke-lineær mindste kvadrater (scipy least_squares)
"""
#--------Imports--------#
import numpy as np
from scipy.optimize import least_squares

#--------Functions--------#
def tri_lat(p1, d1, p2, d2, p3, d3, p4, d4) -> np.ndarray:
    """
    Trilateration funktion der estimerer positionen baseret på 4 kendte punkter, og afstande til ukendt punkt.
    args:
    p1, p2, p3, p4: Koordinater for de 4 måleenheder 
    d1, d2, d3, d4: Estimerede afstande fra de 4 måleenheder til det ukendte punkt
    returns:
    result.x: Den estimerede position (x, y, z) for det ukendte punkt
    """
    if (d1<0 or d2<0 or d3<0 or d4<0): #Vi kan ikke have negative afstande
        print('Error - distances cannot be negative')
        return np.array([float("NaN"), float("NaN"), float("NaN")])
    elif (p1[0]==p2[0]==p3[0]==p4[0]==0 or p1[1]==p2[1]==p3[1]==p4[1]==0 or p1[2]==p2[2]==p3[2]==p4[2]==0): #Hvis f.eks. alle x-koordinater er ens, så kan vi ikke bestemme en unik position i 3D-rummet
        print('Error - anchors cannot be collinear')
        return np.array([float("NaN"), float("NaN"), float("NaN")])
    anchors = np.array([p1, p2, p3, p4])
    distances = np.array([d1, d2, d3, d4])

    def residuals(pos) -> np.ndarray:
        """
        Residuals funktion der beregner forskellen mellem de estimerede afstande og de faktiske afstande baseret på den nuværende position.
        args:
        pos: Den nuværende estimerede position (x, y, z)
        returns:
        Forskellen mellem de estimerede og faktiske afstande
        """
        return np.linalg.norm(anchors - pos, axis=1) - distances

    x0 = anchors.mean(axis=0)
    result = least_squares(residuals, x0) #Bruger scipy's least_squares funktion til at minimere residuals og finde den bedste approximative position
    return result.x #Returnerer den estimerede position (x, y, z) for det ukendte punkt baseret på de 4 kendte punkter og afstande



if __name__ == "__main__":
    p1 = (0, 3, 0)
    d1 = 3.16
    p2 = (-3, 0, 0)
    d2 = 4
    p3 = (0, 6, 0)
    d3 = 5
    p4 = (3, 0, 0)
    d4 = 4.24

    result = tri_lat(p1, d1, p2, d2, p3, d3, p4, d4)
    print(f"Position: x={result[0]:.2f}, y={result[1]:.2f}, z={result[2]:.2f}")