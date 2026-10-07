#!/usr/bin/env python3
"""Fail if a real Bitcoin address appears in any tracked file.

Why: the repository is public. docs/16-security-posture.md section C and
docs/01-thesis.md's no-attribution position mean no address is ever named
in it -- docs, code, fixtures, design exports and prototypes alike. Address
strings live only in watchlist.local.md (gitignored); docs refer to them by
labels ("watch A", ...). This check exists because seven addresses reached
docs/ and five live ones reached design/ unnoticed (2026-10-07).

What it scans: the git index, not the working tree, so as a pre-commit hook
it checks exactly what is about to be committed. Every tracked text file
(a NUL byte in the first 8 KiB marks a file binary and skips it, as git
does). Inside each, it also decodes embedded base64 payloads -- gzip or
plain text -- because design-tool exports (e.g. the prototype HTML in
design/design-system/) carry their scripts that way, and five live
addresses sat inside such blobs where grep cannot see them.

What counts as an address: a whole token (not adjacent to other letters or
digits) that also passes its checksum. Regex alone would flag every hash
and base64 run in the repo; checksum validation leaves ~2^-32 (base58check)
or ~2^-30 (bech32) chance of a random token passing.
  - bech32 / bech32m with hrp bc (mainnet) or tb (testnet/signet)
  - base58check with version byte 0x00/0x05 (mainnet P2PKH/P2SH) or
    0x6f/0xc4 (testnet)
Regtest (bcrt1...) is deliberately not flagged: those addresses exist only
on a local throwaway chain and identify nobody.

Known blind spots, by design rather than oversight:
  - a truncated or mistyped address (`bc1qfake...fake01` style) fails its checksum
    and is not flagged, yet is still searchable. Reviewers treat truncated
    forms the same way.
  - an address glued to other alphanumerics with no separator is not a
    token and is not flagged.
  - images (screenshots, thumbnails) are not OCR'd.

Exceptions: tools/address-allowlist.txt, one address per line followed by a
mandatory reason. Only for strings that identify nobody: BIP-173/350 test
vectors and well-known public examples. Never a watchlist address, never an
address from a real incident, victim or suspect.

Usage: tools/check_no_addresses.py        (exit 0 clean, 1 if found)
Wired as .githooks/pre-commit (enable once per clone:
`git config core.hooksPath .githooks`) and named in ingestor/RUNBOOK.md.
"""
import base64
import binascii
import gzip
import hashlib
import os
import re
import subprocess
import sys

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
B32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BASE58_VERSIONS = {0x00, 0x05, 0x6F, 0xC4}
BECH32_HRPS = {"bc", "tb"}

_EDGE_L = r"(?<![A-Za-z0-9])"
_EDGE_R = r"(?![A-Za-z0-9])"
BECH32_RE = re.compile(_EDGE_L + r"(?:bc|tb|BC|TB)1[02-9ac-hj-np-zAC-HJ-NP-Z]{8,87}" + _EDGE_R)
BASE58_RE = re.compile(_EDGE_L + r"[123mn][1-9A-HJ-NP-Za-km-z]{25,34}" + _EDGE_R)
BASE64_RE = re.compile(r"[A-Za-z0-9+/]{64,}={0,2}")


def base58check_ok(s):
    if not s or any(c not in B58 for c in s):
        return False
    n = 0
    for c in s:
        n = n * 58 + B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    raw = b"\x00" * (len(s) - len(s.lstrip("1"))) + raw
    if len(raw) != 25:
        return False
    payload, checksum = raw[:-4], raw[-4:]
    if hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] != checksum:
        return False
    return payload[0] in BASE58_VERSIONS


def _polymod(values):
    gen = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for v in values:
        top = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ v
        for i in range(5):
            chk ^= gen[i] if (top >> i) & 1 else 0
    return chk


