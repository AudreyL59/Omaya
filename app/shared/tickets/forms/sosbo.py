"""FI_SOSBO (type 11 — SOS BO).

Transposition de la fenêtre interne WinDev FI_SOSBO. Formulaire
multi-mode selon TK_DemandeSOS_BO.IDTK_TypeSOS_BO (cf. afficherTypeDem) :

  1 Problème CALL            : PB CALL (incidentCall)
  2 Problème Attribution BS  : recherche contrat + Modifier le vendeur
  3 Problème Accès Salesforce: réf = mail
  4 Rejet manque facture     : recherche contrat + Modifier l'état
  5 Remontée Terrain Fibre   : PB CALL
  6 Coupure accès portails   : Générer Tk Désactivation Code (+ part.)

Bases : TK_DemandeSOS_BO / TK_TypeSOS_BO / TK_DemandeCodeVendeur =
ticket_bo ; TK_Liste = ticket ; Partenaire / <pfx>_contrat /
<pfx>_produit / <pfx>_etatContrat / client / incidentCall = adv ;
salarie / salarie_partenaire = rh.
"""

from app.core.database import get_connection
from app.shared.notifications.sms import envoi_sms

from ..service import (
    _clean_id,
    _now_windev,
    _to_int,
    _windev_to_iso,
    load_salaries_minimal,
    maj_op_traitement_ticket,
)

ETAT_BS_CALL_EN_COURS = 37  # cf. « Modifier l'état du BS »
TYPE_DEM_DESACTIVATION = 39  # TK_Liste.IDTK_TypeDemande (Tk Désactiv. Code)


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _nom(sid: int) -> str:
    if not sid:
        return ""
    i = load_salaries_minimal({sid}).get(sid, {})
    p = i.get("prenom", "")
    return (
        f"{i.get('nom', '')} {p[:1].upper() + p[1:].lower() if p else ''}"
        .strip()
    )


def _iso_dt_to_windev(s: str) -> str:
    """ISO 'YYYY-MM-DD[ T]HH:MM[:SS]' -> 'YYYYMMDDHHMMSS' (vide -> '')."""
    d = "".join(c for c in str(s or "") if c.isdigit())
    if len(d) < 8:
        return ""
    return (d + "00000000")[:14]


