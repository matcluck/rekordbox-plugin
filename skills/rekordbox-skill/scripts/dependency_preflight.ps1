[CmdletBinding()]
param(
    [switch]$Install,
    [string]$Database = "$env:APPDATA\Pioneer\rekordbox\master.db"
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"

$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$venvPython = Join-Path $project ".venv\Scripts\python.exe"
$checks = @(
    [pscustomobject]@{ Name = "uv"; Present = $null -ne (Get-Command uv -ErrorAction SilentlyContinue); Path = "uv" },
    [pscustomobject]@{ Name = "pyproject"; Present = Test-Path -LiteralPath (Join-Path $project "pyproject.toml") -PathType Leaf; Path = Join-Path $project "pyproject.toml" },
    [pscustomobject]@{ Name = "lockfile"; Present = Test-Path -LiteralPath (Join-Path $project "uv.lock") -PathType Leaf; Path = Join-Path $project "uv.lock" },
    [pscustomobject]@{ Name = "Rekordbox backend"; Present = Test-Path -LiteralPath (Join-Path $PSScriptRoot "rekordbox_backend.py") -PathType Leaf; Path = Join-Path $PSScriptRoot "rekordbox_backend.py" },
    [pscustomobject]@{ Name = "project environment"; Present = Test-Path -LiteralPath $venvPython -PathType Leaf; Path = $venvPython },
    [pscustomobject]@{ Name = "Rekordbox database"; Present = Test-Path -LiteralPath $Database -PathType Leaf; Path = $Database }
)

$checks | Format-Table -AutoSize
$missing = @($checks | Where-Object { -not $_.Present })
if ($Install) {
    if ($missing.Name -contains "uv") { throw "uv is missing; install or approve it before dependency setup." }
    if ($missing.Name -contains "pyproject" -or $missing.Name -contains "lockfile") { throw "The standalone Rekordbox runtime is incomplete: $project" }
    Push-Location -LiteralPath $project
    try {
        & uv sync --locked
        if ($LASTEXITCODE -ne 0) { throw "Locked Rekordbox dependency installation failed." }
    }
    finally { Pop-Location }
}
elseif (@($missing | Where-Object Name -ne "Rekordbox database").Count) {
    Write-Warning ("Missing dependency checks: " + (($missing.Name | Sort-Object -Unique) -join ", "))
    exit 2
}

if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    & $venvPython -c "import psutil, pyrekordbox; print('standalone Rekordbox runtime imports: ok')"
    if ($LASTEXITCODE -ne 0) { throw "The locked environment cannot import pyrekordbox." }
}

Write-Host "Rekordbox dependency preflight passed."
