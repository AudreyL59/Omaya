// content-portail.js
// Injecte sur les portails partenaires (urssaf.fr, gestioniag.fr, etc.)
// y compris dans les iframes (cf. all_frames:true dans manifest).
// Recoit les donnees via chrome.runtime.onMessage et remplit les champs.

console.log('[omaya-dpae] content-portail loaded on', location.href)

function setValue(el, value) {
  if (!el || value == null) return false
  const proto =
    el instanceof HTMLTextAreaElement
      ? window.HTMLTextAreaElement.prototype
      : el instanceof HTMLSelectElement
        ? window.HTMLSelectElement.prototype
        : window.HTMLInputElement.prototype
  const nativeSetter = Object.getOwnPropertyDescriptor(proto, 'value')?.set
  if (nativeSetter) nativeSetter.call(el, String(value))
  else el.value = String(value)
  el.dispatchEvent(new Event('input', { bubbles: true }))
  el.dispatchEvent(new Event('change', { bubbles: true }))
  return true
}

/** Essaye plusieurs selecteurs CSS, retourne le 1er element trouve. */
function findFirst(selectors) {
  for (const sel of selectors) {
    try {
      const el = document.querySelector(sel)
      if (el) return el
    } catch {
      /* selecteur invalide, on continue */
    }
  }
  return null
}

function fillField(label, selectors, value) {
  if (!value) return false
  const el = findFirst(selectors)
  if (!el) {
    console.warn(`[omaya-dpae] champ '${label}' introuvable`, selectors)
    return false
  }
  const ok = setValue(el, value)
  console.log(`[omaya-dpae] ${label} = ${value} -> ${ok}`)
  return ok
}

const FILLERS = {
  // URSSAF DUE (etape 1 : saisie du SIRET de l'employeur)
  urssaf: (data) => {
    const siret = (data.siret || data.login || '').replace(/\s/g, '')
    return fillField('URSSAF SIRET', [
      'input[name="form_siret:champ_siret"]',
      'input[id*="champ_siret" i]',
      'input[name*="siret" i]',
      'input[id*="siret" i]',
      'input[placeholder*="siret" i]',
    ], siret) ? 1 : 0
  },

  // IAG : page de login
  iag: (data) => {
    let n = 0
    if (fillField('IAG login', ['input[name="login"]'], data.login)) n++
    if (fillField('IAG password', ['input[name="password"]'], data.mdp)) n++
    return n
  },

  // SFR : Email + password
  sfr: (data) => {
    let n = 0
    if (fillField('SFR email', ['input[name="Email"]', 'input[type="email"]'], data.login)) n++
    if (fillField('SFR password', ['input[name="password"]', 'input[type="password"]'], data.mdp)) n++
    return n
  },

  // ENI : username + pw
  eni: (data) => {
    let n = 0
    if (fillField('ENI user', ['input[name="username"]'], data.login)) n++
    if (fillField('ENI pw', ['input[name="pw"]'], data.mdp)) n++
    return n
  },

  // Plenitude / Ohm : pas de mapping WinDev defini, sondage generique
  plenitude: (data) => {
    let n = 0
    if (fillField('Plenitude login', ['input[name="login"]', 'input[name="email"]', 'input[type="email"]'], data.login)) n++
    if (fillField('Plenitude pw', ['input[name="password"]', 'input[type="password"]'], data.mdp)) n++
    return n
  },
  ohm: (data) => {
    let n = 0
    if (fillField('Ohm login', ['input[name="login"]', 'input[name="email"]', 'input[type="email"]'], data.login)) n++
    if (fillField('Ohm pw', ['input[name="password"]', 'input[type="password"]'], data.mdp)) n++
    return n
  },
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type !== 'FILL') return
  const partenaire = String(msg.partenaire || '').toLowerCase()
  console.log('[omaya-dpae] FILL', partenaire, msg.data)
  const fn = FILLERS[partenaire]
  if (!fn) {
    sendResponse({ ok: false, error: `Pas de filler pour ${partenaire}` })
    return true
  }
  try {
    const n = fn(msg.data || {})
    sendResponse({ ok: n > 0, filled: n })
  } catch (e) {
    console.error('[omaya-dpae] fill error', e)
    sendResponse({ ok: false, error: String(e) })
  }
  return true
})
