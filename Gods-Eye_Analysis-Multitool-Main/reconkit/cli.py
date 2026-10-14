import argparse
import os

from . import __version__
from .banner import print_banner
from .modules import portscan, dnsinfo, whoislookup, httpinfo, subdomains, geoip, traceroute

MODULES = [portscan, dnsinfo, whoislookup, httpinfo, subdomains, geoip, traceroute]


def build_parser():
    p = argparse.ArgumentParser(
        prog="reconkit",
        description="Toolkit di OSINT e network recon passiva, cross-platform (Windows/Linux/macOS).",
        epilog="Esempi:\n"
               "  reconkit portscan 192.168.1.10 -p 1-1024 -b\n"
               "  reconkit dns esempio.com -T all\n"
               "  reconkit whois esempio.com\n"
               "  reconkit http esempio.com\n"
               "  reconkit subdomains esempio.com\n"
               "  reconkit geoip esempio.com\n"
               "  reconkit traceroute esempio.com\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--no-banner", action="store_true", help="non mostrare il banner di avvio")
    p.add_argument("-V", "--version", action="version", version=f"reconkit {__version__}")
    subparsers = p.add_subparsers(dest="command", required=True)
    for mod in MODULES:
        mod.add_subparser(subparsers)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if os.name == "nt":
        os.system("")  # abilita i colori ANSI nel terminale Windows
    if not args.no_banner:
        print_banner()
    try:
        args.func(args)
    except ValueError as e:
        print(f"Errore: {e}")
        return 2
    except KeyboardInterrupt:
        print("\nInterrotto dall'utente.")
        return 130
    return 0
