// Types partages du module Dialogues (chat + workflow ticket).
// IDs 8 octets tous exposes en string cote backend (JS Number depasse
// 2^53). Cf. memoire feedback_ids_8octets_string cote projet.

export interface DialogueStatut {
  IdStatut: number
  LibStatut: string
  CouleurStatut: number
}

export interface DialogueTheme {
  IdTheme: number
  LibTheme: string
  CodeDroit: string
}

export interface SalarieDest {
  ID: string
  Nom: string
  Prenom: string
}

export interface DialogueDest {
  IDDialogueDEST: string
  Dest_Ope: string
  Dest_Orga: string
  LibDest: string
}

export interface DialogueHisto {
  FaitLe: string
  NomOpe: string
  LibStatut: string
}

export interface DialoguePJ {
  IDPJ: string
  IDDialogue: string
  NomFic: string
  // URL publique complete construite cote backend (DOCS_URL + /DocConv/{id}/{nom}).
  // Vide si le backend n'a pas DOCS_URL configure -> frontend retombera
  // sur son endpoint fallback authentifie.
  Url: string
  DateHeureCreation: string
  Expediteur: string
  NomExp: string
}

export interface DialogueMsg {
  IDMessage: string
  IDDialogue: string
  Contenu: string       // URL-encoded si backend a renvoye au format JSON
  ContenuUni: string    // texte brut
  DateHeureCreation: string
  Expediteur: string
  NomExp: string
  MsgSuppr: boolean
  mesPJs: DialoguePJ[]
}

export interface Dialogue {
  IDDialogue: string
  Sujet: string
  IdStatut: number
  IdTheme: number
  LibTheme: string
  IsPrive: boolean
  DateHeureCreation: string
  Expediteur: string
  DateLecture: string
  MsgNonLu: boolean
  Dests: DialogueDest[]
  Echanges: DialogueMsg[]
  PJs: DialoguePJ[]
  Histo: DialogueHisto[]
}

export interface TacheIT {
  IDTacheIT: string
  IDDialogue: string
  Titre: string
  Contenu: string
  LibStatut: string
  CouleurStatut: number
  LibTache: string
  DateCrea: string
  OpCrea: string
  NomOpCrea: string
  OpTraitement: string
  NomOpTraitement: string
  Terminee: boolean
  TermineeDate: string
  Version: string
}

export interface DialoguePageProps {
  apiBase: string             // ex: '/api/vendeur' ou '/api/adm'
  getToken: () => string | null
  userCial: string            // id_salarie du user connecte (string)
  userNom?: string            // pour afficher "moi" vs "autre" dans les bulles
}
