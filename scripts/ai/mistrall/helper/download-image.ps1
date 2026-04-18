#!/usr/bin/env pwsh
# Helper: Download Ollama image with retry logic and mirror support
# Called by: run-mistrall.ps1 setup

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

$Colors = @{ Success = "Green"; Warning = "Yellow"; Error = "Red"; Info = "Cyan" }

function Write-Success { Write-Host "[OK]" -ForegroundColor $Colors.Success -NoNewline; Write-Host " $args" }
function Write-Warn { Write-Host "[!]" -ForegroundColor $Colors.Warning -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "[X]" -ForegroundColor $Colors.Error -NoNewline; Write-Host " $args" }
function Write-Info { Write-Host "[i]" -ForegroundColor $Colors.Info -NoNewline; Write-Host " $args" }

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  Ollama Image - Download & Load" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if image already exists
Write-Info "Checking if ollama/ollama:latest exists..."
try {
    $imageExists = docker image inspect ollama/ollama:latest 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Image already loaded"
        docker images --filter "reference=ollama/ollama" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
        exit 0
    }
} catch {
    # Image doesn't exist, proceed with download
}

$imageFile = Join-Path $RootDir "ollama-image.tar.gz"

# Option 1: Load from pre-downloaded tar
if (Test-Path $imageFile) {
    Write-Info "Found pre-downloaded image: $imageFile"
    Write-Host ""
    
    Write-Info "Loading image (this may take 2-5 minutes)..."
    $fileSize = (Get-Item $imageFile).Length / 1GB
    Write-Info "Size: $([math]::Round($fileSize, 2)) GB"
    Write-Host ""
    
    try {
        Get-Content $imageFile -AsByteStream | docker load 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Image loaded successfully"
            docker images --filter "reference=ollama/ollama" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
            exit 0
        } else {
            Write-Error "Load failed"
            exit 1
        }
    } catch {
        Write-Error "Error loading image: $_"
        exit 1
    }
}

# Option 2: Pull from Docker Hub with retry
Write-Info "ollama-image.tar.gz not found"
Write-Info "Attempting to download from Docker Hub (retry with backoff)..."
Write-Host ""

$maxRetries = 5
$retryCount = 0
$success = $false

while ($retryCount -lt $maxRetries -and -not $success) {
    $retryCount++
    Write-Info "Attempt $retryCount/$maxRetries..."
    
    try {
        # Pull with progress
        docker pull ollama/ollama:latest 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Image pulled successfully"
            $success = $true
        } else {
            Write-Warn "Pull failed with exit code: $($LASTEXITCODE)"
            
            if ($retryCount -lt $maxRetries) {
                $backoff = [math]::Min([math]::Pow(2, $retryCount - 1) * 10, 60)
                Write-Info "Waiting $backoff seconds before retry..."
                Start-Sleep -Seconds $backoff
            }
        }
    } catch {
        Write-Warn "Error during pull: $_"
        
        if ($retryCount -lt $maxRetries) {
            $backoff = [math]::Min([math]::Pow(2, $retryCount - 1) * 10, 60)
            Write-Info "Waiting $backoff seconds before retry..."
            Start-Sleep -Seconds $backoff
        }
    }
}

if ($success) {
    Write-Success "Ollama image ready"
    docker images --filter "reference=ollama/ollama" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
    exit 0
} else {
    Write-Error "Failed to download image after $maxRetries attempts"
    Write-Info ""
    Write-Info "Alternative options:"
    Write-Info "  1. Download on a faster connection and use ollama-image.tar.gz"
    Write-Info "  2. Use a smaller model: edit .env.mistrall and set MISTRALL_MODEL=phi:latest"
    Write-Info "  3. Check your internet connection and try again"
    exit 1
}
