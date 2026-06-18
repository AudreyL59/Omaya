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

// Retry setter du select dep_naiss (combo lazy loaded - les options
// peuvent ne pas etre encore dans le DOM au 1er essai).
function setDepNaissWithRetry(rawValue, attemptsLeft) {
  const sel = document.getElementById('form_declaration:champ_dept_naiss')
  if (!sel) {
    if (attemptsLeft > 0) {
      setTimeout(() => setDepNaissWithRetry(rawValue, attemptsLeft - 1), 500)
    } else {
      console.warn('[omaya-dpae] dep_naiss select introuvable')
    }
    return
  }
  const opts = Array.from(sel.options)
  if (opts.length <= 1) {
    if (attemptsLeft > 0) {
      console.log('[omaya-dpae] dep_naiss options non chargees, retry...')
      setTimeout(() => setDepNaissWithRetry(rawValue, attemptsLeft - 1), 500)
    } else {
      console.warn('[omaya-dpae] dep_naiss options jamais chargees')
    }
    return
  }
  // Essaye plusieurs formats (zero-pad, brut, padding 3 chiffres)
  const candidates = [
    rawValue,
    String(parseInt(rawValue, 10) || rawValue).padStart(2, '0'),
    String(parseInt(rawValue, 10) || rawValue).padStart(3, '0'),
  ]
  let matched = null
  for (const v of candidates) {
    const opt = opts.find((o) => o.value === v)
    if (opt) {
      matched = opt
      break
    }
  }
  if (!matched) {
    console.warn(
      '[omaya-dpae] dep_naiss valeur', rawValue, 'non trouvee. Options dispo (5 premieres):',
      opts.slice(0, 5).map((o) => `${o.value}=${o.textContent.trim()}`),
    )
    return
  }
  sel.value = matched.value
  const wrapper = sel.closest('.select-custom')
  const label = wrapper?.querySelector('.select-custom__label')
  if (label) label.textContent = matched.textContent.trim()
  sel.dispatchEvent(new Event('change', { bubbles: true }))
  console.log('[omaya-dpae] dep_naiss ->', matched.value, matched.textContent.trim())
}

