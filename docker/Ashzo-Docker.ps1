# Ashzo MCP in Docker. The desktop icon runs this script.
#   -Setup : build the image and create the "Ashzo MCP (Docker)" desktop icon (CREATE_DOCKER_ICON.bat).
#   no flag: start the container (starting Docker Desktop if needed) and open the dashboard.
param([switch]$Setup)

$root = Split-Path -Parent $PSScriptRoot
$dashboard = 'http://localhost:8000/'
$health = 'http://127.0.0.1:8000/api/health'
$dockerDesktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'

function Show-Error([string]$message) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show($message, 'Ashzo MCP', 'OK', 'Error') | Out-Null
}

function Test-Docker {
    & docker info *> $null
    return ($LASTEXITCODE -eq 0)
}

function Ensure-Docker {
    if (Test-Docker) { return }
    if (-not (Test-Path $dockerDesktop)) {
        throw 'Docker Desktop is not installed. Install it from https://www.docker.com/products/docker-desktop/ and try again.'
    }
    Start-Process -FilePath $dockerDesktop | Out-Null
    $deadline = (Get-Date).AddSeconds(180)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        if (Test-Docker) { return }
    }
    throw 'Docker Desktop did not start in time. Wait until it says it is running, then try again.'
}

function Invoke-Compose([string[]]$arguments) {
    Push-Location $root
    try {
        & docker compose @arguments
        if ($LASTEXITCODE -ne 0) { throw "docker compose $($arguments -join ' ') failed (exit code $LASTEXITCODE)." }
    } finally {
        Pop-Location
    }
}

function Wait-Dashboard {
    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline) {
        try {
            $reply = Invoke-RestMethod -Uri $health -TimeoutSec 3
            if ($reply.app -eq 'ashzo-mcp') { return }
        } catch { }
        Start-Sleep -Seconds 2
    }
    throw 'The Ashzo MCP app did not answer. Open Docker Desktop, find the "ashzo-mcp" container and check its logs.'
}

function New-DesktopIcon {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $lnk = Join-Path $desktop 'Ashzo MCP (Docker).lnk'
    $shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
    $shortcut.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$PSCommandPath`""
    $shortcut.WorkingDirectory = $root
    $shortcut.IconLocation = Join-Path $root 'assets\ashzo.ico'
    $shortcut.Description = 'Start Ashzo MCP (Docker) and open the dashboard'
    $shortcut.Save()
    return $lnk
}

try {
    Ensure-Docker
    if ($Setup) {
        Write-Host 'Building the Ashzo MCP image (the first time takes a few minutes)...'
        Invoke-Compose @('build')
        $lnk = New-DesktopIcon
        Write-Host "Created the desktop icon: $lnk"
        exit 0
    }
    Invoke-Compose @('up', '-d', '--build')
    Wait-Dashboard
    Start-Process $dashboard
    exit 0
} catch {
    if ($Setup) {
        Write-Host ''
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
    Show-Error $_.Exception.Message
    exit 1
}
