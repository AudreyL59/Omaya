"""
Service Fen_SMSPerf - Envoi effectif (proc Animation_SmsPerf).

Cf. WinDev D:\\Claude\\WinDev\\Proc Globales\\Animation_SmsPerf.txt (~573 lignes).

Recalcule les scores + envoie les SMS pour tous les codes animations
actifs a une date donnee.

Structure :
1. Charge les codes anim distincts actifs
2. Pour chaque code : charge orgas scores, orgas destinataires, regles
3. Pour chaque regle : charge la prod du partenaire sur la periode +
   filtre horaire + agrege par vendeur/equipe/agence
4. Compose les messages selon prod_groupe (Vend/Eq/Ag) et sms_groupe
5. Envoie les SMS via envoi_sms (smsmode.com) + historise
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Optional

from app.core.database.pg import get_pg_connection
from app.intranets.adm.schemas.sms_perf import (
    EnvoyerSmsParams, EnvoyerSmsResult,
)

logger = logging.getLogger(__name__)

_TYPE_SMS = "Perf-Exo"


# --------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------

def _new_id() -> int:
    n = datetime.now()
    return int(n.strftime("%Y%m%d%H%M%S") + f"{n.microsecond // 1000:03d}")


def _first_day_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _last_day_of_week(d: date) -> date:
    return d + timedelta(days=6 - d.weekday())


def _first_day_of_month(d: date) -> date:
    return d.replace(day=1)


def _last_day_of_month(d: date) -> date:
    if d.month == 12:
        return date(d.year, 12, 31)
    return date(d.year, d.month + 1, 1) - timedelta(days=1)


def _cap_prenom(p: str) -> str:
    if not p:
        return ""
    return p[0].upper() + p[1:].lower() if len(p) > 1 else p.upper()


def _norm_lib(s: str) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).upper()


# --------------------------------------------------------------------
# Chargements
# --------------------------------------------------------------------

def _list_active_codes() -> list[str]:
    """Codes anim distincts avec au moins une regle active."""
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT DISTINCT code_animation
             FROM divers.pgt_smsanimation_regleenvoi
            WHERE is_actif = TRUE
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND type_sms = ?
            ORDER BY code_animation""",
        (_TYPE_SMS,),
    ) or []
    return [(r.get("code_animation") or "").strip()
            for r in rows if r.get("code_animation")]


def _load_regles_by_code(code_anim: str) -> list[dict]:
    """Cf. WinDev reqAnimRegles_ByCode : regles actives d'un code
    (peuvent etre multiples : 1 par partenaire), tri par ordre.
    """
    db = get_pg_connection("rh")
    return db.query(
        """SELECT id_sms_animation_regle_envoi AS id_regle, code_animation,
                  texte_sms, heure_envoi, heure_debut, heure_fin, ordre,
                  sms_groupe, partenaire, prod_groupe, periode_calcul,
                  nb_bs_min
             FROM divers.pgt_smsanimation_regleenvoi
            WHERE is_actif = TRUE
              AND code_animation = ?
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND type_sms = ?
            ORDER BY ordre ASC""",
        (code_anim, _TYPE_SMS),
    ) or []


def _load_orga_score_ids(code_anim: str, date_jour: date) -> set[int]:
    """Cf. WinDev Animation_OrgaScore : orgas incluses dans les scores
    sur ce code a la date. Return set(idorganigramme) descendants inclus.
    """
    db = get_pg_connection("rh")
    rows = db.query(
        """SELECT idorganigramme, du, au
             FROM divers.pgt_sms_animation_orga_periode
            WHERE code_animation = ?
              AND type = ?
              AND is_actif = TRUE
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND (du IS NULL OR du <= ?)
              AND (au IS NULL OR au >= ?)""",
        (code_anim, _TYPE_SMS,
         date_jour.isoformat(), date_jour.isoformat()),
    ) or []
    if not rows:
        return set()
    root_ids = [int(r.get("idorganigramme") or 0)
                for r in rows if r.get("idorganigramme")]
    if not root_ids:
        return set()

    # Recuperation recursive des descendants
    result: set[int] = set(root_ids)
    to_process = list(root_ids)
    while to_process:
        parents = tuple(to_process)
        to_process = []
        placeholders = ",".join(["?"] * len(parents))
        try:
            children = db.query(
                f"""SELECT idorganigramme FROM pgt_organigramme
                     WHERE id_parent IN ({placeholders})
                       AND (modif_elem IS NULL
                            OR modif_elem NOT LIKE '%suppr%')""",
                parents,
            ) or []
        except Exception:
            break
        for c in children:
            oid = int(c.get("idorganigramme") or 0)
            if oid and oid not in result:
                result.add(oid)
                to_process.append(oid)
    return result


