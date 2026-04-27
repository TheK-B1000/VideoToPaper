param(
    [string]$Python = "python",
    [switch]$WithoutPip
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$TempRoot = Join-Path $RepoRoot ".tmp"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

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
    New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null
    $OriginalTemp = $env:TEMP
    $OriginalTmp = $env:TMP
    $env:TEMP = $TempRoot
    $env:TMP = $TempRoot
    $InstalledDevTools = $false

    if (-not (Test-Path $VenvPython)) {
        $VenvArgs = @("-m", "venv")
        if ($WithoutPip) {
            $VenvArgs += "--without-pip"
        }
        $VenvArgs += ".venv"
        Invoke-Checked -Command $Python -Arguments $VenvArgs
    }

    if (-not $WithoutPip) {
        try {
            & $VenvPython -m pip --version *> $null
            if ($LASTEXITCODE -ne 0) {
                Invoke-Checked -Command $VenvPython -Arguments @("-m", "ensurepip", "--upgrade")
            }

            Invoke-Checked -Command $VenvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip")
            Invoke-Checked -Command $VenvPython -Arguments @("-m", "pip", "install", "-e", ".[dev]")
            $InstalledDevTools = $true
        }
        catch {
            Write-Warning "Skipping dev dependency install because pip could not be bootstrapped in this environment."
        }
    }

    & (Join-Path $RepoRoot "scripts\test.ps1") -Python $VenvPython
    if ($LASTEXITCODE -ne 0) {
        throw "Test run failed with exit code ${LASTEXITCODE}."
    }

    Write-Host ""
    Write-Host "Setup complete."
    Write-Host "Activate with: .\.venv\Scripts\Activate.ps1"
    Write-Host "Run tests with: .\scripts\test.ps1"
    if ($InstalledDevTools) {
        Write-Host 'Optional roadmap extras: .\.venv\Scripts\python.exe -m pip install -e ".[ingestion,ai,retrieval,storage,api,ui]"'
    }
}
finally {
    $env:TEMP = $OriginalTemp
    $env:TMP = $OriginalTmp
    Remove-Item -Recurse -Force -LiteralPath $TempRoot -ErrorAction SilentlyContinue
    Pop-Location
}
