#Requires -Version 5.1
# CodeRabbit CLI Installation Script for Windows (x64).
#
# This is the Windows counterpart of install.sh and mirrors its flow:
# resolve version, download the immutable versioned archive, install the
# binary and the cr alias, update PATH, verify, then offer sign-in.
#
# USAGE:
#   # Install latest version
#   powershell -ExecutionPolicy Bypass -c "irm https://cli.coderabbit.ai/install.ps1 | iex"
#
#   # Install specific version
#   $env:CODERABBIT_VERSION = "v1.2.3"; irm https://cli.coderabbit.ai/install.ps1 | iex
#
# ENVIRONMENT VARIABLES:
#   CODERABBIT_VERSION      - Override version to install (e.g. "v1.2.3")
#   CODERABBIT_DOWNLOAD_URL - Override base download URL (default: https://cli.coderabbit.ai/releases)
#   CODERABBIT_API_KEY      - Skip browser login prompt for API-key based setups
#   CI                      - When set, skip the interactive post-install login prompt
#
# INSTALLATION LOCATION:
#   - Binary: %LOCALAPPDATA%\Programs\coderabbit\coderabbit.exe
#   - Alias:  %LOCALAPPDATA%\Programs\coderabbit\cr.exe
#   - Adds the install directory to the user PATH if needed
#
# Stable Windows binaries are Authenticode-signed; this installer requires the
# approved signer identity and Code Signing EKU before installing.

$PreviousErrorActionPreference = $ErrorActionPreference
$PreviousProgressPreference = $ProgressPreference
$PreviousSecurityProtocol = [Net.ServicePointManager]::SecurityProtocol
$RequestTimeoutSeconds = 300
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$ExpectedSignerSubjectBase64 = "Q049Q29kZVJhYmJpdCBJbmMuLCBPPUNvZGVSYWJiaXQgSW5jLiwgTD1TYW4gRnJhbmNpc2NvLCBTPUNhbGlmb3JuaWEsIEM9VVM="
$ExpectedSignerIssuerBase64 = "Q049TWljcm9zb2Z0IElEIFZlcmlmaWVkIENTIEVPQyBDQSAwMywgTz1NaWNyb3NvZnQgQ29ycG9yYXRpb24sIEM9VVM="
# Stable resolves latest; the nightly workflow replaces this with one exact version.
$BundledVersion = "0.8.2"
$TempDir = Join-Path (
    [System.IO.Path]::GetTempPath()
) ("coderabbit-install-" + [System.Guid]::NewGuid().ToString("N"))

