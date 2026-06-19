"""
@Author: Tobias Jensen
@Date: 12/6/2026
Trilateration med Iteratively Reweighted Least Squares (IRLS).
"""
#--------Imports--------#
import numpy as np
from scipy.optimize import least_squares
from OLS import tri_lat #OLS løsning som startgæt

#-------IRLS Funktion-------#
def tri_lat_irls(p1, d1, p2, d2, p3, d3, p4, d4, max_iters=10, tol=1e-1) -> np.ndarray:
    """
    Trilateration med Iteratively Reweighted Least Squares (IRLS).
    args:
        p1...p4: Koordinater (x, y, z) for de 4 måleenheder
        d1.. d4: Estimerede afstande fra måleenhederne til det ukendte punkt
        max_iters: Maksimalt antal iterationer for IRLS
        tol: Tolerance for konvergens i meter. F.eks. er 1e-1 = 10 cm
    returns:
        x_hat: Den estimerede position (x, y, z) for det ukendte punkt
        converged: Bool der indikerer om løsningen konvergerede inden for max_iters
    """
    if any(d < 0 for d in [d1, d2, d3, d4]): #Afstande kan ikke være negative
        print('Error - distances cannot be negative') 
        return np.array([float("NaN")] * 3) #Returnerer NaN, da det eller giver matematisk mening men ikke virkelig

    anchors   = np.array([p1, p2, p3, p4], dtype=float) #Konverterer punkterne til en numpy array for lettere håndtering
    distances = np.array([d1, d2, d3, d4], dtype=float) #Konverterer afstandene til en numpy array for lettere håndtering

    #----Startgæt via OLS----#
    #x_hat er både startgæt og endelig løsning, som opdateres i hver iteration
    x_hat = tri_lat(p1, d1, p2, d2, p3, d3, p4, d4)

    #----Start med ens vægte----#
    #Vægtene sættes til 1 for alle målepunkterne i den første iteration
    weights = np.ones(len(anchors)) #np.ones(len(...)) opretter et arret med 1'er i samme længde som parameteren

    for iteration in range(max_iters): #For loop der kører op til max_iters gange, eller indtil konvergens opnås
        x_old = x_hat.copy() #Gemmer den tidligere løsning / startgæt for at kunne tjekke konvergens. 
        #Bruger copy() for at sikre at x_old er en separat kopi og ikke bare en reference til x_hat
        converged = False #Indikator for om løsning er konvergeret
        #----Trin 1----#
        # Gendefiner residualfunktionen med opdaterede vægte i hver iteration
        def weighted_residuals(x)-> np.ndarray: 
            """
            Beregner de vægtede residualer
            args:
                x: Den aktuelle estimerede position (x, y, z) for det ukendte punkt. Den kaldes med x_hat som argument
            returns:
                Vægtede residualer for hvert målepunkt, som bruges i least_squares optimeringen
            """
            r = np.linalg.norm(anchors - x, axis=1) - distances 
            #Beregner de rå residualer (forskellen mellem den estimerede afstand og den målte afstand for hvert målepunkt)
            return np.sqrt(weights) * r

        result = least_squares(weighted_residuals, x_hat, method='lm') #Bruger scipy's Levenberg-Marquardt algoritme, som gør fancy Non-Lineær matematik
        x_hat = result.x

        #----Trin 2----#
        # Opdater vægte baseret på residualer
        # Stor fejl -> lav vægt og omvendt, for at minimere indflydelsen af outliers
        residuals = np.abs(np.linalg.norm(anchors - x_hat, axis=1) - distances) #Beregner de absolutte residualer for den nye løsning, axis=1 betyder at det beregnes for hver række (hvert målepunkt)
        weights = 1 / (residuals + tol) #Opdaterer vægtene. Tol tilføjes udelukkende for at undgå division med nul 

        #----Trin 3----#
        # Stop hvis løsningen når løsningen er inden for konvergenstolerence
        if np.linalg.norm(x_hat - x_old) < tol: #Tjekker om ændringen i løsningen er mindre end den angivne tolerance, hvilket indikerer konvergens
            converged = True #Sætter converged til True, hvis konvergens er opnået, hvilket gør at den rent faktisk bliver brugt på serveren
            break #

    return x_hat, converged #Returnerer x_hat og konvergens indikator