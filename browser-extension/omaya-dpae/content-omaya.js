// content-omaya.js
// Injecte sur les pages Omaya. Bridge entre la page (window.postMessage)
// et le service worker (chrome.runtime.sendMessage).
//
// Messages reconnus depuis la page :
//   { source: 'omaya-dpae', type: 'PING' }    -> reply PONG via postMessage
//   { source: 'omaya-dpae', type: 'FILL',
//     partenaire: 'urssaf'|'iag'|...,
//     data: { siret, login, mdp, nom, prenom, ... } }
//      -> relay au background qui ciblera l'onglet partenaire actif.

(function () {
  const TAG = 'omaya-dpae'

  window.addEventListener('message', (ev) => {
    if (ev.source !== window) return
    const msg = ev.data
    if (!msg || msg.source !== TAG) return

    if (msg.type === 'PING') {
      window.postMessage(
        { source: TAG, type: 'PONG', version: chrome.runtime.getManifest().version },
        '*',
      )
      return
    }

    if (msg.type === 'FILL') {
      chrome.runtime.sendMessage(
        { type: 'FILL_PARTENAIRE', partenaire: msg.partenaire, data: msg.data },
        (resp) => {
          window.postMessage(
            { source: TAG, type: 'FILL_RESULT', ok: !!resp?.ok, error: resp?.error || null, tabs: resp?.tabs || 0 },
            '*',
          )
        },
      )
      return
    }
  })

  // Annonce silencieuse de la presence de l'extension
  window.postMessage({ source: TAG, type: 'READY', version: chrome.runtime.getManifest().version }, '*')
})()
