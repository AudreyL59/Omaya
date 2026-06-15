"""
Module de recherche multi-cibles (Fen_RecherchePOO WinDev).

4 modes :
  - client   : recherche dans adv.pgt_client (avec option NumBS via
               OEN_contrat.RefClient pour trouver via le contrat)
  - contrat  : recherche cross-partenaires (ENI / SFR / OEN / STR / VAL /
               IAG / TLC). Si NumBS commence par 'LOT' -> recherche dans
               info_interne au lieu de num_bs.
  - salarie  : recherche dans rh.pgt_salarie + coord + embauche + societe
               + type_poste.
  - cv       : recherche dans recrutement.pgt_cvtheque + cv_source.

Chaque fonction retourne une liste de dicts uniformes au format
`SearchRow` (cf. mapping att1..att7 + att_aff + att8 (id) WinDev).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.core.database.pg import get_pg_connection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _str(v: Any) -> str:
    return "" if v is None else str(v)


def _int(v: Any) -> int:
    if v is None or v == "":
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _iso(v: Any) -> str:
    """Date/datetime -> ISO 'YYYY-MM-DD'."""
    if v is None:
        return ""
    s = str(v)
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


def _capitalize(s: str) -> str:
    if not s:
        return ""
    return s[0].upper() + s[1:].lower()


def _normalize_nom(s: str) -> str:
    """Cf. WinDev : ChaineFormate(SaisieNom, ccSansEspace). Retire les
    espaces internes (le format ccSansAccent ne s'applique pas - on garde
    les accents pour ILIKE)."""
    return (s or "").replace(" ", "").strip()


def _empty_criteres(c: dict) -> bool:
    """True si tous les champs de saisie sont vides."""
    return not any(
        (c.get(k) or "").strip()
        for k in ("nom", "prenom", "tel", "mail", "id", "num_bs")
    )


def _row(
    *,
    origine: str,
    id_: Any,
    att1: str = "",
    att2: str = "",
    att3: str = "",
    att4: str = "",
    att5: str = "",
    att6: str = "",
    att7: str = "",
    att_aff: str = "",
    extra: dict | None = None,
) -> dict:
    out = {
        "origine": origine,
        "id": _str(id_),
        "att1": att1,
        "att2": att2,
        "att3": att3,
        "att4": att4,
        "att5": att5,
        "att6": att6,
        "att7": att7,
        "att_aff": att_aff,
    }
    if extra:
        out.update(extra)
    return out


# ---------------------------------------------------------------------------
# Mode CLIENT (Selecteur1 = 1)
# ---------------------------------------------------------------------------


def search_client(criteres: dict) -> list[dict]:
    """Recherche client (adv.pgt_client).

    Colonnes WinDev : Nom / Prenom / CP Ville / Mobile / Fixe / Mail
    Si num_bs renseigne -> JOIN adv.pgt_oen_contrat sur RefClient (cf. WinDev).
    """
    if _empty_criteres(criteres):
        return []

    db = get_pg_connection("adv")
    where_parts = ["(c.modif_elem IS NULL OR c.modif_elem NOT LIKE '%suppr%')"]
    params: list[Any] = []
    joins = ""

    num_bs = (criteres.get("num_bs") or "").strip()
    id_ = (criteres.get("id") or "").strip()
    nom = _normalize_nom(criteres.get("nom") or "")
    prenom = (criteres.get("prenom") or "").strip()
    tel = (criteres.get("tel") or "").strip()
    mail = (criteres.get("mail") or "").strip()

    if num_bs:
        # Cf. WinDev : if NumBS -> JOIN OEN_contrat.RefClient
        joins = " INNER JOIN adv.pgt_oen_contrat oc ON oc.id_client = c.id_client"
        where_parts.append("oc.ref_client ILIKE ?")
        params.append(f"{num_bs}%")
    elif id_:
        where_parts.append("c.id_client::text = ?")
        params.append(id_)
    else:
        if nom:
            # Cf. WinDev : LIKE 'X%' OR LIKE '% X%' (anywhere après espace)
            where_parts.append("(c.nom ILIKE ? OR c.nom ILIKE ?)")
            params.extend([f"{nom}%", f"% {nom}%"])
        if prenom:
            where_parts.append("c.prenom ILIKE ?")
            params.append(f"{prenom}%")
        if tel:
            where_parts.append("(c.gsm ILIKE ? OR c.tel ILIKE ?)")
            params.extend([f"{tel}%", f"{tel}%"])
        if mail:
            where_parts.append("c.mail ILIKE ?")
            params.append(f"{mail}%")

    sql = (
        "SELECT DISTINCT c.id_client, c.nom, c.prenom, c.cp, c.ville, "
        "c.gsm, c.tel, c.mail "
        f"FROM adv.pgt_client c{joins} "
        f"WHERE {' AND '.join(where_parts)} "
        "ORDER BY c.nom ASC LIMIT 500"
    )
    rows = db.query(sql, tuple(params))
    return [
        _row(
            origine="CLIENT",
            id_=r.get("id_client"),
            att2=_str(r.get("nom")),
            att3=_capitalize(_str(r.get("prenom"))),
            att4=f"{_str(r.get('cp'))} {_str(r.get('ville'))}".strip(),
            att5=_str(r.get("gsm")),
            att6=_str(r.get("tel")),
            att7=_str(r.get("mail")),
        )
        for r in (rows or [])
    ]


# ---------------------------------------------------------------------------
# Mode CONTRAT (Selecteur1 = 2)
# ---------------------------------------------------------------------------


def _list_partenaires_actifs() -> list[str]:
    """Liste des prefixes BDD des partenaires actifs."""
    db = get_pg_connection("adv")
    rows = db.query(
        """SELECT prefixe_bdd FROM adv.pgt_partenaire
            WHERE is_actif = TRUE
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND COALESCE(prefixe_bdd, '') <> ''"""
    )
    return sorted({_str(r.get("prefixe_bdd")).strip() for r in (rows or [])})


def search_contrat(criteres: dict) -> list[dict]:
    """Recherche cross-partenaires.

    Colonnes WinDev : NumBS / Vendeur / Date Sign. / Produit / Etat / Partenaire
    Filtres : SaisieID prime sur SaisieNumBS. Si NumBS commence par 'LOT' ->
    cherche dans info_interne (et concatène l'affichage NumBS + info).
    """
    num_bs = (criteres.get("num_bs") or "").strip()
    id_ = (criteres.get("id") or "").strip()
    if not num_bs and not id_:
        return []  # cf. WinDev : refuse si rien

    is_lot = num_bs.upper().startswith("LOT")
    parts = _list_partenaires_actifs()
    if not parts:
        return []

    def fetch(part: str) -> list[dict]:
        lp = part.lower()
        db = get_pg_connection("adv")
        where = [
            "c.id_salarie = s.id_salarie",
            f"c.id_produit = p.id_produit",
            f"c.id_etat_contrat = e.id_etat",
            "(c.modif_elem IS NULL OR c.modif_elem NOT LIKE '%suppr%')",
        ]
        params: list[Any] = []
        bs_col = "c.num_bs"
        if id_:
            where.append("c.id_contrat::text = ?")
            params.append(id_)
        elif is_lot:
            where.append("c.info_interne ILIKE ?")
            params.append(f"%{num_bs}%")
            bs_col = "CONCAT(c.num_bs, ' (', c.info_interne, ')')"
        else:
            where.append("c.num_bs ILIKE ?")
            params.append(f"{num_bs}%")

        try:
            return db.query(
                f"""SELECT c.id_contrat,
                          {bs_col} AS num_bs,
                          c.date_signature,
                          p.lib_produit, p.prefixe_bdd,
                          s.nom AS sal_nom, s.prenom AS sal_prenom,
                          e.lib_etat
                     FROM adv.pgt_{lp}_contrat c,
                          rh.pgt_salarie s,
                          adv.pgt_{lp}_produit p,
                          adv.pgt_{lp}_etat_contrat e
                    WHERE {' AND '.join(where)}
                    ORDER BY c.date_signature DESC NULLS LAST
                    LIMIT 100""",
                tuple(params),
            )
        except Exception:
            return []

    out: list[dict] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for part, rows in zip(parts, pool.map(fetch, parts)):
            for r in rows or []:
                nom = _str(r.get("sal_nom"))
                pre = _capitalize(_str(r.get("sal_prenom")))
                out.append(
                    _row(
                        origine="CONTRAT",
                        id_=r.get("id_contrat"),
                        att2=_str(r.get("num_bs")),
                        att3=f"{nom} {pre}".strip(),
                        att4=_iso(r.get("date_signature")),
                        att5=_str(r.get("lib_produit")),
                        att6=_str(r.get("lib_etat")),
                        att7=part.upper(),
                    )
                )
    out.sort(key=lambda x: x["att4"] or "", reverse=True)
    return out


# ---------------------------------------------------------------------------
# Mode SALARIE (Selecteur1 = 3)
# ---------------------------------------------------------------------------


def search_salarie(criteres: dict) -> list[dict]:
    """Recherche salarie (rh.pgt_salarie + coord + embauche + societe).

    Colonnes WinDev : Nom Prenom / Entite-Poste / Date Embauche /
    Sortie (active) / Mobile / Mail. Aff = Affectation.
    """
    if _empty_criteres(criteres):
        return []

    db = get_pg_connection("rh")
    where = [
        "c.id_salarie = s.id_salarie",
        "e.id_salarie = s.id_salarie",
        "soc.id_ste = e.id_ste",
        "tp.id_type_poste = e.id_type_poste",
        "(s.modif_elem IS NULL OR s.modif_elem NOT LIKE 'suppr')",
    ]
    params: list[Any] = []

    id_ = (criteres.get("id") or "").strip()
    nom = _normalize_nom(criteres.get("nom") or "")
    prenom = (criteres.get("prenom") or "").strip()
    tel = (criteres.get("tel") or "").strip()
    mail = (criteres.get("mail") or "").strip()

    if id_:
        where.append("s.id_salarie::text = ?")
        params.append(id_)
    else:
        if nom:
            where.append("(s.nom ILIKE ? OR s.nom ILIKE ?)")
            params.extend([f"{nom}%", f"% {nom}%"])
        if prenom:
            where.append("s.prenom ILIKE ?")
            params.append(f"{prenom}%")
        if tel:
            where.append("c.tel_mob ILIKE ?")
            params.append(f"%{tel}%")
        if mail:
            where.append("c.mail ILIKE ?")
            params.append(f"{mail}%")

    rows = db.query(
        f"""SELECT s.id_salarie, s.nom, s.prenom,
                   soc.rs_interne, tp.lib_poste,
                   e.en_activite, e.date_debut,
                   c.tel_mob, c.mail
              FROM rh.pgt_salarie s,
                   rh.pgt_salarie_coordonnees c,
                   rh.pgt_salarie_embauche e,
                   rh.pgt_societe soc,
                   rh.pgt_type_poste tp
             WHERE {' AND '.join(where)}
             ORDER BY s.nom ASC
             LIMIT 500""",
        tuple(params),
    )
    out = []
    for r in rows or []:
        nom_complet = (
            f"{_str(r.get('nom'))} {_capitalize(_str(r.get('prenom')))}"
        ).strip()
        ente_poste = (
            f"{_str(r.get('rs_interne'))} - {_str(r.get('lib_poste'))}"
        ).strip(" -")
        out.append(
            _row(
                origine="SALARIE",
                id_=r.get("id_salarie"),
                att2=nom_complet,
                att3=ente_poste,
                att4=_iso(r.get("date_debut")),
                att5="En activité" if r.get("en_activite") else "Hors effectifs",
                att6=_str(r.get("tel_mob")),
                att7=_str(r.get("mail")),
                # Affectation chargee a part si besoin (TODO)
                att_aff="",
                extra={
                    "has_photo": True,
                    "en_activite": bool(r.get("en_activite")),
                },
            )
        )
    return out


# ---------------------------------------------------------------------------
# Mode CV (Selecteur1 = 4)
# ---------------------------------------------------------------------------


def search_cv(criteres: dict) -> list[dict]:
    """Recherche CVtheque (recrutement.pgt_cvtheque + cv_source).

    Colonnes WinDev : Nom Prenom / CP Ville / Date Saisie (ou DateREAC si
    valide) / Source / Mobile / Mail. Aff = Statut CV.
    """
    if _empty_criteres(criteres):
        return []

    db = get_pg_connection("recrutement")
    where = [
        "cs.id_cvsource = cv.id_cvsource",
        "(cv.modif_elem IS NULL OR cv.modif_elem NOT LIKE 'suppr')",
    ]
    params: list[Any] = []

    id_ = (criteres.get("id") or "").strip()
    nom = (criteres.get("nom") or "").strip()
    prenom = (criteres.get("prenom") or "").strip()
    tel = (criteres.get("tel") or "").strip()
    mail = (criteres.get("mail") or "").strip()

    if id_:
        where.append("cv.id_cvtheque::text = ?")
        params.append(id_)
    else:
        if nom:
            where.append("cv.nom ILIKE ?")
            params.append(f"%{nom}%")
        if prenom:
            where.append("cv.prenom ILIKE ?")
            params.append(f"{prenom}%")
        if tel:
            where.append("cv.gsm ILIKE ?")
            params.append(f"%{tel}%")
        if mail:
            where.append("cv.mail ILIKE ?")
            params.append(f"{mail}%")

    rows = db.query(
        f"""SELECT cv.id_cvtheque, cv.nom, cv.prenom,
                   cv.id_communes_france,
                   cv.date_saisie, cv.date_reac,
                   cs.lib_source,
                   cv.gsm, cv.mail
              FROM recrutement.pgt_cvtheque cv,
                   recrutement.pgt_cv_source cs
             WHERE {' AND '.join(where)}
             ORDER BY cv.date_saisie DESC NULLS LAST
             LIMIT 500""",
        tuple(params),
    )
    out = []
    for r in rows or []:
        nom_complet = (
            f"{_str(r.get('nom'))} {_capitalize(_str(r.get('prenom')))}"
        ).strip()
        # date = date_reac si valide sinon date_saisie (cf. WinDev)
        date_reac_iso = _iso(r.get("date_reac"))
        date_saisie_iso = _iso(r.get("date_saisie"))
        date_aff = date_reac_iso or date_saisie_iso
        out.append(
            _row(
                origine="CV",
                id_=r.get("id_cvtheque"),
                att2=nom_complet,
                att3=_str(r.get("id_communes_france")),  # TODO: resolve city name
                att4=date_aff,
                att5=_str(r.get("lib_source")),
                att6=_str(r.get("gsm")),
                att7=_str(r.get("mail")),
                att_aff="",  # TODO: charger Statut CV via pgt_cvtheque_histo si besoin
            )
        )
    return out


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


_DISPATCH = {
    "client": search_client,
    "contrat": search_contrat,
    "salarie": search_salarie,
    "cv": search_cv,
}


def search(mode: str, criteres: dict) -> list[dict]:
    """Dispatcher selon le mode (Selecteur1 WinDev : 1=client, 2=contrat,
    3=salarie, 4=cv)."""
    fn = _DISPATCH.get((mode or "").lower())
    if not fn:
        return []
    return fn(criteres)
