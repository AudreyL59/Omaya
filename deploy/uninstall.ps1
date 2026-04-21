# Rollback complet du deploiement Omaya Vendeur.
# - Arrete et supprime le service Windows
# - Supprime le site IIS + app pool
# - Supprime le sous-dossier D:\Sites\groupeOmaya\www\vendeur
#
# NE SUPPRIME PAS :
# - Le code source dans D:\Claude\Projet Omaya (dev)
# - Le fichier .env
# - Les logs (pour analyse post-mortem)
# - Le certificat HTTPS
# - Le web.config racine (meme s'il contient la regle OmayaAPI)
# - Tout autre contenu de D:\Sites\groupeOmaya\www\
#
# A executer en administrateur.

$ErrorActionPreference = "Continue"

# --- Variables a adapter --------------------------------------------------
$ServiceName = "OmayaVendeurAPI"
$IISSiteName = "omaya-vendeur"
$IISAppPool  = "omaya-vendeur"
$TargetDir   = "D:\Sites\groupeOmaya\www\vendeur"

Write-Host ""
Write-Host "== Rollback Omaya Vendeur ==" -ForegroundColor Cyan
Write-Host ""

$confirm = Read-Host "Confirmer le rollback complet ? (oui/non)"
if ($confirm -ne "oui") {
    Write-Host "Annule." -ForegroundColor Yellow
    exit 0
}

# --- 1. Service backend ---------------------------------------------------
Write-Host ""
Write-Host "[1/3] Service Windows" -ForegroundColor Cyan
$svc = Get-Service $ServiceName -ErrorAction SilentlyContinue
if ($svc) {
    if ($svc.Status -eq 'Running') {
        Write-Host "  Arret du service..."
        & nssm stop $ServiceName confirm 2>&1 | Out-Null
    }
    Write-Host "  Suppression du service..."
    & nssm remove $ServiceName confirm 2>&1 | Out-Null
    Write-Host "  Service supprime." -ForegroundColor Green
} else {
    Write-Host "  Service absent (rien a faire)." -ForegroundColor DarkGray
}

# --- 2. Site IIS ----------------------------------------------------------
Write-Host ""
Write-Host "[2/3] Site IIS" -ForegroundColor Cyan
try {
    Import-Module WebAdministration -ErrorAction Stop

    if (Test-Path "IIS:\Sites\$IISSiteName") {
        Write-Host "  Suppression du site $IISSiteName..."
        Remove-Website -Name $IISSiteName
        Write-Host "  Site supprime." -ForegroundColor Green
    } else {
        Write-Host "  Site $IISSiteName absent." -ForegroundColor DarkGray
    }

    if (Test-Path "IIS:\AppPools\$IISAppPool") {
        Write-Host "  Suppression de l'app pool $IISAppPool..."
        Remove-WebAppPool -Name $IISAppPool
        Write-Host "  App pool supprime." -ForegroundColor Green
    } else {
        Write-Host "  App pool $IISAppPool absent." -ForegroundColor DarkGray
    }
} catch {
    Write-Host "  Module WebAdministration indisponible - suppression IIS a faire manuellement." -ForegroundColor Yellow
}

# --- 3. Sous-dossier frontend ---------------------------------------------
Write-Host ""
Write-Host "[3/3] Suppression du sous-dossier $TargetDir" -ForegroundColor Cyan
if (Test-Path $TargetDir) {
    Remove-Item -Path $TargetDir -Recurse -Force
    Write-Host "  Dossier supprime (www reste intact)." -ForegroundColor Green
} else {
    Write-Host "  $TargetDir absent." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "NB : la regle 'OmayaAPI' dans le web.config racine n'a PAS ete retiree." -ForegroundColor Yellow
Write-Host "Si besoin, editer D:\Sites\groupeOmaya\www\web.config manuellement." -ForegroundColor Yellow

Write-Host ""
Write-Host "Rollback termine." -ForegroundColor Green
Write-Host "Le code source et .env n'ont PAS ete touches." -ForegroundColor DarkGray
