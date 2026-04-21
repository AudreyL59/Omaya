# Verifie que tous les pre-requis serveur sont en place avant deploiement.
# A executer en administrateur.

$ErrorActionPreference = "Continue"
$ProjectRoot = "D:\Claude\Projet Omaya"
$Errors = @()
$Warnings = @()

function Check-Item($Label, $Ok, $Detail, [switch]$Warning) {
    if ($Ok) {
        Write-Host ("  [OK]   {0}" -f $Label) -ForegroundColor Green
        if ($Detail) { Write-Host ("         {0}" -f $Detail) -ForegroundColor DarkGray }
    } else {
        if ($Warning) {
            Write-Host ("  [WARN] {0}" -f $Label) -ForegroundColor Yellow
            $script:Warnings += "$Label - $Detail"
        } else {
            Write-Host ("  [KO]   {0}" -f $Label) -ForegroundColor Red
            $script:Errors += "$Label - $Detail"
        }
        if ($Detail) { Write-Host ("         {0}" -f $Detail) -ForegroundColor DarkGray }
    }
}

Write-Host ""
Write-Host "== Verification pre-requis deploiement Omaya ==" -ForegroundColor Cyan
Write-Host ""

# --- 1. Fichiers projet ---------------------------------------------------
Write-Host "[Projet]" -ForegroundColor Cyan
Check-Item "Repertoire projet" (Test-Path $ProjectRoot) $ProjectRoot
Check-Item "venv Python" (Test-Path "$ProjectRoot\venv\Scripts\python.exe") "$ProjectRoot\venv\Scripts\python.exe"
Check-Item "requirements.txt" (Test-Path "$ProjectRoot\requirements.txt") ""
Check-Item "Fichier .env" (Test-Path "$ProjectRoot\.env") "$ProjectRoot\.env"
Check-Item "Bridge WinDev" (Test-Path "$ProjectRoot\bridge\Dll_ODBC.exe") "$ProjectRoot\bridge\Dll_ODBC.exe"
Check-Item "Frontend src" (Test-Path "$ProjectRoot\frontend\vendeur\package.json") ""

# --- 2. Outils ------------------------------------------------------------
Write-Host ""
Write-Host "[Outils]" -ForegroundColor Cyan
$nssm = Get-Command nssm -ErrorAction SilentlyContinue
Check-Item "NSSM dans PATH" ($nssm -ne $null) $(if ($nssm) { $nssm.Source } else { "https://nssm.cc/download" })

$node = Get-Command node -ErrorAction SilentlyContinue
Check-Item "Node.js dans PATH" ($node -ne $null) $(if ($node) { "version : " + (node -v) } else { "" })

$npm = Get-Command npm -ErrorAction SilentlyContinue
Check-Item "npm dans PATH" ($npm -ne $null) ""

# --- 3. IIS + modules -----------------------------------------------------
Write-Host ""
Write-Host "[IIS]" -ForegroundColor Cyan
$iisService = Get-Service -Name W3SVC -ErrorAction SilentlyContinue
Check-Item "Service IIS (W3SVC)" ($iisService -ne $null -and $iisService.Status -eq 'Running') $(if ($iisService) { "Status : $($iisService.Status)" } else { "Non installe" })

try {
    Import-Module WebAdministration -ErrorAction Stop

    # URL Rewrite : module enregistre dans IIS ?
    $urlRewriteModule = Get-WebGlobalModule -Name 'RewriteModule' -ErrorAction SilentlyContinue
    Check-Item "URL Rewrite module" ($urlRewriteModule -ne $null) "https://www.iis.net/downloads/microsoft/url-rewrite"

    # ARR : module enregistre dans IIS ?
    $arrModule = Get-WebGlobalModule -Name 'ApplicationRequestRouting' -ErrorAction SilentlyContinue
    if (-not $arrModule) {
        $arrModule = Get-WebGlobalModule -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match 'RequestRouter|ApplicationRequestRouting' } |
            Select-Object -First 1
    }
    Check-Item "ARR module" ($arrModule -ne $null) "https://www.iis.net/downloads/microsoft/application-request-routing"

    # ARR Proxy active ?
    $proxyEnabled = $false
    $section = Get-WebConfiguration -PSPath 'MACHINE/WEBROOT/APPHOST' -Filter 'system.webServer/proxy' -ErrorAction SilentlyContinue
    if ($section) { $proxyEnabled = [bool]$section.enabled }
    Check-Item "ARR Proxy active" $proxyEnabled "IIS Manager > ARR Cache > Server Proxy Settings > Enable proxy"
} catch {
    Check-Item "Verification modules IIS" $false "Module WebAdministration indisponible : $($_.Exception.Message)" -Warning
}

