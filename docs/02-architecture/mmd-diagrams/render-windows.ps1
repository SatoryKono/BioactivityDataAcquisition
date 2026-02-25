#Requires -Version 5.1
param(
    [switch]$SvgOnly,
    [switch]$PngOnly,
    [string]$Filter = '*',
    [int]$Scale = 3,
    [int]$Width = 2400,
    [int]$Height = 1800,
    [string[]]$Dirs = @()
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$theme   = Join-Path (Join-Path $baseDir 'theme') 'mermaid-config.json'
$css     = Join-Path (Join-Path $baseDir 'theme') 'custom.css'

$defaultDirs = @('architecture', 'class-diagrams', 'foundation')
$sourceDirs  = if ($Dirs.Count -gt 0) { $Dirs } else { $defaultDirs | ForEach-Object { Join-Path $baseDir $_ } }

$doSvg = -not $PngOnly
$doPng = -not $SvgOnly

$ok = 0; $fail = 0

foreach ($srcDir in $sourceDirs) {
    if (-not (Test-Path $srcDir)) {
        Write-Warning "Directory not found, skipping: $srcDir"
        continue
    }
    Write-Host "`n=== $(Split-Path -Leaf $srcDir) ===" -ForegroundColor Cyan

    $files = Get-ChildItem -Path (Join-Path $srcDir '*') -Include "$Filter.mmd", "$Filter.mermaid" -ErrorAction SilentlyContinue

    foreach ($f in $files) {
        $svgOk = $true; $pngOk = $true

        if ($doSvg) {
            $svgDir = Join-Path $srcDir 'svg'
            $null   = New-Item -ItemType Directory -Force -Path $svgDir
            $svgOut = Join-Path $svgDir "$($f.BaseName).svg"
            mmdc -i $f.FullName -o $svgOut -c $theme --cssFile $css -w $Width -H $Height 2>&1 | Out-Null
            $svgOk = Test-Path $svgOut
        }

        if ($doPng) {
            $pngDir = Join-Path $srcDir 'png'
            $null   = New-Item -ItemType Directory -Force -Path $pngDir
            $pngOut = Join-Path $pngDir "$($f.BaseName).png"
            mmdc -i $f.FullName -o $pngOut -c $theme --cssFile $css -s $Scale -w $Width -H $Height -b white 2>&1 | Out-Null
            $pngOk = Test-Path $pngOut
        }

        if ($svgOk -and $pngOk) {
            Write-Host "  OK   $($f.BaseName)" -ForegroundColor Green
            $ok++
        } else {
            $detail = "svg=$svgOk png=$pngOk"
            Write-Host "  FAIL $($f.BaseName) ($detail)" -ForegroundColor Red
            $fail++
        }
    }
}

Write-Host "`nDone: OK=$ok  FAIL=$fail"
if ($fail -gt 0) { exit 1 }
