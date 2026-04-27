param(
    [string]$Python = ".\.venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$SourcePath = Join-Path $RepoRoot "src"

Push-Location $RepoRoot
try {
    $env:PYTHONPATH = $SourcePath

    & $Python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pytest') else 1)"
    $HasPytest = ($LASTEXITCODE -eq 0)

    if ($HasPytest) {
        & $Python -m pytest
    }
    else {
        & $Python -m unittest discover -s tests
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Tests failed with exit code ${LASTEXITCODE}."
    }
}
finally {
    Pop-Location
}
