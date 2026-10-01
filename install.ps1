#Requires -Version 5.1
<#
.SYNOPSIS
  Install Limpieza on Windows (Python 3.10+, no extra runtime packages).
.NOTES
  Run from a PowerShell prompt in the project folder:

    powershell -ExecutionPolicy Bypass -File .\install.ps1
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Test-Python310 {
    param(
        [Parameter(Mandatory = $true)][string]$Exe,
        [string[]]$PrefixArgs = @()
    )
    try {
        $ver = & $Exe @PrefixArgs -c "import sys; print('%d.%d' % (sys.version_info[0], sys.version_info[1]))" 2>$null
        if (-not $ver) { return $null }
        $parts = ($ver.ToString().Trim() -split "\.")
        if ($parts.Count -lt 2) { return $null }
        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10)) {
            return $ver.ToString().Trim()
        }
    }
    catch {
        return $null
    }
    return $null
}

Write-Host "Limpieza installer (Windows)"
Write-Host "============================"

$pythonExe = $null
$pythonArgs = @()
$pythonVersion = $null

if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($launch in @(@("-3"), @("-3.13"), @("-3.12"), @("-3.11"), @("-3.10"))) {
        $found = Test-Python310 -Exe "py" -PrefixArgs $launch
        if ($found) {
            $pythonExe = "py"
            $pythonArgs = $launch
            $pythonVersion = $found
            break
        }
    }
}

if (-not $pythonExe -and (Get-Command python -ErrorAction SilentlyContinue)) {
    $found = Test-Python310 -Exe "python"
    if ($found) {
        $pythonExe = "python"
        $pythonArgs = @()
        $pythonVersion = $found
    }
}

if (-not $pythonExe) {
    Write-Host @"
Python 3.10 or newer was not found.

Install CPython from https://www.python.org/downloads/
and tick "Add python.exe to PATH". Then re-run this script.

No se encontro Python 3.10+. Instala CPython y vuelve a ejecutar install.ps1.
"@
    exit 1
}

Write-Host "Using Python $pythonVersion ($pythonExe $($pythonArgs -join ' '))"

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment in .venv ..."
    & $pythonExe @pythonArgs -m venv .venv
}

Write-Host "Installing Limpieza (editable, no third-party runtime deps) ..."
& $venvPython -m pip install -e .

Write-Host @"

Installed. / Instalado.

Run / Ejecuta:

  .\.venv\Scripts\limpieza.exe scan --safe
  .\.venv\Scripts\limpieza.exe gui
  .\.venv\Scripts\python.exe -m limpieza scan --safe

Activate the venv (optional) / Activar el entorno (opcional):

  .\.venv\Scripts\Activate.ps1

pipx (optional, isolated app install):

  python -m pip install --user pipx
  pipx install .
"@

$limpieza = Join-Path $PSScriptRoot ".venv\Scripts\limpieza.exe"
if (Test-Path $limpieza) {
    & $limpieza --version
}
exit 0
