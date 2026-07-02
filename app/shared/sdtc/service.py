"""
SDTC - service principal : charge l'ensemble des données nécessaires à
l'ouverture de Fen_SDTC.

Transposition de l'init `MaFenêtre(idSalarié)` :
  - DonneInfoSalarié -> nom, prénom, adresse, société, date_embauche,
    date_ancienneté, idSte
  - InfoMutuelle : "Oui, depuis le DD/MM/YYYY" / "Non"
  - finS + Courrier (FPE / DEMISSION / LICENCIEMENT) selon TypeSortie
  - Date du dernier contrat
  - HTML `mesInfos` (entête + bloc identité + bloc commission avec
    placeholders MONTANT_COMM / MONTANT_CP / MONTANT_DECO / MONTANT_AVANCE
    / NB_TR / DATEABS - remplacés à la génération PDF/Mail).

Endpoint principal : GET /shared/sdtc/{id_salarie}/load
"""

from __future__ import annotations

from app.core.database.pg import get_pg_connection
from app.shared.tickets.forms.sortie_rh import _date_dernier_ctt

from .helpers import _capitalize, _esc, _fr_date, _int, _iso, _str


# ---------------------------------------------------------------------------
# finS : normalisation du libellé sortie (cf. WinDev MaFenêtre)
# ---------------------------------------------------------------------------


# Mapping ID -> libelle pour la combo 'Delai de prevenance' (WinDev).
# Base 1 fidele a la combo WinDev :
#   1 : (ligne vide)
#   2 : sans
#   3 : 24 heures
#   4 : 48 heures
#   5 : 2 semaines
#   6 : 1 mois
# -1 / 0 : valeur avant selection (aucun libelle).
_DELAI_PREVENANCE_MAPPING = {
    "-1": "",
    "0": "",
    "1": "",
    "2": "sans",
    "3": "24 heures",
    "4": "48 heures",
    "5": "2 semaines",
    "6": "1 mois",
}


def _fmt_delai_prevenance(raw: str) -> str:
    """Cf. WinDev ..ValeurAffichee : renvoie le libelle de la combo.

    Si la valeur contient deja un espace ou est explicitement 'sans',
    on considere qu'elle est deja libellee et on la retourne telle
    quelle (juste capitalise le 1er caractere).
    Sinon on cherche dans _DELAI_PREVENANCE_MAPPING (IDs numeriques).
    """
    if not raw:
        return ""
    v = raw.strip()
    if not v:
        return ""
    # Deja libelle (contient un espace ou texte non-numerique)
    if " " in v or v.lower() == "sans":
        return v[:1].upper() + v[1:] if v else ""
    # ID numerique -> lookup mapping
    return _DELAI_PREVENANCE_MAPPING.get(v, v)


def _normalize_fin_s(lib_sortie: str) -> tuple[str, str]:
    """Cf. WinDev :
      si Contient(finS,'FPE')           -> FIN DE PERIODE D'ESSAI A L'INITIATIVE [SAL/EMP]
      si Contient(finS,'mission')       -> DEMISSION
      sinon                              -> LICENCIEMENT

    Retourne (titre_normalisé, kind) avec kind ∈ {'fpe','demission','licenciement',''}.
    """
    if not lib_sortie:
        return ("", "")
    lib_up = lib_sortie.upper()
    if "FPE" in lib_up:
        if "SALAR" in lib_up:
            return ("FIN DE PERIODE D'ESSAI A L'INITIATIVE DU SALARIE", "fpe")
        return ("FIN DE PERIODE D'ESSAI A L'INITIATIVE DE L'EMPLOYEUR", "fpe")
    if "MISSION" in lib_up:
        return ("DEMISSION", "demission")
    return ("LICENCIEMENT", "licenciement")


# ---------------------------------------------------------------------------
# HTML mesInfos (entête du bloc commission avec placeholders)
# ---------------------------------------------------------------------------


