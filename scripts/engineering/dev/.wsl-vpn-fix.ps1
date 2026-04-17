# WSL2 VPN Fix — enables routing from WSL2 through Windows host
# Run as Administrator: powershell -ExecutionPolicy Bypass -File .wsl-vpn-fix.ps1
# Fixes: VPN (TAP-Windows/OpenVPN) blocks WSL2 internet access on Windows 10.

param(
    [switch]$Undo  # Use -Undo to revert changes
)

$ErrorActionPreference = "Stop"
$wslInterface = "vEthernet (WSL)"
$firewallRuleName = "WSL2-VPN-Fix"

if ($Undo) {
    Write-Host "Reverting WSL2 VPN fix..." -ForegroundColor Yellow
    Set-NetIPInterface -InterfaceAlias $wslInterface -Forwarding Disabled -ErrorAction SilentlyContinue
    Write-Host "  IP Forwarding disabled"
    Remove-NetFirewallRule -DisplayName $firewallRuleName -ErrorAction SilentlyContinue
    Write-Host "  Firewall rule removed"
    Get-NetNat -Name "WSL2NAT" -ErrorAction SilentlyContinue | Remove-NetNat -Confirm:$false
    Write-Host "  NAT removed (if existed)"
    Write-Host "Done." -ForegroundColor Green
    exit 0
}

Write-Host "Applying WSL2 VPN fix..." -ForegroundColor Cyan

# 1. Get WSL2 subnet
$wslAddr = Get-NetIPAddress -InterfaceAlias $wslInterface -AddressFamily IPv4
$ip = $wslAddr.IPAddress
$prefixLen = $wslAddr.PrefixLength
Write-Host "  WSL interface: $ip/$prefixLen"

# Calculate subnet
$ipBytes = [System.Net.IPAddress]::Parse($ip).GetAddressBytes()
$maskBytes = [byte[]]::new(4)
for ($i = 0; $i -lt 4; $i++) {
    $bits = [Math]::Min(8, [Math]::Max(0, $prefixLen - $i * 8))
    $maskBytes[$i] = [byte](256 - [Math]::Pow(2, 8 - $bits))
}
$networkBytes = [byte[]]::new(4)
for ($i = 0; $i -lt 4; $i++) {
    $networkBytes[$i] = $ipBytes[$i] -band $maskBytes[$i]
}
$network = ($networkBytes -join ".")
$subnet = "$network/$prefixLen"
Write-Host "  WSL subnet: $subnet"

# 2. Enable IP forwarding
Set-NetIPInterface -InterfaceAlias $wslInterface -Forwarding Enabled
Write-Host "  [OK] IP Forwarding enabled" -ForegroundColor Green

# 3. Allow WSL2 traffic through firewall (both directions)
Remove-NetFirewallRule -DisplayName $firewallRuleName -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName $firewallRuleName `
    -Direction Inbound -Action Allow `
    -LocalAddress $subnet -RemoteAddress Any `
    -Protocol Any -Enabled True | Out-Null
Write-Host "  [OK] Firewall rule created" -ForegroundColor Green

# 4. Try NetNat (may fail on Win10 due to ICS conflict — that's OK)
try {
    Get-NetNat -Name "WSL2NAT" -ErrorAction SilentlyContinue | Remove-NetNat -Confirm:$false -ErrorAction SilentlyContinue
    New-NetNat -Name "WSL2NAT" -InternalIPInterfaceAddressPrefix $subnet -ErrorAction Stop | Out-Null
    Write-Host "  [OK] NAT rule created" -ForegroundColor Green
} catch {
    Write-Host "  [SKIP] NetNat failed (ICS conflict, normal on Win10)" -ForegroundColor Yellow
    Write-Host "         Trying ICS sharing instead..." -ForegroundColor Yellow

    # Enable ICS on the VPN adapter to share with WSL
    # Find the VPN adapter (TAP-Windows)
    $vpnAdapter = Get-NetAdapter | Where-Object { $_.InterfaceDescription -match "TAP" -and $_.Status -eq "Up" }
    if (-not $vpnAdapter) {
        # Fallback to any active non-WSL adapter
        $vpnAdapter = Get-NetAdapter | Where-Object {
            $_.Status -eq "Up" -and
            $_.InterfaceAlias -notmatch "WSL|Default Switch|Loopback"
        } | Select-Object -First 1
    }

    if ($vpnAdapter) {
        Write-Host "  Using adapter for ICS: $($vpnAdapter.Name)" -ForegroundColor Cyan

        # Use netsh to enable routing
        $ifIndex = (Get-NetIPInterface -InterfaceAlias $wslInterface -AddressFamily IPv4).ifIndex
        Write-Host "  WSL interface index: $ifIndex"

        # Enable routing via registry (takes effect after reboot, but let's also try netsh)
        $regPath = "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters"
        $currentValue = (Get-ItemProperty $regPath -Name IPEnableRouter -ErrorAction SilentlyContinue).IPEnableRouter
        if ($currentValue -ne 1) {
            Set-ItemProperty $regPath -Name IPEnableRouter -Value 1
            Write-Host "  [OK] IP routing enabled in registry" -ForegroundColor Green
        } else {
            Write-Host "  [OK] IP routing already enabled in registry" -ForegroundColor Green
        }

        # Start Routing and Remote Access if not running
        $rras = Get-Service RemoteAccess -ErrorAction SilentlyContinue
        if ($rras -and $rras.Status -ne "Running") {
            try {
                Set-Service RemoteAccess -StartupType Manual -ErrorAction SilentlyContinue
                Start-Service RemoteAccess -ErrorAction SilentlyContinue
                Write-Host "  [OK] RRAS service started" -ForegroundColor Green
            } catch {
                Write-Host "  [SKIP] Could not start RRAS: $_" -ForegroundColor Yellow
            }
        }
    }
}

# 5. Configure WSL2 DNS
Write-Host ""
Write-Host "Now configure DNS in WSL2:" -ForegroundColor Yellow
Write-Host "  wsl -d Debian -- bash -c 'echo nameserver 172.26.16.1 > /etc/resolv.conf'" -ForegroundColor White
Write-Host ""
Write-Host "Then test:" -ForegroundColor Yellow
Write-Host "  wsl -d Debian -- bash -c 'ping -c 1 172.26.16.1'" -ForegroundColor White
Write-Host "  wsl -d Debian -- bash -c 'curl -s https://api.openai.com/v1/models | head -1'" -ForegroundColor White
