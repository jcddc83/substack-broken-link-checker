# Substack Link Checker - Scheduled Task Script
#
# Checks for new posts and scans them for broken links. Set up with Windows
# Task Scheduler to run monthly.
#
# SETUP
# -----
# Copy secrets.ps1.example to secrets.ps1 and fill it in. That file is
# gitignored and holds both your configuration and your credentials, so
# nothing personal lives in this script and it stays safe to commit.
#
# Alternatively set SUBSTACK_URL and PROJECT_DIR in the environment.

$ErrorActionPreference = "Stop"

# Where this script lives, which is also the repo root.
$PROJECT_DIR = if ($env:PROJECT_DIR) { $env:PROJECT_DIR } else { $PSScriptRoot }

Set-Location $PROJECT_DIR

# secrets.ps1 supplies SUBSTACK_URL and the NOTIFY_* / SUBSTACK_COOKIE
# variables. Without it the run can still work, but failures go unreported --
# which is the failure mode this whole script exists to avoid, so say so.
$secretsPath = Join-Path $PROJECT_DIR "secrets.ps1"
if (Test-Path $secretsPath) {
    . $secretsPath
} else {
    Write-Host "WARNING: secrets.ps1 not found. Failure alerts will not send."
    Write-Host "         Copy secrets.ps1.example to secrets.ps1 and fill it in."
}

$SUBSTACK_URL = if ($env:SUBSTACK_URL) { $env:SUBSTACK_URL } else { $null }
if (-not $SUBSTACK_URL) {
    Write-Host "ERROR: SUBSTACK_URL is not set. Set it in secrets.ps1 or the environment."
    exit 1
}

# Redirected stdout falls back to the locale encoding on Windows, which cannot
# represent every character in a scraped URL or post title. The CLI reconfigures
# its own streams, but this also covers anything else the run prints.
$env:PYTHONIOENCODING = "utf-8"

# Put src/ on PYTHONPATH so `python -m substack_link_checker` resolves from a
# plain `git clone`, without requiring `pip install -e .` first.
$env:PYTHONPATH = (Join-Path $PROJECT_DIR "src") + ";" + $env:PYTHONPATH

New-Item -ItemType Directory -Force -Path "logs" | Out-Null
New-Item -ItemType Directory -Force -Path "reports" | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"

Start-Transcript -Path "logs\run_$timestamp.log"

Write-Host "=========================================="
Write-Host "Substack Link Checker - Scheduled Run"
Write-Host "Started: $(Get-Date)"
Write-Host "Substack: $SUBSTACK_URL"
Write-Host "=========================================="

$runFailed = $false
try {
    # Step 1: Compare the sitemap against history to find new posts.
    Write-Host "`nStep 1: Finding new posts..."
    python -m substack_link_checker compare $SUBSTACK_URL checked_posts.json 2>&1 |
        Tee-Object -Variable step1Out
    if ($LASTEXITCODE -ne 0) { throw "compare failed (exit code $LASTEXITCODE)" }

    # Step 2: Check the unchecked posts. --only-new skips anything already
    # recorded in history, so a partial previous run does not redo work.
    Write-Host "`nStep 2: Checking unchecked posts for broken links..."
    python -m substack_link_checker check `
        --base-url $SUBSTACK_URL `
        --url-file unchecked_posts.txt `
        --history-file checked_posts.json `
        --only-new `
        --output "reports\broken_links_$timestamp.csv" `
        --verbose 2>&1 | Tee-Object -Variable step2Out
    if ($LASTEXITCODE -ne 0) { throw "check failed (exit code $LASTEXITCODE)" }

    Write-Host "`n=========================================="
    Write-Host "Completed: $(Get-Date)"
    Write-Host "Report saved to: reports\broken_links_$timestamp.csv"
    Write-Host "=========================================="
}
catch {
    $runFailed = $true
    $errMsg = $_.ToString()

    # An expired Substack cookie surfaces as HTTP 403 / Forbidden in the output.
    $combined = @($step1Out) + @($step2Out) + @($errMsg) -join "`n"
    $isCookieError = $combined -match '403|Forbidden|cookie'

    Write-Host "`n=========================================="
    Write-Host "RUN FAILED: $errMsg" -ForegroundColor Red
    Write-Host "Sending failure notification..."
    Write-Host "=========================================="

    $notifyArgs = @("--project", "Substack Link Checker", "--error", $errMsg)
    if ($isCookieError) { $notifyArgs += "--cookie-error" }
    python -m substack_link_checker.notify @notifyArgs
}

Stop-Transcript

# Let Task Scheduler's "Last Run Result" reflect a real failure. Without this
# a failed run reports success and nobody finds out for a month.
if ($runFailed) { exit 1 } else { exit 0 }
