"""Geolocalizzazione IP tramite ip-api.com (servizio pubblico gratuito)."""
import json
import socket
import urllib.request


def lookup(target: str, timeout: float = 8.0):
    try:
        ip = socket.gethostbyname(target)
    except socket.gaierror:
        raise ValueError(f"Impossibile risolvere: {target}")

    url = f"http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,isp,org,as,lat,lon,query"
    req = urllib.request.Request(url, headers={"User-Agent": "ReconKit/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8", "replace"))
    return data


def run(args):
    try:
        data = lookup(args.target)
    except (ValueError, OSError) as e:
        print(f"Errore: {e}")
        return None
    if data.get("status") != "success":
        print(f"Geolocalizzazione non disponibile: {data.get('message', 'errore sconosciuto')}")
        return data
    print(f"IP:        {data.get('query')}")
    print(f"Paese:     {data.get('country')}")
    print(f"Regione:   {data.get('regionName')}")
    print(f"Citta':    {data.get('city')}")
    print(f"ISP:       {data.get('isp')}")
    print(f"Org:       {data.get('org')}")
    print(f"AS:        {data.get('as')}")
    print(f"Coord:     {data.get('lat')}, {data.get('lon')}")
    return data


def add_subparser(subparsers):
    p = subparsers.add_parser("geoip", help="geolocalizzazione di un IP o hostname")
    p.add_argument("target", help="IP o hostname")
    p.set_defaults(func=run)
    return p
