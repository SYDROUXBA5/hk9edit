# One-time setup for the hk9edit skill on Windows: ffmpeg, Python packages, Whisper (speech to text) and its model,
# then a full check. Run it from PowerShell after cloning the skill (see README.md):
#
#   powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\skills\hk9edit\install_windows.ps1"
#
# Safe to run again: anything already installed is kept.
param([switch]$SkipWinget, [string]$Model = "small", [string]$Python = "")
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"          # the progress bar makes Invoke-WebRequest very slow
function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Refresh-Path { $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User") }

Write-Host "`n1/4  ffmpeg and Python"
if (-not $SkipWinget) {
    if (-not (Have winget)) { throw "winget is missing: install 'App Installer' from the Microsoft Store, then run this again." }
    if (-not (Have ffmpeg)) { winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements }
    if (-not (Have py) -and -not (Have python)) { winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements }
    Refresh-Path
}
if (-not (Have ffmpeg)) { throw "ffmpeg is still not found: close PowerShell, open it again and re-run this script." }
if (-not $Python) { $Python = if (Have py) { "py" } else { "python" } }

Write-Host "`n2/4  Python packages (numpy, scipy, pillow)"
& $Python -m pip install --upgrade --quiet numpy scipy pillow
if ($LASTEXITCODE) { throw "pip failed" }

Write-Host "`n3/4  Whisper (runs on this PC; nothing is uploaded)"
$dir = Join-Path $env:USERPROFILE "whisper"
$exe = Get-ChildItem $dir -Recurse -Filter whisper-cli.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $exe) {
    # Windows builds are published on the numbered build releases, not always on the newest version tag
    $rels = Invoke-RestMethod "https://api.github.com/repos/ggml-org/whisper.cpp/releases?per_page=30"
    $rel = $rels | Where-Object { $_.assets.name -contains "whisper-bin-x64.zip" } | Select-Object -First 1
    if (-not $rel) { throw "no whisper-bin-x64.zip found on https://github.com/ggml-org/whisper.cpp/releases" }
    $url = ($rel.assets | Where-Object name -eq "whisper-bin-x64.zip").browser_download_url
    Write-Host "     downloading whisper.cpp $($rel.tag_name)"
    Invoke-WebRequest $url -OutFile (Join-Path $env:TEMP "whisper-bin-x64.zip")
    Expand-Archive (Join-Path $env:TEMP "whisper-bin-x64.zip") -DestinationPath $dir -Force
    $exe = Get-ChildItem $dir -Recurse -Filter whisper-cli.exe | Select-Object -First 1
}
[Environment]::SetEnvironmentVariable("WHISPER_CLI", $exe.FullName, "User"); $env:WHISPER_CLI = $exe.FullName
Write-Host "     $($exe.FullName)"
$models = Join-Path $env:USERPROFILE ".whisper-models"
$file = Join-Path $models "ggml-$Model.en.bin"
if (-not (Test-Path $file)) {
    New-Item -ItemType Directory -Force $models | Out-Null
    Write-Host "     downloading the $Model English model (small = about 470 MB)"
    Invoke-WebRequest "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$Model.en.bin" -OutFile $file
}
[Environment]::SetEnvironmentVariable("WHISPER_MODEL", $file, "User"); $env:WHISPER_MODEL = $file

Write-Host "`n4/4  Check"
& $Python (Join-Path $PSScriptRoot "scripts\setup_check.py")
exit $LASTEXITCODE