def build_info_salarie_html(
    *,
    nom_salarie: str,
    nom_societe: str,
    date_embauche: str,
    date_sortie_reelle: str,
    courrier_info: str,
    fin_s_titre: str,
    adresse1: str,
    adresse2: str,
    cp: str,
    ville: str,
    num_ss: str,
    date_naiss: str,
    lieu_naiss: str,
    dep_naiss: str,
    info_mutuelle: str,
    date_anciennete_yyyymmdd: str,
) -> str:
    """Construit le bloc HTML `mesInfos` fidèle WinDev (avec placeholders
    MONTANT_COMM / MONTANT_CP / MONTANT_DECO / MONTANT_AVANCE / NB_TR /
    DATEABS qui seront remplis à la génération finale).

    `date_anciennete_yyyymmdd` au format 'YYYYMMDD' pour comparer aux 20260201
    (cf. WinDev `si monVendeur.DateAnciennete >= 20260201`).
    """
    montant_cp_line = ""
    if date_anciennete_yyyymmdd and date_anciennete_yyyymmdd >= "20260201":
        montant_cp_line = "<p>CP : MONTANT_CP </br>"

    sortie_line = (
        f"Sorti(e) le {_esc(date_sortie_reelle)} {_esc(courrier_info)}</br>"
        if date_sortie_reelle
        else f"Sorti(e) le : {_esc(courrier_info)}</br>"
    )

    return (
        "<table border='1' cellspacing='0'>"
        "<tr><th align='center'><b>"
        "<font face='arial' style='font-size:14pt;text-align:center;'>"
        "SOLDE DE TOUT COMPTE</font></b></th></tr>"
        f"<tr><td align='center'><b>"
        f"<font face='arial' style='font-size:10pt;text-align:center;'>"
        f"{_esc(nom_salarie)} chez {_esc(nom_societe)}</font></b></td></tr>"
        f"<tr><td align='center'>"
        f"<font face='arial' style='font-size:8pt;text-align:center;' size='1'>"
        f"Entré(e) le {_esc(date_embauche)}<br/>"
        f"{sortie_line}"
        f"<b>{_esc(fin_s_titre)}</b></br>"
        f"{_esc(adresse1)}</br>"
        f"{_esc(adresse2)}</br>"
        f"{_esc(cp)} {_esc(ville)}</br>"
        f"N° SS: {_esc(num_ss)}</br>"
        f"Né(e) le : {_esc(date_naiss)} à {_esc(lieu_naiss)} ({_esc(dep_naiss)})</br></br>"
        "<p>COMM : MONTANT_COMM </br>"
        f"{montant_cp_line}"
        "DECO : MONTANT_DECO </br>"
        "AVANCE : MONTANT_AVANCE </br>"
        "Nombre de TR : NB_TR </br>"
        f"Mutuelle Entreprise : {_esc(info_mutuelle)} </br>"
        "Absence : DATEABS </br>"
        "</td></tr></table>"
        "<font face='arial' style='font-size:8pt;' size='1'>"
        "<p>Cordialement.</p>"
        "</font>"
    )


# ---------------------------------------------------------------------------
# load - point d'entrée principal pour l'ouverture de Fen_SDTC
# ---------------------------------------------------------------------------


