# Wrapper PowerShell pour Task Scheduler.
# Lance scripts/monitor_symmetricds.py via le venv du projet.
#
# Installation Task Scheduler :
#   - Programme : powershell.exe
#   - Arguments : -ExecutionPolicy Bypass -File "D:\Sites\groupeOmaya\Code\scripts\monitor_symmetricds.ps1"
#   - Demarrer dans : D:\Sites\groupeOmaya\Code
#   - Frequence : toutes les 15 min
#   - User : SYSTEM (ou un compte avec acces PG + reseau)
#   - 'Executer meme si l'utilisateur n'est pas connecte' : OUI

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$Script = Join-Path $ProjectRoot "scripts\monitor_symmetricds.py"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Python venv introuvable : $PythonExe"
    exit 1
}
if (-not (Test-Path $Script)) {
    Write-Error "Script introuvable : $Script"
    exit 1
}

& $PythonExe $Script
exit $LASTEXITCODE