def bech32_ok(s):
    if s.lower() != s and s.upper() != s:
        return False  # mixed case is invalid by spec
    s = s.lower()
    hrp, _, data = s.rpartition("1")
    if hrp not in BECH32_HRPS or len(data) < 6 or any(c not in B32 for c in data):
        return False
    values = [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]
    values += [B32.index(c) for c in data]
    return _polymod(values) in (1, 0x2BC830A3)  # bech32, bech32m


def addresses_in(text):
    """Every checksum-valid address token in `text`, as (offset, string)."""
    for regex, ok in ((BECH32_RE, bech32_ok), (BASE58_RE, base58check_ok)):
        for m in regex.finditer(text):
            if ok(m.group()):
                yield m.start(), m.group()


def decoded_blobs(text):
    """Embedded base64 payloads that decode (after gunzip, if gzip) to
    UTF-8 text, as (offset, base64 string, decoded text, was_gzip).
    Fonts and images fail the UTF-8 decode and are skipped."""
    for m in BASE64_RE.finditer(text):
        try:
            raw = base64.b64decode(m.group(), validate=True)
        except (binascii.Error, ValueError):
            continue
        was_gzip = raw[:2] == b"\x1f\x8b"
        if was_gzip:
            try:
                raw = gzip.decompress(raw)
            except (OSError, EOFError):
                continue
        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        yield m.start(), m.group(), decoded, was_gzip


def is_binary(data):
    return b"\x00" in data[:8192]


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def scan_text(text):
    """(line, address, where) for every address in text and its blobs."""
    for off, addr in addresses_in(text):
        yield line_of(text, off), addr, ""
    for off, _, decoded, was_gzip in decoded_blobs(text):
        kind = "gzip+base64" if was_gzip else "base64"
        for _, addr in addresses_in(decoded):
            yield line_of(text, off), addr, f" (inside {kind} payload)"


def repo_root():
    return subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
    ).stdout.strip()


def load_allowlist(path):
    allowed = {}
    if not os.path.exists(path):
        return allowed
    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) < 2:
                sys.exit(f"{path}:{lineno}: allowlist entry has no reason: {parts[0]}")
            allowed[parts[0]] = parts[1]
    return allowed


def index_files(root):
    """(path, bytes) for every file in the git index, read from the index
    itself via one `git cat-file --batch` process."""
    ls = subprocess.run(
        ["git", "ls-files", "-s", "-z"], capture_output=True, check=True, cwd=root
    ).stdout
    entries = []
    for rec in ls.split(b"\x00"):
        if not rec:
            continue
        meta, path = rec.split(b"\t", 1)
        mode, sha, _stage = meta.split()
        if mode == b"160000":  # submodule
            continue
        entries.append((path.decode("utf-8", "replace"), sha))
    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=root
    )
    for path, sha in entries:
        proc.stdin.write(sha + b"\n")
        proc.stdin.flush()
        header = proc.stdout.readline().split()
        size = int(header[2])
        data = proc.stdout.read(size)
        proc.stdout.read(1)  # trailing newline
        yield path, data
    proc.stdin.close()
    proc.wait()


def main():
    root = repo_root()
    allowed = load_allowlist(os.path.join(root, "tools", "address-allowlist.txt"))
    found = set()
    for path, data in index_files(root):
        if is_binary(data):
            continue
        text = data.decode("utf-8", "replace")
        for lineno, addr, where in scan_text(text):
            if addr in allowed or addr.lower() in allowed:
                continue
            found.add((path, lineno, addr, where))

    if not found:
        return 0
    print("Address strings found in tracked files (repo is public; see "
          "docs/16-security-posture.md section C):", file=sys.stderr)
    for path, lineno, addr, where in sorted(found):
        print(f"  {path}:{lineno}: {addr}{where}", file=sys.stderr)
    print("Docs: replace each with a label defined in watchlist.local.md (gitignored). "
          "Design assets: run tools/scrub_design_addresses.py. Only test vectors and "
          "well-known public examples may go in tools/address-allowlist.txt, with a reason.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
