"""
Service d'authentification — logique de connexion.

Transposition du code de connexion WinDev (ReqConnexion sur Bdd_Omaya_RH).
"""

from app.core.auth.security import verify_password, create_access_token
from app.core.auth.schemas import UserToken, LoginResponse
from app.core.database import get_connection
from app.shared.procedures.droits import charger_droits


def authenticate_user(email: str, password: str) -> LoginResponse | None:
    """
    Authentifie un utilisateur par email + mot de passe.

    1. Requête sur salarie + salarie_embauche + salarie_coordonnées (Bdd_Omaya_RH)
    2. Déchiffrement AES128 du mot de passe
    3. Chargement des droits via InitDroit()
    4. Génération du JWT

    Retourne None si échec d'authentification.
    """
    db = get_connection("rh")

    # Requête de connexion (transposition de ReqConnexion)
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

    # Vérification mot de passe (AES128)
    mdp_crypte = row.get("MDPCrypte", "")
    if not mdp_crypte or not verify_password(mdp_crypte, password):
        return None

    # Récupérer le profil poste (catégorie)
    prof_poste = ""
    id_type_poste = row.get("IdTypePoste")
    if id_type_poste:
        type_poste_row = db.query_one(
            "SELECT Catégorie FROM TypePoste WHERE IdTypePoste = ?",
            (id_type_poste,),
        )
        if type_poste_row:
            prof_poste = type_poste_row.get("Catégorie", "")

    # Charger les droits d'accès
    id_salarie = int(row["IDSalarie"])
    droits = charger_droits(db, id_salarie)

    # Construire le user
    user = UserToken(
        id_salarie=id_salarie,
        login=row.get("LOGIN", ""),
        nom=row.get("NOM", ""),
        prenom=(row.get("PRENOM") or "").capitalize(),
        is_actif=bool(row.get("EnActivité")),
        is_pause=bool(row.get("EnPause")),
        agenda_actif=bool(row.get("AgendaActif")),
        active_log=bool(row.get("ActiveLog")),
        gsm=row.get("TélMob") or "",
        id_ste=int(row.get("IdSte") or 0),
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
