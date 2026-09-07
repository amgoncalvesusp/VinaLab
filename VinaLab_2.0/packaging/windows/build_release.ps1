param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if ($env:OS -ne "Windows_NT") { throw "Build Windows artifacts on Windows." }
& $Python -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m pip install "${ProjectRoot}[build]"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python (Join-Path $ProjectRoot "packaging\build_support.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $Python -m PyInstaller --noconfirm --clean --distpath (Join-Path $ProjectRoot "dist") --workpath (Join-Path $ProjectRoot "build\pyinstaller") (Join-Path $ProjectRoot "vinalab.spec")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$Executable = Join-Path $ProjectRoot "dist\VinaLab_2.0\VinaLab_2.0.exe"
$ReportDirectory = Join-Path $ProjectRoot "artifacts"
New-Item -ItemType Directory -Force -Path $ReportDirectory | Out-Null

function Invoke-FrozenCheck([string]$Flag, [string]$ReportFlag, [int]$TimeoutMs) {
    $Report = Join-Path $ReportDirectory ("frozen-{0}-{1}.json" -f $Flag.TrimStart('-'), [guid]::NewGuid())
    $Process = Start-Process -FilePath $Executable -ArgumentList @($Flag, $ReportFlag, "`"$Report`"") -WorkingDirectory $env:TEMP -WindowStyle Hidden -PassThru
    if (!$Process.WaitForExit($TimeoutMs)) {
        Stop-Process -Id $Process.Id -ErrorAction SilentlyContinue
        throw "Frozen check timed out: $Flag. Report: $Report"
    }
    if ($Process.ExitCode -ne 0) {
        throw "Frozen check failed ($($Process.ExitCode)): $Flag. Report: $Report"
    }
    if (!(Test-Path -LiteralPath $Report -PathType Leaf)) { throw "Missing frozen report: $Report" }
    $result = Get-Content -LiteralPath $Report -Raw | ConvertFrom-Json
    if ($result.ok -ne $true) { throw "Frozen report indicates failure: $Report" }
    if ($Flag -eq '--smoke-test') {
        foreach ($name in @('conversion', 'reference', 'vina', 'vinardo', 'xtb_gfn2', 'xtb_gfnff')) {
            $step = @($result.steps | Where-Object { $_.name -eq $name })
            if ($step.Count -ne 1 -or $step[0].ok -ne $true) {
                throw "Missing or failed smoke step ${name}: $Report"
            }
        }
    }
    Write-Host "Frozen check passed: $Report"
}

Invoke-FrozenCheck '--check-runtime' '--runtime-check-output' 120000
Invoke-FrozenCheck '--smoke-test' '--smoke-test-output' 1200000

$InnoCompiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$InnoPath = if ($null -ne $InnoCompiler) { $InnoCompiler.Source } else { $null }
if (!$InnoPath) {
    $Candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe")
    )
    $InnoPath = $Candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}
if ($InnoPath) {
    & $InnoPath (Join-Path $ProjectRoot "packaging\windows\VinaLab_2.0.iss")
    exit $LASTEXITCODE
}

Write-Host "Standalone build is ready in dist\VinaLab_2.0. Install Inno Setup 6 to create Setup.exe."
