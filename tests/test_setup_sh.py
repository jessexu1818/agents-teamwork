"""Installer acceptance tests for setup.sh (TASK 6)."""
import subprocess
import tomllib
from pathlib import Path
import tempfile

REPO = Path(__file__).resolve().parent.parent
SETUP = REPO / "setup.sh"


def run_setup(target: Path, *args: str) -> subprocess.CompletedProcess:
    cmd = ["sh", str(SETUP), "--target", str(target), *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))


def test_setup_sh_skills_only_outputs_only_skill_files():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        t.mkdir()
        r = run_setup(t, "--tools", "claude,agents", "--components", "skills-only", "--yes")
        assert r.returncode == 0, f"stderr: {r.stderr}\nstdout: {r.stdout}"
        assert (t / ".claude" / "skills" / "team-orchestrator" / "SKILL.md").exists()
        assert (t / ".agents" / "skills" / "team-orchestrator" / "SKILL.md").exists()
        # Exact file count: 2 SKILL.md files only (verified via RED fail with ==3).
        all_files = [p for p in t.rglob("*") if p.is_file()]
        assert len(all_files) == 2, f"expected exactly 2 files, got {[str(p.relative_to(t)) for p in all_files]}"
        assert all(p.name == "SKILL.md" for p in all_files)
        # no roles
        assert not list((t / ".claude" / "agents").glob("*")) if (t / ".claude" / "agents").exists() else True
        assert not list((t / ".agents" / "agents").glob("*")) if (t / ".agents" / "agents").exists() else True
        # no AGENTS.md, no codex config
        assert not (t / "AGENTS.md").exists()
        assert not (t / ".codex" / "config.toml").exists()


def test_setup_sh_full_codex_outputs_toml_roles_and_config():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        t.mkdir()
        r = run_setup(t, "--tools", "codex", "--components", "all", "--yes")
        assert r.returncode == 0, f"stderr: {r.stderr}\nstdout: {r.stdout}"
        tomls = list((t / ".codex" / "agents").glob("*.toml"))
        assert len(tomls) == 5, f"expected 5 core .toml roles, got {[p.name for p in tomls]}"
        for p in tomls:
            data = tomllib.loads(p.read_text(encoding="utf-8"))
            assert data.get("model"), f"empty model in {p}"
        assert (t / ".codex" / "config.toml").exists()
        cfg = tomllib.loads((t / ".codex" / "config.toml").read_text(encoding="utf-8"))
        assert "model" in cfg
        assert (t / "AGENTS.md").exists()


def test_setup_sh_global_refused_with_guide():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        t.mkdir()
        r = run_setup(t, "--global")
        assert r.returncode != 0
        combined = (r.stdout or "") + (r.stderr or "")
        assert "guides/global-setup.md" in combined
