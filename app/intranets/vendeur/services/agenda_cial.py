"""
Services agenda commercial : listing RDV + recherche commerciaux.

Tables AgendaCommercial + AgendaCommercial_Catégorie dans Bdd_Omaya_ADV.
Jointure sur TK_Liste (Bdd_Omaya_Ticket) pour récupérer l'info client,
puis sur TK_Call ou TK_CallSFR (Bdd_Omaya_Ticket_BO) selon IDTK_TypeDemande.
"""

import base64
import struct

from app.core.database import get_connection


def _to_int(v) -> int:
    if v is None or v == "":
        return 0
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            pass
        try:
            raw = base64.b64decode(v)
            if len(raw) == 8:
                return struct.unpack("<q", raw)[0]
            if len(raw) == 4:
                return struct.unpack("<i", raw)[0]
        except Exception:
            pass
    return 0


def _winrgb_to_hex(color_int: int | None) -> str:
    """
    Convertit un entier couleur WinDev (format BGR : 0x00BBGGRR) en hex #RRGGBB.
    """
    n = int(color_int or 0)
    r = n & 0xFF
    g = (n >> 8) & 0xFF
    b = (n >> 16) & 0xFF
    return f"#{r:02X}{g:02X}{b:02X}"


def _today_windev() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d")


def rechercher_commerciaux(
    id_salarie_user: int,
    search: str,
    acces_global: bool = False,
    is_resp: bool = False,
) -> list[dict]:
    """
    Recherche les commerciaux : salariés actifs accessibles au user qui
    répondent à UNE de ces conditions :
      - Ont le droit AgendaCial
      - Ont au moins 1 RDV dans AgendaCommercial (ModifELEM <> 'suppr')

    Respecte le scope d'accès (ProdRezo / manager / user simple).
    """
    from app.intranets.vendeur.services.cooptation import rechercher_vendeurs

    # 1. Étape : obtenir les salariés accessibles (sans filtre nom global ici,
    # mais on réutilise le scope de droits existant pour restreindre)
    base_results = rechercher_vendeurs(
        id_salarie_user, search, acces_global=acces_global, is_resp=is_resp
    )
    if not base_results:
        return []

    ids_accessibles = {int(r["id_salarie"]) for r in base_results}

    # 2. Obtenir les salariés ayant le droit AgendaCial
    db_rh = get_connection("rh")
    droit_rows = db_rh.query(
        """SELECT DISTINCT sd.IDSalarie
        FROM salarie_droitAccès sd
        INNER JOIN TypeDroitAccès td ON td.IDTypeDroitAccès = sd.IDTypeDroitAccès
        WHERE td.CodeInterne = 'AgendaCial'
          AND td.FDV = 1
          AND sd.DroitActif = 1
          AND sd.ModifELEM NOT LIKE '%suppr%'"""
    )
    ids_avec_droit = {_to_int(r.get("IDSalarie")) for r in droit_rows}
    ids_avec_droit.discard(0)

    # 3. Obtenir les salariés ayant au moins 1 RDV dans AgendaCommercial
    db_adv = get_connection("adv")
    rdv_rows = db_adv.query(
        """SELECT DISTINCT IDSalarie FROM AgendaCommercial
        WHERE ModifELEM <> 'suppr'"""
    )
    ids_avec_rdv = {_to_int(r.get("IDSalarie")) for r in rdv_rows}
    ids_avec_rdv.discard(0)

    # 4. Intersection : salariés accessibles ET (avec droit OU avec RDV)
    ids_eligibles = ids_accessibles & (ids_avec_droit | ids_avec_rdv)

    return [r for r in base_results if int(r["id_salarie"]) in ids_eligibles]


