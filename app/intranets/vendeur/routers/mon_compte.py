from fastapi import APIRouter, Depends, HTTPException

from app.core.auth.dependencies import get_current_user
from app.core.auth.schemas import UserToken
from app.core.database import get_connection
from app.intranets.vendeur.schemas.mon_compte import (
    MonCompteResponse,
    IdentiteResponse,
    CoordonneesResponse,
    DocumentItem,
)
from app.intranets.vendeur.services.ftp_documents import lister_fiches_salaire

router = APIRouter(prefix="/mon-compte", tags=["vendeur-mon-compte"])


def _charger_fiche(id_salarie: int) -> MonCompteResponse:
    db = get_connection("rh")

    row_sal = db.query_one(
        """SELECT IDSalarie, Civilité, Nom, Nom_Marital, Prenom, Sexe, Nationalité,
            Date_Naiss, Lieu_Naiss, Dep_Naiss, Num_SS, CPAM, NumCIN,
            SituationFam, AvecEnfant, NbEnfants, TravailleurHandi, Photo
        FROM salarie WHERE IDSalarie = ?""",
        (id_salarie,),
    )

    identite = IdentiteResponse(id_salarie=id_salarie)
    if row_sal:
        identite = IdentiteResponse(
            id_salarie=id_salarie,
            civilite=int(row_sal.get("Civilité") or 0),
            nom=row_sal.get("Nom") or "",
            nom_marital=row_sal.get("Nom_Marital") or "",
            prenom=row_sal.get("Prenom") or "",
            sexe=row_sal.get("Sexe") or "",
            nationalite=row_sal.get("Nationalité") or "",
            date_naiss=str(row_sal.get("Date_Naiss") or ""),
            lieu_naiss=row_sal.get("Lieu_Naiss") or "",
            dep_naiss=int(row_sal.get("Dep_Naiss") or 0),
            num_ss=row_sal.get("Num_SS") or "",
            cpam=row_sal.get("CPAM") or "",
            num_cin=row_sal.get("NumCIN") or "",
            situation_fam=int(row_sal.get("SituationFam") or 0),
            avec_enfant=bool(row_sal.get("AvecEnfant")),
            nb_enfants=int(row_sal.get("NbEnfants") or 0),
            travailleur_handi=bool(row_sal.get("TravailleurHandi")),
            photo=row_sal.get("Photo") or "",
        )

    row_coord = db.query_one(
        """SELECT Adresse1, Adresse2, CP, Ville, TélFixe, TélMob, Mail, Mail2,
            UrgNom, UrgLien, UrgTél, IBAN, BIC
        FROM salarie_coordonnées WHERE IDSalarie = ?""",
        (id_salarie,),
    )

    coordonnees = CoordonneesResponse()
    if row_coord:
        coordonnees = CoordonneesResponse(
            adresse1=row_coord.get("Adresse1") or "",
            adresse2=row_coord.get("Adresse2") or "",
            cp=row_coord.get("CP") or "",
            ville=row_coord.get("Ville") or "",
            tel_fixe=row_coord.get("TélFixe") or "",
            tel_mob=row_coord.get("TélMob") or "",
            mail=row_coord.get("Mail") or "",
            mail2=row_coord.get("Mail2") or "",
            urg_nom=row_coord.get("UrgNom") or "",
            urg_lien=row_coord.get("UrgLien") or "",
            urg_tel=row_coord.get("UrgTél") or "",
            iban=row_coord.get("IBAN") or "",
            bic=row_coord.get("BIC") or "",
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
