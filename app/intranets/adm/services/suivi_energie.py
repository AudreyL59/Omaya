"""Services pour Fen_SuiviEnergie (module ADM > Suivi Énergie).

Sous-fenêtres :
  - Fen_ExtractionEnergie : extraction tickets Call Energie OEN par
    periode + toggle Validé/Annulé + export XLSX
  - Fen_TicketCall (à venir)
"""

from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection


# ID type demande = 22 pour les tickets Call Energie (cf code WinDev)
TK_TYPE_DEMANDE_ENERGIE = 22
# IDTK_Statut = 28 = Cloturé annulé (exclu de l'extraction)
TK_STATUT_EXCLU = 28


def _date_str(v: Any) -> str:
    if v is None: return ""
    if isinstance(v, (date, datetime)): return v.strftime("%Y-%m-%d")
    return str(v)


def _capitalize(s: str) -> str:
    return s.capitalize() if s else ""


# ====================================================================
# 1. EXTRACTION ENERGIE (Fen_ExtractionEnergie)
# ====================================================================


class ExtractionEnergieRow(BaseModel):
    id_tk_liste: str
    date_souscription: str = ""
    numero_cm: str = ""
    nom: str = ""
    prenom: str = ""
    telephone: str = ""
    adresse_mail: str = ""
    date_activation: str = ""
    type_contrat: str = ""      # ELEC / GAZ / DUAL
    commercial: str = ""


def search_extraction_energie(
    du: date, au: date, statut: str = "valide",
) -> list[ExtractionEnergieRow]:
    """cf Fen_ExtractionEnergie : liste les tickets Call energie OEN
    sur la periode Du/Au (date_crea).

    statut :
      - 'valide'  : StatutProd IN (1, 3) (cf BoutonSegmente1 = 1)
      - 'annule'  : StatutProd = 2

    Agrege par ticket : si 2 paniers -> TYPE = 'DUAL',
    sinon TYPE = OEN_produit.SousFAM.
    """
    if statut == "annule":
        statut_prod = (2,)
    else:
        statut_prod = (1, 3)

    db_bo = get_pg_connection("ticket_bo")
    db_tk = get_pg_connection("ticket")
    db_adv = get_pg_connection("adv")
    db_rh = get_pg_connection("rh")

    placeholder = ",".join("?" * len(statut_prod))
    rows = db_bo.query(
        f"""SELECT c.id_tk_liste, c.id_salarie, c.nom_client, c.prenom_client,
                   c.mobile1, c.adr_mail, c.ref_appel,
                   l.date_crea, l.op_crea, l.id_tk_statut,
                   p.id_produit, p.partenaire, p.statut_prod,
                   p.observations, p.date_entree
              FROM ticket_bo.pgt_tk_call c
              JOIN ticket.pgt_tk_liste l ON l.id_tk_liste = c.id_tk_liste
              JOIN ticket_bo.pgt_tk_call_panier p
                ON p.id_tk_liste = l.id_tk_liste
             WHERE (l.modif_elem IS NULL OR l.modif_elem NOT LIKE '%suppr%')
               AND l.id_tk_type_demande = ?
               AND l.id_tk_statut <> ?
               AND l.date_crea >= ?
               AND l.date_crea < (?::date + INTERVAL '1 day')
               AND p.partenaire = 'OEN'
               AND p.statut_prod IN ({placeholder})
             ORDER BY l.date_crea ASC""",
        (TK_TYPE_DEMANDE_ENERGIE, TK_STATUT_EXCLU, du, au, *statut_prod),
    ) or []
    if not rows:
        return []

    # Resolutions batch : produits OEN + vendeurs
    id_prods = list({int(r["id_produit"]) for r in rows if r.get("id_produit")})
    id_sals  = list({int(r["op_crea"]) for r in rows if r.get("op_crea")})

    prods_map: dict[int, str] = {}
    if id_prods:
        ids = ",".join(str(i) for i in id_prods)
        p = db_adv.query(
            f"""SELECT id_produit, sous_fam FROM adv.pgt_oen_produit
                 WHERE id_produit IN ({ids})""",
        ) or []
        prods_map = {int(x["id_produit"]): (x.get("sous_fam") or "") for x in p}

    sals_map: dict[int, str] = {}
    if id_sals:
        ids = ",".join(str(i) for i in id_sals)
        s = db_rh.query(
            f"""SELECT id_salarie, nom, prenom FROM rh.pgt_salarie
                 WHERE id_salarie IN ({ids})""",
        ) or []
        for x in s:
            prenom = _capitalize((x.get("prenom") or "").lower())
            nom = (x.get("nom") or "").upper()
            sals_map[int(x["id_salarie"])] = f"{prenom} {nom}".strip()

    # Agrege par id_tk_liste : si 2 paniers -> DUAL
    by_tk: dict[str, ExtractionEnergieRow] = {}
    for r in rows:
        id_tl = str(r["id_tk_liste"])
        item = by_tk.get(id_tl)
        if item is None:
            id_p = int(r.get("id_produit") or 0)
            item = ExtractionEnergieRow(
                id_tk_liste=id_tl,
                date_souscription=_date_str(r.get("date_crea")),
                numero_cm=r.get("observations") or "",
                nom=r.get("nom_client") or "",
                prenom=r.get("prenom_client") or "",
                telephone=r.get("mobile1") or "",
                adresse_mail=r.get("adr_mail") or "",
                date_activation=_date_str(r.get("date_entree")),
                type_contrat=prods_map.get(id_p, ""),
                commercial=sals_map.get(int(r.get("op_crea") or 0), ""),
            )
            by_tk[id_tl] = item
        else:
            # 2e panier sur le meme ticket -> DUAL
            item.type_contrat = "DUAL"
            # Mise a jour date d'activation si plus recente
            de = _date_str(r.get("date_entree"))
            if de:
                item.date_activation = de
    return list(by_tk.values())


