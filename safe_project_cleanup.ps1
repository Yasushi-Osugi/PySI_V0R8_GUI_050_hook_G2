<# ----------------------------------------------
  safe_project_cleanup.ps1  v1.1 (ASCII-only)
  Purpose:
    1) Preview cleanup targets (git clean dry-run)
    2) Zip-archive large/ignored data to dated folder
    3) Optionally delete ignored/untracked files safely
  ---------------------------------------------- #>

[CmdletBinding()]
param(
  [switch]$NonInteractive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Err ($msg){ Write-Host "[ERR ] $msg" -ForegroundColor Red }

# Ensure project root (git repo)
if (-not (Test-Path .git)) {
  Err "Not a git repository. Run at project root."
  exit 1
}

Info "Checking git status..."
git -c color.ui=always status | Write-Host

Info "git clean dry-run (ignored only: -ndX)"
git clean -ndX | Write-Host
Info "git clean dry-run (ignored + untracked: -ndx)"
git clean -ndx | Write-Host

# Candidates to archive
$archiveCandidates = @(
  'var','report','data','_data_parameters',
  '**/__pycache__','*.pyc','*.pyo','*.sqlite','*.xlsx','backup','*_BK*','*~$*'
)

function PrettySize([decimal]$bytes){
  $u = 'B','KB','MB','GB','TB'; $i = 0
  while($bytes -ge 1024 -and $i -lt $u.Count-1){ $bytes /= 1024; $i++ }
  '{0:N2} {1}' -f $bytes,$u[$i]
}

function MeasurePatterns($patterns){
  $total = 0
  foreach($pat in $patterns){
    $items = Get-ChildItem -Path $pat -Force -ErrorAction SilentlyContinue -Recurse
    foreach($it in $items){
      try{
        if($it.PSIsContainer){
          $size = (Get-ChildItem -LiteralPath $it.FullName -Force -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Sum Length).Sum
          $total += [int64]$size
        } else {
          $total += [int64]$it.Length
        }
      } catch {}
    }
  }
  $total
}

Info "Estimating archive candidate total size..."
$bytes = MeasurePatterns $archiveCandidates
Write-Host ("Estimated size: " + (PrettySize $bytes)) -ForegroundColor Green

# Mode selection
Write-Host ""
Write-Host "=== Select mode ===" -ForegroundColor Magenta
Write-Host "  [1] Archive only"
Write-Host "  [2] Archive, then delete ignored (git clean -fdX)"
Write-Host "  [3] Archive, then delete ignored+untracked (git clean -fdx) [DANGER]"
Write-Host "  [4] Preview only (do nothing)"
Write-Host "  [0] Cancel"
$choice = if($NonInteractive){ '1' } else { Read-Host "Enter choice [1/2/3/4/0]" }

if($choice -notin '0','1','2','3','4'){
  Err "Invalid choice. Abort."
  exit 1
}
if($choice -eq '0' -or $choice -eq '4'){
  Info "Preview only / Canceled. Bye."
  exit 0
}

# Archive destination
$archiveRoot = "C:\Users\ohsug\PSI_archives"
if (-not (Test-Path $archiveRoot)) { New-Item -ItemType Directory -Path $archiveRoot | Out-Null }
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$destDir = Join-Path $archiveRoot ("project_backup_" + $stamp)
$zipPath = Join-Path $destDir "bulk_data.zip"
New-Item -ItemType Directory -Path $destDir | Out-Null
Info ("Archive destination: " + $destDir)

# Zip helper
function Add-ToZip($pattern){
  $matches = Get-ChildItem -Path $pattern -Force -ErrorAction SilentlyContinue
  if(-not $matches){ return }
  foreach($m in $matches){
    try{
      if (-not (Test-Path $zipPath)) {
        Compress-Archive -Path $m.FullName -DestinationPath $zipPath -CompressionLevel Optimal
      } else {
        Compress-Archive -Path $m.FullName -DestinationPath $zipPath -CompressionLevel Optimal -Update
      }
      Write-Host ("  + " + $m.FullName) -ForegroundColor DarkGray
    } catch {
      Warn ("Compress failed: " + $m.FullName + " — " + $_.Exception.Message)
    }
  }
}

Info "Creating archive (may take time)..."
foreach($pat in $archiveCandidates){ Add-ToZip $pat }

if(-not (Test-Path $zipPath)){
  Warn "No files matched. Archive not created."
} else {
  $zipSize = (Get-Item $zipPath).Length
  Write-Host ("Archive created: " + $zipPath + "  [" + (PrettySize $zipSize) + "]") -ForegroundColor Green
}

# Deletion phase
switch($choice){
  '1' { Info "Mode [1]: Archive only. No deletion." }
  '2' {
    if(-not $NonInteractive){
      $confirm = Read-Host "Delete ignored files (git clean -fdX). Type: DELETE"
      if($confirm -ne 'DELETE'){ Warn "Canceled."; exit 0 }
    }
    Info "Running: git clean -fdX"
    git clean -fdX | Write-Host
  }
  '3' {
    Warn "Mode [3]: This will delete ignored + untracked! Not reversible."
    if(-not $NonInteractive){
      $confirm = Read-Host "Type: DELETE ALL"
      if($confirm -ne 'DELETE ALL'){ Warn "Canceled."; exit 0 }
    }
    Info "Running: git clean -fdx"
    git clean -fdx | Write-Host
  }
}

# Final summary
Write-Host ""
Info "Done. Final git status:"
git status | Write-Host
Write-Host ("Backup archive is at: " + $destDir) -ForegroundColor Cyan

