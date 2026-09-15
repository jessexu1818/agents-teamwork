#!/bin/sh
# setup.sh: thin wrapper around scripts/generate.py with safe install prompts (POSIX sh).
set -eu
unset CDPATH
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd -P)

TARGET=""
TOOLS="all"
EXTRA=""
COMPONENTS="all"
PRESET="pro"
ORCHESTRATOR_MODEL=""
EXPLORER_MODEL=""
WORKER_MODEL=""
TESTER_MODEL=""
REVIEWER_MODEL=""
RESEARCHER_MODEL=""
PLANNER_MODEL=""
ORACLE_MODEL=""
DESIGNER_MODEL=""
REVIEWER_EFFORT=""
WANT_GLOBAL=0
AUTO_YES=0

show_help() {
cat <<'USAGE'
Usage: setup.sh --target <path> [options]

Required:
  --target <path>        existing directory to install into (must differ from source dir)

Optional:
  --tools <all|csv>      all or csv of claude,codex,codebuddy,kiro,opencode,cursor,agents,antigravity,copilot,windsurf,qoder,trae (default: all)
  --extra <csv>          csv subset of planner,oracle,designer (default: empty)
  --components <v>       all|skills-only (default: all)
  --preset <v>           pro|plus|custom (default: pro)
  --orchestrator-model/--explorer-model/--worker-model/--tester-model/--reviewer-model <m>
  --researcher-model/--planner-model/--oracle-model/--designer-model <m>, --reviewer-effort <e>
  --yes                  skip confirmation prompts (assume yes)
  --global               NOT SUPPORTED in v1 (refused with guidance)
  --help                 show this help

Limits:
  --global is refused in v1. The per-tool global install matrix varies too much
  across OS/user dirs; see guides/global-setup.md for manual steps.

Examples:
  sh setup.sh --target /tmp/demo --tools claude,agents --components skills-only --yes
  sh setup.sh --target /tmp/demo --components all --extra planner --preset pro
USAGE
}

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

need_value() {
  if [ $# -lt 2 ] || [ -z "$2" ]; then
    fail "option $1 requires a value"
  fi
}

while [ $# -gt 0 ]; do
  case "$1" in
    --target) need_value "$@"; TARGET=$2; shift 2 ;;
    --target=*) TARGET=${1#--target=}; shift ;;
    --tools) need_value "$@"; TOOLS=$2; shift 2 ;;
    --tools=*) TOOLS=${1#--tools=}; shift ;;
    --extra) need_value "$@"; EXTRA=$2; shift 2 ;;
    --extra=*) EXTRA=${1#--extra=}; shift ;;
    --components) need_value "$@"; COMPONENTS=$2; shift 2 ;;
    --components=*) COMPONENTS=${1#--components=}; shift ;;
    --preset) need_value "$@"; PRESET=$2; shift 2 ;;
    --preset=*) PRESET=${1#--preset=}; shift ;;
    --orchestrator-model) need_value "$@"; ORCHESTRATOR_MODEL=$2; shift 2 ;;
    --orchestrator-model=*) ORCHESTRATOR_MODEL=${1#--orchestrator-model=}; shift ;;
    --explorer-model) need_value "$@"; EXPLORER_MODEL=$2; shift 2 ;;
    --explorer-model=*) EXPLORER_MODEL=${1#--explorer-model=}; shift ;;
    --worker-model) need_value "$@"; WORKER_MODEL=$2; shift 2 ;;
    --worker-model=*) WORKER_MODEL=${1#--worker-model=}; shift ;;
    --tester-model) need_value "$@"; TESTER_MODEL=$2; shift 2 ;;
    --tester-model=*) TESTER_MODEL=${1#--tester-model=}; shift ;;
    --reviewer-model) need_value "$@"; REVIEWER_MODEL=$2; shift 2 ;;
    --reviewer-model=*) REVIEWER_MODEL=${1#--reviewer-model=}; shift ;;
    --researcher-model) need_value "$@"; RESEARCHER_MODEL=$2; shift 2 ;;
    --researcher-model=*) RESEARCHER_MODEL=${1#--researcher-model=}; shift ;;
    --planner-model) need_value "$@"; PLANNER_MODEL=$2; shift 2 ;;
    --planner-model=*) PLANNER_MODEL=${1#--planner-model=}; shift ;;
    --oracle-model) need_value "$@"; ORACLE_MODEL=$2; shift 2 ;;
    --oracle-model=*) ORACLE_MODEL=${1#--oracle-model=}; shift ;;
    --designer-model) need_value "$@"; DESIGNER_MODEL=$2; shift 2 ;;
    --designer-model=*) DESIGNER_MODEL=${1#--designer-model=}; shift ;;
    --reviewer-effort) need_value "$@"; REVIEWER_EFFORT=$2; shift 2 ;;
    --reviewer-effort=*) REVIEWER_EFFORT=${1#--reviewer-effort=}; shift ;;
    --global) WANT_GLOBAL=1; shift ;;
    --yes) AUTO_YES=1; shift ;;
    --help|-h) show_help; exit 0 ;;
    --) shift; break ;;
    -*) fail "unknown option: $1 (see --help)" ;;
    *) fail "unexpected argument: $1 (see --help)" ;;
  esac