# ====================================================================
# 2. TICKET CALL ENERGIE (Fen_TicketCall)
# ====================================================================


class TicketCallItem(BaseModel):
    id_tk_liste: str
    id_tk_call: str
    id_salarie: int
    date_crea: str = ""
    date_h_appel: str = ""
    date_deb_prise_en_charge: str = ""
    date_fin_prise_en_charge: str = ""
    lib_statut: str = ""
    nom_client: str = ""
    prenom_client: str = ""
    cp: str = ""
    ville: str = ""
    adr_mail: str = ""
    mobile1: str = ""
    ref_appel: str = ""
    ope_appel: int = 0
    nom_operateur: str = ""
    nb_ctt: int = 0
    liste_num_ctt: str = ""     # Col_ListeNumCtt : Lib_produit + NumBS
    num_cm: str = ""            # Col_NumCM (Observations quand partenaire OEN)
    delai_prise_charge_min: float = 0.0
    duree_appel_sec: float = 0.0
    partenaires: list[str] = []
    row_color_alert: bool = False  # >1h entre crea et num_date_saisie


class AnalyseTrancheEnergie(BaseModel):
    tranche_horaire: str
    nb_ticket: int = 0
    moins_3_min: int = 0
    entre_3_et_5: int = 0
    entre_5_et_7: int = 0
    plus_de_7: int = 0


class AnalyseVentesItem(BaseModel):
    delai: str
    ventes_validees: int = 0
    ventes_annulees: int = 0


class AnalyseVentesTotaux(BaseModel):
    tranches: list[AnalyseVentesItem] = []
    nb_ventes_validees: int = 0
    nb_ventes_annulees: int = 0
    nb_ventes_pas_statuees: int = 0


class PlanningRdvItem(BaseModel):
    id_tk_call: str
    id_tk_liste: str
    id_salarie: int
    titre: str = ""       # nom + prenom client
    contenu: str = ""     # panier(s)
    ressource: str = ""   # 'Crea Ticket' ou nom operateur
    date_debut: str = ""
    date_fin: str = ""
    couleur_hex: str = ""
    nb_valide: int = 0


_COULEURS_DELAI = {
    "moins_3": "#bbf7d0",     # vert pastel (<3min)
    "entre_3_5": "#fef08a",   # jaune pastel
    "entre_5_7": "#fed7aa",   # orange pastel
    "plus_7": "#fecaca",      # rouge pastel
}


def _delai_label(en_min: float) -> tuple[str, str]:
    """Retourne (libelle, key_couleur) selon le delai en minutes."""
    if en_min < 3: return ("< 3 min", "moins_3")
    if en_min < 5: return ("3 à 5 min", "entre_3_5")
    if en_min < 7: return ("5 à 7 min", "entre_5_7")
    return ("> 7 min", "plus_7")


