"""
Service Fen_ExportFicTR - Export CSV pour Commande de Titres Restaurant.

Cf. WinDev :
- 2 modes de recherche : par entite (societe + mois) ou par salarie
- Le tableau resultat est exporte en CSV avec 16 colonnes fixes
- Si MatriculeTR absent en base : genere auto Nom[0:2]_Prenom[0:2]_JJMMAAAA
  + UPDATE en base pour la prochaine fois
"""
import logging
import re
import unicodedata
from datetime import date
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.export_tr import (
    ExportCsvParams, ExportTRRow, RechercheParEntiteParams,
    RechercheParSalarieParams, RechercheResult,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _clean_id(v) -> str:
    if v is None:
        return ""
    try:
        n = int(v)
        return str(n) if n else ""
    except (TypeError, ValueError):
        return ""


def _iso_date(v) -> str:
    if v is None:
        return ""
    s = str(v)[:10]
    if s.startswith("1900") or s.startswith("0000") or s == "":
        return ""
    return s


def _premier_jour(mois_paiement: str) -> str:
    """'2026-07' -> '2026-07-01'."""
    return mois_paiement + "-01"


def _dernier_jour(mois_paiement: str) -> str:
    """'2026-07' -> '2026-07-31'."""
    y = int(mois_paiement[:4])
    m = int(mois_paiement[5:7])
    if m == 12:
        d0 = date(y + 1, 1, 1)
    else:
        d0 = date(y, m + 1, 1)
    from datetime import timedelta
    return (d0 - timedelta(days=1)).isoformat()


def _cap2(s: str) -> str:
    """'DUPONT' -> 'Du'. 'jean-marie' -> 'Je'."""
    s = (s or "").strip()
    if not s:
        return ""
    return s[0].upper() + (s[1:2].lower() if len(s) > 1 else "")


def _matricule_auto(nom: str, prenom: str, date_naiss: str) -> str:
    """cf. WinDev :
    PremiereLettreEnMajuscule(Gauche(Nom, 2))+"_"+
    PremiereLettreEnMajuscule(Gauche(Prenom, 2))+"_"+
    DateVersChaine(Date_Naiss, "JJMMAAAA")
    """
    if not date_naiss or len(date_naiss) < 10:
        return ""
    # ISO YYYY-MM-DD -> JJMMAAAA
    jjmmaaaa = f"{date_naiss[8:10]}{date_naiss[5:7]}{date_naiss[:4]}"
    return f"{_cap2(nom)}_{_cap2(prenom)}_{jjmmaaaa}"


_CIVILITE_MAP = {
    1: "M.",
    2: "Mme",
    3: "Mlle",
}


def _civilite_str(v) -> str:
    """Convertit civilite smallint -> libelle. WinDev conventions :
    1=M., 2=Mme, 3=Mlle. Autres (0, 255) -> vide."""
    if v is None:
        return ""
    try:
        return _CIVILITE_MAP.get(int(v), "")
    except (TypeError, ValueError):
        return str(v).strip()


def _row_from_query(r: dict, raison_sociale: str) -> ExportTRRow:
    """Convertit une row SQL en ExportTRRow (mappe les colonnes)."""
    return ExportTRRow(
        id_salarie=_clean_id(r.get("id_salarie")),
        matricule=(r.get("matricule_tr") or "").strip(),
        civilite=_civilite_str(r.get("civilite")),
        nom=(r.get("nom") or "").strip(),
        prenom=(r.get("prenom") or "").strip(),
        date_naissance=_iso_date(r.get("date_naiss")),
        adresse_1=(r.get("adresse1") or "").strip(),
        adresse_2=(r.get("adresse2") or "").strip(),
        adresse_3="",
        code_postal=(r.get("cp") or "").strip(),
        ville=(r.get("ville") or "").strip(),
        email=(r.get("mail") or "").strip(),
        pays="France",
        nombre_titres="",
        ref_pdist=raison_sociale,
        nom_employeur=raison_sociale,
        reference_chargement="",
    )


def _update_matricule_if_needed(row: ExportTRRow) -> None:
    """Si matricule vide -> genere + UPDATE en base."""
    if row.matricule or not row.id_salarie:
        return
    new_mat = _matricule_auto(row.nom, row.prenom, row.date_naissance)
    if not new_mat:
        return
    rh = get_pg_connection("rh")
    try:
        rh.execute(
            "UPDATE pgt_salarie SET matricule_tr = ?, modif_date = NOW() "
            "WHERE id_salarie = ?",
            (new_mat, int(row.id_salarie)),
        )
        row.matricule = new_mat
    except Exception:
        logger.exception("UPDATE matricule_tr KO id=%s", row.id_salarie)


# --------------------------------------------------------------------
# Recherche par entite (societe + mois)
# --------------------------------------------------------------------

def rechercher_par_entite(
    p: RechercheParEntiteParams,
) -> RechercheResult:
    """Cf. WinDev Btn Lancer la recherche par entite.

    Recupere tous les salaries de la societe id_ste dont date_debut
    d'embauche <= dernier jour du mois. Inclut les sortis si leur date
    de sortie demandee >= 1er jour du mois ET id_type_sortie > 1
    (motifs autres que 'demission volontaire').
    """
    if not p.id_ste:
        return RechercheResult(ok=False, message="Entite requise")
    if not re.match(r"^\d{4}-\d{2}$", p.mois_paiement or ""):
        return RechercheResult(
            ok=False, message="Format mois_paiement invalide (YYYY-MM)",
        )

    date_deb = _premier_jour(p.mois_paiement)
    date_fin = _dernier_jour(p.mois_paiement)

    rh = get_pg_connection("rh")
    try:
        rows = rh.query(
            """SELECT DISTINCT ON (s.id_salarie)
                    s.id_salarie, s.nom, s.prenom, s.date_naiss,
                    s.civilite, s.matricule_tr,
                    c.adresse1, c.adresse2, c.cp, c.ville, c.mail,
                    e.en_activite,
                    ste.raison_sociale
                 FROM pgt_salarie s
                 JOIN pgt_salarie_embauche e ON e.id_salarie = s.id_salarie
                 LEFT JOIN pgt_salarie_coordonnees c
                        ON c.id_salarie = s.id_salarie
                 LEFT JOIN pgt_societe ste ON ste.id_ste = e.id_ste
                WHERE e.id_ste = ?
                  AND e.date_debut <= ?
                  AND (s.modif_elem IS NULL
                       OR s.modif_elem NOT LIKE '%suppr%')
                  AND (e.modif_elem IS NULL
                       OR e.modif_elem NOT LIKE '%suppr%')
                ORDER BY s.id_salarie, e.date_debut DESC NULLS LAST""",
            (int(p.id_ste), date_fin),
        ) or []
    except Exception as e:
        logger.exception("Recherche par entite KO")
        return RechercheResult(ok=False, message=f"Erreur SQL : {e}")

    lignes: list[ExportTRRow] = []
    for r in rows:
        # cf. WinDev testAjout = EnActivite ; sinon check sortie
        actif = bool(r.get("en_activite"))
        if not actif:
            # Verifier salarie_sortie : type > 1 ET demandee >= date_deb
            sortie = rh.query_one(
                """SELECT date_sortie_demandee, id_type_sortie
                     FROM pgt_salarie_sortie
                    WHERE id_salarie = ?
                      AND (modif_elem IS NULL
                           OR modif_elem NOT LIKE '%suppr%')
                    ORDER BY date_sortie_demandee DESC NULLS LAST
                    LIMIT 1""",
                (int(r.get("id_salarie") or 0),),
            )
            if not sortie:
                continue
            id_type = sortie.get("id_type_sortie") or 0
            date_sortie = _iso_date(sortie.get("date_sortie_demandee"))
            if int(id_type) <= 1:
                continue
            if not date_sortie or date_sortie < date_deb:
                continue
        raison = (r.get("raison_sociale") or "").strip()
        row = _row_from_query(r, raison)
        _update_matricule_if_needed(row)
        lignes.append(row)

    lignes.sort(key=lambda x: (x.nom, x.prenom))
    return RechercheResult(
        ok=True, lignes=lignes,
        message=f"{len(lignes)} salarie(s) trouve(s)",
    )


# --------------------------------------------------------------------
# Recherche par salarie
# --------------------------------------------------------------------

def rechercher_par_salarie(
    p: RechercheParSalarieParams,
) -> RechercheResult:
    """Cf. WinDev Btn Lancer la recherche par salarie."""
    if not p.id_salarie or p.id_salarie == "0":
        return RechercheResult(
            ok=False, message="Merci de choisir un salarie",
        )
    rh = get_pg_connection("rh")
    try:
        r = rh.query_one(
            """SELECT s.id_salarie, s.nom, s.prenom, s.date_naiss,
                      s.civilite, s.matricule_tr,
                      c.adresse1, c.adresse2, c.cp, c.ville, c.mail,
                      e.en_activite,
                      ste.raison_sociale
                 FROM pgt_salarie s
                 LEFT JOIN pgt_salarie_embauche e ON e.id_salarie = s.id_salarie
                 LEFT JOIN pgt_salarie_coordonnees c
                        ON c.id_salarie = s.id_salarie
                 LEFT JOIN pgt_societe ste ON ste.id_ste = e.id_ste
                WHERE s.id_salarie = ?
                  AND (s.modif_elem IS NULL
                       OR s.modif_elem NOT LIKE '%suppr%')
                ORDER BY e.date_debut DESC NULLS LAST
                LIMIT 1""",
            (int(p.id_salarie),),
        )
    except Exception as e:
        logger.exception("Recherche par salarie KO")
        return RechercheResult(ok=False, message=f"Erreur SQL : {e}")

    if not r:
        return RechercheResult(ok=False, message="Salarie introuvable")

    raison = (r.get("raison_sociale") or "").strip()
    row = _row_from_query(r, raison)
    _update_matricule_if_needed(row)
    return RechercheResult(
        ok=True, lignes=[row], message="1 salarie",
    )


# --------------------------------------------------------------------
# Export CSV
# --------------------------------------------------------------------

_CSV_HEADERS = [
    ("MATRICULE",              "matricule"),
    ("civilite",               "civilite"),
    ("NOM",                    "nom"),
    ("PRENOM",                 "prenom"),
    ("DATE_DE_NAISSANCE",      "date_naissance"),
    ("ADRESSE_1",              "adresse_1"),
    ("adresse_2",              "adresse_2"),
    ("adresse_3",              "adresse_3"),
    ("CODE_POSTAL",            "code_postal"),
    ("VILLE",                  "ville"),
    ("email",                  "email"),
    ("PAYS",                   "pays"),
    ("NOMBRE_DE_TITRES",       "nombre_titres"),
    ("ref_pdist",              "ref_pdist"),
    ("nom_de_l_employeur",     "nom_employeur"),
    ("reference_chargement",   "reference_chargement"),
]


def _format_val(attr: str, value: str) -> str:
    """Formate une valeur pour l'export CSV.
    - date_naissance ISO -> JJ/MM/AAAA (comme WinDev DateVersChaine)
    """
    if not value:
        return ""
    if attr == "date_naissance" and len(value) >= 10:
        return f"{value[8:10]}/{value[5:7]}/{value[:4]}"
    return value


def _sanitize_csv_field(v: str) -> str:
    """Retire les caracteres qui casseraient le CSV separateur ';'."""
    return v.replace(";", ",").replace("\r", " ").replace("\n", " ")


def generer_csv(p: ExportCsvParams) -> tuple[str, bytes]:
    """Genere le CSV et retourne (nom_fichier, contenu).

    Encoding : Windows-1252 (pour ouverture Excel FR sans BOM UTF-8
    problematique).
    """
    lines: list[str] = []
    lines.append(";".join(h for h, _ in _CSV_HEADERS))
    for row in p.lignes:
        d = row.model_dump()
        cells = []
        for _, attr in _CSV_HEADERS:
            raw = str(d.get(attr) or "")
            cells.append(_sanitize_csv_field(_format_val(attr, raw)))
        lines.append(";".join(cells))
    content_str = "\r\n".join(lines) + "\r\n"
    try:
        content = content_str.encode("cp1252", errors="replace")
    except Exception:
        content = content_str.encode("utf-8")

    # Nom fichier : 'Vendeurs {Entite}.csv' - normalise pour OS
    lib = (p.lib_entite or "export").strip()
    lib = unicodedata.normalize("NFKD", lib)
    lib = "".join(c for c in lib if not unicodedata.combining(c))
    lib = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", lib)
    lib = re.sub(r"\s+", "_", lib.strip()) or "export"
    fic_name = f"Vendeurs_{lib}.csv"
    return fic_name, content
