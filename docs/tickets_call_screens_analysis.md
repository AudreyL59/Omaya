# Analyse Ticket Energie + Ticket Fibre (portage Flutter -> React/Python)

Ce document sert de spec pour la migration des 2 ecrans Flutter vers
l'intranet Vendeur (React + FastAPI/PostgreSQL).

**Sources** :
- `d:/Claude/omayapp_flutter/lib/features/call/call_screen.dart`
  (1434 l., ecran Ticket Energie)
- `d:/Claude/omayapp_flutter/lib/features/call_sfr/call_sfr_screen.dart`
  (1078 l., ecran Ticket Fibre SFR)

Les deux ecrans sont des `ConsumerStatefulWidget` Riverpod mono-fichier,
pilotes par un entier `_plan` qui joue le role de pager (pas de vraie
stack Navigator).

---

## 1. Vue d'ensemble par ecran

### 1.1 CallScreen — Ticket Energie (Fen_Call)

**Role metier.** L'operateur cree/reprend un panier de vente de contrats
d'energie (elec/gaz) et de produits connexes, aupres de partenaires
(OEN, ENI, STR, VAL, PRO, OHM). Fiche client -> ajout de N produits par
partenaire -> validation par code SMS envoye au client.

**Plans (11)** :

| Plan | Titre AppBar | Role |
|---|---|---|
| 1 | Mes Paniers en cours | Liste des tickets non finalises du commercial |
| 2 | Mon Client | Formulaire client (Part/Pro) |
| 3 | Panier | Liste des produits ajoutes + bouton "Ajouter" + validation code |
| 4 | Panier | Grille des logos partenaires |
| 5 | Mon Offre | Formulaire offre (depend du partenaire) |
| 6 | Mon Offre | OHM - infos logement |
| 7 | Mon Offre | OHM - types d'installation |
| 8 | Mon Offre | OHM - financiers + observations |
| 9 | Mon Offre | Justificatif (photo facture) - vestige, non appele |
| 11 | Mon Client | Scan CIN + KBIS (Pro uniquement) |

**Etat interne principal** : `_plan`, `_loading`, `_loadingMessage`,
`_tickets`, `_idTicketEnCours`, `_civilite`, `_nomCtrl`, `_nomMaritalCtrl`,
`_prenomCtrl`, `_dnaissCtrl`, `_depNaissCtrl`, `_typeLogement`,
`_adresse1Ctrl`, `_adresse2Ctrl`, `_cpCtrl`, `_villes`, `_villeId`,
`_villeNom`, `_mobile1Ctrl`, `_mailCtrl`, `_clientPro`, `_rsCtrl`,
`_siretCtrl`, `_panier`, `_codeGenere`, `_codeCtrl`, `_showCodeInput`,
`_codeTest`, `_partenaires`, `_libPart`, `_typePart` (OEN/ENI/STR/VAL/
PRO/OHM), `_produits`, `_selectedProdId`, `_selectedProdDualId`,
`_oenTypeOffre` (1=Mono, 2=Dual), `_numBSCtrl`, `_numBSDualCtrl`,
`_refClientCtrl`, `_dateActivCtrl`, `_infosContratCtrl`, `_optProtected`,
`_optAcceptComPart`, `_optConsentDistri`, `_optMaintenance`, `_optMandat`,
`_optNumerique`, `_nbPersFoyerCtrl`, `_sitProCtrl`, `_rfrCtrl`,
`_dateEntreeCtrl`, `_superficieCtrl`, `_anneeConstruCtrl`,
`_anneeInstallCtrl`, `_typesInstall` (avec cles `_chauffage`/`_eauChaude`
mutees), `_autreInstall`, `_autreInstallCtrl`, `_montantGazCtrl`,
`_montantElecCtrl`, `_chauffAppoint`, `_isoCombles`, `_chauffAlter`
(1=Oui, 2=Non), `_chauffAlterCtrl`, `_observationsCtrl`, `_justifImage`,
`_photoOk`, `_cinOk`, `_kbisOk`.

