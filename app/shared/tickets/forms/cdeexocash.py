"""FI_CdeExoCash (type 24 — Commande ExoCash).

Tables :
  - TK_CdeExoCash / TK_CdeExoCashLot / TK_CdeExoCashEnvoi : base ticket_rh
  - ExoCashLot / ExoCashFamilleLot / ExoCashLotHistoStock : base divers
  - salarie_Livret : base rh (calcul du solde, débit à la validation)
  - TK_Liste : base ticket (statut 29 = Commande validée)

Fonctionnalités :
  - Panier (ajout / suppression / MAJ Qté) — lots d'ExoCashLot
  - Solde ExoCash du salarié (somme crédit - débit de salarie_Livret)
  - Validation : MAJ TK_CdeExoCash, débit livret, MAJ stocks
    ExoCashLot + histo, statut ticket 29, SMS au salarié
  - Envois (TK_CdeExoCashEnvoi) : ajout / édition / suppression
"""

from app.core.database import get_connection
from app.shared.notifications.sms import envoi_sms

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    _windev_to_iso,
    date_only_to_iso,
    iso_to_date_only,
    load_salaries_minimal,
    maj_op_traitement_ticket,
)

STATUT_COMMANDE_VALIDEE = 29  # TK_Liste.IDTK_Statut après validation
TYPE_OP_LIVRET_DEBIT_EXOCASH = 3  # cf. salarie_Livret.IDTypeOperationLivret

# ExoCashLot.Catégorie (enum 1 octet)
CATEG_POUR = {1: "Femme", 2: "Homme", 3: "H/F"}


# --------------------------------------------------------------------
# Helpers cross-DB
# --------------------------------------------------------------------

def _lots_catalogue(ids: set[int] | None = None) -> dict[int, dict]:
    """Retourne {IDExoCashLot: {libfam, marque, liblot, categ, montant,
    montant_solde, en_solde, stock, sur_commande}} depuis ExoCashLot +
    ExoCashFamilleLot (base divers). Si ids fourni, filtre."""
    db = get_connection("divers")
    where = ""
    if ids:
        ids_ok = {int(i) for i in ids if i}
        if not ids_ok:
            return {}
        where = " WHERE IDExoCashLot IN (" + ",".join(str(i) for i in ids_ok) + ")"
    out: dict[int, dict] = {}
    fams: dict[int, str] = {}
    try:
        for r in db.query("SELECT IDExoCashFamilleLot, LibFamilleLot "
                          "FROM ExoCashFamilleLot"):
            fams[_to_int(r.get("IDExoCashFamilleLot"))] = (
                r.get("LibFamilleLot") or ""
            ).strip()
    except Exception:
        pass
    try:
        rows = db.query(
            "SELECT IDExoCashLot, IDExoCashFamilleLot, Marque, LibLot, "
            "Catégorie, Montant, MontantSolde, EnSolde, Stock, SurCommande "
            "FROM ExoCashLot" + where
        )
    except Exception:
        rows = []
    for r in rows or []:
        try:
            idl = _clean_id(_to_int(r.get("IDExoCashLot")))
            if not idl:
                continue
            categ = _to_int(r.get("Catégorie"))
            out[idl] = {
                "id": idl,
                "id_famille": _to_int(r.get("IDExoCashFamilleLot")),
                "libfam": fams.get(_to_int(r.get("IDExoCashFamilleLot")), ""),
                "marque": str(r.get("Marque") or "").strip(),
                "liblot": str(r.get("LibLot") or "").strip(),
                "categ": categ,
                "pour": CATEG_POUR.get(categ, ""),
                "montant": float(r.get("Montant") or 0),
                "montant_solde": float(r.get("MontantSolde") or 0),
                "en_solde": bool(r.get("EnSolde")),
                "stock": _to_int(r.get("Stock")),
                "sur_commande": bool(r.get("SurCommande")),
            }
        except Exception:
            continue
    return out


