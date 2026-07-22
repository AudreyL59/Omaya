"""Schemas Pydantic du module Dialogues (chat + workflow ticket).

Portage des structures WinDev :
  St_Dialogue / St_DialogueStatut / St_DialogueTheme / St_DialogueDEST /
  St_DialogueHISTO / ST_DialogueMSG / ST_DialoguePJ

Convention IDs : tous les IDs 8 octets (WinDev idEntierDateHeureSys)
sont exposés en `str` côté API (JS Number depasse 2^53).
Cf. memoire feedback_ids_8octets_string.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
#  Référentiels
# ---------------------------------------------------------------------------

class DialogueStatut(BaseModel):
    """Portage St_DialogueStatut."""

    IdStatut: int
    LibStatut: str = ""
    CouleurStatut: int = 0


class DialogueTheme(BaseModel):
    """Portage St_DialogueTheme."""

    IdTheme: int
    LibTheme: str = ""
    CodeDroit: str = ""


class SalarieDest(BaseModel):
    """Portage ST_SALARIE réduit (uniquement les champs utilisés
    par le module Dialogues)."""

    ID: str = ""
    Nom: str = ""
    Prenom: str = ""


# ---------------------------------------------------------------------------
#  Dialogue : destinataires / histo / PJ / message
# ---------------------------------------------------------------------------

class DialogueDest(BaseModel):
    """Portage St_DialogueDEST : destinataire d'un dialogue.

    Un dialogue peut avoir plusieurs destinataires ; chacun est
    soit un opérateur (`Dest_Ope > 0`) soit une orga (`Dest_Orga > 0`).
    """

    IDDialogueDEST: str = ""
    Dest_Ope: str = ""
    Dest_Orga: str = ""
    LibDest: str = ""  # résolu côté service (nom salarié ou lib_orga)


class DialogueHisto(BaseModel):
    """Portage St_DialogueHISTO : entrée d'historique de statut."""

    FaitLe: str = ""
    NomOpe: str = ""
    LibStatut: str = ""


class DialoguePJ(BaseModel):
    """Portage ST_DialoguePJ : pièce jointe.

    `Url` est renseigné cote backend a partir de DOCS_URL du .env :
    ex. https://interne.omaya.fr/DocConv/{id_dialogue}/{nom_fic}.
    Les fichiers sont exposes par IIS statiquement (pas d'auth), meme
    pattern que l'app Flutter existante.
    """

    IDPJ: str = ""
    IDDialogue: str = ""
    NomFic: str = ""
    Url: str = ""
    DateHeureCreation: str = ""
    Expediteur: str = ""
    NomExp: str = ""


class DialogueMsg(BaseModel):
    """Portage ST_DialogueMSG : message textuel + PJ regroupées."""

    IDMessage: str = ""
    IDDialogue: str = ""
    Contenu: str = ""       # URL-encode si Format='JSON' coté WinDev
    ContenuUni: str = ""    # texte brut (unicode)
    DateHeureCreation: str = ""
    Expediteur: str = ""
    NomExp: str = ""
    MsgSuppr: bool = False
    mesPJs: list[DialoguePJ] = Field(default_factory=list)


class Dialogue(BaseModel):
    """Portage St_Dialogue : agrégat renvoyé par ListeJSON.

    Contient toutes les données dénormalisées d'un dialogue
    (dests, messages, PJs, historique).
    """

    IDDialogue: str = ""
    Sujet: str = ""
    IdStatut: int = 0
    IdTheme: int = 0
    LibTheme: str = ""
    IsPrive: bool = False
    DateHeureCreation: str = ""
    Expediteur: str = ""
    DateLecture: str = ""
    MsgNonLu: bool = False
    Dests: list[DialogueDest] = Field(default_factory=list)
    Echanges: list[DialogueMsg] = Field(default_factory=list)
    PJs: list[DialoguePJ] = Field(default_factory=list)
    Histo: list[DialogueHisto] = Field(default_factory=list)


# ---------------------------------------------------------------------------
#  Payloads d'écriture
# ---------------------------------------------------------------------------

class DialogueSavePayload(BaseModel):
    """Création (IDDialogue=0) ou modification d'un dialogue.

    Aligne sur ce que WinDev Dialogue_Enr attend :
    Dialogue1 = JSONVersVariant(sFiltreClient).
    """

    IDDialogue: str = ""    # "" ou "0" = création
    Sujet: str = ""
    IdTheme: int = 0
    Expediteur: str = ""    # renseigné côté client
    Dests: list[DialogueDest] = Field(default_factory=list)


class DialogueMsgPayload(BaseModel):
    """Envoi d'un message + PJ attachées (WinDev Dialogue_EnrPJMSG)."""

    IDMessage: str = "0"           # forcé côté serveur (nouveau)
    IDDialogue: str
    ContenuUni: str = ""
    Contenu: str = "JSON"          # format demandé pour la réponse
    DateHeureCreation: str = ""
    Expediteur: str
    NomExp: str = ""
    MsgSuppr: bool = False
    mesPJs: list[DialoguePJ] = Field(default_factory=list)


class DialoguePJPayload(BaseModel):
    """Enregistrement PJ après upload (WinDev Dialogue_EnrPJ)."""

    IDPJ: str = "0"
    IDDialogue: str
    Expediteur: str
    NomFic: str


class MsgModifPayload(BaseModel):
    """Modification d'un message existant (WinDev Dialogue_ModifMSG)."""

    IDMessage: str
    IDDialogue: str = ""
    ContenuUni: str = ""
    Contenu: str = "JSON"


class MsgSupprPayload(BaseModel):
    """Suppression logique d'un message (WinDev Dialogue_SupprMSG)."""

    IDMessage: str
    IDDialogue: str = ""


# ---------------------------------------------------------------------------
#  Réponses simples
# ---------------------------------------------------------------------------

class TacheIT(BaseModel):
    """Portage St_TacheIT (partie affichee dans l'onglet 'Suivi IT'
    d'un dialogue). Regroupe la tache et son statut/type resolu."""

    IDTacheIT: str = ""
    IDDialogue: str = ""
    Titre: str = ""
    Contenu: str = ""
    LibStatut: str = ""
    CouleurStatut: int = 0         # WinDev COLORREF (R + G*256 + B*65536)
    LibTache: str = ""             # libelle du type de tache
    DateCrea: str = ""             # ISO
    OpCrea: str = ""
    NomOpCrea: str = ""            # 'NOM Prenom'
    OpTraitement: str = ""
    NomOpTraitement: str = ""
    Terminee: bool = False
    TermineeDate: str = ""
    Version: str = ""


class ReponseTK(BaseModel):
    """Portage STRéponseTK : réponse standard des procs d'écriture."""

    nIdDemande: str = "0"
    sInfoData: str = ""
