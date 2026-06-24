# Build du frontend ADM + copie dans le site IIS.
# On possede tout le sous-dossier /adm sous www : on peut le wiper avant re-copie.
# Le reste de D:\Sites\groupeOmaya\www\ n'est jamais touche.

$ErrorActionPreference = "Stop"

# --- Variables a adapter --------------------------------------------------
$ProjectRoot = "D:\Claude\Projet Omaya"
$FrontendDir = "$ProjectRoot\frontend\adm"
$TargetDir   = "D:\Sites\groupeOmaya\www\adm"
$WebConfig   = "$ProjectRoot\deploy\web.config.adm"
$RootConfig  = "D:\Sites\groupeOmaya\www\web.config"

# --- Build ----------------------------------------------------------------
Push-Location $FrontendDir
try {
    Write-Host "Installation des dependances..." -ForegroundColor Cyan
    npm ci

    Write-Host "Build production..." -ForegroundColor Cyan
    # Wipe l'ancien dist pour eviter de deployer un build precedent si
    # npm run build echoue silencieusement (PS5 ne propage pas l'exit
    # code de npm par defaut).
    if (Test-Path "$FrontendDir\dist") {
        Remove-Item -Recurse -Force "$FrontendDir\dist"
    }
    npm run build
    if ($LASTEXITCODE -ne 0) {
        throw "Build echoue : npm run build exit code $LASTEXITCODE"
    }
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
Write-Host "Frontend ADM deploye dans : $TargetDir" -ForegroundColor Green

# --- web.config racine ----------------------------------------------------
# Idem build-frontend.ps1 : copie auto si absent (fresh install), alerte si
# present sans 'OmayaAPI' (cas serveur interne avec WEBDEV/ASP.NET deja).
$RootTemplate = "$ProjectRoot\deploy\web.config.ovh-root"
if (-not (Test-Path $RootConfig)) {
    Write-Host ""
    Write-Host "$RootConfig absent -> copie automatique depuis $RootTemplate" -ForegroundColor Cyan
    Copy-Item -Path $RootTemplate -Destination $RootConfig -Force
    Write-Host "OK. Verifier que IIS URL Rewrite + ARR sont installes et ARR Proxy active." -ForegroundColor Green
} else {
    $rootXml = Get-Content $RootConfig -Raw
    if ($rootXml -notmatch 'OmayaAPI') {
        Write-Host ""
        Write-Host "ATTENTION : regle 'OmayaAPI' non trouvee dans $RootConfig." -ForegroundColor Yellow
        Write-Host "Fusionner le contenu de deploy\web.config.root.snippet dans ce fichier." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Testez : https://sos.groupe-exo.omaya.fr/adm/" -ForegroundColor Green
Write-Host ""
Write-Host "Si premier deploiement : n'oublie pas de creer l'Application IIS dediee :" -ForegroundColor Cyan
Write-Host "  New-WebAppPool -Name OmayaAdmPool" -ForegroundColor DarkGray
Write-Host "  Set-ItemProperty -Path 'IIS:\AppPools\OmayaAdmPool' -Name 'managedRuntimeVersion' -Value ''" -ForegroundColor DarkGray
Write-Host "  New-WebApplication -Site 'groupeOmaya - Site WEBDEV client' -Name 'adm' -PhysicalPath '$TargetDir' -ApplicationPool 'OmayaAdmPool'" -ForegroundColor DarkGray
