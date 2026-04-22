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
Write-Host "Frontend ADM deploye dans : $TargetDir" -ForegroundColor Green

# --- Rappel sur le web.config racine --------------------------------------
if (-not (Test-Path $RootConfig)) {
    Write-Host ""
    Write-Host "ATTENTION : $RootConfig n'existe pas." -ForegroundColor Yellow
    Write-Host "Le reverse proxy /api ne fonctionnera PAS tant qu'il n'est pas en place." -ForegroundColor Yellow
} else {
    $rootXml = Get-Content $RootConfig -Raw
    if ($rootXml -notmatch 'OmayaAPI') {
        Write-Host ""
        Write-Host "ATTENTION : regle 'OmayaAPI' non trouvee dans $RootConfig." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Testez : https://sos.groupe-exo.omaya.fr/adm/" -ForegroundColor Green
Write-Host ""
Write-Host "Si premier deploiement : n'oublie pas de creer l'Application IIS dediee :" -ForegroundColor Cyan
Write-Host "  New-WebAppPool -Name OmayaAdmPool" -ForegroundColor DarkGray
Write-Host "  Set-ItemProperty -Path 'IIS:\AppPools\OmayaAdmPool' -Name 'managedRuntimeVersion' -Value ''" -ForegroundColor DarkGray
Write-Host "  New-WebApplication -Site 'groupeOmaya - Site WEBDEV client' -Name 'adm' -PhysicalPath '$TargetDir' -ApplicationPool 'OmayaAdmPool'" -ForegroundColor DarkGray
