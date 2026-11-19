#!/usr/bin/env python3
"""
Privacy & Secret Guard for RRRemote repository.
Scans all tracked (or candidate) text files and fails if personal IPs, keys,
passwords, emails, or machine-specific secrets are present.
"""

from __future__ import annotations

import ipaddress
import re
import subprocess
import sys
from pathlib import Path

ALLOWED_EXAMPLE_IPS = {
    "0.0.0.0",
    "127.0.0.1",
    "1.2.3.4",
    "192.0.2.1",
    "198.51.100.1",
    "203.0.113.1",
    "203.0.113.10",
}

FORBIDDEN_PATTERNS = [
    ("Private key header", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b")),
    ("GCP project ID", re.compile(r"\bproject-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{3}\b")),
    ("Personal Gmail", re.compile(r"\b[a-zA-Z0-9._%+-]+@gmail\.com\b")),
    ("Hardcoded Ed25519 pubkey", re.compile(r"[A-Za-z0-9+/]{43}=")),
    ("Hardcoded admin password", re.compile(r"Admin Password Is:\s*\S+")),
]

IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
# Ignore lines with known version numbers like 1.5.3.0 or standard OIDs/schemas
VERSION_CONTEXT_RE = re.compile(r"(version|tag|release|v\d+\.\d+|rustdesk|ubuntu|debian|flutter)", re.IGNORECASE)


def is_forbidden_ip(ip_str: str) -> bool:
    if ip_str in ALLOWED_EXAMPLE_IPS:
        return False
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    if ip.is_loopback or ip.is_unspecified:
        return False
    # Block both real public IPs and personal LAN IPs (192.168.31.x, 10.14.x.x, etc.)
    # Allow RFC 5737 documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24)
    doc_nets = [
        ipaddress.ip_network("192.0.2.0/24"),
        ipaddress.ip_network("198.51.100.0/24"),
        ipaddress.ip_network("203.0.113.0/24"),
    ]
    if any(ip in net for net in doc_nets):
        return False
    return True


def list_files(repo_root: Path) -> list[Path]:
    res = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    files = []
    for line in res.stdout.splitlines():
        p = repo_root / line.strip()
        if p.is_file():
            files.append(p)
    return files


def scan_file(path: Path, repo_root: Path) -> list[str]:
    rel = path.relative_to(repo_root).as_posix()
    if rel == "scripts/privacy-check.py":
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for label, regex in FORBIDDEN_PATTERNS:
            if regex.search(line):
                findings.append(f"{rel}:{lineno}: [{label}] matched")

        for m in IPV4_RE.finditer(line):
            ip_str = m.group(0)
            if is_forbidden_ip(ip_str) and not VERSION_CONTEXT_RE.search(line):
                findings.append(f"{rel}:{lineno}: [IPv4 address] {ip_str}")
    return findings


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    all_findings: list[str] = []
    for p in list_files(repo_root):
        all_findings.extend(scan_file(p, repo_root))

    if all_findings:
        print("PRIVACY CHECK FAILED! Potential sensitive data detected:", file=sys.stderr)
        for item in all_findings:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print("Privacy check passed: 0 sensitive items found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
