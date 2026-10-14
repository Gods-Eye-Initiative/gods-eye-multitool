"""Subdomain enumeration passiva via Certificate Transparency logs (crt.sh)."""
import json
import urllib.request
import urllib.parse


def find(domain: str, timeout: float = 15.0):
    url = "https://crt.sh/?q=%25." + urllib.parse.quote(domain) + "&output=json"
    req = urllib.request.Request(url, headers={"User-Agent": "ReconKit/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", "replace")
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError:
        entries = []

    names = set()
    for entry in entries:
        value = entry.get("name_value", "")
        for line in value.splitlines():
            line = line.strip().lower()
            if line and not line.startswith("*."):
                names.add(line)
            elif line.startswith("*."):
                names.add(line[2:])
    return sorted(names)


def run(args):
    print(f"Ricerca subdomain per {args.domain} su crt.sh (Certificate Transparency)...")
    try:
        names = find(args.domain)
    except OSError as e:
        print(f"Errore di rete: {e}")
        return []
    if not names:
        print("Nessun subdomain trovato.")
    for n in names:
        print(f"  {n}")
    print(f"\nTotale: {len(names)} subdomain unici trovati")
    return names


def add_subparser(subparsers):
    p = subparsers.add_parser("subdomains", help="enumerazione passiva subdomain via certificati TLS pubblici (crt.sh)")
    p.add_argument("domain", help="dominio principale, es. esempio.com")
    p.set_defaults(func=run)
    return p
