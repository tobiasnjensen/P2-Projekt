#!/usr/bin/env python3
"""
@Tobias Jensen
@date: 22/4/2026
RSSI Scanner for Raspberry Pi with RTL8187 Wireless Adapter

Usage:
    For test på telefon med hotspot:
    sudo python3 rssi_scanner.py -i wlan1 --mac aa:bb:cc:dd:ee:ff -c 6
    find mac med airodump-ng. Kan finde på OneNote
"""

import argparse, collections, signal, subprocess, threading, time, socket, json
from datetime import datetime
from scapy.all import sniff, RadioTap, Dot11, Dot11Beacon, Dot11ProbeResp

#Server setup
SERVER_IP = "192.168.0.102" 
UDP_PORT = 6769

#RTL8187 driver offset
RTL8187_OFFSET = 0 #Fungerer fint uden offset, men kan justeres.

#Rolling average window size (number of packets)
ROLLING_WINDOW = int(input("Enter rolling average window size (default 10): ") or "10")



stop_event = threading.Event() #Opretter et threading Event-objekt der bruges til at stoppe sniffing-loopet på tværs af tråde

def rssi_to_distance(rssi, tx_power=-17.1, path_loss_exp=2.7) -> float:
    """
    Konverterer en RSSI-værdi til en estimeret afstand i meter ved hjælp af log-distance path loss modellen.
    args:
    rssi: Den målte signalstyrke i dBm
    tx_power: Kalibreret RSSI-værdi ved 1 meters afstand (RSSI_0), standard -17.1 dBm
    path_loss_exp: Path loss eksponent der beskriver signalets dæmpning gennem mediet, standard 2.7
    returns:
    Estimeret afstand i meter
    """
    return 10 ** ((tx_power - rssi) / (10 * path_loss_exp))

def handle_sigint(sig, frame):
    """
    Signalhåndtering for Ctrl+C (SIGINT).
    Sætter stop_event så sniffing-loopet afsluttes pænt.
    """
    print("\n[*] Ctrl+C caught — stopping...")
    stop_event.set() #Sætter stop_event til True så sniffing-loopet afsluttes


def bring_interface_up(interface: str) -> bool:
    """
    Forsøger at genstarte Wi-Fi interfacet i monitor mode, hvis det er gået ned.
    Sætter interfacet ned, skifter til monitor mode og starter det op igen.
    args:
    interface: Navnet på Wi-Fi interfacet (f.eks. "wlan1")
    returns:
    True hvis genstarten lykkedes, False hvis den fejlede
    """
    try:
        print(f"\n[!] Interface down — attempting to recover {interface}...")
        subprocess.run(["sudo", "ip", "link", "set", interface, "down"], check=True) #Sætter interfacet ned
        subprocess.run(["sudo", "iw", "dev", interface, "set", "type", "monitor"], check=True) #Sætter interfacet til monitor mode
        subprocess.run(["sudo", "ip", "link", "set", interface, "up"], check=True) #Starter interfacet op igen
        time.sleep(1) #Venter 1 sekund på at interfacet er klar
        print(f"[*] {interface} recovered.\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Recovery failed: {e}")
        return False


def get_rssi(packet) -> int | None:
    """
    Funktion til at udtrække RSSI-værdien fra pakken ved hjælp af Scapy's RadioTap-lag,
    og korrigerer den med RTL8187-driverens offset.
    args:
    packet: Scapy-pakken
    returns:
    Korrigeret RSSI-værdi i dBm, eller None hvis den ikke kan udtrækkes
    """
    if packet.haslayer(RadioTap): #Tjekker om pakken har et RadioTap-lag
        try:
            raw = packet[RadioTap].dBm_AntSignal #Udtrækker den rå RSSI-værdi fra RadioTap-laget
            return raw + RTL8187_OFFSET #Returnerer den korrigerede RSSI-værdi
        except AttributeError: #Hvis dBm_AntSignal ikke findes i RadioTap-laget, returneres None
            return None
    return None


def get_ssid(packet) -> str:
    """
    Funktion til at udtrække SSID-navnet fra en Beacon- eller ProbeResponse-pakke.
    args:
    packet: Scapy-pakken
    returns:
    SSID-strengen, "<hidden>" hvis SSID er tomt, eller "<unknown>" hvis pakken ikke er af den rette type
    """
    if packet.haslayer(Dot11Beacon) or packet.haslayer(Dot11ProbeResp): #Tjekker om pakken er en Beacon eller ProbeResponse
        try:
            ssid = packet[Dot11].info.decode("utf-8", errors="replace") #Dekoder SSID-feltet fra bytes til string
            return ssid if ssid else "<hidden>" #Returnerer SSID eller "<hidden>" hvis det er tomt
        except Exception:
            return "<unknown>"
    return "<unknown>"


