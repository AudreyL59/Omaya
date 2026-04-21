# Déploiement ERP Omaya — Windows Server 2019

Cible : `https://sos.groupe-exo.omaya.fr/`

## Architecture

```
Navigateur  →  IIS (:443, cert Let's Encrypt)
                ├─ /api/*      →  uvicorn (127.0.0.1:8000)  →  bridge WinDev  →  HFSQL
                │                 (règle dans D:\Sites\groupeOmaya\www\web.config)
                ├─ /vendeur/*  →  D:\Sites\groupeOmaya\www\vendeur\  (dist Vite + SPA fallback)
                └─ /*          →  autres fichiers déjà présents dans www, non touchés
```

Le frontend est servi sous le chemin `/vendeur/` pour cohabiter avec d'autres contenus déjà présents à la racine du site IIS.

## Vérification auto des pré-requis

Avant tout, lance ce script — il vérifie l'ensemble des points ci-dessous et liste ce qui manque :

```powershell
cd "D:\Claude\Projet Omaya"
.\deploy\check-prerequisites.ps1
```

## Pré-requis (à vérifier sur le serveur)

- [x] Python 3.x avec un venv dans `D:\Claude\Projet Omaya\venv\` (dépendances : `pip install -r requirements.txt`)
- [x] Node.js + npm
- [x] Bridge WinDev (`D:\Claude\Projet Omaya\bridge\Dll_ODBC.exe`) accessible
- [x] IIS installé avec les modules :
  - **URL Rewrite** — https://www.iis.net/downloads/microsoft/url-rewrite
  - **Application Request Routing (ARR)** — https://www.iis.net/downloads/microsoft/application-request-routing
- [x] **NSSM** dans le PATH — https://nssm.cc/download
- [x] Certificat Let's Encrypt pour `sos.groupe-exo.omaya.fr` importé dans IIS
- [x] DNS `sos.groupe-exo.omaya.fr` → IP du serveur

## Étape 1 — Activer ARR en proxy

Indispensable pour le reverse proxy `/api` → uvicorn.

1. Ouvrir **IIS Manager**
2. Sélectionner le nœud serveur (racine)
3. Double-cliquer **Application Request Routing Cache**
4. Panneau droit → **Server Proxy Settings…**
5. Cocher **Enable proxy** → Appliquer

## Étape 2 — Fichier `.env` de production

```powershell
Copy-Item "D:\Claude\Projet Omaya\deploy\env.production.example" "D:\Claude\Projet Omaya\.env"
# Puis éditer et remplacer les REMPLACER
notepad "D:\Claude\Projet Omaya\.env"
```

Points clés :
- `DEBUG=False`
- `CORS_ORIGINS=https://sos.groupe-exo.omaya.fr`
- `HASH_SECRET_KEY` : valeur aléatoire longue (ex. `python -c "import secrets; print(secrets.token_urlsafe(48))"`)

## Étape 3 — Installer le service backend

Ouvrir **PowerShell en administrateur** :

```powershell
cd "D:\Claude\Projet Omaya"
# Installer / maj les dépendances Python dans le venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# Installer le service NSSM
.\deploy\install-service.ps1
```

Vérifs :
- `Get-Service OmayaVendeurAPI` → `Running`
- `curl http://127.0.0.1:8000/` → `{"status":"ok",...}`
- Logs : `D:\Claude\Projet Omaya\logs\api-stderr.log`

## Étape 4 — Builder et déployer le frontend

```powershell
cd "D:\Claude\Projet Omaya"
.\deploy\build-frontend.ps1
```

Le script :
1. Fait `npm ci` + `npm run build` dans `frontend\vendeur\` (avec `base: '/vendeur/'`)
2. Vide le sous-dossier `D:\Sites\groupeOmaya\www\vendeur\`
3. Y copie le contenu de `dist\` + `deploy\web.config` (SPA fallback)
4. Avertit si la règle `/api` est absente du web.config racine

## Étape 5 — web.config racine (reverse proxy /api)

Le site IIS pointant sur `D:\Sites\groupeOmaya\www` existe déjà (binding HTTPS + cert Let's Encrypt). Pas de création à faire.

**Action unique requise** : s'assurer que la règle `OmayaAPI` est présente dans le web.config de la **racine du site** (`D:\Sites\groupeOmaya\www\web.config`).

- **Si le fichier n'existe pas** : copier `deploy\web.config.root.snippet` vers `D:\Sites\groupeOmaya\www\web.config` (le renommer en `web.config`).
- **Si le fichier existe** : fusionner la `<rule name="OmayaAPI">` dans `<rewrite><rules>`, et ajouter les en-têtes de sécurité absents.

### Arborescence finale

```
D:\Sites\groupeOmaya\www\
├── web.config            ← contient la règle OmayaAPI (à fusionner si fichier existant)
├── vendeur\              ← entièrement géré par build-frontend.ps1
│   ├── index.html
│   ├── favicon.svg, icons.svg
│   ├── assets\
│   └── web.config        ← SPA fallback (/vendeur/index.html)
└── <autres fichiers préexistants, non touchés>
```

Si l'app pool a été stoppé, le redémarrer :
```powershell
Import-Module WebAdministration
Restart-WebAppPool -Name "<nom_app_pool>"
```

## Étape 6 — Test

1. Ouvrir **https://sos.groupe-exo.omaya.fr/vendeur/** → redirection vers la page de login
2. Tester une route API : https://sos.groupe-exo.omaya.fr/api/ → `{"status":"ok",...}`
3. Se connecter → tous les onglets du menu doivent fonctionner (URLs `https://.../vendeur/mon-compte`, etc.)

## Mise à jour par la suite

**Backend** (code Python modifié) :
```powershell
Restart-Service OmayaVendeurAPI
```

**Frontend** (code React modifié) :
```powershell
.\deploy\build-frontend.ps1
```

**Dépendances Python ajoutées** :
```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Restart-Service OmayaVendeurAPI
```

## Rollback (désinstallation)

En cas de problème, pour tout retirer proprement :

```powershell
cd "D:\Claude\Projet Omaya"
.\deploy\uninstall.ps1
```

Supprime : service Windows, site IIS, app pool, dossier `D:\Sites\groupeOmaya\www`.
Conserve : code source, `.env`, logs, certificat.

## Dépannage

| Symptôme | Vérifier |
|---|---|
| 502 Bad Gateway sur `/api/...` | ARR proxy activé (étape 1) ? Service uvicorn up ? Règle `OmayaAPI` dans le web.config racine ? |
| 404 sur route profonde (ex. `/vendeur/organigramme`) | `web.config` présent dans `D:\Sites\groupeOmaya\www\vendeur\` avec la règle `SPAFallback` |
| Assets JS/CSS en 404 (page blanche) | Vérifier que `vite.config.ts` a bien `base: '/vendeur/'` et rebuild |
| CORS error dans la console | `CORS_ORIGINS` dans `.env` contient bien `https://sos.groupe-exo.omaya.fr` |
| Service ne démarre pas | `D:\Claude\Projet Omaya\logs\api-stderr.log` |
| Connexion HFSQL échoue | Bridge `Dll_ODBC.exe` présent ? Serveur HFSQL joignable ? |