def _search_tickets_call_raw(
    du: date, au: date, etat: str,
) -> list[dict]:
    """Requete brute : cf ReqTkCall WinDev."""
    db_bo = get_pg_connection("ticket_bo")

    where = [
        "(c.modif_elem IS NULL OR c.modif_elem NOT LIKE '%suppr%')",
        "l.date_crea >= ?",
        "l.date_crea < (?::date + INTERVAL '1 day')",
        # Optionnel mais safe : ne prend que les tickets Energie
        "l.id_tk_type_demande = 22",
    ]
    params: list = [du, au]
    if etat == "ouverts":
        where.append("(l.cloturee IS NULL OR l.cloturee = FALSE)")
    elif etat == "clotures":
        where.append("l.cloturee = TRUE")

    rows = db_bo.query(
        f"""SELECT c.id_tk_call, c.id_tk_liste, c.id_salarie,
                   c.civilite_client, c.nom_client, c.nom_marital_client,
                   c.prenom_client, c.date_naiss, c.dep_naiss,
                   c.adresse1, c.adresse2, c.cp, c.ville, c.adr_mail,
                   c.mobile1, c.type_logement, c.appel_en_cours,
                   c.date_h_appel, c.ope_appel, c.ref_appel,
                   c.date_deb_prise_en_charge, c.date_fin_prise_en_charge,
                   l.date_crea, l.id_tk_statut, l.date_cloture, l.cloturee
              FROM ticket_bo.pgt_tk_call c
              JOIN ticket.pgt_tk_liste l ON l.id_tk_liste = c.id_tk_liste
             WHERE {' AND '.join(where)}
             ORDER BY l.date_crea DESC
             LIMIT 5000""",
        tuple(params),
    ) or []
    return rows