def lister_rdvs_cial(id_commercial: int, date_from: str, date_to: str) -> list[dict]:
    """
    Liste des RDV de l'agenda commercial d'un commercial entre deux dates.
    date_from / date_to : format YYYYMMDD.
    """
    db_adv = get_connection("adv")

    # DateDébut est Date+Heure stocké en ISO "YYYY-MM-DDT..."
    # On utilise LEFT(DateDébut, 8) qui retourne YYYYMMDD (confirmé fonctionnel)
    rows = db_adv.query(
        """SELECT
            a.IDAgendaCommercial, a.Titre, a.Contenu, a.InfoCompl,
            a.DateDébut, a.DateFin, a.IDTK_Liste, a.OPCrea,
            a.IDAgendaCommercial_Catégorie,
            c.Lib_Catégorie, c.Couleur, c.IdCvStatut
        FROM AgendaCommercial a
        INNER JOIN AgendaCommercial_Catégorie c
            ON c.IDAgendaCommercial_Catégorie = a.IDAgendaCommercial_Catégorie
        WHERE a.IDSalarie = ?
          AND LEFT(a.DateDébut, 8) >= ?
          AND LEFT(a.DateDébut, 8) <= ?
          AND a.ModifELEM <> 'suppr'
        ORDER BY a.DateDébut ASC""",
        (id_commercial, date_from, date_to),
    )

    if not rows:
        return []

    # Récupérer les infos TK_Liste pour savoir quel TK_Call/TK_CallSFR interroger
    tk_liste_ids = {_to_int(r.get("IDTK_Liste")) for r in rows}
    tk_liste_ids.discard(0)

    types_par_liste: dict[int, int] = {}
    if tk_liste_ids:
        db_tk = get_connection("ticket")
        ids_sql = ",".join(str(i) for i in tk_liste_ids)
        tk_rows = db_tk.query(
            f"""SELECT IDTK_Liste, IDTK_TypeDemande
            FROM TK_Liste WHERE IDTK_Liste IN ({ids_sql})"""
        )
        for t in tk_rows:
            types_par_liste[_to_int(t.get("IDTK_Liste"))] = _to_int(t.get("IDTK_TypeDemande"))

    # Grouper par type pour fetch batch
    ids_sfr = [
        i for i, t in types_par_liste.items() if t == 20
    ]
    ids_call = [
        i for i, t in types_par_liste.items() if t == 22
    ]

    clients_par_liste: dict[int, dict] = {}
    if ids_sfr or ids_call:
        db_bo = get_connection("ticket_bo")

        fields = (
            "IDTK_Liste, NomClient, PrenomClient, NomMaritalClient, CivilitéClient, "
            "DATENAISS, DEPNAISS, ADRESSE1, ADRESSE2, CP, VILLE, Mobile1, adrMail, "
            "TypeLogement, ClientPro, ClientRS, ClientSiret"
        )

        if ids_sfr:
            ids_sql = ",".join(str(i) for i in ids_sfr)
            sfr_rows = db_bo.query(
                f"SELECT {fields} FROM TK_CallSFR WHERE IDTK_Liste IN ({ids_sql})"
            )
            for c in sfr_rows:
                clients_par_liste[_to_int(c.get("IDTK_Liste"))] = c

        if ids_call:
            ids_sql = ",".join(str(i) for i in ids_call)
            call_rows = db_bo.query(
                f"SELECT {fields} FROM TK_Call WHERE IDTK_Liste IN ({ids_sql})"
            )
            for c in call_rows:
                clients_par_liste[_to_int(c.get("IDTK_Liste"))] = c

    result = []
    for r in rows:
        id_liste = _to_int(r.get("IDTK_Liste"))
        client = clients_par_liste.get(id_liste, {})
        type_demande = types_par_liste.get(id_liste, 0)

        result.append({
            "id_rdv": str(_to_int(r.get("IDAgendaCommercial"))),
            "date_debut": r.get("DateDébut") or "",
            "date_fin": r.get("DateFin") or "",
            "titre": r.get("Titre") or "",
            "contenu": r.get("Contenu") or "",
            "info_compl": r.get("InfoCompl") or "",
            "id_categorie": _to_int(r.get("IDAgendaCommercial_Catégorie")),
            "lib_categorie": r.get("Lib_Catégorie") or "",
            "couleur_hex": _winrgb_to_hex(_to_int(r.get("Couleur"))),
            "id_cv_statut": _to_int(r.get("IdCvStatut")),
            "id_tk_liste": str(id_liste),
            "op_crea": _to_int(r.get("OPCrea")),
            "client_civilite": _to_int(client.get("CivilitéClient")),
            "client_nom": client.get("NomClient") or "",
            "client_prenom": client.get("PrenomClient") or "",
            "client_nom_marital": client.get("NomMaritalClient") or "",
            "client_naissance": client.get("DATENAISS") or "",
            "client_dep_naiss": _to_int(client.get("DEPNAISS")),
            "client_adresse1": client.get("ADRESSE1") or "",
            "client_adresse2": client.get("ADRESSE2") or "",
            "client_cp": client.get("CP") or "",
            "client_ville": client.get("VILLE") or "",
            "client_mobile": client.get("Mobile1") or "",
            "client_email": client.get("adrMail") or "",
            "client_type_logement": _to_int(client.get("TypeLogement")),
            "client_pro": bool(client.get("ClientPro")),
            "client_rs": client.get("ClientRS") or "",
            "client_siret": client.get("ClientSiret") or "",
            "type_demande": type_demande,
        })
    return result
