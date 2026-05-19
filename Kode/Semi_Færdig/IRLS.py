"""
@Author: Tobias Jensen
@Date: 12/6/2026
Trilateration med Iteratively Reweighted Least Squares (IRLS).
"""

import numpy as np
from scipy.optimize import least_squares
from OLS import tri_lat #OLS løsning som startgæt

def tri_lat_irls(p1, d1, p2, d2, p3, d3, p4, d4, max_iters=10, tol=1e-1) -> np.ndarray: #tol = 10 cm
    """
    Trilateration med Iteratively Reweighted Least Squares (IRLS).
    args:
        p1..p4: Koordinater (x, y, z) for de 4 måleenheder
        d1..d4: Estimerede afstande fra måleenhederne til det ukendte punkt
        max_iters: Maksimalt antal iterationer for IRLS
        tol: Tolerance for konvergens
    returns:
        x_hat: Den estimerede position (x, y, z) for det ukendte punkt
    """
    if any(d < 0 for d in [d1, d2, d3, d4]): #Afstande kan ikke være negative
        print('Error - distances cannot be negative') 
        return np.array([float("NaN")] * 3) #Returnerer NaN, da det eller giver matematisk mening men ikke virkelig

    anchors   = np.array([p1, p2, p3, p4], dtype=float) #Konverterer punkterne til en numpy array for lettere håndtering
    distances = np.array([d1, d2, d3, d4], dtype=float) #Konverterer afstandene til en numpy array for lettere håndtering

    #----Startgæt via OLS----#
    x_hat = tri_lat(p1, d1, p2, d2, p3, d3, p4, d4)

    #----Start med ens vægte----#
    weights = np.ones(len(anchors))

    for iteration in range(max_iters):
        x_old = x_hat.copy()
        converged = False
        #----Trin 1----#
        # Gendefiner residualfunktionen med opdaterede vægte i hver iteration
        def weighted_residuals(x):
            r = np.linalg.norm(anchors - x, axis=1) - distances
            return np.sqrt(weights) * r

        result = least_squares(weighted_residuals, x_hat, method='lm')
        x_hat = result.x

        #----Trin 2----#
        # Opdater vægte baseret på residualer
        # Stor fejl -> lav vægt og omvendt, for at minimere indflydelsen af outliers
        residuals = np.abs(np.linalg.norm(anchors - x_hat, axis=1) - distances)
        weights = 1 / (residuals + tol)

        #----Trin 3----#
        # Stop hvis løsningen når løsningen er inden for konvergenstolerence
        if np.linalg.norm(x_hat - x_old) < tol:
            converged = True
            break

    return x_hat, converged