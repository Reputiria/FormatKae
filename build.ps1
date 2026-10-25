param([string]$FFmpegDirectory = '', [switch]$CreateZip)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create Python environment.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Could not install build dependencies.' }
$buildArguments = @('scripts\build.py', '--ffmpeg', $FFmpegDirectory)
if ($CreateZip) { $buildArguments += '--zip' }
& '.\.venv\Scripts\python.exe' @buildArguments
if ($LASTEXITCODE -ne 0) { throw 'Build failed.' }
