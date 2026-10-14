"""Analisi di robots.txt e sitemap.xml di un sito."""
import re
import urllib.request
import urllib.error
from urllib.parse import urljoin

LOC_RE = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.IGNORECASE)
SITEMAP_TAG_RE = re.compile(r"<sitemap>", re.IGNORECASE)


def _fetch(url: str, timeout: float = 10.0):
    req = urllib.request.Request(url, headers={"User-Agent": "ReconKit/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace"), resp.status


def _normalize_base(target: str) -> str:
    if not target.startswith(("http://", "https://")):
        target = "https://" + target
    if not target.endswith("/"):
        target += "/"
    return target


def analyze_robots(base_url: str):
    url = urljoin(base_url, "robots.txt")
    try:
        text, status = _fetch(url)
    except urllib.error.HTTPError as e:
        return {"url": url, "found": False, "status": e.code, "disallow": [], "sitemaps": []}
    except OSError as e:
        return {"url": url, "found": False, "error": str(e), "disallow": [], "sitemaps": []}

    disallow, sitemaps = [], []
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            if path:
                disallow.append(path)
        elif line.lower().startswith("sitemap:"):
            sitemaps.append(line.split(":", 1)[1].strip())
    return {"url": url, "found": True, "status": status, "disallow": disallow, "sitemaps": sitemaps}


def analyze_sitemap(sitemap_url: str, max_depth: int = 1):
    try:
        text, status = _fetch(sitemap_url)
    except (urllib.error.HTTPError, OSError) as e:
        return {"url": sitemap_url, "found": False, "error": str(e), "urls": [], "is_index": False}

    is_index = bool(SITEMAP_TAG_RE.search(text))
    locs = LOC_RE.findall(text)

    if is_index and max_depth > 0:
        all_urls = []
        for sub in locs[:20]:  # limite di sicurezza sui sitemap index molto grandi
            sub_result = analyze_sitemap(sub, max_depth=max_depth - 1)
            all_urls.extend(sub_result["urls"])
        return {"url": sitemap_url, "found": True, "is_index": True, "urls": all_urls}

    return {"url": sitemap_url, "found": True, "is_index": False, "urls": locs}


def run(args):
    base = _normalize_base(args.target)
    print(f"Analisi di {base}robots.txt ...\n")

    robots = analyze_robots(base)
    if not robots["found"]:
        print(f"  robots.txt non trovato o non accessibile ({robots.get('error', robots.get('status'))})")
    else:
        print(f"  Trovato ({robots['status']}). Regole Disallow: {len(robots['disallow'])}")
        for d in robots["disallow"][:30]:
            print(f"    Disallow: {d}")
        if len(robots["disallow"]) > 30:
            print(f"    ... e altre {len(robots['disallow']) - 30}")
        if robots["sitemaps"]:
            print(f"\n  Sitemap dichiarate in robots.txt: {len(robots['sitemaps'])}")
            for s in robots["sitemaps"]:
                print(f"    {s}")

    sitemap_urls = robots.get("sitemaps") or [urljoin(base, "sitemap.xml")]
    total_pages = 0
    for sm_url in sitemap_urls:
        print(f"\nAnalisi sitemap: {sm_url}")
        result = analyze_sitemap(sm_url)
        if not result["found"]:
            print(f"  Non trovata o non accessibile ({result.get('error')})")
            continue
        print(f"  {'Sitemap index' if result['is_index'] else 'Sitemap'} con {len(result['urls'])} URL")
        for u in result["urls"][:15]:
            print(f"    {u}")
        if len(result["urls"]) > 15:
            print(f"    ... e altre {len(result['urls']) - 15}")
        total_pages += len(result["urls"])

    print(f"\nTotale pagine indicizzate nelle sitemap: {total_pages}")
    return {"robots": robots, "total_pages": total_pages}


def add_subparser(subparsers):
    p = subparsers.add_parser("sitemap", help="analizza robots.txt e sitemap.xml di un sito")
    p.add_argument("target", help="dominio o URL, es. esempio.com")
    p.set_defaults(func=run)
    return p
