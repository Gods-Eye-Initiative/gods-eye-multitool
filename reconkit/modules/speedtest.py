"""Test di velocita' (download) e latenza verso endpoint pubblici, senza dipendenze esterne."""
import socket
import time
import urllib.request

# File di test di dimensione nota, ospitati da CDN pubbliche affidabili.
DOWNLOAD_URLS = [
    ("Cloudflare (10MB)", "https://speed.cloudflare.com/__down?bytes=10000000"),
]
LATENCY_TARGETS = [
    ("Google DNS", "8.8.8.8", 53),
    ("Cloudflare DNS", "1.1.1.1", 53),
]


def measure_latency(host: str, port: int, attempts: int = 4, timeout: float = 2.0):
    times = []
    for _ in range(attempts):
        start = time.time()
        try:
            with socket.create_connection((host, port), timeout=timeout):
                times.append((time.time() - start) * 1000)
        except OSError:
            continue
    if not times:
        return None
    return {"min": round(min(times), 1), "avg": round(sum(times) / len(times), 1), "max": round(max(times), 1),
            "samples": len(times)}


def measure_download(url: str, timeout: float = 20.0, chunk_size: int = 65536):
    req = urllib.request.Request(url, headers={"User-Agent": "ReconKit/0.1"})
    start = time.time()
    total = 0
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
    elapsed = time.time() - start
    if elapsed <= 0:
        return None
    mbps = (total * 8 / 1_000_000) / elapsed
    return {"bytes": total, "seconds": round(elapsed, 2), "mbps": round(mbps, 2)}


def run(args):
    print("Test di latenza:")
    for name, host, port in LATENCY_TARGETS:
        res = measure_latency(host, port)
        if res:
            print(f"  {name:<16} min={res['min']}ms  media={res['avg']}ms  max={res['max']}ms  ({res['samples']} campioni)")
        else:
            print(f"  {name:<16} nessuna risposta")

    if args.latency_only:
        return

    print("\nTest di velocita' in download:")
    for name, url in DOWNLOAD_URLS:
        print(f"  {name} ...", end=" ", flush=True)
        try:
            res = measure_download(url)
        except OSError as e:
            print(f"errore di rete: {e}")
            continue
        if res:
            mb = res["bytes"] / 1_000_000
            print(f"{mb:.1f} MB in {res['seconds']}s -> {res['mbps']} Mbps")
        else:
            print("fallito")


def add_subparser(subparsers):
    p = subparsers.add_parser("speedtest", help="test di latenza e velocita' di download della connessione")
    p.add_argument("--latency-only", action="store_true", help="misura solo la latenza, salta il download")
    p.set_defaults(func=run)
    return p
