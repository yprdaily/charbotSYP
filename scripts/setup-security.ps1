# scripts/setup-security.ps1
# One-shot local security setup for this repo (Windows)
# - Install/ensure: pre-commit, detect-secrets
# - Install git hook
# - Run pre-commit on all files (optional)
# - Create/Update .secrets.baseline safely

[CmdletBinding()]
param(
  [string]$RepoRoot = (Get-Location).Path,
  [switch]$SkipPreCommitRun,
  [switch]$StageBaseline
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Require-Command([string]$name, [string]$hint) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Missing command: $name`n$hint"
  }
}

Write-Host "== RepoRoot: $RepoRoot ==" -ForegroundColor Cyan
Set-Location $RepoRoot

# --- prerequisites ---
Require-Command git "Install Git for Windows and retry."
Require-Command py  "Install Python (py launcher) and retry."

# --- ensure pip packages (user install; avoids admin) ---
Write-Host "`n== Ensure Python tools ==" -ForegroundColor Cyan
py -m pip install --upgrade pip | Out-Null
py -m pip install --upgrade pre-commit detect-secrets | Out-Null

# --- ensure pre-commit config exists (create minimal if missing) ---
if (-not (Test-Path ".pre-commit-config.yaml")) {
  Write-Host "`n== .pre-commit-config.yaml not found; creating minimal config ==" -ForegroundColor Yellow
  @"
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.21.2
    hooks:
      - id: gitleaks
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]
"@ | Set-Content -Encoding utf8 ".pre-commit-config.yaml"
} else {
  Write-Host "`n== Found .pre-commit-config.yaml ==" -ForegroundColor Green
}

# --- install hook ---
Write-Host "`n== Install pre-commit hook ==" -ForegroundColor Cyan
py -m pre_commit install

if (-not $SkipPreCommitRun) {
  Write-Host "`n== Run pre-commit on all files ==" -ForegroundColor Cyan
  py -m pre_commit run -a
} else {
  Write-Host "`n== Skip pre-commit run (-SkipPreCommitRun) ==" -ForegroundColor Yellow
}

# --- create/update detect-secrets baseline ---
Write-Host "`n== Create/Update .secrets.baseline ==" -ForegroundColor Cyan

$baseline = Join-Path $RepoRoot ".secrets.baseline"
$tmp = Join-Path $RepoRoot ".secrets.baseline.tmp"

if (Test-Path $baseline) {
  # update: read existing baseline then output new baseline
  py -m detect_secrets scan --all-files --baseline $baseline | Out-File -Encoding utf8 -FilePath $tmp
  Move-Item -Force $tmp $baseline
  Write-Host "Updated: .secrets.baseline" -ForegroundColor Green
} else {
  # initial create: output baseline
  py -m detect_secrets scan --all-files | Out-File -Encoding utf8 -FilePath $baseline
  Write-Host "Created: .secrets.baseline" -ForegroundColor Green
}

# --- optional stage baseline ---
if ($StageBaseline) {
  Write-Host "`n== Stage baseline ==" -ForegroundColor Cyan
  git add .secrets.baseline
  Write-Host "Staged: .secrets.baseline" -ForegroundColor Green
}

Write-Host "`nDONE." -ForegroundColor Green
Write-Host "Next (optional): review baseline interactively -> py -m detect_secrets audit .secrets.baseline" -ForegroundColor Gray
