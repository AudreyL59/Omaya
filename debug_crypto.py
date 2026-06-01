from app.core.database.pg import get_pg_connection
from app.core.auth.security import verify_password

LOGIN_TESTE = ""   # <-- mets ICI ce que tu tapes dans l'intranet
MDP_TESTE   = ""                  # le mdp qu'on vient de dechiffrer

db = get_pg_connection("rh")

# 1. La requete de login trouve-t-elle ta ligne ?
row = db.query_one(
    """SELECT s.id_salarie, s.login, s.nom, s.prenom, s.mdp_crypte,
              se.en_activite, sc.tel_mob
       FROM pgt_salarie_embauche se
       INNER JOIN pgt_salarie s ON se.id_salarie = s.id_salarie
       INNER JOIN pgt_salarie_coordonnees sc ON sc.id_salarie = s.id_salarie
       WHERE s.modif_elem NOT LIKE '%suppr%'
         AND LOWER(s.login) = LOWER(?)""",
    (LOGIN_TESTE,)
)
print(f"\n--- Resultat requete login ---")
print(f"row trouvee : {row is not None}")
if row:
    print(f"id_salarie  = {row['id_salarie']}")
    print(f"login en bd = '{row['login']}'")
    print(f"nom         = '{row['nom']}'")
    print(f"taille mdp  = {len(bytes(row['mdp_crypte']))} octets")
    print(f"en_activite = {row['en_activite']}")
    print(f"\n--- Verification mdp ---")
    print(f"verify_password = {verify_password(row['mdp_crypte'], MDP_TESTE)}")
