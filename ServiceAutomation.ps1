# Define the path for the SSH key
$sshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519"
$sshDir = "$env:USERPROFILE\.ssh"

# Check if the SSH key file already exists
if (-not (Test-Path $sshKeyPath)) {
    Write-Host "SSH key not found at $sshKeyPath. Generating a new key."

    # Ensure the .ssh directory exists
    if (-not (Test-Path $sshDir)) {
        New-Item -ItemType Directory -Path $sshDir
    }

    # Generate the new SSH key.
    ssh-keygen -t ed25519 -C '821311@gmail.com' -f $sshKeyPath -N ""
} else {
    Write-Host "SSH key already exists."
}

# Check for Administrator privileges
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Warning "================================================================"
    Write-Warning "ADMINISTRATOR PRIVILEGES REQUIRED"
    Write-Warning "This script needs to configure the 'ssh-agent' Windows Service."
    Write-Warning "Please restart your terminal/PowerShell as Administrator."
    Write-Warning "================================================================"
}

try {
    # Ensure the ssh-agent service is running
    Write-Host "Configuring ssh-agent service..."
    Get-Service ssh-agent | Set-Service -StartupType Automatic -ErrorAction Stop

    $service = Get-Service ssh-agent
    if ($service.Status -ne 'Running') {
        Start-Service ssh-agent -ErrorAction Stop
    }

    # Add the SSH key to the ssh-agent
    Write-Host "Adding key to ssh-agent..."
    ssh-add $sshKeyPath
}
catch {
    Write-Error "Failed to configure or start ssh-agent."
    Write-Error "Error details: $($_.Exception.Message)"
    if (-not $isAdmin) {
        Write-Host "Tip: This error is likely because you are not running as Administrator." -ForegroundColor Yellow
    }
}

Write-Host "`nSSH setup process finished."
Write-Host "Your Public Key (add this to GitHub):" -ForegroundColor Green
Get-Content "${sshKeyPath}.pub"
