"""Differential AGENTS.md merge tests (RED first)."""
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GEN = REPO / "scripts" / "generate.py"
SETUP = REPO / "setup.sh"
TEMPLATE = (REPO / "templates" / "AGENTS.md").read_text(encoding="utf-8")

BEGIN = "<!-- agents-teamwork:begin -->"
END = "<!-- agents-teamwork:end -->"

sys.path.insert(0, str(REPO / "scripts"))
import generate  # noqa: E402
import importlib  # noqa: E402

importlib.reload(generate)


def test_identical_block_returns_unchanged():
    first = generate.merge_agents_md(None, TEMPLATE)
    assert BEGIN in first and END in first
    second = generate.merge_agents_md(first, TEMPLATE)
    assert second == first


def test_stale_block_replaced_custom_preserved():
    before = "# My project header\nCustom intro line.\n"
    after = "\n# Footer\nCustom outro.\n"
    old_inner = "OLD STALE TEMPLATE TEXT"
    existing = before + BEGIN + "\n" + old_inner + "\n" + END + after
    merged = generate.merge_agents_md(existing, TEMPLATE)
    assert OLD_INNER_NOT_PRESENT(merged, old_inner)
    assert TEMPLATE.strip() in merged
    assert merged.startswith(before)
    assert merged.endswith(after)
    assert BEGIN in merged and END in merged


def OLD_INNER_NOT_PRESENT(merged, old_inner):
    return old_inner not in merged


def test_no_block_appends_preserving_custom():
    custom = "# My custom AGENTS.md\nSome user rules here.\n"
    merged = generate.merge_agents_md(custom, TEMPLATE)
    assert merged.startswith(custom)
    assert BEGIN in merged and END in merged
    assert TEMPLATE.strip() in merged


def test_no_file_creates_just_block():
    merged = generate.merge_agents_md(None, TEMPLATE)
    assert BEGIN in merged and END in merged
    assert TEMPLATE.strip() in merged


def test_cli_merge_mode_creates_and_reports_unchanged():
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "AGENTS.md"
        r1 = subprocess.run(
            [sys.executable, str(GEN), "--merge-agents-md", str(f)],
            capture_output=True, text=True, cwd=str(REPO),
        )
        assert r1.returncode == 0, f"stderr: {r1.stderr}\nstdout: {r1.stdout}"
        assert f.exists()
        assert BEGIN in f.read_text(encoding="utf-8")
        assert r1.stdout.strip().split()[-1] in ("written", "merged")
        r2 = subprocess.run(
            [sys.executable, str(GEN), "--merge-agents-md", str(f)],
            capture_output=True, text=True, cwd=str(REPO),
        )
        assert r2.returncode == 0, f"stderr: {r2.stderr}\nstdout: {r2.stdout}"
        assert "unchanged" in r2.stdout


def test_direct_generate_preserves_custom():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        t.mkdir()
        custom = "# Custom user content\nDo not delete me.\n"
        (t / "AGENTS.md").write_text(custom, encoding="utf-8")
        r = subprocess.run(
            [sys.executable, str(GEN), "--target", str(t),
             "--tools", "agents", "--components", "all"],
            capture_output=True, text=True, cwd=str(REPO),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}\nstdout: {r.stdout}"
        content = (t / "AGENTS.md").read_text(encoding="utf-8")
        assert custom in content
        assert BEGIN in content and END in content
        assert TEMPLATE.strip() in content


def test_setup_sh_preserves_custom_agents_md():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        t.mkdir()
        custom = "# User project notes\nKeep me safe.\n"
        (t / "AGENTS.md").write_text(custom, encoding="utf-8")
        r = subprocess.run(
            ["sh", str(SETUP), "--target", str(t),
             "--tools", "agents", "--components", "all", "--yes"],
            capture_output=True, text=True, cwd=str(REPO),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}\nstdout: {r.stdout}"
        content = (t / "AGENTS.md").read_text(encoding="utf-8")
        assert custom in content
        assert BEGIN in content and END in content
