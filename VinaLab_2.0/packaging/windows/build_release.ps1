param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $ProjectRoot

& $Python -m PyInstaller --noconfirm --clean vinalab.spec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$InnoCompiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($null -ne $InnoCompiler) {
    & $InnoCompiler.Source (Join-Path $ProjectRoot "packaging\windows\VinaLab_2.0.iss")
    exit $LASTEXITCODE
}

Write-Host "Standalone build is ready in dist\VinaLab_2.0. Install Inno Setup 6 to create Setup.exe."