def _load_nums_dest(code_anim: str, date_jour: date) -> list[str]:
    """Cf. WinDev Animation_NumDest : numeros de tel des salaries membres
    des orgas destinataires du code a la date + staff destinataire global.
    """
    db = get_pg_connection("rh")
    # 1. Orgas destinataires (SmsAnimation_OrgaDest)
    dest_rows = db.query(
        """SELECT idorganigramme
             FROM divers.pgt_smsanimation_orgadest
            WHERE anim_code = ?
              AND is_actif = TRUE
              AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
              AND (du IS NULL OR du <= ?)
              AND (au IS NULL OR au >= ?)""",
        (code_anim, date_jour.isoformat(), date_jour.isoformat()),
    ) or []
    orga_ids: set[int] = set()
    for r in dest_rows:
        oid = int(r.get("idorganigramme") or 0)
        if oid:
            orga_ids.add(oid)

    # Descendants recursifs
    if orga_ids:
        to_process = list(orga_ids)
        while to_process:
            parents = tuple(to_process)
            to_process = []
            placeholders = ",".join(["?"] * len(parents))
            try:
                children = db.query(
                    f"""SELECT idorganigramme FROM pgt_organigramme
                         WHERE id_parent IN ({placeholders})
                           AND (modif_elem IS NULL
                                OR modif_elem NOT LIKE '%suppr%')""",
                    parents,
                ) or []
            except Exception:
                break
            for c in children:
                oid = int(c.get("idorganigramme") or 0)
                if oid and oid not in orga_ids:
                    orga_ids.add(oid)
                    to_process.append(oid)

    nums: set[str] = set()
    if orga_ids:
        placeholders = ",".join(["?"] * len(orga_ids))
        try:
            rows = db.query(
                f"""SELECT DISTINCT c.tel_mob
                     FROM pgt_salarie_organigramme so
                     JOIN pgt_salarie_coordonnees c
                          ON c.id_salarie = so.id_salarie
                     JOIN pgt_salarie_embauche e
                          ON e.id_salarie = so.id_salarie
                    WHERE so.idorganigramme IN ({placeholders})
                      AND (so.date_debut IS NULL OR so.date_debut <= ?)
                      AND (so.date_fin IS NULL OR so.date_fin >= ?)
                      AND e.en_activite = TRUE
                      AND (so.modif_elem IS NULL
                           OR so.modif_elem NOT LIKE '%suppr%')""",
                tuple(orga_ids) + (
                    date_jour.isoformat(), date_jour.isoformat(),
                ),
            ) or []
        except Exception:
            logger.exception("_load_nums_dest orgas")
            rows = []
        for r in rows:
            tel = (r.get("tel_mob") or "").strip()
            if tel:
                nums.add(tel)

    # 2. Staff destinataire global (pgt_smsanimation.liste_num_staff)
    try:
        r = db.query_one(
            """SELECT liste_num_staff FROM divers.pgt_smsanimation
                WHERE type_sms = ? LIMIT 1""",
            (_TYPE_SMS,),
        )
    except Exception:
        r = None
    if r:
        liste = (r.get("liste_num_staff") or "").strip()
        if liste:
            ids = [x.strip() for x in liste.split(";")
                   if x.strip().isdigit()]
            if ids:
                placeholders = ",".join(["?"] * len(ids))
                try:
                    rows = db.query(
                        f"""SELECT DISTINCT tel_mob
                             FROM pgt_salarie_coordonnees
                            WHERE id_salarie IN ({placeholders})""",
                        tuple(int(x) for x in ids),
                    ) or []
                except Exception:
                    rows = []
                for row in rows:
                    tel = (row.get("tel_mob") or "").strip()
                    if tel:
                        nums.add(tel)
    return sorted(nums)


