"""Traceroute via ICMP echo (richiede privilegi di amministratore/root, come il traceroute di sistema)."""
import os
import socket
import struct
import time


def _checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    total = sum((data[i] << 8) + data[i + 1] for i in range(0, len(data), 2))
    total = (total >> 16) + (total & 0xFFFF)
    total += total >> 16
    return ~total & 0xFFFF


def _build_icmp_echo(pid: int, seq: int) -> bytes:
    header = struct.pack("!BBHHH", 8, 0, 0, pid & 0xFFFF, seq)
    payload = b"reconkit-trace"
    chk = _checksum(header + payload)
    header = struct.pack("!BBHHH", 8, 0, chk, pid & 0xFFFF, seq)
    return header + payload


def trace(target: str, max_hops: int = 30, timeout: float = 2.0, probes_per_hop: int = 1):
    dest_ip = socket.gethostbyname(target)
    pid = os.getpid()
    results = []

    for ttl in range(1, max_hops + 1):
        try:
            send_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        except PermissionError:
            raise PermissionError(
                "Servono privilegi di amministratore/root per creare socket ICMP raw "
                "(su Linux: sudo; su Windows: terminale come Amministratore)."
            )
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
        recv_sock.settimeout(timeout)

        packet = _build_icmp_echo(pid, ttl)
        start = time.time()
        hop_addr = None
        try:
            send_sock.sendto(packet, (dest_ip, 0))
            try:
                data, addr = recv_sock.recvfrom(512)
                hop_addr = addr[0]
            except socket.timeout:
                hop_addr = None
        finally:
            send_sock.close()
            recv_sock.close()

        elapsed_ms = (time.time() - start) * 1000
        results.append({"ttl": ttl, "addr": hop_addr, "ms": round(elapsed_ms, 1) if hop_addr else None})
        if hop_addr == dest_ip:
            break
    return results, dest_ip


def run(args):
    try:
        results, dest_ip = trace(args.target, max_hops=args.max_hops, timeout=args.timeout)
    except PermissionError as e:
        print(f"Errore: {e}")
        return None
    except socket.gaierror:
        print(f"Impossibile risolvere l'host: {args.target}")
        return None

    print(f"Traceroute verso {args.target} ({dest_ip}), max {args.max_hops} hop\n")
    for r in results:
        if r["addr"]:
            print(f"  {r['ttl']:>2}  {r['addr']:<16}  {r['ms']} ms")
        else:
            print(f"  {r['ttl']:>2}  *  (nessuna risposta)")
    return results


def add_subparser(subparsers):
    p = subparsers.add_parser("traceroute", help="traceroute ICMP (richiede privilegi admin/root)")
    p.add_argument("target", help="IP o hostname")
    p.add_argument("-m", "--max-hops", type=int, default=30)
    p.add_argument("--timeout", type=float, default=2.0)
    p.set_defaults(func=run)
    return p
