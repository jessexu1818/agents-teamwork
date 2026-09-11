"""Tests for scripts/verify.py — doctor-style output checker."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GEN = REPO / "scripts" / "generate.py"
VERIFY = REPO / "scripts" / "verify.py"

CORE_ROLES = ["explorer", "worker", "tester", "reviewer", "researcher"]


def run_gen(target: Path, *args: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(GEN), "--target", str(target), *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))


def run_verify(target: Path, *args: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(VERIFY), "--target", str(target), *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))


def gen_full(target: Path):
    target.mkdir(parents=True, exist_ok=True)
    r = run_gen(target, "--tools", "all", "--extra", "planner,oracle,designer",
                "--preset", "pro")
    assert r.returncode == 0, f"gen failed: {r.stderr}"


def test_verify_passes_on_fresh_full_output():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        gen_full(t)
        r = run_verify(t)
        assert r.returncode == 0, f"verify failed: {r.stdout}\n{r.stderr}"


def test_verify_fails_when_role_file_missing():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        gen_full(t)
        victim = t / ".claude" / "agents" / "worker.md"
        assert victim.exists()
        victim.unlink()
        r = run_verify(t)
        assert r.returncode != 0
        combined = (r.stdout or "") + (r.stderr or "")
        assert "worker" in combined.lower()
        assert ("missing" in combined.lower() or "not found" in combined.lower()
                or "expected" in combined.lower())


def test_verify_fails_on_corrupted_codex_toml():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        gen_full(t)
        victim = t / ".codex" / "agents" / "worker.toml"
        assert victim.exists()
        victim.write_text("this is = not [ valid toml", encoding="utf-8")
        r = run_verify(t)
        assert r.returncode != 0
        combined = (r.stdout or "") + (r.stderr or "")
        assert "toml" in combined.lower() or "parse" in combined.lower()


def test_verify_fails_on_bad_skill_description():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        gen_full(t)
        # simulate violation via temp copy: rewrite one SKILL.md frontmatter
        skill = t / ".agents" / "skills" / "team-orchestrator" / "SKILL.md"
        assert skill.exists()
        text = skill.read_text(encoding="utf-8")
        assert text.startswith("---")
        parts = text.split("---", 2)
        assert len(parts) >= 3
        body = parts[2]
        bad = ("---\nname: team-orchestrator\n"
               "description: Broken description without required prefix.\n---\n" + body)
        skill.write_text(bad, encoding="utf-8")
        r = run_verify(t)
        assert r.returncode != 0
        combined = (r.stdout or "") + (r.stderr or "")
        assert "use when" in combined.lower() or "description" in combined.lower()
