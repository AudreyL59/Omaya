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

// Convertit YYYY-MM-DD -> DD/MM/YYYY (format URSSAF)
function isoToFr(iso) {
  if (!iso || iso.length < 10) return ''
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`
}

// URSSAF DUE etape 2 : remplit le formulaire de declaration apres
// le clic sur 'Commencer la declaration'.
function fillUrssafStep2(data) {
  // Selecteurs : id colon-escape n'est pas necessaire dans une chaine
  // quotee, et [id="..."] / [name="..."] est tolere.
  let n = 0
  const f = (label, idName, value) =>
    fillField(label, [`[id="${idName}"]`, `[name="${idName}"]`], value) && n++

  f('Nom naissance', 'form_declaration:champ_nom_naiss', data.nom)
  f('Nom marital', 'form_declaration:champ_nom_marital', data.nom_marital)
  f('Prenom', 'form_declaration:champ_prenom', data.prenom)
  f('Date naissance', 'form_declaration:champ_date_naissance', isoToFr(data.date_naiss))
  f('Lieu naissance', 'form_declaration:champ_commune_naiss', data.lieu_naiss)
  f('No secu', 'form_declaration:champ_no_secu', (data.num_ss || '').replace(/\s/g, ''))
  f('Tel', 'form_declaration:champ_tel', data.tel_mob)
  f('Date embauche', 'form_declaration:date_embInputDate', isoToFr(data.date_debut))
  f('Heure embauche', 'form_declaration:champ_heure_cpl_embauche', '09:00')
  f('Periode essai', 'form_declaration:champ_periode_essai', '90')
  return n
}

const FILLERS = {
  // URSSAF DUE :
  //   etape 1 -> remplit SIRET + click submit (cf. WinDev
  //              HTMLExecuteTraitementChamp 'form_siret:form-compte-submit')
  //   etape 2 -> au reload (page suivante meme origine), reprise via
  //              sessionStorage et remplissage du formulaire declaration.
  urssaf: (data) => {
    const siret = (data.siret || data.login || '').replace(/\s/g, '')
    const ok = fillField('URSSAF SIRET', [
      'input[name="form_siret:champ_siret"]',
      'input[id*="champ_siret" i]',
      'input[name*="siret" i]',
      'input[id*="siret" i]',
      'input[placeholder*="siret" i]',
    ], siret)
    if (!ok) return 0

    // Sauve les data pour l'etape 2 (la page peut recharger apres submit)
    try {
      sessionStorage.setItem('omaya-dpae-urssaf-step2', JSON.stringify(data))
    } catch (e) {
      console.warn('[omaya-dpae] sessionStorage indispo', e)
    }

    // Click submit apres un delai (laisse le temps a la valeur d'etre prise)
    setTimeout(() => {
      const btn = findFirst([
        '[id="form_siret:form-compte-submit"]',
        'button[id*="form-compte-submit"]',
        'input[type="submit"][id*="form-compte-submit"]',
      ])
      if (btn) {
        console.log('[omaya-dpae] URSSAF click submit')
        btn.click()
      } else {
        console.warn('[omaya-dpae] URSSAF submit btn introuvable')
      }
    }, 500)
    return 1
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

// Au chargement du content script : si on est sur URSSAF apres un submit
// step 1, le sessionStorage contient les donnees a injecter en step 2.
// Le content script est re-injecte sur la nouvelle page (meme origine
// urssaf.fr), donc le storage est accessible.
;(function reprendreUrssafStep2() {
  if (!/due\.urssaf\.fr/.test(location.href)) return
  let raw = null
  try {
    raw = sessionStorage.getItem('omaya-dpae-urssaf-step2')
  } catch {}
  if (!raw) return
  let data
  try {
    data = JSON.parse(raw)
  } catch {
    sessionStorage.removeItem('omaya-dpae-urssaf-step2')
    return
  }
  // Attend 2s que le formulaire declaration soit rendu
  setTimeout(() => {
    const n = fillUrssafStep2(data)
    console.log('[omaya-dpae] URSSAF step 2 -> ' + n + ' champs remplis')
    if (n > 0) {
      try {
        sessionStorage.removeItem('omaya-dpae-urssaf-step2')
      } catch {}
    }
  }, 2000)
})()

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
