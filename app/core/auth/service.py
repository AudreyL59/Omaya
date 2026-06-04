"""
Service d'authentification — logique de connexion.

Transposition du code de connexion WinDev (ReqConnexion sur Bdd_Omaya_RH).

Deux backends selon l'intranet :
- intracall (Call Fibre / Energie, servis sur OVH) : tout en HFSQL.
- serveur interne (Vendeur / ADM) : PostgreSQL (cible de migration, déjà peuplée).
Le routage se fait sur le champ `intranet` du LoginRequest (cf. HFSQL_AUTH_INTRANETS).
"""

from app.core.auth.security import verify_password, create_access_token
from app.core.auth.schemas import UserToken, LoginResponse
from app.core.database import get_connection
from app.core.database.pg import get_pg_connection
from app.shared.procedures.droits import charger_droits, charger_droits_hfsql

# Intranets dont l'authentification passe par HFSQL (servis depuis intracall,
# où il n'y a pas de PostgreSQL peuplé : tout est en HFSQL).
HFSQL_AUTH_INTRANETS = {"call_fibre", "call_energie"}


def authenticate_user(
    email: str,
    password: str,
    intranet: str = "vendeur",
) -> LoginResponse | None:
    """Authentifie un utilisateur par email + mot de passe.

    Aiguille vers le backend HFSQL ou PG selon l'intranet. Retourne None si
    échec d'authentification.
    """
    if intranet in HFSQL_AUTH_INTRANETS:
        return _authenticate_hfsql(email, password, intranet)
    return _authenticate_pg(email, password, intranet)


def _build_login_response(
    id_salarie: int,
    login: str,
    nom: str,
    prenom: str,
    is_actif: bool,
    is_pause: bool,
    is_resp: bool,
    agenda_actif: bool,
    active_log: bool,
    gsm: str,
    id_ste: int,
    prof_poste: str,
    droits: list[str],
) -> LoginResponse:
    """Construit le UserToken + le JWT (commun HFSQL/PG)."""
    user = UserToken(
        id_salarie=id_salarie,
        login=login,
        nom=nom,
        prenom=(prenom or "").capitalize(),
        is_actif=is_actif,
        is_pause=is_pause,
        is_resp=is_resp,
        agenda_actif=agenda_actif,
        active_log=active_log,
        gsm=gsm or "",
        id_ste=id_ste,
        prof_poste=prof_poste,
        droits=droits,
    )
    token_data = {
        "sub": str(user.id_salarie),
        "login": user.login,
        "nom": user.nom,
        "prenom": user.prenom,
        "is_actif": user.is_actif,
        "is_pause": user.is_pause,
        "is_resp": user.is_resp,
        "agenda_actif": user.agenda_actif,
        "active_log": user.active_log,
        "gsm": user.gsm,
        "id_ste": user.id_ste,
        "prof_poste": user.prof_poste,
        "droits": user.droits,
    }
    access_token = create_access_token(token_data)
    return LoginResponse(access_token=access_token, user=user)


def _authenticate_hfsql(email: str, password: str, intranet: str) -> LoginResponse | None:
    """Authentification via HFSQL (Bdd_Omaya_RH) — transposition de ReqConnexion."""
    db = get_connection("rh")

    row = db.query_one(
        """
        SELECT
            salarie.IDSalarie,
            salarie.NOM,
            salarie.PRENOM,
            salarie.MDPCrypte,
            salarie.LOGIN,
            salarie.AgendaActif,
            salarie.ActiveLog,
            salarie_embauche.EnActivité,
            salarie_embauche.IdSte,
            salarie_embauche.IdTypePoste,
            salarie_embauche.EnPause,
            salarie_embauche.RespEquipe,
            salarie_coordonnées.TélMob
        FROM salarie_embauche
        INNER JOIN (
            salarie_coordonnées
            INNER JOIN salarie
                ON salarie_coordonnées.IDSalarie = salarie.IDSalarie
        ) ON salarie_embauche.IDSalarie = salarie.IDSalarie
        WHERE salarie.ModifELEM NOT LIKE '%suppr%'
            AND (salarie.LOGIN = ? OR salarie.LOGIN = ?)
        """,
        (email.strip().lower(), email.strip().upper()),
    )
    if not row:
        return None

    mdp_crypte = row.get("MDPCrypte", "")
    if not mdp_crypte or not verify_password(mdp_crypte, password):
        return None

    prof_poste = ""
    id_type_poste = row.get("IdTypePoste")
    if id_type_poste:
        type_poste_row = db.query_one(
            "SELECT Catégorie FROM TypePoste WHERE IdTypePoste = ?",
            (id_type_poste,),
        )
        if type_poste_row:
            prof_poste = type_poste_row.get("Catégorie", "")

    id_salarie = int(row["IDSalarie"])
    droits = charger_droits_hfsql(db, id_salarie, intranet)

    return _build_login_response(
        id_salarie=id_salarie,
        login=row.get("LOGIN", ""),
        nom=row.get("NOM", ""),
        prenom=row.get("PRENOM") or "",
        is_actif=bool(row.get("EnActivité")),
        is_pause=bool(row.get("EnPause")),
        is_resp=bool(row.get("RespEquipe")),
        agenda_actif=bool(row.get("AgendaActif")),
        active_log=bool(row.get("ActiveLog")),
        gsm=row.get("TélMob") or "",
        id_ste=int(row.get("IdSte") or 0),
        prof_poste=prof_poste,
        droits=droits,
    )


def _authenticate_pg(email: str, password: str, intranet: str) -> LoginResponse | None:
    """Authentification via PostgreSQL (schema rh, tables pgt_*)."""
    db = get_pg_connection("rh")

    row = db.query_one(
        """
        SELECT
            s.id_salarie,
            s.nom,
            s.prenom,
            s.mdp_crypte,
            s.login,
            s.agenda_actif,
            s.active_log,
            se.en_activite,
            se.id_ste,
            se.id_type_poste,
            se.en_pause,
            se.resp_equipe,
            sc.tel_mob
        FROM pgt_salarie_embauche se
        INNER JOIN pgt_salarie s ON se.id_salarie = s.id_salarie
        INNER JOIN pgt_salarie_coordonnees sc ON sc.id_salarie = s.id_salarie
        WHERE s.modif_elem NOT LIKE '%suppr%'
            AND LOWER(s.login) = LOWER(?)
        """,
        (email.strip(),),
    )
    if not row:
        return None

    mdp_crypte = row.get("mdp_crypte")
    if not mdp_crypte or not verify_password(mdp_crypte, password):
        return None

    prof_poste = ""
    id_type_poste = row.get("id_type_poste")
    if id_type_poste:
        type_poste_row = db.query_one(
            "SELECT categorie FROM pgt_type_poste WHERE id_type_poste = ?",
            (id_type_poste,),
        )
        if type_poste_row:
            prof_poste = type_poste_row.get("categorie", "")

    id_salarie = int(row["id_salarie"])
    droits = charger_droits(db, id_salarie, intranet)

    return _build_login_response(
        id_salarie=id_salarie,
        login=row.get("login", ""),
        nom=row.get("nom", ""),
        prenom=row.get("prenom") or "",
        is_actif=bool(row.get("en_activite")),
        is_pause=bool(row.get("en_pause")),
        is_resp=bool(row.get("resp_equipe")),
        agenda_actif=bool(row.get("agenda_actif")),
        active_log=bool(row.get("active_log")),
        gsm=row.get("tel_mob") or "",
        id_ste=int(row.get("id_ste") or 0),
        prof_poste=prof_poste,
        droits=droits,
    )
