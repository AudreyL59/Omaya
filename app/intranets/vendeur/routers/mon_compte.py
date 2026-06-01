from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.core.database.pg import get_pg_connection
from app.intranets.vendeur.schemas.mon_compte import (
    MonCompteResponse,
    IdentiteResponse,
    CoordonneesResponse,
    DocumentItem,
)
from app.intranets.vendeur.services.ftp_documents import lister_fiches_salaire

router = APIRouter(prefix="/mon-compte", tags=["vendeur-mon-compte"])


def _charger_fiche(id_salarie: int) -> MonCompteResponse:
    db = get_pg_connection("rh")

    row_sal = db.query_one(
        """SELECT id_salarie, civilite, nom, nom_marital, prenom, sexe, nationalite,
            date_naiss, lieu_naiss, dep_naiss, num_ss, cpam, num_cin,
            situation_fam, avec_enfant, nb_enfants, travailleur_handi,
            encode(photo, 'base64') AS photo_b64
        FROM pgt_salarie WHERE id_salarie = ?""",
        (id_salarie,),
    )

    identite = IdentiteResponse(id_salarie=str(id_salarie))
    if row_sal:
        identite = IdentiteResponse(
            id_salarie=str(id_salarie),
            civilite=int(row_sal.get("civilite") or 0),
            nom=row_sal.get("nom") or "",
            nom_marital=row_sal.get("nom_marital") or "",
            prenom=row_sal.get("prenom") or "",
            sexe=row_sal.get("sexe") or "",
            nationalite=row_sal.get("nationalite") or "",
            date_naiss=str(row_sal.get("date_naiss") or ""),
            lieu_naiss=row_sal.get("lieu_naiss") or "",
            dep_naiss=int(row_sal.get("dep_naiss") or 0),
            num_ss=row_sal.get("num_ss") or "",
            cpam=row_sal.get("cpam") or "",
            num_cin=row_sal.get("num_cin") or "",
            situation_fam=int(row_sal.get("situation_fam") or 0),
            avec_enfant=bool(row_sal.get("avec_enfant")),
            nb_enfants=int(row_sal.get("nb_enfants") or 0),
            travailleur_handi=bool(row_sal.get("travailleur_handi")),
            photo=(row_sal.get("photo_b64") or "").replace("\n", ""),
        )

    row_coord = db.query_one(
        """SELECT adresse1, adresse2, cp, ville, tel_fixe, tel_mob, mail, mail2,
            urg_nom, urg_lien, urg_tel, iban, bic
        FROM pgt_salarie_coordonnees WHERE id_salarie = ?""",
        (id_salarie,),
    )

    coordonnees = CoordonneesResponse()
    if row_coord:
        coordonnees = CoordonneesResponse(
            adresse1=row_coord.get("adresse1") or "",
            adresse2=row_coord.get("adresse2") or "",
            cp=row_coord.get("cp") or "",
            ville=row_coord.get("ville") or "",
            tel_fixe=row_coord.get("tel_fixe") or "",
            tel_mob=row_coord.get("tel_mob") or "",
            mail=row_coord.get("mail") or "",
            mail2=row_coord.get("mail2") or "",
            urg_nom=row_coord.get("urg_nom") or "",
            urg_lien=row_coord.get("urg_lien") or "",
            urg_tel=row_coord.get("urg_tel") or "",
            iban=row_coord.get("iban") or "",
            bic=row_coord.get("bic") or "",
        )

    return MonCompteResponse(identite=identite, coordonnees=coordonnees)

SITUATION_FAM_LABELS = {
    0: "",
    1: "Célibataire",
    2: "Marié(e)",
    3: "Pacsé(e)",
    4: "Divorcé(e)",
    5: "Veuf(ve)",
    6: "Concubinage",
}


@router.get("", response_model=MonCompteResponse)
def get_mon_compte(user: UserToken = Depends(get_current_user)):
    """Retourne les infos identité + coordonnées du salarié connecté."""
    return _charger_fiche(user.id_salarie)


@router.get("/documents", response_model=list[DocumentItem])
def get_documents(user: UserToken = Depends(get_current_user)):
    """Liste les fiches de salaire du salarié depuis le FTP."""
    return lister_fiches_salaire(user.id_salarie)


@router.get("/fiche/{id_salarie}", response_model=MonCompteResponse)
def get_fiche_salarie(
    id_salarie: int,
    user: UserToken = Depends(get_current_user),
):
    """Consulter la fiche d'un autre salarié (droit FicheVend requis)."""
    if "FicheVend" not in user.droits and id_salarie != user.id_salarie:
        raise HTTPException(status_code=403, detail="Droit FicheVend requis")
    return _charger_fiche(id_salarie)


@router.get("/fiche/{id_salarie}/documents", response_model=list[DocumentItem])
def get_fiche_documents(
    id_salarie: int,
    user: UserToken = Depends(get_current_user),
):
    """Liste les fiches de salaire d'un autre salarié (droit FicheVend requis)."""
    if "FicheVend" not in user.droits and id_salarie != user.id_salarie:
        raise HTTPException(status_code=403, detail="Droit FicheVend requis")
    return lister_fiches_salaire(id_salarie)
