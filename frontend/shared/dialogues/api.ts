// Client HTTP du module Dialogues. Tous les endpoints sont mountes
// sous `${apiBase}/dialogues/*` (ex: /api/vendeur/dialogues/statuts).

import type {
  Dialogue, DialogueMsg, DialoguePJ, DialogueStatut, DialogueTheme,
  SalarieDest, TacheIT,
} from './types'

interface Ctx {
  apiBase: string
  getToken: () => string | null
}

const authHeaders = (ctx: Ctx) => ({
  Authorization: `Bearer ${ctx.getToken()}`,
})

const jsonHeaders = (ctx: Ctx) => ({
  ...authHeaders(ctx),
  'Content-Type': 'application/json',
})

async function req<T>(
  ctx: Ctx,
  method: string,
  path: string,
  body?: unknown,
): Promise<T | null> {
  try {
    const opts: RequestInit = { method, headers: authHeaders(ctx) }
    if (body !== undefined) {
      opts.headers = jsonHeaders(ctx)
      opts.body = JSON.stringify(body)
    }
    const r = await fetch(`${ctx.apiBase}/dialogues${path}`, opts)
    if (!r.ok) return null
    const text = await r.text()
    return text ? (JSON.parse(text) as T) : null
  } catch {
    return null
  }
}

// -- Referentiels ----------------------------------------------------------

export const fetchStatuts = (ctx: Ctx) =>
  req<DialogueStatut[]>(ctx, 'GET', '/statuts')

export const fetchThemes = (ctx: Ctx) =>
  req<DialogueTheme[]>(ctx, 'GET', '/themes')

export const fetchDestinataires = (ctx: Ctx) =>
  req<SalarieDest[]>(ctx, 'POST', '/liste-dest')

// -- Liste dialogues -------------------------------------------------------

export const fetchListeJson = (
  ctx: Ctx, typeMsg: number, userCial: string,
) => req<Dialogue[]>(ctx, 'POST', `/liste-json/${typeMsg}/${userCial}`)

// -- Marquage lu -----------------------------------------------------------

export const marquerLu = (
  ctx: Ctx, idDial: string, userCial: string,
) => req<{ nIdDemande: string; sInfoData: string }>(
  ctx, 'GET', `/marquer-lu/${idDial}/${userCial}`,
)

// -- Ecritures -------------------------------------------------------------

export const saveDialogue = (
  ctx: Ctx, userCial: string, payload: unknown,
) => req<Dialogue>(ctx, 'POST', `/enregistre/${userCial}`, payload)

export const sendMessage = (ctx: Ctx, payload: unknown) =>
  req<DialogueMsg>(ctx, 'POST', '/enregistre-pjmsg', payload)

export const modifyMessage = (ctx: Ctx, payload: unknown) =>
  req<DialogueMsg>(ctx, 'POST', '/modif-msg', payload)

export const deleteMessage = (ctx: Ctx, payload: unknown) =>
  req<DialogueMsg>(ctx, 'POST', '/suppr-msg', payload)

export const registerPJ = (ctx: Ctx, payload: unknown) =>
  req<DialoguePJ>(ctx, 'POST', '/enregistre-pj', payload)

// -- Suivi IT --------------------------------------------------------------

export const fetchTachesIT = (ctx: Ctx, idDialogue: string) =>
  req<TacheIT[]>(ctx, 'GET', `/${idDialogue}/taches-it`)

// -- Upload / download PJ --------------------------------------------------

export async function uploadFichier(
  ctx: Ctx, idDialogue: string, file: File | Blob, filename?: string,
): Promise<{ fileName: string; fileSize: number; ResEnvoi: boolean } | null> {
  const fd = new FormData()
  fd.append('file', file, filename)
  try {
    const r = await fetch(
      `${ctx.apiBase}/dialogues/upload-fichier/${idDialogue}`,
      { method: 'POST', headers: authHeaders(ctx), body: fd },
    )
    if (!r.ok) return null
    return await r.json()
  } catch {
    return null
  }
}

export const fichierUrl = (
  ctx: Ctx, idDialogue: string, nomFic: string,
) => `${ctx.apiBase}/dialogues/fichier/${idDialogue}/${encodeURIComponent(nomFic)}`
