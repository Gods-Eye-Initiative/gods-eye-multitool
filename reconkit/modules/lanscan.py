"""Scansione della LAN locale con lookup del vendor dalla tabella ARP di sistema."""
import ipaddress
import json
import platform
import re
import socket
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PROBE_PORTS = (80, 443, 22, 445, 3389, 135, 139, 62078)


def _local_subnet():
    """Deduce la subnet /24 locale dall'IP uscente di default."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    finally:
        s.close()
    net = ipaddress.ip_network(local_ip + "/24", strict=False)
    return str(net)


def _touch(host: str, timeout: float = 0.5):
    """Tenta una connessione breve per far comparire l'host nella tabella ARP."""
    for port in PROBE_PORTS:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return
        except OSError:
            continue


def _read_arp_table():
    """Legge la tabella ARP di sistema (Windows: 'arp -a', Linux/macOS: 'arp -a' o 'ip neigh')."""
    entries = {}
    mac_re = re.compile(r"(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}")
    ip_re = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

    commands = [["arp", "-a"]]
    if platform.system() == "Linux":
        commands.insert(0, ["ip", "neigh"])

    for cmd in commands:
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        for line in out.splitlines():
            ip_m = ip_re.search(line)
            mac_m = mac_re.search(line)
            if ip_m and mac_m:
                entries[ip_m.group(0)] = mac_m.group(0).replace("-", ":").upper()
        if entries:
            break
    return entries


def _vendor_lookup(mac: str, timeout: float = 4.0):
    url = f"https://api.macvendors.com/{mac}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ReconKit/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace").strip()
    except Exception:
        return None


def scan(subnet: str = None, threads: int = 100, lookup_vendor: bool = True):
    subnet = subnet or _local_subnet()
    net = ipaddress.ip_network(subnet, strict=False)
    hosts = [str(h) for h in net.hosts()]

    with ThreadPoolExecutor(max_workers=threads) as pool:
        list(pool.map(_touch, hosts))

    arp_table = _read_arp_table()
    results = []
    for ip in hosts:
        mac = arp_table.get(ip)
        if not mac:
            continue
        try:
            hostname = socket.gethostbyaddr(ip)[0]
        except (socket.herror, socket.gaierror):
            hostname = ""
        vendor = _vendor_lookup(mac) if lookup_vendor else None
        results.append({"ip": ip, "mac": mac, "hostname": hostname, "vendor": vendor or ""})

    results.sort(key=lambda r: tuple(int(p) for p in r["ip"].split(".")))
    return subnet, results


def run(args):
    print(f"Scansione LAN su {args.subnet or '(subnet rilevata automaticamente)'} ...")
    subnet, results = scan(args.subnet, threads=args.threads, lookup_vendor=not args.no_vendor)
    print(f"Subnet: {subnet}\n")
    if not results:
        print("Nessun dispositivo trovato nella tabella ARP (prova ad aumentare i tempi o verifica i permessi).")
        return []
    print(f"{'IP':<16}{'MAC':<19}{'HOSTNAME':<28}VENDOR")
    for r in results:
        print(f"{r['ip']:<16}{r['mac']:<19}{r['hostname'][:26]:<28}{r['vendor']}")
    print(f"\nTotale dispositivi trovati: {len(results)}")
    return results


def add_subparser(subparsers):
    p = subparsers.add_parser("lanscan", help="scansione dispositivi sulla LAN locale con MAC vendor lookup")
    p.add_argument("subnet", nargs="?", default=None, help="subnet CIDR (default: rilevata automaticamente, es. 192.168.1.0/24)")
    p.add_argument("-t", "--threads", type=int, default=100)
    p.add_argument("--no-vendor", action="store_true", help="salta il lookup del vendor (nessuna richiesta di rete esterna)")
    p.set_defaults(func=run)
    return p
