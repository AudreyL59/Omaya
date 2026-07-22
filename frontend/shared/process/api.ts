// Client HTTP du module Process.

import type {
  Process, ProcessListItem, ProfilItem, SocieteItem,
} from './types'

interface Ctx {
  apiBase: string
  getToken: () => string | null
}

const auth = (ctx: Ctx) => ({ Authorization: `Bearer ${ctx.getToken()}` })
const jsonH = (ctx: Ctx) => ({ ...auth(ctx), 'Content-Type': 'application/json' })

async function req<T>(
  ctx: Ctx, method: string, path: string, body?: unknown,
): Promise<T | null> {
  try {
    const opts: RequestInit = { method, headers: auth(ctx) }
    if (body !== undefined) {
      opts.headers = jsonH(ctx)
      opts.body = JSON.stringify(body)
    }
    const r = await fetch(`${ctx.apiBase}/process${path}`, opts)
    if (!r.ok) return null
    const text = await r.text()
    return text ? (JSON.parse(text) as T) : null
  } catch {
    return null
  }
}

// -- Lecture --------------------------------------------------------------

export const fetchList = (ctx: Ctx, search: string) =>
  req<ProcessListItem[]>(
    ctx, 'GET', `?search=${encodeURIComponent(search)}`)

export const fetchOne = (ctx: Ctx, idProcess: string) =>
  req<Process>(ctx, 'GET', `/${idProcess}`)

export const fetchServices = (ctx: Ctx) =>
  req<string[]>(ctx, 'GET', '/services')

export const fetchProfils = (ctx: Ctx) =>
  req<ProfilItem[]>(ctx, 'GET', '/profils')

export const fetchSocietes = (ctx: Ctx) =>
  req<SocieteItem[]>(ctx, 'GET', '/societes')

export const fichierUrl = (ctx: Ctx, idFichier: string) =>
  `${ctx.apiBase}/process/fichier/${idFichier}`

// -- Ecriture (ADM) ------------------------------------------------------

export const saveProcess = (
  ctx: Ctx,
  payload: { IDProcess: string; Titre: string; Service: string; MotsCles: string },
) => req<{ IDProcess: string }>(ctx, 'POST', '/save', payload)

export const deleteProcess = (ctx: Ctx, idProcess: string) =>
  req<{ ok: boolean }>(ctx, 'DELETE', `/${idProcess}`)

export async function uploadFichier(
  ctx: Ctx, idProcess: string, file: File,
): Promise<{ IDProcessFichier: string } | null> {
  const fd = new FormData()
  fd.append('file', file, file.name)
  try {
    const r = await fetch(
      `${ctx.apiBase}/process/${idProcess}/fichier`,
      { method: 'POST', headers: auth(ctx), body: fd },
    )
    if (!r.ok) return null
    return await r.json()
  } catch { return null }
}

export const deleteFichier = (ctx: Ctx, idFichier: string) =>
  req<{ ok: boolean }>(ctx, 'DELETE', `/fichier/${idFichier}`)

export const saveDroit = (
  ctx: Ctx,
  payload: {
    IDProcessDroit: string; IDProcess: string
    IDSalarie: string; TypeProfil: string; IdSte: string; DroitActif: boolean
  },
) => req<{ IDProcessDroit: string }>(ctx, 'POST', '/droit/save', payload)

export const deleteDroit = (ctx: Ctx, idDroit: string) =>
  req<{ ok: boolean }>(ctx, 'DELETE', `/droit/${idDroit}`)