### 1.2 CallSfrScreen — Ticket Fibre SFR (Fen_CallSFR)

**Role metier.** Vente forfaits SFR (Fibre, Mobile, en Pro : FIB PRO,
MOB PRO) avec gestion portabilite, code RIO, type de prise, migration/
conquete, resiliation, anomalies pour vente mobile differee.

**Plans (7)** :

| Plan | Titre AppBar | Role |
|---|---|---|
| 1 | Mes Paniers en cours | Liste tickets non finalises |
| 2 | Mon client | Formulaire client + bouton test eligibilite Fibre |
| 3 | Mon client | Scan CIN + KBIS (si Pro) |
| 4 | Panier Client | Liste produits + ajout Fibre/Mobile + vente directe/differee + validation code |
| 5 | Panier Client | Liste offres SFR filtrees (TV/PS5/HT) |
| 6 | Portabilite | Portabilite (N° + RIO), type prise, lettre de resil |
| 7 | Mon client | WebView test eligibilite Fibre (sfr.fr) |

**Etat interne principal** : identique Energie + `_mobile2Ctrl`,
`_venteMobile` (1=direct, 2=differee), `_showVenteMobile`, `_anomalies`,
`_selectedAnomalie`, `_infoCpltAnomalieCtrl`, `_showAnomalie`, `_offresSFR`,
`_typeOffre` (`FIBRE|MOBILE|FIB PRO|MOB PRO`), `_avecTV`, `_optChoisies`,
`_idProdChoisi`, `_typeProdChoisi`, `_portabilite`, `_numPortCtrl`,
`_codeRioCtrl`, `_nouvellePrise`, `_numPriseCtrl`, `_ficResil`,
`_resilOnServer` (null/true/false), `_resilChecking`.

---

## 2. Composants UI cles a recreer cote React

