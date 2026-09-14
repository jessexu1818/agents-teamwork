param(
  [string]$Target = "",
  [string]$Tools = "all",
  [string]$Extra = "",
  [ValidateSet("all", "skills-only")][string]$Components = "all",
  [ValidateSet("pro", "plus", "custom")][string]$Preset = "pro",
  [string]$OrchestratorModel = "",
  [string]$ExplorerModel = "",
  [string]$WorkerModel = "",
  [string]$TesterModel = "",
  [string]$ReviewerModel = "",
  [string]$ResearcherModel = "",
  [string]$PlannerModel = "",
  [string]$OracleModel = "",
  [string]$DesignerModel = "",
  [string]$ReviewerEffort = "",
  [switch]$Global,
  [switch]$Yes,
  [switch]$Help
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Show-Usage {
  @'
Usage: setup.ps1 -Target <path> [options]

Required:
  -Target <path>        existing directory to install into (must differ from source dir)

Optional:
  -Tools <all|csv>      all or csv of claude,codex,codebuddy,kiro,opencode,cursor,agents,antigravity,copilot,windsurf,qoder,trae (default: all)
  -Extra <csv>          csv subset of planner,oracle,designer (default: empty)
  -Components <v>       all|skills-only (default: all)
  -Preset <v>           pro|plus|custom (default: pro)
  -OrchestratorModel <m>, -ExplorerModel <m>, -WorkerModel <m>, -TesterModel <m>
  -ReviewerModel <m>, -ResearcherModel <m>, -PlannerModel <m>, -OracleModel <m>
  -DesignerModel <m>, -ReviewerEffort <e>
  -Yes                  skip confirmation prompts (assume yes)
  -Global               NOT SUPPORTED in v1 (refused with guidance)
  -Help                 show this help

Limits:
  -Global is refused in v1. The per-tool global install matrix varies too much
  across OS/user dirs; see guides/global-setup.md for manual steps.

Examples:
  .\setup.ps1 -Target C:\tmp\demo -Tools "claude,agents" -Components skills-only -Yes
  .\setup.ps1 -Target C:\tmp\demo -Components all -Extra "planner" -Preset pro
'@
}

function Fail([string]$Message) {
  Write-Error $Message
  exit 1
}

function Test-IsSymlink([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { return $false }
  $item = Get-Item -LiteralPath $Path -Force
  return ($null -ne $item.LinkType -and $item.LinkType -ne "") -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
}

function Get-OverwriteList([string]$Src, [string]$Dst, [string]$Entry) {
  $out = @()
  if (Test-Path -LiteralPath $Src -PathType Leaf) {
    if (Test-Path -LiteralPath $Dst) { $out += $Entry }
    return $out
  }
  $files = Get-ChildItem -LiteralPath $Src -Recurse -Force -File -ErrorAction Stop
  foreach ($f in $files) {
    $rel = $f.FullName.Substring($Src.Length).TrimStart('\', '/')
    $live = Join-Path $Dst $rel
    if (Test-Path -LiteralPath $live) { $out += ("$Entry/$rel" -replace '\\', '/') }
  }
  return $out
}

function Get-TypeConflictList([string]$Src, [string]$Dst) {
  $out = @()
  $files = Get-ChildItem -LiteralPath $Src -Recurse -Force -File -ErrorAction Stop
  foreach ($f in $files) {
    $rel = $f.FullName.Substring($Src.Length).TrimStart('\', '/')
    $live = Join-Path $Dst $rel
    if ((Test-Path -LiteralPath $live) -and (-not (Test-Path -LiteralPath $live -PathType Leaf))) {
      $out += ($rel -replace '\\', '/')
    }
  }
  $dirs = Get-ChildItem -LiteralPath $Src -Recurse -Force -Directory -ErrorAction Stop
  foreach ($d in $dirs) {
    $rel = $d.FullName.Substring($Src.Length).TrimStart('\', '/')
    if ($rel -eq "") { continue }
    $live = Join-Path $Dst $rel
    if ((Test-Path -LiteralPath $live) -and (-not (Test-Path -LiteralPath $live -PathType Container))) {
      $out += ($rel -replace '\\', '/')
    }
  }
  return $out
}

function Get-InnerSymlink([string]$Dst) {
  $items = Get-ChildItem -LiteralPath $Dst -Recurse -Force -ErrorAction Stop
  foreach ($it in $items) {
    $isLink = ($null -ne $it.LinkType -and $it.LinkType -ne "") -or (($it.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
    if ($isLink) { return $it.FullName }
  }
  return ""
}

function Ask-Choice([string]$Prompt, [bool]$DefaultYes) {
  if ($Yes) { return $true }
  if ($DefaultYes) { $hint = "[Y/n]" } else { $hint = "[y/N]" }
  while ($true) {
    $answer = Read-Host "$Prompt $hint"
    if ([string]::IsNullOrWhiteSpace($answer)) { return $DefaultYes }
    switch ($answer.Trim().ToLowerInvariant()) {
      "y" { return $true }
      "yes" { return $true }
      "n" { return $false }
      "no" { return $false }
      default { Write-Host "Please answer yes or no." }
    }
  }
}

function Install-Entry([string]$Entry, [string]$Src, [string]$Dst) {
  if (-not (Test-Path -LiteralPath $Src)) { Fail "staged source is missing: $Src" }
  $srcIsDir = Test-Path -LiteralPath $Src -PathType Container
  $dstExists = Test-Path -LiteralPath $Dst
  if ($dstExists) {
    $dstIsDir = Test-Path -LiteralPath $Dst -PathType Container
    $dstIsLink = Test-IsSymlink $Dst
    if ((-not $dstIsLink) -and $srcIsDir -and $dstIsDir) {
      $inner = Get-InnerSymlink $Dst
      if ($inner -ne "") {
        Write-Warning "Skipped ${Entry}: existing target contains a symbolic link ($inner)."
        $script:Skipped++
        return
      }
      $clashes = Get-TypeConflictList $Src $Dst
      if ($clashes.Count -gt 0) {
        Write-Warning "Skipped ${Entry}: source and target types conflict at:"
        foreach ($c in $clashes) { Write-Warning "  $c" }
        $script:Skipped++
        return
      }
    } elseif ($dstIsLink) {
      Write-Host "WARNING: the following symbolic link will be replaced:"
      Write-Host "  - $Entry"
    } elseif (($srcIsDir -and (-not $dstIsDir)) -or ((-not $srcIsDir) -and $dstIsDir)) {
      Write-Warning "Skipped ${Entry}: source and target types are incompatible."
      $script:Skipped++
      return
    } else {
      $existing = Get-OverwriteList $Src $Dst $Entry
      if ($existing.Count -gt 0) {
        Write-Host "WARNING: the following existing files will be overwritten:"
        foreach ($e in $existing) { Write-Host "  - $e" }
      }
    }
    if (-not (Ask-Choice "Update ${Entry}? Only listed paths are replaced." $false)) {
      Write-Host "Skipped $Entry (existing target left unchanged)."
      $script:Skipped++
      return
    }
    if ($dstIsLink) {
      Remove-Item -LiteralPath $Dst -Force
      Copy-Item -LiteralPath $Src -Destination $Dst -Recurse -Force
    } elseif ($srcIsDir -and $dstIsDir) {
      $children = Get-ChildItem -LiteralPath $Src -Force
      foreach ($child in $children) {
        Copy-Item -LiteralPath $child.FullName -Destination (Join-Path $Dst $child.Name) -Recurse -Force
      }
    } else {
      if (($Entry -eq "AGENTS.md") -and (-not $srcIsDir) -and (Test-Path -LiteralPath $Dst -PathType Leaf) -and (-not $dstIsLink)) {
        $pyExe = $null
        $c = Get-Command python3 -ErrorAction SilentlyContinue
        if ($null -eq $c) { $c = Get-Command python -ErrorAction SilentlyContinue }
        if ($null -ne $c) { $pyExe = $c.Source }
        if ($pyExe) {
          & $pyExe (Join-Path $ScriptDir "scripts/generate.py") --merge-agents-md "$Dst" --agents-template (Join-Path $ScriptDir "templates/AGENTS.md") | Out-Null
          Write-Host "Merged $Entry."
          $script:Updated++
          return
        }
        Copy-Item -LiteralPath $Src -Destination $Dst -Force
      } else {
        Copy-Item -LiteralPath $Src -Destination $Dst -Force
      }
    }
    Write-Host "Updated $Entry."
    $script:Updated++
  } else {
    if (-not (Ask-Choice "Install ${Entry}?" $true)) {
      Write-Host "Skipped $Entry."
      $script:Skipped++
      return
    }
    Copy-Item -LiteralPath $Src -Destination $Dst -Recurse -Force
    Write-Host "Installed $Entry."
    $script:NewCount++
  }
}

if ($Help) { Show-Usage; exit 0 }

if ($Global) {
  Write-Error "--Global is not supported in v1. Global install paths differ per tool and OS; follow guides/global-setup.md for manual steps."
  exit 1
}

if ([string]::IsNullOrWhiteSpace($Target)) { Fail "-Target <path> is required (use -Help for usage)" }
if (-not (Test-Path -LiteralPath $Target -PathType Container)) { Fail "target must be an existing directory: $Target" }

$TargetDir = (Resolve-Path -LiteralPath $Target).Path
$ResolvedScript = (Resolve-Path -LiteralPath $ScriptDir).Path
if ($TargetDir.TrimEnd('\', '/') -eq $ResolvedScript.TrimEnd('\', '/')) {
  Fail "target must differ from the setup source directory"
}

$genScript = Join-Path $ScriptDir "scripts/generate.py"
if (-not (Test-Path -LiteralPath $genScript -PathType Leaf)) { Fail "setup source is missing: $genScript" }

$pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
if ($null -eq $pythonCmd) { $pythonCmd = Get-Command python -ErrorAction SilentlyContinue }
if ($null -eq $pythonCmd) { Fail "python3 (or python) is required on PATH" }

$stageBase = Join-Path ([IO.Path]::GetTempPath()) ("agents-teamwork-" + [IO.Path]::GetRandomFileName())
$stageDir = Join-Path $stageBase "stage"
New-Item -ItemType Directory -Path $stageDir -Force | Out-Null
try {
  $genArgs = @($genScript, "--target", $stageDir, "--tools", $Tools, "--components", $Components, "--preset", $Preset)
  if (-not [string]::IsNullOrWhiteSpace($Extra)) { $genArgs += @("--extra", $Extra) }
  if (-not [string]::IsNullOrWhiteSpace($OrchestratorModel)) { $genArgs += @("--orchestrator-model", $OrchestratorModel) }
  if (-not [string]::IsNullOrWhiteSpace($ExplorerModel)) { $genArgs += @("--explorer-model", $ExplorerModel) }
  if (-not [string]::IsNullOrWhiteSpace($WorkerModel)) { $genArgs += @("--worker-model", $WorkerModel) }
  if (-not [string]::IsNullOrWhiteSpace($TesterModel)) { $genArgs += @("--tester-model", $TesterModel) }
  if (-not [string]::IsNullOrWhiteSpace($ReviewerModel)) { $genArgs += @("--reviewer-model", $ReviewerModel) }
  if (-not [string]::IsNullOrWhiteSpace($ResearcherModel)) { $genArgs += @("--researcher-model", $ResearcherModel) }
  if (-not [string]::IsNullOrWhiteSpace($PlannerModel)) { $genArgs += @("--planner-model", $PlannerModel) }
  if (-not [string]::IsNullOrWhiteSpace($OracleModel)) { $genArgs += @("--oracle-model", $OracleModel) }
  if (-not [string]::IsNullOrWhiteSpace($DesignerModel)) { $genArgs += @("--designer-model", $DesignerModel) }
  if (-not [string]::IsNullOrWhiteSpace($ReviewerEffort)) { $genArgs += @("--reviewer-effort", $ReviewerEffort) }
  & $pythonCmd.Source @genArgs
  if ($LASTEXITCODE -ne 0) { Fail "generate.py failed with exit code $LASTEXITCODE" }

  $script:NewCount = 0
  $script:Updated = 0
  $script:Skipped = 0

  $tops = Get-ChildItem -LiteralPath $stageDir -Force
  foreach ($top in $tops) {
    Install-Entry $top.Name $top.FullName (Join-Path $TargetDir $top.Name)
  }

  Write-Host ""
  Write-Host "Setup complete: $script:NewCount new, $script:Updated updated, $script:Skipped skipped in $TargetDir."
  Write-Host "Options: tools=$Tools components=$Components preset=$Preset"
  if ($Components -eq "skills-only") {
    Write-Host "Next: skills installed only. Verify a SKILL.md under each tool dir, then re-run with -Components all to add agent roles and AGENTS.md."
  } else {
    Write-Host "Next: verify AGENTS.md plus per-tool agents/ and skills/team-orchestrator/SKILL.md, then commit the result into the target repo."
  }
} finally {
  if (Test-Path -LiteralPath $stageBase) { Remove-Item -LiteralPath $stageBase -Recurse -Force -ErrorAction SilentlyContinue }
}
