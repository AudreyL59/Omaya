"""
Service Call Fibre - chargement de la fiche d'un ticket (popup).

Transposition du code WinDev `PAGE_TicketFicheFibre` (code init serveur) :
- TK_CallSFR + TK_Liste (par IDTK_Liste) -> infos client + vente + statut
- Salarie + Salarie_Coordonnees (par IDSalarie) -> vendeur
- TK_CallSFR_Panier JOIN SFR_OffresProvad -> panier (toutes les lignes)
- Pour chaque ligne du panier, HLitRecherche TK_CallSFR_Panier pour les
  champs detail (NumPortabilite, RIO, NumPrise_Optique, OptChoisies,
  TestEligibilite-image).

Phase 1 = lecture seule. Save/verrou ope traites separement.
Phase 2 = viewer documents (CIN/KBIS/Lettre resil) via rest.omaya.fr.
"""

import base64
import urllib.request
from typing import Any

from app.core.database import get_connection
from app.intranets.call.fibre.services.tickets import (
    _capitalize,
    _format_nom_client,
    _format_ville,
    _iso,
    _str_id,
    _to_int,
)


DOC_BASE_URL = "https://rest.omaya.fr/DocOmaya"


def _url_exists(url: str, timeout: float = 3.0) -> bool:
    """HEAD HTTP : True si le fichier existe (HTTP 200/2xx)."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _first_existing(*urls: str) -> tuple[str, str]:
    """Retourne (url, kind) du premier fichier existant.

    kind = 'pdf' si l'URL finit par .pdf, sinon 'image'.
    Si aucun n'existe -> ("", "").
    """
    for url in urls:
        if not url:
            continue
        if _url_exists(url):
            kind = "pdf" if url.lower().endswith(".pdf") else "image"
            return url, kind
    return "", ""


def _mask_phone(num: str) -> str:
    """'0612345678' -> '06123456xx'. Vide si num vide."""
    s = (num or "").strip()
    if not s:
        return ""
    if len(s) <= 2:
        return "xx"
    return s[:-2] + "xx"


def _bool(v: Any) -> bool:
    return bool(v) and v not in (0, "0", "")


def _safe_b64_data_url(raw: Any) -> str:
    """Memo binaire HFSQL -> data URL base64. Renvoie '' si vide ou non-binaire."""
    if not raw:
        return ""
    if isinstance(raw, memoryview):
        raw = bytes(raw)
    if isinstance(raw, (bytes, bytearray)):
        b64 = base64.b64encode(raw).decode("ascii")
    elif isinstance(raw, str):
        # Si deja en base64 (le pont peut deja serializer ainsi), on prend tel quel
        b64 = raw
    else:
        return ""
    return f"data:image/jpeg;base64,{b64}"


def load_fiche(id_tk_liste: int, current_user_id: int = 0) -> dict:
    """Charge toutes les donnees necessaires pour afficher la fiche d'un
    ticket Call Fibre.

    `current_user_id` : id_salarie de l'utilisateur connecte. Sert a savoir
    s'il a deja pris l'appel (= a poser le verrou) -> si oui, on demasque
    les mobiles. Sinon les 2 derniers chars sont remplaces par "xx".
    """
    db_ticket = get_connection("ticket")
    db_bo = get_connection("ticket_bo")
    db_rh = get_connection("rh")
    db_adv = get_connection("adv")

    # 1. Infos ticket : TK_Liste + TK_CallSFR (2 queries, pas cross-base)
    rows_liste = db_ticket.query(
        """SELECT
            IDTK_Liste AS id_tk_liste,
            IDTK_Statut AS id_tk_statut,
            OPCrea AS op_crea,
            Cloturée AS cloturee,
            DateCloture AS date_cloture
        FROM TK_Liste
        WHERE IDTK_Liste = ?""",
        (id_tk_liste,),
    )
    if not rows_liste:
        return {"error": "Ticket introuvable"}
    tk_liste = rows_liste[0]

    rows_call = db_bo.query(
        """SELECT
            IDtk_CallSFR, IDTK_Liste, IDSalarie,
            CivilitéClient, NomClient, NomMaritalClient, PrenomClient,
            DATENAISS, DEPNAISS, TypeLogement, ADRESSE1, ADRESSE2, CP, VILLE,
            adrMail, Mobile1, Mobile2,
            AppelEnCours, DateH_Appel, OpéAppel, RefAppel,
            MotifAnnulation, DateDeb_PriseEnCharge, DateFin_PriseEnCharge,
            InterventionVend, MobPropoVend, InfoVente,
            AnomalieMobile, IDTK_CallSFR_TypeAnomalie, InfoCpltAnomalie,
            Opt_Rappel, Opt_Partenaire,
            ClientPro, ClientRS, ClientSiret
        FROM TK_CallSFR
        WHERE IDTK_Liste = ?
          AND ModifELEM NOT LIKE '%suppr%'""",
        (id_tk_liste,),
    )
    if not rows_call:
        return {"error": "Pas de TK_CallSFR pour ce ticket"}
    tc = rows_call[0]

    id_call_sfr = _to_int(tc.get("IDtk_CallSFR"))
    id_salarie = _to_int(tc.get("IDSalarie"))
    id_tk_statut = _to_int(tk_liste.get("id_tk_statut"))
    appel_en_cours = _bool(tc.get("AppelEnCours"))
    ope_appel_id = _to_int(tc.get("OpéAppel"))

    # Verrou opé : est-ce que l'opé connecte a pris l'appel ?
    # WinDev demasque les mobiles uniquement si EtatAppelClient = AppelEnCours = 1.
    # Ici on demasque si l'opé connecte est l'opé du ticket actuel (par securite).
    is_my_call = appel_en_cours and ope_appel_id == current_user_id

    mobile1_raw = (tc.get("Mobile1") or "").strip()
    mobile2_raw = (tc.get("Mobile2") or "").strip()
    mobile1 = mobile1_raw if is_my_call else _mask_phone(mobile1_raw)
    mobile2 = mobile2_raw if is_my_call else _mask_phone(mobile2_raw)

    # 2. Salarie vendeur :
    #    - Nom + Prenom : table Salarie
    #    - TélMob : table Salarie_Coordonnees (jointure sur IDSalarie)
    nom_vend = ""
    prenom_vend = ""
    gsm_vend_raw = ""
    if id_salarie:
        rows_sal = db_rh.query(
            "SELECT Nom, Prenom FROM Salarie WHERE IDSalarie = ?",
            (id_salarie,),
        )
        if rows_sal:
            s = rows_sal[0]
            nom_vend = (s.get("Nom") or "").strip()
            prenom_vend = _capitalize((s.get("Prenom") or "").strip())
        rows_coord = db_rh.query(
            "SELECT TélMob FROM Salarie_Coordonnees WHERE IDSalarie = ?",
            (id_salarie,),
        )
        if rows_coord:
            gsm_vend_raw = (rows_coord[0].get("TélMob") or "").strip()
    gsm_vend = gsm_vend_raw if is_my_call else _mask_phone(gsm_vend_raw)

    # 3. Panier : TK_CallSFR_Panier + SFR_OffresProvad (cross-base impossible)
    rows_panier = db_bo.query(
        """SELECT
            IDTK_CallSFR_Panier, IDOffres_SFR, Opt_TV, TYPE, portabilité,
            TypeVente, MotifAnnulation, StatutProd,
            NumPortabilité, NumPrise_RIO, NumPrise_Optique, OptChoisies
        FROM TK_CallSFR_Panier
        WHERE IDtk_CallSFR = ?
          AND ModifELEM NOT LIKE '%suppr%'""",
        (id_call_sfr,),
    )
    # Lib_Offre via SFR_OffresProvad (base adv)
    offre_ids = {_to_int(p.get("IDOffres_SFR")) for p in rows_panier}
    offre_ids.discard(0)
    offre_libs: dict[int, str] = {}
    if offre_ids:
        oids_sql = ",".join(str(i) for i in offre_ids)
        rows_off = db_adv.query(
            f"""SELECT IDOffres_SFR, Lib_Offre FROM SFR_OffresProvad
            WHERE IDOffres_SFR IN ({oids_sql})"""
        )
        for o in rows_off:
            offre_libs[_to_int(o.get("IDOffres_SFR"))] = (o.get("Lib_Offre") or "").strip()

    panier = []
    for p in rows_panier:
        id_off = _to_int(p.get("IDOffres_SFR"))
        panier.append({
            "id": _str_id(p.get("IDTK_CallSFR_Panier")),
            "id_offre": _str_id(p.get("IDOffres_SFR")),
            "lib_offre": offre_libs.get(id_off, ""),
            "type": (p.get("TYPE") or "").strip(),  # "FIBRE" / "MOBILE"
            "opt_tv": _bool(p.get("Opt_TV")),
            "portabilite": _bool(p.get("portabilité")),
            "type_vente": _to_int(p.get("TypeVente")),
            "statut_prod": _to_int(p.get("StatutProd")),
            "motif_annulation": (p.get("MotifAnnulation") or "").strip(),
            "num_portabilite": (p.get("NumPortabilité") or "").strip(),
            "num_rio": (p.get("NumPrise_RIO") or "").strip(),
            "num_prise_optique": (p.get("NumPrise_Optique") or "").strip(),
            "opt_choisies": (p.get("OptChoisies") or "").strip(),
        })

    # 4. Statuts vente disponibles (dynamique selon IDTK_Statut)
    # WinDev: ListeAjoute Non défini=0, Validé=1, Annulé=2, Num BS ajouté=3,
    # et si IDTK_Statut=15: Validé - Différé=4
    statuts_vente = [
        {"id": 0, "label": "Non défini"},
        {"id": 1, "label": "Validé"},
        {"id": 2, "label": "Annulé"},
        {"id": 3, "label": "Num BS ajouté"},
    ]
    if id_tk_statut == 15:
        statuts_vente.append({"id": 4, "label": "Validé - Différé"})

    # 5. Compteurs panier (pour pre-calculer les etats des boutons)
    nb_prod_total = len(panier)
    nb_prod_valide = sum(1 for p in panier if p["statut_prod"] == 1)
    nb_prod_annule = sum(1 for p in panier if p["statut_prod"] == 2)
    btn_valider_actif = nb_prod_valide > 0 and (nb_prod_valide + nb_prod_annule) == nb_prod_total
    btn_annuler_actif = nb_prod_total > 0 and nb_prod_annule == nb_prod_total

    return {
        "id_ticket": _str_id(id_tk_liste),
        "id_call_sfr": _str_id(id_call_sfr),
        "id_tk_statut": id_tk_statut,
        "is_cloture": _bool(tk_liste.get("cloturee")),
        "is_statut_34": id_tk_statut == 34,  # Affiche libelle special
        "is_my_call": is_my_call,  # mobile demasque ou non
        "client": {
            "civilite": _to_int(tc.get("CivilitéClient")),
            "nom": (tc.get("NomClient") or "").strip(),
            "nom_marital": (tc.get("NomMaritalClient") or "").strip(),
            "prenom": (tc.get("PrenomClient") or "").strip(),
            "nom_format": _format_nom_client(
                _to_int(tc.get("CivilitéClient")),
                tc.get("NomClient"),
                tc.get("NomMaritalClient"),
                tc.get("PrenomClient"),
            ),
            "date_naiss": _iso(tc.get("DATENAISS"))[:10],
            "dep_naiss": _to_int(tc.get("DEPNAISS")),
            "type_logement": _to_int(tc.get("TypeLogement")),  # 1=Maison, 2=Appart
            "adresse1": (tc.get("ADRESSE1") or "").strip(),
            "adresse2": (tc.get("ADRESSE2") or "").strip(),
            "cp": (tc.get("CP") or "").strip(),
            "ville": _format_ville(tc.get("VILLE") or ""),
            "email": (tc.get("adrMail") or "").strip(),
            "mobile1": mobile1,
            "mobile2": mobile2,
            "opt_rappel": _bool(tc.get("Opt_Rappel")),
            "opt_partenaire": _bool(tc.get("Opt_Partenaire")),
            "client_pro": _bool(tc.get("ClientPro")),
            "client_rs": (tc.get("ClientRS") or "").strip(),
            "client_siret": (tc.get("ClientSiret") or "").strip(),
        },
        "vendeur": {
            "id_salarie": id_salarie,
            "nom": nom_vend,
            "prenom": prenom_vend,
            "gsm": gsm_vend,
            "lib_affectation": "",  # TODO: affectationTerrainVendeur(IDSalarie)
        },
        "vente": {
            "ref_appel": (tc.get("RefAppel") or "").strip(),
            "intervention_vendeur": _bool(tc.get("InterventionVend")),
            "mobile_propose_vendeur": _bool(tc.get("MobPropoVend")),
            "info_vente": (tc.get("InfoVente") or "").strip(),
        },
        "anomalie": {
            "active": _bool(tc.get("AnomalieMobile")),
            "id_type": _to_int(tc.get("IDTK_CallSFR_TypeAnomalie")),
            "info_cplt": (tc.get("InfoCpltAnomalie") or "").strip(),
        },
        "panier": panier,
        "nb_prod_total": nb_prod_total,
        "nb_prod_valide": nb_prod_valide,
        "nb_prod_annule": nb_prod_annule,
        "btn_valider_actif": btn_valider_actif,
        "btn_annuler_actif": btn_annuler_actif,
        "statuts_vente": statuts_vente,
    }


def load_documents(id_tk_liste: int, client_pro: bool = False) -> dict:
    """Detecte les documents disponibles pour un ticket (CIN + KBIS).

    Conventions de nommage (cf. code WinDev) :
    - CIN  : <idCallSFR>_PieceIdentite.{pdf|png|jpg}  (fallback _CIN.jpg)
    - KBIS : <IDTicket>_KBIS.{pdf|png}                (uniquement si Pro)

    Retourne {cin: {url, kind}, kbis: {url, kind}}. Kind = 'pdf' ou 'image'.
    url et kind vides si rien trouve.
    """
    # On a besoin du IDtk_CallSFR pour la CIN (pas l'IDTK_Liste).
    db_bo = get_connection("ticket_bo")
    rows = db_bo.query(
        "SELECT IDtk_CallSFR FROM TK_CallSFR WHERE IDTK_Liste = ? AND ModifELEM NOT LIKE '%suppr%'",
        (id_tk_liste,),
    )
    id_call_sfr = _to_int(rows[0].get("IDtk_CallSFR")) if rows else 0

    # CIN : 3 candidats par ordre de priorite (PDF > PNG > JPG fallback _CIN.jpg)
    cin_url, cin_kind = "", ""
    if id_call_sfr:
        cin_url, cin_kind = _first_existing(
            f"{DOC_BASE_URL}/{id_call_sfr}_PieceIdentite.pdf",
            f"{DOC_BASE_URL}/{id_call_sfr}_PieceIdentite.png",
            f"{DOC_BASE_URL}/{id_call_sfr}_PieceIdentite.jpg",
            f"{DOC_BASE_URL}/{id_call_sfr}_CIN.jpg",
        )

    # KBIS : 2 candidats (PDF > PNG)
    kbis_url, kbis_kind = "", ""
    if client_pro:
        kbis_url, kbis_kind = _first_existing(
            f"{DOC_BASE_URL}/{id_tk_liste}_KBIS.pdf",
            f"{DOC_BASE_URL}/{id_tk_liste}_KBIS.png",
        )

    return {
        "cin": {"url": cin_url, "kind": cin_kind},
        "kbis": {"url": kbis_url, "kind": kbis_kind},
    }


def load_lettre_resil(id_tk_liste: int, id_panier: int) -> dict:
    """Detecte la Lettre de resiliation pour une ligne de panier donnee.

    Convention : <IDTicket>_<IDPanier>_LettreResil.{pdf|png}
    """
    url, kind = _first_existing(
        f"{DOC_BASE_URL}/{id_tk_liste}_{id_panier}_LettreResil.pdf",
        f"{DOC_BASE_URL}/{id_tk_liste}_{id_panier}_LettreResil.png",
    )
    return {"url": url, "kind": kind}


def _sql_str(s: Any) -> str:
    """Escape un texte pour interpolation SQL HFSQL : double les simple quotes."""
    if s is None:
        return ""
    return str(s).replace("'", "''")


def _sql_now() -> str:
    """Date+Heure HFSQL compact pour ModifDate ('YYYYMMDDHHMMSS')."""
    from datetime import datetime as _dt
    return _dt.now().strftime("%Y%m%d%H%M%S")


def _sql_bool(b: Any) -> int:
    return 1 if _bool(b) else 0


def save_vente_infos(id_tk_liste: int, payload: dict) -> dict:
    """UPDATE TK_CallSFR avec les infos client + vente + anomalie modifiees.

    Transposition du bouton "Enregistrer les infos client et vente" WinDev.
    Match avec TK_CallSFR via IDTK_Liste.
    """
    db_bo = get_connection("ticket_bo")
    c = payload.get("client", {}) or {}
    v = payload.get("vente", {}) or {}
    a = payload.get("anomalie", {}) or {}
    now_wd = _sql_now()

    sql = f"""UPDATE TK_CallSFR SET
        CivilitéClient = {_to_int(c.get('civilite'))},
        NomClient = '{_sql_str(c.get('nom'))}',
        NomMaritalClient = '{_sql_str(c.get('nom_marital'))}',
        PrenomClient = '{_sql_str(c.get('prenom'))}',
        DATENAISS = '{_sql_str(_dates_to_compact(c.get('date_naiss')))}',
        DEPNAISS = {_to_int(c.get('dep_naiss'))},
        TypeLogement = {_to_int(c.get('type_logement'))},
        ADRESSE1 = '{_sql_str(c.get('adresse1'))}',
        ADRESSE2 = '{_sql_str(c.get('adresse2'))}',
        CP = '{_sql_str(c.get('cp'))}',
        VILLE = '{_sql_str(c.get('ville'))}',
        adrMail = '{_sql_str(c.get('email'))}',
        InfoVente = '{_sql_str(v.get('info_vente'))}',
        RefAppel = '{_sql_str(v.get('ref_appel'))}',
        InterventionVend = {1 if _bool(v.get('intervention_vendeur')) else 2},
        MobPropoVend = {1 if _bool(v.get('mobile_propose_vendeur')) else 2},
        AnomalieMobile = {_sql_bool(a.get('active'))},
        IDTK_CallSFR_TypeAnomalie = {_to_int(a.get('id_type'))},
        InfoCpltAnomalie = '{_sql_str(a.get('info_cplt'))}',
        ModifDate = '{now_wd}'
    WHERE IDTK_Liste = {_to_int(id_tk_liste)}
      AND ModifELEM NOT LIKE '%suppr%'"""
    db_bo.query(sql)
    return {"ok": True}


def save_offre(id_panier: int, payload: dict) -> dict:
    """UPDATE TK_CallSFR_Panier avec les modifs de la ligne d'offre.

    Transposition du bouton "Enregistrer les modifs Offre" WinDev.
    """
    db_bo = get_connection("ticket_bo")
    now_wd = _sql_now()

    sql = f"""UPDATE TK_CallSFR_Panier SET
        portabilité = {_sql_bool(payload.get('portabilite'))},
        NumPortabilité = '{_sql_str(payload.get('num_portabilite'))}',
        NumPrise_RIO = '{_sql_str(payload.get('num_rio'))}',
        TypeVente = {_to_int(payload.get('type_vente'))},
        StatutProd = {_to_int(payload.get('statut_prod'))},
        NumPrise_Optique = '{_sql_str(payload.get('num_prise_optique'))}',
        OptChoisies = '{_sql_str(payload.get('opt_choisies'))}',
        ModifDate = '{now_wd}'
    WHERE IDTK_CallSFR_Panier = {_to_int(id_panier)}"""
    db_bo.query(sql)
    return {"ok": True}


def _dates_to_compact(s: str | None) -> str:
    """ISO 'YYYY-MM-DD' -> compact 'YYYYMMDD'. Vide si non parsable."""
    if not s:
        return ""
    s = str(s).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:4] + s[5:7] + s[8:10]
    if len(s) == 8 and s.isdigit():
        return s
    return ""


def load_panier_ligne_image(id_panier: int) -> str:
    """Charge l'image TestEligibilite d'une ligne de panier (FIBRE uniquement).

    Renvoie une data URL base64 ou "" si pas d'image / non FIBRE.
    Appel separe pour eviter de charger toutes les images dans la fiche.
    """
    db_bo = get_connection("ticket_bo")
    rows = db_bo.query(
        """SELECT TYPE, TestEligibilité FROM TK_CallSFR_Panier
        WHERE IDTK_CallSFR_Panier = ?""",
        (id_panier,),
    )
    if not rows:
        return ""
    r = rows[0]
    if (r.get("TYPE") or "").strip().upper() != "FIBRE":
        return ""
    return _safe_b64_data_url(r.get("TestEligibilité"))
