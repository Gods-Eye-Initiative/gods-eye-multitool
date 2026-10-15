"""Shared command metadata and safe, non-interactive GUI dispatch."""
import argparse
import contextlib
import io
import secrets
import string

from .cli import build_parser
from .modules import crypto


PALETTE = {
    "background": "#10151c",
    "panel": "#19222d",
    "panel_alt": "#202c39",
    "text": "#e8eef4",
    "muted": "#9eacb9",
    "primary": "#a78bfa",
    "green": "#53d69a",
    "amber": "#f3b85d",
    "red": "#f17676",
}

TOOLS = [
    {
        "id": "portscan", "title": "Scansione porte", "group": "RETE",
        "description": "Verifica porte TCP o UDP raggiungibili su un host autorizzato.",
        "positionals": ("target",),
        "fields": [
            ("target", "Host o IP", "text", "esempio.com / 192.168.1.10", True),
            ("ports", "Porte", "text", "top, all o 22,80,8000-8100", False, "top"),
            ("threads", "Thread", "text", "200", False, "200"),
            ("timeout", "Timeout (s)", "text", "1.0", False, "1.0"),
            ("udp", "Scansione UDP (attiva)", "check", "", False, False),
            ("banners", "Rileva banner", "check", "", False, False),
            ("ping_only", "Solo rilevamento host", "check", "", False, False),
            ("no_ping", "Salta rilevamento host", "check", "", False, False),
        ],
        "options": [("ports", "-p"), ("threads", "-t"), ("timeout", "--timeout")],
        "flags": [("udp", "-u"), ("banners", "-b"), ("ping_only", "-P"), ("no_ping", "-Pn")],
        "active": True,
    },
    {
        "id": "dns", "title": "DNS", "group": "DOMINI",
        "description": "Interroga un resolver per i record DNS selezionati.",
        "positionals": ("name",),
        "fields": [
            ("name", "Dominio", "text", "esempio.com", True),
            ("type", "Tipi record", "text", "A,AAAA,MX,NS,TXT", False, "A,AAAA,MX,NS,TXT"),
            ("server", "Resolver", "text", "8.8.8.8", False, "8.8.8.8"),
        ],
        "options": [("type", "-T"), ("server", "-s")],
    },
    {
        "id": "whois", "title": "WHOIS", "group": "DOMINI",
        "description": "Recupera i dati di registrazione pubblici del dominio.",
        "positionals": ("domain",), "fields": [("domain", "Dominio", "text", "esempio.com", True)],
    },
    {
        "id": "http", "title": "Analisi HTTP", "group": "WEB",
        "description": "Controlla intestazioni, sicurezza HTTP e certificato TLS.",
        "positionals": ("url",),
        "fields": [
            ("url", "URL o dominio", "text", "https://esempio.com", True),
            ("no_tls", "Salta il controllo TLS", "check", "", False, False),
        ],
        "flags": [("no_tls", "--no-tls")],
    },
    {
        "id": "subdomains", "title": "Sottodomini", "group": "DOMINI",
        "description": "Cerca sottodomini nei certificati pubblici Certificate Transparency.",
        "positionals": ("domain",), "fields": [("domain", "Dominio principale", "text", "esempio.com", True)],
    },
    {
        "id": "geoip", "title": "GeoIP", "group": "RETE",
        "description": "Stima la posizione di un indirizzo IP o hostname.",
        "positionals": ("target",), "fields": [("target", "IP o hostname", "text", "8.8.8.8", True)],
    },
    {
        "id": "traceroute", "title": "Traceroute", "group": "RETE",
        "description": "Traccia il percorso IP via ICMP (privilegi elevati richiesti).",
        "positionals": ("target",),
        "fields": [
            ("target", "IP o hostname", "text", "esempio.com", True),
            ("max_hops", "Hop massimi", "text", "30", False, "30"),
            ("timeout", "Timeout per hop (s)", "text", "2.0", False, "2.0"),
        ],
        "options": [("max_hops", "-m"), ("timeout", "--timeout")],
        "android_unsupported": "Traceroute ICMP raw non è supportato in modo affidabile su Android.",
    },
    {
        "id": "lanscan", "title": "Dispositivi LAN", "group": "RETE",
        "description": "Rileva host sulla LAN locale. Esegue connessioni di sonda attive.",
        "positionals": ("subnet",),
        "fields": [
            ("subnet", "Subnet CIDR (opzionale)", "text", "192.168.1.0/24", False),
            ("threads", "Thread", "text", "100", False, "100"),
            ("no_vendor", "Salta ricerca vendor", "check", "", False, False),
        ],
        "options": [("threads", "-t")], "flags": [("no_vendor", "--no-vendor")],
        "active": True,
        "android_unsupported": "La scansione LAN dipende dalla tabella ARP e da utility di sistema non disponibili nell'app Android.",
    },
    {
        "id": "speedtest", "title": "Velocità e latenza", "group": "RETE",
        "description": "Misura la latenza e, facoltativamente, scarica un file di test da 10 MB.",
        "fields": [("latency_only", "Misura solo la latenza", "check", "", False, False)],
        "flags": [("latency_only", "--latency-only")],
    },
    {
        "id": "sslcheck", "title": "Verifica TLS", "group": "WEB",
        "description": "Rileva protocolli TLS e scadenza del certificato.",
        "positionals": ("hostname",),
        "fields": [
            ("hostname", "Hostname", "text", "esempio.com", True),
            ("port", "Porta", "text", "443", False, "443"),
        ],
        "options": [("port", "-p")],
    },
    {
        "id": "emailsec", "title": "Sicurezza email", "group": "DOMINI",
        "description": "Controlla i record SPF, DKIM comuni e DMARC del dominio.",
        "positionals": ("domain",),
        "fields": [
            ("domain", "Dominio", "text", "esempio.com", True),
            ("server", "Resolver", "text", "8.8.8.8", False, "8.8.8.8"),
        ],
        "options": [("server", "-s")],
    },
    {
        "id": "sitemap", "title": "Mappa del sito", "group": "WEB",
        "description": "Analizza robots.txt e sitemap.xml.",
        "positionals": ("target",), "fields": [("target", "Dominio o URL", "text", "esempio.com", True)],
    },
    {
        "id": "linkcheck", "title": "Controllo link", "group": "WEB",
        "description": "Esplora un numero limitato di pagine e verifica i collegamenti.",
        "positionals": ("url",),
        "fields": [
            ("url", "URL iniziale", "text", "https://esempio.com", True),
            ("max_pages", "Pagine massime", "text", "20", False, "20"),
            ("threads", "Thread", "text", "20", False, "20"),
            ("all_domains", "Controlla anche altri domini", "check", "", False, False),
        ],
        "options": [("max_pages", "-m"), ("threads", "-t")],
        "flags": [("all_domains", "--all-domains")],
    },
    {
        "id": "encrypt", "title": "Cifra testo", "group": "CRITTOGRAFIA",
        "description": "Cifra testo con AES-256-CCM. La chiave non viene salvata né mostrata.",
        "crypto": "encrypt",
        "fields": [
            ("text", "Testo da cifrare", "multiline", "", True),
            ("key", "Chiave personale", "password", "Non lasciare vuoto", True),
        ],
    },
    {
        "id": "decrypt", "title": "Decifra testo", "group": "CRITTOGRAFIA",
        "description": "Decifra un testo G.E.M. e autentica il risultato.",
        "crypto": "decrypt",
        "fields": [
            ("text", "Testo cifrato", "multiline", "", True),
            ("key", "Chiave personale", "password", "Non lasciare vuoto", True),
        ],
    },
    {
        "id": "genkey", "title": "Genera chiave", "group": "CRITTOGRAFIA",
        "description": "Genera una chiave casuale ad alta entropia da conservare in modo sicuro.",
        "crypto": "genkey",
        "fields": [("length", "Lunghezza", "text", "24", False, "24")],
    },
]

