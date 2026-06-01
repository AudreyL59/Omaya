"""
Service d'authentification — logique de connexion.

Transposition du code de connexion WinDev (ReqConnexion sur Bdd_Omaya_RH).
"""

from app.core.auth.security import verify_password, create_access_token
from app.core.auth.schemas import UserToken, LoginResponse
from app.core.database.pg import get_pg_connection
from app.shared.procedures.droits import charger_droits


def authenticate_user(
    email: str,
    password: str,
    intranet: str = "vendeur",
) -> LoginResponse | None:
    """
    Authentifie un utilisateur par email + mot de passe.

    1. Requête sur pgt_salarie + pgt_salarie_embauche + pgt_salarie_coordonnees (schema rh)
    2. Déchiffrement AES128 du mot de passe (mdp_crypte stocké en bytea)
    3. Chargement des droits via InitDroit() — filtre selon l'intranet cible
    4. Génération du JWT

    Retourne None si échec d'authentification.
    """
    db = get_pg_connection("rh")

    # Requête de connexion
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

    # Vérification mot de passe (AES128) — mdp_crypte est en bytea (bytes bruts)
    mdp_crypte = row.get("mdp_crypte")
    if not mdp_crypte or not verify_password(mdp_crypte, password):
        return None

    # Récupérer le profil poste (catégorie)
    prof_poste = ""
    id_type_poste = row.get("id_type_poste")
    if id_type_poste:
        type_poste_row = db.query_one(
            "SELECT categorie FROM pgt_type_poste WHERE id_type_poste = ?",
            (id_type_poste,),
        )
        if type_poste_row:
            prof_poste = type_poste_row.get("categorie", "")

    # Charger les droits d'accès (filtre selon l'intranet)
    id_salarie = int(row["id_salarie"])
    droits = charger_droits(db, id_salarie, intranet)

    # Construire le user
    user = UserToken(
        id_salarie=id_salarie,
        login=row.get("login", ""),
        nom=row.get("nom", ""),
        prenom=(row.get("prenom") or "").capitalize(),
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

    # Générer le JWT
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

    return LoginResponse(
        access_token=access_token,
        user=user,
    )
