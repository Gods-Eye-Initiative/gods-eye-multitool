"""Scansione porte TCP/UDP (stessa logica di PortLens)."""
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

TOP_PORTS = [
    20, 21, 22, 23, 25, 53, 67, 69, 80, 88, 110, 111, 119, 123, 135, 137, 138,
    139, 143, 161, 162, 389, 443, 445, 465, 514, 515, 587, 631, 636, 873, 993,
    995, 1080, 1433, 1521, 1723, 2049, 2181, 3000, 3128, 3306, 3389, 5000, 5060,
    5432, 5601, 5672, 5900, 5985, 6379, 6443, 8000, 8008, 8080, 8443, 8888,
    9000, 9090, 9200, 9300, 11211, 27017,
]
HTTP_PORTS = {80, 8000, 8008, 8080, 8888, 3000, 5000, 9000}
DISCOVERY_PORTS = (80, 443, 22, 445, 3389, 135)


def parse_ports(spec: str):
    spec = spec.strip().lower()
    if spec == "top":
        return sorted(set(TOP_PORTS))
    if spec == "all":
        return list(range(1, 65536))
    ports = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            lo, hi = int(a), int(b)
            if lo > hi:
                raise ValueError(f"Intervallo non valido: {part}")
            ports.update(range(lo, hi + 1))
        else:
            ports.add(int(part))
    if not ports or min(ports) < 1 or max(ports) > 65535:
        raise ValueError("Le porte devono essere comprese tra 1 e 65535")
    return sorted(ports)


def expand_targets(target: str):
    if "/" in target:
        net = ipaddress.ip_network(target, strict=False)
        if net.version != 4:
            raise ValueError("Per ora e' supportato solo IPv4")
        if net.num_addresses > 65536:
            raise ValueError("Rete troppo grande (max /16)")
        hosts = list(net.hosts()) or [net.network_address]
        return [str(h) for h in hosts]
    try:
        return [socket.gethostbyname(target)]
    except socket.gaierror:
        raise ValueError(f"Impossibile risolvere l'host: {target}")


def is_alive(host: str, timeout: float = 0.6) -> bool:
    for port in DISCOVERY_PORTS:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except ConnectionRefusedError:
            return True
        except OSError:
            continue
    return False


def service_name(port: int, proto: str = "tcp") -> str:
    try:
        return socket.getservbyport(port, proto)
    except OSError:
        return "unknown"


def grab_banner(sock: socket.socket, port: int) -> str:
    try:
        sock.settimeout(1.5)
        if port in HTTP_PORTS:
            sock.sendall(b"HEAD / HTTP/1.0\r\nHost: target\r\n\r\n")
        data = sock.recv(512)
        if not data.strip():
            return ""
        lines = data.decode("utf-8", "replace").splitlines()
        info = [lines[0].strip()]
        info += [l.strip() for l in lines[1:] if l.lower().startswith("server:")]
        return " | ".join(info)[:120]
    except OSError:
        return ""


def scan_tcp_port(host, port, timeout, grab):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        if s.connect_ex((host, port)) != 0:
            return None
        banner = grab_banner(s, port) if grab else ""
        return {"port": port, "proto": "tcp", "state": "open",
                "service": service_name(port), "banner": banner}
    except OSError:
        return None
    finally:
        s.close()


def scan_udp_port(host, port, timeout, grab=False):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(b"\x00", (host, port))
        try:
            s.recvfrom(1024)
            state = "open"
        except socket.timeout:
            state = "open|filtered"
        except ConnectionError:
            return None
        return {"port": port, "proto": "udp", "state": state,
                "service": service_name(port, "udp"), "banner": ""}
    except OSError:
        return None
    finally:
        s.close()


def scan_host(host, ports, udp=False, timeout=1.0, threads=200, grab=False):
    fn = scan_udp_port if udp else scan_tcp_port
    results = []
    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = [pool.submit(fn, host, p, timeout, grab) for p in ports]
        for f in as_completed(futures):
            r = f.result()
            if r:
                results.append(r)
    return sorted(results, key=lambda r: r["port"])


def run(args):
    ports = parse_ports(args.ports)
    hosts = expand_targets(args.target)
    report = []

    if len(hosts) > 1 and not args.no_ping:
        print(f"Host discovery su {len(hosts)} indirizzi...")
        with ThreadPoolExecutor(max_workers=100) as pool:
            alive = list(pool.map(is_alive, hosts))
        hosts = [h for h, ok in zip(hosts, alive) if ok]
        print(f"Host attivi: {len(hosts)}")

    if args.ping_only:
        for h in hosts:
            print(f"  {h} attivo")
            report.append({"host": h, "ports": []})
        return report

    for h in hosts:
        print(f"\nScansione di {h} ({len(ports)} porte, {'UDP' if args.udp else 'TCP'})...")
        res = scan_host(h, ports, args.udp, args.timeout, args.threads, args.banners)
        print(f"\nRisultati per {h}")
        if not res:
            print("  Nessuna porta aperta trovata.")
        else:
            print(f"  {'PORTA':<10}{'STATO':<15}{'SERVIZIO':<14}INFO")
            for r in res:
                print(f"  {str(r['port']) + '/' + r['proto']:<10}{r['state']:<15}{r['service']:<14}{r['banner']}")
        report.append({"host": h, "ports": res})
    return report


def add_subparser(subparsers):
    p = subparsers.add_parser("portscan", help="scansione porte TCP/UDP (stile nmap)")
    p.add_argument("target", help="IP, hostname o rete CIDR")
    p.add_argument("-p", "--ports", default="top", help="'top', 'all' o lista: 22,80,8000-8100")
    p.add_argument("-u", "--udp", action="store_true", help="scansione UDP")
    p.add_argument("-b", "--banners", action="store_true", help="banner grabbing")
    p.add_argument("-P", "--ping-only", action="store_true", help="solo host discovery")
    p.add_argument("-Pn", "--no-ping", action="store_true", help="salta l'host discovery")
    p.add_argument("-t", "--threads", type=int, default=200)
    p.add_argument("--timeout", type=float, default=1.0)
    p.set_defaults(func=run)
    return p
