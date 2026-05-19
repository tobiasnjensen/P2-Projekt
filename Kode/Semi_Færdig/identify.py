"""
@Author: Tobias Jensen
@Date: 15/5/2026
Simpel drone-klassificering baseret på bevægelsesmønstre.
Gemmer en positions-historik per BSSID og vurderer om enheden opfører sig som en drone.

Kald fra server.py efter trilateration:
    from drone_classifier import update_history, is_drone
    update_history(bssid, float(x_hat[0]), float(x_hat[1]), float(x_hat[2]), time.time())
    if is_drone(bssid):
        print(f"Drone detekteret: {bssid}")
"""

import math
from collections import deque
from discord_alarm import send_discord_alarm

# -------Konfiguration------- #
MIN_SAMPLES       = 5     # Minimum antal positioner før klassificering
MAX_HISTORY       = 30    # Maks positioner gemt per enhed
HEIGHT_THRESHOLD  = 0.25   # Minimum højde i meter for at tælle som "i luften"
MIN_SPEED         = 1.5  # Minimum hastighed i m/s — filtrerer fastmonterede AP'er fra
MAX_SPEED         = 20.0  # Maksimal hastighed i m/s — filtrerer biler/fly fra

# Intern historik: { bssid -> deque af (x, y, z, t) }
_history = {}
_first_seen = {}

def update_history(bssid, x, y, z, timestamp):
    """Tilføjer en ny position med tidsstempel til historikken for det givne BSSID."""
    if bssid not in _history:
        _history[bssid] = deque(maxlen=MAX_HISTORY)
        _first_seen[bssid] = timestamp  # Gem kun første gang
    _history[bssid].append((x, y, z, timestamp))


def is_drone(bssid):
    """
    Returnerer True hvis enheden opfører sig som en drone, ellers False.
    Kræver mindst MIN_SAMPLES positioner i historikken.
    Kriterier:
        1. Gennemsnitshøjde over HEIGHT_THRESHOLD
        2. Gennemsnitshastighed mellem MIN_SPEED og MAX_SPEED
    """
    samples = list(_history.get(bssid, []))

    if len(samples) < MIN_SAMPLES:
        return False

    # Kriterium 1: Højde
    recent = samples[-MIN_SAMPLES:]

    avg_z = sum(s[2] for s in recent) / len(recent)
    if avg_z < HEIGHT_THRESHOLD:
        return False

    # Kriterium 2: Hastighed (med faktiske timestamps)
    speeds = []
    for i in range(1, len(recent)):
        x1, y1, z1, t1 = recent[i - 1]
        x2, y2, z2, t2 = recent[i]
        dt = t2 - t1
        if dt <= 0:
            continue
        dist = math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)
        speeds.append(dist / dt)

    if not speeds:
        return False

    avg_speed = sum(speeds) / len(speeds)
    if not (MIN_SPEED <= avg_speed <= MAX_SPEED):
        return False

    return True

if __name__ == "__main__":
    bssid = "00:11:22:33:44:55"
    for i in range(10):
        update_history(bssid, x=i * 0.5, y=0, z=2.0, timestamp=i)  # Bevæger sig 0.5 m/s
    if is_drone(bssid):
        send_discord_alarm(f"Drone detekteret: {bssid} ved position (IDK, det en test)")
