"""Client WHOIS minimale via protocollo RFC 3912 (porta 43), con referral da IANA."""
import re
import socket

REFERRAL_RE = re.compile(
    r"(?:refer|whois|Registrar WHOIS Server)\s*:\s*(\S+)", re.IGNORECASE
)


def _raw_query(query: str, server: str, timeout: float = 6.0) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((server, 43))
        s.sendall((query + "\r\n").encode())
        chunks = []
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8", "replace")
    finally:
        s.close()


def _find_referral(text: str):
    m = REFERRAL_RE.search(text)
    return m.group(1).strip() if m else None


def lookup(domain: str, max_hops: int = 3):
    """Interroga whois.iana.org per il TLD, poi segue i referral fino al whois autoritativo."""
    domain = domain.strip().lower()
    tld = domain.rsplit(".", 1)[-1]

    server = "whois.iana.org"
    query = tld
    chain = []
    seen_servers = set()

    for _ in range(max_hops):
        if server in seen_servers:
            break
        seen_servers.add(server)
        try:
            text = _raw_query(query, server)
        except OSError as e:
            chain.append((server, f"[errore di connessione: {e}]"))
            break
        chain.append((server, text))
        next_server = _find_referral(text)
        if not next_server or next_server == server:
            break
        server = next_server
        query = domain  # dal secondo hop in poi si interroga sul dominio completo

    return chain


def run(args):
    chain = lookup(args.domain)
    for server, text in chain:
        print(f"\n--- Risposta da {server} ---")
        print(text.strip() if text.strip() else "(risposta vuota)")
    if not chain:
        print("Nessuna risposta ricevuta.")
    return chain


def add_subparser(subparsers):
    p = subparsers.add_parser("whois", help="lookup WHOIS di un dominio (segue i referral)")
    p.add_argument("domain", help="dominio da interrogare, es. esempio.com")
    p.set_defaults(func=run)
    return p
