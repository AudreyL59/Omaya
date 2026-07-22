"""Schemas Pydantic du module Process (bibliotheque de procedures/tutos).

3 tables :
  - divers.pgt_process         : dossier (titre, service, mots_cles, diagramme)
  - divers.pgt_process_droit   : droit d'acces (par salarie OU par profil,
                                  + societe)
  - divers.pgt_process_fichier : PJ stockees en bytea

IDs 8 octets exposes en `str` (cf. memoire feedback_ids_8octets_string).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
#  Read models
# ---------------------------------------------------------------------------

class ProcessFichierMeta(BaseModel):
    """Metadonnees d'un fichier (sans le contenu bytea)."""

    IDProcessFichier: str = ""
    Titre: str = ""
    Extension: str = ""
    TailleFic: int = 0
    DateCrea: str = ""
    DerniereModif: str = ""
    OpeCrea: str = ""
    NomOpeCrea: str = ""


class ProcessDroit(BaseModel):
    """Une ligne de droit d'acces (par salarie OU par profil, + societe).

    Regles :
      - `IDSalarie` != 0 -> ciblage nominatif
      - `TypeProfil` != "" -> ciblage par profil (niveau mini hierarchique
        pour la filiere FDV ; STAFF voit tout ; CALL/CALLRH match exact)
      - `IdSte` = 0 -> toutes societes
    """

    IDProcessDroit: str = ""
    IDProcess: str = ""
    IDSalarie: str = ""
    NomSalarie: str = ""       # resolu server-side pour l'UI
    TypeProfil: str = ""       # STAFF | FDV VRP | FDV MAN | FDV DA | FDV DR | CALL | CALLRH
    IdSte: str = ""            # id societe (0 -> "Toutes")
    LibSte: str = ""           # resolu server-side (vide si Toutes)
    DroitActif: bool = True


class Process(BaseModel):
    """Un process avec ses metadonnees + liste des PJ et droits.

    Le champ `Diagramme` reste bytea cote DB (Fen_Diagramme WinDev),
    non expose ici en V1 — editeur web tldraw prevu en V2.
    """

    IDProcess: str = ""
    Titre: str = ""
    Service: str = ""          # code libre : IT, RH, COMM, BO…
    MotsCles: str = ""
    DateCrea: str = ""
    DerniereModif: str = ""
    OpeCrea: str = ""
    NomOpeCrea: str = ""
    OpeModif: str = ""
    NomOpeModif: str = ""
    Fichiers: list[ProcessFichierMeta] = Field(default_factory=list)
    Droits: list[ProcessDroit] = Field(default_factory=list)
    Diagrammes: list["ProcessDiagrammeMeta"] = Field(default_factory=list)


class ProcessListItem(BaseModel):
    """Ligne dans la liste des process (vue compacte pour le panneau
    gauche : pas de details, juste titre + service + qui/quand)."""

    IDProcess: str = ""
    Titre: str = ""
    Service: str = ""
    MotsCles: str = ""
    DateCrea: str = ""
    DerniereModif: str = ""
    OpeCrea: str = ""
    NomOpeCrea: str = ""
    NbFichiers: int = 0


# ---------------------------------------------------------------------------
#  Write payloads
# ---------------------------------------------------------------------------

class ProcessSavePayload(BaseModel):
    """Create (IDProcess="" ou "0") ou update d'un process."""

    IDProcess: str = ""
    Titre: str
    Service: str = ""
    MotsCles: str = ""


class ProcessDroitSavePayload(BaseModel):
    """Ajout ou modification d'un droit d'acces sur un process."""

    IDProcessDroit: str = "0"
    IDProcess: str
    IDSalarie: str = "0"       # 0 si ciblage par profil
    TypeProfil: str = ""       # vide si ciblage nominatif
    IdSte: str = "0"           # 0 = toutes societes
    DroitActif: bool = True


class ProfilItem(BaseModel):
    """Un item du referentiel des profils (pour le dropdown UI)."""

    Code: str
    Lib: str = ""
    Ordre: int = 0


# ---------------------------------------------------------------------------
#  Diagrammes (N par process, stockes dans pgt_process_fichier
#  avec extension .excalidraw — meme pattern que WinDev qui stocke les
#  .wddiag comme des fichiers du process).
# ---------------------------------------------------------------------------

class ProcessDiagrammeMeta(BaseModel):
    """Metadonnees d'un diagramme (sans le contenu JSON, pour la liste
    dans le detail du process)."""

    IDProcessDiagramme: str = ""
    Titre: str = ""
    DateCrea: str = ""
    DerniereModif: str = ""
    OpeCrea: str = ""
    NomOpeCrea: str = ""


class ProcessDiagramme(BaseModel):
    """Diagramme complet (avec contenu JSON Excalidraw)."""

    IDProcessDiagramme: str = ""
    IDProcess: str = ""
    Titre: str = ""
    ContenuJson: str = ""
    DateCrea: str = ""
    DerniereModif: str = ""
    OpeCrea: str = ""


class ProcessDiagrammeSavePayload(BaseModel):
    """Create (IDProcessDiagramme='0') ou update d'un diagramme."""

    IDProcessDiagramme: str = "0"
    IDProcess: str
    Titre: str = ""
    ContenuJson: str = ""


# Resout la forward-ref dans Process.Diagrammes: list["ProcessDiagrammeMeta"]
from pydantic import ConfigDict  # noqa: E402
Process.model_rebuild()
