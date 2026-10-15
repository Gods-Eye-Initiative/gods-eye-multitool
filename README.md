# G.E.M.

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
Oppure scarica `G.E.M.exe` dalla sezione **Releases** (nessun Python richiesto).

## Interfacce grafiche

La CLI resta disponibile senza installare Kivy. Su Windows, con Python 3.8 o successivo
installato insieme al componente Tcl/Tk, installa ReconKit e avvia la GUI desktop:

```powershell
py -m pip install .
reconkit-gui
# In alternativa, dalla cartella del progetto:
py -m reconkit.gui_tk
```

Su Linux/macOS la GUI Tkinter può essere avviata con `python -m reconkit.gui_tk`
(su alcune distribuzioni Linux occorre installare il pacchetto di sistema `python3-tk`).
I comandi sono eseguiti in un thread separato; l'output effettivo è mostrato nella
finestra. Le operazioni sincrone dei moduli esistenti non espongono un'interruzione
cooperativa, quindi la finestra resta utilizzabile ma non offre un arresto forzato.
Durante l'esecuzione la schermata mostra i log prodotti dal modulo; al termine li
sostituisce con il solo risultato finale. Le funzioni di cifratura usano direttamente
le API, senza prompt interattivi.

### Eseguibile Windows standalone

Per creare su Windows un eseguibile singolo senza finestra console, dalla cartella del
progetto esegui in PowerShell (serve Python 3.8 o successivo con Tcl/Tk):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install ".[windows]"
pyinstaller --clean --noconfirm --onefile --windowed --name GEM --paths . --add-data "reconkit\logo.png;reconkit" --add-data "reconkit\logo_sidebar.png;reconkit" packaging\windows_gui.py
```

The `--add-data` options include the original window icon and the high-quality,
pre-scaled sidebar logo in the one-file bundle.

L'extra `windows` installa PyInstaller solo per il packaging: non è una dipendenza
runtime della CLI. L'eseguibile prodotto è `dist\GEM.exe`. Smoke test da PowerShell:

```powershell
Test-Path .\dist\ReconKit.exe
Start-Process -FilePath .\dist\ReconKit.exe
Start-Sleep -Seconds 3
$app = Get-Process -Name GEM -ErrorAction SilentlyContinue |
  Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $app) { throw "La finestra di GEM non è stata avviata." }
Write-Output "GUI aperta: $($app.MainWindowTitle)"
```

L'eseguibile resta avviato dopo il test; chiudilo normalmente dalla finestra.

### APK Android (Buildozer)

La GUI Android è realizzata in Kivy e configurata in `buildozer.spec`. La compilazione APK
richiede Linux o WSL2 con Ubuntu (non è supportata direttamente da Windows). È preferibile
usare un normale utente Linux, non `root`, e lavorare su una copia del progetto nel filesystem
Linux di WSL (per esempio `~/src/ReconKit`, non `/mnt/c/...`).

Installa le dipendenze di sistema. Il pacchetto `venv` deve corrispondere alla versione
Python installata: per esempio, se `python3 --version` mostra Python 3.14, Ubuntu potrebbe
richiedere `python3.14-venv` invece di `python3-venv`.

```bash
sudo apt update
PYTHON_VERSION="$(python3 -c 'import sys; print("{}.{}".format(sys.version_info.major, sys.version_info.minor))')"
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip "python${PYTHON_VERSION}-venv" \
  build-essential autoconf libtool pkg-config zlib1g-dev libncurses-dev \
  libtinfo6 cmake libffi-dev libssl-dev
```

Dalla cartella del progetto crea un ambiente virtuale dedicato e installa Buildozer al suo
interno. Il controllo `command -v python` conferma che il virtualenv è attivo; non continuare
con l'installazione se la creazione o l'attivazione fallisce.

```bash
python3 -m venv .venv-android
source .venv-android/bin/activate
command -v python
python --version
python -m pip install --upgrade pip buildozer
command -v buildozer
buildozer --version
```

Se `apt update` riporta `Hash Sum mismatch`, gli indici e il mirror possono essere
temporaneamente non sincronizzati (o una cache/proxy sta servendo file vecchi). Non
disabilitare le verifiche hash/firma e non usare `trusted=yes`: riprova aggiornando gli
indici senza cache e con retry:

```bash
sudo apt-get clean
sudo apt-get update -o Acquire::Retries=5 -o Acquire::http::No-Cache=true
```

Esegui poi nuovamente `sudo apt install ...` solo se l'aggiornamento termina senza errori.
Se il mismatch persiste, attendi alcuni minuti e riprova; in alternativa controlla i mirror
configurati in `/etc/apt/sources.list` e `/etc/apt/sources.list.d/ubuntu.sources` e scegli
un mirror Ubuntu ufficiale coerente con la release della distribuzione. Il messaggio
`python3-pip has no installation candidate` dopo un `apt update` fallito è spesso dovuto agli
indici incompleti o obsoleti, non all'assenza del pacchetto: controlla `apt-cache policy
python3-pip` dopo aver risolto l'aggiornamento.

Per i prerequisiti aggiornati consulta la
[guida Buildozer](https://buildozer.readthedocs.io/). Crea l'APK di debug:

```bash
buildozer -v android debug
```

Se appare ancora `ensurepip is not available`, installa il pacchetto corrispondente alla
versione Python mostrata da `python3 --version` (per Python 3.14: `sudo apt install
python3.14-venv`), poi ripeti la creazione e l'attivazione dell'ambiente virtuale. Il messaggio
`python: command not found` prima dell'attivazione è normale su alcune installazioni Ubuntu:
usa `python3` per creare il virtualenv e `python` solo dopo averlo attivato. Se `buildozer`
non viene trovato, verifica che `.venv-android` sia attivo e che `python -m pip install
--upgrade pip buildozer` sia terminato senza errori; non lanciare la build con `sudo`.

Il primo build scarica SDK/NDK e può durare a lungo. L'APK di debug viene creato sotto
`bin/` (ad esempio `bin/reconkit-0.1.0-arm64-v8a-debug.apk`). Per installare e avviare
l'app collegata via USB puoi eseguire `buildozer android debug deploy run`, oppure copia
l'APK e installalo manualmente. L'app richiede il permesso Internet per i controlli
di rete. Il setup Kivy è facoltativo: per lo sviluppo locale è disponibile anche
`python -m pip install ".[android]"`, mentre non è necessario per CLI o Tkinter.

La UI Android rende non disponibili Traceroute (socket ICMP raw/privilegi elevati) e
Dispositivi LAN (tabella ARP e utility di sistema non presenti nell'app). La GUI segnala
esplicitamente queste limitazioni; le scansioni porte e LAN, dove disponibili, sono
attività attive e richiedono autorizzazione. Le altre funzioni di rete dipendono dalla
connettività e dalle restrizioni del dispositivo.

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
