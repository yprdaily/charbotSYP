Param(
  [string]$RepoUrl = "https://github.com/your-username/your-repo.git",
  [string]$ProjectDir = "$env:USERPROFILE\dev\chatbot-react",
  [string]$GcpProject = "your-gcp-project-id",
  [string]$GcpRegion = "asia-northeast1",
  [switch]$InstallDeps,
  [switch]$BuildFrontend,
  [switch]$ConfigureGcloud
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Ok($msg)   { Write-Host "[ OK ] $msg" -ForegroundColor Green }

function Test-Cmd($name) {
  try { Get-Command $name -ErrorAction Stop | Out-Null; return $true } catch { return $false }
}

function Try-Run($scriptBlock, $onFailMsg) {
  try { & $scriptBlock } catch { Write-Warn "${onFailMsg}: $($_.Exception.Message)" }
}

Write-Info "CorpBot setup starting..."
Write-Info "Target dir: $ProjectDir"

# 0) prerequisites check
if (-not (Test-Cmd git))  { throw "git is not installed. Install Git for Windows first." }
if (-not (Test-Cmd node)) { Write-Warn "node is not installed. Install Node.js LTS." }
if (-not (Test-Cmd npm))  { Write-Warn "npm is not available. Install Node.js LTS." }
if (-not (Test-Cmd gcloud)) { Write-Warn "gcloud is not installed. Install Google Cloud SDK if you deploy/test Cloud Run." }

Write-Ok "commands check done"

# Optional: install via winget (best-effort)
if ($InstallDeps) {
  if (Test-Cmd winget) {
    Write-Info "Attempting dependency install via winget (best-effort)..."
    Try-Run { winget install --id Git.Git -e --source winget } "Git install skipped/failed"
    Try-Run { winget install --id OpenJS.NodeJS.LTS -e --source winget } "Node install skipped/failed"
    Try-Run { winget install --id Google.CloudSDK -e --source winget } "gcloud install skipped/failed"
    Try-Run { winget install --id Microsoft.VisualStudioCode -e --source winget } "VS Code install skipped/failed"
  } else {
    Write-Warn "winget not found. Skipping auto-install."
  }
}

# 1) clone or pull
if (-not (Test-Path $ProjectDir)) {
  Write-Info "Cloning repository..."
  New-Item -ItemType Directory -Force (Split-Path $ProjectDir) | Out-Null
  git clone $RepoUrl $ProjectDir
  Write-Ok "Cloned: $RepoUrl"
} else {
  Write-Info "Repository exists. Pulling latest..."
  Push-Location $ProjectDir
  git fetch origin
  git checkout main
  git pull --rebase origin main
  Pop-Location
  Write-Ok "Updated repo"
}

# 2) enforce local folders
Push-Location $ProjectDir
New-Item -ItemType Directory -Force .\ops | Out-Null
Write-Ok "Ensured ops/ exists (debug only; should be gitignored)"

# 3) show status
Write-Info "Current git status:"
git status

# 4) frontend install/build (optional)
if ($BuildFrontend -or $InstallDeps) {
  if (Test-Path ".\frontend\package.json") {
    Write-Info "Frontend detected: frontend/"
    Push-Location ".\frontend"
    if ($InstallDeps) {
      Write-Info "npm ci..."
      npm ci
      Write-Ok "npm ci done"
    }
    if ($BuildFrontend) {
      Write-Info "npm run build..."
      npm run build
      Write-Ok "frontend build done"
    }
    Pop-Location
  } else {
    Write-Warn "frontend/package.json not found. Skipping frontend install/build."
  }
}

# 5) gcloud configure (optional)
if ($ConfigureGcloud) {
  if (Test-Cmd gcloud) {
    Write-Info "Configuring gcloud project/region..."
    gcloud auth login | Out-Null
    gcloud config set project $GcpProject | Out-Null
    gcloud config set run/region $GcpRegion | Out-Null
    gcloud config set builds/region $GcpRegion | Out-Null
    Write-Ok "gcloud configured"
  } else {
    Write-Warn "gcloud not installed; skipping configuration."
  }
}

Pop-Location

Write-Host ""
Write-Ok "Setup complete."
Write-Host ""
Write-Host "Next steps:"
Write-Host "1) Build frontend (if needed):  cd $ProjectDir\frontend ; npm ci ; npm run build" -ForegroundColor Gray
Write-Host "2) Load Chrome extension: chrome://extensions -> Developer mode -> Load unpacked -> select $ProjectDir" -ForegroundColor Gray
Write-Host "3) If Cloud Run deploy needed: gcloud builds triggers run corpbot-api-main --project $GcpProject --region $GcpRegion --branch main" -ForegroundColor Gray
