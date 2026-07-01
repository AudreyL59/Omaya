"""Services pour Fen_SuiviEnergie (module ADM > Suivi Énergie).

Sous-fenêtres :
  - Fen_ExtractionEnergie : extraction tickets Call Energie OEN par
    periode + toggle Validé/Annulé + export XLSX
  - Fen_TicketCall (à venir)
"""

from datetime import date, datetime
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
