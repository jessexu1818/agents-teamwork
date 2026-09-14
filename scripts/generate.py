#!/usr/bin/env python3
"""Generate per-tool agent configs + skills from templates/.

Presets (documented for --help):
  pro: orchestrator=gpt-5, reviewer=gpt-5, explorer/worker/tester/researcher/
       planner/oracle/designer=gpt-5-mini, reviewer-effort=low
  plus: all=gpt-5-mini except reviewer=gpt-5, reviewer-effort=low
  custom: all=gpt-5-mini including reviewer, reviewer-effort=low (override via flags)
"""
import argparse
import sys
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


def merge_agents_md(existing: str | None, template: str) -> str:
    inner = template.strip()
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
    p.add_argument("--agents-template", default=None, help="template file for --merge-agents-md (default templates/AGENTS.md)")
    p.add_argument("--preset", default="pro", choices=["pro", "plus", "custom"])
    for r in ["orchestrator", "explorer", "worker", "tester", "reviewer",
              "researcher", "planner", "oracle", "designer"]:
        p.add_argument(f"--{r}-model", default=None, help=f"override {r} model")
    p.add_argument("--reviewer-effort", default=None, help="override reviewer effort")
    args = p.parse_args(argv)
    if args.merge_agents_md is None and not args.target:
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
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / ".codex" / "agents"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    meta, body = parse_frontmatter(substitute(src, models))
                    (adir / f"{role}.toml").write_text(role_to_toml(meta, body))
                    n_roles += 1
                cfg = (f"model = {toml_str(models['orchestrator'])}\n"
                       f"[agents]\ndefault_subagent_model = {toml_str(models['worker'])}\n")
                (target / ".codex" / "config.toml").write_text(cfg)
        elif tool == "antigravity":
            skill_path = target / ".agents" / "skills" / "team-orchestrator" / "SKILL.md"
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / ".agent" / "agents"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    (adir / f"{role}.md").write_text(substitute(src, models))
                    n_roles += 1
        elif tool == "copilot":
            skill_path = target / ".github" / "skills" / "team-orchestrator" / "SKILL.md"
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / ".github" / "agents"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    meta, body = parse_frontmatter(substitute(src, models))
                    (adir / f"{role}.agent.md").write_text(role_to_copilot_agent(meta, body))
                    n_roles += 1
        elif tool == "windsurf":
            skill_path = target / ".windsurf" / "skills" / "team-orchestrator" / "SKILL.md"
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / ".windsurf" / "rules"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    meta, body = parse_frontmatter(substitute(src, models))
                    (adir / f"{role}.md").write_text(role_to_windsurf_rule(meta, body))
                    n_roles += 1
        elif tool == "qoder":
            skill_path = target / ".qoder" / "skills" / "team-orchestrator" / "SKILL.md"
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / ".qoder" / "agents"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    meta, body = parse_frontmatter(substitute(src, models))
                    (adir / f"{role}.md").write_text(role_to_qoder_agent(meta, body))
                    n_roles += 1
        elif tool == "trae":
            skill_path = target / ".trae" / "skills" / "team-orchestrator" / "SKILL.md"
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / ".trae" / "rules"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    (adir / f"{role}.md").write_text(substitute(src, models))
                    n_roles += 1
        else:
            skill_path = target / f".{tool}" / "skills" / "team-orchestrator" / "SKILL.md"
            skill_path.parent.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(skill_text)
            n_skills += 1
            if args.components == "all":
                adir = target / f".{tool}" / "agents"
                adir.mkdir(parents=True, exist_ok=True)
                for role in roles:
                    src = (TEMPLATE_ROOT / "roles" / f"{role}.md").read_text()
                    (adir / f"{role}.md").write_text(substitute(src, models))
                    n_roles += 1

    if args.components == "all":
        (target).mkdir(parents=True, exist_ok=True)
        agents_path = target / "AGENTS.md"
        template_text = (TEMPLATE_ROOT / "AGENTS.md").read_text()
        existing_text = agents_path.read_text() if agents_path.is_file() else None
        agents_path.write_text(merge_agents_md(existing_text, template_text))

    print(f"Generated {n_roles} roles + {n_skills} skills for [{','.join(tools)}] "
          f"to {target} (preset={args.preset}, components={args.components})")


if __name__ == "__main__":
    main()