def _panier_lignes(id_ticket: int) -> list[dict]:
    rh = get_connection("ticket_rh")
    try:
        rows = rh.query(
            """SELECT IDTK_CdeExoCashLot, IDExoCashLot, Qté, NumSuivi,
                MontantPayé
            FROM TK_CdeExoCashLot
            WHERE ModifElem NOT LIKE '%suppr%' AND IDTK_Liste = ?""",
            (int(id_ticket),),
        )
    except Exception:
        return []
    lines = [
        {
            "id_panier": str(_clean_id(_to_int(r.get("IDTK_CdeExoCashLot")))),
            "id_lot": _clean_id(_to_int(r.get("IDExoCashLot"))),
            "qte": _to_int(r.get("Qté")),
            "num_suivi": (r.get("NumSuivi") or "").strip(),
            "montant_unitaire": float(r.get("MontantPayé") or 0),
        }
        for r in rows or []
    ]
    cat = _lots_catalogue({l["id_lot"] for l in lines})
    for l in lines:
        info = cat.get(l["id_lot"], {})
        l["libfam"] = info.get("libfam", "")
        l["marque"] = info.get("marque", "")
        l["liblot"] = info.get("liblot", "")
        l["categ"] = info.get("categ", 0)
        l["pour"] = info.get("pour", "")
        l["stock"] = info.get("stock", 0)
        l["sur_commande"] = info.get("sur_commande", False)
        l["montant_total"] = l["montant_unitaire"] * l["qte"]
    return lines


def _envois(id_ticket: int) -> list[dict]:
    try:
        rows = get_connection("ticket_rh").query(
            """SELECT IDTK_CdeExoCashEnvoi, NumSuivi, dateEnvoi, Transporteur
            FROM TK_CdeExoCashEnvoi
            WHERE ModifElem <> 'suppr' AND IDTK_Liste = ?""",
            (int(id_ticket),),
        )
    except Exception:
        return []
    out = []
    for r in rows or []:
        ide = _clean_id(_to_int(r.get("IDTK_CdeExoCashEnvoi")))
        out.append({
            "id_envoi": str(ide),
            "num_suivi": (r.get("NumSuivi") or "").strip(),
            "date_envoi": date_only_to_iso(r.get("dateEnvoi")),
            "transporteur": (r.get("Transporteur") or "").strip(),
        })
    # AdresseLivraison via SELECT isolé (mémo)
    for e in out:
        try:
            r = get_connection("ticket_rh").query_one(
                "SELECT IDTK_CdeExoCashEnvoi, AdresseLivraison "
                "FROM TK_CdeExoCashEnvoi "
                "WHERE IDTK_CdeExoCashEnvoi = ?",
                (int(e["id_envoi"]),),
            )
            e["adresse"] = ((r.get("AdresseLivraison") if r else "") or "").strip()
        except Exception:
            e["adresse"] = ""
    return out


