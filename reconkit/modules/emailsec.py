"""Verifica SPF, DKIM (selettori comuni) e DMARC di un dominio."""
from . import dnsinfo

COMMON_DKIM_SELECTORS = [
    "default", "selector1", "selector2", "google", "k1", "s1", "s2",
    "mail", "dkim", "smtp", "mandrill", "mailgun", "sendgrid",
]


def check_spf(domain: str, server: str = "8.8.8.8"):
    try:
        result = dnsinfo.query(domain, "TXT", server=server)
    except OSError:
        return None
    for r in result["records"]:
        if r["value"].lower().startswith("v=spf1"):
            return r["value"]
    return None


def check_dmarc(domain: str, server: str = "8.8.8.8"):
    try:
        result = dnsinfo.query(f"_dmarc.{domain}", "TXT", server=server)
    except OSError:
        return None
    for r in result["records"]:
        if r["value"].lower().startswith("v=dmarc1"):
            return r["value"]
    return None


def check_dkim(domain: str, server: str = "8.8.8.8", selectors=None):
    found = {}
    for sel in (selectors or COMMON_DKIM_SELECTORS):
        name = f"{sel}._domainkey.{domain}"
        try:
            result = dnsinfo.query(name, "TXT", server=server)
        except OSError:
            continue
        for r in result["records"]:
            if "v=dkim1" in r["value"].lower() or "p=" in r["value"].lower():
                found[sel] = r["value"]
                break
    return found


def _parse_spf_mechanisms(spf: str):
    return [m for m in spf.split() if not m.lower().startswith("v=spf1")]


def run(args):
    domain = args.domain
    print(f"Verifica email security per {domain}\n")

    spf = check_spf(domain, args.server)
    print("SPF:")
    if spf:
        print(f"  {spf}")
        mechs = _parse_spf_mechanisms(spf)
        if not any(m in ("-all", "~all") for m in mechs):
            print("  Nota: nessun meccanismo '-all' o '~all' finale trovato (policy permissiva).")
    else:
        print("  Nessun record SPF trovato.")

    dmarc = check_dmarc(domain, args.server)
    print("\nDMARC:")
    if dmarc:
        print(f"  {dmarc}")
        if "p=none" in dmarc.lower():
            print("  Nota: policy 'p=none' - DMARC e' solo in modalita' di monitoraggio, non blocca nulla.")
    else:
        print("  Nessun record DMARC trovato (_dmarc." + domain + ").")

    print("\nDKIM (selettori comuni testati):")
    dkim = check_dkim(domain, args.server)
    if dkim:
        for sel, value in dkim.items():
            print(f"  [{sel}] {value[:100]}{'...' if len(value) > 100 else ''}")
    else:
        print("  Nessun selettore comune trovato. Il DKIM potrebbe comunque essere attivo con un")
        print("  selettore personalizzato: chiedi al provider email quale selettore usa.")

    return {"spf": spf, "dmarc": dmarc, "dkim": dkim}


def add_subparser(subparsers):
    p = subparsers.add_parser("emailsec", help="verifica record SPF, DKIM e DMARC di un dominio")
    p.add_argument("domain", help="dominio da verificare, es. esempio.com")
    p.add_argument("-s", "--server", default="8.8.8.8", help="resolver DNS da interrogare")
    p.set_defaults(func=run)
    return p
