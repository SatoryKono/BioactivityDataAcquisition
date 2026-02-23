# Export all root CA certs to PEM bundle for WSL
$certs = Get-ChildItem -Path Cert:\LocalMachine\Root
$certs += Get-ChildItem -Path Cert:\CurrentUser\Root

$pem = ""
foreach ($cert in $certs) {
    $base64 = [Convert]::ToBase64String($cert.RawData, 'InsertLineBreaks')
    $pem += "-----BEGIN CERTIFICATE-----`n$base64`n-----END CERTIFICATE-----`n"
}

$outPath = "E:\g-drive\05_AI\github\BioactivityDataAcquisition2\.ca-bundle.pem"
$pem | Out-File -FilePath $outPath -Encoding ascii -NoNewline
Write-Host "Exported $($certs.Count) certificates to $outPath"
