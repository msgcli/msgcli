# install.ps1 — Quick installer for msgcli on Windows
# Usage: irm https://msgcli.org/install.ps1 | iex

$ErrorActionPreference = "Stop"
$REPO = if ($env:MSGCLI_REPO) { $env:MSGCLI_REPO } else { "https://github.com/msgcli/msgcli" }

function Find-Python {
    $candidates = @("python", "python3", "py")
    foreach ($cmd in $candidates) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($found) {
            return $found.Source
        }
    }
    return $null
}

function Check-Python($python) {
    try {
        & $python -c "import sys; assert sys.version_info >= (3, 9)" 2>$null
        if ($LASTEXITCODE -ne 0) {
            $ver = & $python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))" 2>$null
            Write-Host "Error: Python >= 3.9 is required (found $ver)" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "Error: Python >= 3.9 is required" -ForegroundColor Red
        exit 1
    }
}

function Check-Pip($python) {
    & $python -m pip --version 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: pip is not installed" -ForegroundColor Red
        exit 1
    }
}

function Install {
    $python = Find-Python
    if (-not $python) {
        Write-Host "Error: python is not installed" -ForegroundColor Red
        exit 1
    }

    Check-Python $python
    Check-Pip $python

    Write-Host "Installing msgcli..."
    & $python -m pip install --upgrade "git+${REPO}.git"
    & $python -m pip install --upgrade cryptography

    Write-Host ""
    Write-Host "msgcli installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Quick start:"
    Write-Host "  msg <username>    # Hybrid mode (server + client)"
    Write-Host "  msg user@host     # Client connect and chat"
    Write-Host "  msg --server      # Server mode"
    Write-Host "For more details, visit https://msgcli.org"
}

Install
