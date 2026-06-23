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
from datetime import datetime
from typing import Any

from app.core.database import get_connection
from app.intranets.call.fibre.services.tickets import (
    _capitalize,
    _format_nom_client,
    _format_ville,
    _iso,
    _load_offres_ref,
    _str_id,
    _to_int,
)


def _iso_date(v: Any) -> str:
    """HFSQL Date (compact 8 chars) ou DateTime (>= 14 chars) -> 'YYYY-MM-DD'.

    Le champ DATENAISS de TK_CallSFR est de type 'Date' (pas DateTime), donc
    stocke sous 8 chars compact "19910405". La fonction _iso() de tickets.py
    ne gere que les formats >= 14 chars -> renvoyait "19910405" tel quel et
    le frontend (input type="date") refusait la valeur.
    """
    if not v:
        return ""
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    if not s or s.startswith("0000"):
        return ""
    # Compact 8 chars OU plus (Date / DateTime HFSQL)
    if len(s) >= 8 and s[:8].isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    # ISO "1991-04-05..."
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return ""


DOC_BASE_URL = "https://rest.omaya.fr/DocOmaya"


# Cache module : referentiel TK_CallSFR_TypeAnomalie (motifs Vente differee).
_TYPE_ANOMALIE_CACHE: list[dict] | None = None
_TYPE_ANOMALIE_AT: float = 0.0
_TYPE_ANOMALIE_TTL = 600.0  # 10 minutes


def _load_motifs_anomalie() -> list[dict]:
    """Charge le referentiel TK_CallSFR_TypeAnomalie (base ticket_bo).

    Cache 10min. Retourne une liste [{id, label}, ...] triee par IDTK_CallSFR_TypeAnomalie.
    """
    import time as _time
    global _TYPE_ANOMALIE_CACHE, _TYPE_ANOMALIE_AT
    now = _time.monotonic()
    if _TYPE_ANOMALIE_CACHE is not None and now - _TYPE_ANOMALIE_AT < _TYPE_ANOMALIE_TTL:
        return _TYPE_ANOMALIE_CACHE
    db_bo = get_connection("ticket_bo")
    rows = db_bo.query(
        """SELECT IDTK_CallSFR_TypeAnomalie, LibTypeAnomalie
        FROM TK_CallSFR_TypeAnomalie
        WHERE ModifELEM NOT LIKE '%suppr%'
        ORDER BY IDTK_CallSFR_TypeAnomalie ASC"""
    )
    out = [
        {
            "id": _to_int(r.get("IDTK_CallSFR_TypeAnomalie")),
            "label": (r.get("LibTypeAnomalie") or "").strip(),
        }
        for r in rows
    ]
    _TYPE_ANOMALIE_CACHE = out
    _TYPE_ANOMALIE_AT = now
    return out


# Cache des HEAD HTTP pour les URLs DocOmaya. TTL 60s : evite de refaire
# 4 HEAD sequentiels a chaque ouverture de fiche pour un meme ticket.
import time as _time_mod
_URL_HEAD_CACHE: dict[str, tuple[bool, float]] = {}
_URL_HEAD_TTL = 60.0


def _url_exists(url: str, timeout: float = 1.5) -> bool:
    """HEAD HTTP : True si le fichier existe (HTTP 200/2xx).

    Cache 60s pour eviter les HEAD repetes. Timeout court (1.5s) car les
    docs sont sur le meme serveur OVH -> si > 1.5s c'est qu'ils n'existent
    pas (ou que le serveur lag, on prefere echouer vite).
    """
    now = _time_mod.monotonic()
    cached = _URL_HEAD_CACHE.get(url)
    if cached is not None and now - cached[1] < _URL_HEAD_TTL:
        return cached[0]
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            exists = 200 <= resp.status < 300
    except Exception:
        exists = False
    _URL_HEAD_CACHE[url] = (exists, now)
    return exists