def load(id_salarie: int) -> dict:
    """Charge tout ce qu'il faut pour l'ouverture de Fen_SDTC."""
    db_rh = get_pg_connection("rh")

    sal = db_rh.query_one(
        """SELECT s.id_salarie, s.civilite, s.nom, s.prenom, s.num_ss,
                  s.date_naiss, s.lieu_naiss, s.dep_naiss,
                  c.adresse1, c.adresse2, c.cp, c.ville, c.mail,
                  c.tel_mob, c.tel_fixe,
                  se.date_debut AS date_embauche, se.date_anciennete,
                  se.id_ste,
                  soc.rs_interne, soc.raison_sociale
             FROM rh.pgt_salarie s
             LEFT JOIN rh.pgt_salarie_coordonnees c ON c.id_salarie = s.id_salarie
             LEFT JOIN rh.pgt_salarie_embauche se ON se.id_salarie = s.id_salarie
             LEFT JOIN rh.pgt_societe soc ON soc.id_ste = se.id_ste
            WHERE s.id_salarie = ?""",
        (int(id_salarie),),
    )
    if not sal:
        return {"found": False}

    nom = _str(sal.get("nom"))
    prenom = _str(sal.get("prenom"))
    nom_salarie = f"{nom} {_capitalize(prenom)}".strip()
    nom_societe = _str(sal.get("rs_interne")) or _str(sal.get("raison_sociale"))
    id_ste = _int(sal.get("id_ste"))
    date_embauche_iso = _iso(sal.get("date_embauche"))
    date_anciennete_iso = _iso(sal.get("date_anciennete"))
    date_anciennete_yyyymmdd = date_anciennete_iso.replace("-", "") if date_anciennete_iso else ""

    # --- Sortie -----------------------------------------------------------
    sortie_row = db_rh.query_one(
        """SELECT ss.date_sortie_reelle, ss.date_sortie_demandee,
                  ss.courrier_date_envoi, ss.courrier_date_recep,
                  ss.courrier_delai_prev,
                  ss.mail_objet, ss.mail_contenu,
                  ss.id_type_sortie,
                  tss.lib_sortie
             FROM rh.pgt_salarie_sortie ss
             LEFT JOIN rh.pgt_type_sortie_salarie tss
               ON tss.id_type_sortie = ss.id_type_sortie
            WHERE ss.id_salarie = ?""",
        (int(id_salarie),),
    )
    sortie_data = {
        "date_sortie_reelle": "",
        "date_sortie_demandee": "",
        "lib_sortie_raw": "",
        "titre_sortie": "",
        "kind": "",
        "courrier_info": "",
        "mail_objet": "",
        "mail_contenu": "",
    }
    if sortie_row:
        date_sortie = _iso(sortie_row.get("date_sortie_reelle"))
        date_sortie_dem = _iso(sortie_row.get("date_sortie_demandee"))
        lib_raw = _str(sortie_row.get("lib_sortie"))
        titre, kind = _normalize_fin_s(lib_raw)
        courrier_info = ""
        if kind == "fpe":
            envoi = _fr_date(sortie_row.get("courrier_date_envoi"))
            delai_raw = _str(sortie_row.get("courrier_delai_prev"))
            # cf. WinDev : ..ValeurAffichee renvoie le libelle de la combo.
            # Notre colonne contient soit un libelle deja formate ('1 mois',
            # '24 heures', 'sans'...) soit un ID numerique (1-6 ou -1).
            # -> _fmt_delai_prevenance convertit l'ID en libelle si besoin.
            delai = _fmt_delai_prevenance(delai_raw)
            if envoi:
                courrier_info = f"(Courrier envoye le {envoi}"
                if delai:
                    courrier_info += f" + delai de prevenance : {delai}"
                courrier_info += ")"
        elif kind == "demission":
            recu = _fr_date(sortie_row.get("courrier_date_recep"))
            if recu:
                courrier_info = f"(Courrier recu le {recu})"
        sortie_data = {
            "date_sortie_reelle": date_sortie,
            "date_sortie_demandee": date_sortie_dem,
            "lib_sortie_raw": lib_raw,
            "titre_sortie": titre,
            "kind": kind,
            "courrier_info": courrier_info,
            "mail_objet": _str(sortie_row.get("mail_objet")),
            "mail_contenu": _str(sortie_row.get("mail_contenu")),
        }

    # --- Mutuelle ---------------------------------------------------------
    mut = db_rh.query_one(
        """SELECT mutuelle_doc_envoyes, adhesion_date
             FROM rh.pgt_salarie_mutuelle WHERE id_salarie = ?""",
        (int(id_salarie),),
    )
    info_mutuelle = "Non"
    if mut and mut.get("mutuelle_doc_envoyes"):
        info_mutuelle = "Oui"
        adh = _fr_date(mut.get("adhesion_date"))
        if adh:
            info_mutuelle = f"Oui, depuis le {adh}"

    # --- Date dernier ctt ------------------------------------------------
    try:
        dernier_ctt = _date_dernier_ctt(int(id_salarie))
    except Exception:
        dernier_ctt = ""

    # --- HTML mesInfos avec placeholders ---------------------------------
    info_salarie_html = build_info_salarie_html(
        nom_salarie=nom_salarie,
        nom_societe=nom_societe,
        date_embauche=_fr_date(sal.get("date_embauche")),
        date_sortie_reelle=_fr_date(sortie_data["date_sortie_reelle"]),
        courrier_info=sortie_data["courrier_info"],
        fin_s_titre=sortie_data["titre_sortie"],
        adresse1=_str(sal.get("adresse1")),
        adresse2=_str(sal.get("adresse2")),
        cp=_str(sal.get("cp")),
        ville=_str(sal.get("ville")),
        num_ss=_str(sal.get("num_ss")),
        date_naiss=_fr_date(sal.get("date_naiss")),
        lieu_naiss=_str(sal.get("lieu_naiss")),
        dep_naiss=_str(sal.get("dep_naiss")),
        info_mutuelle=info_mutuelle,
        date_anciennete_yyyymmdd=date_anciennete_yyyymmdd,
    )

    return {
        "found": True,
        "id_salarie": str(id_salarie),
        "salarie": {
            "civilite": _int(sal.get("civilite")),
            "nom": nom,
            "prenom": prenom,
            "lib_nom": nom_salarie,
            "num_ss": _str(sal.get("num_ss")),
            "date_naiss": _iso(sal.get("date_naiss")),
            "lieu_naiss": _str(sal.get("lieu_naiss")),
            "dep_naiss": _str(sal.get("dep_naiss")),
            "adresse1": _str(sal.get("adresse1")),
            "adresse2": _str(sal.get("adresse2")),
            "cp": _str(sal.get("cp")),
            "ville": _str(sal.get("ville")),
            "mail": _str(sal.get("mail")),
            "tel_mob": _str(sal.get("tel_mob")),
            "tel_fixe": _str(sal.get("tel_fixe")),
            "date_embauche": date_embauche_iso,
            "date_anciennete": date_anciennete_iso,
            "date_anciennete_yyyymmdd": date_anciennete_yyyymmdd,
            "id_ste": str(id_ste) if id_ste else "",
            "lib_societe": nom_societe,
        },
        "sortie": sortie_data,
        "info_mutuelle": info_mutuelle,
        "date_dernier_ctt": dernier_ctt,
        "info_salarie_html": info_salarie_html,
    }


