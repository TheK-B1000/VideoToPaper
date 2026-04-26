param(
    [string]$Python = "python",
    [switch]$WithoutPip
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$SourcePath = Join-Path $RepoRoot "src"

function Invoke-Checked {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $Command $($Arguments -join ' ')"
    }
}

Push-Location $RepoRoot
try {
    if (-not (Test-Path $VenvPython)) {
        $VenvArgs = @("-m", "venv")
        if ($WithoutPip) {
            $VenvArgs += "--without-pip"
        }
        $VenvArgs += ".venv"
        Invoke-Checked -Command $Python -Arguments $VenvArgs
    }

    $env:PYTHONPATH = $SourcePath
    Invoke-Checked -Command $VenvPython -Arguments @("-m", "unittest", "discover", "-s", "tests")

    Write-Host ""
    Write-Host "Setup complete."
    Write-Host "Activate with: .\.venv\Scripts\Activate.ps1"
    Write-Host "Run tests with: .\scripts\test.ps1"
}
finally {
    Pop-Location
}
