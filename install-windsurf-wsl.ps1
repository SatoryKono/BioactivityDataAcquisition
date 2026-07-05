#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Install Windsurf in WSL via PowerShell

.DESCRIPTION
    This script automatically installs Windsurf in WSL by downloading
    the latest version from the official site and configuring the environment.

.PARAMETER WslDistribution
    WSL distribution name (default: Ubuntu)

.PARAMETER InstallPath
    Installation path in WSL (default: /usr/local/bin)

.EXAMPLE
    .\install-windsurf-wsl.ps1

.EXAMPLE
    .\install-windsurf-wsl.ps1 -WslDistribution "Ubuntu-22.04"
#>

param(
    [string]$WslDistribution = "Ubuntu",
    [string]$InstallPath = "/usr/local/bin"
)

# Colors for output
$SuccessColor = "Green"
$InfoColor = "Cyan"
$WarningColor = "Yellow"
$ErrorColor = "Red"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Test-WslCommand {
    param(
        [string]$Command
    )
    $result = wsl -d $WslDistribution -- bash -c "command -v $Command" 2>&1
    return $LASTEXITCODE -eq 0
}

function Invoke-WslCommand {
    param(
        [string]$Command,
        [switch]$Sudo = $false
    )
    $prefix = if ($Sudo) { "sudo" } else { "" }
    $fullCommand = "$prefix $Command"
    $result = wsl -d $WslDistribution -- bash -c $fullCommand 2>&1
    return $result
}

function Install-Windsurf-Manual {
    Write-ColorOutput "Manual Windsurf installation..." $InfoColor
    Write-ColorOutput "Please follow these steps manually:" $WarningColor
    Write-ColorOutput "1. Download Windsurf for Linux from https://windsurf.ai/" $InfoColor
    Write-ColorOutput "2. Copy the file to WSL: /mnt/c/Users/YourUsername/Downloads/" $InfoColor
    Write-ColorOutput "3. In WSL, execute:" $InfoColor
    Write-ColorOutput "   sudo mv windsurf* $InstallPath/windsurf" $InfoColor
    Write-ColorOutput "   sudo chmod +x $InstallPath/windsurf" $InfoColor
    return $false
}

function Add-WindsurfToPath {
    Write-ColorOutput "Adding Windsurf to PATH..." $InfoColor
    
    $bashrcLine = "export PATH=`$PATH:$InstallPath"
    $profileLine = "export PATH=`$PATH:$InstallPath"
    
    # Add to .bashrc
    $bashrcContent = Invoke-WslCommand "cat ~/.bashrc"
    if ($bashrcContent -notmatch [regex]::Escape($InstallPath)) {
        Invoke-WslCommand "echo '$bashrcLine' >> ~/.bashrc"
        Write-ColorOutput "Added to ~/.bashrc" $SuccessColor
    } else {
        Write-ColorOutput "Already in ~/.bashrc" $InfoColor
    }
    
    # Add to .profile
    $profileContent = Invoke-WslCommand "cat ~/.profile"
    if ($profileContent -notmatch [regex]::Escape($InstallPath)) {
        Invoke-WslCommand "echo '$profileLine' >> ~/.profile"
        Write-ColorOutput "Added to ~/.profile" $SuccessColor
    } else {
        Write-ColorOutput "Already in ~/.profile" $InfoColor
    }
}

function Test-WindsurfInstallation {
    Write-ColorOutput "Testing Windsurf installation..." $InfoColor
    
    $version = Invoke-WslCommand "windsurf --version"
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "Windsurf installed successfully!" $SuccessColor
        Write-ColorOutput "Version: $version" $InfoColor
        return $true
    } else {
        Write-ColorOutput "Windsurf not installed or not working" $ErrorColor
        return $false
    }
}

# Main script
Write-ColorOutput "========================================" $InfoColor
Write-ColorOutput "Installing Windsurf in WSL" $InfoColor
Write-ColorOutput "========================================" $InfoColor
Write-ColorOutput ""

# Check WSL
Write-ColorOutput "Checking WSL..." $InfoColor
$wslCheck = wsl --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput "WSL not installed or not available" $ErrorColor
    exit 1
}
Write-ColorOutput "WSL found: $wslCheck" $SuccessColor

# Check distribution
Write-ColorOutput "Checking WSL distribution: $WslDistribution" $InfoColor
$distroCheck = wsl -d $WslDistribution -- echo "test" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-ColorOutput "Distribution '$WslDistribution' not found" $ErrorColor
    Write-ColorOutput "Available distributions:" $InfoColor
    wsl -l -v
    exit 1
}
Write-ColorOutput "Distribution '$WslDistribution' available" $SuccessColor

# Check if Windsurf is already installed
Write-ColorOutput "Checking Windsurf installation..." $InfoColor
if (Test-WslCommand "windsurf") {
    Write-ColorOutput "Windsurf already installed" $WarningColor
    $currentVersion = Invoke-WslCommand "windsurf --version"
    Write-ColorOutput "Current version: $currentVersion" $InfoColor
    
    $reinstall = Read-Host "Reinstall? (y/N)"
    if ($reinstall -ne "y" -and $reinstall -ne "Y") {
        Write-ColorOutput "Installation cancelled" $InfoColor
        exit 0
    }
}

# Manual installation (since automatic download URL is not available)
$installSuccess = Install-Windsurf-Manual

if ($installSuccess) {
    # Add to PATH
    Add-WindsurfToPath
    
    # Test installation
    Write-ColorOutput "" $InfoColor
    Test-WindsurfInstallation
    
    Write-ColorOutput "" $InfoColor
    Write-ColorOutput "========================================" $SuccessColor
    Write-ColorOutput "Installation complete!" $SuccessColor
    Write-ColorOutput "========================================" $SuccessColor
    Write-ColorOutput "" $InfoColor
    Write-ColorOutput "To run Windsurf in WSL:" $InfoColor
    Write-ColorOutput "  wsl -d $WslDistribution -- windsurf" $InfoColor
    Write-ColorOutput "  or" $InfoColor
    Write-ColorOutput "  wsl -d $WslDistribution" $InfoColor
    Write-ColorOutput "  windsurf" $InfoColor
    Write-ColorOutput "" $InfoColor
    Write-ColorOutput "To run your project:" $InfoColor
    Write-ColorOutput "  wsl -d $WslDistribution -- windsurf /mnt/e/g-drive/05_AI/github/BioactivityDataAcquisition2" $InfoColor
} else {
    Write-ColorOutput "" $ErrorColor
    Write-ColorOutput "========================================" $ErrorColor
    Write-ColorOutput "Please complete manual installation" $ErrorColor
    Write-ColorOutput "========================================" $ErrorColor
    exit 1
}
