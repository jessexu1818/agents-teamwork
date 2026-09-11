#!/usr/bin/env python3
"""Doctor-style checker for generated output (stdlib only)."""
import argparse
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import generate


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Verify generated team configs.")
    p.add_argument("--target", required=True, help="generated output directory")
    p.add_argument("--templates", default=str(HERE.parent / "templates"),
                   help="templates directory")
    p.add_argument("--quiet", action="store_true", help="exit code only")
    return p.parse_args(argv)


def skill_rel(tool):
    if tool in ("codex", "agents", "antigravity"):
        return Path(".agents/skills/team-orchestrator/SKILL.md")
    if tool == "copilot":
        return Path(".github/skills/team-orchestrator/SKILL.md")
    if tool == "windsurf":
        return Path(".windsurf/skills/team-orchestrator/SKILL.md")
    if tool == "qoder":
        return Path(".qoder/skills/team-orchestrator/SKILL.md")
    if tool == "trae":
        return Path(".trae/skills/team-orchestrator/SKILL.md")
    return Path(f".{tool}/skills/team-orchestrator/SKILL.md")


def role_rel(tool, role):
    if tool == "codex":
        return Path(f".codex/agents/{role}.toml")
    if tool == "antigravity":
        return Path(f".agent/agents/{role}.md")
    if tool == "copilot":
        return Path(f".github/agents/{role}.agent.md")
    if tool == "windsurf":
        return Path(f".windsurf/rules/{role}.md")
    if tool == "qoder":
        return Path(f".qoder/agents/{role}.md")
    if tool == "trae":
        return Path(f".trae/rules/{role}.md")
    return Path(f".{tool}/agents/{role}.md")


def find_line(text, needle, default=1):
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return default


def main(argv=None):
    args = parse_args(argv)
    target = Path(args.target)
    templates = Path(args.templates)
    errors = []

    def err(path, line, msg):
        errors.append(f"{path}:{line}: {msg}")

    if not target.is_dir():
        print(f"{target}:1: target directory missing", file=sys.stderr)
        return 1

    # 1. template frontmatter required keys
    for p in sorted((templates / "roles").glob("*.md")):
        try:
            meta, _ = generate.parse_frontmatter(p.read_text(encoding="utf-8"))
        except Exception as e:
            err(p, 1, f"frontmatter read error: {e}")
            continue
        for key in ("name", "description", "model", "reasoning"):
            if key not in meta:
                err(p, 1, f"template {p.name} missing required key '{key}'")

    # 2. skill inventory for every tool
    seen_skill = {}
    for tool in generate.ALL_TOOLS:
        rel = skill_rel(tool)
        seen_skill.setdefault(str(rel), []).append(tool)
    for rel_str, tools in seen_skill.items():
        fp = target / rel_str
        if not fp.is_file():
            err(fp, 1, f"missing expected skill file for {','.join(tools)}")

    # 3. core role inventory for every tool
    for tool in generate.ALL_TOOLS:
        for role in generate.CORE_ROLES:
            fp = target / role_rel(tool, role)
            if not fp.is_file():
                err(fp, 1, f"missing expected role file '{role}' for tool '{tool}'")

    # 4. SKILL.md frontmatter checks
    for rel_str in seen_skill:
        fp = target / rel_str
        if not fp.is_file():
            continue
        try:
            text = fp.read_text(encoding="utf-8")
        except Exception as e:
            err(fp, 1, f"read error: {e}")
            continue
        if "{{" in text:
            err(fp, find_line(text, "{{"), "unresolved placeholder '{{' in OUTPUT")
        meta, _ = generate.parse_frontmatter(text)
        for key in ("name", "description"):
            if key not in meta or not meta[key]:
                err(fp, 1, f"SKILL.md missing required key '{key}'")
        desc = meta.get("description", "")
        if desc and not desc.startswith("Use when"):
            err(fp, find_line(text, "description:"), "SKILL.md description must start with 'Use when'")

    # 5. role .md output checks: model non-empty, no placeholders
    for tool in generate.ALL_TOOLS:
        roles = list(generate.CORE_ROLES)
        for extra in generate.EXTRA_CHOICES:
            rp = target / role_rel(tool, extra)
            if rp.is_file() and rp.suffix == ".md":
                roles.append(extra)
        for role in roles:
            fp = target / role_rel(tool, role)
            if not fp.is_file() or fp.suffix != ".md":
                continue
            try:
                text = fp.read_text(encoding="utf-8")
            except Exception as e:
                err(fp, 1, f"read error: {e}")
                continue
            if "{{" in text:
                err(fp, find_line(text, "{{"), "unresolved placeholder '{{' in OUTPUT")
                continue
            meta, _ = generate.parse_frontmatter(text)
            # transformed outputs (copilot/windsurf/qoder) keep only a subset;
            # require model where present, require full keys otherwise
            if tool in ("copilot", "windsurf", "qoder"):
                if "description" not in meta:
                    err(fp, 1, f"role {role} missing required key 'description'")
            else:
                for key in ("name", "description", "model"):
                    if key not in meta or not meta[key]:
                        err(fp, 1, f"role {role} missing required key '{key}'")
            if "model" in meta and not meta["model"]:
                err(fp, find_line(text, "model:"), f"role {role} has empty model")

    # 6. toml parse + model checks
    for fp in sorted(target.rglob("*.toml")):
        try:
            text = fp.read_text(encoding="utf-8")
        except Exception as e:
            err(fp, 1, f"read error: {e}")
            continue
        if "{{" in text:
            err(fp, find_line(text, "{{"), "unresolved placeholder '{{' in OUTPUT")
        try:
            data = tomllib.loads(text)
        except Exception as e:
            err(fp, 1, f"toml parse error: {e}")
            continue
        if fp.parent.name == "agents" and fp.parent.parent.name == ".codex":
            if not data.get("model"):
                err(fp, 1, "codex role has empty model")

    # 7. global placeholder sweep for stray files (AGENTS.md, configs)
    for fp in sorted(target.rglob("*")):
        if not fp.is_file() or fp.suffix in (".toml", ".md"):
            continue
        try:
            text = fp.read_text(encoding="utf-8")
        except Exception:
            continue
        if "{{" in text:
            err(fp, find_line(text, "{{"), "unresolved placeholder '{{' in OUTPUT")

    if errors:
        if not args.quiet:
            for e in errors:
                print(e)
            print(f"FAIL: {len(errors)} issue(s) in {target}")
        return 1
    if not args.quiet:
        print(f"OK: {target} passed all checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
