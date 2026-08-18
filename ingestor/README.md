# Ingestor

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then fill in real RPC credentials from bitcoin.conf
.venv/bin/python main.py
```

## Known constraint: Python version

This machine has only `/usr/bin/python3` (Apple's Command Line Tools Python, 3.9.6) — no Homebrew, pyenv, uv, or python.org install present. 3.9 reached end of life in October 2025.

The venv is built from this Python because there is nothing newer to pin it to. In practice this surfaces as a `NotOpenSSLWarning` from `urllib3` on every run (this system's `ssl` module is built against LibreSSL, which `urllib3` v2 doesn't recognise as new enough) — harmless for RPC calls over `127.0.0.1`, but worth knowing the source of rather than treating as unexplained noise.

If a newer Python becomes available on this machine, rebuild the venv against it instead:

```
rm -rf .venv
python3.12 -m venv .venv   # or whatever version is installed
.venv/bin/pip install -r requirements.txt
```
