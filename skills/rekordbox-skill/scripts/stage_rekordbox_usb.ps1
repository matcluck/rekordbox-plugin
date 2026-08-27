<#
.SYNOPSIS
Safely stage audio from a Rekordbox USB export or a specified USB subfolder.

.DESCRIPTION
Inventories <SourceRoot>\<PayloadRelativePath>, excludes macOS resource forks, and
copies supported audio into a new or resumable staging tree. Existing staged
files must match their source SHA-256 exactly; nothing is overwritten.

.EXAMPLE
$staging = Join-Path $PWD 'artifacts\runs\<run-id>\staging'
.\scripts\stage_rekordbox_usb.ps1 -SourceRoot <device-root> -StagingRoot $staging
.\scripts\stage_rekordbox_usb.ps1 -SourceRoot <device-root> -StagingRoot $staging -Apply
.\scripts\stage_rekordbox_usb.ps1 -SourceRoot <device-root> -PayloadRelativePath Music -StagingRoot $staging -Apply
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$SourceRoot,
    [Parameter(Mandatory)][string]$StagingRoot,
    [string]$PayloadRelativePath = 'Contents',
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$source = (Resolve-Path -LiteralPath $SourceRoot).Path.TrimEnd('\\')
if ([IO.Path]::IsPathRooted($PayloadRelativePath) -or $PayloadRelativePath -match '(^|[\\/])\.\.([\\/]|$)') {
    throw 'PayloadRelativePath must be a relative child path without traversal.'
}
$payload = Join-Path $source $PayloadRelativePath
if (-not (Test-Path -LiteralPath $payload -PathType Container)) {
    throw "Expected an audio payload directory at: $payload"
}

$destination = [IO.Path]::GetFullPath($StagingRoot).TrimEnd('\\')
$allowedExtensions = @('.mp3', '.wav', '.m4a', '.aif', '.aiff', '.flac', '.aac', '.ogg', '.opus', '.wma')

function Get-StageSha256 {
    param([Parameter(Mandatory)][string]$LiteralPath)
    if (Get-Command Get-FileHash -ErrorAction SilentlyContinue) {
        return (Get-FileHash -LiteralPath $LiteralPath -Algorithm SHA256).Hash
    }
    $stream = [IO.File]::OpenRead($LiteralPath)
    try {
        $sha = [Security.Cryptography.SHA256]::Create()
        try {
            return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-', '')
        }
        finally { $sha.Dispose() }
    }
    finally { $stream.Dispose() }
}

$files = @(
    Get-ChildItem -LiteralPath $payload -Recurse -File |
        Where-Object { $_.Extension.ToLowerInvariant() -in $allowedExtensions -and -not $_.Name.StartsWith('._') } |
        Sort-Object FullName
)
if ($files.Count -eq 0) { throw "No supported audio files found under: $payload" }

$sourceBytes = ($files | Measure-Object Length -Sum).Sum
$plan = foreach ($file in $files) {
    $relative = $file.FullName.Substring($payload.Length).TrimStart('\\')
    [pscustomobject]@{
        Source = $file.FullName
        RelativePath = $relative
        Destination = Join-Path $destination $relative
        Bytes = $file.Length
    }
}

Write-Host "Source audio: $($files.Count) file(s), $sourceBytes byte(s)"
Write-Host "Staging root: $destination"
if (-not $Apply) {
    $plan | Select-Object Source, RelativePath, Bytes | Format-Table -AutoSize
    Write-Host 'Dry run only. Re-run with -Apply to copy and SHA-256 verify every file.'
    exit 0
}

New-Item -ItemType Directory -Force -Path $destination | Out-Null
$copied = 0
$resumed = 0
foreach ($item in $plan) {
    if (Test-Path -LiteralPath $item.Destination -PathType Leaf) {
        $existing = Get-Item -LiteralPath $item.Destination
        if ($existing.Length -ne $item.Bytes) {
            throw "Staged destination differs in size and will not be overwritten: $($item.Destination)"
        }
        $sourceHash = Get-StageSha256 -LiteralPath $item.Source
        $destinationHash = Get-StageSha256 -LiteralPath $item.Destination
        if ($sourceHash -ne $destinationHash) {
            throw "Staged destination differs in SHA-256 and will not be overwritten: $($item.Destination)"
        }
        $resumed++
        continue
    }

    $parent = Split-Path -Path $item.Destination -Parent
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $temporary = Join-Path $parent ('.__codex_stage_' + [guid]::NewGuid().ToString('N'))
    try {
        Copy-Item -LiteralPath $item.Source -Destination $temporary -ErrorAction Stop
        if ((Get-Item -LiteralPath $temporary).Length -ne $item.Bytes) {
            throw "Temporary staged copy has an unexpected size: $temporary"
        }
        $sourceHash = Get-StageSha256 -LiteralPath $item.Source
        $temporaryHash = Get-StageSha256 -LiteralPath $temporary
        if ($sourceHash -ne $temporaryHash) {
            throw "Temporary staged copy failed SHA-256 verification: $($item.Source)"
        }
        Move-Item -LiteralPath $temporary -Destination $item.Destination -ErrorAction Stop
        $copied++
    }
    finally {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
    }
}

$staged = @(
    Get-ChildItem -LiteralPath $destination -Recurse -File |
        Where-Object { $_.Extension.ToLowerInvariant() -in $allowedExtensions -and -not $_.Name.StartsWith('._') }
)
$stagedBytes = ($staged | Measure-Object Length -Sum).Sum
if ($staged.Count -ne $files.Count -or $stagedBytes -ne $sourceBytes) {
    throw "Staging count/byte verification failed: source $($files.Count)/$sourceBytes; staged $($staged.Count)/$stagedBytes"
}
Write-Host "Verified staging complete. New: $copied; already verified: $resumed; total: $($staged.Count) file(s), $stagedBytes byte(s)."