# ---------------------------------------------------------------------------
# Substitution des placeholders dans mesInfos (Btn "Generation PDFs/XLS/Mail")
# ---------------------------------------------------------------------------


def substitute_placeholders(
    html: str,
    *,
    comm_tot_stc: float,
    date_anciennete_yyyymmdd: str,
    deco: float = 0.0,
    avance: float = 0.0,
    nb_tr: int = 0,
    date_dernier_ctt: str = "",
) -> str:
    """Substitue les placeholders MONTANT_COMM / MONTANT_CP / MONTANT_DECO /
    MONTANT_AVANCE / NB_TR / DATEABS dans le HTML mesInfos.

    Cf. WinDev Btn "Generation des PDFs, XLS et du mail recap" :
      si DateAnciennete >= 20260201 :
        MontantCom  = Comm_Tot_STC / 1.1
        MontantCP   = Comm_Tot_STC - MontantCom
        -> MONTANT_COMM = MontantCom €
        -> MONTANT_CP   = MontantCP €
      sinon :
        -> MONTANT_COMM = Comm_Tot_STC €

      -> MONTANT_DECO   = deco €
      -> MONTANT_AVANCE = avance €
      -> NB_TR          = nb_tr
      -> DATEABS        = " à compter du DD/MM/YYYY" (si dernier_ctt)
    """
    def fmt_money(v: float) -> str:
        return f"{v:,.2f}".replace(",", " ").replace(".", ",") + " €"

    out = html
    if date_anciennete_yyyymmdd and date_anciennete_yyyymmdd >= "20260201":
        montant_com = comm_tot_stc / 1.1
        montant_cp = comm_tot_stc - montant_com
        out = out.replace("MONTANT_COMM", fmt_money(montant_com))
        out = out.replace("MONTANT_CP", fmt_money(montant_cp))
    else:
        out = out.replace("MONTANT_COMM", fmt_money(comm_tot_stc))

    out = out.replace("MONTANT_DECO", fmt_money(deco))
    out = out.replace("MONTANT_AVANCE", fmt_money(avance))
    out = out.replace("NB_TR", str(int(nb_tr)))
    dateabs = f" à compter du {_fr_date(date_dernier_ctt)}" if date_dernier_ctt else ""
    out = out.replace("DATEABS", dateabs)
    return out