def list_ticket_call_energie(
    du: date, au: date, etat: str = "tous",
) -> list[TicketCallItem]:
    """cf Fen_TicketCall Energie : liste des tickets Call + resolution
    panier + operateur + statut."""
    rows = _search_tickets_call_raw(du, au, etat)
    if not rows:
        return []

    db_bo = get_pg_connection("ticket_bo")
    db_tk = get_pg_connection("ticket")
    db_rh = get_pg_connection("rh")
    db_adv = get_pg_connection("adv")

    # Panier par id_tk_call
    id_calls = [int(r["id_tk_call"]) for r in rows]
    ids_sql = ",".join(str(i) for i in id_calls)
    paniers = db_bo.query(
        f"""SELECT p.id_tk_call, p.id_produit, p.partenaire, p.num_bs,
                   p.num_date_saisie, p.observations, p.statut_prod
              FROM ticket_bo.pgt_tk_call_panier p
             WHERE p.id_tk_call IN ({ids_sql})
               AND (p.modif_elem IS NULL OR p.modif_elem NOT LIKE '%suppr%')""",
    ) or []
    paniers_by_call: dict[int, list[dict]] = {}
    for p in paniers:
        paniers_by_call.setdefault(int(p["id_tk_call"]), []).append(p)

    # Lookup produits par partenaire (schema commun adv)
    all_prods: dict[tuple[str, int], str] = {}
    for p in paniers:
        part = (p.get("partenaire") or "").upper()
        pid = int(p.get("id_produit") or 0)
        if not part or not pid: continue
        table = f"pgt_{part.lower()}_produit"
        if (part, pid) in all_prods: continue
        try:
            r = db_adv.query_one(
                f"SELECT lib_produit FROM adv.{table} WHERE id_produit = ? LIMIT 1",
                (pid,),
            )
            all_prods[(part, pid)] = (r or {}).get("lib_produit") or ""
        except Exception:
            all_prods[(part, pid)] = ""

    # Statuts + operateurs + salaries
    id_statuts = list({int(r.get("id_tk_statut") or 0) for r in rows if r.get("id_tk_statut")})
    id_ope     = list({int(r.get("ope_appel") or 0) for r in rows if r.get("ope_appel")})

    statuts_map: dict[int, str] = {}
    if id_statuts:
        ids = ",".join(str(i) for i in id_statuts)
        s = db_tk.query(
            f"SELECT id_tk_statut, lib_statut FROM ticket.pgt_tk_statut WHERE id_tk_statut IN ({ids})",
        ) or []
        statuts_map = {int(x["id_tk_statut"]): x.get("lib_statut") or "" for x in s}

    ope_map: dict[int, str] = {}
    if id_ope:
        ids = ",".join(str(i) for i in id_ope)
        s = db_rh.query(
            f"SELECT id_salarie, nom, prenom FROM rh.pgt_salarie WHERE id_salarie IN ({ids})",
        ) or []
        for x in s:
            prenom = _capitalize((x.get("prenom") or "").lower())
            ope_map[int(x["id_salarie"])] = f"{prenom} {(x.get('nom') or '').upper()}".strip()

    out: list[TicketCallItem] = []
    for r in rows:
        id_c = int(r["id_tk_call"])
        pans = paniers_by_call.get(id_c, [])

        # Construit Col_ListeNumCtt + partenaires + row_color_alert
        libs: list[str] = []
        parts_set: set[str] = set()
        num_cm = ""
        row_alert = False
        for p in pans:
            part = (p.get("partenaire") or "").upper()
            parts_set.add(part)
            pid = int(p.get("id_produit") or 0)
            lib = all_prods.get((part, pid)) or f"Prod {part} inconnu"
            num_bs = p.get("num_bs") or ""
            line = f"{lib} {num_bs}"
            nds = p.get("num_date_saisie")
            if isinstance(nds, datetime):
                line += f" ({nds.strftime('%d/%m/%Y %H:%M')})"
                # Diff crea vs num_date_saisie : >1h -> rouge
                dc = r.get("date_crea")
                if isinstance(dc, datetime):
                    diff_h = (nds - dc).total_seconds() / 3600.0
                    if diff_h >= 1:
                        row_alert = True
            libs.append(line)
            if part == "OEN":
                num_cm = p.get("observations") or ""

        # Delai + duree
        delai_min = 0.0
        duree_sec = 0.0
        dc = r.get("date_crea")
        deb = r.get("date_deb_prise_en_charge")
        fin = r.get("date_fin_prise_en_charge")
        if isinstance(dc, datetime) and isinstance(deb, datetime):
            delai_min = max(0.0, (deb - dc).total_seconds() / 60.0)
        if isinstance(deb, datetime) and isinstance(fin, datetime):
            duree_sec = max(0.0, (fin - deb).total_seconds())

        out.append(TicketCallItem(
            id_tk_liste=str(r["id_tk_liste"]),
            id_tk_call=str(r["id_tk_call"]),
            id_salarie=int(r.get("id_salarie") or 0),
            date_crea=_date_str(dc) if not isinstance(dc, datetime) else dc.strftime("%Y-%m-%d %H:%M:%S"),
            date_h_appel=(r.get("date_h_appel").strftime("%Y-%m-%d %H:%M:%S")
                          if isinstance(r.get("date_h_appel"), datetime) else ""),
            date_deb_prise_en_charge=(deb.strftime("%Y-%m-%d %H:%M:%S")
                                       if isinstance(deb, datetime) else ""),
            date_fin_prise_en_charge=(fin.strftime("%Y-%m-%d %H:%M:%S")
                                       if isinstance(fin, datetime) else ""),
            lib_statut=statuts_map.get(int(r.get("id_tk_statut") or 0), ""),
            nom_client=r.get("nom_client") or "",
            prenom_client=r.get("prenom_client") or "",
            cp=r.get("cp") or "",
            ville=r.get("ville") or "",
            adr_mail=r.get("adr_mail") or "",
            mobile1=r.get("mobile1") or "",
            ref_appel=r.get("ref_appel") or "",
            ope_appel=int(r.get("ope_appel") or 0),
            nom_operateur=ope_map.get(int(r.get("ope_appel") or 0), ""),
            nb_ctt=len(pans),
            liste_num_ctt="\n".join(libs),
            num_cm=num_cm,
            delai_prise_charge_min=round(delai_min, 2),
            duree_appel_sec=round(duree_sec, 1),
            partenaires=sorted(parts_set),
            row_color_alert=row_alert,
        ))
    return out


