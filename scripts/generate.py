#!/usr/bin/env python3
"""Generate per-tool agent configs + skills from templates/.

Presets (documented for --help):
  pro: orchestrator=gpt-5, reviewer=gpt-5, explorer/worker/tester/researcher/
       planner/oracle/designer=gpt-5-mini, reviewer-effort=low
  plus: all=gpt-5-mini except reviewer=gpt-5, reviewer-effort=low
  custom: all=gpt-5-mini including reviewer, reviewer-effort=low (override via flags)
"""
import argparse
import re
import sys
import tomllib
from pathlib import Path

ALL_TOOLS = ["claude", "codex", "codebuddy", "kiro", "opencode", "cursor", "agents",
             "antigravity", "copilot", "windsurf", "qoder", "trae"]
CORE_ROLES = ["explorer", "worker", "tester", "reviewer", "researcher"]
EXTRA_CHOICES = ["planner", "oracle", "designer"]

PRO = {
    "orchestrator": "gpt-5", "explorer": "gpt-5-mini", "worker": "gpt-5-mini",
    "tester": "gpt-5-mini", "reviewer": "gpt-5", "researcher": "gpt-5-mini",
    "planner": "gpt-5-mini", "oracle": "gpt-5-mini", "designer": "gpt-5-mini",
    "reviewer_effort": "low",
}
PLUS = {**PRO, "orchestrator": "gpt-5-mini"}
CUSTOM = {k: "gpt-5-mini" for k in PRO if k != "reviewer_effort"} | {"reviewer_effort": "low"}
PRESETS = {"pro": PRO, "plus": PLUS, "custom": CUSTOM}

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "templates"

AGENTS_BEGIN = "<!-- agents-teamwork:begin -->"
AGENTS_END = "<!-- agents-teamwork:end -->"

TOML_BEGIN = "# agents-teamwork:begin"
TOML_END = "# agents-teamwork:end"


