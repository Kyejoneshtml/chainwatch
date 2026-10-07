#!/usr/bin/env python3
"""Replace every real Bitcoin address in design assets with an obviously
fake placeholder of the same type prefix and length.

Why: design/design-system/ is an export from Claude Design, whose source is
not in this repository. The export shipped with five live mainnet addresses,
displayed beside fraud-alert wording (docs/16-security-posture.md section C).
Any re-export reinstates whatever the source contains, so after every
re-export: run this, then tools/check_no_addresses.py, before committing.

Placeholders keep the original length and leading character(s), so layout
and middle-ellipsis truncation (AddressLabel shows the first 8 and last 6)
behave exactly as before, and both visible ends read as fake:
    bc1qfakeaddressnotrealjustforexamplefake01   (42-char bech32 shape)
    1FakeAddrNotRealIllustrationFake03           (34-char base58 shape)
Each contains characters outside its own alphabet ('o'/'j' for bech32,
'l'/'I' for base58), so it can never be a valid address, whatever it is
later edited to.

Numbering follows first appearance across the files given, so the same real
address maps to the same placeholder everywhere in one run. No mapping is
stored: storing one would mean committing the real addresses.

Scans plain text and embedded base64 payloads (gzip or plain), rewriting
both in place.

Usage: tools/scrub_design_addresses.py [paths...]   (default: design/)
"""
import base64
import gzip
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_no_addresses as chk  # noqa: E402

BECH32_MIDDLE = "addressnotrealjustforexample"
BASE58_MIDDLE = "rNotRealIllustration"


def placeholder(real, n):
    tag = f"{n:02d}"
    if real.lower().startswith(("bc1", "tb1")):
        head, tail = real[:3].lower() + "qfake", "fake" + tag
        middle = BECH32_MIDDLE
    else:
        head, tail = real[0] + "FakeAdd", "Fake" + tag
        middle = BASE58_MIDDLE
    fill = len(real) - len(head) - len(tail)
    out = head + (middle * (fill // len(middle) + 1))[:fill] + tail
    assert len(out) == len(real)
    assert not chk.bech32_ok(out) and not chk.base58check_ok(out)
    return out


def main(argv):
    root = chk.repo_root()
    targets = argv or [os.path.join(root, "design")]
    files = []
    for t in targets:
        if os.path.isdir(t):
            listed = subprocess.run(
                ["git", "ls-files", "-z", t], capture_output=True, check=True, cwd=root
            ).stdout.split(b"\x00")
            files += [os.path.join(root, p.decode()) for p in listed if p]
        else:
            files.append(t)

    mapping = {}

    def fake(addr):
        if addr not in mapping:
            mapping[addr] = placeholder(addr, len(mapping) + 1)
        return mapping[addr]

    def replace_plain(text):
        hits = list(chk.addresses_in(text))
        for _, addr in hits:
            fake(addr)
        for addr in {a for _, a in hits}:
            text = text.replace(addr, mapping[addr])
        return text

    changed = []
    for path in sorted(files):
        with open(path, "rb") as f:
            data = f.read()
        if chk.is_binary(data):
            continue
        text = data.decode("utf-8")
        new = replace_plain(text)
        for _, b64, decoded, was_gzip in list(chk.decoded_blobs(new)):
            scrubbed = replace_plain(decoded)
            if scrubbed == decoded:
                continue
            raw = scrubbed.encode("utf-8")
            if was_gzip:
                raw = gzip.compress(raw, mtime=0)
            new = new.replace(b64, base64.b64encode(raw).decode("ascii"), 1)
        if new != text:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new)
            changed.append(os.path.relpath(path, root))

    for path in changed:
        print(f"scrubbed {path}")
    print(f"{len(mapping)} distinct address(es) replaced in {len(changed)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