# --- 4. Certificat HTTPS --------------------------------------------------
Write-Host ""
Write-Host "[Certificat]" -ForegroundColor Cyan
# Cherche dans plusieurs stores (My = Personal, WebHosting = IIS, Root = AC racines)
$certStores = @('Cert:\LocalMachine\My', 'Cert:\LocalMachine\WebHosting', 'Cert:\LocalMachine\Root')
$cert = $null
$certStore = $null
foreach ($store in $certStores) {
    if (-not (Test-Path $store)) { continue }
    $found = Get-ChildItem -Path $store -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Subject -match 'sos\.groupe-exo\.omaya\.fr' -or
            ($_.DnsNameList -and $_.DnsNameList.Unicode -contains 'sos.groupe-exo.omaya.fr')
        } |
        Sort-Object NotAfter -Descending | Select-Object -First 1
    if ($found) {
        $cert = $found
        $certStore = $store
        break
    }
}
if ($cert) {
    $daysLeft = ($cert.NotAfter - (Get-Date)).Days
    $detail = "Store $certStore - expire le $($cert.NotAfter.ToString('yyyy-MM-dd')) - $daysLeft jours restants"
    if ($daysLeft -lt 0) {
        Check-Item "Certificat sos.groupe-exo.omaya.fr" $false $detail
    } elseif ($daysLeft -lt 15) {
        Check-Item "Certificat sos.groupe-exo.omaya.fr" $true $detail -Warning
    } else {
        Check-Item "Certificat sos.groupe-exo.omaya.fr" $true $detail
    }
} else {
    Check-Item "Certificat sos.groupe-exo.omaya.fr" $false "Non trouve dans : $($certStores -join ', ')" -Warning
}

# --- 5. Ports -------------------------------------------------------------
Write-Host ""
Write-Host "[Reseau]" -ForegroundColor Cyan
$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port8000) {
    $proc = Get-Process -Id $port8000.OwningProcess -ErrorAction SilentlyContinue
    Check-Item "Port 8000 libre" $false "Deja utilise par : $($proc.ProcessName) (PID $($port8000.OwningProcess))" -Warning
} else {
    Check-Item "Port 8000 libre" $true ""
}

$port443 = Get-NetTCPConnection -LocalPort 443 -State Listen -ErrorAction SilentlyContinue
Check-Item "Port 443 en ecoute (IIS)" ($port443 -ne $null) ""

# --- 6. Service existant --------------------------------------------------
Write-Host ""
Write-Host "[Service]" -ForegroundColor Cyan
$svc = Get-Service OmayaVendeurAPI -ErrorAction SilentlyContinue
if ($svc) {
    Check-Item "Service OmayaVendeurAPI" $true "Deja installe - status : $($svc.Status)" -Warning
} else {
    Write-Host "  [INFO] Service OmayaVendeurAPI non installe (normal avant premiere install)" -ForegroundColor DarkGray
}

# --- Resume ---------------------------------------------------------------
Write-Host ""
Write-Host "== Resume ==" -ForegroundColor Cyan
if ($Errors.Count -eq 0 -and $Warnings.Count -eq 0) {
    Write-Host "Tout est pret pour le deploiement." -ForegroundColor Green
    exit 0
}
if ($Warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "Avertissements ($($Warnings.Count)) :" -ForegroundColor Yellow
    $Warnings | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
}
if ($Errors.Count -gt 0) {
    Write-Host ""
    Write-Host "Erreurs bloquantes ($($Errors.Count)) :" -ForegroundColor Red
    $Errors | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
}
exit 0