def _memo(db, id_ticket: int, field: str) -> str:
    try:
        r = db.query_one(
            f"SELECT IDTK_Liste, {field} FROM TK_DemandeSOS_BO "
            f"WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        return ((r.get(field) if r else "") or "").strip()
    except Exception:
        return ""


def _types() -> list[dict]:
    try:
        db = get_connection("ticket_bo")
        return [
            {
                "id": _to_int(r.get("IDTK_TypeSOS_BO")),
                "lib": (r.get("Lib_TypeSos") or "").strip(),
            }
            for r in db.query(
                "SELECT IDTK_TypeSOS_BO, Lib_TypeSos FROM TK_TypeSOS_BO "
                "ORDER BY Lib_TypeSos"
            )
        ]
    except Exception:
        return []


def _partenaires() -> list[dict]:
    try:
        db = get_connection("adv")
        out = []
        for r in db.query(
            "SELECT IDPartenaire, Lib_Partenaire, PréfixeBDD, IsActif "
            "FROM Partenaire WHERE IsActif = 1 ORDER BY Lib_Partenaire"
        ):
            pfx = (r.get("PréfixeBDD") or "").strip()
            if pfx:
                out.append({
                    "id": _to_int(r.get("IDPartenaire")),
                    "lib": (r.get("Lib_Partenaire") or "").strip(),
                    "prefixe": pfx,
                })
        return out
    except Exception:
        return []


# afficherTypeDem() : libellés + zones visibles selon le type
_MODES = {
    1: dict(benef="Demandeur", ref="Date et Heure", ref_kind="text",
            pbcall=True, contrats=False, modif_vendeur=False,
            modif_etat=False, desactivation=False),
    2: dict(benef="Choisir le bon VRP", ref="Num Ctt", ref_kind="text",
            pbcall=False, contrats=True, modif_vendeur=True,
            modif_etat=False, desactivation=False),
    3: dict(benef="Vendeur concerné", ref="Adresse Mail",
            ref_kind="email", pbcall=False, contrats=False,
            modif_vendeur=False, modif_etat=False, desactivation=False),
    4: dict(benef="Vendeur concerné", ref="Num Ctt", ref_kind="text",
            pbcall=False, contrats=True, modif_vendeur=False,
            modif_etat=True, desactivation=False),
    5: dict(benef="Demandeur", ref="Num Ctt", ref_kind="text",
            pbcall=True, contrats=False, modif_vendeur=False,
            modif_etat=False, desactivation=False),
    6: dict(benef="Vendeur concerné", ref="Adresse Mail",
            ref_kind="email", pbcall=False, contrats=False,
            modif_vendeur=False, modif_etat=False, desactivation=True),
}


def _mode(id_type: int) -> dict:
    return _MODES.get(int(id_type or 0), dict(
        benef="Bénéficiaire", ref="Référence", ref_kind="text",
        pbcall=False, contrats=False, modif_vendeur=False,
        modif_etat=False, desactivation=False,
    ))


# --------------------------------------------------------------------
# chercherContrat (multi-partenaire, base adv)
# --------------------------------------------------------------------

def _chercher_contrat(ref: str) -> list[dict]:
    ref = (ref or "").strip()
    if not ref:
        return []
    adv = get_connection("adv")
    rows: list[dict] = []
    cli_ids: set[int] = set()
    sal_ids: set[int] = set()
    for p in _partenaires():
        pfx = p["prefixe"]
        moisp = "MoisP_Ra" if pfx.upper() == "SFR" else "MoisP"
        sql = (
            f"SELECT pc.IDcontrat, pc.NumBS, pc.IDclient, pc.IDSalarie, "
            f"pc.DateSignature, pc.{moisp} AS MoisP, pp.Lib_produit, "
            f"pe.Lib_Etat, pe.IDetat "
            f"FROM {pfx}_contrat pc, {pfx}_produit pp, {pfx}_etatContrat pe "
            f"WHERE pc.IDproduit = pp.IDproduit "
            f"AND pc.IDetatContrat = pe.IDetat "
            f"AND pc.NumBS LIKE ? AND pc.ModifElem NOT LIKE '%suppr%'"
        )
        try:
            res = adv.query(sql, (f"{ref}%",))
        except Exception:
            continue
        for r in res or []:
            idc = _clean_id(_to_int(r.get("IDclient")))
            ids = _clean_id(_to_int(r.get("IDSalarie")))
            cli_ids.add(idc)
            sal_ids.add(ids)
            rows.append({
                "id_contrat": str(_clean_id(_to_int(r.get("IDcontrat")))),
                "partenaire": pfx,
                "n_contrat": (r.get("NumBS") or "").strip(),
                "prod": (r.get("Lib_produit") or "").strip(),
                "date_signature": _windev_to_iso(r.get("DateSignature")),
                "etat": (r.get("Lib_Etat") or "").strip(),
                "id_etat": _to_int(r.get("IDetat")),
                "mois_paiement": (str(r.get("MoisP") or "")).strip(),
                "_id_client": idc,
                "id_salarie": str(ids) if ids else "",
            })
    # Noms clients (adv) + vendeurs (rh)
    clients: dict[int, str] = {}
    if cli_ids:
        ids_sql = ",".join(str(i) for i in cli_ids if i)
        try:
            for r in adv.query(
                f"SELECT IDclient, NOM, PRENOM FROM client "
                f"WHERE IDclient IN ({ids_sql})"
            ):
                cid = _clean_id(_to_int(r.get("IDclient")))
                pn = (r.get("PRENOM") or "").strip()
                clients[cid] = (
                    f"{(r.get('NOM') or '').strip()} "
                    f"{pn[:1].upper() + pn[1:].lower() if pn else ''}".strip()
                )
        except Exception:
            pass
    sals = load_salaries_minimal(sal_ids)
    for row in rows:
        row["nom_client"] = clients.get(row.pop("_id_client"), "")
        si = sals.get(_to_int(row["id_salarie"]), {})
        sp = si.get("prenom", "")
        row["nom_vendeur"] = (
            f"{si.get('nom', '')} "
            f"{sp[:1].upper() + sp[1:].lower() if sp else ''}".strip()
        )
    return rows


# --------------------------------------------------------------------
# load / save
# --------------------------------------------------------------------

def load(id_ticket: int) -> dict:
    db = get_connection("ticket_bo")
    r = db.query_one(
        """SELECT IDTK_Liste, IDTK_DemandeSOS_BO, Bénéficiaire,
            IDTK_TypeSOS_BO, Ref_A_contrôler
        FROM TK_DemandeSOS_BO WHERE IDTK_Liste = ?""",
        (int(id_ticket),),
    )
    if not r:
        return {"found": False}

    id_type = _to_int(r.get("IDTK_TypeSOS_BO"))
    benef = _clean_id(_to_int(r.get("Bénéficiaire")))
    ref = (r.get("Ref_A_contrôler") or "").strip()
    info_cplt = _memo(db, id_ticket, "InfoCplt")
    mode = _mode(id_type)

    out = {
        "found": True,
        "id_demande": str(_clean_id(_to_int(r.get("IDTK_DemandeSOS_BO")))),
        "id_type": id_type,
        "types": _types(),
        "benef_id": str(benef) if benef else "",
        "benef_nom": _nom(benef),
        "ref": ref,
        "info_cplt": info_cplt,
        "mode": mode,
        "partenaires": _partenaires() if mode["desactivation"] else [],
    }
    if mode["contrats"] and ref:
        out["contrats"] = _chercher_contrat(ref)
    else:
        out["contrats"] = []
    return out


def save(id_ticket: int, payload: dict, user_id: int) -> dict:
    action = str(payload.get("action") or "enregistrer")
    now = _now_windev()

    # --- recherche de contrats (chercherContrat) ---
    if action == "search_contrat":
        return {
            "ok": True,
            "contrats": _chercher_contrat(str(payload.get("ref") or "")),
        }

    # --- Enregistrer le contenu du ticket ---
    if action == "enregistrer":
        db = get_connection("ticket_bo")
        cur = db.query_one(
            "SELECT IDTK_DemandeSOS_BO FROM TK_DemandeSOS_BO "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not cur:
            return {"ok": False, "error": "Demande SOS BO introuvable"}
        db.query(
            """UPDATE TK_DemandeSOS_BO SET
                Bénéficiaire = ?, IDTK_TypeSOS_BO = ?, Ref_A_contrôler = ?,
                InfoCplt = ?, ModifDate = ?, ModifOP = ?, ModifELEM = 'new'
            WHERE IDTK_Liste = ?""",
            (
                _to_int(payload.get("benef_id")),
                _to_int(payload.get("id_type")),
                str(payload.get("ref") or "").strip(),
                str(payload.get("info_cplt") or ""),
                now, int(user_id), int(id_ticket),
            ),
        )
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True}

    # --- Envoyer un SMS « demande traitée » ---
    if action == "sms_traite":
        tk = get_connection("ticket").query_one(
            "SELECT IDTK_Liste, OPCREA FROM TK_Liste WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not tk:
            return {"ok": False, "error": "Ticket introuvable"}
        op_crea = _clean_id(_to_int(tk.get("OPCREA")))
        gsm = ""
        try:
            rc = get_connection("rh").query_one(
                "SELECT IDSalarie, TélMob FROM salarie_coordonnées "
                "WHERE IDSalarie = ?",
                (int(op_crea),),
            )
            gsm = ((rc.get("TélMob") if rc else "") or "").replace(".", "").strip()
        except Exception:
            gsm = ""
        if not gsm:
            return {"ok": False, "error": "Pas de mobile pour le demandeur"}
        type_lib = str(payload.get("type_lib") or "").strip()
        benef_nom = str(payload.get("benef_nom") or "").strip()
        txt = (
            f"Votre demande au BO : {type_lib}, pour {benef_nom} "
            "est bien traité."
        )
        try:
            res = envoi_sms(txt, gsm, "", "OMAYA-Info")
        except Exception as e:
            res = f"erreur : {e}"
        return {"ok": True, "sms_result": res}

    # --- Générer Tk Désactivation Code (nouveau ticket type 39) ---
    if action == "gen_desactivation":
        id_part = _to_int(payload.get("id_partenaire"))
        if not id_part:
            return {"ok": False, "error": "Choisis un partenaire"}
        bo = get_connection("ticket_bo")
        d = bo.query_one(
            "SELECT IDTK_Liste, Bénéficiaire FROM TK_DemandeSOS_BO "
            "WHERE IDTK_Liste = ?",
            (int(id_ticket),),
        )
        if not d:
            return {"ok": False, "error": "Demande SOS BO introuvable"}
        benef = _clean_id(_to_int(d.get("Bénéficiaire")))
        sp = None
        try:
            sp = get_connection("rh").query_one(
                "SELECT IDSalarie, IDPartenaire, Code, LOGIN, MDP "
                "FROM salarie_partenaire "
                "WHERE IDSalarie = ? AND IDPartenaire = ?",
                (int(benef), int(id_part)),
            )
        except Exception:
            sp = None
        if not sp:
            return {
                "ok": False,
                "error": "Ce vendeur n'a pas de code pour le "
                         "partenaire sélectionné",
            }
        id_new = int(now)
        try:
            bo.query(
                """INSERT INTO TK_DemandeCodeVendeur
                (IDTK_DemandeCodeVendeur, IDTK_Liste, TypeOri, IDElem,
                 IDPartenaire, Code, LOGIN, MDP, ModifDate, ModifElem,
                 ModifOp)
                VALUES (?, ?, 'TK', ?, ?, ?, ?, ?, ?, 'new', ?)""",
                (
                    id_new, id_new, int(id_ticket), int(id_part),
                    str(sp.get("Code") or ""), str(sp.get("LOGIN") or ""),
                    str(sp.get("MDP") or ""), now, int(user_id),
                ),
            )
            get_connection("ticket").query(
                """INSERT INTO TK_Liste
                (IDTK_Liste, DATECREA, OPCREA, OPDEST, OpTraitementStaff,
                 OrdreTraitementStaff, Service, IDTK_TypeDemande,
                 IDTK_Statut, Cloturée, ModifDate, ModifOP, ModifELEM)
                VALUES (?, ?, ?, ?, 0, 0, 'BO', ?, 1, 0, ?, ?, 'New')""",
                (
                    id_new, now, int(user_id), int(user_id),
                    TYPE_DEM_DESACTIVATION, now, int(user_id),
                ),
            )
        except Exception as e:
            return {"ok": False, "error": f"Création ticket : {e}"}
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True, "id_nouveau_ticket": str(id_new)}

    # --- PB CALL : créer / modifier un incidentCall ---
    if action == "incident_save":
        adv = get_connection("adv")
        id_inc = _to_int(payload.get("id_incident"))
        debut = _iso_dt_to_windev(payload.get("debut"))
        fin = _iso_dt_to_windev(payload.get("fin"))
        comment = str(payload.get("commentaire") or "")
        try:
            if not id_inc:
                id_inc = int(now)
                adv.query(
                    """INSERT INTO incidentCall
                    (IDincidentCall, DateDEBUT, DateFIN, commentaire,
                     ModifDate, ModifOP, ModifELEM)
                    VALUES (?, ?, ?, ?, ?, ?, 'new')""",
                    (id_inc, debut, fin, comment, now, int(user_id)),
                )
            else:
                adv.query(
                    """UPDATE incidentCall SET
                        DateDEBUT = ?, DateFIN = ?, commentaire = ?,
                        ModifDate = ?, ModifOP = ?, ModifELEM = 'modif'
                    WHERE IDincidentCall = ?""",
                    (debut, fin, comment, now, int(user_id), int(id_inc)),
                )
        except Exception as e:
            return {"ok": False, "error": f"incidentCall : {e}"}
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True, "id_incident": str(id_inc)}

    # --- Modifier le vendeur du BS ---
    if action == "modif_vendeur_bs":
        pfx = str(payload.get("partenaire") or "").strip()
        id_contrat = _to_int(payload.get("id_contrat"))
        new_vendeur = _to_int(payload.get("benef_id"))
        old_vendeur = _to_int(payload.get("id_salarie_old"))
        num = str(payload.get("n_contrat") or "")
        if not (pfx and id_contrat and new_vendeur):
            return {"ok": False, "error": "Paramètres incomplets"}
        adv = get_connection("adv")
        try:
            adv.query(
                f"UPDATE {pfx}_contrat SET IDSalarie = ?, ModifDate = ? "
                f"WHERE IDcontrat = ?",
                (int(new_vendeur), now, int(id_contrat)),
            )
        except Exception as e:
            return {"ok": False, "error": f"Réattribution : {e}"}
        # AjoutHistoriqueAttribution (best-effort)
        try:
            adv.query(
                f"""INSERT INTO {pfx}_histoAttrCtt
                (idHisto, TypeCtt, IDcontrat, NUM, OPSAISIE, DATE,
                 VendeurOld, VendeurNew, ModifOP, ModifDate, ModifELEM)
                VALUES (?, '', ?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (int(now), int(id_contrat), num, int(user_id), now,
                 int(old_vendeur), int(new_vendeur), int(user_id), now),
            )
        except Exception:
            pass
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True}

    # --- Modifier l'état du BS (-> 37 BS CALL en cours) ---
    if action == "modif_etat_bs":
        pfx = str(payload.get("partenaire") or "").strip()
        id_contrat = _to_int(payload.get("id_contrat"))
        old_etat = _to_int(payload.get("id_etat_old"))
        if not (pfx and id_contrat):
            return {"ok": False, "error": "Paramètres incomplets"}
        adv = get_connection("adv")
        try:
            adv.query(
                f"UPDATE {pfx}_contrat SET IDetatContrat = ?, "
                f"ModifDate = ? WHERE IDcontrat = ?",
                (ETAT_BS_CALL_EN_COURS, now, int(id_contrat)),
            )
        except Exception as e:
            return {"ok": False, "error": f"Changement d'état : {e}"}
        # ajouteHistoContrat (best-effort)
        try:
            adv.query(
                f"""INSERT INTO {pfx}_histoEtatCtt
                (idHisto, IDcontrat, OPSAISIE, DATE, OLD_etat, NEW_etat,
                 ModifOP, ModifDate, ModifELEM)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new')""",
                (int(now), int(id_contrat), int(user_id), now,
                 int(old_etat), ETAT_BS_CALL_EN_COURS, int(user_id), now),
            )
        except Exception:
            pass
        maj_op_traitement_ticket(int(id_ticket), int(user_id))
        return {"ok": True}

    return {"ok": False, "error": "Action non disponible"}
