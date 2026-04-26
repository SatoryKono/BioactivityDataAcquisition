$ErrorActionPreference = 'Stop'

$gitCmd = 'C:\Program Files\Git\cmd'
$marker = 'Ensure Git for Windows precedes GitHub Desktop in PATH'

$snippet = @"
# $marker
$gitCmdPath = '$gitCmd'
if (-not ((`$env:Path -split ';') -contains `$gitCmdPath)) {
    `$env:Path = `$gitCmdPath + ';' + `$env:Path
}
"@

function Update-ProfileFile {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path
    )

    $parent = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }

    if (Test-Path -LiteralPath $Path) {
        $content = Get-Content -Raw -LiteralPath $Path
        if ($content -match [regex]::Escape($marker)) {
            return $false
        }

        Add-Content -LiteralPath $Path -Value "`r`n$snippet"
        return $true
    }

    Set-Content -LiteralPath $Path -Value $snippet
    return $true
}

$updated = @()
$targets = @(
    (Join-Path $env:USERPROFILE 'Documents\WindowsPowerShell\profile.ps1'),
    (Join-Path $env:USERPROFILE 'Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1')
)

foreach ($target in $targets) {
    if (Update-ProfileFile -Path $target) {
        $updated += $target
    }
}

if ($updated.Count -eq 0) {
    Write-Host 'No profile changes were needed.'
} else {
    Write-Host 'Updated profile file(s):'
    $updated | ForEach-Object { Write-Host $_ }
}

$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ([string]::IsNullOrWhiteSpace($userPath)) {
    $segments = @()
} else {
    $segments = $userPath -split ';' | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
}

$desired = 'C:\Program Files\Git\cmd'
$filtered = @($segments | Where-Object { $_ -ine $desired })
$newPath = @($desired) + $filtered
[Environment]::SetEnvironmentVariable('Path', ($newPath -join ';'), 'User')
Write-Host 'Updated user PATH order for new sessions.'
