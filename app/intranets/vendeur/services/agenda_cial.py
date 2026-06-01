"""
Services agenda commercial : listing RDV + recherche commerciaux.

Tables AgendaCommercial + AgendaCommercial_Catégorie dans Bdd_Omaya_ADV.
Jointure sur TK_Liste (Bdd_Omaya_Ticket) pour récupérer l'info client,
puis sur TK_Call ou TK_CallSFR (Bdd_Omaya_Ticket_BO) selon IDTK_TypeDemande.
"""

import base64
import struct

from app.core.database.pg import get_pg_connection


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
    db_rh = get_pg_connection("rh")
    droit_rows = db_rh.query(
        """SELECT DISTINCT sd.id_salarie
        FROM pgt_salarie_droit_acces sd
        INNER JOIN pgt_type_droit_acces td ON td.id_type_droit_acces = sd.id_type_droit_acces
        WHERE td.code_interne = 'AgendaCial'
          AND td.fdv = TRUE
          AND sd.droit_actif = TRUE
          AND sd.modif_elem NOT LIKE '%suppr%'"""
    )
    ids_avec_droit = {_to_int(r.get("id_salarie")) for r in droit_rows}
    ids_avec_droit.discard(0)

    # 3. Obtenir les salariés ayant au moins 1 RDV dans AgendaCommercial
    db_adv = get_pg_connection("adv")
    rdv_rows = db_adv.query(
        """SELECT DISTINCT id_salarie FROM pgt_agenda_commercial
        WHERE modif_elem <> 'suppr'"""
    )
    ids_avec_rdv = {_to_int(r.get("id_salarie")) for r in rdv_rows}
    ids_avec_rdv.discard(0)

    # 4. Intersection : salariés accessibles ET (avec droit OU avec RDV)
    ids_eligibles = ids_accessibles & (ids_avec_droit | ids_avec_rdv)

    return [r for r in base_results if int(r["id_salarie"]) in ids_eligibles]


def lister_rdvs_cial(id_commercial: int, date_from: str, date_to: str) -> list[dict]:
    """
    Liste des RDV de l'agenda commercial d'un commercial entre deux dates.
    date_from / date_to : format YYYYMMDD.
    """
    db_adv = get_pg_connection("adv")

    # DateDébut est Date+Heure stocké en ISO "YYYY-MM-DDT..."
    # On utilise LEFT(DateDébut, 8) qui retourne YYYYMMDD (confirmé fonctionnel)
    rows = db_adv.query(
        """SELECT
            a.id_agenda_commercial, a.titre, a.contenu, a.info_compl,
            a.date_debut, a.date_fin, a.id_tk_liste, a.op_crea,
            a.id_agenda_commercial_categorie,
            c.lib_categorie, c.couleur, c.id_cv_statut
        FROM pgt_agenda_commercial a
        INNER JOIN pgt_agenda_commercial_categorie c
            ON c.id_agenda_commercial_categorie = a.id_agenda_commercial_categorie
        WHERE a.id_salarie = ?
          AND LEFT(a.date_debut, 8) >= ?
          AND LEFT(a.date_debut, 8) <= ?
          AND a.modif_elem <> 'suppr'
        ORDER BY a.date_debut ASC""",
        (id_commercial, date_from, date_to),
    )

    if not rows:
        return []

    # Récupérer les infos TK_Liste pour savoir quel TK_Call/TK_CallSFR interroger
    tk_liste_ids = {_to_int(r.get("id_tk_liste")) for r in rows}
    tk_liste_ids.discard(0)

    types_par_liste: dict[int, int] = {}
    if tk_liste_ids:
        db_tk = get_pg_connection("ticket")
        ids_sql = ",".join(str(i) for i in tk_liste_ids)
        tk_rows = db_tk.query(
            f"""SELECT id_tk_liste, id_tk_type_demande
            FROM pgt_tk_liste WHERE id_tk_liste IN ({ids_sql})"""
        )
        for t in tk_rows:
            types_par_liste[_to_int(t.get("id_tk_liste"))] = _to_int(t.get("id_tk_type_demande"))

    # Grouper par type pour fetch batch
    ids_sfr = [
        i for i, t in types_par_liste.items() if t == 20
    ]
    ids_call = [
        i for i, t in types_par_liste.items() if t == 22
    ]

    clients_par_liste: dict[int, dict] = {}
    if ids_sfr or ids_call:
        db_bo = get_pg_connection("ticket_bo")

        fields = (
            "id_tk_liste, nom_client, prenom_client, nom_marital_client, civilite_client, "
            "date_naiss, dep_naiss, adresse1, adresse2, cp, ville, mobile1, adr_mail, "
            "type_logement, client_pro, client_rs, client_siret"
        )

        if ids_sfr:
            ids_sql = ",".join(str(i) for i in ids_sfr)
            sfr_rows = db_bo.query(
                f"SELECT {fields} FROM pgt_tk_call_sfr WHERE id_tk_liste IN ({ids_sql})"
            )
            for c in sfr_rows:
                clients_par_liste[_to_int(c.get("id_tk_liste"))] = c

        if ids_call:
            ids_sql = ",".join(str(i) for i in ids_call)
            call_rows = db_bo.query(
                f"SELECT {fields} FROM pgt_tk_call WHERE id_tk_liste IN ({ids_sql})"
            )
            for c in call_rows:
                clients_par_liste[_to_int(c.get("id_tk_liste"))] = c

    result = []
    for r in rows:
        id_liste = _to_int(r.get("id_tk_liste"))
        client = clients_par_liste.get(id_liste, {})
        type_demande = types_par_liste.get(id_liste, 0)

        result.append({
            "id_rdv": str(_to_int(r.get("id_agenda_commercial"))),
            "date_debut": r.get("date_debut") or "",
            "date_fin": r.get("date_fin") or "",
            "titre": r.get("titre") or "",
            "contenu": r.get("contenu") or "",
            "info_compl": r.get("info_compl") or "",
            "id_categorie": _to_int(r.get("id_agenda_commercial_categorie")),
            "lib_categorie": r.get("lib_categorie") or "",
            "couleur_hex": _winrgb_to_hex(_to_int(r.get("couleur"))),
            "id_cv_statut": _to_int(r.get("id_cv_statut")),
            "id_tk_liste": str(id_liste),
            "op_crea": _to_int(r.get("op_crea")),
            "client_civilite": _to_int(client.get("civilite_client")),
            "client_nom": client.get("nom_client") or "",
            "client_prenom": client.get("prenom_client") or "",
            "client_nom_marital": client.get("nom_marital_client") or "",
            "client_naissance": client.get("date_naiss") or "",
            "client_dep_naiss": _to_int(client.get("dep_naiss")),
            "client_adresse1": client.get("adresse1") or "",
            "client_adresse2": client.get("adresse2") or "",
            "client_cp": client.get("cp") or "",
            "client_ville": client.get("ville") or "",
            "client_mobile": client.get("mobile1") or "",
            "client_email": client.get("adr_mail") or "",
            "client_type_logement": _to_int(client.get("type_logement")),
            "client_pro": bool(client.get("client_pro")),
            "client_rs": client.get("client_rs") or "",
            "client_siret": client.get("client_siret") or "",
            "type_demande": type_demande,
        })
    return result
