# ==============================
# CONFIG
# ==============================
$TargetRegion = "US"
$ExpectedCountryCode = "US"
$StorePackage = "Microsoft.WindowsStore"

Write-Host "=== START ==="

# ==============================
# 0. Проверка прав
# ==============================
$admin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $admin) {
    Write-Warning "Run as Administrator"
    exit
}

# ==============================
# 1. Проверка IP
# ==============================
Write-Host "[1] Checking IP..."

try {
    $json = curl.exe -s https://ipinfo.io/json | ConvertFrom-Json
    $loc = $json.country

    Write-Host "Detected country: $loc"

    if ($loc -ne $ExpectedCountryCode) {
        Write-Warning "VPN NOT OK (expected $ExpectedCountryCode)"
    } else {
        Write-Host "VPN OK"
    }
}
catch {
    Write-Warning "IP check failed"
}

# ==============================
# 2. Регион
# ==============================
Write-Host "[2] Setting region..."

try {
    Set-WinSystemLocale $TargetRegion
    Set-Culture $TargetRegion

    if ($TargetRegion -eq "US") { $GeoId = 244 }
    elseif ($TargetRegion -eq "DE") { $GeoId = 94 }
    elseif ($TargetRegion -eq "NL") { $GeoId = 176 }
    else { $GeoId = 244 }

    Set-WinHomeLocation -GeoId $GeoId

    Write-Host "Region set"
}
catch {
    Write-Warning "Region failed"
}

# ==============================
# 3. Жёсткое убийство процессов
# ==============================
Write-Host "[3] Killing Store-related processes..."

$targets = @(
    "WinStore.App",
    "Microsoft.WindowsStore",
    "RuntimeBroker",
    "ShellExperienceHost"
)

for ($i = 0; $i -lt 5; $i++) {
    foreach ($name in $targets) {
        Get-Process -Name $name -ErrorAction SilentlyContinue | Stop-Process -Force
    }
    Start-Sleep -Milliseconds 800
}

# ==============================
# 4. Reset Store
# ==============================
Write-Host "[4] Reset..."

Start-Process "wsreset.exe" -Wait

# ==============================
# 5. Re-register с retry
# ==============================
Write-Host "[5] Re-register..."

$success = $false

for ($attempt = 1; $attempt -le 3; $attempt++) {

    Write-Host "Attempt $attempt..."

    # снова убиваем (Store любит воскресать)
    foreach ($name in $targets) {
        Get-Process -Name $name -ErrorAction SilentlyContinue | Stop-Process -Force
    }

    Start-Sleep -Seconds 2

    try {
        $pkg = Get-AppxPackage -AllUsers $StorePackage

        if ($pkg) {
            foreach ($p in $pkg) {
                Add-AppxPackage -DisableDevelopmentMode `
                    -Register "$($p.InstallLocation)\AppxManifest.xml" `
                    -ErrorAction Stop
            }

            Write-Host "Re-register SUCCESS"
            $success = $true
            break
        }
    }
    catch {
        Write-Warning "Attempt failed"
    }

    Start-Sleep -Seconds 2
}

if (-not $success) {
    Write-Warning "Re-register failed after retries"
}

# ==============================
# 6. Запуск Store
# ==============================
Write-Host "[6] Launching..."

Start-Process "ms-windows-store:"

Write-Host "=== DONE ==="