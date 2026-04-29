# Deploiement complet Omaya :
#  1. Si modifs locales -> commit + push (regle "push avant pull serveur")
#  2. git pull
#  3. Restart services NSSM (OmayaVendeurAPI + OmayaProductionWorker)
#  4. Build + deploiement frontend Vendeur (vers IIS)
#  5. Build + deploiement frontend ADM (vers IIS)
#
# Usage (PowerShell admin recommande pour les services NSSM) :
#   .\deploy\deploy-all.ps1
#
# Options :
#   -SkipApi       : ne redemarre pas OmayaVendeurAPI
#   -SkipWorker    : ne redemarre pas OmayaProductionWorker
#   -SkipVendeur   : ne builde pas frontend\vendeur
#   -SkipAdm       : ne builde pas frontend\adm
#   -SkipPull      : pas de git pull (utile en dev local)

param(
    [switch]$SkipApi,
    [switch]$SkipWorker,
    [switch]$SkipVendeur,
    [switch]$SkipAdm,
    [switch]$SkipPull
)

$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Claude\Projet Omaya"
$DeployDir   = Join-Path $ProjectRoot "deploy"

Push-Location $ProjectRoot
try {

    # --- 1. Push local eventuel ----------------------------------------
    if (-not $SkipPull) {
        Write-Host ""
        Write-Host "[1/5] Verification des modifs locales..." -ForegroundColor Cyan

        $status = git status --porcelain
        if ($status) {
            Write-Host "  Modifs locales detectees :" -ForegroundColor Yellow
            git status --short
            Write-Host ""
            $msg = "deploy: auto-commit avant pull (" + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + ")"
            git add -A
            git commit -m $msg
            git push
            Write-Host "  Commit + push OK" -ForegroundColor Green
        } else {
            Write-Host "  Working tree clean" -ForegroundColor Green
        }

        Write-Host ""
        Write-Host "[2/5] git pull..." -ForegroundColor Cyan
        git pull --rebase
    } else {
        Write-Host "[1-2/5] git pull skip" -ForegroundColor DarkGray
    }

    # --- 3. Restart services -------------------------------------------
    Write-Host ""
    Write-Host "[3/5] Restart services NSSM..." -ForegroundColor Cyan

    function Restart-NssmService {
        param([string]$Name)
        $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
        if (-not $svc) {
            Write-Host "  $Name : service introuvable, skip" -ForegroundColor Yellow
            return
        }
        Write-Host "  $Name : restart..." -ForegroundColor DarkGray
        & nssm restart $Name | Out-Null
        Start-Sleep -Seconds 2
        $after = Get-Service -Name $Name
        Write-Host ("  {0} : {1}" -f $Name, $after.Status) -ForegroundColor Green
    }

    if (-not $SkipApi)    { Restart-NssmService "OmayaVendeurAPI" }    else { Write-Host "  API skip" -ForegroundColor DarkGray }
    if (-not $SkipWorker) { Restart-NssmService "OmayaProductionWorker" } else { Write-Host "  Worker skip" -ForegroundColor DarkGray }

    # --- 4. Build frontend Vendeur -------------------------------------
    Write-Host ""
    if (-not $SkipVendeur) {
        Write-Host "[4/5] Build frontend Vendeur..." -ForegroundColor Cyan
        & (Join-Path $DeployDir "build-frontend.ps1")
    } else {
        Write-Host "[4/5] Build Vendeur skip" -ForegroundColor DarkGray
    }

    # --- 5. Build frontend ADM -----------------------------------------
    Write-Host ""
    if (-not $SkipAdm) {
        Write-Host "[5/5] Build frontend ADM..." -ForegroundColor Cyan
        & (Join-Path $DeployDir "build-frontend-adm.ps1")
    } else {
        Write-Host "[5/5] Build ADM skip" -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "===========================================" -ForegroundColor Green
    Write-Host " Deploiement termine" -ForegroundColor Green
    Write-Host "===========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Cote navigateur : Ctrl+Shift+R pour bypass cache" -ForegroundColor Yellow
}
finally {
    Pop-Location
}