def write_if_changed(path, text):
    """Write text to path only when bytes differ (avoids mtime churn).

    Creates parent dirs. Returns True when the file was written,
    False when the existing content was already byte-identical.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    new_bytes = text.encode("utf-8")
    if p.is_file():
        try:
            if p.read_bytes() == new_bytes:
                return False
        except OSError:
            pass
    p.write_bytes(new_bytes)
    return True


def fresh_config_toml(orchestrator, worker):
    """Fresh .codex/config.toml content (valid standalone TOML with markers)."""
    return (f"{TOML_BEGIN}\nmodel = {toml_str(orchestrator)}\n"
            f"[agents]\ndefault_subagent_model = {toml_str(worker)}\n{TOML_END}\n")


def merge_config_toml(existing, orchestrator, worker):
    """TOML-aware merge for .codex/config.toml (line-based surgery only).

    Managed keys (only these two): root `model` and
    `agents.default_subagent_model`. User content is never reformatted;
    tomllib is used for parsing/detection only, insertions are line-based.

    Marker rule: markers only wrap appended multi-line blocks. Single-line
    insertions are unmarked: a later run sees the key present with our value
    -> equals generated -> unchanged (silent); if the user edited it after
    -> conflict -> keep + warn. That lets future runs recognize our values
    without marker comments on every line.

    Returns (new_text, status, warning) where status is one of
    written|unchanged|merged|kept-user-values|left-untouched and warning
    is None or a human-readable string listing kept/conflicting keys.
    """
    fresh_block = fresh_config_toml(orchestrator, worker)
    if existing is None or existing.strip() == "":
        return (fresh_block, "written", None)
    bi = existing.find(TOML_BEGIN)
    if bi != -1:
        ei = existing.find(TOML_END, bi + len(TOML_BEGIN))
        if ei != -1:
            # Marked block: update managed values in place (shape-preserving).
            # Blind full-block replacement would corrupt appended agents-only
            # blocks (model would land inside [mcp] on the next run).
            try:
                mdata = tomllib.loads(existing)
            except Exception:
                return (existing, "left-untouched",
                        "left-untouched: existing config.toml is not valid TOML; leaving unchanged")
            if not isinstance(mdata, dict):
                return (existing, "left-untouched",
                        "left-untouched: existing config.toml is not valid TOML; leaving unchanged")
            before = existing[:bi]
            block = existing[bi:ei + len(TOML_END)]
            after = existing[ei + len(TOML_END):]
            has_model_in_block = bool(re.search(r"^[ \t]*model[ \t]*=", block, re.M))
            has_agents_in_block = bool(re.search(r"^[ \t]*default_subagent_model[ \t]*=", block, re.M))
            new_block_lines = []
            for line in block.splitlines():
                if re.match(r"^[ \t]*model[ \t]*=", line):
                    new_block_lines.append(f"model = {toml_str(orchestrator)}")
                elif re.match(r"^[ \t]*default_subagent_model[ \t]*=", line):
                    new_block_lines.append(f"default_subagent_model = {toml_str(worker)}")
                else:
                    new_block_lines.append(line)
            new_block = "\n".join(new_block_lines)
            merged1 = before + new_block + after
            if "\r\n" in existing:
                merged1 = merged1.replace("\r\n", "\n").replace("\n", "\r\n")
            if merged1 != existing:
                try:
                    tomllib.loads(merged1)
                except Exception:
                    return (existing, "left-untouched",
                            "left-untouched: existing config.toml is not valid TOML; leaving unchanged")
                # Warn only about outside (user-owned) keys we did not touch.
                try:
                    pdata = tomllib.loads(merged1)
                except Exception:
                    pdata = {}
                outside_conflicts = []
                if not has_model_in_block and isinstance(pdata, dict) and "model" in pdata:
                    if pdata.get("model") != orchestrator:
                        outside_conflicts.append("model")
                av = pdata.get("agents") if isinstance(pdata, dict) else None
                if not has_agents_in_block and isinstance(av, dict) and "default_subagent_model" in av:
                    if av.get("default_subagent_model") != worker:
                        outside_conflicts.append("agents.default_subagent_model")
                warn = (f"kept-user-values: keeping existing {', '.join(outside_conflicts)}"
                        if outside_conflicts else None)
                return (merged1, "merged", warn)
            # In-block values already correct: fall through to missing/conflict
            # handling for keys living outside the block (user-owned).
            has_root = "model" in mdata
            agents_val = mdata.get("agents")
            has_agents_key = isinstance(agents_val, dict) and "default_subagent_model" in agents_val
            if not has_root or not has_agents_key:
                # Reuse insertion logic below on the (unchanged) file.
                existing = merged1
                data = mdata
            else:
                outside_conflicts = []
                if not has_model_in_block and mdata.get("model") != orchestrator:
                    outside_conflicts.append("model")
                if not has_agents_in_block and isinstance(agents_val, dict):
                    if agents_val.get("default_subagent_model") != worker:
                        outside_conflicts.append("agents.default_subagent_model")
                if outside_conflicts:
                    return (existing, "kept-user-values",
                            f"kept-user-values: keeping existing {', '.join(outside_conflicts)}")
                return (existing, "unchanged", None)
    try:
        data = tomllib.loads(existing)
    except Exception:
        return (existing, "left-untouched",
                "left-untouched: existing config.toml is not valid TOML; leaving unchanged")
    if not isinstance(data, dict):
        return (existing, "left-untouched",
                "left-untouched: existing config.toml is not valid TOML; leaving unchanged")
    has_root = "model" in data
    agents_val = data.get("agents")
    has_agents_key = isinstance(agents_val, dict) and "default_subagent_model" in agents_val
    cur_root = data.get("model") if has_root else None
    cur_agents = agents_val.get("default_subagent_model") if has_agents_key else None
    missing_root = not has_root
    missing_agents = not has_agents_key
    if not missing_root and not missing_agents:
        if cur_root == orchestrator and cur_agents == worker:
            return (existing, "unchanged", None)
        conflicts = []
        if cur_root != orchestrator:
            conflicts.append("model")
        if cur_agents != worker:
            conflicts.append("agents.default_subagent_model")
        return (existing, "kept-user-values",
                f"kept-user-values: keeping existing {', '.join(conflicts)}")
    conflicts = []
    if has_root and cur_root != orchestrator:
        conflicts.append("model")
    if has_agents_key and cur_agents != worker:
        conflicts.append("agents.default_subagent_model")

    def _is_table_header(line):
        return line.strip().startswith("[")

    def _is_agents_header(line):
        return re.match(r"^\s*\[\s*['\"]?agents['\"]?\s*\]\s*(#.*)?$", line) is not None

    is_crlf = "\r\n" in existing
    lines = existing.splitlines()
    if missing_root:
        idx = None
        for i, ln in enumerate(lines):
            if _is_table_header(ln):
                idx = i
                break
        new_line = f"model = {toml_str(orchestrator)}"
        if idx is None:
            lines.append(new_line)
        else:
            lines.insert(idx, new_line)
    if missing_agents:
        has_agents_table = isinstance(data.get("agents"), dict)
        agents_idx = None
        for i, ln in enumerate(lines):
            if _is_agents_header(ln):
                agents_idx = i
                break
        new_key = f"default_subagent_model = {toml_str(worker)}"
        if agents_idx is not None:
            lines.insert(agents_idx + 1, new_key)
        elif has_agents_table:
            # Table exists but no explicit header found (e.g. inline table):
            # appending a second [agents] block would be invalid TOML.
            # Leave untouched rather than corrupt.
            return (existing, "left-untouched",
                    "left-untouched: existing [agents] table has no header line; leaving unchanged")
        else:
            lines.append(TOML_BEGIN)
            lines.append("[agents]")
            lines.append(new_key)
            lines.append(TOML_END)
    new_text = "\n".join(lines) + "\n"
    if is_crlf:
        new_text = new_text.replace("\r\n", "\n").replace("\n", "\r\n")
    warn = None
    if conflicts:
        warn = f"kept-user-values: keeping existing {', '.join(conflicts)}"
    return (new_text, "merged", warn)


def merge_agents_md(existing: str | None, template: str) -> str:
    inner = template.strip()
    while AGENTS_BEGIN in inner and AGENTS_END in inner:
        inner = inner.split(AGENTS_BEGIN, 1)[1].rsplit(AGENTS_END, 1)[0].strip()
    fresh_block = f"{AGENTS_BEGIN}\n{inner}\n{AGENTS_END}\n"
    fresh_inline = f"{AGENTS_BEGIN}\n{inner}\n{AGENTS_END}"
    if existing is None or existing == "":
        return fresh_block
    bi = existing.find(AGENTS_BEGIN)
    if bi != -1:
        ei = existing.find(AGENTS_END, bi + len(AGENTS_BEGIN))
        if ei != -1:
            before = existing[:bi]
            after = existing[ei + len(AGENTS_END):]
            return before + fresh_inline + after
    if existing.endswith("\n\n"):
        sep = ""
    elif existing.endswith("\n"):
        sep = "\n"
    else:
        sep = "\n\n"
    return existing + sep + fresh_block


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Render team-orchestrator templates to per-tool configs.",
        epilog=("presets: pro (orch+reviewer gpt-5, rest gpt-5-mini, effort low); "
                "plus (all mini except reviewer gpt-5, effort low); "
                "custom (all mini, effort low). Override with --*-model flags."),
    )
    p.add_argument("--tools", default="all",
                   help="all or csv of claude,codex,codebuddy,kiro,opencode,cursor,agents,antigravity,copilot,windsurf,qoder,trae")
    p.add_argument("--extra", default="",
                   help="csv subset of planner,oracle,designer (default empty)")
    p.add_argument("--components", default="all", choices=["all", "skills-only"])
    p.add_argument("--target", required=False, default=None, help="output directory")
    p.add_argument("--merge-agents-md", default=None, help="merge AGENTS.md block into FILE and exit")
    p.add_argument("--merge-config-toml", default=None, help="merge .codex/config.toml keys into FILE and exit")
    p.add_argument("--agents-template", default=None, help="template file for --merge-agents-md (default templates/AGENTS.md)")
    p.add_argument("--preset", default="pro", choices=["pro", "plus", "custom"])
    for r in ["orchestrator", "explorer", "worker", "tester", "reviewer",
              "researcher", "planner", "oracle", "designer"]:
        p.add_argument(f"--{r}-model", default=None, help=f"override {r} model")
    p.add_argument("--reviewer-effort", default=None, help="override reviewer effort")
    args = p.parse_args(argv)
    if args.merge_agents_md is None and args.merge_config_toml is None and not args.target:
        p.error("the following arguments are required: --target")
    return args


def resolve_tools(s):
    s = s.strip()
    if s == "all":
        return list(ALL_TOOLS)
    tools = [t.strip() for t in s.split(",") if t.strip()]
    for t in tools:
        if t not in ALL_TOOLS:
            sys.exit(f"unknown tool: {t}")
    return list(dict.fromkeys(tools))


def resolve_extra(s):
    if not s.strip():
        return []
    extras = [e.strip() for e in s.split(",") if e.strip()]
    for e in extras:
        if e not in EXTRA_CHOICES:
            sys.exit(f"unknown extra role: {e}")
    return extras


def build_models(preset, args):
    m = dict(PRESETS[preset])
    for r in ["orchestrator", "explorer", "worker", "tester", "reviewer",
              "researcher", "planner", "oracle", "designer"]:
        v = getattr(args, f"{r}_model")
        if v:
            m[r] = v
    if args.reviewer_effort:
        m["reviewer_effort"] = args.reviewer_effort
    return m


def substitute(text, models):
    for k, v in models.items():
        tag = "{{" + k.upper() + "_MODEL}}" if k != "reviewer_effort" else "{{REVIEWER_EFFORT}}"
        text = text.replace(tag, v)
    # orchestrator placeholder (future-proof; may not exist in templates yet)
    text = text.replace("{{ORCHESTRATOR_MODEL}}", models["orchestrator"])
    return text


def parse_frontmatter(text):
    """Return (meta dict, body str). Meta values unquoted."""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip().strip('"').strip("'")
        meta[k.strip()] = v
    return meta, parts[2].lstrip("\n")


def toml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def role_to_toml(meta, body):
    lines = []
    lines.append(f"name = {toml_str(meta.get('name', ''))}")
    lines.append(f"description = {toml_str(meta.get('description', ''))}")
    lines.append(f"model = {toml_str(meta.get('model', ''))}")
    if meta.get("reasoning"):
        lines.append(f"model_reasoning_effort = {toml_str(meta['reasoning'])}")
    if meta.get("sandbox"):
        lines.append(f"sandbox_mode = {toml_str(meta['sandbox'])}")
    if meta.get("temperature"):
        lines.append(f"temperature = {meta['temperature']}")
    # Escape backslashes first, then triple-quotes (order matters for valid TOML).
    safe = body.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    lines.append(f'developer_instructions = """{safe}"""')
    return "\n".join(lines) + "\n"


def role_to_copilot_agent(meta, body):
    lines = ["---", f"name: {meta.get('name', '')}",
             f"description: {meta.get('description', '')}",
             f"model: {meta.get('model', '')}", "---", ""]
    if not body.endswith("\n"):
        body += "\n"
    return "\n".join(lines) + body


def role_to_windsurf_rule(meta, body):
    lines = ["---", "trigger: model_decision",
             f"description: {meta.get('description', '')}", "---", ""]
    if not body.endswith("\n"):
        body += "\n"
    return "\n".join(lines) + body


def role_to_qoder_agent(meta, body):
    denied = meta.get("denied_tools", "").lower()
    if "write" in denied or "edit" in denied:
        tools = "Read, Grep, Glob, Bash"
    else:
        tools = "Read, Grep, Glob, Bash, Edit, Write"
    lines = ["---", f"name: {meta.get('name', '')}",
             f"description: {meta.get('description', '')}",
             f"model: {meta.get('model', '')}",
             f"tools: {tools}", "---", ""]
    if not body.endswith("\n"):
        body += "\n"
    return "\n".join(lines) + body


def main(argv=None):
    args = parse_args(argv)
    if args.merge_agents_md is not None:
        tmpl_path = Path(args.agents_template) if args.agents_template else (TEMPLATE_ROOT / "AGENTS.md")
        template_text = tmpl_path.read_text()
        dest = Path(args.merge_agents_md)
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(merge_agents_md(None, template_text))
            print("written")
            return
        existing_text = dest.read_text()
        merged_text = merge_agents_md(existing_text, template_text)
        if merged_text == existing_text:
            print("unchanged")
        else:
            dest.write_text(merged_text)
            print("merged")
        return
    if args.merge_config_toml is not None:
        models = build_models(args.preset, args)
        dest = Path(args.merge_config_toml)
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            text, status, warn = merge_config_toml(None, models["orchestrator"], models["worker"])
            dest.write_text(text, encoding="utf-8")
            print(status)
            if warn:
                print(warn, file=sys.stderr)
            return
        existing_text = dest.read_bytes().decode("utf-8")
        new_text, status, warn = merge_config_toml(
            existing_text, models["orchestrator"], models["worker"])
        if new_text != existing_text:
            dest.write_bytes(new_text.encode("utf-8"))
        print(status)
        if warn:
            print(warn, file=sys.stderr)
        return
    tools = list(dict.fromkeys(resolve_tools(args.tools)))
    if not tools:
        parser = argparse.ArgumentParser()
        parser.error("--tools resolved to empty set")
    extras = resolve_extra(args.extra)
    roles = list(CORE_ROLES) + [e for e in EXTRA_CHOICES if e in extras]
    models = build_models(args.preset, args)
    target = Path(args.target)
    target.mkdir(parents=True, exist_ok=True)

    skill_src = (TEMPLATE_ROOT / "skills" / "team-orchestrator" / "SKILL.md").read_text()
    skill_text = substitute(skill_src, models)
    n_roles = n_skills = 0

    for tool in tools:
        if tool == "codex":
            skill_path = target / ".agents" / "skills" / "team-orchestrator" / "SKILL.md"
            write_if_changed(skill_path, skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / ".codex" / "agents"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    meta, body = parse_frontmatter(substitute(src, models))
                    write_if_changed(adir / f"{role}.toml", role_to_toml(meta, body))
                    n_roles += 1
                cfg_path = target / ".codex" / "config.toml"
                existing_cfg = cfg_path.read_bytes().decode("utf-8") if cfg_path.is_file() else None
                merged_cfg, _, warn = merge_config_toml(
                    existing_cfg, models["orchestrator"], models["worker"])
                if warn:
                    print(warn, file=sys.stderr)
                write_if_changed(cfg_path, merged_cfg)
        elif tool == "antigravity":
            skill_path = target / ".agents" / "skills" / "team-orchestrator" / "SKILL.md"
            write_if_changed(skill_path, skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / ".agent" / "agents"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    write_if_changed(adir / f"{role}.md", substitute(src, models))
                    n_roles += 1
        elif tool == "copilot":
            skill_path = target / ".github" / "skills" / "team-orchestrator" / "SKILL.md"
            write_if_changed(skill_path, skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / ".github" / "agents"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    meta, body = parse_frontmatter(substitute(src, models))
                    write_if_changed(adir / f"{role}.agent.md", role_to_copilot_agent(meta, body))
                    n_roles += 1
        elif tool == "windsurf":
            skill_path = target / ".windsurf" / "skills" / "team-orchestrator" / "SKILL.md"
            write_if_changed(skill_path, skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / ".windsurf" / "rules"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    meta, body = parse_frontmatter(substitute(src, models))
                    write_if_changed(adir / f"{role}.md", role_to_windsurf_rule(meta, body))
                    n_roles += 1
        elif tool == "qoder":
            skill_path = target / ".qoder" / "skills" / "team-orchestrator" / "SKILL.md"
            write_if_changed(skill_path, skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / ".qoder" / "agents"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    meta, body = parse_frontmatter(substitute(src, models))
                    write_if_changed(adir / f"{role}.md", role_to_qoder_agent(meta, body))
                    n_roles += 1
        elif tool == "trae":
            skill_path = target / ".trae" / "skills" / "team-orchestrator" / "SKILL.md"
            write_if_changed(skill_path, skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / ".trae" / "rules"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    write_if_changed(adir / f"{role}.md", substitute(src, models))
                    n_roles += 1
        else:
            skill_path = target / f".{tool}" / "skills" / "team-orchestrator" / "SKILL.md"
            write_if_changed(skill_path, skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / f".{tool}" / "agents"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    write_if_changed(adir / f"{role}.md", substitute(src, models))
                    n_roles += 1

    if args.components == "all":
        (target).mkdir(parents=True, exist_ok=True)
        agents_path = target / "AGENTS.md"
        template_text = (TEMPLATE_ROOT / "AGENTS.md").read_text()
        existing_text = agents_path.read_text() if agents_path.is_file() else None
        write_if_changed(agents_path, merge_agents_md(existing_text, template_text))

    print(f"Generated {n_roles} roles + {n_skills} skills for [{','.join(tools)}] "
          f"to {target} (preset={args.preset}, components={args.components})")


if __name__ == "__main__":
    main()
