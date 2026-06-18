// background.js (service worker MV3)
// Route les requetes 'FILL_PARTENAIRE' du content Omaya vers les onglets
// OU les frames (iframes) ouverts sur les portails partenaires.
//
// 2 modes :
//   1. Le portail est ouvert dans un onglet separe -> chrome.tabs.query
//   2. Le portail est embarque en iframe sur la page Omaya elle-meme
//      -> chrome.webNavigation.getAllFrames sur le tab sender + ciblage
//         par frameId via chrome.tabs.sendMessage(tabId, msg, {frameId})

const PARTENAIRE_URL_PATTERNS = {
  urssaf: ['https://www.due.urssaf.fr/*'],
  iag: ['https://*.gestioniag.fr/*'],
  sfr: ['https://*.sfr.fr/*'],
  eni: ['https://*.eni-energie.com/*'],
  plenitude: ['https://*.plenitude.com/*'],
  ohm: ['https://*.ohm-energie.com/*'],
}

const PARTENAIRE_URL_REGEX = {
  urssaf: /^https:\/\/www\.due\.urssaf\.fr\//,
  iag: /^https:\/\/[^/]*gestioniag\.fr\//,
  sfr: /^https:\/\/[^/]*sfr\.fr\//,
  eni: /^https:\/\/[^/]*eni-energie\.com\//,
  plenitude: /^https:\/\/[^/]*plenitude\.com\//,
  ohm: /^https:\/\/[^/]*ohm-energie\.com\//,
}

function sendToFrame(tabId, frameId, partenaire, data) {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(
      tabId,
      { type: 'FILL', partenaire, data },
      { frameId },
      (resp) => {
        if (chrome.runtime.lastError) {
          resolve({ ok: false, error: chrome.runtime.lastError.message })
        } else {
          resolve(resp || { ok: false })
        }
      },
    )
  })
}

async function tryFillIframes(senderTabId, partenaire, data) {
  const regex = PARTENAIRE_URL_REGEX[partenaire]
  if (!regex || !senderTabId) return 0
  const frames = await new Promise((resolve) =>
    chrome.webNavigation.getAllFrames({ tabId: senderTabId }, (f) =>
      resolve(f || []),
    ),
  )
  const matching = frames.filter((f) => f.url && regex.test(f.url))
  let ok = 0
  for (const f of matching) {
    const r = await sendToFrame(senderTabId, f.frameId, partenaire, data)
    if (r?.ok) ok++
  }
  return ok
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type !== 'FILL_PARTENAIRE') return

  const partenaire = String(msg.partenaire || '').toLowerCase()
  const patterns = PARTENAIRE_URL_PATTERNS[partenaire]
  if (!patterns) {
    sendResponse({ ok: false, error: `Partenaire inconnu : ${partenaire}` })
    return true
  }

  ;(async () => {
    // 1. Cherche dans les onglets independants
    const tabs = await new Promise((resolve) =>
      chrome.tabs.query({ url: patterns }, (t) => resolve(t || [])),
    )
    let okCount = 0
    for (const tab of tabs) {
      const r = await sendToFrame(tab.id, 0, partenaire, msg.data || {})
      if (r?.ok) okCount++
    }

    // 2. Fallback : cherche dans les iframes de l'onglet emetteur
    if (okCount === 0 && sender?.tab?.id) {
      okCount = await tryFillIframes(sender.tab.id, partenaire, msg.data || {})
    }

    if (okCount > 0) {
      sendResponse({ ok: true, tabs: okCount })
    } else {
      sendResponse({
        ok: false,
        error:
          'Portail non trouvé (ni onglet, ni iframe). Ouvre le portail puis réessaie.',
        tabs: 0,
      })
    }
  })()
  return true // reponse async
})
