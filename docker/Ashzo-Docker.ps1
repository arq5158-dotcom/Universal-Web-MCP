# Ashzo MCP in Docker. The desktop icon runs this script.
#   -Setup : build the image, create the "Ashzo MCP (Docker)" desktop icon, and register Ashzo
#            with Claude Desktop and Claude Code (CREATE_DOCKER_ICON.bat).
#   no flag: start the container (starting Docker Desktop if needed) and open the dashboard.
param([switch]$Setup)

$root = Split-Path -Parent $PSScriptRoot
$dashboard = 'http://localhost:8000/'
$health = 'http://127.0.0.1:8000/api/health'
$dockerDesktop = Join-Path $env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
$dockerArgs = @('exec', '-i', '-e', 'ASHZO_DASHBOARD_URL=http://127.0.0.1:8000', 'ashzo-mcp', 'python', 'server.py')

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

# Adds (or replaces) the "ashzo-mcp" entry in one claude_desktop_config.json, keeping everything else.
# The original file is copied to <file>.bak once, before the first change.
function Set-ClaudeConfig([string]$file) {
    $config = [pscustomobject]@{}
    if (Test-Path $file) {
        $raw = Get-Content $file -Raw
        if ($raw.Trim()) {
            try { $config = $raw | ConvertFrom-Json }
            catch { throw "$file is not valid JSON, so it was left alone. Fix or remove it, then run setup again." }
        }
        if (-not (Test-Path "$file.bak")) { Copy-Item $file "$file.bak" }
    }
    if (-not $config.PSObject.Properties['mcpServers']) {
        $config | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{})
    }
    $entry = [pscustomobject]@{ command = 'docker'; args = $dockerArgs }
    $config.mcpServers | Add-Member -NotePropertyName 'ashzo-mcp' -NotePropertyValue $entry -Force
    $json = $config | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($file, $json, (New-Object System.Text.UTF8Encoding $false))
}

# Claude Desktop: update every config it can read (the normal install and the Microsoft Store install).
function Register-ClaudeDesktop {
    $files = @()
    $normal = Join-Path $env:APPDATA 'Claude'
    if (Test-Path $normal) { $files += Join-Path $normal 'claude_desktop_config.json' }
    $packages = Join-Path $env:LOCALAPPDATA 'Packages'
    foreach ($pkg in (Get-ChildItem $packages -Directory -Filter 'Claude_*' -ErrorAction SilentlyContinue)) {
        $files += Join-Path $pkg.FullName 'LocalCache\Roaming\Claude\claude_desktop_config.json'
    }
    if ($files.Count -eq 0) { return 'Claude Desktop: not installed, skipped.' }
    foreach ($file in $files) {
        if (Split-Path $file -Parent | Test-Path) {
            Set-ClaudeConfig $file
        }
    }
    return 'Claude Desktop: registered. Quit Claude completely (tray icon, Quit) and open it again.'
}

# Claude Code: a user-level MCP server, so it works in every folder.
function Register-ClaudeCode {
    if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
        return 'Claude Code: not installed, skipped.'
    }
    & claude mcp remove ashzo-mcp -s user *> $null
    & claude mcp add -s user ashzo-mcp -- docker @dockerArgs *> $null
    if ($LASTEXITCODE -ne 0) { return 'Claude Code: could not register. Run it yourself: claude mcp add -s user ashzo-mcp -- docker exec -i ashzo-mcp python server.py' }
    return 'Claude Code: registered. Start a new Claude Code session to use it.'
}

try {
    Ensure-Docker
    if ($Setup) {
        Write-Host 'Building the Ashzo MCP image (the first time takes a few minutes)...'
        Invoke-Compose @('build')
        $lnk = New-DesktopIcon
        Write-Host "Created the desktop icon: $lnk"
        Write-Host (Register-ClaudeDesktop)
        Write-Host (Register-ClaudeCode)
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