TOOL_BY_ID = {tool["id"]: tool for tool in TOOLS}


def build_argv(tool_id, values):
    """Convert GUI fields into argv and let the existing CLI validate them."""
    spec = TOOL_BY_ID[tool_id]
    argv = [tool_id]
    for name in spec.get("positionals", ()):
        value = str(values.get(name, "")).strip()
        if value:
            argv.append(value)
    for name, flag in spec.get("options", ()):
        value = str(values.get(name, "")).strip()
        if value:
            argv.extend((flag, value))
    for name, flag in spec.get("flags", ()):
        if values.get(name):
            argv.append(flag)
    return argv


class _OutputCapture(io.StringIO):
    def __init__(self, on_output=None):
        super().__init__()
        self.on_output = on_output

    def write(self, text):
        written = super().write(text)
        if text and self.on_output is not None:
            self.on_output(text)
        return written


def execute_tool(tool_id, values, on_output=None):
    """Run a ReconKit command without interactive stdin/getpass, return its output."""
    spec = TOOL_BY_ID[tool_id]
    crypto_action = spec.get("crypto")
    if crypto_action == "encrypt":
        return crypto.encrypt_text(values.get("text", ""), values.get("key", ""))
    if crypto_action == "decrypt":
        return crypto.decrypt_text(values.get("text", ""), values.get("key", ""))
    if crypto_action == "genkey":
        length = int(values.get("length", 24))
        if not 8 <= length <= 256:
            raise ValueError("La lunghezza della chiave deve essere tra 8 e 256.")
        alphabet = string.ascii_letters + string.digits + "-_!@#%&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    parser = build_parser()
    stdout, stderr = _OutputCapture(on_output), _OutputCapture(on_output)
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            args = parser.parse_args(build_argv(tool_id, values))
            args.func(args)
    except SystemExit as exc:
        details = (stderr.getvalue() or stdout.getvalue()).strip()
        raise ValueError(details or "Il comando è terminato con un errore.") from exc
    except Exception as exc:
        details = (stderr.getvalue() + stdout.getvalue()).strip()
        message = "{}{}".format(details + "\n" if details else "", str(exc))
        raise RuntimeError(message) from exc
    result = stdout.getvalue().strip()
    error_output = stderr.getvalue().strip()
    if error_output:
        result = "{}\n{}".format(result, error_output).strip()
    return result or "Operazione completata; il modulo non ha prodotto output."


def android_unsupported_reason(tool_id):
    return TOOL_BY_ID[tool_id].get("android_unsupported")
