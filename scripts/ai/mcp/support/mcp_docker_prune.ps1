# Shared helper: drop exited/orphan containers for a given MCP image before
# starting a new stdio session. Does not stop running containers (other clients
# may still own them). Never touches bioetl-*.
function Remove-McpExitedContainers {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ImageMatch
    )
    $ErrorActionPreference = 'SilentlyContinue'
    $dryRun = $env:BIOETL_MCP_PRUNE_DRY_RUN -eq '1'
    $rows = docker ps -aq --filter 'status=exited' 2>$null
    if (-not $rows) { return }
    foreach ($id in $rows) {
        $meta = docker inspect --format '{{.Name}}|{{.Config.Image}}' $id 2>$null
        if (-not $meta) { continue }
        $parts = $meta -split '\|', 2
        $name = ([string]$parts[0]).TrimStart('/')
        $image = [string]$parts[1]
        if ($name -eq 'bioetl' -or $name -eq 'bioetl-neo4j' -or $name.StartsWith('bioetl-')) { continue }
        if ($image -notlike "*$ImageMatch*") { continue }
        if ($dryRun) {
            Write-Error "dry-run: would docker rm -f $id name=$name image=$image"
            continue
        }
        docker rm -f $id 2>$null | Out-Null
    }
}
