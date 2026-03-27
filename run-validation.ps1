param(
    [switch]$IncludeBpx,
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

function Resolve-PythonExecutable {
    param([string]$Override)

    if ($Override) {
        return $Override
    }

    $venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }

    if ($env:PYTHON_EXE) {
        return $env:PYTHON_EXE
    }

    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    throw "Could not locate Python. Pass -PythonExe or create .venv."
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

$referenceJson = Join-Path $repoRoot "figures\battmo-validation-reference.json"
if (-not (Test-Path $referenceJson)) {
    throw "Missing $referenceJson. Run runReproduction in MATLAB first."
}

$resolvedPython = Resolve-PythonExecutable -Override $PythonExe

Write-Host "Repository root: $repoRoot"
Write-Host "Python: $resolvedPython"
Write-Host "Running optional Python-side validation workflow..."

Invoke-Checked -FilePath $resolvedPython -Arguments @("scripts\plot_battmo_validation.py")

if ($IncludeBpx) {
    Write-Host "Running optional BPX / PyBaMM FAIR interoperability workflow..."
    Invoke-Checked -FilePath $resolvedPython -Arguments @("scripts\export_bpx.py")
    Invoke-Checked -FilePath $resolvedPython -Arguments @("scripts\verify_bpx.py", "--output", "codex\figures\bpx_verification_summary.json")
    Invoke-Checked -FilePath $resolvedPython -Arguments @("scripts\compare_battmo_pybamm.py")
}

Write-Host ""
Write-Host "Validation outputs:"
Write-Host "  figures\publication\INP5-70-120-H0B_graphite-lnmo_schmitt-2026_battmo-vs-experiment-summary.json"
Write-Host "  figures\publication\INP5-70-120-H0B_graphite-lnmo_schmitt-2026_battmo-vs-experiment.png"

if ($IncludeBpx) {
    Write-Host ""
    Write-Host "Optional BPX / PyBaMM outputs:"
    Write-Host "  parameters\INP5-70-120-H0B_graphite-lnmo_schmitt-2026_validation.bpx.json"
    Write-Host "  codex\figures\bpx_verification_summary.json"
    Write-Host "  codex\figures\battmo-vs-pybamm-bpx-summary.json"
    Write-Host "  codex\figures\battmo-vs-pybamm-bpx.png"
}