def _solde_exocash(id_salarie: int) -> float:
    """Somme crédit - débit (salarie_Livret rh) pour le salarié."""
    if not id_salarie:
        return 0.0
    try:
        r = get_connection("rh").query_one(
            "SELECT SUM(MontantCrédit) AS c, SUM(MontantDébit) AS d "
            "FROM salarie_Livret WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        return float((r.get("c") or 0)) - float((r.get("d") or 0))
    except Exception:
        return 0.0


def _adresse_salarie(id_salarie: int) -> str:
    """Adresse de livraison par défaut = nom + adresses depuis
    salarie_coordonnées (rh)."""
    if not id_salarie:
        return ""
    try:
        rh = get_connection("rh")
        i = load_salaries_minimal({int(id_salarie)}).get(int(id_salarie), {})
        nom = i.get("nom", "")
        prenom = i.get("prenom", "")
        nom_pre = f"{nom} {prenom[:1].upper() + prenom[1:].lower() if prenom else ''}".strip()
        c = rh.query_one(
            "SELECT IDSalarie, Adresse1, ADRESSE2, CP, Ville "
            "FROM salarie_coordonnées WHERE IDSalarie = ?",
            (int(id_salarie),),
        )
        if not c:
            return nom_pre
        parts = [nom_pre, (c.get("Adresse1") or "").strip()]
        a2 = (c.get("ADRESSE2") or "").strip()
        if a2:
            parts.append(a2)
        parts.append(
            f"{(c.get('CP') or '').strip()} {(c.get('Ville') or '').strip()}"
            .strip()
        )
        return "\n".join(p for p in parts if p)
    except Exception:
        return ""


# --------------------------------------------------------------------
# load / save
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    db = get_connection("ticket_rh")
    r = db.query_one(
        """SELECT IDTK_Liste, IDTK_CdeExoCash, IDSalarie, DateCommande,
            CommandeValidée, DateValidation, OpéValidation
        FROM TK_CdeExoCash WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}
    id_cde = _clean_id(_to_int(r.get("IDTK_CdeExoCash")))
    id_salarie = _clean_id(_to_int(r.get("IDSalarie")))
    op_valid = _clean_id(_to_int(r.get("OpéValidation")))
    op_valid_nom = ""
    if op_valid:
        i = load_salaries_minimal({op_valid}).get(op_valid, {})
        p = i.get("prenom", "")
        op_valid_nom = (
            f"{p[:1].upper() + p[1:].lower() if p else ''} "
            f"{i.get('nom', '')[:1].upper() if i.get('nom') else ''}"
        ).strip()

    panier = _panier_lignes(id_ticket)
    montant_global = sum(l["montant_total"] for l in panier)
    solde = _solde_exocash(id_salarie)

    return {
        "found": True,
        "id_cde": str(id_cde) if id_cde else "",
        "id_salarie": str(id_salarie) if id_salarie else "",
        "salarie_nom": (
            lambda i: f"{i.get('nom', '')} {(i.get('prenom') or '')[:1].upper() + (i.get('prenom') or '')[1:].lower() if i.get('prenom') else ''}".strip()
        )(load_salaries_minimal({id_salarie}).get(id_salarie, {})),
        "date_commande": _windev_to_iso(r.get("DateCommande")),
        "commande_validee": bool(r.get("CommandeValidée")),
        "date_validation": _windev_to_iso(r.get("DateValidation")),
        "op_validation_nom": op_valid_nom,
        "panier": panier,
        "envois": _envois(id_ticket),
        "lots_dispos": list(_lots_catalogue().values()),
        "montant_global": montant_global,
        "solde": solde,
        "adresse_defaut": _adresse_salarie(id_salarie),
    }


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "")
    now = _now_windev()
    rh = get_connection("ticket_rh")

    # --- panier : ajout d'un lot ---
    if action == "add_lot":
        id_lot = _to_int(payload.get("id_lot"))
        if not id_lot:
            return {"ok": False, "error": "Lot manquant"}
        cur = rh.query_one(
            "SELECT IDTK_CdeExoCash FROM TK_CdeExoCash WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Commande introuvable"}
        id_cde = _clean_id(_to_int(cur.get("IDTK_CdeExoCash")))
        lot = _lots_catalogue({id_lot}).get(id_lot)
        if not lot:
            return {"ok": False, "error": "Lot introuvable"}
        montant = (
            lot["montant_solde"]
            if (lot["en_solde"] and lot["montant_solde"] > 0)
            else lot["montant"]
        )
        new_id = int(now)
        try:
            rh.query(
                """INSERT INTO TK_CdeExoCashLot
                (IDTK_CdeExoCashLot, IDTK_CdeExoCash, IDTK_Liste,
                 IDExoCashLot, Qté, MontantPayé, ModifOp, ModifDate,
                 ModifElem)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?, 'new')""",
                (
                    new_id, int(id_cde), int(id_ticket), int(id_lot),
                    montant, int(user_id), now,
                ),
            )
        except Exception as e:
            return {"ok": False, "error": f"add_lot : {e}"}
        return {"ok": True}

    # --- panier : suppression (soft delete) ---
    if action == "del_lot":
        id_panier = _to_int(payload.get("id_panier"))
        if not id_panier:
            return {"ok": False, "error": "Ligne manquante"}
        try:
            rh.query(
                """UPDATE TK_CdeExoCashLot SET ModifElem = 'suppr',
                    ModifOp = ?, ModifDate = ?
                WHERE IDTK_CdeExoCashLot = ?""",
                (int(user_id), now, int(id_panier)),
            )
        except Exception as e:
            return {"ok": False, "error": f"del_lot : {e}"}
        return {"ok": True}

    # --- panier : MAJ Qté / NumSuivi (cf. HModifie WinDev, ModifElem='new') ---
    if action == "update_lot":
        id_panier = _to_int(payload.get("id_panier"))
        if not id_panier:
            return {"ok": False, "error": "Ligne manquante"}
        qte = max(1, _to_int(payload.get("qte") or 1))
        num_suivi = str(payload.get("num_suivi") or "").strip()
        try:
            rh.query(
                """UPDATE TK_CdeExoCashLot SET Qté = ?, NumSuivi = ?,
                    ModifOp = ?, ModifDate = ?, ModifElem = 'new'
                WHERE IDTK_CdeExoCashLot = ?""",
                (qte, num_suivi, int(user_id), now, int(id_panier)),
            )
        except Exception as e:
            return {"ok": False, "error": f"update_lot : {e}"}
        return {"ok": True}

    # --- envoi (TK_CdeExoCashEnvoi) : add / update / del ---
    if action in ("add_envoi", "update_envoi"):
        cur = rh.query_one(
            "SELECT IDTK_CdeExoCash FROM TK_CdeExoCash WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Commande introuvable"}
        id_cde = _clean_id(_to_int(cur.get("IDTK_CdeExoCash")))
        num = str(payload.get("num_suivi") or "").strip()
        d_env = iso_to_date_only(payload.get("date_envoi"))
        transp = str(payload.get("transporteur") or "").strip()
        adr = str(payload.get("adresse") or "")
        if action == "add_envoi":
            new_id = int(now)
            try:
                rh.query(
                    """INSERT INTO TK_CdeExoCashEnvoi
                    (IDTK_CdeExoCashEnvoi, IDTK_CdeExoCash, IDTK_Liste,
                     NumSuivi, dateEnvoi, Transporteur, AdresseLivraison,
                     ModifOp, ModifDate, ModifElem)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                    (
                        new_id, int(id_cde), int(id_ticket), num, d_env,
                        transp, adr, int(user_id), now,
                    ),
                )
            except Exception as e:
                return {"ok": False, "error": f"add_envoi : {e}"}
            return {"ok": True, "id_envoi": str(new_id)}
        else:
            id_envoi = _to_int(payload.get("id_envoi"))
            if not id_envoi:
                return {"ok": False, "error": "Envoi manquant"}
            try:
                rh.query(
                    """UPDATE TK_CdeExoCashEnvoi SET NumSuivi = ?,
                        dateEnvoi = ?, Transporteur = ?,
                        AdresseLivraison = ?, ModifOp = ?, ModifDate = ?,
                        ModifElem = 'modif'
                    WHERE IDTK_CdeExoCashEnvoi = ?""",
                    (
                        num, d_env, transp, adr, int(user_id), now,
                        int(id_envoi),
                    ),
                )
            except Exception as e:
                return {"ok": False, "error": f"update_envoi : {e}"}
            return {"ok": True}

    if action == "del_envoi":
        id_envoi = _to_int(payload.get("id_envoi"))
        if not id_envoi:
            return {"ok": False, "error": "Envoi manquant"}
        try:
            rh.query(
                """UPDATE TK_CdeExoCashEnvoi SET ModifElem = 'suppr',
                    ModifOp = ?, ModifDate = ?
                WHERE IDTK_CdeExoCashEnvoi = ?""",
                (int(user_id), now, int(id_envoi)),
            )
        except Exception as e:
            return {"ok": False, "error": f"del_envoi : {e}"}
        return {"ok": True}

    # --- validation finale ---
    if action == "valider":
        cur = rh.query_one(
            """SELECT IDTK_CdeExoCash, IDSalarie FROM TK_CdeExoCash
            WHERE IDTK_Liste = ?""",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Commande introuvable"}
        id_salarie = _clean_id(_to_int(cur.get("IDSalarie")))

        panier = _panier_lignes(int(id_ticket))
        if not panier:
            return {"ok": False, "error": "Le panier est vide"}
        montant_total = sum(l["montant_total"] for l in panier)
        solde = _solde_exocash(id_salarie)
        if montant_total > solde:
            return {"ok": False,
                    "error": "Solde ExoCash insuffisant pour valider"}

        # 1. TK_CdeExoCash → CommandeValidée
        try:
            rh.query(
                """UPDATE TK_CdeExoCash SET CommandeValidée = 1,
                    DateValidation = ?, OpéValidation = ?, ModifDate = ?,
                    ModifOp = ?, ModifElem = 'modif'
                WHERE IDTK_Liste = ?""",
                (now, int(user_id), now, int(user_id), int(id_ticket)),
            )
        except Exception as e:
            return {"ok": False, "error": f"valider : {e}"}

        # 2. salarie_Livret : débit (base rh)
        try:
            get_connection("rh").query(
                """INSERT INTO salarie_Livret
                (IDsalarie_Livret, IDSalarie, IDTypeOperationLivret,
                 IDChallenge, IDTK_Liste, MontantCrédit, MontantDébit,
                 DateOpération, Operateur, ModifDate, ModifOp, ModifElem)
                VALUES (?, ?, ?, 0, ?, 0, ?, ?, ?, ?, ?, 'new')""",
                (
                    int(now), int(id_salarie), TYPE_OP_LIVRET_DEBIT_EXOCASH,
                    int(id_ticket), float(montant_total), now,
                    int(user_id), now, int(user_id),
                ),
            )
        except Exception as e:
            return {"ok": False, "error": f"salarie_Livret : {e}"}

        # 3. ExoCashLot.Stock − Qté + ExoCashLotHistoStock (base divers)
        div = get_connection("divers")
        for l in panier:
            try:
                lot = _lots_catalogue({l["id_lot"]}).get(l["id_lot"])
                if not lot:
                    continue
                if not lot["sur_commande"]:
                    new_stock = max(0, lot["stock"] - l["qte"])
                    div.query(
                        "UPDATE ExoCashLot SET Stock = ?, ModifDate = ?, "
                        "ModifOp = ?, ModifElem = 'modif' "
                        "WHERE IDExoCashLot = ?",
                        (new_stock, now, int(user_id), int(l["id_lot"])),
                    )
                # histo
                div.query(
                    """INSERT INTO ExoCashLotHistoStock
                    (IDExoCashLotHistoStock, IDExoCashLot, dateHisto,
                     OpéCrea, Qté, IDTK_Liste, ModifDate, ModifOp,
                     ModifElem)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                    (
                        int(now), int(l["id_lot"]), now, int(user_id),
                        -l["qte"] if not lot["sur_commande"] else 0,
                        int(id_ticket), now, int(user_id),
                    ),
                )
            except Exception:
                pass

        # 4. TK_Liste statut 29
        try:
            get_connection("ticket").query(
                """UPDATE TK_Liste SET IDTK_Statut = ?, ModifDate = ?,
                    ModifOp = ?
                WHERE IDTK_Liste = ?""",
                (STATUT_COMMANDE_VALIDEE, now, int(user_id), int(id_ticket)),
            )
        except Exception:
            pass

        # 5. SMS au salarié
        sms_result = ""
        try:
            c = get_connection("rh").query_one(
                "SELECT IDSalarie, TélMob FROM salarie_coordonnées "
                "WHERE IDSalarie = ?",
                (int(id_salarie),),
            )
            gsm = ((c.get("TélMob") if c else "") or "")
            for ch in (".", " ", "/", "-"):
                gsm = gsm.replace(ch, "")
            if gsm:
                sms_result = envoi_sms(
                    "Commande validee. Elle sera expediee prochainement.",
                    gsm, "", "ExoCash",
                )
        except Exception as e:
            sms_result = f"SMS non envoyé : {e}"

        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True, "sms_result": sms_result}

    if action == "actualiser_solde":
        cur = rh.query_one(
            "SELECT IDSalarie FROM TK_CdeExoCash WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Commande introuvable"}
        return {"ok": True, "solde": _solde_exocash(
            _clean_id(_to_int(cur.get("IDSalarie")))
        )}

    return {"ok": False, "error": "Action non disponible"}
