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

ALL_TOOLS = ["claude", "codex", "codebuddy", "kiro", "opencode", "cursor", "agents"]
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


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Render team-orchestrator templates to per-tool configs.",
        epilog=("presets: pro (orch+reviewer gpt-5, rest gpt-5-mini, effort low); "
                "plus (all mini except reviewer gpt-5, effort low); "
                "custom (all mini, effort low). Override with --*-model flags."),
    )
    p.add_argument("--tools", default="all",
                   help="all or csv of claude,codex,codebuddy,kiro,opencode,cursor,agents")
    p.add_argument("--extra", default="",
                   help="csv subset of planner,oracle,designer (default empty)")
    p.add_argument("--components", default="all", choices=["all", "skills-only"])
    p.add_argument("--target", required=True, help="output directory")
    p.add_argument("--preset", default="pro", choices=["pro", "plus", "custom"])
    for r in ["orchestrator", "explorer", "worker", "tester", "reviewer",
              "researcher", "planner", "oracle", "designer"]:
        p.add_argument(f"--{r}-model", default=None, help=f"override {r} model")
    p.add_argument("--reviewer-effort", default=None, help="override reviewer effort")
    return p.parse_args(argv)


def resolve_tools(s):
    s = s.strip()
    if s == "all":
        return list(ALL_TOOLS)
    tools = [t.strip() for t in s.split(",") if t.strip()]
    for t in tools:
        if t not in ALL_TOOLS:
            sys.exit(f"unknown tool: {t}")
    return tools


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
    if meta.get("sandbox"):
        lines.append(f"sandbox_mode = {toml_str(meta['sandbox'])}")
    if meta.get("temperature"):
        lines.append(f"temperature = {meta['temperature']}")
    safe = body.replace('"""', '\\"\\"\\"')
    lines.append(f'developer_instructions = """{safe}"""')
    return "\n".join(lines) + "\n"


def main(argv=None):
    args = parse_args(argv)
    tools = resolve_tools(args.tools)
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
        (target / "AGENTS.md").write_text((TEMPLATE_ROOT / "AGENTS.md").read_text())

    print(f"Generated {n_roles} roles + {n_skills} skills for [{','.join(tools)}] "
          f"to {target} (preset={args.preset}, components={args.components})")


if __name__ == "__main__":
    main()
