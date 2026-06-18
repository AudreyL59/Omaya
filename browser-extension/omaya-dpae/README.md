# Omaya DPAE Filler

Extension Chrome/Edge qui remplit automatiquement les portails partenaires
(URSSAF DUE, IAG, SFR, ENI, etc.) depuis le module **Nouvelle DPAE** de
l'intranet ADM Omaya.

## Pourquoi une extension ?

Une SPA web (l'intranet Omaya) ne peut pas piloter le DOM d'un iframe
cross-origin pour des raisons de sécurité du navigateur (Same-Origin
Policy). L'extension contourne ça en injectant un script directement
sur les domaines partenaires.

## Installation (Chrome / Edge)

1. Ouvrir `chrome://extensions/` (ou `edge://extensions/`).
2. Activer le mode **développeur** (toggle en haut à droite).
3. Cliquer sur **"Charger l'extension non empaquetée"**.
4. Choisir le dossier `browser-extension/omaya-dpae/`.
5. L'icône Omaya DPAE apparaît dans la barre.

## Utilisation

1. Ouvre Omaya → Salariés → Nouvelle DPAE → enregistre le salarié.
2. Phase 2 (codes partenaires) : choisis le partenaire dans la combo.
3. Clique sur **"Ouvrir le portail"** (nouvel onglet).
4. Reviens sur l'onglet Omaya, clique sur **"Remplir le formulaire"**.
5. L'extension détecte l'onglet partenaire ouvert et remplit les champs.

## Architecture

```
browser-extension/omaya-dpae/
├── manifest.json         (MV3, déclare permissions + content scripts)
├── background.js         (service worker - route les messages)
├── content-omaya.js      (injecté sur Omaya - bridge postMessage ↔ runtime)
├── content-portail.js    (injecté sur les portails - remplit les champs)
└── icons/
```

Flow :
```
[Omaya page]  --postMessage-->  [content-omaya]  --runtime.sendMessage-->  [background]
                                                                                |
                                                       chrome.tabs.query(partenaire)
                                                                                |
                                                                tabs.sendMessage(fill)
                                                                                ↓
                                                                      [content-portail]
                                                                                ↓
                                                                  document.querySelector
                                                                  setValue + dispatch event
```

## Ajouter un nouveau portail

1. Dans `manifest.json` : ajouter le pattern d'URL dans `host_permissions`
   ET dans le 2e bloc `content_scripts.matches`.
2. Dans `background.js` : ajouter une entrée à `PARTENAIRE_URL_PATTERNS`.
3. Dans `content-portail.js` : ajouter une fonction à `FILLERS` avec
   les sélecteurs CSS des champs (inspecter le DOM du portail pour les
   trouver).

## Données envoyées par Omaya

```js
{
  source: 'omaya-dpae',
  type: 'FILL',
  partenaire: 'urssaf',
  data: {
    siret: '81086107000029',
    login: '...',
    mdp: '...',
    nom: 'DUPONT',
    prenom: 'Jean',
    // etc.
  }
}
```