# --------------------------------------------------------------------
# Chargement prod selon partenaire
# --------------------------------------------------------------------

def _load_prods(
    partenaire: str, date_deb: datetime, date_fin: datetime,
) -> list[dict]:
    """Cf. WinDev switch selon Partenaire : charge les 'ventes' entre
    date_deb et date_fin selon la source.

    Retourne liste de {id_source, id_salarie, datecrea, num_date_saisie}.
    """
    part = (partenaire or "").strip()
    db = get_pg_connection("ticket_bo")

    if part == "SFR":
        try:
            return db.query(
                """SELECT DISTINCT
                          tl.id_tk_liste AS id_source,
                          tl.datecrea,
                          tk.id_salarie,
                          tkp.num_date_saisie
                     FROM ticket_bo.pgt_tk_call_sfr_panier tkp
                     JOIN ticket_bo.pgt_tk_call_sfr tk
                          ON tk.id_tk_call_sfr = tkp.id_tk_call_sfr
                     JOIN ticket_bo.pgt_tk_liste tl
                          ON tl.id_tk_liste = tk.id_tk_liste
                    WHERE tkp.type = 'FIBRE'
                      AND (tkp.statut_prod = 1 OR tkp.statut_prod = 3)
                      AND tl.datecrea BETWEEN ? AND ?
                      AND tkp.num NOT LIKE 'TK%'
                      AND tkp.num <> ''
                      AND (tkp.modif_elem IS NULL
                           OR tkp.modif_elem NOT LIKE '%suppr%')""",
                (date_deb.isoformat(sep=" "), date_fin.isoformat(sep=" ")),
            ) or []
        except Exception:
            logger.exception("_load_prods SFR")
            return []

    if part == "Coopt":
        rh = get_pg_connection("rh")
        try:
            return rh.query(
                """SELECT DISTINCT
                          id_cvtheque AS id_source,
                          date_saisie AS datecrea,
                          ope_saisie AS id_salarie,
                          modif_date AS num_date_saisie
                     FROM recrutement.pgt_cvtheque
                    WHERE origine = 2
                      AND date_saisie BETWEEN ? AND ?
                      AND ope_saisie <> 0
                      AND (modif_elem IS NULL
                           OR modif_elem NOT LIKE '%suppr%')""",
                (date_deb.isoformat(sep=" "), date_fin.isoformat(sep=" ")),
            ) or []
        except Exception:
            logger.exception("_load_prods Coopt")
            return []

    if part == "JO":
        rh = get_pg_connection("rh")
        try:
            return rh.query(
                """SELECT DISTINCT
                          id_salarie AS id_source,
                          jo_coopteur AS id_salarie,
                          date_debut AS datecrea,
                          date_debut AS num_date_saisie
                     FROM pgt_salarie_embauche
                    WHERE jo_directe = TRUE
                      AND date_debut BETWEEN ? AND ?
                      AND jo_coopteur <> 0
                      AND jo_coopteur <> 6""",
                (date_deb.date().isoformat(), date_fin.date().isoformat()),
            ) or []
        except Exception:
            logger.exception("_load_prods JO")
            return []

    if part == "NonProd":
        # Salaries FDV MAN/VRP actifs SANS TK ni TK_CallSFR sur la periode
        rh = get_pg_connection("rh")
        try:
            return rh.query(
                """SELECT DISTINCT
                          e.id_salarie AS id_source,
                          e.id_salarie,
                          e.date_debut AS datecrea,
                          e.date_debut AS num_date_saisie
                     FROM pgt_salarie_embauche e
                     JOIN pgt_salarie s ON s.id_salarie = e.id_salarie
                     LEFT JOIN pgt_type_poste tp
                            ON tp.id_type_poste = e.id_type_poste
                    WHERE e.date_debut <= ?
                      AND e.id_ste <> 4
                      AND e.en_activite = TRUE
                      AND e.id_salarie > 6
                      AND (tp.categorie = 'FDV MAN'
                           OR tp.categorie = 'FDV VRP')
                      AND (s.modif_elem IS NULL
                           OR s.modif_elem NOT LIKE '%suppr%')""",
                (date_fin.date().isoformat(),),
            ) or []
        except Exception:
            logger.exception("_load_prods NonProd")
            return []

    # Autres partenaires : TK_Call_Panier avec Partenaire = X
    try:
        return db.query(
            """SELECT DISTINCT
                      tl.id_tk_liste AS id_source,
                      tl.datecrea,
                      tk.id_salarie,
                      tkp.num_date_saisie
                 FROM ticket_bo.pgt_tk_call_panier tkp
                 JOIN ticket_bo.pgt_tk_call tk
                      ON tk.id_tk_call = tkp.id_tk_call
                 JOIN ticket_bo.pgt_tk_liste tl
                      ON tl.id_tk_liste = tk.id_tk_liste
                WHERE tkp.partenaire = ?
                  AND (tkp.statut_prod = 1 OR tkp.statut_prod = 3)
                  AND tl.datecrea BETWEEN ? AND ?
                  AND tkp.num_bs NOT LIKE 'TK%'
                  AND tkp.num_bs <> ''
                  AND (tkp.modif_elem IS NULL
                       OR tkp.modif_elem NOT LIKE '%suppr%')""",
            (
                part,
                date_deb.isoformat(sep=" "),
                date_fin.isoformat(sep=" "),
            ),
        ) or []
    except Exception:
        logger.exception("_load_prods %s", part)
        return []