done

if [ "$WANT_GLOBAL" -eq 1 ]; then
  printf 'Error: --global is not supported in v1.\n' >&2
  printf 'Global install paths differ per tool and OS; follow guides/global-setup.md for manual steps.\n' >&2
  exit 1
fi

if [ -z "$TARGET" ]; then
  fail "--target <path> is required (see --help)"
fi

case "$COMPONENTS" in
  all|skills-only) ;;
  *) fail "--components must be all|skills-only" ;;
esac

case "$PRESET" in
  pro|plus|custom) ;;
  *) fail "--preset must be pro|plus|custom" ;;
esac

if [ ! -d "$TARGET" ]; then
  fail "target must be an existing directory: $TARGET"
fi

TARGET_DIR=$(cd -- "$TARGET" && pwd -P)
if [ "$TARGET_DIR" = "$SCRIPT_DIR" ]; then
  fail "target must differ from the setup source directory"
fi

if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 is required on PATH"
fi

if [ ! -f "$SCRIPT_DIR/scripts/generate.py" ]; then
  fail "setup source is missing: $SCRIPT_DIR/scripts/generate.py"
fi

# Prompt helper with distinct defaults: fresh installs default yes,
# overwrites default no. --yes bypasses all prompts.
ask_yes_no() {
  prompt_msg=$1
  default_is_yes=$2
  if [ "$AUTO_YES" -eq 1 ]; then
    return 0
  fi
  if [ "$default_is_yes" = "yes" ]; then
    hint='[Y/n]'
  else
    hint='[y/N]'
  fi
  while :; do
    printf '%s %s ' "$prompt_msg" "$hint"
    if ! IFS= read -r reply; then
      printf '\nSetup cancelled: input ended before completion.\n' >&2
      exit 1
    fi
    case "$reply" in
      y|Y|yes|YES|Yes) return 0 ;;
      n|N|no|NO|No) return 1 ;;
      '')
        if [ "$default_is_yes" = "yes" ]; then return 0; else return 1; fi
        ;;
      *) printf '%s\n' 'Please answer yes or no.' ;;
    esac
  done
}