def _first_existing(*urls: str) -> tuple[str, str]:
    """Retourne (url, kind) du premier fichier existant.

    Les HEAD sont faits en PARALLELE pour ne pas additionner les timeouts.
    On respecte l'ordre de priorite : on retourne le premier URL existant
    selon l'ordre des args (PDF avant PNG avant JPG).
    Si aucun n'existe -> ("", "").
    """
    from concurrent.futures import ThreadPoolExecutor
    valid_urls = [u for u in urls if u]
    if not valid_urls:
        return "", ""
    with ThreadPoolExecutor(max_workers=min(len(valid_urls), 4)) as pool:
        results = list(pool.map(_url_exists, valid_urls))
    for url, exists in zip(valid_urls, results):
        if exists:
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

    Perf : on parallelise les queries independantes (chaque query HFSQL
    spawn un subprocess Dll_ODBC.exe + bloque le thread Python ~150ms).
    On tient en 2 vagues paralleles (~2 x 150ms ~= 300ms) :
    - Vague 1 : TK_Liste + TK_CallSFR + referentiels caches (motifs, offres)
    - Vague 2 : Panier + Salarie + Salarie_Coordonnees (3 queries paralleles)
    Le referentiel SFR_OffresProvad est mis en cache -> plus de 3e vague
    (avant : l'offre lib_offre etait une requete sequentielle apres la vague 2).
    """
    from concurrent.futures import ThreadPoolExecutor
    db_ticket = get_connection("ticket")
    db_bo = get_connection("ticket_bo")
    db_rh = get_connection("rh")

    # Vague 1 : TK_Liste + TK_CallSFR en parallele (2 queries, bases differentes)
    sql_liste = """SELECT
            IDTK_Liste AS id_tk_liste,
            IDTK_Statut AS id_tk_statut,
            OPCrea AS op_crea,
            Cloturée AS cloturee,
            DateCloture AS date_cloture
        FROM TK_Liste
        WHERE IDTK_Liste = ?"""
    sql_call = """SELECT
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
          AND ModifELEM NOT LIKE '%suppr%'"""
    # Vague 1 : TK_Liste + TK_CallSFR + referentiels (motifs, offres) en parallele.
    # Les referentiels sont mis en cache (10min) donc le 1er appel paie ~150ms,
    # les suivants sont instantanes (pas de subprocess).
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_liste = pool.submit(db_ticket.query, sql_liste, (id_tk_liste,))
        f_call = pool.submit(db_bo.query, sql_call, (id_tk_liste,))
        f_motifs = pool.submit(_load_motifs_anomalie)
        f_offres = pool.submit(_load_offres_ref)
        rows_liste = f_liste.result()
        rows_call = f_call.result()
        motifs_anomalie = f_motifs.result()
        offre_libs = f_offres.result()
    if not rows_liste:
        return {"error": "Ticket introuvable"}
    tk_liste = rows_liste[0]
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

    # Vague 2 : Salarie + Salarie_Coordonnees + Panier en parallele (3 queries,
    # 2 bases differentes). Toutes independantes -> 1 seul round-trip.
    # NB : pas de JOIN SQL (le bridge encapsule chaque source dans un sous-objet
    # JSON -> on joint en Python, comme partout dans le code).
    nom_vend = ""
    prenom_vend = ""
    gsm_vend_raw = ""
    ope_en_cours_nom = ""
    # Si un AUTRE ope a un appel en cours sur ce ticket, on recupere son nom
    # (pour la boite d'alerte affichee a l'ouverture de la fiche).
    need_ope = appel_en_cours and ope_appel_id and not is_my_call
    with ThreadPoolExecutor(max_workers=4) as pool:
        f_sal = pool.submit(
            db_rh.query, "SELECT Nom, Prenom FROM Salarie WHERE IDSalarie = ?", (id_salarie,)
        ) if id_salarie else None
        f_coord = pool.submit(
            db_rh.query, "SELECT TélMob FROM Salarie_Coordonnees WHERE IDSalarie = ?", (id_salarie,)
        ) if id_salarie else None
        f_ope = pool.submit(
            db_rh.query, "SELECT Nom, Prenom FROM Salarie WHERE IDSalarie = ?", (ope_appel_id,)
        ) if need_ope else None
        f_panier = pool.submit(
            db_bo.query,
            """SELECT
                IDTK_CallSFR_Panier, IDOffres_SFR, Opt_TV, TYPE, portabilité,
                TypeVente, MotifAnnulation, StatutProd,
                NumPortabilité, NumPrise_RIO, NumPrise_Optique, OptChoisies
            FROM TK_CallSFR_Panier
            WHERE IDtk_CallSFR = ?
              AND ModifELEM NOT LIKE '%suppr%'""",
            (id_call_sfr,),
        )
        rows_sal = f_sal.result() if f_sal else []
        rows_coord = f_coord.result() if f_coord else []
        rows_ope = f_ope.result() if f_ope else []
        rows_panier = f_panier.result()
    if rows_sal:
        s = rows_sal[0]
        nom_vend = (s.get("Nom") or "").strip()
        prenom_vend = _capitalize((s.get("Prenom") or "").strip())
    if rows_coord:
        gsm_vend_raw = (rows_coord[0].get("TélMob") or "").strip()
    if rows_ope:
        o = rows_ope[0]
        ope_en_cours_nom = f"{(o.get('Nom') or '').strip()} {_capitalize((o.get('Prenom') or '').strip())}".strip()
    gsm_vend = gsm_vend_raw if is_my_call else _mask_phone(gsm_vend_raw)
    # Lib_Offre via le referentiel SFR_OffresProvad mis en cache (vague 1).

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
        "appel_en_cours": appel_en_cours,  # un ope a un appel en cours sur ce ticket
        "ope_en_cours_nom": ope_en_cours_nom,  # nom de l'ope en ligne (si autre que moi)
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
            "date_naiss": _iso_date(tc.get("DATENAISS")),
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
        "motifs_anomalie": motifs_anomalie,
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


# --- Phase 3 : verrou ope + actions panier --------------------------------

def peek_verrou(id_tk_liste: int) -> dict:
    """Renvoie l'etat actuel du verrou ope sur un ticket :
    {appel_en_cours, ope_appel_id, ope_appel_nom, date_h_appel,
     duree_minutes_si_en_cours}.

    Permet au frontend d'afficher la bonne confirmation avant prise d'appel.
    """
    from datetime import datetime as _dt
    db_bo = get_connection("ticket_bo")
    db_rh = get_connection("rh")
    rows = db_bo.query(
        """SELECT IDtk_CallSFR, AppelEnCours, OpéAppel, DateH_Appel
        FROM TK_CallSFR
        WHERE IDTK_Liste = ? AND ModifELEM NOT LIKE '%suppr%'""",
        (id_tk_liste,),
    )
    if not rows:
        return {"error": "Ticket introuvable"}
    r = rows[0]
    appel_en_cours = _bool(r.get("AppelEnCours"))
    ope_appel_id = _to_int(r.get("OpéAppel"))
    date_h_appel_iso = _iso(r.get("DateH_Appel"))
    nom_ope = ""
    if ope_appel_id:
        rs = db_rh.query(
            "SELECT Nom, Prenom FROM Salarie WHERE IDSalarie = ?",
            (ope_appel_id,),
        )
        if rs:
            nom_ope = f"{(rs[0].get('Nom') or '').strip()} {_capitalize((rs[0].get('Prenom') or '').strip())}".strip()
    # Duree depuis prise d'appel (en minutes/secondes)
    minutes = 0
    seconds = 0
    dt = _parse_dt(r.get("DateH_Appel"))
    if dt is not None:
        delta = _dt.now() - dt
        total = max(0, int(delta.total_seconds()))
        minutes = total // 60
        seconds = total % 60
    return {
        "appel_en_cours": appel_en_cours,
        "ope_appel_id": ope_appel_id,
        "ope_appel_nom": nom_ope,
        "date_h_appel": date_h_appel_iso,
        "duree_minutes": minutes,
        "duree_secondes": seconds,
    }


def _parse_dt(v: Any):
    """Wrapper local pour eviter une import circulaire avec tickets.py."""
    from app.intranets.call.fibre.services.tickets import _parse_dt as _pdt
    return _pdt(v)


def prendre_appel(id_tk_liste: int, user_id: int, force: bool = False) -> dict:
    """Pose le verrou ope sur un ticket.

    Si `force=False` et un autre ope a deja le verrou (ou a raccroche
    recemment), renvoie {needs_confirm: True, peek: {...}} pour que le
    frontend affiche la confirmation. Si force=True, ecrase.

    Logique WinDev :
    - UPDATE TK_CallSFR : AppelEnCours=1, OpéAppel=user, DateH_Appel=now
    - UPDATE TK_CallSFR : DateDeb_PriseEnCharge=now si vide
    - Envoi SMS au vendeur "Attention, vous allez bientot recevoir un appel..."
    """
    from datetime import datetime as _dt
    db_bo = get_connection("ticket_bo")
    db_rh = get_connection("rh")

    rows = db_bo.query(
        """SELECT IDtk_CallSFR, IDSalarie, AppelEnCours, OpéAppel, DateH_Appel,
            DateDeb_PriseEnCharge, NomClient, NomMaritalClient, PrenomClient
        FROM TK_CallSFR
        WHERE IDTK_Liste = ? AND ModifELEM NOT LIKE '%suppr%'""",
        (id_tk_liste,),
    )
    if not rows:
        return {"error": "Ticket introuvable"}
    r = rows[0]
    id_call_sfr = _to_int(r.get("IDtk_CallSFR"))
    id_salarie = _to_int(r.get("IDSalarie"))

    # Si pas force et un autre ope a le verrou : demande confirmation
    if not force:
        appel_en_cours = _bool(r.get("AppelEnCours"))
        ope_appel_id = _to_int(r.get("OpéAppel"))
        date_h_appel = _parse_dt(r.get("DateH_Appel"))
        # Confirmation obligatoire si verrou actif par un autre, ou si trace
        # de prise d'appel par un autre (meme s'il a raccroche).
        if (appel_en_cours and ope_appel_id and ope_appel_id != user_id) or (
            not appel_en_cours and date_h_appel is not None and ope_appel_id != user_id
        ):
            peek = peek_verrou(id_tk_liste)
            return {"needs_confirm": True, "peek": peek}

    # UPDATE TK_CallSFR : pose le verrou
    now_wd = _sql_now()
    db_bo.query(
        f"""UPDATE TK_CallSFR SET
            AppelEnCours = 1,
            OpéAppel = {_to_int(user_id)},
            DateH_Appel = '{now_wd}',
            ModifDate = '{now_wd}'
        WHERE IDtk_CallSFR = {id_call_sfr}"""
    )
    # DateDeb_PriseEnCharge si vide
    if not _parse_dt(r.get("DateDeb_PriseEnCharge")):
        db_bo.query(
            f"""UPDATE TK_CallSFR SET
                DateDeb_PriseEnCharge = '{now_wd}',
                ModifDate = '{now_wd}'
            WHERE IDtk_CallSFR = {id_call_sfr}"""
        )

    # Envoi SMS au vendeur "Attention, vous allez bientot recevoir un appel..."
    sms_result = _envoyer_sms_vendeur_prise_appel(
        db_rh, id_salarie, user_id,
        r.get("NomClient"), r.get("NomMaritalClient"), r.get("PrenomClient"),
    )
    return {"ok": True, "sms": sms_result}


def lacher_appel(id_tk_liste: int) -> dict:
    """Libere le verrou ope. UPDATE AppelEnCours=0, DateFin_PriseEnCharge=now si vide."""
    db_bo = get_connection("ticket_bo")
    rows = db_bo.query(
        "SELECT IDtk_CallSFR, DateFin_PriseEnCharge FROM TK_CallSFR WHERE IDTK_Liste = ?",
        (id_tk_liste,),
    )
    if not rows:
        return {"error": "Ticket introuvable"}
    r = rows[0]
    id_call_sfr = _to_int(r.get("IDtk_CallSFR"))
    now_wd = _sql_now()
    sets = ["AppelEnCours = 0", f"ModifDate = '{now_wd}'"]
    if not _parse_dt(r.get("DateFin_PriseEnCharge")):
        sets.append(f"DateFin_PriseEnCharge = '{now_wd}'")
    db_bo.query(
        f"""UPDATE TK_CallSFR SET {', '.join(sets)}
        WHERE IDtk_CallSFR = {id_call_sfr}"""
    )
    return {"ok": True}


def _envoyer_sms_vendeur_prise_appel(
    db_rh, id_vendeur: int, id_ope: int,
    nom_client: str, nom_marital: str, prenom_client: str,
) -> str:
    """Envoie le SMS "Attention, vous allez bientot recevoir un appel...".

    Cherche le GSM du vendeur via Salarie_Coordonnees, puis appelle envoi_sms().
    """
    from app.shared.notifications.sms import envoi_sms
    # GSM vendeur
    rows_v = db_rh.query(
        "SELECT TélMob FROM Salarie_Coordonnees WHERE IDSalarie = ?",
        (id_vendeur,),
    )
    gsm = ""
    if rows_v:
        gsm = (rows_v[0].get("TélMob") or "").strip()
    gsm = "".join(c for c in gsm if c.isdigit() or c == "+")
    if not gsm:
        return "Pas de GSM vendeur (SMS non envoye)"
    # Nom de l'ope (signataire du SMS)
    rows_op = db_rh.query(
        "SELECT Nom, Prenom FROM Salarie WHERE IDSalarie = ?",
        (id_ope,),
    )
    nom_ope = ""
    if rows_op:
        nom_ope = f"{(rows_op[0].get('Nom') or '').strip()} {_capitalize((rows_op[0].get('Prenom') or '').strip())}".strip()
    nom_clt = _format_nom_client_sms(nom_client, nom_marital, prenom_client)
    texte = f"Attention, vous allez bientot recevoir un appel du CALL pour votre client {nom_clt}."
    return envoi_sms(texte, gsm, emetteur="Omaya-Call")


def _envoyer_sms_vendeur_renvoi_complement(
    db_rh, id_vendeur: int,
    nom_client: str, nom_marital: str, prenom_client: str,
) -> str:
    from app.shared.notifications.sms import envoi_sms
    rows_v = db_rh.query(
        "SELECT TélMob FROM Salarie_Coordonnees WHERE IDSalarie = ?",
        (id_vendeur,),
    )
    gsm = "".join(c for c in (rows_v[0].get("TélMob") or "") if c.isdigit() or c == "+") if rows_v else ""
    if not gsm:
        return "Pas de GSM vendeur"
    nom_clt = _format_nom_client_sms(nom_client, nom_marital, prenom_client)
    texte = f"Attention, votre panier pour le client {nom_clt} est renvoye pour complement."
    return envoi_sms(texte, gsm, emetteur="Omaya-Call")


def _envoyer_sms_vendeur_renvoi_lettre_resil(
    db_rh, id_vendeur: int,
    nom_client: str, nom_marital: str, prenom_client: str,
) -> str:
    from app.shared.notifications.sms import envoi_sms
    rows_v = db_rh.query(
        "SELECT TélMob FROM Salarie_Coordonnees WHERE IDSalarie = ?",
        (id_vendeur,),
    )
    gsm = "".join(c for c in (rows_v[0].get("TélMob") or "") if c.isdigit() or c == "+") if rows_v else ""
    if not gsm:
        return "Pas de GSM vendeur"
    nom_clt = _format_nom_client_sms(nom_client, nom_marital, prenom_client)
    texte = f"Attention, votre panier pour le client {nom_clt} est renvoye car il manque la lettre de resiliation."
    return envoi_sms(texte, gsm, emetteur="Omaya-Call")


def _envoyer_sms_vendeur_validation_degroupage(
    db_rh, id_vendeur: int,
    nom_client: str, nom_marital: str, prenom_client: str,
) -> str:
    from app.shared.notifications.sms import envoi_sms
    rows_v = db_rh.query(
        "SELECT TélMob FROM Salarie_Coordonnees WHERE IDSalarie = ?",
        (id_vendeur,),
    )
    gsm = "".join(c for c in (rows_v[0].get("TélMob") or "") if c.isdigit() or c == "+") if rows_v else ""
    if not gsm:
        return "Pas de GSM vendeur"
    nom_clt = _format_nom_client_sms(nom_client, nom_marital, prenom_client)
    texte = f"Le CALL vient d'envoyer le panier degroupe SFR pour votre client {nom_clt}."
    return envoi_sms(texte, gsm, emetteur="Omaya-Call")


def _format_nom_client_sms(nom: str, nom_marital: str, prenom: str) -> str:
    """'NOM ep MARITAL Prenom' (sans accent, pour SMS)."""
    parts = [(nom or "").strip()]
    if (nom_marital or "").strip():
        parts.append(f"ep {nom_marital.strip()}")
    parts.append(_capitalize((prenom or "").strip()))
    return " ".join(p for p in parts if p)


# --- Actions panier -------------------------------------------------------

def annuler_ligne_panier(id_panier: int, motifs: list[str], precisions: str) -> dict:
    """UPDATE TK_CallSFR_Panier : StatutProd=2 + MotifAnnulation (concat).

    Transposition Popup1. Au moins 1 motif coche OU des informations
    complementaires requis (sinon renvoie 400).
    """
    has_precisions = bool((precisions or "").strip())
    if not motifs and not has_precisions:
        return {"error": "Merci d'ajouter un motif ou des informations complementaires"}
    parts = []
    if motifs:
        parts.append("Motif(s) d'annulation :\n" + "\n".join(f"  - {m}" for m in motifs))
    if has_precisions:
        parts.append(f"Informations complementaires:\n{precisions.strip()}")
    motif_str = "\n".join(parts)
    db_bo = get_connection("ticket_bo")
    now_wd = _sql_now()
    db_bo.query(
        f"""UPDATE TK_CallSFR_Panier SET
            StatutProd = 2,
            MotifAnnulation = '{_sql_str(motif_str)}',
            ModifDate = '{now_wd}'
        WHERE IDTK_CallSFR_Panier = {_to_int(id_panier)}"""
    )
    return {"ok": True}


def _action_vente_finale(
    id_tk_liste: int,
    payload: dict,
    new_statut: int,
    send_sms_renvoi: bool = False,
    send_sms_si_degroupage: bool = False,
    send_sms_lettre_resil: bool = False,
    extra_info_vente: str = "",
) -> dict:
    """Logique commune AnnulVente / ValideVente / RenvoiPanier / RenvoiLettreResil.

    1. save_vente_infos (UPDATE TK_CallSFR) si payload fourni
    2. UPDATE TK_Liste IDTK_Statut = new_statut
    2b. Append `extra_info_vente` a TK_CallSFR.InfoVente si fourni (note de renvoi)
    3. Si verrou actif : libere (AppelEnCours=0, DateFin_PriseEnCharge=now)
    4. SMS si demande (renvoi complement / validation degroupage / renvoi lettre resil)
    """
    db_bo = get_connection("ticket_bo")
    db_ticket = get_connection("ticket")
    db_rh = get_connection("rh")
    now_wd = _sql_now()

    # 1. Save infos vente (si payload fourni — RenvoiPanier ne save pas)
    if payload:
        save_vente_infos(id_tk_liste, payload)

    # Recupere infos pour le SMS et le statut anterieur
    rows_call = db_bo.query(
        """SELECT IDtk_CallSFR, IDSalarie, AppelEnCours, InfoVente,
            NomClient, NomMaritalClient, PrenomClient
        FROM TK_CallSFR WHERE IDTK_Liste = ?""",
        (id_tk_liste,),
    )
    if not rows_call:
        return {"error": "Ticket introuvable"}
    r_call = rows_call[0]
    id_call_sfr = _to_int(r_call.get("IDtk_CallSFR"))
    id_salarie = _to_int(r_call.get("IDSalarie"))
    appel_en_cours = _bool(r_call.get("AppelEnCours"))
    nom_client = r_call.get("NomClient") or ""
    nom_marital = r_call.get("NomMaritalClient") or ""
    prenom_client = r_call.get("PrenomClient") or ""

    # Recupere statut TK_Liste avant pour SMS degroupage
    rows_liste = db_ticket.query(
        "SELECT IDTK_Statut FROM TK_Liste WHERE IDTK_Liste = ?",
        (id_tk_liste,),
    )
    statut_avant = _to_int(rows_liste[0].get("IDTK_Statut")) if rows_liste else 0

    # 2. UPDATE TK_Liste IDTK_Statut
    db_ticket.query(
        f"""UPDATE TK_Liste SET
            IDTK_Statut = {new_statut},
            ModifDate = '{now_wd}'
        WHERE IDTK_Liste = {_to_int(id_tk_liste)}"""
    )

    # 2b. Append d'une note dans InfoVente (ex: renvoi lettre de resil)
    if extra_info_vente:
        cur_info = (r_call.get("InfoVente") or "").strip()
        new_info = f"{cur_info}\n{extra_info_vente}".strip() if cur_info else extra_info_vente
        db_bo.query(
            f"""UPDATE TK_CallSFR SET
                InfoVente = '{_sql_str(new_info)}',
                ModifDate = '{now_wd}'
            WHERE IDtk_CallSFR = {id_call_sfr}"""
        )

    # 3. Libere le verrou si actif
    if appel_en_cours:
        db_bo.query(
            f"""UPDATE TK_CallSFR SET
                AppelEnCours = 0,
                DateFin_PriseEnCharge = '{now_wd}',
                ModifDate = '{now_wd}'
            WHERE IDtk_CallSFR = {id_call_sfr}"""
        )

    # 4. SMS optionnel
    sms_result = ""
    if send_sms_renvoi:
        sms_result = _envoyer_sms_vendeur_renvoi_complement(
            db_rh, id_salarie, nom_client, nom_marital, prenom_client,
        )
    elif send_sms_lettre_resil:
        sms_result = _envoyer_sms_vendeur_renvoi_lettre_resil(
            db_rh, id_salarie, nom_client, nom_marital, prenom_client,
        )
    elif send_sms_si_degroupage and statut_avant == 34:
        sms_result = _envoyer_sms_vendeur_validation_degroupage(
            db_rh, id_salarie, nom_client, nom_marital, prenom_client,
        )

    return {"ok": True, "sms": sms_result}


def annuler_vente(id_tk_liste: int, payload: dict) -> dict:
    """Confirme l'annulation de toute la vente (POPUP_AnnulVente WinDev).

    -> TK_Liste IDTK_Statut = 14 + save vente + lacher verrou. Pas de SMS.
    """
    return _action_vente_finale(id_tk_liste, payload, new_statut=14)


def valider_vente(id_tk_liste: int, payload: dict) -> dict:
    """Confirme la validation du panier (POPUP_ValideVente WinDev).

    -> TK_Liste IDTK_Statut = 15 + save vente + lacher verrou + SMS si
    le statut anterieur etait 34 (panier degroupe).
    """
    return _action_vente_finale(
        id_tk_liste, payload, new_statut=15, send_sms_si_degroupage=True,
    )


def renvoyer_complement(id_tk_liste: int) -> dict:
    """Renvoie le panier pour complement (POPUP_RenvoiPanier WinDev).

    -> TK_Liste IDTK_Statut = 28 + lacher verrou + SMS vendeur (toujours).
    Pas de save vente (le code WinDev ne save rien d'autre que le statut).
    """
    return _action_vente_finale(
        id_tk_liste, payload={}, new_statut=28, send_sms_renvoi=True,
    )


def renvoyer_lettre_resil(id_tk_liste: int, user_nom: str, user_prenom: str) -> dict:
    """Bouton 'Renvoyer pour lettre de resil' (FIBRE, offres sans portabilite).

    Append InfoVente "Ticket renvoye pour lettre de resil le {now} par {user}",
    TK_Liste statut=28, lacher verrou, SMS specifique au vendeur.
    """
    note = (
        f"Ticket renvoye pour lettre de resil le "
        f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
        f"par {user_nom} {_capitalize(user_prenom)}"
    )
    return _action_vente_finale(
        id_tk_liste, payload={}, new_statut=28,
        send_sms_lettre_resil=True, extra_info_vente=note,
    )


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
