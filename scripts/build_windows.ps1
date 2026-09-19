param(
    [string]$Python = 'python',
    [string]$InnoCompiler = '',
    [switch]$SkipDependencies
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = Split-Path -Parent $PSScriptRoot
$originalSearchPath = $env:PATH
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path '.venv\Scripts\python.exe')) {
        & $Python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Creating virtual environment failed.' }
    }
    $pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not $SkipDependencies) {
        & $pythonExe -m pip install -r requirements-build.lock
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    }
    & $pythonExe scripts\collect_licenses.py
    if ($LASTEXITCODE -ne 0) { throw 'License collection failed.' }
    $testDirectory = Join-Path $projectRoot ('build\pytest-' + [guid]::NewGuid().ToString('N'))
    & $pythonExe -m pytest -q -p no:cacheprovider --basetemp $testDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
    # Keep unrelated tools (e.g. Poppler/Conda ICU DLLs) out of dependency discovery.
    $pythonBase = & $pythonExe -c 'import sys; print(sys.base_prefix)'
    $env:PATH = "$projectRoot\.venv\Scripts;$pythonBase;$pythonBase\DLLs;$env:WINDIR\System32;$env:WINDIR"
    & $pythonExe -m PyInstaller --clean --noconfirm CHSITranslator.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
    $env:CHSI_SELFTEST_OUTPUT = Join-Path $projectRoot 'build\frozen-selftest.json'
    $selfTest = Start-Process -FilePath '.\dist\CHSITranslator\CHSITranslator.exe' -ArgumentList '--self-test' -WindowStyle Hidden -PassThru -Wait
    if ($selfTest.ExitCode -ne 0 -or -not (Test-Path $env:CHSI_SELFTEST_OUTPUT)) { throw 'Frozen application self-test failed.' }
    if ((Get-Content $env:CHSI_SELFTEST_OUTPUT -Raw | ConvertFrom-Json).status -ne 'passed') { throw 'Frozen self-test did not pass.' }
    Remove-Item Env:CHSI_SELFTEST_OUTPUT
    if (-not $InnoCompiler) {
        $candidates = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")
        $InnoCompiler = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    }
    if (-not $InnoCompiler -or -not (Test-Path $InnoCompiler)) { throw 'Install Inno Setup 6 and specify -InnoCompiler path\ISCC.exe.' }
    & $InnoCompiler installer\setup.iss
    if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
    & $pythonExe scripts\package_source.py
    if ($LASTEXITCODE -ne 0) { throw 'Source packaging failed.' }
    Write-Output 'Build complete. See release/.'
} finally {
    $env:PATH = $originalSearchPath
    Pop-Location
}
