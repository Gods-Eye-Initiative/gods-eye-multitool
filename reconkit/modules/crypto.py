"""
Cifratura/decifratura testo con AES-256 in modalita' CCM (la stessa modalita'
usata da CCMP/WPA2): un'unica chiave scelta dall'utente deriva sia la cifratura
che l'autenticazione, quindi un testo manomesso o una chiave sbagliata vengono
rilevati e il decrypt fallisce invece di restituire dati corrotti in silenzio.

Formato del blob prodotto (prima di base64):
  MAGIC(4) | VERSION(1) | SALT(16) | NONCE(13) | CIPHERTEXT+TAG(len rimanente)
"""
import base64
import getpass
import os
import secrets
import string
import sys

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESCCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC = b"CPK1"
VERSION = 1
SALT_LEN = 16
NONCE_LEN = 13
KEY_LEN = 32  # AES-256
PBKDF2_ITERATIONS = 390_000
ENV_VAR = "RECONKIT_KEY"


class DecryptionError(Exception):
    """Chiave errata o testo cifrato manomesso/corrotto."""


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=KEY_LEN, salt=salt, iterations=PBKDF2_ITERATIONS)
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_text(plaintext: str, passphrase: str) -> str:
    """Ritorna il testo cifrato come stringa base64 (sicura da incollare ovunque)."""
    if not passphrase:
        raise ValueError("La chiave non puo' essere vuota")
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    key = _derive_key(passphrase, salt)

    aesccm = AESCCM(key, tag_length=16)
    ciphertext = aesccm.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)

    blob = MAGIC + bytes([VERSION]) + salt + nonce + ciphertext
    return base64.urlsafe_b64encode(blob).decode("ascii")


def decrypt_text(token: str, passphrase: str) -> str:
    """Ritorna il testo in chiaro. Solleva DecryptionError se la chiave e' sbagliata
    o il testo cifrato e' stato alterato."""
    if not passphrase:
        raise ValueError("La chiave non puo' essere vuota")
    try:
        blob = base64.urlsafe_b64decode(token.strip().encode("ascii"))
    except Exception as e:
        raise DecryptionError(f"Testo cifrato non valido (base64 malformato): {e}")

    header_len = len(MAGIC) + 1 + SALT_LEN + NONCE_LEN
    if len(blob) < header_len:
        raise DecryptionError("Testo cifrato troppo corto o malformato")
    if blob[:4] != MAGIC:
        raise DecryptionError("Testo cifrato non riconosciuto (magic bytes mancanti)")

    version = blob[4]
    if version != VERSION:
        raise DecryptionError(f"Versione del formato non supportata: {version}")

    offset = 5
    salt = blob[offset:offset + SALT_LEN]
    offset += SALT_LEN
    nonce = blob[offset:offset + NONCE_LEN]
    offset += NONCE_LEN
    ciphertext = blob[offset:]

    key = _derive_key(passphrase, salt)
    aesccm = AESCCM(key, tag_length=16)
    try:
        plaintext = aesccm.decrypt(nonce, ciphertext, associated_data=None)
    except Exception:
        raise DecryptionError("Chiave errata, oppure il testo cifrato e' stato alterato o corrotto")
    return plaintext.decode("utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _get_key(args) -> str:
    if args.key:
        print("Attenzione: passare la chiave con -k la rende visibile nella cronologia della shell.",
              file=sys.stderr)
        return args.key
    env_key = os.environ.get(ENV_VAR)
    if env_key:
        return env_key
    key = getpass.getpass("Chiave: ")
    if getattr(args, "confirm", False):
        key2 = getpass.getpass("Conferma chiave: ")
        if key != key2:
            print("Errore: le due chiavi non coincidono.", file=sys.stderr)
            sys.exit(2)
    return key


def _read_input(args) -> str:
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            return f.read()
    if args.text is not None:
        return args.text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Errore: fornisci il testo come argomento, con -i FILE, oppure via stdin.", file=sys.stderr)
    sys.exit(2)


def _write_output(args, text: str):
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Scritto in {args.output}")
    else:
        print(text)


def run_encrypt(args):
    plaintext = _read_input(args)
    key = _get_key(args)
    token = encrypt_text(plaintext, key)
    _write_output(args, token)


def run_decrypt(args):
    token = _read_input(args)
    key = _get_key(args)
    try:
        plaintext = decrypt_text(token, key)
    except DecryptionError as e:
        print(f"Errore: {e}", file=sys.stderr)
        sys.exit(1)
    _write_output(args, plaintext)


def run_genkey(args):
    alphabet = string.ascii_letters + string.digits + "-_!@#%&*"
    key = "".join(secrets.choice(alphabet) for _ in range(args.length))
    print(key)


def _add_io_args(p):
    p.add_argument("text", nargs="?", default=None, help="testo da elaborare (in alternativa: -i o stdin)")
    p.add_argument("-i", "--input", metavar="FILE", help="leggi il testo da file invece che dall'argomento")
    p.add_argument("-o", "--output", metavar="FILE", help="scrivi il risultato su file invece che a schermo")
    p.add_argument("-k", "--key", help="chiave in chiaro (sconsigliato: resta nella cronologia della shell)")


def add_subparser(subparsers):
    enc = subparsers.add_parser("encrypt", help="cifra un testo con AES-256-CCM e una chiave personale")
    _add_io_args(enc)
    enc.add_argument("--confirm", action="store_true", help="chiedi la chiave due volte per evitare refusi")
    enc.set_defaults(func=run_encrypt)

    dec = subparsers.add_parser("decrypt", help="decifra un testo cifrato con 'encrypt'")
    _add_io_args(dec)
    dec.set_defaults(func=run_decrypt)

    gen = subparsers.add_parser("genkey", help="genera una chiave casuale robusta per encrypt/decrypt")
    gen.add_argument("-l", "--length", type=int, default=24, help="lunghezza della chiave (default 24)")
    gen.set_defaults(func=run_genkey)

    return [enc, dec, gen]