def make_packet_handler(mac_filter: str | None, udp_sock, target_address):
    """
    Factory-funktion der opretter og returnerer en packet_handler-funktion med de givne parametre.
    Bruges til at indkapsle MAC-filter, UDP-socket og rolling average historik i handleren.
    args:
    mac_filter: MAC-adresse der filtreres på, eller None for alle enheder
    udp_sock: UDP-socket der bruges til at sende data til serveren
    target_address: Tuple med serverens IP-adresse og port (SERVER_IP, UDP_PORT)
    returns:
    packet_handler: Funktion der behandler en enkelt Scapy-pakke
    """
    mac_filter_normalized = mac_filter.lower() if mac_filter else None #Normaliserer MAC-filteret til lowercase

    rssi_history: dict[str, collections.deque] = {} #Dictionary der gemmer en rolling RSSI-historik per BSSID

    def packet_handler(packet) -> None:
        """
        Indre funktion der behandler én modtaget Wi-Fi-pakke.
        Udtrækker RSSI, beregner rolling average, estimerer afstand og sender data via UDP.
        args:
        packet: Scapy-pakken der skal behandles
        """
        rssi = get_rssi(packet) #Udtrækker RSSI-værdien fra pakken
        if rssi is None: #Hvis RSSI-værdien ikke kunne udtrækkes, stoppes funktionen
            return
        if not packet.haslayer(Dot11): #Hvis pakken ikke har et Dot11-lag, stoppes funktionen
            return

        dot11 = packet[Dot11] #Gemmer Dot11-laget i dot11 variablen
        addrs = {a.lower() for a in [dot11.addr1, dot11.addr2, dot11.addr3] if a} #Udtrækker alle MAC-adresser fra pakken og gemmer dem i et set

        if mac_filter_normalized and mac_filter_normalized not in addrs: #Hvis MAC-filteret er aktivt og adressen ikke matcher, stoppes funktionen
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3] #Opretter et tidsstempel for den aktuelle pakke
        bssid = (dot11.addr3 or dot11.addr2 or "??:??:??:??:??:??").lower() #Udtrækker BSSID fra pakken (addr3 foretrækkes, fallback til addr2)

        if bssid not in rssi_history: #Hvis BSSID'et ikke kendes endnu, oprettes en ny deque til det
            rssi_history[bssid] = collections.deque(maxlen=ROLLING_WINDOW) #Opretter en ny deque med maks ROLLING_WINDOW elementer
        rssi_history[bssid].append(rssi) #Tilføjer den aktuelle RSSI-værdi til historikken for dette BSSID
        avg_rssi = sum(rssi_history[bssid]) / len(rssi_history[bssid]) #Beregner den rullende gennemsnits-RSSI for dette BSSID

        distance = rssi_to_distance(avg_rssi) #Konverterer den gennemsnitlige RSSI til en estimeret afstand
        udp_sock.sendto( #Sender en JSON-pakke med måledata til serveren via UDP
            json.dumps({
                "timestamp": timestamp,   #Tidsstempel for målingen
                "bssid": bssid,           #BSSID på den detekterede enhed
                "distance": distance,     #Estimeret afstand i meter
                "anchor_id": "anchor_1"  #Identifikator for denne Raspberry Pi (hardcoded per Pi)
            }).encode('utf-8'),
            target_address #Serverens IP og port
        )

    return packet_handler #Returnerer den færdige handler-funktion


def stop_filter(_):
    """
    Stopfunktion der bruges af Scapy's sniff() til at afgøre hvornår sniffing skal stoppe.
    Returnerer True når stop_event er sat (Ctrl+C er trykket).
    """
    return stop_event.is_set()


def set_channel(interface: str, channel: int):
    """
    Funktion til at sætte Wi-Fi interfacet til den ønskede kanal.
    args:
    interface: Navnet på Wi-Fi interfacet (f.eks. "wlan1")
    channel: Det Wi-Fi channel der skal sættes (f.eks. 6 eller 11)
    """
    subprocess.run(
        ["iw", "dev", interface, "set", "channel", str(channel)], #Eksempel: iw dev wlan1 set channel 6
        check=False
    )


