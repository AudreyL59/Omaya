// Types partages du module Process.
// IDs 8 octets exposes en string cote backend (JS Number > 2^53).

export interface ProcessListItem {
  IDProcess: string
  Titre: string
  Service: string
  MotsCles: string
  DateCrea: string
  DerniereModif: string
  OpeCrea: string
  NomOpeCrea: string
  NbFichiers: number
}

export interface ProcessFichierMeta {
  IDProcessFichier: string
  Titre: string
  Extension: string
  TailleFic: number
  DateCrea: string
  DerniereModif: string
  OpeCrea: string
  NomOpeCrea: string
  OpeModif: string
  NomOpeModif: string
}

export interface ProcessDroit {
  IDProcessDroit: string
  IDProcess: string
  IDSalarie: string
  NomSalarie: string
  TypeProfil: string
  IdSte: string
  LibSte: string
  DroitActif: boolean
}

export interface Process {
  IDProcess: string
  Titre: string
  Service: string
  MotsCles: string
  DateCrea: string
  DerniereModif: string
  OpeCrea: string
  NomOpeCrea: string
  OpeModif: string
  NomOpeModif: string
  Fichiers: ProcessFichierMeta[]
  Droits: ProcessDroit[]
  Diagrammes: ProcessDiagrammeMeta[]
}

export interface ProcessDiagrammeMeta {
  IDProcessDiagramme: string
  Titre: string
  DateCrea: string
  DerniereModif: string
  OpeCrea: string
  NomOpeCrea: string
  OpeModif: string
  NomOpeModif: string
}

export interface ProcessDiagramme {
  IDProcessDiagramme: string
  IDProcess: string
  Titre: string
  ContenuJson: string
  DateCrea: string
  DerniereModif: string
  OpeCrea: string
}

export interface ProfilItem {
  Code: string
  Lib: string
  Ordre: number
}

export interface SocieteItem {
  IdSte: string
  Lib: string
}

export interface SalarieHit {
  ID: string
  Nom: string
  Prenom: string
  Lib: string
}

export interface ProcessPageProps {
  apiBase: string       // '/api/vendeur' | '/api/adm'
  getToken: () => string | null
  canEdit: boolean      // ADM = true, Vendeur = false
}
