// content-portail.js
// Injecte sur les portails partenaires (urssaf.fr, gestioniag.fr, etc.).
// Recoit les donnees via chrome.runtime.onMessage et remplit les champs.

const FILLERS = {
  // URSSAF DUE : etape 1 = saisie SIRET (cf. WinDev "form_siret:champ_siret")
  urssaf: (data) => {
    setValue('input[name="form_siret:champ_siret"]', data.siret || data.login || '')
    // L'utilisateur clique manuellement sur "Commencer la declaration"
    return 1
  },

  // IAG : login + password sur la page d'accueil
  iag: (data) => {
    setValue('input[name="login"]', data.login || '')
    setValue('input[name="password"]', data.mdp || '')
    return 2
  },

  // SFR : Email + password (cf. WinDev)
  sfr: (data) => {
    setValue('input[name="Email"]', data.login || '')
    setValue('input[name="password"]', data.mdp || '')
    return 2
  },

  // ENI : username + pw
  eni: (data) => {
    setValue('input[name="username"]', data.login || '')
    setValue('input[name="pw"]', data.mdp || '')
    return 2
  },

  // Plenitude / Ohm : pas de mapping defini par WinDev, placeholder
  plenitude: (data) => {
    setValue('input[name="login"], input[name="email"]', data.login || '')
    setValue('input[name="password"]', data.mdp || '')
    return 2
  },
  ohm: (data) => {
    setValue('input[name="login"], input[name="email"]', data.login || '')
    setValue('input[name="password"]', data.mdp || '')
    return 2
  },
}

function setValue(selector, value) {
  if (!value) return false
  const el = document.querySelector(selector)
  if (!el) return false
  // Pour React/Vue : on doit dispatcher un evenement input apres setter
  const nativeSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype,
    'value',
  )?.set
  if (nativeSetter) nativeSetter.call(el, value)
  else el.value = value
  el.dispatchEvent(new Event('input', { bubbles: true }))
  el.dispatchEvent(new Event('change', { bubbles: true }))
  return true
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type !== 'FILL') return
  const fn = FILLERS[String(msg.partenaire || '').toLowerCase()]
  if (!fn) {
    sendResponse({ ok: false, error: 'Pas de filler pour ce partenaire' })
    return true
  }
  try {
    const n = fn(msg.data || {})
    sendResponse({ ok: n > 0, filled: n })
  } catch (e) {
    sendResponse({ ok: false, error: String(e) })
  }
  return true
})
