"""Analisi header HTTP, security header e certificato TLS di un sito."""
import re
import socket
import ssl
import urllib.request
import urllib.error

SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
]
GENERATOR_RE = re.compile(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', re.IGNORECASE)


def fetch_headers(url: str, timeout: float = 8.0):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    req = urllib.request.Request(url, headers={"User-Agent": "ReconKit/0.1"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            headers = dict(resp.headers.items())
            status = resp.status
            body = resp.read(20000).decode("utf-8", "replace")
            final_url = resp.geturl()
    except urllib.error.HTTPError as e:
        headers = dict(e.headers.items()) if e.headers else {}
        status = e.code
        body = ""
        final_url = url
    return {"url": url, "final_url": final_url, "status": status, "headers": headers, "body": body}


def tls_cert_info(hostname: str, port: int = 443, timeout: float = 6.0):
    ctx = ssl.create_default_context()
    with socket.create_connection((hostname, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert()
            cipher = ssock.cipher()
    subject = dict(x[0] for x in cert.get("subject", []))
    issuer = dict(x[0] for x in cert.get("issuer", []))
    return {
        "subject_cn": subject.get("commonName", "?"),
        "issuer": issuer.get("organizationName", issuer.get("commonName", "?")),
        "not_before": cert.get("notBefore"),
        "not_after": cert.get("notAfter"),
        "san": [v for k, v in cert.get("subjectAltName", []) if k == "DNS"],
        "cipher": cipher[0] if cipher else "?",
    }


def run(args):
    target = args.url
    hostname = target.replace("https://", "").replace("http://", "").split("/")[0]

    print(f"Richiesta HTTP a {target} ...")
    info = fetch_headers(target)
    print(f"Stato: {info['status']}  (URL finale: {info['final_url']})")
    print("\nHeader di risposta:")
    for k, v in info["headers"].items():
        print(f"  {k}: {v}")

    headers_lower = {k.lower(): v for k, v in info["headers"].items()}

    print("\nSecurity header:")
    for h in SECURITY_HEADERS:
        value = headers_lower.get(h.lower())
        print(f"  [{'OK' if value else '--'}] {h}" + (f": {value}" if value else " (assente)"))

    gen = GENERATOR_RE.search(info["body"])
    server_hdr = headers_lower.get("server")
    powered_by = headers_lower.get("x-powered-by")
    if server_hdr or powered_by or gen:
        print("\nTecnologie rilevate (da header/meta):")
        if server_hdr:
            print(f"  Server: {server_hdr}")
        if powered_by:
            print(f"  X-Powered-By: {powered_by}")
        if gen:
            print(f"  Generator: {gen.group(1)}")

    if not args.no_tls:
        try:
            cert = tls_cert_info(hostname)
            print("\nCertificato TLS:")
            print(f"  Soggetto: {cert['subject_cn']}")
            print(f"  Emesso da: {cert['issuer']}")
            print(f"  Validita': {cert['not_before']}  ->  {cert['not_after']}")
            print(f"  SAN: {', '.join(cert['san']) if cert['san'] else '-'}")
            print(f"  Cifratura: {cert['cipher']}")
        except Exception as e:
            print(f"\nCertificato TLS: non disponibile ({e})")

    return info


def add_subparser(subparsers):
    p = subparsers.add_parser("http", help="header HTTP, security header e certificato TLS")
    p.add_argument("url", help="URL o dominio, es. esempio.com")
    p.add_argument("--no-tls", action="store_true", help="salta il controllo del certificato TLS")
    p.set_defaults(func=run)
    return p
