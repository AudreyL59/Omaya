# Build du frontend Vendeur + copie dans le site IIS.
# On possede tout le sous-dossier /vendeur sous www : on peut le wiper avant re-copie.
# Le reste de D:\Sites\groupeOmaya\www\ n'est jamais touche.

$ErrorActionPreference = "Stop"

# --- Variables a adapter --------------------------------------------------
$ProjectRoot = "D:\Claude\Projet Omaya"
$FrontendDir = "$ProjectRoot\frontend\vendeur"
$TargetDir   = "D:\Sites\groupeOmaya\www\vendeur"
$WebConfig   = "$ProjectRoot\deploy\web.config"
$RootConfig  = "D:\Sites\groupeOmaya\www\web.config"

# --- Build ----------------------------------------------------------------
Push-Location $FrontendDir
try {
    Write-Host "Installation des dependances..." -ForegroundColor Cyan
    npm ci

    Write-Host "Build production..." -ForegroundColor Cyan
    npm run build
    if (-not (Test-Path "$FrontendDir\dist\index.html")) {
        throw "Build echoue : dist\index.html introuvable"
    }
}
finally {
    Pop-Location
}

# --- Deploiement ----------------------------------------------------------
Write-Host "Deploiement vers $TargetDir..." -ForegroundColor Cyan
if (Test-Path $TargetDir) {
    Get-ChildItem -Path $TargetDir -Force | Remove-Item -Recurse -Force
} else {
    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
}

Copy-Item -Path "$FrontendDir\dist\*" -Destination $TargetDir -Recurse -Force
Copy-Item -Path $WebConfig -Destination (Join-Path $TargetDir "web.config") -Force

Write-Host ""
Write-Host "Frontend deploye dans : $TargetDir" -ForegroundColor Green

# --- Rappel sur le web.config racine --------------------------------------
if (-not (Test-Path $RootConfig)) {
    Write-Host ""
    Write-Host "ATTENTION : $RootConfig n'existe pas." -ForegroundColor Yellow
    Write-Host "Le reverse proxy /api ne fonctionnera PAS tant qu'il n'est pas en place." -ForegroundColor Yellow
    Write-Host "Copier deploy\web.config.root.snippet vers $RootConfig (ou fusionner avec l'existant)." -ForegroundColor Yellow
} else {
    $rootXml = Get-Content $RootConfig -Raw
    if ($rootXml -notmatch 'OmayaAPI') {
        Write-Host ""
        Write-Host "ATTENTION : regle 'OmayaAPI' non trouvee dans $RootConfig." -ForegroundColor Yellow
        Write-Host "Fusionner le contenu de deploy\web.config.root.snippet dans ce fichier." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Testez : https://sos.groupe-exo.omaya.fr/vendeur/" -ForegroundColor Green
