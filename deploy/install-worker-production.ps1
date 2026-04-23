# Installation du service Windows pour le worker d'extraction production via NSSM.
# Pre-requis : NSSM installe et dans le PATH.
# A executer en administrateur dans PowerShell.

$ErrorActionPreference = "Stop"

# --- Variables a adapter --------------------------------------------------
$ServiceName   = "OmayaProductionWorker"
$ProjectRoot   = "D:\Claude\Projet Omaya"
$PythonExe     = "$ProjectRoot\venv\Scripts\python.exe"
$WorkerScript  = "$ProjectRoot\worker_production.py"
$LogDir        = "$ProjectRoot\logs"

# --- Verifications --------------------------------------------------------
if (-not (Test-Path $PythonExe)) {
    throw "Python introuvable : $PythonExe"
}
if (-not (Test-Path $WorkerScript)) {
    throw "Worker script introuvable : $WorkerScript"
}
if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    throw "NSSM n'est pas dans le PATH. Installe-le depuis https://nssm.cc/download"
}
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# --- (Re)installation -----------------------------------------------------
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Service existant detecte, arret + suppression..." -ForegroundColor Yellow
    if ($existing.Status -eq 'Running') {
        & nssm stop $ServiceName confirm | Out-Null
    }
    & nssm remove $ServiceName confirm | Out-Null
}

# Creation
& nssm install $ServiceName $PythonExe $WorkerScript
& nssm set $ServiceName AppDirectory        $ProjectRoot
& nssm set $ServiceName AppEnvironmentExtra "PYTHONUNBUFFERED=1"
& nssm set $ServiceName Start               SERVICE_AUTO_START
& nssm set $ServiceName Description         "ERP Omaya - Worker extraction production"
& nssm set $ServiceName AppStdout           "$LogDir\worker-production-stdout.log"
& nssm set $ServiceName AppStderr           "$LogDir\worker-production-stderr.log"
& nssm set $ServiceName AppRotateFiles      1
& nssm set $ServiceName AppRotateBytes      10485760
& nssm set $ServiceName AppExit             Default Restart

# Demarrage
& nssm start $ServiceName

Start-Sleep -Seconds 2
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($svc) {
    Write-Host "Status : $($svc.Status)" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Service installe : $ServiceName" -ForegroundColor Green
Write-Host "Logs             : $LogDir" -ForegroundColor Green
Write-Host "Fichier log app  : $LogDir\worker-production.log" -ForegroundColor Green