# --------------------------------------------------------------------
# Helpers salarie / organigramme
# --------------------------------------------------------------------

def _load_salarie_infos(id_salarie: int, date_ref: date) -> Optional[dict]:
    """Retourne { nom, prenom, id_equipe, lib_equipe, id_parent,
    lib_parent, id_type_niveau_orga } pour un salarie a une date.
    """
    rh = get_pg_connection("rh")
    try:
        s = rh.query_one(
            "SELECT nom, prenom FROM pgt_salarie WHERE id_salarie = ?",
            (id_salarie,),
        )
    except Exception:
        return None
    if not s:
        return None
    try:
        eq = rh.query_one(
            """SELECT o.idorganigramme, o.lib_orga, o.id_parent,
                      o.id_type_niveau_orga,
                      p.lib_orga AS parent_lib
                 FROM pgt_salarie_organigramme so
                 JOIN pgt_organigramme o
                      ON o.idorganigramme = so.idorganigramme
                 LEFT JOIN pgt_organigramme p
                        ON p.idorganigramme = o.id_parent
                WHERE so.id_salarie = ?
                  AND (so.modif_elem IS NULL
                       OR so.modif_elem NOT LIKE '%suppr%')
                  AND (so.date_debut IS NULL OR so.date_debut <= ?)
                  AND (so.date_fin IS NULL OR so.date_fin >= ?)
                ORDER BY so.date_debut DESC NULLS LAST
                LIMIT 1""",
            (id_salarie, date_ref.isoformat(), date_ref.isoformat()),
        )
    except Exception:
        eq = None
    if not eq:
        return None
    return {
        "nom": (s.get("nom") or "").strip(),
        "prenom": (s.get("prenom") or "").strip(),
        "id_equipe": int(eq.get("idorganigramme") or 0),
        "lib_equipe": (eq.get("lib_orga") or "").strip(),
        "id_parent": int(eq.get("id_parent") or 0),
        "lib_parent": (eq.get("parent_lib") or "").strip(),
        "id_type_niveau_orga": int(eq.get("id_type_niveau_orga") or 0),
    }


def _nom_vendeur(prenom: str, nom: str) -> str:
    """Format 'Prenom N' (cf. WinDev)."""
    if not prenom:
        return nom
    if not nom:
        return _cap_prenom(prenom)
    return f"{_cap_prenom(prenom)} {nom[0].upper()}"


# --------------------------------------------------------------------
# Historique (evite doublons)
# --------------------------------------------------------------------