def analyse_ventes_tk_call_energie(
    du: date, au: date, etat: str = "tous",
) -> AnalyseVentesTotaux:
    """Analyse des ventes par tranche de delai (cf onglet Analyse ventes
    Fen_TicketCall) : compte les paniers Validés (statut_prod IN 1,3)
    vs Annulés (statut_prod=2) par tranche de delai (<3 / 3-5 / 5-7 / >7)."""
    rows = _search_tickets_call_raw(du, au, etat)
    if not rows:
        return AnalyseVentesTotaux()

    db_bo = get_pg_connection("ticket_bo")
    id_calls = [int(r["id_tk_call"]) for r in rows]
    ids_sql = ",".join(str(i) for i in id_calls)
    paniers = db_bo.query(
        f"""SELECT id_tk_call, statut_prod FROM ticket_bo.pgt_tk_call_panier
             WHERE id_tk_call IN ({ids_sql})
               AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
    ) or []
    paniers_by_call: dict[int, list[dict]] = {}
    for p in paniers:
        paniers_by_call.setdefault(int(p["id_tk_call"]), []).append(p)

    # Agrege par tranche de delai
    tranches_map: dict[str, AnalyseVentesItem] = {}
    tot_val = tot_ann = tot_pas = 0
    for r in rows:
        deb = r.get("date_deb_prise_en_charge")
        crea = r.get("date_crea")
        delai = 0.0
        if isinstance(deb, datetime) and isinstance(crea, datetime):
            delai = max(0.0, (deb - crea).total_seconds() / 60.0)
        lbl, _ = _delai_label(delai)

        item = tranches_map.get(lbl)
        if item is None:
            item = AnalyseVentesItem(delai=lbl)
            tranches_map[lbl] = item

        for p in paniers_by_call.get(int(r["id_tk_call"]), []):
            sp = int(p.get("statut_prod") or 0)
            if sp in (1, 3):
                item.ventes_validees += 1
                tot_val += 1
            elif sp == 2:
                item.ventes_annulees += 1
                tot_ann += 1
            else:
                tot_pas += 1

    order = {"< 3 min": 0, "3 à 5 min": 1, "5 à 7 min": 2, "> 7 min": 3}
    tranches = sorted(tranches_map.values(), key=lambda x: order.get(x.delai, 99))
    return AnalyseVentesTotaux(
        tranches=tranches,
        nb_ventes_validees=tot_val,
        nb_ventes_annulees=tot_ann,
        nb_ventes_pas_statuees=tot_pas,
    )


def planning_appels_energie(
    du: date, au: date, etat: str = "tous",
) -> list[PlanningRdvItem]:
    """cf onglet Planning : genere les RDV pour le calendrier
    (colonne 'Crea Ticket' + colonnes operateurs). Chaque ticket
    genere 2 RDV : un a la date de crea, un a la prise en charge."""
    rows = _search_tickets_call_raw(du, au, etat)
    if not rows:
        return []

    db_bo = get_pg_connection("ticket_bo")
    db_rh = get_pg_connection("rh")
    id_calls = [int(r["id_tk_call"]) for r in rows]
    ids_sql = ",".join(str(i) for i in id_calls)
    paniers = db_bo.query(
        f"""SELECT id_tk_call, num_bs, num_date_saisie, statut_prod, partenaire
              FROM ticket_bo.pgt_tk_call_panier
             WHERE id_tk_call IN ({ids_sql})
               AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')""",
    ) or []
    paniers_by_call: dict[int, list[dict]] = {}
    for p in paniers:
        paniers_by_call.setdefault(int(p["id_tk_call"]), []).append(p)

    id_ope = list({int(r.get("ope_appel") or 0) for r in rows if r.get("ope_appel")})
    ope_map: dict[int, str] = {}
    if id_ope:
        ids = ",".join(str(i) for i in id_ope)
        s = db_rh.query(
            f"SELECT id_salarie, nom, prenom FROM rh.pgt_salarie WHERE id_salarie IN ({ids})",
        ) or []
        for x in s:
            prenom = _capitalize((x.get("prenom") or "").lower())
            ope_map[int(x["id_salarie"])] = f"{prenom} {(x.get('nom') or '').upper()}".strip()

    out: list[PlanningRdvItem] = []
    for r in rows:
        # Skip vendeur ID=6 cf code WinDev
        id_sa = int(r.get("id_salarie") or 0)
        if id_sa == 6: continue

        dc = r.get("date_crea")
        if not isinstance(dc, datetime): continue

        # Delai + couleur
        deb = r.get("date_deb_prise_en_charge")
        delai_min = 0.0
        if isinstance(deb, datetime):
            delai_min = max(0.0, (deb - dc).total_seconds() / 60.0)
        _, key = _delai_label(delai_min)
        couleur = _COULEURS_DELAI[key]

        # Titre + contenu
        titre = f"{r.get('nom_client') or ''} {_capitalize((r.get('prenom_client') or '').lower())}".strip()
        pans = paniers_by_call.get(int(r["id_tk_call"]), [])
        contenu_parts = []
        nb_val = 0
        for p in pans:
            sp = int(p.get("statut_prod") or 0)
            etat_prod = "Pas statué"
            if sp == 1: etat_prod = "Validé"; nb_val += 1
            elif sp == 2: etat_prod = "Annulé"
            elif sp == 3: etat_prod = "Num BS ajouté"; nb_val += 1
            line = p.get("num_bs") or ""
            nds = p.get("num_date_saisie")
            if isinstance(nds, datetime):
                line += f" ({nds.strftime('%d/%m/%Y %H:%M')})"
            line += f" - {etat_prod}"
            contenu_parts.append(line)
        contenu = "\n".join(contenu_parts)

        # RDV 1 : Crea Ticket (colonne 'Crea Ticket')
        deb_crea = dc.replace(second=0, microsecond=0)
        fin_crea = deb_crea + timedelta(minutes=3)
        out.append(PlanningRdvItem(
            id_tk_call=str(r["id_tk_call"]),
            id_tk_liste=str(r["id_tk_liste"]),
            id_salarie=id_sa,
            titre=titre, contenu=contenu,
            ressource="Crea Ticket",
            date_debut=deb_crea.strftime("%Y-%m-%d %H:%M:%S"),
            date_fin=fin_crea.strftime("%Y-%m-%d %H:%M:%S"),
            couleur_hex=couleur, nb_valide=nb_val,
        ))

        # RDV 2 : Colonne operateur (Prise en charge)
        ope_id = int(r.get("ope_appel") or 0)
        nom_ope = ope_map.get(ope_id, "")
        if nom_ope and isinstance(deb, datetime):
            fin = r.get("date_fin_prise_en_charge")
            if isinstance(fin, datetime) and deb <= fin:
                d_deb, d_fin = deb, fin
            else:
                d_deb, d_fin = deb, deb + timedelta(minutes=3)
            out.append(PlanningRdvItem(
                id_tk_call=str(r["id_tk_call"]),
                id_tk_liste=str(r["id_tk_liste"]),
                id_salarie=id_sa,
                titre=titre, contenu=contenu,
                ressource=nom_ope,
                date_debut=d_deb.strftime("%Y-%m-%d %H:%M:%S"),
                date_fin=d_fin.strftime("%Y-%m-%d %H:%M:%S"),
                couleur_hex=couleur, nb_valide=nb_val,
            ))
    return out


