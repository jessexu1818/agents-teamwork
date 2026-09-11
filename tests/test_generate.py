"""Tests for scripts/generate.py — 7-tool rendering from templates/."""
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GEN = REPO / "scripts" / "generate.py"

CORE_ROLES = ["explorer", "worker", "tester", "reviewer", "researcher"]
EXTRA_ROLES = ["planner", "oracle", "designer"]

NEW_TOOLS = ["antigravity", "copilot", "windsurf", "qoder", "trae"]

SKILL_PATHS = {
    "antigravity": ".agents/skills/team-orchestrator/SKILL.md",
    "copilot": ".github/skills/team-orchestrator/SKILL.md",
    "windsurf": ".windsurf/skills/team-orchestrator/SKILL.md",
    "qoder": ".qoder/skills/team-orchestrator/SKILL.md",
    "trae": ".trae/skills/team-orchestrator/SKILL.md",
}

ROLE_GLOBS = {
    "antigravity": ".agent/agents/*.md",
    "copilot": ".github/agents/*.agent.md",
    "windsurf": ".windsurf/rules/*.md",
    "qoder": ".qoder/agents/*.md",
    "trae": ".trae/rules/*.md",
}


def run_gen(target: Path, *args: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(GEN), "--target", str(target), *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))


def test_skills_only_outputs_only_skill_no_roles():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "claude,agents", "--components", "skills-only",
                    "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        assert (t / ".claude" / "skills" / "team-orchestrator" / "SKILL.md").exists()
        assert (t / ".agents" / "skills" / "team-orchestrator" / "SKILL.md").exists()
        # no role files
        assert not list(t.glob(".claude/agents/*"))
        assert not list(t.glob(".agents/agents/*"))
        # no AGENTS.md, no codex config
        assert not (t / "AGENTS.md").exists()
        assert not (t / ".codex" / "config.toml").exists()


def test_full_core_roles_default_extra_empty():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "claude", "--components", "all",
                    "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        files = sorted(p.stem for p in (t / ".claude" / "agents").glob("*.md"))
        assert files == sorted(CORE_ROLES)
        assert (t / "AGENTS.md").exists()


def test_full_with_extra_outputs_eight():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "claude", "--components", "all",
                    "--extra", "planner,oracle,designer", "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        files = sorted(p.stem for p in (t / ".claude" / "agents").glob("*.md"))
        assert files == sorted(CORE_ROLES + EXTRA_ROLES)


def test_no_placeholders_remain():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "all", "--components", "all",
                    "--extra", "planner,oracle,designer", "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        for p in t.rglob("*"):
            if p.is_file():
                text = p.read_text(encoding="utf-8", errors="ignore")
                assert "{{" not in text, f"placeholder left in {p}"


def test_codex_toml_parses_and_has_model():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "codex", "--components", "all",
                    "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        tomls = list((t / ".codex" / "agents").glob("*.toml"))
        assert len(tomls) == len(CORE_ROLES)
        for p in tomls:
            data = tomllib.loads(p.read_text(encoding="utf-8"))
            assert "model" in data, f"missing model in {p}"
            assert data["model"], f"empty model in {p}"
        cfg = tomllib.loads((t / ".codex" / "config.toml").read_text(encoding="utf-8"))
        assert "model" in cfg


def test_idempotent_run_twice_same_output():
    import tempfile
    import hashlib
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        args = ["--tools", "claude,codex", "--components", "all",
                "--extra", "planner", "--preset", "plus"]
        r1 = run_gen(t, *args)
        assert r1.returncode == 0, f"stderr: {r1.stderr}"

        def snapshot():
            h = {}
            for p in sorted(t.rglob("*")):
                if p.is_file():
                    h[str(p.relative_to(t))] = hashlib.sha256(
                        p.read_bytes()).hexdigest()
            return h
        first = snapshot()
        r2 = run_gen(t, *args)
        assert r2.returncode == 0, f"stderr: {r2.stderr}"
        assert snapshot() == first