| Composant Flutter | Role | Reutilisation |
|---|---|---|
| `_segRow` + `_segBtn` | Boutons segmentes ronds (bord noir 1.5px, radius 25) | Civilite, Logement, Part/Pro, Mono/Dual, Vente mobile |
| Champ CP + Dropdown ville | Input CP -> `_searchVilles` a >=4 chars -> dropdown villes | Commun (Plan 2) |
| DatePicker FR wrappe | `showDatePicker` locale FR, sortie `dd/MM/yyyy`, API `yyyyMMdd` | Naissance, Date activation, Date entree logement |
| Liste tickets (Dismissible + Card) | Double-tap ouvre, swipe supprime | Plan 1 identique 2 ecrans |
| Dialog confirm Oui/Non | AlertDialog "Voulez vous..." | Suppr ticket, suppr produit, valider panier, ajouter offre |
| `_checkOpt(label, value, onChanged)` | CheckboxListTile dense + label 13px | Options ENI/STR/VAL/OHM |
| `_labelField(label, ctrl, type, suffix)` | Row + TextField suffixText (Energie) | Formulaires OHM |
| `_field(ctrl, label, type, caps)` | TextField labelle compact (SFR) | Formulaire client SFR |
| Card d'offre SFR | Titre gras + prix XL + engagement + badge promo + debits + services | Plan 5 SFR |
| Grille partenaires (GridView 2 col) | Card + logo base64 (SafeImageMemory - decodage `\r\n`) | Plan 4 Energie |
| Segment NavBar bas | Row "Retour <-" / "Etape suivante ->" | Plans 6-7 OHM |
| Loading overlay | Spinner + message optionnel (~jusqu'a 1 min pour create client) | Communs, critique UX |
| Photo editor multi-pages | `showPhotoEditorMulti(context, titre:)` custom | Scan CIN/KBIS/Clarification |
| PDF builder SPECIMEN | PDF A4 + filigrane rouge 50% -0.785 rad, tuile 150x250, fontSize 36 | CIN, KBIS, Justif, Clarification (Energie & SFR) |
| Bouton resiliation avec statut serveur | Bouton scan + icone check(vert)/cancel(rouge) | Plan 6 SFR |
| WebView | WebViewWidget SFR eligibilite | Plan 7 SFR |
| SafeImageMemory | Rendu image tolerant (base64/Uint8List) | Logos partenaires, preview justif |

---

## 3. Flow metier

### 3.1 Flow Energie

1. **Init** (`_loadInit`) : POST `/Call/ClientsNonFinalises/{usersCial}`
   (tickets) puis POST `/PartCall` (partenaires). Aucun ticket -> Plan 2,
   sinon Plan 1.
2. **Plan 1** : selection ticket existant (double-tap `_openTicket`) OU
   "Nouveau client" -> reset form + Plan 2.
   - `_openTicket` : si Pro et (`KbisOK` && `PhotoOK`) -> charge panier
     + Plan 3, sinon Plan 11 (docs).
3. **Plan 2 -> `_validerClient`** : validations locales, POST `/Call/
   NouveauTK/{usersCial}` avec `receiveTimeout: kCreateReceiveTimeout`
   (~1 min). Succes -> ajout `_tickets` local. Pro -> Plan 11, Part -> Plan 4.
4. **Plan 11 (docs Pro)** : `_scanAndUploadDoc('PieceIdentite'|'KBIS')`
   -> PDF filigrane -> upload `/RecepFichier`. Puis "Valider" : GET
   `/Call/ClientsNonFinalises/VerifPhoto/{id}/PieceIdentite` (+ KBIS si
   Pro) -> Plan 4.
5. **Plan 4 (partenaires)** : tap logo -> POST `/Call/ProduitActifs/
   {part}` -> `_initOffreFields()`. Si OHM -> GET `/Call/OHM/
   ListeTypeInstall` + Plan 6, sinon Plan 5.
6. **Plan 5 (offre)** : formulaire selon `_typePart` (voir tableau plus
   bas). Ajout -> POST `/Call/ClientsNonFinalises/Panier/Produit/Ajout`
   avec payload `_baseProd()`. OEN Dual -> 2e POST + `_scanClarification`
   (upload sous 2 noms). Retour Plan 3.
7. **Plans 6-8 (OHM)** : navigation sequentielle `_navBar`. Ajout final
   `_ajouterProduitOHM` -> meme endpoint avec sous-liste `TypesInstall`.
   Retour Plan 3.
8. **Plan 3 (panier)** : "Valider panier" -> genere code local 6 chiffres
   (`100000 + ms%900000`) -> POST `/Call/ClientsNonFinalises/EnvoiLien/
   {code}` -> affichage champ code. Saisie == `_codeTest` local -> dialog
   confirm -> POST `/Call/ClientsNonFinalises/Validation/{usersCial}` ->
   Navigator.pop.
9. **Plan 9 (Justif)** : vestige, non atteint par le flow actuel.

### 3.2 Flow Fibre SFR

1. **Init** : POST `/CallSFR/ClientsNonFinalises/{usersCial}` + GET
   `/CallSFR/AnomalieListe`. Aucun ticket -> Plan 2, sinon Plan 1.
2. **Plan 1** : idem Energie. `_openTicket` : `isPro ? kbisOk : photoOk`
   -> OK -> panier + Plan 4, sinon Plan 3.
3. **Plan 2 -> `_validerClient`** : validations, POST `/CallSFR/
   NouveauTK/{usersCial}`. Succes -> **toujours Plan 3** (docs
   systematiques contrairement a Energie).
4. **Plan 3 (docs)** : `_scanAndUploadDoc` avec PDF filigrane multi-pages
   + upload. `_validerDocs` : GET `/CallSFR/ClientsNonFinalises/
   VerifPhoto/{id}/PieceIdentite` (+ KBIS si Pro) -> panier + Plan 4.
5. **Plan 4 (panier)** :
   - Ajouter FIBRE / MOBILE -> GET `/SFR/ListerOffres/{type}/{0|1}` +
     Plan 5.
   - Si panier MOBILE + droit `BS_SFRDiff` -> segment direct/differee.
     Differee -> POST `AnomalieMobile/.../0` (init), changement motif ->
     POST `.../1`. Motif magic `100` -> champ libre `InfoCplAnomalie`.
   - Valider panier : identique Energie (code + `EnvoiLien` + confirm +
     `Validation`).
6. **Plan 5 (offres)** : tri client par TV. Tap -> confirm ; FIB -> dialog
   Conquete/Migration. Migration -> `_ajouterProduitDirect` (POST direct,
   `TypeVente=3`, ignore portabilite). Sinon Plan 6.
7. **Plan 6 (portabilite)** :
   - Portabilite -> N° + RIO (>=12 chars).
   - Sinon + FIB : `_scanResiliation` (photo -> PDF **sans filigrane** ->
     upload `{id}_LettreResil.pdf`). Statut via GET `{lienSiteRest}/
     DocOmaya/{id}_LettreResil.pdf` avec `Range: bytes=0-0` (200/206 =
     existe). Bloquant pour validation aval.
   - FIB : Nouvelle prise / Prise parc (numero nettoye).
   - Valider -> POST `/CallSFR/ClientsNonFinalises/Panier/Produit/Ajout`
     avec `TypeVente=1` par defaut. Retour Plan 4.
8. **Plan 7** : WebView SFR (aucune API).

---

## 4. WEBSERVICES - EXHAUSTIF

Base URL : prefixee par `dioClientProvider` (Riverpod). `appState.
usersCial` = ID commercial connecte. Payloads `jsonEncode(...)`.

### 4.1 Ecran Energie (CallScreen)

| URL | Meth | Payload | Retour | Declencheur | Ecran |
|---|---|---|---|---|---|
| `/WebRest_Omayapp/Call/ClientsNonFinalises/{usersCial}` | POST | (aucun) | `List<Map>` : `IDTK_Liste, NomClient, PrenomClient, ClientPro, ClientRS, CP, VILLE, DateCreation, PhotoOK, KbisOK, Code` | `_loadInit` au montage | Energie |
| `/WebRest_Omayapp/PartCall` | POST | (aucun) | `List<Map>` : `Nom, Bdd (OEN/ENI/STR/VAL/PRO/OHM), Logo (base64)` | `_loadInit` | Energie |
| `/WebRest_Omayapp/Call/ClientsNonFinalises/Panier/{idTicket}` | POST | (aucun) | `List<Map>` : `IDtk_Call_Panier, LibOffre, Part, NumBS` | `_loadPanier` (ouverture, ajout/suppr) | Energie |
| `/WebRest_Omayapp/Call/ClientsNonFinalises/Suppr/{usersCial}` | POST | `{IDTK_Liste}` | - | Swipe suppr ticket (Plan 1) | Energie |
| `/WebRest_Omayapp/Call/NouveauTK/{usersCial}` | POST | Client complet (voir §5) | `{nIdDemande, sInfoData?}` | Bouton Valider client (Plan 2) | Energie |
| `/WebRest_Omayapp/Call/ProduitActifs/{part}` | POST | (aucun) | `List<Map>` : `IDProduit, LibProd` | Tap logo partenaire (Plan 4) + boucle VAL | Energie |
| `/WebRest_Omayapp/Call/OHM/ListeTypeInstall` | GET | - | `List<Map>` : `TypeInstall, LibTypeInstall, Chauffage, EauChaude` | Selection OHM (Plan 4->6) | Energie |
| `/WebRest_Omayapp/Call/ClientsNonFinalises/Panier/Produit/Ajout` | POST | `_baseProd()` (~30 champs, voir §5) | `{nIdDemande, sInfoData?}` | Bouton Ajouter produit (Plans 5, 8) + boucle VAL + 2e POST OEN Dual | Energie |
| `/WebRest_Omayapp/Call/ClientsNonFinalises/Panier/Produit/Suppr` | POST | `{IDtk_Call_Panier}` | - | Tap produit -> confirm (Plan 3) | Energie |
| `/WebRest_Omayapp/Call/ClientsNonFinalises/EnvoiLien/{code6ch}` | POST | `{IDTK_Liste}` | - | Valider panier (Plan 3) | Energie |
| `/WebRest_Omayapp/Call/ClientsNonFinalises/Validation/{usersCial}` | POST | `{IDTK_Liste}` | - | Saisie code + confirm (Plan 3) | Energie |
| `/WebRest_Omayapp/Call/ClientsNonFinalises/VerifPhoto/{idTicket}/{type}` (`type` = `PieceIdentite \| KBIS \| Justif`) | GET | - | `{nIdDemande, ...}` (!=0 = trouve) | `_validerDocs` (Plan 11), `_validerJustif` (Plan 9) | Energie |

### 4.2 Ecran Fibre SFR (CallSfrScreen)

| URL | Meth | Payload | Retour | Declencheur | Ecran |
|---|---|---|---|---|---|
| `/WebRest_Omayapp/CallSFR/ClientsNonFinalises/{usersCial}` | POST | (aucun) | `List<Map>` tickets (idem Energie) | `_loadInit` | Fibre |
| `/WebRest_Omayapp/CallSFR/AnomalieListe` | GET | - | `List<Map>` : `IDtk_CallSFR_Anomalie, LibTypeAnomalie` | `_loadInit` | Fibre |
| `/WebRest_Omayapp/CallSFR/ClientsNonFinalises/Panier/{idTicket}` | POST | (aucun) | `List<Map>` : `IDtk_CallSFR_Panier, LibOffre, Type (FIBRE/MOBILE/...), NumPortabilite` | `_loadPanier` | Fibre |
| `/WebRest_Omayapp/CallSFR/ClientsNonFinalises/Suppr/{usersCial}` | POST | `{IDTK_Liste}` | - | Swipe suppr ticket (Plan 1) | Fibre |
| `/WebRest_Omayapp/CallSFR/NouveauTK/{usersCial}` | POST | Client (+ `Mobile2`) | `{nIdDemande, sInfoData?}` | Valider client (Plan 2) | Fibre |
| `/WebRest_Omayapp/SFR/ListerOffres/{type}/{avecTV}` (`type` = `FIBRE\|MOBILE\|FIB PRO\|MOB PRO`, `avecTV` = `0\|1`) | GET | - | `List<Map>` : `IDOffres_SFR, Lib_Offre, PrixOffre, Engagement, EnPromo, InfoPromo, DebitDown, DebitUp, ServiceInclus, Type` | Boutons Ajouter FIBRE/MOBILE (Plan 4) + toggle TV (Plan 5) | Fibre |
| `/WebRest_Omayapp/CallSFR/ClientsNonFinalises/Panier/Produit/Ajout` | POST | `{IDSalarie, IDtk_CallSFR, IDTK_Liste, IDOffres_SFR, Opt_TV, Type, Portabilite, NumPriseOptique, NumPortabilite, NumPrise_RIO, TypeVente (1=Conquete, 3=Migration), OptionsChoisies}` | `{nIdDemande, sInfoData?}` | `_validerProduit` (Plan 6), `_ajouterProduitDirect` (Migration Plan 5) | Fibre |
| `/WebRest_Omayapp/CallSFR/ClientsNonFinalises/Panier/Produit/Suppr` | POST | `{IDtk_CallSFR_Panier}` | - | Swipe suppr produit (Plan 4) | Fibre |
| `/WebRest_Omayapp/CallSFR/ClientsNonFinalises/AnomalieMobile/{usersCial}/{idInd}` (`idInd` = 0 init, 1 update) | POST | `{IDTK_Liste, IDtk_CallSFR_Anomalie, InfoCplAnomalie}` | - | Bascule differee + changement motif (Plan 4) | Fibre |
| `/WebRest_Omayapp/CallSFR/ClientsNonFinalises/EnvoiLien/{code6ch}` | POST | `{IDTK_Liste}` | - | Valider panier (Plan 4) | Fibre |
| `/WebRest_Omayapp/CallSFR/ClientsNonFinalises/Validation/{usersCial}` | POST | `{IDTK_Liste}` | `{nIdDemande, sInfoData?}` | Saisie code (Plan 4) | Fibre |
| `/WebRest_Omayapp/CallSFR/ClientsNonFinalises/VerifPhoto/{idTicket}/{type}` (`type` = `PieceIdentite\|KBIS`) | GET | - | `{nIdDemande, ...}` (!=0 = trouve) | `_validerDocs` (Plan 3) | Fibre |
| `{appState.lienSiteRest}/DocOmaya/{idTicket}_LettreResil.pdf` | GET `Range: bytes=0-0` | - | 200/206 = existe | `_checkResilOnServer` (Plan 6) | Fibre |

### 4.3 Webservices communs

| URL | Meth | Payload | Retour | Declencheur | Ecran |
|---|---|---|---|---|---|
| `/WebRest_Omayapp/ListeVilleByCP/{cp}` | GET | - | `List<Map>` : `ID, NomVille, CP` | `onChanged` CP >=4 chars (Plan 2) | Commun |
| `{appState.lienSiteRest}/WebRest_Omayapp/RecepFichier` | POST multipart | `http.Request` direct (PAS dio) — `Content-Type: multipart/form-data; boundary=----WinDevBoundary{ms}` — champ `file; filename="<name>"; Content-Type: application/pdf\|image/png` | `{ResEnvoi: bool\|1}` | Upload : `{id}_PieceIdentite.pdf`, `{id}_KBIS.pdf`, `{id}_Clarification.pdf`, `{id}_LettreResil.pdf`, `{id}_Justif.png` | Commun |

**Note** : `RecepFichier` utilise `package:http` directement avec le
boundary WinDev exact `----WinDevBoundary<ms>`. Backend WinDev cote
serveur.

**TOTAL : 21 webservices distincts** (10 Energie + 9 Fibre + 2 communs).

---

## 5. Points d'attention pour le portage

### 5.1 Dependances externes

- **`package:image_picker`** : camera pour Justif (Energie 9) et Lettre
  resil (SFR 6). `pickImage(source: camera)`.
- **`showPhotoEditorMulti(context, titre:)`** : composant custom qui
  prend N photos et retourne une liste d'objets `{bytes}`. Utilise CIN,
  KBIS, Clarification. **Il faudra un equivalent React** (camera multi
  cliches + edition).
- **`package:pdf`** : generation PDF A4 client + filigrane SPECIMEN
  (rouge 50%, -0.785 rad, tuile 150x250, fontSize 36). SFR Plan 3 CIN/
  KBIS et Energie Plan 11 CIN/KBIS + Clarification. Lettre resil SFR :
  **PDF sans filigrane**.
- **`package:http`** (en plus de dio) : uniquement upload multipart
  `/RecepFichier` (boundary manuel WinDev). Timeout 90 s cote SFR.
- **`package:webview_flutter`** : Plan 7 SFR uniquement.
- **`SafeImageMemory`** : composant custom rendu image tolerant. Decode
  base64 apres suppression `\r\n`.
- **`AppState` (Riverpod)** : `usersCial` (int), `lienSiteRest` (URL
  base), `verifDroit(code)` (droits, ex. `BS_SFRDiff`).
- **`toastAffiche(msg)`** et **`formatDateHeure(str)`** de `app_utils.
  dart` (a porter).
- **`kCreateReceiveTimeout` / `handleCreationTimeout(e)`** de
  `dio_creation_timeout.dart` — timeout etendu creation client (~1 min).

### 5.2 Formats de dates, IDs, encodages

- **Dates UI** : `dd/MM/yyyy` (locale FR).
- **Dates API** : `_formatDateApi(d)` -> `yyyyMMdd`. Applique a
  `DATENAISS`, `DateEntree` OHM, `DateEntree` OEN.
- **NumBS pre-remplis OEN** : `CT-yyMMdd`, `RefClient = CM-yyMMdd`
  (jour).
- **Code validation client** : entier 6 chiffres calcule client
  `100000 + (ms%900000)`. Envoye au serveur via `EnvoiLien/{code}` (SMS
  au client). Ressaisie -> comparaison **locale** avec `_codeTest` (pas
  de re-verif serveur).
- **IDs** : `int`. `_toInt(v)` gere types mixtes. Serveur retourne
  `nIdDemande` (0 = echec, message dans `sInfoData`).
- **Booleens serveur** : parfois `true/false`, parfois `1/0` (ex.
  `ResEnvoi`, `PhotoOK`, `KbisOK`, `ClientPro`, `EnPromo`). Comparer
  `== true`.
- **Booleens URL SFR** : `avecTV` -> `'0'/'1'` string dans l'URL.
- **Type de vente SFR** : `1 = Conquete`, `2 = choix Migration dans
  dialog` (declenche `_ajouterProduitDirect(typeVente:3)` -> **payload
  envoie `3`**). Attention : valeur dialog != valeur API.
- **NumPrise SFR** : nettoyage `replaceAll(' ', '').replaceAll('_',
  '-')`. Si nouvelle prise -> chaine `'Nouvelle prise'`.
- **NumPortabilite SFR** : points supprimes avant envoi
  (`replaceAll('.', '')`).
- **Payload `_baseProd()` Energie** : ~35 cles. Fautes typo
  **`Supercie`** (Superficie), **`ChauffageAlternantif`** (Alternatif) :
  a conserver a l'identique pour compat serveur.

### 5.3 Logique metier subtile

**Energie :**

- **OEN Dual** : 2 dropdowns (Gaz + Elec) + 2 NumBS. Ajout = 2 POST
  successifs. Clarification uploadee 1 fois sous 2 noms
  `{nId1}_Clarification.pdf` et `{nId2}_Clarification.pdf`.
- **VAL** : "Ajouter" **charge tous** les produits VAL (POST
  `/ProduitActifs/VAL` refait) et les POST en boucle. `FormatNumerique`
  = 1/0 selon checkbox.
- **OEN** : `refClientCtrl` -> champ **`Observations`** (pas champ
  dedie). `optProtected` (jamais coche UI) -> `OPT_eFacture`.
- **ENI** : les 3 checkboxes UI (`_optAcceptComPart`, `_optConsentDistri`,
  `_optMaintenance`) mappent `OPT_CialPart`, `OPT_ConsentDistri`,
  `Opt_Maintenance` (attention casse `Opt_` vs `OPT_`). Autres options
  `OPT_Reforestation`, `OPT_EnergieVerteGaz`, `OPT_Mail`,
  `OPT_eCommunication`, `OPT_eFacture`, `OPT_optinCommercial` **forcees
  false** ("Coches supprimees").
- **OHM** : `TypesInstall` = sous-liste `{TypeInstall, Chauffage,
  EauChaude}` construite depuis `_typesInstall` (cles `_chauffage`/
  `_eauChaude` mutees).
- **Chauffage alternatif** : `1=Oui`, `2=Non` UI mais envoye booleen
  `ChauffageAlternantif = (_chauffAlter == 1)`.
- **Plan 9** : jamais atteint. Vestige a confirmer metier.
- **Bouton Retour AppBar** specifique : 3->1, 4->3, 5->4, 6/7/8->plan-1,
  9->5, 11->1.

**SFR :**

- **`_openTicket`** : `isPro ? kbisOk : photoOk` (PhotoOK non teste pour
  Pro). **Diverge d'Energie** (`!isPro OR (kbisOk && photoOk)`).
- **`BS_SFRDiff`** : droit qui masque le segment direct/differee. A
  porter cote droits Vendeur.
- **Anomalie mobile** : POST `AnomalieMobile/.../0` a la bascule
  differee (init), POST `.../1` a chaque changement motif. Motif `100`
  magique -> champ libre `InfoCplAnomalie`.
- **Filtrage TV client** : `_offresSFR` refiltree en Dart (`Lib_Offre`
  contient TV/HIGH TECH/PS5) en plus du filtre serveur (redondance
  WinDev).
- **Migration Fibre** : shortcut skip Plan 6, envoie `Portabilite=false`,
  `NumPortabilite=''`, `NumPrise_RIO=''`, `NumPriseOptique=''`,
  `TypeVente=3`.
- **Validation portabilite** : `_codeRioCtrl.text.length < 12` bloque.
- **Lettre resil Fibre** : **bloquante** pour validation si non-
  portabilite + FIB (`_ficResil.isEmpty`). Verif serveur async via `GET
  Range:bytes=0-0`. Echec upload -> `_ficResil` reset ''.
- **Upload SFR** : timeouts explicites 90 s (send + stream). Energie sans.

### 5.4 Differences majeures Energie <-> Fibre

| Aspect | Energie | Fibre SFR |
|---|---|---|
| Plans | 11 (1-9, 11) | 7 |
| Apres validation client (Plan 2) | Pro -> 11 (docs) ; Part -> 4 (partenaires) | Toujours -> 3 (docs) — CIN obligatoire |
| Test docs ouverture ticket | `!isPro OR (kbisOk && photoOk)` | `isPro ? kbisOk : photoOk` |
| Choix produit | Grille logos partenaires -> dropdown produits | Boutons FIBRE/MOBILE -> cartes offres |
| Champs client sup | - | `Mobile2` |
| Docs obligatoires | Part: aucun ; Pro: CIN+KBIS+Clarif par OEN | CIN pour tous (+KBIS Pro) + Lettre resil non-portab Fibre |
| PDF filigrane SPECIMEN | CIN, KBIS, Clarification | CIN, KBIS ; **lettre resil sans filigrane** |
| Upload | Timeout non specifie | Timeout 90 s |
| Payload produit | ~30 cles (`OPT_*`, `Opt_*`, OHM) | Restreint (`Opt_TV`, `Portabilite`, `NumPortabilite`, `NumPriseOptique`, `NumPrise_RIO`, `TypeVente`, `OptionsChoisies`) |
| Droit bloquant | Aucun | `BS_SFRDiff` |
| Anomalies vente differee | N/A | Liste + endpoint dedie |
| WebView interne | Aucune | Plan 7 test eligibilite |
| Code SMS | `EnvoiLien/{code}` (Call) | `EnvoiLien/{code}` (CallSFR) — meme algo, endpoint distinct |
| Validation panier | `Call/.../Validation/{cial}` (retour non parse) | `CallSFR/.../Validation/{cial}` (retour parse) |
| Naming cles panier | `IDtk_Call_Panier`, `IDtk_Call` | `IDtk_CallSFR_Panier`, `IDtk_CallSFR` |
| Segment Part/Pro Plan 4 | N/A | Affiche si `_clientPro` (mais no-op — visuel) |

### 5.5 Divers a surveiller

- `TextEditingController` non nettoyes hors `dispose()`. Reset "nouveau
  client" (`_resetClientForm`) manuel. **A repliquer cote React**
  explicitement.
- Booleens serveur avec `== true` : semantique laxiste (accepter
  `true/1`).
- Suppression locale ticket : `_tickets.remove(t)` + setState.
  Optimistic UI, aucune re-fetch. **A reproduire**.
- `_partenaires[i]['Logo']` : base64 avec possibles `\r\n` — nettoyer
  avant `atob` React.
- `toastAffiche` = unique retour utilisateur pour beaucoup d'erreurs.
  **Systeme de notif/toast global** cote React.
- `Riverpod` + `ref.read` : `usersCial` et `lienSiteRest` sont
  dynamiques, a lire a chaque appel (pas capture une seule fois).
