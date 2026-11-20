<#
.SYNOPSIS
    Install or auto-update RRRemote on Windows and configure self-hosted server settings.
.EXAMPLE
    .\scripts\install-windows.ps1 -Server "203.0.113.10" -Key "<PUBKEY>" -ApiServer "http://203.0.113.10:21114" -RegisterAutoUpdate
#>
param(
    [string]$Repo = "melotusme/RRRemote",
    [string]$FallbackRepo = "",
    [string]$Server = "",
    [string]$Relay = "",
    [string]$Key = "",
    [string]$ApiServer = "",
    [string]$Proxy = "",
    [switch]$RegisterAutoUpdate,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"

$StateDir = Join-Path $env:LOCALAPPDATA "RRRemote"
$VersionFile = Join-Path $StateDir "installed_tag.txt"
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

function Get-LatestRelease {
    param([string]$TargetRepo)
    $headers = @{
        "User-Agent" = "RRRemote-Installer"
        "Accept"     = "application/vnd.github+json"
    }
    $params = @{
        Uri             = "https://api.github.com/repos/$TargetRepo/releases/latest"
        Headers         = $headers
        UseBasicParsing = $true
    }
    if ($Proxy) { $params["Proxy"] = $Proxy }
    try {
        return Invoke-RestMethod @params
    } catch {
        # Fallback to zero-rate-limit GitHub web redirect + expanded_assets HTML
        Write-Warning "GitHub API unavailable or rate-limited; falling back to web release redirect..."
        $webParams = @{
            Uri             = "https://github.com/$TargetRepo/releases/latest"
            Headers         = @{ "User-Agent" = "RRRemote-Installer" }
            UseBasicParsing = $true
        }
        if ($Proxy) { $webParams["Proxy"] = $Proxy }
        $resp = Invoke-WebRequest @webParams
        $finalUri = if ($resp.BaseResponse.ResponseUri) { $resp.BaseResponse.ResponseUri.AbsoluteUri } else { "" }
        if ($finalUri -match "/releases/tag/([^/?#]+)") {
            $tagName = $Matches[1]
        } else {
            throw "Could not resolve latest release tag from $finalUri"
        }
        $assetsParams = @{
            Uri             = "https://github.com/$TargetRepo/releases/expanded_assets/$tagName"
            Headers         = @{ "User-Agent" = "RRRemote-Installer" }
            UseBasicParsing = $true
        }
        if ($Proxy) { $assetsParams["Proxy"] = $Proxy }
        $html = (Invoke-WebRequest @assetsParams).Content
        $matches = [regex]::Matches($html, 'href="(/[^"]+/releases/download/[^"]+)"')
        $assets = @()
        $seen = @{}
        foreach ($m in $matches) {
            $relUrl = $m.Groups[1].Value
            if (-not $seen.ContainsKey($relUrl)) {
                $seen[$relUrl] = $true
                $fname = Split-Path -Leaf $relUrl
                $assets += [pscustomobject]@{
                    name                 = $fname
                    browser_download_url = "https://github.com$relUrl"
                }
            }
        }
        return [pscustomobject]@{
            tag_name = $tagName
            assets   = $assets
        }
    }
}

$release = $null
$usedRepo = $Repo
try {
    $release = Get-LatestRelease -TargetRepo $Repo
} catch {
    if ($FallbackRepo) {
        Write-Warning "No release found in $Repo yet, falling back to $FallbackRepo..."
        $release = Get-LatestRelease -TargetRepo $FallbackRepo
        $usedRepo = $FallbackRepo
    } else {
        throw
    }
}

$tag = "$usedRepo@$($release.tag_name)"
$currentTag = if (Test-Path $VersionFile) { (Get-Content $VersionFile -Raw).Trim() } else { "" }

if ($CheckOnly) {
    Write-Host "Current: $currentTag | Latest: $tag"
    exit 0
}

if ($currentTag -ne $tag) {
    $asset = $release.assets | Where-Object {
        $_.name -match "(x86_64|x64).*\.(exe|msi)$" -and $_.name -notmatch "sciter|arm64"
    } | Select-Object -First 1

    if (-not $asset) {
        throw "No Windows x86_64 installer asset found in release $($release.tag_name) of $usedRepo"
    }

    $dlPath = Join-Path $env:TEMP $asset.name
    Write-Host "[rrremote] Downloading $($asset.name) from $usedRepo ($($release.tag_name))..."
    $dlParams = @{
        Uri             = $asset.browser_download_url
        OutFile         = $dlPath
        UseBasicParsing = $true
    }
    if ($Proxy) { $dlParams["Proxy"] = $Proxy }
    Invoke-WebRequest @dlParams

    Write-Host "[rrremote] Installing $($asset.name)..."
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    $startParams = @{ PassThru = $true }
    if (-not $isAdmin) { $startParams["Verb"] = "RunAs" }

    if ($asset.name -like "*.msi") {
        $proc = Start-Process msiexec.exe -ArgumentList @("/i", "`"$dlPath`"", "/qn", "/norestart") @startParams
        $proc.WaitForExit()
    } else {
        $proc = Start-Process -FilePath $dlPath -ArgumentList @("--silent-install") @startParams
        # Wait up to 90s because silent-install may keep child service handles open
        $null = $proc.WaitForExit(90000)
    }

    if (-not (Test-Path "C:\Program Files\RustDesk\rustdesk.exe")) {
        throw "Installation verification failed: C:\Program Files\RustDesk\rustdesk.exe not found"
    }

    # Ensure branded RRRemote Desktop & Start Menu shortcuts (and clean legacy RustDesk shortcut)
    try {
        $wshell = New-Object -ComObject WScript.Shell
        $targetExe = "C:\Program Files\RustDesk\rustdesk.exe"
        $desktopDir = [Environment]::GetFolderPath("Desktop")
        $startMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
        foreach ($scPath in @(
            (Join-Path $desktopDir "RRRemote.lnk"),
            (Join-Path $startMenuDir "RRRemote.lnk")
        )) {
            $sc = $wshell.CreateShortcut($scPath)
            $sc.TargetPath = $targetExe
            $sc.WorkingDirectory = "C:\Program Files\RustDesk"
            $sc.IconLocation = "$targetExe,0"
            $sc.Description = "RRRemote Remote Desktop"
            $sc.Save()
        }
        Remove-Item (Join-Path $desktopDir "RustDesk.lnk") -Force -ErrorAction SilentlyContinue
    } catch {
        Write-Warning "Shortcut refresh skipped: $_"
    }

    Set-Content -Path $VersionFile -Value $tag -Encoding UTF8
    Remove-Item -Path $dlPath -Force -ErrorAction SilentlyContinue
    Write-Host "[rrremote] Installed $tag."
} else {
    Write-Host "[rrremote] Already up to date ($tag)."
}

if ($Server -and $Key) {
    $scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    $cfgScript = Join-Path $scriptRoot "configure-client.py"
    $argsList = @($cfgScript, "--server", $Server, "--key", $Key)
    if ($Relay) { $argsList += @("--relay", $Relay) }
    if ($ApiServer) { $argsList += @("--api-server", $ApiServer) }
    python @argsList
}

if ($RegisterAutoUpdate) {
    $scriptPath = $MyInvocation.MyCommand.Path
    $taskAction = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`" -Repo `"$Repo`""
    $taskTrigger = New-ScheduledTaskTrigger -Daily -At "04:00"
    $taskSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName "RRRemote-AutoUpdate" -Action $taskAction -Trigger $taskTrigger -Settings $taskSettings -Force | Out-Null
    Write-Host "[rrremote] Registered daily auto-update scheduled task 'RRRemote-AutoUpdate'."
}