def _already_sent(code_animation: str, date_jour: date) -> bool:
    """Cf. WinDev reqAnimation : verifie si un HistoAnimation existe."""
    db = get_pg_connection("rh")
    try:
        r = db.query_one(
            """SELECT id_histo_animation
                 FROM divers.pgt_histo_animation
                WHERE code_animation = ?
                  AND date_envoi_sms = ?
                  AND (modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')
                LIMIT 1""",
            (code_animation, date_jour.isoformat()),
        )
    except Exception:
        return False
    return bool(r)


def _mark_sent(code_animation: str, date_jour: date, op_id: int) -> None:
    db = get_pg_connection("rh")
    try:
        db.execute(
            """INSERT INTO divers.pgt_histo_animation
                  (id_histo_animation, code_animation, date_envoi_sms,
                   modif_date, modif_op, modif_elem)
               VALUES (?, ?, ?, NOW(), ?, 'new')""",
            (
                _new_id(), code_animation, date_jour.isoformat(),
                int(op_id),
            ),
        )
    except Exception:
        logger.exception("_mark_sent %s", code_animation)


# --------------------------------------------------------------------
# Proc principale
# --------------------------------------------------------------------

def animation_sms_perf(
    p: EnvoyerSmsParams, op_id: int, simulation: bool = True,
) -> EnvoyerSmsResult:
    """Cf. WinDev Animation_SmsPerf(DateJour).

    Args:
        p.date_jour : date pour laquelle recalculer + envoyer
        op_id : id salarie qui declenche
        simulation : True (defaut) = pas d'envoi reel, juste calcul + logs
                     False = envoi SMS via smsmode.com + historique
    """
    try:
        date_jour = date.fromisoformat(p.date_jour[:10])
    except Exception:
        return EnvoyerSmsResult(ok=False, message="Date invalide")

    codes = _list_active_codes()
    if not codes:
        return EnvoyerSmsResult(
            ok=True, message="Aucune regle active",
        )

    stats = {
        "nb_regles": 0, "nb_sms_envoyes": 0, "nb_erreurs": 0,
        "nb_deja_envoyes": 0, "logs": [],
    }
    now = datetime.now()

    # Import envoi SMS (lazy pour tests sans SMS_API_KEY)
    envoi_sms = None
    if not simulation:
        try:
            from app.shared.notifications.sms import (
                envoi_sms as _envoi_sms,
            )
            envoi_sms = _envoi_sms
        except ImportError:
            envoi_sms = None

    for code_anim in codes:
        # Check si deja envoye pour ce code + date
        if _already_sent(code_anim, date_jour):
            stats["nb_deja_envoyes"] += 1
            stats["logs"].append(f"{code_anim} : deja envoye")
            continue

        # Charge configuration
        orga_score_ids = _load_orga_score_ids(code_anim, date_jour)
        nums_dest = _load_nums_dest(code_anim, date_jour)
        if not nums_dest:
            stats["logs"].append(f"{code_anim} : aucun destinataire")
            continue
        regles = _load_regles_by_code(code_anim)
        if not regles:
            continue

        # Compose les messages sur toutes les regles de ce code
        messages: dict[str, str] = {}
        for regle in regles:
            stats["nb_regles"] += 1
            _compute_messages_for_regle(
                regle, date_jour, now, orga_score_ids, messages,
            )

        # Envoi (ou simulation)
        for code_msg, msg in messages.items():
            if not msg.strip():
                continue
            if simulation:
                stats["logs"].append(f"{code_msg} : {msg[:120]}...")
                continue
            envoi_ok = False
            for num in nums_dest:
                if envoi_sms is None:
                    stats["nb_erreurs"] += 1
                    continue
                try:
                    result = envoi_sms(msg, num)
                    if result.startswith("SMS envoye"):
                        envoi_ok = True
                        stats["nb_sms_envoyes"] += 1
                    else:
                        stats["nb_erreurs"] += 1
                        stats["logs"].append(
                            f"KO {num}: {result[:60]}",
                        )
                except Exception as e:
                    stats["nb_erreurs"] += 1
                    stats["logs"].append(f"exc {num}: {e}")
            if envoi_ok:
                _mark_sent(code_msg, date_jour, op_id)

    return EnvoyerSmsResult(
        ok=True,
        nb_sms_envoyes=stats["nb_sms_envoyes"],
        nb_regles_traitees=stats["nb_regles"],
        message=(
            f"{stats['nb_regles']} regles - {stats['nb_sms_envoyes']} SMS - "
            f"{stats['nb_erreurs']} erreurs - {stats['nb_deja_envoyes']} deja envoyes"
            + (" (SIMULATION)" if simulation else "")
        ),
    )


