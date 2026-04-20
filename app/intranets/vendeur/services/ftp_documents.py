"""
Service de listing des documents salarié via FTP.

Transposition de listerFichier() WinDev.
Les fiches de salaire sont stockées sur le FTP dans :
/OMAYA/gestionRH/{id_salarie}/Fiches_Salaires/
"""

import ftplib
from urllib.parse import quote
from app.core.config import FTP_HOST, FTP_USER, FTP_PASSWORD, DOCS_URL


def lister_fiches_salaire(id_salarie: int) -> list[dict]:
    """
    Liste les fichiers de fiches de salaire d'un salarié depuis le FTP.

    Retourne une liste de dicts : {nom, taille_mo, date}
    """
    rep_ftp = f"/OMAYA/gestionRH/{id_salarie}/Fiches_Salaires"
    fichiers = []

    try:
        ftp = ftplib.FTP(timeout=10)
        ftp.encoding = "latin-1"
        ftp.connect(FTP_HOST, 21)
        ftp.login(FTP_USER, FTP_PASSWORD)

        try:
            ftp.cwd(rep_ftp)
        except ftplib.error_perm:
            ftp.quit()
            return []

        # NLST pour la liste des noms + SIZE pour chaque fichier
        noms = ftp.nlst()
        for nom in noms:
            if nom in (".", ".."):
                continue
            taille = 0
            try:
                taille = ftp.size(nom) or 0
            except Exception:
                pass

            fichiers.append({
                "nom": nom,
                "taille_mo": round(taille / 1024 / 1024, 2),
                "date": "",
                "url": f"{DOCS_URL.rstrip('/')}/gestionRH/{id_salarie}/Fiches_Salaires/{quote(nom)}",
            })

        ftp.quit()
    except Exception:
        pass

    # Tri par nom décroissant (les plus récents en premier)
    fichiers.sort(key=lambda f: f["nom"], reverse=True)
    return fichiers
