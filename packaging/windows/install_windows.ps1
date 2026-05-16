#requires -Version 5.1
$ErrorActionPreference = "Stop"

$AppName = "VinaLab"
$Version = "0.0.2"
$InstallRoot = Join-Path $env:LOCALAPPDATA $AppName
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExeSource = Join-Path $SourceDir "VinaLab.exe"
$ExeTarget = Join-Path $InstallRoot "VinaLab.exe"
$ShortcutPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "VinaLab.lnk"
$LegacyRuntime = Join-Path $InstallRoot "VinaLab_runtime"

if (-not (Test-Path $ExeSource)) {
    throw "VinaLab.exe não encontrado ao lado deste instalador."
}

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
Copy-Item -Force -Path $ExeSource -Destination $ExeTarget

if (Test-Path $LegacyRuntime) {
    Remove-Item -LiteralPath $LegacyRuntime -Recurse -Force
}

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $ExeTarget
$Shortcut.WorkingDirectory = $InstallRoot
$Shortcut.Description = "VinaLab $Version"
$Shortcut.Save()

Write-Host "VinaLab $Version instalado em $InstallRoot"
Write-Host "Atalho criado em $ShortcutPath"
