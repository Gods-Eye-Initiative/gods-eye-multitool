"""Trova link rotti su una o piu' pagine di un sito (crawl limitato allo stesso dominio)."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
import urllib.request
import urllib.error


class _LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    self.links.append(value)


def _fetch_page(url: str, timeout: float = 10.0):
    req = urllib.request.Request(url, headers={"User-Agent": "ReconKit/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace"), resp.status


def _check_link(url: str, timeout: float = 8.0):
    req = urllib.request.Request(url, headers={"User-Agent": "ReconKit/0.1"}, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return url, resp.status
    except urllib.error.HTTPError as e:
        if e.code == 405:  # alcuni server non accettano HEAD: ritenta con GET
            try:
                req2 = urllib.request.Request(url, headers={"User-Agent": "ReconKit/0.1"})
                with urllib.request.urlopen(req2, timeout=timeout) as resp:
                    return url, resp.status
            except urllib.error.HTTPError as e2:
                return url, e2.code
            except OSError:
                return url, None
        return url, e.code
    except OSError:
        return url, None


def extract_links(page_url: str):
    html, _ = _fetch_page(page_url)
    parser = _LinkExtractor()
    parser.feed(html)
    resolved = set()
    for href in parser.links:
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        resolved.add(urljoin(page_url, href))
    return resolved


def crawl_and_check(start_url: str, same_domain_only: bool = True, max_pages: int = 20, threads: int = 20):
    domain = urlparse(start_url).netloc
    to_visit = {start_url}
    visited = set()
    all_links = set()

    while to_visit and len(visited) < max_pages:
        page = to_visit.pop()
        if page in visited:
            continue
        visited.add(page)
        try:
            page_links = extract_links(page)
        except (urllib.error.HTTPError, OSError):
            continue
        all_links |= page_links
        if same_domain_only:
            for link in page_links:
                if urlparse(link).netloc == domain and link not in visited:
                    to_visit.add(link)

    results = []
    with ThreadPoolExecutor(max_workers=threads) as pool:
        futures = [pool.submit(_check_link, link) for link in all_links]
        for f in as_completed(futures):
            results.append(f.result())

    return sorted(visited), sorted(results, key=lambda r: (r[1] is None, r[1] or 0))


def run(args):
    start = args.url
    if not start.startswith(("http://", "https://")):
        start = "https://" + start

    print(f"Scansione di {start} (max {args.max_pages} pagine, dominio {'ristretto' if not args.all_domains else 'non ristretto'}) ...\n")
    visited, results = crawl_and_check(
        start, same_domain_only=not args.all_domains, max_pages=args.max_pages, threads=args.threads
    )
    print(f"Pagine analizzate: {len(visited)}")
    print(f"Link unici trovati: {len(results)}\n")

    broken = [r for r in results if r[1] is None or r[1] >= 400]
    ok = [r for r in results if r not in broken]

    if broken:
        print(f"Link rotti o non raggiungibili ({len(broken)}):")
        for url, status in broken:
            print(f"  [{status if status else 'ERRORE'}] {url}")
    else:
        print("Nessun link rotto trovato.")

    print(f"\nLink funzionanti: {len(ok)}")
    return {"visited": visited, "broken": broken, "ok_count": len(ok)}


def add_subparser(subparsers):
    p = subparsers.add_parser("linkcheck", help="trova link rotti su un sito (crawl limitato allo stesso dominio)")
    p.add_argument("url", help="pagina di partenza, es. esempio.com")
    p.add_argument("-m", "--max-pages", type=int, default=20, help="numero massimo di pagine da visitare (default 20)")
    p.add_argument("-t", "--threads", type=int, default=20)
    p.add_argument("--all-domains", action="store_true", help="segui anche i link verso altri domini (solo per il controllo, non per il crawl)")
    p.set_defaults(func=run)
    return p
