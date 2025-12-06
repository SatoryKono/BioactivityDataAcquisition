Param(
    [string]$Root = "docs"
)

$ErrorActionPreference = "Stop"

function Render-MMD {
    param([string]$InPath)

    $base = [System.IO.Path]::GetFileNameWithoutExtension($InPath)
    $dir = [System.IO.Path]::GetDirectoryName($InPath)
    $out = Join-Path $dir "$base.png"

    $content = Get-Content -LiteralPath $InPath -Raw
    if ($content -match '^\s*---\s*') {
        $content = [regex]::Replace($content, '(?s)^---.*?---\s*', '', 1)
    }

    $tmp = [System.IO.Path]::GetTempFileName()
    Set-Content -LiteralPath $tmp -Value $content -Encoding utf8

    & npx -y @mermaid-js/mermaid-cli@10.9.1 --input $tmp --output $out --backgroundColor white --scale 1
    if ($LASTEXITCODE -ne 0) {
        throw "mermaid-cli failed for $InPath (exit $LASTEXITCODE)"
    }

    Remove-Item -LiteralPath $tmp -Force
}

Get-ChildItem -Path $Root -Recurse -Filter *.mmd | ForEach-Object { Render-MMD $_.FullName }