function Test-FileSystemEntry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LiteralPath
    )

    $Parent = Split-Path -Parent $LiteralPath
    $Leaf = Split-Path -Leaf $LiteralPath
    $Entry = Get-ChildItem `
        -LiteralPath $Parent `
        -Force `
        -ErrorAction SilentlyContinue |
        Where-Object {
            [string]::Equals(
                $_.Name,
                $Leaf,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        } |
        Select-Object -First 1
    return $null -ne $Entry
}

try {
    [Net.ServicePointManager]::SecurityProtocol = (
        $PreviousSecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    )

    # --- Platform check -------------------------------------------------------
    # PROCESSOR_ARCHITECTURE reflects the *process*; a 32-bit PowerShell host on
    # a 64-bit OS reports x86. PROCESSOR_ARCHITEW6432 holds the OS architecture.
    $OsArch = $env:PROCESSOR_ARCHITEW6432
    if (-not $OsArch) {
        $OsArch = $env:PROCESSOR_ARCHITECTURE
    }
    if ($OsArch -eq "ARM64") {
        Write-Host "[INFO] ARM64 Windows detected. Installing the x64 build (runs under emulation)."
    } elseif ($OsArch -ne "AMD64") {
        Write-Error "Unsupported architecture: $OsArch (only x64/AMD64 is supported)"
    }

    # Git is required for repository discovery and reviews. Fail before
    # downloading anything so a fresh machine gets one actionable prerequisite.
    if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) {
        Write-Error (
            "Git for Windows is required. Install it from " +
            "https://git-scm.com/download/win, then run this command again."
        )
    }

    # --- Version resolution (parity with install.sh) --------------------------
    $BaseUrl = if ($env:CODERABBIT_DOWNLOAD_URL) {
        $env:CODERABBIT_DOWNLOAD_URL.TrimEnd("/")
    } else {
        "https://cli.coderabbit.ai/releases"
    }

    if ($env:CODERABBIT_VERSION) {
        # Accept both "1.2.3" and "v1.2.3"; published paths are unprefixed.
        $Version = $env:CODERABBIT_VERSION
        if ($Version.StartsWith("v")) {
            $Version = $Version.Substring(1)
        }
        Write-Host "[INFO] Version: $Version (from CODERABBIT_VERSION)"
    } elseif ($BundledVersion) {
        # Nightly bootstraps pin an immutable signed version so later unsigned
        # Unix nightlies cannot move the Windows installer to missing bytes.
        $Version = $BundledVersion
        Write-Host "[INFO] Version: $Version (from installer)"
    } else {
        # Resolve latest once, then download immutable versioned bytes.
        try {
            $VersionContent = (
                Invoke-WebRequest `
                    -Uri "$BaseUrl/latest/VERSION" `
                    -UseBasicParsing `
                    -TimeoutSec $RequestTimeoutSeconds
            ).Content
            # VERSION may be served as application/octet-stream, in which
            # case Invoke-WebRequest returns bytes rather than a string.
            if ($VersionContent -is [byte[]]) {
                $VersionContent = [System.Text.Encoding]::UTF8.GetString(
                    $VersionContent
                )
            }
            $Version = ([string]$VersionContent).Trim()
        } catch {
            Write-Error "Failed to fetch version information ($_)"
        }
        if ($Version.StartsWith("v")) {
            $Version = $Version.Substring(1)
        }
        Write-Host "[INFO] Version: $Version"
    }
    if ($Version -notmatch "^[0-9A-Za-z][0-9A-Za-z.-]*$") {
        Write-Error "CodeRabbit release version is invalid: $Version"
    }

    # --- Download and extract -------------------------------------------------
    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
    $ZipPath = Join-Path $TempDir "coderabbit-windows-x64.zip"

    Write-Host "[INFO] Downloading CodeRabbit CLI..."
    try {
        Invoke-WebRequest `
            -Uri "$BaseUrl/$Version/coderabbit-windows-x64.zip" `
            -OutFile $ZipPath `
            -UseBasicParsing `
            -TimeoutSec $RequestTimeoutSeconds
    } catch {
        if ($env:CODERABBIT_VERSION) {
            Write-Error "Release $Version could not be downloaded - check CODERABBIT_VERSION and try again ($_)"
        } else {
            Write-Error "Failed to download CodeRabbit CLI $Version ($_)"
        }
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $Archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        $Entries = @($Archive.Entries)
        if (
            $Entries.Count -ne 1 -or
            $Entries[0].FullName -cne "coderabbit.exe"
        ) {
            Write-Error (
                "Downloaded archive must contain exactly one top-level " +
                "coderabbit.exe"
            )
        }

        $Candidate = Join-Path $TempDir "coderabbit.exe"
        $InputStream = $null
        $OutputStream = $null
        try {
            $InputStream = $Entries[0].Open()
            $OutputStream = [System.IO.File]::Create($Candidate)
            $InputStream.CopyTo($OutputStream)
        } finally {
            if ($null -ne $OutputStream) {
                $OutputStream.Dispose()
            }
            if ($null -ne $InputStream) {
                $InputStream.Dispose()
            }
        }
    } finally {
        $Archive.Dispose()
    }

    # --- Authenticity check ---------------------------------------------------
    # Authenticode covers both integrity and publisher identity, the same role
    # codesign/notarization plays for the macOS binaries.
    if (
        $ExpectedSignerSubjectBase64.StartsWith("__") -or
        $ExpectedSignerIssuerBase64.StartsWith("__")
    ) {
        Write-Error "Windows signer identity is not configured in this installer"
    }
    try {
        $ExpectedSignerSubject = [System.Text.Encoding]::UTF8.GetString(
            [System.Convert]::FromBase64String($ExpectedSignerSubjectBase64)
        )
        $ExpectedSignerIssuer = [System.Text.Encoding]::UTF8.GetString(
            [System.Convert]::FromBase64String($ExpectedSignerIssuerBase64)
        )
    } catch {
        Write-Error "Windows signer identity in this installer is invalid"
    }
    if (
        [string]::IsNullOrWhiteSpace($ExpectedSignerSubject) -or
        [string]::IsNullOrWhiteSpace($ExpectedSignerIssuer)
    ) {
        Write-Error "Windows signer identity in this installer is empty"
    }

    $Signature = Get-AuthenticodeSignature -FilePath $Candidate
    if ($Signature.Status -ne "Valid" -or -not $Signature.SignerCertificate) {
        Write-Error (
            "coderabbit.exe does not carry a valid Authenticode signature " +
            "(status: $($Signature.Status))"
        )
    }
    if (-not [string]::Equals(
        $Signature.SignerCertificate.Subject,
        $ExpectedSignerSubject,
        [System.StringComparison]::Ordinal
    )) {
        Write-Error (
            "coderabbit.exe is signed by an unexpected publisher: " +
            $Signature.SignerCertificate.Subject
        )
    }
    if (-not [string]::Equals(
        $Signature.SignerCertificate.Issuer,
        $ExpectedSignerIssuer,
        [System.StringComparison]::Ordinal
    )) {
        Write-Error (
            "coderabbit.exe is signed by an unexpected issuer: " +
            $Signature.SignerCertificate.Issuer
        )
    }
    $CodeSigningEkuOid = "1.3.6.1.5.5.7.3.3"
    $EkuExtension = $Signature.SignerCertificate.Extensions |
        Where-Object { $_.Oid.Value -eq "2.5.29.37" } |
        Select-Object -First 1
    $HasCodeSigningEku = (
        $null -ne $EkuExtension -and
        @(
            $EkuExtension.EnhancedKeyUsages |
                Where-Object { $_.Value -eq $CodeSigningEkuOid }
        ).Count -gt 0
    )
    if (-not $HasCodeSigningEku) {
        Write-Error "coderabbit.exe signer certificate lacks the Code Signing EKU"
    }

    # --- Install both commands ------------------------------------------------
    $InstallDir = Join-Path $env:LOCALAPPDATA "Programs\coderabbit"
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    $Binary = Join-Path $InstallDir "coderabbit.exe"
    $Alias = Join-Path $InstallDir "cr.exe"
    $InstallOperation = if (
        (Test-FileSystemEntry -LiteralPath $Binary) -or
        (Test-FileSystemEntry -LiteralPath $Alias)
    ) {
        "replace_existing"
    } else {
        "fresh_install"
    }

    Write-Host "[INFO] Installing to $InstallDir"

    # Stage and smoke both command names before changing the live pair. Keep
    # backups until the installed pair has also passed verification so any
    # copy, rename, or launch failure can restore the previous installation.
    $StageDir = Join-Path (
        Split-Path -Parent $InstallDir
    ) ("coderabbit-stage-" + [System.Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $StageDir -Force | Out-Null
    $StagedBinary = Join-Path $StageDir "coderabbit.exe"
    $StagedAlias = Join-Path $StageDir "cr.exe"
    $ExpectedBinaryHash = (Get-FileHash -LiteralPath $Candidate -Algorithm SHA256).Hash
    try {
        Copy-Item -LiteralPath $Candidate -Destination $StagedBinary
        Copy-Item -LiteralPath $Candidate -Destination $StagedAlias
        foreach ($StagedCommand in @($StagedBinary, $StagedAlias)) {
            $StagedHash = (
                Get-FileHash -LiteralPath $StagedCommand -Algorithm SHA256
            ).Hash
            if ($StagedHash -cne $ExpectedBinaryHash) {
                throw "Staged CodeRabbit CLI failed integrity verification"
            }
            $StagedVersion = (& $StagedCommand --version | Out-String).Trim()
            if (
                $LASTEXITCODE -ne 0 -or
                -not [string]::Equals(
                    $StagedVersion,
                    $Version,
                    [System.StringComparison]::Ordinal
                )
            ) {
                throw "Staged CodeRabbit CLI failed version verification"
            }
        }

        $InstallPairs = @(
            @{ Source = $StagedBinary; Destination = $Binary },
            @{ Source = $StagedAlias; Destination = $Alias }
        )
        $BackupPaths = @{}
        $InstalledDestinations = @()
        try {
            foreach ($Pair in $InstallPairs) {
                $Destination = $Pair.Destination
                if (Test-FileSystemEntry -LiteralPath $Destination) {
                    $BackupPath = "$Destination." +
                        [System.Guid]::NewGuid().ToString("N") + ".old"
                    Move-Item `
                        -LiteralPath $Destination `
                        -Destination $BackupPath `
                        -Force
                    $BackupPaths[$Destination] = $BackupPath
                }
                Move-Item `
                    -LiteralPath $Pair.Source `
                    -Destination $Destination `
                    -Force
                $InstalledDestinations += $Destination
            }

            foreach ($InstalledCommand in @($Binary, $Alias)) {
                $InstalledHash = (
                    Get-FileHash -LiteralPath $InstalledCommand -Algorithm SHA256
                ).Hash
                if ($InstalledHash -cne $ExpectedBinaryHash) {
                    throw "Installed CodeRabbit CLI failed integrity verification"
                }
                $ReportedVersion = (
                    & $InstalledCommand --version | Out-String
                ).Trim()
                if (
                    $LASTEXITCODE -ne 0 -or
                    -not [string]::Equals(
                        $ReportedVersion,
                        $Version,
                        [System.StringComparison]::Ordinal
                    )
                ) {
                    throw (
                        "Installed CodeRabbit version mismatch: " +
                        "'$ReportedVersion' != '$Version'"
                    )
                }
            }
        } catch {
            $InstallError = $_
            $RollbackErrors = @()
            foreach ($Destination in $InstalledDestinations) {
                try {
                    Remove-Item -LiteralPath $Destination -Force
                } catch {
                    $RollbackErrors += $_.Exception.Message
                }
            }
            foreach ($Destination in $BackupPaths.Keys) {
                try {
                    Move-Item `
                        -LiteralPath $BackupPaths[$Destination] `
                        -Destination $Destination `
                        -Force
                } catch {
                    $RollbackErrors += $_.Exception.Message
                }
            }
            if ($RollbackErrors.Count -gt 0) {
                throw (
                    "Installation failed and rollback was incomplete: " +
                    ($RollbackErrors -join "; ")
                )
            }
            throw $InstallError
        }

        foreach ($BackupPath in $BackupPaths.Values) {
            Remove-Item `
                -LiteralPath $BackupPath `
                -Force `
                -ErrorAction SilentlyContinue
        }
    } finally {
        Remove-Item $StageDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    # --- PATH update (user PATH, parity with install.sh shell profiles) -------
    # Append via the registry so the existing value is left untouched:
    # [Environment]::SetEnvironmentVariable would expand %VAR% references and
    # flatten REG_EXPAND_SZ to REG_SZ.
    $NormalizedInstallDir = $InstallDir.TrimEnd([char[]]"\/")
    $PathUpdated = $false
    $RegKey = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey(
        "Environment", $true
    )
    try {
        $RawUserPath = ""
        $UserPathKind = [Microsoft.Win32.RegistryValueKind]::ExpandString
        if (@($RegKey.GetValueNames()) -contains "Path") {
            $RawUserPath = [string]$RegKey.GetValue(
                "Path",
                "",
                [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames
            )
            $UserPathKind = $RegKey.GetValueKind("Path")
        }
        $UserPathContainsInstallDir = @(
            $RawUserPath -split ";" |
                ForEach-Object {
                    [Environment]::ExpandEnvironmentVariables(
                        $_.Trim().Trim('"')
                    ).TrimEnd([char[]]"\/")
                } |
                Where-Object { $_ -eq $NormalizedInstallDir }
        ).Count -gt 0
        if (-not $UserPathContainsInstallDir) {
            Write-Host "[INFO] Adding $InstallDir to your user PATH..."
            $NewUserPath = if ($RawUserPath.Trim() -eq "") {
                $InstallDir
            } else {
                $RawUserPath.TrimEnd(";") + ";" + $InstallDir
            }
            $RegKey.SetValue("Path", $NewUserPath, $UserPathKind)
            $PathUpdated = $true
        }
    } finally {
        $RegKey.Close()
    }

    # Make both commands available in this session immediately.
    $ProcessPathEntries = @(
        $env:Path -split ";" |
            ForEach-Object { $_.Trim() } |
            Where-Object {
                $_ -ne "" -and
                -not $_.TrimEnd([char[]]"\/").Equals(
                    $NormalizedInstallDir,
                    [System.StringComparison]::OrdinalIgnoreCase
                )
            }
    )
    $env:Path = (@($InstallDir) + $ProcessPathEntries) -join ";"

    # Windows PowerShell 5.1 turns redirected native stderr into a
    # terminating error under ErrorActionPreference=Stop, so relax it for
    # this soft check.
    $PreviousDoctorSource = $env:CR_CLI_DOCTOR_SOURCE
    $PreviousInstallOperation = $env:CR_CLI_INSTALL_OPERATION
    if ($PreviousDoctorSource -ceq "auto_update") {
        $env:CR_CLI_DOCTOR_SOURCE = "auto_update"
        $env:CR_CLI_INSTALL_OPERATION = "self_update"
    } else {
        $env:CR_CLI_DOCTOR_SOURCE = "install_ps1"
        $env:CR_CLI_INSTALL_OPERATION = $InstallOperation
    }
    $ErrorActionPreference = "Continue"
    $DoctorExitCode = 1
    try {
        & $Binary doctor > $null 2> $null
        $DoctorExitCode = $LASTEXITCODE
    } catch {
        $DoctorExitCode = 1
    } finally {
        $ErrorActionPreference = "Stop"
        $env:CR_CLI_DOCTOR_SOURCE = $PreviousDoctorSource
        $env:CR_CLI_INSTALL_OPERATION = $PreviousInstallOperation
    }
    if ($DoctorExitCode -eq 0) {
        Write-Host "[SUCCESS] Installation verified"
    } else {
        Write-Host "[WARNING] CLI install could not be verified with 'coderabbit doctor'"
    }

    Write-Host "[SUCCESS] Installation complete"
    Write-Host "  coderabbit -> $Binary"
    Write-Host "  cr         -> $Alias"

    # --- Post-install login (parity with install.sh) ---------------------------
    $LoginStatus = "skipped"
    $CanPromptForLogin = (
        -not $env:CODERABBIT_API_KEY -and
        -not $env:CI -and
        [Environment]::UserInteractive -and
        -not [Console]::IsInputRedirected
    )
    if ($CanPromptForLogin) {
        Write-Host ""
        Write-Host "[AUTH] Sign in to CodeRabbit"
        Write-Host "[AUTH] Connect your account now so the CLI is ready for reviews."
        Write-Host "[AUTH] You can skip this and run 'coderabbit auth login' later."
        $LoginAnswer = ""
        try {
            $LoginAnswer = Read-Host "[AUTH] Start browser sign-in now? [Y/n]"
        } catch {
            $LoginAnswer = "n"
        }
        if ($LoginAnswer.Trim() -match "^(|y|yes)$") {
            try {
                & $Binary auth login
                if ($LASTEXITCODE -eq 0) {
                    $LoginStatus = "success"
                } else {
                    $LoginStatus = "failed"
                    Write-Host "[WARNING] Login did not complete. Run 'coderabbit auth login' when ready."
                }
            } catch {
                $LoginStatus = "failed"
                Write-Host "[WARNING] Login did not complete. Run 'coderabbit auth login' when ready."
            }
        } else {
            Write-Host "[INFO] Skipping sign-in. Run 'coderabbit auth login' when ready."
        }
    }

    # --- Next steps (parity with install.sh) -----------------------------------
    Write-Host ""
    Write-Host "Next steps"
    $Step = 1
    if ($PathUpdated) {
        Write-Host "  $Step. Restart your terminal so the PATH change takes effect"
        $Step++
    }
    if ($LoginStatus -ne "success" -and -not $env:CODERABBIT_API_KEY) {
        Write-Host "  $Step. Run 'coderabbit auth login' to authenticate"
        $Step++
    }
    Write-Host "  $Step. Run 'coderabbit review' from a git repository"
    Write-Host ""
    Write-Host "Try these commands:"
    Write-Host "  coderabbit --help          # Show modes and commands"
    Write-Host "  coderabbit review          # Review local changes"
    Write-Host "  coderabbit review --agent  # Emit structured findings for agents"
    Write-Host "  coderabbit stats           # Show review statistics"
    Write-Host ""
    Write-Host "Tip: Use 'cr' as a short alias for 'coderabbit'"
    Write-Host "To update: re-run this installer."
    Write-Host "To uninstall: delete $InstallDir and remove it from your PATH."
} finally {
    Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    [Net.ServicePointManager]::SecurityProtocol = $PreviousSecurityProtocol
    $ErrorActionPreference = $PreviousErrorActionPreference
    $ProgressPreference = $PreviousProgressPreference
}
