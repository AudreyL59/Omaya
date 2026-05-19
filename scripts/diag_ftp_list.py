"""Diagnostic du listage FTP (formats supportes par le serveur).

Usage (SUR LE SERVEUR, venv) :
    .\\venv\\Scripts\\python.exe scripts\\diag_ftp_list.py [chemin]
defaut chemin = /OMAYA/DocTicket
"""

import ftplib
import sys

sys.path.insert(0, ".")

from app.core.config import FTP_HOST, FTP_PASSWORD, FTP_USER  # noqa: E402


def main(path: str):
    f = ftplib.FTP(timeout=20)
    f.encoding = "latin-1"
    f.connect(FTP_HOST, 21)
    f.login(FTP_USER, FTP_PASSWORD)

    print("=== FEAT ===")
    try:
        print(f.sendcmd("FEAT"))
    except Exception as e:
        print("FEAT err:", e)

    print(f"\n=== MLSD {path} ===")
    try:
        print(list(f.mlsd(path))[:5])
    except Exception as e:
        print("MLSD err:", repr(e))

    print(f"\n=== NLST {path} ===")
    try:
        print(f.nlst(path)[:10])
    except Exception as e:
        print("NLST err:", repr(e))

    print(f"\n=== LIST {path} (brut) ===")
    try:
        lines = []
        f.retrlines(f"LIST {path}", lines.append)
        for ln in lines[:10]:
            print(repr(ln))
    except Exception as e:
        print("LIST err:", repr(e))

    try:
        f.quit()
    except Exception:
        pass


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/OMAYA/DocTicket")