# List staged files that would overwrite existing target files.
list_overwrites() {
  staged=$1
  live=$2
  entry=$(basename "$staged")
  if [ -f "$staged" ]; then
    if [ -e "$live" ] || [ -L "$live" ]; then
      printf '%s\n' "$entry"
    fi
    return 0
  fi
  find "$staged" -type f -print | while IFS= read -r staged_file; do
    rel=${staged_file#"$staged"/}
    live_file=$live/$rel
    if [ -e "$live_file" ] || [ -L "$live_file" ]; then
      printf '%s\n' "$entry/$rel"
    fi
  done
}

show_overwrites() {
  staged=$1
  live=$2
  found=$(list_overwrites "$staged" "$live")
  if [ -z "$found" ]; then
    return 0
  fi
  printf '%s\n' 'WARNING: the following existing files will be overwritten:'
  printf '%s\n' "$found" | sed 's/^/  - /'
}

# List type mismatches (file vs dir, symlink in the way) between stage and target.
list_type_conflicts() {
  staged=$1
  live=$2
  find "$staged" -type f -print | while IFS= read -r staged_file; do
    rel=${staged_file#"$staged"/}
    live_file=$live/$rel
    if { [ -e "$live_file" ] || [ -L "$live_file" ]; } && [ ! -f "$live_file" ]; then
      printf '%s\n' "$rel"
    fi
  done
  find "$staged" -type d -print | while IFS= read -r staged_dir; do
    if [ "$staged_dir" = "$staged" ]; then
      continue
    fi
    rel=${staged_dir#"$staged"/}
    live_dir=$live/$rel
    if { [ -e "$live_dir" ] || [ -L "$live_dir" ]; } && [ ! -d "$live_dir" ]; then
      printf '%s\n' "$rel"
    fi
  done
}

STAGE_BASE=""
STAGE_DIR=""
cleanup_stage() {
  if [ -n "$STAGE_BASE" ] && [ -d "$STAGE_BASE" ]; then
    rm -rf "$STAGE_BASE"
  fi
}

N_NEW=0
N_UPDATED=0
N_SKIPPED=0
install_entry() {
  entry_name=$1
  staged_path=$2
  live_path=$3
  if [ ! -e "$staged_path" ]; then
    printf 'Error: staged source is missing: %s\n' "$staged_path" >&2
    exit 1
  fi
  if [ -e "$live_path" ] || [ -L "$live_path" ]; then
    if [ ! -L "$live_path" ] && [ -d "$staged_path" ] && [ -d "$live_path" ]; then
      inner_link=$(find "$live_path" -type l -print -quit)
      if [ -n "$inner_link" ]; then
        printf 'Skipped %s: existing target contains a symbolic link (%s).\n' "$entry_name" "$inner_link" >&2
        N_SKIPPED=$((N_SKIPPED + 1))
        return 0
      fi
      type_clash=$(list_type_conflicts "$staged_path" "$live_path")
      if [ -n "$type_clash" ]; then
        printf 'Skipped %s: source and target types conflict at:\n' "$entry_name" >&2
        printf '%s\n' "$type_clash" | sed 's/^/  /' >&2
        N_SKIPPED=$((N_SKIPPED + 1))
        return 0
      fi
    elif [ -L "$live_path" ]; then
      printf '%s\n' 'WARNING: the following symbolic link will be replaced:'
      printf '  - %s\n' "$entry_name"
    elif { [ -d "$staged_path" ] && [ ! -d "$live_path" ]; } || { [ -f "$staged_path" ] && [ ! -f "$live_path" ]; }; then
      printf 'Skipped %s: source and target types are incompatible.\n' "$entry_name" >&2
      N_SKIPPED=$((N_SKIPPED + 1))
      return 0
    else
      show_overwrites "$staged_path" "$live_path"
    fi
    if ! ask_yes_no "Update $entry_name? Only listed paths are replaced." "no"; then
      printf 'Skipped %s (existing target left unchanged).\n' "$entry_name"
      N_SKIPPED=$((N_SKIPPED + 1))
      return 0
    fi
    if [ -L "$live_path" ]; then
      rm "$live_path"
      cp -R "$staged_path" "$live_path"
    elif [ -d "$staged_path" ] && [ -d "$live_path" ]; then
      if [ "$entry_name" = ".codex" ] && [ -f "$staged_path/config.toml" ]; then
        for child in "$staged_path"/*; do
          if [ ! -e "$child" ] && [ ! -L "$child" ]; then
            continue
          fi
          cname=$(basename "$child")
          if [ "$cname" = "config.toml" ]; then
            continue
          fi
          cp -R "$child" "$live_path"/
        done
        for child in "$staged_path"/.*; do
          if [ ! -e "$child" ] && [ ! -L "$child" ]; then
            continue
          fi
          cname=$(basename "$child")
          case "$cname" in
            .|..) continue ;;
            config.toml) continue ;;
          esac
          cp -R "$child" "$live_path"/
        done
        set -- python3 "$SCRIPT_DIR/scripts/generate.py" \
          --merge-config-toml "$live_path/config.toml" \
          --preset "$PRESET"
        if [ -n "$ORCHESTRATOR_MODEL" ]; then set -- "$@" --orchestrator-model "$ORCHESTRATOR_MODEL"; fi
        if [ -n "$EXPLORER_MODEL" ]; then set -- "$@" --explorer-model "$EXPLORER_MODEL"; fi
        if [ -n "$WORKER_MODEL" ]; then set -- "$@" --worker-model "$WORKER_MODEL"; fi
        if [ -n "$TESTER_MODEL" ]; then set -- "$@" --tester-model "$TESTER_MODEL"; fi
        if [ -n "$REVIEWER_MODEL" ]; then set -- "$@" --reviewer-model "$REVIEWER_MODEL"; fi
        if [ -n "$RESEARCHER_MODEL" ]; then set -- "$@" --researcher-model "$RESEARCHER_MODEL"; fi
        if [ -n "$PLANNER_MODEL" ]; then set -- "$@" --planner-model "$PLANNER_MODEL"; fi
        if [ -n "$ORACLE_MODEL" ]; then set -- "$@" --oracle-model "$ORACLE_MODEL"; fi
        if [ -n "$DESIGNER_MODEL" ]; then set -- "$@" --designer-model "$DESIGNER_MODEL"; fi
        if [ -n "$REVIEWER_EFFORT" ]; then set -- "$@" --reviewer-effort "$REVIEWER_EFFORT"; fi
        merge_status=$("$@") || fail ".codex/config.toml merge failed"
        printf '%s\n' ".codex/config.toml: $merge_status"
        N_UPDATED=$((N_UPDATED + 1))
        return 0
      fi
      cp -R "$staged_path"/. "$live_path"/
    elif [ -f "$staged_path" ] && { [ -f "$live_path" ] || [ ! -e "$live_path" ]; }; then
      if [ "$entry_name" = "AGENTS.md" ] && [ -f "$live_path" ] && [ ! -L "$live_path" ]; then
        agents_status=$(python3 "$SCRIPT_DIR/scripts/generate.py" --merge-agents-md "$live_path" --agents-template "$SCRIPT_DIR/templates/AGENTS.md") || fail "AGENTS.md merge failed"
        printf '%s\n' "AGENTS.md: $agents_status"
        N_UPDATED=$((N_UPDATED + 1))
        return 0
      fi
      cp "$staged_path" "$live_path"
    else
      rm -rf "$live_path"
      cp -R "$staged_path" "$live_path"
    fi
    printf 'Updated %s.\n' "$entry_name"
    N_UPDATED=$((N_UPDATED + 1))
  else
    if ! ask_yes_no "Install $entry_name?" "yes"; then
      printf 'Skipped %s.\n' "$entry_name"
      N_SKIPPED=$((N_SKIPPED + 1))
      return 0
    fi
    cp -R "$staged_path" "$live_path"
    printf 'Installed %s.\n' "$entry_name"
    N_NEW=$((N_NEW + 1))
  fi
}

STAGE_BASE=$(mktemp -d)
STAGE_DIR=$STAGE_BASE/stage
mkdir -p "$STAGE_DIR"
trap cleanup_stage EXIT

set -- python3 "$SCRIPT_DIR/scripts/generate.py" \
  --target "$STAGE_DIR" \
  --tools "$TOOLS" \
  --components "$COMPONENTS" \
  --preset "$PRESET"
if [ -n "$EXTRA" ]; then set -- "$@" --extra "$EXTRA"; fi
if [ -n "$ORCHESTRATOR_MODEL" ]; then set -- "$@" --orchestrator-model "$ORCHESTRATOR_MODEL"; fi
if [ -n "$EXPLORER_MODEL" ]; then set -- "$@" --explorer-model "$EXPLORER_MODEL"; fi
if [ -n "$WORKER_MODEL" ]; then set -- "$@" --worker-model "$WORKER_MODEL"; fi
if [ -n "$TESTER_MODEL" ]; then set -- "$@" --tester-model "$TESTER_MODEL"; fi
if [ -n "$REVIEWER_MODEL" ]; then set -- "$@" --reviewer-model "$REVIEWER_MODEL"; fi
if [ -n "$RESEARCHER_MODEL" ]; then set -- "$@" --researcher-model "$RESEARCHER_MODEL"; fi
if [ -n "$PLANNER_MODEL" ]; then set -- "$@" --planner-model "$PLANNER_MODEL"; fi
if [ -n "$ORACLE_MODEL" ]; then set -- "$@" --oracle-model "$ORACLE_MODEL"; fi
if [ -n "$DESIGNER_MODEL" ]; then set -- "$@" --designer-model "$DESIGNER_MODEL"; fi
if [ -n "$REVIEWER_EFFORT" ]; then set -- "$@" --reviewer-effort "$REVIEWER_EFFORT"; fi
"$@"

for staged_top in "$STAGE_DIR"/.* "$STAGE_DIR"/*; do
  if [ ! -e "$staged_top" ] && [ ! -L "$staged_top" ]; then
    continue
  fi
  top_name=$(basename "$staged_top")
  case "$top_name" in
    .|..) continue ;;
  esac
  install_entry "$top_name" "$staged_top" "$TARGET_DIR/$top_name"
done

printf '\nSetup complete: %s new, %s updated, %s skipped in %s.\n' "$N_NEW" "$N_UPDATED" "$N_SKIPPED" "$TARGET_DIR"
printf 'Options: tools=%s components=%s preset=%s\n' "$TOOLS" "$COMPONENTS" "$PRESET"
if [ "$COMPONENTS" = "skills-only" ]; then
  printf '%s\n' 'Next: skills installed only. Verify a SKILL.md under each tool dir, then re-run with --components all to add agent roles and AGENTS.md.'
else
  printf '%s\n' 'Next: verify AGENTS.md plus per-tool agents/ and skills/team-orchestrator/SKILL.md, then commit the result into the target repo.'
fi