def _compute_messages_for_regle(
    regle: dict, date_jour: date, now: datetime,
    orga_score_ids: set[int], messages: dict[str, str],
) -> None:
    """Calcul + composition des messages pour une regle donnee.

    Modifie 'messages' en place avec les fragments generes.
    """
    def _to_h(v) -> int:
        if v is None:
            return 0
        if isinstance(v, int):
            return v
        if hasattr(v, "hour"):
            return int(v.hour)
        try:
            return int(str(v).split(":")[0])
        except Exception:
            return 0
    periode = int(regle.get("periode_calcul") or 1)
    heure_envoi = _to_h(regle.get("heure_envoi"))
    heure_debut = _to_h(regle.get("heure_debut"))
    heure_fin = _to_h(regle.get("heure_fin")) or 23
    partenaire = (regle.get("partenaire") or "").strip()
    code_anim = (regle.get("code_animation") or "").strip()
    prod_groupe = int(regle.get("prod_groupe") or 1)
    sms_groupe = bool(regle.get("sms_groupe"))
    nb_bs_min = int(regle.get("nb_bs_min") or 1)
    texte_sms = (regle.get("texte_sms") or "").strip()

    # Determine periode + testSMS
    if periode == 1:  # Journalier
        date_deb_d = date_jour
        date_fin_d = date_jour
        test_sms = True
    elif periode == 2:  # Hebdomadaire
        date_deb_d = _first_day_of_week(date_jour)
        date_fin_d = _last_day_of_week(date_jour)
        test_sms = (date_jour == date_fin_d)
    else:  # Mensuel
        date_deb_d = _first_day_of_month(date_jour)
        date_fin_d = _last_day_of_month(date_jour)
        test_sms = (date_jour == date_fin_d)

    if not test_sms:
        return
    # Verif heure envoi
    if heure_envoi > now.hour and date_jour == now.date():
        return

    date_deb = datetime.combine(date_deb_d, datetime.min.time()).replace(
        hour=heure_debut,
    )
    date_fin = datetime.combine(date_fin_d, datetime.min.time()).replace(
        hour=heure_fin, minute=59, second=59,
    )

    # Charge la prod
    prods = _load_prods(partenaire, date_deb, date_fin)
    if not prods:
        return

    infos_prod_v: dict[int, int] = {}
    infos_prod_eq: dict[int, int] = {}
    infos_prod_ag: dict[int, int] = {}
    lib_eq: dict[int, str] = {}
    liste_ids_seen: set = set()

    for prod in prods:
        id_sal = int(prod.get("id_salarie") or 0)
        if not id_sal:
            continue
        id_source = prod.get("id_source")
        if id_source in liste_ids_seen:
            continue
        infos = _load_salarie_infos(id_sal, date_jour)
        if not infos:
            continue
        id_eq = infos["id_equipe"]
        # Filtre : orga doit etre dans le scope des scores
        if orga_score_ids and id_eq not in orga_score_ids:
            continue

        # Filtre horaire (heure signature dans plage)
        datecrea = prod.get("datecrea")
        if isinstance(datecrea, datetime):
            h_sign = datecrea.hour
        else:
            h_sign = 0
        if not (heure_debut <= h_sign <= heure_fin):
            continue

        liste_ids_seen.add(id_source)
        infos_prod_v[id_sal] = infos_prod_v.get(id_sal, 0) + 1
        infos_prod_eq[id_eq] = infos_prod_eq.get(id_eq, 0) + 1
        lib_eq[id_eq] = (
            f"Eq {infos['lib_equipe'][:20]}"
        )
        # Compte au niveau agence
        id_parent = infos["id_parent"]
        infos_prod_ag[id_parent] = infos_prod_ag.get(id_parent, 0) + 1
        lib_eq[id_parent] = (
            f"Ag {infos['lib_parent'][:20]}"
        )

    # Compose les messages selon prod_groupe
    if prod_groupe == 1:  # Vendeur
        _compose_vendeur(
            code_anim, regle, infos_prod_v, sms_groupe, texte_sms,
            nb_bs_min, heure_envoi, date_jour, messages,
        )
    elif prod_groupe == 2:  # Equipe
        _compose_groupe(
            code_anim, regle, infos_prod_eq, lib_eq, sms_groupe,
            texte_sms, nb_bs_min, heure_envoi, messages,
        )
    elif prod_groupe == 3:  # Agence
        _compose_groupe(
            code_anim, regle, infos_prod_ag, lib_eq, sms_groupe,
            texte_sms, nb_bs_min, heure_envoi, messages,
        )


