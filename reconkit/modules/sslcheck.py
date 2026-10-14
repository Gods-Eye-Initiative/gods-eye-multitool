"""Verifica approfondita TLS: protocolli supportati, scadenza certificato, cifrari."""
import datetime
import socket
import ssl

PROTOCOLS = [
    ("TLSv1.0", ssl.TLSVersion.TLSv1),
    ("TLSv1.1", ssl.TLSVersion.TLSv1_1),
    ("TLSv1.2", ssl.TLSVersion.TLSv1_2),
    ("TLSv1.3", ssl.TLSVersion.TLSv1_3),
]
DEPRECATED = {"TLSv1.0", "TLSv1.1"}


def _try_protocol(hostname: str, port: int, version, timeout: float):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        ctx.minimum_version = version
        ctx.maximum_version = version
    except ValueError:
        return None  # protocollo non supportato dalla libreria OpenSSL locale
    try:
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname):
                return True
    except (ssl.SSLError, OSError):
        return False


def check(hostname: str, port: int = 443, timeout: float = 6.0):
    results = {"protocols": {}, "cert": None}
    for name, version in PROTOCOLS:
        results["protocols"][name] = _try_protocol(hostname, port, version, timeout)

    ctx = ssl.create_default_context()
    with socket.create_connection((hostname, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert()
            cipher = ssock.cipher()

    not_after = datetime.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
    days_left = (not_after - datetime.datetime.utcnow()).days
    subject = dict(x[0] for x in cert.get("subject", []))
    issuer = dict(x[0] for x in cert.get("issuer", []))

    results["cert"] = {
        "subject_cn": subject.get("commonName", "?"),
        "issuer": issuer.get("organizationName", issuer.get("commonName", "?")),
        "not_after": cert.get("notAfter"),
        "days_left": days_left,
        "cipher": cipher[0] if cipher else "?",
        "tls_version": cipher[1] if cipher else "?",
    }
    return results


def run(args):
    hostname = args.hostname.replace("https://", "").replace("http://", "").split("/")[0]
    print(f"Verifica TLS di {hostname}:{args.port} ...\n")

    try:
        results = check(hostname, args.port)
    except OSError as e:
        print(f"Errore di connessione: {e}")
        return None

    print("Protocolli supportati:")
    for name, supported in results["protocols"].items():
        if supported is None:
            tag = "n/d (non supportato dalla libreria locale)"
        elif supported:
            tag = "ATTIVO" + ("  <-- deprecato, da disabilitare" if name in DEPRECATED else "")
        else:
            tag = "disattivo"
        print(f"  {name:<10} {tag}")

    cert = results["cert"]
    print("\nCertificato:")
    print(f"  Soggetto:        {cert['subject_cn']}")
    print(f"  Emesso da:       {cert['issuer']}")
    print(f"  Scadenza:        {cert['not_after']}  ({cert['days_left']} giorni rimanenti)")
    if cert["days_left"] < 0:
        print("  ATTENZIONE: il certificato e' scaduto.")
    elif cert["days_left"] < 15:
        print("  ATTENZIONE: il certificato scade a breve.")
    print(f"  Connessione attuale: {cert['tls_version']} con {cert['cipher']}")
    return results


def add_subparser(subparsers):
    p = subparsers.add_parser("sslcheck", help="verifica approfondita TLS: protocolli supportati e scadenza certificato")
    p.add_argument("hostname", help="dominio da verificare, es. esempio.com")
    p.add_argument("-p", "--port", type=int, default=443)
    p.set_defaults(func=run)
    return p
