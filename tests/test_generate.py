"""Tests for scripts/generate.py — 7-tool rendering from templates/."""
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GEN = REPO / "scripts" / "generate.py"

CORE_ROLES = ["explorer", "worker", "tester", "reviewer", "researcher"]
EXTRA_ROLES = ["planner", "oracle", "designer"]


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