def main():
    """
    Main funktion der håndterer argumenter, signaler og starter sniffing-loopet.
    Opretter en UDP-socket, parser argumenter, og kører sniffing indtil stop_event sættes.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #Opretter en UDP-socket til at sende data til serveren
    target_address = (SERVER_IP, UDP_PORT) #Tuple med serverens IP-adresse og port

    #--------Argument Parsing--------#
    parser = argparse.ArgumentParser( #Opretter en argumentparser til kommandolinjeargumenter
        description="Sniff 802.11 frames and print RSSI (RTL8187 / Raspberry Pi)"
    )
    parser.add_argument("-i", "--interface", default="wlan1",
                        help="Monitor-mode interface (default: wlan1)") #Argument for Wi-Fi interface
    parser.add_argument("-c", "--channel", type=int, default=None,
                        help="Lock to a specific channel (1-13). Highly recommended!") #Argument for Wi-Fi channel
    parser.add_argument("--mac", default=None,
                        help="Only show frames involving this MAC address") #Argument for MAC-adressefilter
    parser.add_argument("--offset", type=int, default=RTL8187_OFFSET,
                        help=f"RTL8187 RSSI correction offset (default: {RTL8187_OFFSET})") #Argument for RTL8187 RSSI korrektions-offset
    parser.add_argument("--window", type=int, default=ROLLING_WINDOW,
                        help=f"Rolling average window size (default: {ROLLING_WINDOW})") #Argument for rolling average vinduets størrelse
    parser.add_argument("--beacons-only", action="store_true",                           #Den er også et input, så dette argument er irrelevant
                        help="Only display Beacon and Probe Response frames") #Argument for kun at vise Beacon og ProbeResponse pakker
    args = parser.parse_args() #Parser alle argumenter fra kommandolinjen

    signal.signal(signal.SIGINT, handle_sigint) #Registrerer signalhåndtering for Ctrl+C (SIGINT)

    if args.channel: #Hvis et channel-argument er angivet, låses interfacet til det pågældende channel
        print(f"[*] Locking to channel {args.channel}")
        set_channel(args.interface, args.channel)

    if args.mac: #Udskriver aktivt MAC-filter hvis angivet
        print(f"[*] MAC filter active: {args.mac}")

    print(f"[*] RTL8187 RSSI offset: +{args.offset} dBm")
    print(f"[*] Rolling average window: {args.window} packets")

    bpf_filter = ( #Sætter et BPF-filter hvis --beacons-only er aktivt, ellers filtreres der ikke på pakketype
        "type mgt subtype beacon or type mgt subtype probe-resp"
        if args.beacons_only else None
    )

    handler = make_packet_handler( #Opretter packet_handler-funktionen med de givne argumenter
        mac_filter=args.mac if args.mac else None,
        udp_sock=sock,
        target_address=target_address
        )

    print(f"[*] Sniffing on {args.interface} — press Ctrl+C to stop\n")
    print(f"{'Timestamp':<16} {'Type':<8}   {'Address':<20}   {'SSID/DST':<32}   {'RSSI':<12} {'Avg RSSI'}")
    print("-" * 110)

    while not stop_event.is_set(): #Kører sniffing-loopet indtil stop_event sættes (Ctrl+C)
        try:
            sniff( #Starter sniffing-processen for at indsamle Wi-Fi-pakker
                iface=args.interface,        #Wi-Fi interface der skal sniffes på
                prn=handler,                 #Funktion der kaldes for hver modtaget pakke
                filter=bpf_filter,           #BPF-filter der begrænser hvilke pakker der fanges
                store=False,                 #Pakker gemmes ikke i hukommelsen
                stop_filter=stop_filter,     #Funktion der afgør hvornår sniffing skal stoppe
                timeout=1,                   #Sniffing køres i 1 sekund ad gangen så stop_event tjekkes jævnligt
            )
        except OSError as e:
            if stop_event.is_set(): #Hvis stop_event er sat, afsluttes loopet pænt
                break
            if "100" in str(e) or "Network is down" in str(e): #Hvis interfacet er gået ned, forsøges det genstartet
                if not bring_interface_up(args.interface):
                    print("[!] Could not recover interface. Exiting.")
                    break
                if args.channel: #Låser igen til det ønskede channel efter genstart
                    set_channel(args.interface, args.channel)
            else:
                print(f"[!] Unexpected OSError: {e}") #Uventet fejl der ikke kan håndteres
                break

    print("[*] Exited cleanly.")


if __name__ == "__main__":
    main()