// URSSAF DUE etape 2 : remplit le formulaire de declaration apres
// le clic sur 'Commencer la declaration'.
//
// Conformement au JS WinDev original, on click sur chaque input avant
// de dispatcher 'change' pour forcer la revalidation cote site URSSAF
// (sinon les listeners onBlur/onChange ne se declenchent pas toujours).
function fillUrssafStep2(data) {
  let n = 0
  const f = (label, idName, value) =>
    fillField(label, [`[id="${idName}"]`, `[name="${idName}"]`], value) && n++

  // Helper specifique pour les inputs widgetises (date PrimeFaces) :
  // focus + setValue + dispatch input/change/blur
  const fInputDeep = (label, idName, value) => {
    if (!value) return false
    const el = document.getElementById(idName)
    if (!el) {
      console.warn(`[omaya-dpae] champ '${label}' (${idName}) introuvable`)
      return false
    }
    try { el.focus() } catch {}
    const proto = window.HTMLInputElement.prototype
    const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set
    if (setter) setter.call(el, String(value))
    else el.value = String(value)
    el.dispatchEvent(new Event('input', { bubbles: true }))
    el.dispatchEvent(new Event('change', { bubbles: true }))
    el.dispatchEvent(new Event('blur', { bubbles: true }))
    console.log(`[omaya-dpae] ${label} (deep) = ${value}`)
    return true
  }

  f('Nom naissance', 'form_declaration:champ_nom_naiss', data.nom)
  f('Nom marital', 'form_declaration:champ_nom_marital', data.nom_marital)
  f('Prenom', 'form_declaration:champ_prenom', data.prenom)
  f('Date naissance', 'form_declaration:champ_date_naissance', isoToFr(data.date_naiss))
  f('Lieu naissance', 'form_declaration:champ_commune_naiss', data.lieu_naiss)

  // No secu : log explicite si vide cote Omaya
  const numSs = (data.num_ss || '').replace(/\s/g, '')
  if (!numSs) {
    console.warn('[omaya-dpae] No_secu vide cote Omaya - aucun remplissage')
  } else if (fInputDeep('No secu', 'form_declaration:champ_no_secu', numSs)) {
    n++
  }

  f('Tel', 'form_declaration:champ_tel', data.tel_mob)

  // Date embauche : widget PrimeFaces calendar -> focus + blur en plus
  if (fInputDeep('Date embauche', 'form_declaration:date_embInputDate', isoToFr(data.date_debut))) {
    n++
  }

  f('Heure embauche', 'form_declaration:champ_heure_cpl_embauche', '09:00')
  f('Periode essai', 'form_declaration:champ_periode_essai', '90')

  // Force le focus + revalidation des champs critiques (cf. WinDev .click()
  // suivi de dispatchEvent('change')).
  for (const id of [
    'form_declaration:champ_nom_naiss',
    'form_declaration:champ_nom_marital',
    'form_declaration:champ_prenom',
    'form_declaration:champ_date_naissance',
    'form_declaration:champ_no_secu',
  ]) {
    const el = document.getElementById(id)
    if (el) {
      try { el.click() } catch {}
      el.dispatchEvent(new Event('change', { bubbles: true }))
    }
  }

  // Departement de naissance : combo native + wrapper '.select-custom'
  // qui doit etre mis a jour manuellement. Souvent en lazy load -> retry
  // jusqu'a 5x toutes les 500ms.
  if (data.dep_naiss != null && data.dep_naiss !== '' && data.dep_naiss !== 0) {
    setDepNaissWithRetry(String(data.dep_naiss), 5)
    n++
  } else {
    console.warn('[omaya-dpae] dep_naiss vide cote Omaya - aucun remplissage')
  }

  // Type de contrat : radio par defaut form_declaration:champ_contrat:0 (CDI)
  const radioContrat = document.getElementById('form_declaration:champ_contrat:0')
  if (radioContrat) {
    radioContrat.click()
    n++
  }

  // Sexe : radio H (champ_sexe:0) ou F (champ_sexe:1)
  const sexeKey = (data.sexe || '').toUpperCase() === 'H' ? '0' : '1'
  const radioSexe = document.getElementById(`form_declaration:champ_sexe:${sexeKey}`)
  if (radioSexe) {
    radioSexe.click()
    n++
  }

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

  // IAG : page de login + validation du formulaire myForm
  // cf. WinDev : HTMLValeurChamp(login/password) + HTMLValideFormulaire(myForm)
  // Apres submit -> dashboard.php, le content script est re-injecte et
  // reprend les data via sessionStorage pour remplir l'etape 2.
  iag: (data) => {
    let n = 0
    if (fillField('IAG login', ['input[name="login"]'], data.login)) n++
    if (fillField('IAG password', ['input[name="password"]'], data.mdp)) n++
    if (n > 0) {
      // Sauve pour l'etape 2 (dashboard.php apres login)
      try {
        sessionStorage.setItem('omaya-dpae-iag-step2', JSON.stringify(data))
      } catch (e) {
        console.warn('[omaya-dpae] sessionStorage indispo', e)
      }
      // Valide myForm apres 500ms
      setTimeout(() => {
        const submitBtn = findFirst([
          'form[name="myForm"] button[type="submit"]',
          'form[name="myForm"] input[type="submit"]',
          'form[id="myForm"] button[type="submit"]',
          'form[id="myForm"] input[type="submit"]',
          'form[name="myForm"] [type="submit"]',
        ])
        if (submitBtn) {
          console.log('[omaya-dpae] IAG click submit myForm')
          submitBtn.click()
        } else {
          const form =
            document.forms?.myForm ||
            document.querySelector('form[name="myForm"], form[id="myForm"]')
          if (form) {
            console.log('[omaya-dpae] IAG submit myForm (fallback)')
            form.submit()
          } else {
            console.warn('[omaya-dpae] IAG myForm introuvable')
          }
        }
      }, 500)
    }
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

// IAG step 2 : apres le submit du login, dashboard.php (meme origine
// gestioniag.fr) doit recevoir les infos identitaires du candidat.
// cf. WinDev : nom, prenom, adr1, adr2, cp, ville, teleph.
function fillIagStep2(data) {
  let n = 0
  if (fillField('IAG nom', ['input[name="nom"]'], data.nom)) n++
  if (fillField('IAG prenom', ['input[name="prenom"]'], data.prenom)) n++
  if (fillField('IAG adr1', ['input[name="adr1"]'], data.adresse)) n++
  if (fillField('IAG adr2', ['input[name="adr2"]'], data.adresse2)) n++
  if (fillField('IAG cp', ['input[name="cp"]'], data.cp)) n++
  if (fillField('IAG ville', ['input[name="ville"]'], data.ville)) n++
  if (fillField('IAG teleph', ['input[name="teleph"]'], data.tel_mob)) n++
  return n
}

// Generique : si on est sur le bon domaine avec un flag sessionStorage,
// reprend les data et rejoue la step 2 apres un delai de stabilisation.
function reprendreStep2(domainRegex, storageKey, fillFn, delayMs) {
  if (!domainRegex.test(location.href)) return
  let raw = null
  try {
    raw = sessionStorage.getItem(storageKey)
  } catch {}
  if (!raw) return
  let data
  try {
    data = JSON.parse(raw)
  } catch {
    sessionStorage.removeItem(storageKey)
    return
  }
  setTimeout(() => {
    const n = fillFn(data)
    console.log(`[omaya-dpae] ${storageKey} -> ${n} champs remplis`)
    if (n > 0) {
      try {
        sessionStorage.removeItem(storageKey)
      } catch {}
    }
  }, delayMs)
}

;(function reprises() {
  reprendreStep2(/due\.urssaf\.fr/, 'omaya-dpae-urssaf-step2', fillUrssafStep2, 2000)
  reprendreStep2(/gestioniag\.fr/, 'omaya-dpae-iag-step2', fillIagStep2, 2000)
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
