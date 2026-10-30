#!/usr/bin/env python3
"""Apply the Windows SDK pointer-width fixes needed by the pinned Firefox ESR tree."""

from pathlib import Path
import sys


def replace_once(path: Path, old: str, new: str, expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0 and new in text:
        return  # Already patched; keep the operation idempotent.
    if count != expected:
        raise SystemExit(
            f"{path}: expected {expected} occurrence(s) of {old!r}, found {count}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    print(f"Patched {path}: {old.strip()} -> {new.strip()}")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fix_windows_nspr.py FIREFOX_SOURCE_DIR")
    root = Path(sys.argv[1])
    w95sock = root / "nsprpub/pr/src/md/windows/w95sock.c"
    prsocket = root / "nsprpub/pr/src/io/prsocket.c"
    if not w95sock.is_file() or not prsocket.is_file():
        raise SystemExit(f"NSPR source files not found under {root}")

    # Winsock APIs use u_long / DWORD (32-bit unsigned long on Windows).
    # PRInt32 is a signed int and clang correctly rejects these pointer types.
    replace_once(w95sock, "  PRInt32 result;\n\n  if (ioctlsocket(fd->secret->md.osfd, FIONREAD, &result) < 0) {",
                 "  u_long result;\n\n  if (ioctlsocket(fd->secret->md.osfd, FIONREAD, &result) < 0) {")
    replace_once(w95sock, "  PRInt32 dwBytes;\n", "  DWORD dwBytes;\n")
    replace_once(prsocket, "        PRInt32 rvSent;\n", "        DWORD rvSent;\n")
    replace_once(prsocket, "    PRInt32 rvSent;\n", "    DWORD rvSent;\n")

    for path in (w95sock, prsocket):
        contents = path.read_text(encoding="utf-8")
        if "ioctlsocket(fd->secret->md.osfd, FIONREAD, &result)" in contents and "  PRInt32 result;" in contents:
            raise SystemExit(f"Unpatched FIONREAD result in {path}")
    print("Windows NSPR pointer-width fixes are present.")


if __name__ == "__main__":
    main()
