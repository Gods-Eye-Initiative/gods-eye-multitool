# ReconKit

Toolkit di OSINT, network recon **passiva** e cifratura testo, cross-platform (Windows, Linux, macOS), scritto in Python. Tutti i moduli di recon usano solo la libreria standard; i soli comandi `encrypt`/`decrypt`/`genkey` richiedono la libreria `cryptography` (installata automaticamente da pip).

> **Uso responsabile:** usa questo strumento solo su domini/sistemi tuoi o per cui hai un'autorizzazione esplicita. ReconKit raccoglie solo informazioni pubbliche su infrastrutture (domini, IP, certificati); non include bruteforce, cracking o exploitation.

## Strumenti inclusi

| Comando       | Cosa fa |
|---------------|---------|
| `portscan`    | Scansione porte TCP/UDP, host discovery su reti CIDR, banner grabbing |
| `dns`         | Query record DNS: A, AAAA, MX, NS, TXT, SOA |
| `whois`       | Lookup WHOIS di un dominio, con referral automatico |
| `http`        | Header HTTP, security header, certificato TLS, tecnologie rilevate |
| `subdomains`  | Enumerazione passiva dei subdomain via Certificate Transparency (crt.sh) |
| `geoip`       | Geolocalizzazione di un IP o hostname |
| `traceroute`  | Traceroute ICMP (richiede privilegi admin/root) |
| `lanscan`     | Dispositivi sulla tua LAN locale, con MAC vendor lookup |
| `speedtest`   | Latenza e velocita' di download della tua connessione |
| `sslcheck`    | Protocolli TLS supportati e scadenza certificato |
| `emailsec`    | Verifica record SPF, DKIM (selettori comuni) e DMARC |
| `sitemap`     | Analisi di robots.txt e sitemap.xml |
| `linkcheck`   | Trova link rotti su un sito (crawl limitato allo stesso dominio) |
| `encrypt`     | Cifra un testo con AES-256-CCM e una chiave personale |
| `decrypt`     | Decifra un testo cifrato con `encrypt` |
| `genkey`      | Genera una chiave casuale robusta per `encrypt`/`decrypt` |

## Installazione

**Linux / macOS**
```bash
pipx install git+https://github.com/Gods-Eye-Initiative/gods-eye-multitool.git
# oppure
git clone https://github.com/Gods-Eye-Initiative/gods-eye-multitool.git && cd reconkit && pip install .
```

**Windows** (con Python installato)
```powershell
py -m pip install git+https://github.com/Gods-Eye-Initiative/gods-eye-multitool.git
```
Oppure scarica `reconkit.exe` dalla sezione **Releases** (nessun Python richiesto).

## Uso
```bash
reconkit portscan 192.168.1.10 -p 1-1024 -b
reconkit dns esempio.com -T all
reconkit whois esempio.com
reconkit http esempio.com
reconkit subdomains esempio.com
reconkit geoip esempio.com
reconkit traceroute esempio.com      # richiede sudo / terminale amministratore
reconkit lanscan                     # scansiona la tua LAN (subnet rilevata automaticamente)
reconkit speedtest
reconkit sslcheck esempio.com
reconkit emailsec esempio.com
reconkit sitemap esempio.com
reconkit linkcheck esempio.com

reconkit encrypt "messaggio segreto"   # chiede la chiave in modo nascosto
reconkit decrypt -i note.enc
reconkit genkey                         # genera una chiave robusta pronta all'uso
```
Senza installare: `python -m reconkit <comando> [opzioni]`.
Per l'elenco completo: `reconkit --help` o `reconkit <comando> --help`.

## Personalizzazione
Il banner di avvio si modifica in `reconkit/banner.py` (arte ASCII, tagline, autore). Si disattiva con `--no-banner`.

## Cifratura testo (`encrypt` / `decrypt` / `genkey`)
Usa **AES-256 in modalita' CCM** (la stessa di CCMP/WPA2) con una chiave scelta da te:
- La chiave passa per PBKDF2-HMAC-SHA256 (390.000 iterazioni) con salt casuale, per resistere al bruteforce.
- Cifra e autentica insieme: una chiave sbagliata o un testo manomesso fanno fallire `decrypt` con un errore, invece di restituire dati corrotti.
- L'output e' una stringa base64 sicura da incollare in chat, email o file.
- Non esiste un "recupero chiave": se la perdi, il testo e' irrecuperabile per design.
- La chiave si puo' passare con `-k CHIAVE` (sconsigliato: resta nella cronologia della shell), con la variabile d'ambiente `RECONKIT_KEY`, oppure verra' richiesta in modo nascosto a schermo.

## Limiti
- `whois` segue i referral standard ma alcuni registrar restituiscono dati parziali.
- `traceroute` richiede privilegi elevati (come il traceroute/tracert di sistema).
- `subdomains` dipende dalla disponibilita' di crt.sh ed e' limitato ai certificati pubblicamente loggati.
- Nessuno strumento qui effettua ricerche su persone (username, email, numeri di telefono): ReconKit copre solo infrastrutture di rete e domini.
- `lanscan` legge la tabella ARP di sistema dopo aver "toccato" gli host: trova solo dispositivi che rispondono a una connessione TCP su porte comuni, non e' una scansione ARP attiva via raw socket.
- `emailsec` testa solo una lista di selettori DKIM comuni: un selettore personalizzato non verra' trovato automaticamente.

## Licenza
MIT