def test_role_to_toml_escapes_backslash():
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    import generate
    import importlib
    importlib.reload(generate)
    body = 'path C:\\path\\x and quote """ end'
    toml_text = generate.role_to_toml(
        {"name": "t", "description": "d", "model": "m"}, body)
    data = tomllib.loads(toml_text)
    assert data["developer_instructions"] == body


def test_empty_tools_exits_nonzero():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "", "--components", "all",
                    "--preset", "pro")
        assert r.returncode != 0


@pytest.mark.parametrize("tool", NEW_TOOLS)
def test_new_tools_skills_only_yields_skill_no_roles(tool):
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", tool, "--components", "skills-only",
                    "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        assert (t / SKILL_PATHS[tool]).exists(), f"missing skill for {tool}"
        assert not list(t.glob(ROLE_GLOBS[tool])), f"role files leaked for {tool}"


@pytest.mark.parametrize("tool", NEW_TOOLS)
def test_new_tools_full_run_core_and_extra_roles(tool):
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", tool, "--components", "all",
                    "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        assert len(list(t.glob(ROLE_GLOBS[tool]))) == len(CORE_ROLES)
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", tool, "--components", "all",
                    "--extra", "planner,oracle,designer", "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        assert len(list(t.glob(ROLE_GLOBS[tool]))) == len(CORE_ROLES + EXTRA_ROLES)


def test_copilot_agent_frontmatter_model_no_sandbox():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "copilot", "--components", "all",
                    "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        p = t / ".github" / "agents" / "explorer.agent.md"
        assert p.exists()
        text = p.read_text(encoding="utf-8")
        assert "model:" in text
        assert "sandbox" not in text


def test_windsurf_rule_has_trigger_model_decision():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "windsurf", "--components", "all",
                    "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        p = t / ".windsurf" / "rules" / "explorer.md"
        assert p.exists()
        assert "trigger: model_decision" in p.read_text(encoding="utf-8")


def test_qoder_tools_readonly_vs_write():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "qoder", "--components", "all",
                    "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        exp = (t / ".qoder" / "agents" / "explorer.md").read_text(encoding="utf-8")
        wrk = (t / ".qoder" / "agents" / "worker.md").read_text(encoding="utf-8")
        exp_tools = next(l for l in exp.splitlines() if l.startswith("tools:"))
        wrk_tools = next(l for l in wrk.splitlines() if l.startswith("tools:"))
        assert "Edit" not in exp_tools and "Write" not in exp_tools
        assert "Edit" in wrk_tools and "Write" in wrk_tools


def test_skill_category_routing_table_and_resolution_priority():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "agents", "--components", "all",
                    "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        text = (t / ".agents" / "skills" / "team-orchestrator" / "SKILL.md").read_text(encoding="utf-8")
        assert "Category routing" in text
        assert "Resolution priority" in text
        for cat in ["quick", "deep", "ultrabrain", "visual"]:
            assert any("|" in line and cat in line for line in text.splitlines()), \
                f"missing table row for category {cat}"


def test_skill_tool_restrictions_deny_matrix():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "agents", "--components", "all",
                    "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        text = (t / ".agents" / "skills" / "team-orchestrator" / "SKILL.md").read_text(encoding="utf-8")
        assert ("Tool restrictions" in text or "Deny matrix" in text)
        for role in ["explorer", "reviewer", "researcher", "oracle", "designer"]:
            assert role in text, f"missing read-only role {role}"
        low = text.lower()
        assert "write" in low and "edit" in low


def test_codex_reviewer_toml_has_reasoning_effort():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "codex", "--components", "all",
                    "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        text = (t / ".codex" / "agents" / "reviewer.toml").read_text(encoding="utf-8")
        assert "model_reasoning_effort" in text


def test_role_templates_have_reasoning_key():
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    import generate
    import importlib
    importlib.reload(generate)
    for p in (REPO / "templates" / "roles").glob("*.md"):
        meta, _ = generate.parse_frontmatter(p.read_text(encoding="utf-8"))
        assert "reasoning" in meta, f"missing reasoning in {p.name}"
