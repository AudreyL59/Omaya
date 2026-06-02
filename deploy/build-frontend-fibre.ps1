# Build du frontend Call Fibre + copie dans le site IIS intracall.omaya.fr.
# Cible : sous-dossier /cf de l'IIS du site intracall.omaya.fr.

$ErrorActionPreference = "Stop"

# --- Variables a adapter --------------------------------------------------
$ProjectRoot = "D:\Claude\Projet Omaya"
$FrontendDir = "$ProjectRoot\frontend\fibre"
$TargetDir   = "D:\Sites\IntraCall\www\cf"
$WebConfig   = "$ProjectRoot\deploy\web.config.cf"
$RootConfig  = "D:\Sites\IntraCall\www\web.config"

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
Write-Host "Frontend Call Fibre deploye dans : $TargetDir" -ForegroundColor Green

# --- Rappel sur le web.config racine --------------------------------------
if (-not (Test-Path $RootConfig)) {
    Write-Host ""
    Write-Host "ATTENTION : $RootConfig n'existe pas." -ForegroundColor Yellow
    Write-Host "  - Le reverse proxy /api ne fonctionnera PAS tant qu'il n'est pas en place." -ForegroundColor Yellow
    Write-Host "  - La racine du domaine ne renverra pas 404 non plus." -ForegroundColor Yellow
    Write-Host "  Copier : $ProjectRoot\deploy\web.config.intracall -> $RootConfig" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Testez : https://intracall.omaya.fr/cf/" -ForegroundColor Green
Write-Host ""
Write-Host "Si premier deploiement : n'oublie pas de creer l'Application IIS dediee :" -ForegroundColor Cyan
Write-Host "  New-WebAppPool -Name OmayaCallFibrePool" -ForegroundColor DarkGray
Write-Host "  Set-ItemProperty -Path 'IIS:\AppPools\OmayaCallFibrePool' -Name 'managedRuntimeVersion' -Value ''" -ForegroundColor DarkGray
Write-Host "  New-WebApplication -Site 'IntraCall - Site WEBDEV client' -Name 'cf' -PhysicalPath '$TargetDir' -ApplicationPool 'OmayaCallFibrePool'" -ForegroundColor DarkGray
