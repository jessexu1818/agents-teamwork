"""Ownership marker tests (RED first): never clobber foreign files."""
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GEN = REPO / "scripts" / "generate.py"
SETUP = REPO / "setup.sh"

MD_MARKER = "<!-- agents-teamwork: managed file - safe to overwrite on reinstall -->"
TOML_MARKER = "# agents-teamwork: managed file - safe to overwrite on reinstall"

sys.path.insert(0, str(REPO / "scripts"))
import generate  # noqa: E402
import importlib  # noqa: E402

importlib.reload(generate)


def run_gen(target: Path, *args: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(GEN), "--target", str(target), *args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))


def first_body_line_after_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                rest = lines[i + 1:]
                for ln in rest:
                    if ln.strip() == "":
                        continue
                    return ln.strip()
                return ""
    for ln in lines:
        if ln.strip() == "":
            continue
        return ln.strip()
    return ""


def test_fresh_role_contains_marker():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "claude", "--components", "all", "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        text = (t / ".claude" / "agents" / "worker.md").read_text(encoding="utf-8")
        assert MD_MARKER in text
        assert first_body_line_after_frontmatter(text) == MD_MARKER


def test_fresh_skill_contains_marker():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "claude", "--components", "all", "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        text = (t / ".claude" / "skills" / "team-orchestrator" / "SKILL.md").read_text(encoding="utf-8")
        assert MD_MARKER in text
        assert first_body_line_after_frontmatter(text) == MD_MARKER


def test_fresh_codex_toml_first_line_marker():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "codex", "--components", "all", "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        text = (t / ".codex" / "agents" / "worker.toml").read_text(encoding="utf-8")
        assert text.splitlines()[0].strip() == TOML_MARKER


def test_identical_rerun_unchanged():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        args = ["--tools", "claude", "--components", "all", "--preset", "pro"]
        r1 = run_gen(t, *args)
        assert r1.returncode == 0, f"stderr: {r1.stderr}"
        import hashlib

        def snap():
            return {str(p.relative_to(t)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(t.rglob("*")) if p.is_file()}
        first = snap()
        r2 = run_gen(t, *args)
        assert r2.returncode == 0, f"stderr: {r2.stderr}"
        assert snap() == first


def test_owned_but_stale_gets_updated():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "claude", "--components", "all", "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        p = t / ".claude" / "agents" / "worker.md"
        fresh = p.read_text(encoding="utf-8")
        stale = fresh.replace("Worker", "STALE-WORKER") if "Worker" in fresh else MD_MARKER + "\nstale\n"
        assert stale != fresh
        # keep marker so it counts as ours but stale
        assert MD_MARKER in stale
        p.write_text(stale, encoding="utf-8")
        r2 = run_gen(t, "--tools", "claude", "--components", "all", "--preset", "pro")
        assert r2.returncode == 0, f"stderr: {r2.stderr}"
        assert p.read_text(encoding="utf-8") == fresh


def test_foreign_file_kept_byte_identical_with_warning():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "claude", "--components", "all", "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        p = t / ".claude" / "agents" / "worker.md"
        foreign = "---\nname: worker\ndescription: my custom worker\nmodel: custom-model\n---\n\n# My custom worker\nDo not overwrite me.\n"
        assert MD_MARKER not in foreign
        p.write_text(foreign, encoding="utf-8")
        r2 = run_gen(t, "--tools", "claude", "--components", "all", "--preset", "pro")
        assert r2.returncode == 0, f"stderr: {r2.stderr}"
        assert p.read_bytes().decode("utf-8") == foreign
        assert "kept-user-file" in (r2.stderr or "").lower()


def test_legacy_adopt_unmarked_core_gets_marked():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        r = run_gen(t, "--tools", "claude", "--components", "all", "--preset", "pro")
        assert r.returncode == 0, f"stderr: {r.stderr}"
        p = t / ".claude" / "agents" / "worker.md"
        fresh = p.read_text(encoding="utf-8")
        # legacy = fresh with marker lines stripped
        legacy = "\n".join(l for l in fresh.splitlines() if l.strip() != MD_MARKER) + "\n"
        assert MD_MARKER not in legacy
        assert legacy != fresh
        p.write_text(legacy, encoding="utf-8")
        # is_ours must treat legacy as ours
        assert generate.is_ours(p, fresh) is True
        r2 = run_gen(t, "--tools", "claude", "--components", "all", "--preset", "pro")
        assert r2.returncode == 0, f"stderr: {r2.stderr}"
        assert p.read_text(encoding="utf-8") == fresh


def test_sync_file_cli_kept_and_updated():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        # staged source with marker
        src = d / "src.md"
        src.write_text("---\nname: x\ndescription: d\n---\n" + MD_MARKER + "\nhello\n", encoding="utf-8")
        # foreign live
        live_foreign = d / "live1.md"
        live_foreign.write_text("custom user content\n", encoding="utf-8")
        r = subprocess.run([sys.executable, str(GEN), "--sync-file", str(src), str(live_foreign)],
                           capture_output=True, text=True, cwd=str(REPO))
        assert r.returncode == 0, f"stderr: {r.stderr}\nstdout: {r.stdout}"
        assert "kept" in r.stdout.lower()
        assert live_foreign.read_text(encoding="utf-8") == "custom user content\n"
        # owned stale live
        live_owned = d / "live2.md"
        live_owned.write_text("---\nname: x\ndescription: d\n---\n" + MD_MARKER + "\nstale\n", encoding="utf-8")
        r2 = subprocess.run([sys.executable, str(GEN), "--sync-file", str(src), str(live_owned)],
                            capture_output=True, text=True, cwd=str(REPO))
        assert r2.returncode == 0, f"stderr: {r2.stderr}\nstdout: {r2.stdout}"
        assert "updated" in r2.stdout.lower() or "written" in r2.stdout.lower()
        assert live_owned.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")


def test_setup_sh_e2e_keeps_custom_worker_while_others_install():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        t.mkdir()
        claude_agents = t / ".claude" / "agents"
        claude_agents.mkdir(parents=True)
        windsurf_rules = t / ".windsurf" / "rules"
        windsurf_rules.mkdir(parents=True)
        custom_claude = "# My own worker - do not touch\nCustom content here.\n"
        custom_windsurf = "# My windsurf worker\nKeep me.\n"
        (claude_agents / "worker.md").write_text(custom_claude, encoding="utf-8")
        (windsurf_rules / "worker.md").write_text(custom_windsurf, encoding="utf-8")
        r = subprocess.run(["sh", str(SETUP), "--target", str(t),
                            "--tools", "claude,windsurf", "--components", "all",
                            "--preset", "pro", "--yes"],
                           capture_output=True, text=True, cwd=str(REPO))
        assert r.returncode == 0, f"stderr: {r.stderr}\nstdout: {r.stdout}"
        assert (claude_agents / "worker.md").read_text(encoding="utf-8") == custom_claude
        assert (windsurf_rules / "worker.md").read_text(encoding="utf-8") == custom_windsurf
        combined = (r.stdout or "") + (r.stderr or "")
        assert "kept" in combined.lower()
        # other roles still install
        assert (claude_agents / "explorer.md").exists()
        assert (windsurf_rules / "explorer.md").exists()
