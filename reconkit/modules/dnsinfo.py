"""Client DNS minimale (solo libreria standard) per i record comuni."""
import random
import socket
import struct

RTYPES = {"A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "MX": 15, "TXT": 16, "AAAA": 28}
RTYPES_REV = {v: k for k, v in RTYPES.items()}


def _encode_name(name: str) -> bytes:
    out = b""
    for label in name.rstrip(".").split("."):
        out += bytes([len(label)]) + label.encode()
    return out + b"\x00"


def _decode_name(data: bytes, offset: int):
    """Decodifica un nome gestendo la compressione a puntatori. Ritorna (nome, nuovo_offset)."""
    labels = []
    jumped = False
    start_offset = offset
    while True:
        length = data[offset]
        if length == 0:
            offset += 1
            break
        if (length & 0xC0) == 0xC0:
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if not jumped:
                start_offset = offset + 2
            offset = pointer
            jumped = True
            continue
        offset += 1
        labels.append(data[offset:offset + length].decode("utf-8", "replace"))
        offset += length
    end = start_offset if jumped else offset
    return ".".join(labels), end


def query(name: str, rtype: str = "A", server: str = "8.8.8.8", timeout: float = 3.0, port: int = 53):
    qtype = RTYPES.get(rtype.upper())
    if qtype is None:
        raise ValueError(f"Tipo di record non supportato: {rtype}")

    tid = random.randint(0, 0xFFFF)
    header = struct.pack(">HHHHHH", tid, 0x0100, 1, 0, 0, 0)
    question = _encode_name(name) + struct.pack(">HH", qtype, 1)
    packet = header + question

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(packet, (server, port))
        data, _ = s.recvfrom(4096)
    finally:
        s.close()

    _, flags, qdcount, ancount, _, _ = struct.unpack(">HHHHHH", data[:12])
    rcode = flags & 0x000F
    offset = 12
    for _ in range(qdcount):
        _, offset = _decode_name(data, offset)
        offset += 4  # qtype + qclass

    records = []
    for _ in range(ancount):
        _, offset = _decode_name(data, offset)
        rtype_val, _, ttl, rdlength = struct.unpack(">HHIH", data[offset:offset + 10])
        offset += 10
        rdata_raw = data[offset:offset + rdlength]
        type_name = RTYPES_REV.get(rtype_val, str(rtype_val))

        if type_name == "A":
            value = socket.inet_ntoa(rdata_raw)
        elif type_name == "AAAA":
            value = socket.inet_ntop(socket.AF_INET6, rdata_raw)
        elif type_name in ("NS", "CNAME"):
            value, _ = _decode_name(data, offset)
        elif type_name == "MX":
            pref = struct.unpack(">H", rdata_raw[:2])[0]
            exch, _ = _decode_name(data, offset + 2)
            value = f"{pref} {exch}"
        elif type_name == "TXT":
            parts = []
            pos = 0
            while pos < len(rdata_raw):
                ln = rdata_raw[pos]
                parts.append(rdata_raw[pos + 1:pos + 1 + ln].decode("utf-8", "replace"))
                pos += 1 + ln
            value = " ".join(parts)
        elif type_name == "SOA":
            mname, off2 = _decode_name(data, offset)
            rname, off2 = _decode_name(data, off2)
            value = f"{mname} {rname}"
        else:
            value = rdata_raw.hex()

        records.append({"type": type_name, "ttl": ttl, "value": value})
        offset += rdlength

    return {"rcode": rcode, "records": records}


RCODES = {0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN", 5: "REFUSED"}


def run(args):
    types = [t.strip().upper() for t in args.type.split(",")] if args.type != "all" else list(RTYPES.keys())
    all_records = []
    for t in types:
        try:
            result = query(args.name, t, server=args.server)
        except ValueError as e:
            print(f"Errore: {e}")
            continue
        except OSError as e:
            print(f"Errore di rete interrogando {args.server}: {e}")
            continue
        rcode_name = RCODES.get(result["rcode"], str(result["rcode"]))
        if not result["records"]:
            print(f"{t:6} nessun record ({rcode_name})")
        for r in result["records"]:
            print(f"{r['type']:6} ttl={r['ttl']:<7} {r['value']}")
            all_records.append(r)
    return all_records


def add_subparser(subparsers):
    p = subparsers.add_parser("dns", help="interrogazione record DNS (A, AAAA, MX, NS, TXT, SOA)")
    p.add_argument("name", help="dominio da interrogare")
    p.add_argument("-T", "--type", default="A,AAAA,MX,NS,TXT",
                   help="tipi separati da virgola, o 'all' (default: A,AAAA,MX,NS,TXT)")
    p.add_argument("-s", "--server", default="8.8.8.8", help="resolver DNS da interrogare (default 8.8.8.8)")
    p.set_defaults(func=run)
    return p
