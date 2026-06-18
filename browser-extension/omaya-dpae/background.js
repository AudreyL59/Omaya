// background.js (service worker MV3)
// Route les requetes 'FILL_PARTENAIRE' du content Omaya vers les onglets
// ouverts sur les portails partenaires.

const PARTENAIRE_URL_PATTERNS = {
  urssaf: ['https://www.due.urssaf.fr/*'],
  iag: ['https://*.gestioniag.fr/*'],
  sfr: ['https://*.sfr.fr/*'],
  eni: ['https://*.eni-energie.com/*'],
  plenitude: ['https://*.plenitude.com/*'],
  ohm: ['https://*.ohm-energie.com/*'],
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type !== 'FILL_PARTENAIRE') return

  const partenaire = String(msg.partenaire || '').toLowerCase()
  const patterns = PARTENAIRE_URL_PATTERNS[partenaire]
  if (!patterns) {
    sendResponse({ ok: false, error: `Partenaire inconnu : ${partenaire}` })
    return true
  }

  chrome.tabs.query({ url: patterns }, (tabs) => {
    if (!tabs || tabs.length === 0) {
      sendResponse({ ok: false, error: 'Aucun onglet partenaire ouvert', tabs: 0 })
      return
    }
    let pending = tabs.length
    let okCount = 0
    tabs.forEach((tab) => {
      chrome.tabs.sendMessage(
        tab.id,
        { type: 'FILL', partenaire, data: msg.data || {} },
        (resp) => {
          if (!chrome.runtime.lastError && resp?.ok) okCount++
          pending--
          if (pending === 0) {
            sendResponse({ ok: okCount > 0, tabs: okCount })
          }
        },
      )
    })
  })
  return true // reponse async
})