def export_extraction_energie_xlsx(
    rows: list[ExtractionEnergieRow],
) -> bytes:
    """XLSX simple (pas de couleurs necessaires ici)."""
    import io
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font

    columns: list[tuple[str, str]] = [
        ("date_souscription", "Date de souscription"),
        ("numero_cm", "Numéro de CM"),
        ("nom", "Nom"),
        ("prenom", "Prénom"),
        ("telephone", "Téléphone"),
        ("adresse_mail", "Adresse mail"),
        ("date_activation", "Date d'activation"),
        ("type_contrat", "Type de contrat"),
        ("commercial", "Commercial"),
    ]
    wb = Workbook(); ws = wb.active; ws.title = "Extraction Énergie"
    ws.append([lbl for _, lbl in columns])
    header_fill = PatternFill(start_color="FF17494E", end_color="FF17494E",
                               fill_type="solid")
    header_font = Font(color="FFFFFFFF", bold=True)
    for cell in ws[1]:
        cell.fill = header_fill; cell.font = header_font

    for r in rows:
        ws.append([getattr(r, k) for k, _ in columns])

    for i, w in enumerate([16, 20, 20, 20, 14, 28, 16, 12, 22], start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    ws.freeze_panes = "A2"
    buf = io.BytesIO(); wb.save(buf); buf.seek(0)
    return buf.read()
