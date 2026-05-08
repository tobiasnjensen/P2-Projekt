"""
@author: Tobias Jensen
@date: 22/4/2026
Trilateration med vægtet lineær least squares"""

#--------Imports--------#
import numpy as np

#--------Functions--------#
def tri_lat_wls(p1, d1, w1, p2, d2, w2, p3, d3, w3, p4, d4, w4) -> np.ndarray:
    """
    Trilateration med lineær Weighted Least Squares (WLS).
    Lineariserer sfæreligningerne og anvender vægte direkte på det lineære system.
    
    Strategi: Subtraher den måleenhed med højest vægt fra de øvrige,
    så den mest pålidelige måling bevares bedst muligt i lineariseringen.
    
    args:
        p1..p4: Koordinater (x, y, z) for de 4 måleenheder
        d1..d4: Estimerede afstande fra måleenhederne til det ukendte punkt
        w1..w4: Vægte for hver måleenhed (højere = mere pålidelig)
    returns:
        x_hat: Den estimerede position (x, y, z) for det ukendte punkt
    """
    if any(d < 0 for d in [d1, d2, d3, d4]):
        print('Error - distances cannot be negative')
        return np.array([float("NaN")] * 3)

    anchors = np.array([p1, p2, p3, p4], dtype=float)
    distances = np.array([d1, d2, d3, d4], dtype=float)
    weights = np.array([w1, w2, w3, w4], dtype=float)

    # Vælg referencemåling som den med højest vægt
    ref_idx = np.argmax(weights)
    other_idx = [i for i in range(len(anchors)) if i != ref_idx]

    # Byg A-matrix og b-vektor ved at subtrahere referenceligningen
    A = []
    b = []
    row_weights = []

    for i in other_idx:
        row = 2 * (anchors[i] - anchors[ref_idx])
        rhs = (distances[ref_idx]**2 - distances[i]**2
                - np.dot(anchors[ref_idx], anchors[ref_idx])
                + np.dot(anchors[i], anchors[i]))
        A.append(row)
        b.append(rhs)
        # Vægt for differensligning: geometrisk middel af de to involverede vægte
        row_weights.append(np.sqrt(weights[ref_idx] * weights[i]))

    A = np.array(A)
    b = np.array(b)

    # Vægtmatrix
    W = np.diag(row_weights)

    # WLS løsning: x_hat = ((WA)^T WA)^-1 (WA)^T Wb
    WA = W @ A
    Wb = W @ b
    x_hat = np.linalg.lstsq(WA, Wb, rcond=None)[0]

    return x_hat


#--------Main--------#
if __name__ == "__main__":
    p1 = (0, 3, 3)
    d1 = 3.16
    w1 = 1       # Høj vægt - pålidelig måling

    p2 = (-3, 0, 0)
    d2 = 4
    w2 = 0.1       # Lav vægt - upålidelig måling

    p3 = (0, 6, 1)
    d3 = 5
    w3 = 0.1       # Lav vægt - upålidelig måling

    p4 = (3, 0, 0)
    d4 = 4.24
    w4 = 0.5       # Mellem vægt

    result = tri_lat_wls(p1, d1, w1, p2, d2, w2, p3, d3, w3, p4, d4, w4)
    print(f"Position: x={result[0]:.2f}, y={result[1]:.2f}, z={result[2]:.2f}")