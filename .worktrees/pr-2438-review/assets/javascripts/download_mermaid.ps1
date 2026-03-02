# Download mermaid bundle and css into assets (PowerShell)
# Usage: .\download_mermaid.ps1 -Version 10.4.0 -Proxy 'http://proxy:8080'
param(
    [string]$Version = '10.4.0',
    [string]$Proxy = ''
)

Write-Host "Downloading mermaid v$Version to assets/javascripts and assets/stylesheets..."

# Ensure TLS 1.2 (required on older Windows / PowerShell hosts)
try
{
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
}
catch
{
    Write-Host "Warning: Could not set SecurityProtocol to TLS1.2, continuing and hoping for the best."
}

if ($Proxy -ne '')
{
    try
    {
        Write-Host "Setting default web proxy: $Proxy"
        $webProxy = New-Object System.Net.WebProxy($Proxy)
        [System.Net.WebRequest]::DefaultWebProxy = $webProxy
        [System.Net.WebRequest]::DefaultWebProxy.Credentials = [System.Net.CredentialCache]::DefaultNetworkCredentials
    }
    catch
    {
        Write-Host "Warning: could not set DefaultWebProxy: $( $_.Exception.Message )"
    }
}

New-Item -ItemType Directory -Path assets\javascripts -Force | Out-Null
New-Item -ItemType Directory -Path assets\stylesheets -Force | Out-Null

$base = "https://cdn.jsdelivr.net/npm/mermaid@$Version/dist"

function TryInvokeWebRequest($url, $outPath)
{
    try
    {
        Write-Host "[Invoke-WebRequest] $url -> $outPath"
        if ($Proxy -ne '')
        {
            Invoke-WebRequest -Uri $url -OutFile $outPath -Proxy $Proxy -ErrorAction Stop
        }
        else
        {
            Invoke-WebRequest -Uri $url -OutFile $outPath -ErrorAction Stop
        }
        return $true
    }
    catch
    {
        Write-Host "Invoke-WebRequest failed: $( $_.Exception.Message )"
        return $false
    }
}

function TryBitsTransfer($url, $outPath)
{
    try
    {
        Write-Host "[BITS] $url -> $outPath"
        # Start-BitsTransfer will typically use system proxy settings
        Start-BitsTransfer -Source $url -Destination $outPath -ErrorAction Stop
        return $true
    }
    catch
    {
        Write-Host "Start-BitsTransfer failed: $( $_.Exception.Message )"
        return $false
    }
}

function TryWebClient($url, $outPath)
{
    try
    {
        Write-Host "[WebClient] $url -> $outPath (forcing TLS1.2)"
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $wc = New-Object System.Net.WebClient
        if ($Proxy -ne '')
        {
            $wc.Proxy = New-Object System.Net.WebProxy($Proxy)
        }
        $wc.DownloadFile($url, $outPath)
        return $true
    }
    catch
    {
        Write-Host "WebClient failed: $( $_.Exception.Message )"
        return $false
    }
}

function DownloadFile($url, $outPath)
{
    if (Test-Path $outPath)
    {
        Write-Host "Already exists: $outPath"; return
    }
    if (TryInvokeWebRequest $url $outPath)
    {
        return
    }
    if (Get-Command Start-BitsTransfer -ErrorAction SilentlyContinue)
    {
        if (TryBitsTransfer $url $outPath)
        {
            return
        }
    }
    if (TryWebClient $url $outPath)
    {
        return
    }
    Write-Host "All download methods failed for $url"
}

DownloadFile "$base/mermaid.min.js" "assets\javascripts\mermaid.min.js"
DownloadFile "$base/mermaid.esm.min.mjs" "assets\javascripts\mermaid.esm.min.mjs"
DownloadFile "$base/mermaid.min.css" "assets\stylesheets\mermaid.css"

# Record version
$Version | Out-File -FilePath assets\javascripts\MERMAID_VERSION -Encoding utf8

Write-Host "Done. Please git add assets/javascripts/mermaid.min.js assets/javascripts/mermaid-init.js assets/stylesheets/mermaid.css assets/javascripts/MERMAID_VERSION"
