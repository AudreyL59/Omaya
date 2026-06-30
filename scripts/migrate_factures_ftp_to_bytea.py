"""
Migration one-shot : remplit la colonne `contenu` (bytea) de
`divers.pgt_commande_facture` pour les factures historiques creees
via WinDev (Fen_FactureFiche + Fen_EnvoieFTP) dont le fichier est
encore uniquement sur le serveur FTP interne.

Pre-WinDev pattern : `Repertoire = "factures/"+idCommande+"/"` +
`nom_fic` -> chemin FTP complet `<base>/factures/<id>/<nom_fic>`.

Apres migration : le contenu est en BDD bytea, sync via SymmetricDS
canal erp_blob -> dispo sur les 2 noeuds (interne + OVH).

Idempotent : ne touche QUE les lignes avec contenu IS NULL (et non
supprimees). Peut etre relance autant de fois que voulu, par
exemple apres une nouvelle synchro HFSQL qui aurait ajoute des
factures historiques manquantes.

Usage (SUR LE SERVEUR INTERNE qui a acces au FTP local) :
  .\\venv\\Scripts\\python.exe scripts\\migrate_factures_ftp_to_bytea.py [--dry-run] [--limit N] [--base PATH]

Options :
  --dry-run     n'ecrit rien en BDD, log seulement ce qui serait fait
  --limit N     limite a N factures (test progressif)
  --base PATH   prefixe FTP avant 'factures/...' (defaut : ''). Si le
                serveur FTP a un dossier racine genre /OMAYA, passe
                --base /OMAYA
"""

from __future__ import annotations

import argparse
import ftplib
import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2  # noqa: E402

from app.core.config import FTP_HOST, FTP_PASSWORD, FTP_USER  # noqa: E402
from app.core.database.pg import get_pg_connection  # noqa: E402


def _ftp_connect() -> ftplib.FTP:
    ftp = ftplib.FTP(timeout=30)
    ftp.encoding = "latin-1"
    ftp.connect(FTP_HOST, 21)
    ftp.login(FTP_USER, FTP_PASSWORD)
    return ftp


def _ftp_retr(ftp: ftplib.FTP, abs_path: str) -> bytes | None:
    """RETR un fichier absolu. Retourne None si non trouve."""
    try:
        # Decoupe en (dossier, nom) car CWD + RETR(nom) est plus fiable
        # que RETR avec chemin complet sur certains serveurs FTP.
        folder, name = abs_path.rsplit("/", 1)
        ftp.cwd(folder or "/")
        buf = io.BytesIO()
        ftp.retrbinary(f"RETR {name}", buf.write)
        return buf.getvalue()
    except ftplib.error_perm:
        return None
    except Exception as e:
        print(f"   FTP ERR : {e}")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0,
                    help="0 = tous (defaut)")
    ap.add_argument("--base", default="",
                    help="prefixe FTP (ex: /OMAYA). Defaut: vide.")
    args = ap.parse_args()

    base = (args.base or "").rstrip("/")
    print(f"[CONF] FTP_HOST={FTP_HOST} base={base!r}")

    db = get_pg_connection("divers")
    sql = """
        SELECT id_commande_facture, id_commande, nom_fic
          FROM divers.pgt_commande_facture
         WHERE contenu IS NULL
           AND nom_fic IS NOT NULL AND nom_fic <> ''
           AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
         ORDER BY id_commande_facture
    """
    if args.limit > 0:
        sql += f" LIMIT {int(args.limit)}"
    rows = db.query(sql) or []
    total = len(rows)
    print(f"[INFO] {total} facture(s) avec contenu=NULL a migrer")
    if total == 0:
        return 0

    ftp = _ftp_connect()
    print(f"[INFO] FTP connecte (encoding={ftp.encoding})")

    ok = 0; ko = 0; skipped = 0
    t0 = time.time()

    for i, r in enumerate(rows, 1):
        id_fac = int(r["id_commande_facture"])
        id_cmd = int(r["id_commande"])
        nom = r["nom_fic"]
        abs_path = f"{base}/factures/{id_cmd}/{nom}"

        print(f"[{i:5}/{total}] facture={id_fac} cmd={id_cmd} "
              f"path={abs_path}", end=" ", flush=True)

        try:
            content = _ftp_retr(ftp, abs_path)
        except Exception as e:
            # Connexion perdue ? On reconnecte une fois et on retente
            print(f"\n   [WARN] reconnect FTP ({e})")
            try:
                ftp.close()
            except Exception:
                pass
            ftp = _ftp_connect()
            content = _ftp_retr(ftp, abs_path)

        if content is None:
            print("KO (fichier FTP absent)")
            ko += 1
            continue
        if len(content) == 0:
            print("SKIP (vide)")
            skipped += 1
            continue

        if args.dry_run:
            print(f"OK [{len(content):,} octets] (dry-run, pas d'UPDATE)")
            ok += 1
        else:
            try:
                db.query(
                    """UPDATE divers.pgt_commande_facture
                          SET contenu = ?,
                              modif_date = NOW(),
                              modif_elem = COALESCE(NULLIF(modif_elem, ''), 'migr')
                        WHERE id_commande_facture = ?""",
                    (psycopg2.Binary(content), id_fac),
                )
                print(f"OK [{len(content):,} octets]")
                ok += 1
            except Exception as e:
                print(f"DB-KO : {e}")
                ko += 1

    try:
        ftp.quit()
    except Exception:
        pass

    elapsed = time.time() - t0
    print()
    print(f"=== Fini en {elapsed:.1f}s : OK={ok} KO={ko} SKIP={skipped} ===")
    if args.dry_run:
        print("(dry-run : aucune ecriture en BDD effectuee)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
