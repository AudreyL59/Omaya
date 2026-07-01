"""Service Fen_RechercheVille (recherche commune France + ajout commune).

Cf code WinDev Fen_RechercheVille :
  - Recherche par CP + Nom Ville dans CommunesFrance (divers.pgt_communes_france)
  - Bouton 'Choisir cette ville' renvoie l'objet au parent (mode picker)
  - Bloc 'AJOUTER UNE VILLE' visible uniquement si droit AjoutCommune :
    * Formulaire CP + Nom + Département + CodePays (défaut FR) +
      Code Commune + Latitude + Longitude
    * Liens externes : Google (chercher code commune) + coordonneesgps.net
    * Bouton 'Ajouter la ville' -> INSERT dans CommunesFrance (favorite=False)
"""

from datetime import datetime

from pydantic import BaseModel

from app.core.database.pg import get_pg_connection


class CommuneItem(BaseModel):
    id_communes_france: str
    code_postal: str = ""
    nom_ville: str = ""
    departement: str = ""
    code_commune: str = ""
    code_pays: str = "FR"
    latitude_deg: float = 0.0
    longitude_deg: float = 0.0
    favorite: bool = False


class CommunePayload(BaseModel):
    code_postal: str
    nom_ville: str
    departement: str
    code_commune: str
    code_pays: str = "FR"
    latitude_deg: float = 0.0
    longitude_deg: float = 0.0


def search_communes(cp: str = "", nom: str = "",
                    limit: int = 500) -> list[CommuneItem]:
    """Recherche : CodePostal LIKE 'cp%' AND NomVille LIKE '%nom%'.
    Reproduit reqRechVille WinDev."""
    db = get_pg_connection("divers")
    where = ["(modif_elem IS NULL OR modif_elem NOT LIKE '%suppr%')"]
    params: list = []
    if cp:
        where.append("code_postal LIKE ?")
        params.append(f"{cp}%")
    if nom:
        # WinDev met le nom en UPPER dans la BDD, on force le uppercase
        where.append("UPPER(nom_ville) LIKE UPPER(?)")
        params.append(f"%{nom}%")

    rows = db.query(
        f"""SELECT id_communes_france, code_postal, nom_ville, departement,
                   code_commune, code_pays, latitude_deg, longitude_deg, favorite
              FROM divers.pgt_communes_france
             WHERE {' AND '.join(where)}
             ORDER BY code_postal, nom_ville
             LIMIT ?""",
        tuple(params + [int(limit)]),
    ) or []
    return [CommuneItem(
        id_communes_france=str(r["id_communes_france"]),
        code_postal=r.get("code_postal") or "",
        nom_ville=r.get("nom_ville") or "",
        departement=r.get("departement") or "",
        code_commune=r.get("code_commune") or "",
        code_pays=r.get("code_pays") or "FR",
        latitude_deg=float(r.get("latitude_deg") or 0),
        longitude_deg=float(r.get("longitude_deg") or 0),
        favorite=bool(r.get("favorite")),
    ) for r in rows]


def create_commune(p: CommunePayload, op_id: int) -> int:
    """Ajoute une commune (cf btn 'Ajouter la ville' WinDev).
    Validation : tous les champs obligatoires + coordonnees != 0.
    Retourne id_communes_france (0 si echec)."""
    if not p.code_postal or not p.nom_ville or not p.code_commune \
            or not p.departement or p.latitude_deg == 0 \
            or p.longitude_deg == 0:
        raise ValueError(
            "Merci de remplir correctement tous les champs pour que la "
            "ville soit utilisable dans la CVTHEQUE",
        )

    db = get_pg_connection("divers")
    id_new = int(datetime.now().strftime("%Y%m%d%H%M%S%f")[:17])
    # Cles composites cf schema (code_pays_code_commune, code_pays_code_postal_nom_ville)
    nom_upper = (p.nom_ville or "").upper()
    cp_ck = f"{p.code_pays}{p.code_commune}"
    cp_pn = f"{p.code_pays}{p.code_postal}{nom_upper}"
    db.query(
        """INSERT INTO divers.pgt_communes_france
              (id_communes_france, code_commune, code_postal, nom_ville,
               departement, latitude_deg, longitude_deg, code_pays, favorite,
               code_pays_code_commune, code_pays_code_postal_nom_ville,
               modif_date, modif_op, modif_elem)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, FALSE, ?, ?, NOW(), ?, 'new')""",
        (id_new, p.code_commune, p.code_postal, nom_upper,
         p.departement, float(p.latitude_deg), float(p.longitude_deg),
         p.code_pays, cp_ck, cp_pn, int(op_id)),
    )
    return id_new
