#!/usr/bin/env python3
"""
@Author: Tobias Jensen
@Date: 29/4/2026
RSSI calibration tool
Collects N RSSI samples for a known distance
and calculates average RSSI for calibration.

Usage:
sudo python3 rssi_calibration.py -i wlan1 --mac aa:bb:cc:dd:ee:ff -c 6/11
"""

#--------Imports--------#
import argparse, signal, subprocess, time
from scapy.all import sniff, RadioTap, Dot11
import numpy as np

#--------Configuration--------#
SAMPLES_REQUIRED = int(input("Enter the number of samples to collect: ") or "10000") #Antallet af samples
samples = []
stop = False

#--------Functions--------#
def handle_sigint(sig, frame): #Funktion til at stoppe kalibreringen tidligt ved Ctrl+C
    global stop
    print("\n[*] Stopping calibration early…")
    stop = True


def set_channel(interface, channel):
    """
    Funktion til at sætte Wi-Fi interfacet til den ønskede channel. 
    args:
    interface: Navnet på Wi-Fi interfacet (f.eks. "wlan1")
    channel: Det Wi-Fi channel, der skal sættes (f.eks. 6 eller 11)
    """
    subprocess.run( #Starter en ekstern linux command
        ["iw", "dev", interface, "set", "channel", str(channel)], #Eksempel: iw dev iwlan1 set channel 6
        check=False
    )


def get_rssi(packet):
    """
    Funktion til at udtrække RSSI-værdi fra pakken ved hjælp af Scapy's RadioTap-lag.
    RadioTap-laget indeholder metadata om Wi-Fi-pakken, herunder signalstyrken (RSSI).
    args:
    packet: Scapy-pakken
    returns:
    RSSI-værdien i dBm, eller None hvis den ikke kan udtrækkes
    """

    if packet.haslayer(RadioTap): #Tjekker om pakken har radiotap-lag
        try:
            return packet[RadioTap].dBm_AntSignal #Udtrækker RSSI-værdien fra radiotap-laget
        except AttributeError: #Hvis dBm_AntSignal ikke findes i radiotap-laget, returneres None
            return None
    return None


def packet_handler(packet, mac_filter):
    """
    Funktion til at behandle en modtaget pakke og tilføje RSSI-værdien til listen over samples.
    args:
    packet: Scapy-pakken
    mac_filter: MAC-adressen på den enhed, der skal kalibreres mod (Dronen i dette tilfælge(E4:7A:2C:CC:FD:24))
    """
    global samples
    if len(samples) >= SAMPLES_REQUIRED: #Hvis det ønskede antal samples er insamlet stopper funktionen
        return

    if not packet.haslayer(Dot11): #Hvis pakken ikke har Dot11-lag, stopper funktionen
        return

    rssi = get_rssi(packet) #Gemmen målt RSSI-værdi i rssi variablen
    if rssi is None: #Hvis RSSI-værdien ikke kunne udtrækkes, stopper funktionen
        return

    dot11 = packet[Dot11] #Gemmer Dot11 laget i dot11 variablen.
    addrs = {a.lower() for a in [dot11.addr1, dot11.addr2, dot11.addr3] if a} #Udtrækker alle MAC-adresser fra pakken og gemmer dem i et set (addrs)

    if mac_filter not in addrs: #Hvis den ønskede MAC-adresse ikke findes i pakken, stopper funktionen
        return

    samples.append(rssi) #Tilføjer den målte RSSI-værdi til listen over samples

    if len(samples) % 500 == 0: #Udskriver status hver 500. sample
        print(f"Collected {len(samples)} / {SAMPLES_REQUIRED} samples") #Udskriver antal insamlede samples


def main():
    """
    Main funktion der håndterer argumenter, signaler og starter sniffing-processen for at indsamle RSSI-samples.

    """
    #--------Argument Parsing--------#
    parser = argparse.ArgumentParser(description="RSSI Calibration Tool")
    parser.add_argument("-i", "--interface", default="wlan1") #Argument for Wi-Fi interface.
    parser.add_argument("-c", "--channel", type=int, required=True) #Argument for Wi-Fi channel (1-13)
    parser.add_argument("--mac", required=True, help="BSSID to calibrate against") #Argument for MAC-adressen 
    #eksempel: sudo python3 calibration.py -i wlan1 --mac E4:7A:2C:CC:FD:24 -c 6

    args = parser.parse_args() #

    signal.signal(signal.SIGINT, handle_sigint) #Registrerer signalhåndtering for Ctrl+C (SIGINT) for at stoppe kalibreringen tidligt

    print(f"[*] Locking to channel {args.channel}") #Udskriver hvilken channel der låses til
    set_channel(args.interface, args.channel) #Sætter Wi-Fi interfacet til den ønskede channel

    print(f"[*] Calibrating against {args.mac}") #Udskriver hvilken MAC-adresse der kalibreres mod
    print(f"[*] Gathering {SAMPLES_REQUIRED} RSSI samples…\n") #Udskriver at indsamlingen af RSSI-samples er startet

    while not stop and len(samples) < SAMPLES_REQUIRED: #Kører loop til stop == true eller det ønskede antal samples er indsamlet
        sniff( #Starter sniffing-processen for at indsamle Wi-Fi-pakker på det angivne interface og channel
            iface=args.interface, #Wi-Fi interface der skal sniffes på
            prn=lambda pkt: packet_handler(pkt, args.mac.lower()), #Funktion der kaldes for hver modtaget pakke, med MAC-filteret som argument
            store=False, #Angiver at pakker ikke skal gemmes i hukommelsen
            timeout=1, #Angiver at sniffing-processen skal køre i 1 sekund ad gangen
        ) 

    if len(samples) == 0: #Hvis ingen samples er indsamlet, udskrives en advarsel og programmet afsluttes
        #Dette sker hvis f.eks. MAC-adressen er forkert.
        print("[!] No samples collected")
        return

    rssi_array = np.array(samples) #Konverterer listen over samples til en NumPy-array for nemmere beregning af statistik
    mean_rssi = np.mean(rssi_array) #Beregner gennemsnittet af de indsamlede RSSI-samples
    std_rssi = np.std(rssi_array) #Beregner standardafvigelsen af de indsamlede RSSI-samples

    print("\n=== Calibration result ===") #Udskriver kalibreringsresultaterne, herunder antal indsamlede samples, gennemsnitlig RSSI og standardafvigelse
    print(f"Samples collected : {len(samples)}")
    print(f"Mean RSSI         : {mean_rssi:.2f} dBm")
    print(f"Std deviation    : {std_rssi:.2f} dB")

    print("\nRecommended calibration constant:")
    print(f"RSSI_0 = {mean_rssi:.2f}  (use at known distance)")

    print("\n[*] Calibration done.")


if __name__ == "__main__":
    main()