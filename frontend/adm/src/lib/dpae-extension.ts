/**
 * Bridge entre la page Omaya et l'extension navigateur Omaya DPAE Filler.
 *
 * L'extension injecte content-omaya.js sur ce domaine qui ecoute les
 * window.postMessage de source='omaya-dpae' et les relaie vers le service
 * worker MV3 qui dispatche aux onglets partenaires ouverts.
 *
 * Cote install : voir browser-extension/omaya-dpae/README.md
 */

const TAG = 'omaya-dpae'

export interface FillData {
  siret?: string
  login?: string
  mdp?: string
  nom?: string
  nom_marital?: string
  prenom?: string
  sexe?: string
  date_naiss?: string
  lieu_naiss?: string
  dep_naiss?: number | string
  num_ss?: string
  adresse?: string
  cp?: string
  ville?: string
  tel_mob?: string
  mail?: string
  date_debut?: string
}

export interface FillResult {
  ok: boolean
  tabs?: number
  error?: string | null
}

/** Detecte si l'extension est installee (ping/pong avec timeout). */
export function isExtensionInstalled(timeoutMs = 500): Promise<boolean> {
  return new Promise((resolve) => {
    let done = false
    const handler = (ev: MessageEvent) => {
      if (ev.source !== window) return
      const d = ev.data as { source?: string; type?: string }
      if (d?.source === TAG && d?.type === 'PONG') {
        done = true
        window.removeEventListener('message', handler)
        resolve(true)
      }
    }
    window.addEventListener('message', handler)
    window.postMessage({ source: TAG, type: 'PING' }, '*')
    setTimeout(() => {
      if (done) return
      window.removeEventListener('message', handler)
      resolve(false)
    }, timeoutMs)
  })
}

/** Envoie une requete de remplissage. Retourne {ok, tabs, error}. */
export function fillPartenaire(
  partenaire: string,
  data: FillData,
  timeoutMs = 3000,
): Promise<FillResult> {
  return new Promise((resolve) => {
    let done = false
    const handler = (ev: MessageEvent) => {
      if (ev.source !== window) return
      const d = ev.data as {
        source?: string
        type?: string
        ok?: boolean
        tabs?: number
        error?: string | null
      }
      if (d?.source === TAG && d?.type === 'FILL_RESULT') {
        done = true
        window.removeEventListener('message', handler)
        resolve({ ok: !!d.ok, tabs: d.tabs, error: d.error })
      }
    }
    window.addEventListener('message', handler)
    window.postMessage({ source: TAG, type: 'FILL', partenaire, data }, '*')
    setTimeout(() => {
      if (done) return
      window.removeEventListener('message', handler)
      resolve({ ok: false, error: 'Extension absente ou ne répond pas' })
    }, timeoutMs)
  })
}