def _compose_vendeur(
    code_anim: str, regle: dict, infos_prod_v: dict[int, int],
    sms_groupe: bool, texte_sms: str, nb_bs_min: int, heure_envoi: int,
    date_jour: date, messages: dict[str, str],
) -> None:
    """Composition messages type 'Vendeur'."""
    if not sms_groupe:
        # SMS individuel : 1 par vendeur >= nb_bs_min
        for id_sal, nb in infos_prod_v.items():
            if nb < nb_bs_min:
                continue
            infos = _load_salarie_infos(id_sal, date_jour)
            if not infos:
                continue
            nom_vend = _nom_vendeur(infos["prenom"], infos["nom"])
            code_msg = (
                f"{code_anim}_{nb}" if heure_envoi == 0 else code_anim
            )
            msg = texte_sms.replace("[NOM]", nom_vend).replace(
                "[SCORE]", str(nb),
            )
            messages[f"{id_sal}_{code_msg}"] = msg
    else:
        # SMS groupe : liste des vendeurs dans [LISTE]
        liste_vend: list[str] = []
        for id_sal, nb in infos_prod_v.items():
            if nb < nb_bs_min:
                continue
            infos = _load_salarie_infos(id_sal, date_jour)
            if not infos:
                continue
            nom_vend = _nom_vendeur(infos["prenom"], infos["nom"])
            liste_vend.append(f" - {nom_vend} : {nb}")
        if liste_vend:
            msg = texte_sms.replace("[LISTE]", "\n" + "\n".join(liste_vend))
            existing = messages.get(code_anim, "")
            messages[code_anim] = (existing + "\n" + msg).strip()


def _compose_groupe(
    code_anim: str, regle: dict, infos_prod: dict[int, int],
    lib_eq: dict[int, str], sms_groupe: bool, texte_sms: str,
    nb_bs_min: int, heure_envoi: int, messages: dict[str, str],
) -> None:
    """Composition messages type 'Equipe' ou 'Agence'."""
    if not sms_groupe:
        for id_orga, nb in infos_prod.items():
            if nb < nb_bs_min or id_orga <= 0:
                continue
            nom = lib_eq.get(id_orga, str(id_orga))
            code_msg = (
                f"{code_anim}_{nb}" if heure_envoi == 0 else code_anim
            )
            msg = texte_sms.replace("[NOM]", nom).replace(
                "[SCORE]", str(nb),
            )
            existing = messages.get(f"{id_orga}_{code_msg}", "")
            messages[f"{id_orga}_{code_msg}"] = existing + msg
    else:
        liste_lignes: list[str] = []
        for id_orga, nb in infos_prod.items():
            if nb < nb_bs_min or id_orga <= 0:
                continue
            nom = lib_eq.get(id_orga, str(id_orga))
            liste_lignes.append(f" - {nom} : {nb}")
        if liste_lignes:
            msg = texte_sms.replace(
                "[LISTE]", "\n" + "\n".join(liste_lignes),
            )
            existing = messages.get(code_anim, "")
            messages[code_anim] = (existing + "\n\n" + msg).strip()
