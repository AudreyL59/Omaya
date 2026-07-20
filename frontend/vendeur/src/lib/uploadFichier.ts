/**
 * Upload d'un fichier vers WinDev /RecepFichier via le proxy
 * `/api/vendeur/ticket-call/upload-fichier`.
 *
 * Retourne le JSON de la reponse WS (typiquement `{ ResEnvoi: true|1 }`).
 *
 * cf. project_ticket_call_upload_paths.md : le chemin serveur cible
 * (`fileName`) est a demander au user au cas par cas.
 */

import { getToken } from '@/api'

const API = '/api/vendeur/ticket-call/upload-fichier'


export interface UploadResult {
  ok: boolean
  raw?: any
  error?: string
}


/**
 * Poste un fichier au proxy (le proxy relaie vers /RecepFichier WinDev
 * avec le boundary multipart specifique).
 *
 * @param file       fichier a envoyer (PDF, PNG, ...)
 * @param fileName   nom cible cote serveur DocOmaya (ex:
 *                   '20260720123456_PieceIdentite.pdf').
 */
export async function uploadFichier(
  file: Blob | File | Uint8Array,
  fileName: string,
): Promise<UploadResult> {
  const fd = new FormData()
  const blob = file instanceof Uint8Array
    ? new Blob([file.slice().buffer as ArrayBuffer], { type: 'application/octet-stream' })
    : (file instanceof File ? file : file)
  fd.append('file', blob, fileName)
  fd.append('file_name', fileName)

  try {
    const r = await fetch(API, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: fd,
    })
    if (!r.ok) {
      const txt = await r.text()
      return { ok: false, error: `HTTP ${r.status} - ${txt.slice(0, 200)}` }
    }
    const data = await r.json().catch(() => ({}))
    // WinDev peut renvoyer {ResEnvoi: true|1} — on tolere les 2
    const okFlag = data?.ResEnvoi === true || data?.ResEnvoi === 1
                    || Object.keys(data).length === 0
    return { ok: !!okFlag, raw: data }
  } catch (e: any) {
    return { ok: false, error: e?.message || 'Erreur reseau' }
  }
}
