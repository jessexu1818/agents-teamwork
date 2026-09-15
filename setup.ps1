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

function Get-PythonExe() {
  $c = Get-Command python3 -ErrorAction SilentlyContinue
  if ($null -eq $c) { $c = Get-Command python -ErrorAction SilentlyContinue }
  if ($null -eq $c) { return $null }
  return $c.Source
}

function Sync-StagedFile([string]$StagedFile, [string]$LiveFile, [string]$Rel, [string]$PyExe) {
  if (-not (Test-Path -LiteralPath $LiveFile)) {
    $parent = Split-Path -Parent $LiveFile
    if ($parent -and (-not (Test-Path -LiteralPath $parent))) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    Copy-Item -LiteralPath $StagedFile -Destination $LiveFile -Force
    return "written"
  }
  $sh = (Get-FileHash -LiteralPath $StagedFile -Algorithm SHA256).Hash
  $lh = (Get-FileHash -LiteralPath $LiveFile -Algorithm SHA256).Hash
  if ($sh -eq $lh) { return "unchanged" }
  $st = & $PyExe (Join-Path $ScriptDir "scripts/generate.py") --sync-file "$StagedFile" "$LiveFile"
  if ($LASTEXITCODE -ne 0) { Fail "sync failed for $Rel with exit code $LASTEXITCODE" }
  $status = (($st | Out-String).Trim().Split() | Where-Object { $_ -ne "" } | Select-Object -Last 1)
  if ($status -eq "kept") {
    Write-Host "kept user file: $Rel"
    $script:Kept++
  }
  return $status
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
      if (($Entry -eq ".codex") -and (Test-Path -LiteralPath (Join-Path $Src "config.toml") -PathType Leaf)) {
        $pyExe = Get-PythonExe
        if (-not $pyExe) {
          Fail "python3 (or python) is required to merge .codex/config.toml without overwriting user content"
        }
        $entryDirty = $false
        $stagedFiles = Get-ChildItem -LiteralPath $Src -Recurse -Force -File -ErrorAction Stop
        foreach ($sf in $stagedFiles) {
          $rel = $sf.FullName.Substring($Src.Length).TrimStart('\', '/')
          if ($rel -eq "config.toml") { continue }
          $live = Join-Path $Dst $rel
          $relDisp = ("$Entry/$rel" -replace '\\', '/')
          $s = Sync-StagedFile $sf.FullName $live $relDisp $pyExe
          if ($s -eq "written" -or $s -eq "updated") { $entryDirty = $true }
        }
        $mergeArgs = @((Join-Path $ScriptDir "scripts/generate.py"), "--merge-config-toml", (Join-Path $Dst "config.toml"), "--preset", $Preset)
        if (-not [string]::IsNullOrWhiteSpace($OrchestratorModel)) { $mergeArgs += @("--orchestrator-model", $OrchestratorModel) }
        if (-not [string]::IsNullOrWhiteSpace($ExplorerModel)) { $mergeArgs += @("--explorer-model", $ExplorerModel) }
        if (-not [string]::IsNullOrWhiteSpace($WorkerModel)) { $mergeArgs += @("--worker-model", $WorkerModel) }
        if (-not [string]::IsNullOrWhiteSpace($TesterModel)) { $mergeArgs += @("--tester-model", $TesterModel) }
        if (-not [string]::IsNullOrWhiteSpace($ReviewerModel)) { $mergeArgs += @("--reviewer-model", $ReviewerModel) }
        if (-not [string]::IsNullOrWhiteSpace($ResearcherModel)) { $mergeArgs += @("--researcher-model", $ResearcherModel) }
        if (-not [string]::IsNullOrWhiteSpace($PlannerModel)) { $mergeArgs += @("--planner-model", $PlannerModel) }
        if (-not [string]::IsNullOrWhiteSpace($OracleModel)) { $mergeArgs += @("--oracle-model", $OracleModel) }
        if (-not [string]::IsNullOrWhiteSpace($DesignerModel)) { $mergeArgs += @("--designer-model", $DesignerModel) }
        if (-not [string]::IsNullOrWhiteSpace($ReviewerEffort)) { $mergeArgs += @("--reviewer-effort", $ReviewerEffort) }
        $mergeStatus = & $pyExe @mergeArgs
        if ($LASTEXITCODE -ne 0) { Fail ".codex/config.toml merge failed with exit code $LASTEXITCODE" }
        Write-Host ".codex/config.toml: $mergeStatus"
        $m = (($mergeStatus | Out-String).Trim().Split() | Where-Object { $_ -ne "" } | Select-Object -Last 1)
        if ($m -eq "merged" -or $m -eq "written") { $entryDirty = $true }
        if ($entryDirty) {
          Write-Host "Updated $Entry."
          $script:Updated++
        } else {
          Write-Host "Up to date $Entry (unchanged, kept user files preserved)."
          $script:Skipped++
        }
        return
      }
      $pyExe2 = Get-PythonExe
      if (-not $pyExe2) {
        Fail "python3 (or python) is required to sync files without overwriting user content"
      }
      $entryDirty2 = $false
      $stagedFiles2 = Get-ChildItem -LiteralPath $Src -Recurse -Force -File -ErrorAction Stop
      foreach ($sf in $stagedFiles2) {
        $rel2 = $sf.FullName.Substring($Src.Length).TrimStart('\', '/')
        $live2 = Join-Path $Dst $rel2
        $relDisp2 = ("$Entry/$rel2" -replace '\\', '/')
        $s2 = Sync-StagedFile $sf.FullName $live2 $relDisp2 $pyExe2
        if ($s2 -eq "written" -or $s2 -eq "updated") { $entryDirty2 = $true }
      }
      if ($entryDirty2) {
        Write-Host "Updated $Entry."
        $script:Updated++
      } else {
        Write-Host "Up to date $Entry (unchanged, kept user files preserved)."
        $script:Skipped++
      }
      return
    } else {
      if (($Entry -eq "AGENTS.md") -and (-not $srcIsDir) -and (Test-Path -LiteralPath $Dst -PathType Leaf) -and (-not $dstIsLink)) {
        $pyExe = $null
        $c = Get-Command python3 -ErrorAction SilentlyContinue
        if ($null -eq $c) { $c = Get-Command python -ErrorAction SilentlyContinue }
        if ($null -ne $c) { $pyExe = $c.Source }
        if ($pyExe) {
          $agentsStatus = & $pyExe (Join-Path $ScriptDir "scripts/generate.py") --merge-agents-md "$Dst" --agents-template (Join-Path $ScriptDir "templates/AGENTS.md")
          if ($LASTEXITCODE -ne 0) { Fail "AGENTS.md merge failed with exit code $LASTEXITCODE" }
          Write-Host "AGENTS.md: $agentsStatus"
          $m2 = (($agentsStatus | Out-String).Trim().Split() | Where-Object { $_ -ne "" } | Select-Object -Last 1)
          if ($m2 -eq "unchanged") { $script:Skipped++ } else { $script:Updated++ }
          return
        }
        Fail "python3 (or python) is required to merge AGENTS.md without overwriting user content"
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
  $script:Kept = 0

  $tops = Get-ChildItem -LiteralPath $stageDir -Force
  foreach ($top in $tops) {
    Install-Entry $top.Name $top.FullName (Join-Path $TargetDir $top.Name)
  }

  Write-Host ""
  Write-Host "Setup complete: $script:NewCount new, $script:Updated updated, $script:Skipped skipped, $script:Kept kept in $TargetDir."
  Write-Host "Options: tools=$Tools components=$Components preset=$Preset"
  if ($Components -eq "skills-only") {
    Write-Host "Next: skills installed only. Verify a SKILL.md under each tool dir, then re-run with -Components all to add agent roles and AGENTS.md."
  } else {
    Write-Host "Next: verify AGENTS.md plus per-tool agents/ and skills/team-orchestrator/SKILL.md, then commit the result into the target repo."
  }
} finally {
  if (Test-Path -LiteralPath $stageBase) { Remove-Item -LiteralPath $stageBase -Recurse -Force -ErrorAction SilentlyContinue }
}
