"""RED-first TOML-aware config.toml merge tests."""
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GEN = REPO / "scripts" / "generate.py"
SETUP = REPO / "setup.sh"

sys.path.insert(0, str(REPO / "scripts"))
import generate  # noqa: E402
import importlib  # noqa: E402

importlib.reload(generate)

ORCH = "gpt-5"
WORKER = "gpt-5-mini"


def test_fresh_write_valid_toml_markers():
    text, status, warn = generate.merge_config_toml(None, ORCH, WORKER)
    assert status == "written"
    assert "# agents-teamwork:begin" in text
    assert "# agents-teamwork:end" in text
    data = tomllib.loads(text)
    assert data["model"] == ORCH
    assert data["agents"]["default_subagent_model"] == WORKER


def test_identical_existing_byte_identical():
    fresh, _, _ = generate.merge_config_toml(None, ORCH, WORKER)
    second, status, warn = generate.merge_config_toml(fresh, ORCH, WORKER)
    assert second == fresh
    assert status == "unchanged"


def test_legacy_bare_equal_unchanged_silent():
    legacy = f'model = "{ORCH}"\n[agents]\ndefault_subagent_model = "{WORKER}"\n'
    new, status, warn = generate.merge_config_toml(legacy, ORCH, WORKER)
    assert new == legacy
    assert status == "unchanged"
    assert warn is None


def test_conflict_keeps_user_values_with_warning():
    existing = f'model = "custom"\n[agents]\ndefault_subagent_model = "{WORKER}"\n'
    new, status, warn = generate.merge_config_toml(existing, ORCH, WORKER)
    assert new == existing
    assert status == "kept-user-values"
    assert warn is not None and "model" in warn


def test_missing_root_model_inserted_before_mcp():
    existing = f'[agents]\ndefault_subagent_model = "{WORKER}"\n[mcp]\ncommand = "x"\n'
    new, status, warn = generate.merge_config_toml(existing, ORCH, WORKER)
    assert status == "merged"
    assert new.index(f'model = "{ORCH}"') < new.index("[mcp]")
    data = tomllib.loads(new)
    assert data["model"] == ORCH
    assert data["mcp"]["command"] == "x"
    assert data["agents"]["default_subagent_model"] == WORKER


def test_missing_agents_key_inserted_after_header():
    existing = f'model = "{ORCH}"\n[agents]\nother = "keep"\n'
    new, status, warn = generate.merge_config_toml(existing, ORCH, WORKER)
    assert status == "merged"
    data = tomllib.loads(new)
    assert data["agents"]["other"] == "keep"
    assert data["agents"]["default_subagent_model"] == WORKER
    lines = new.splitlines()
    hdr = next(i for i, l in enumerate(lines) if l.strip() == "[agents]")
    key = next(i for i, l in enumerate(lines) if "default_subagent_model" in l)
    assert key == hdr + 1


def test_mcp_only_appended_marked_block_parses():
    existing = f'model = "{ORCH}"\n[mcp]\ncommand = "foo"\n'
    new, status, warn = generate.merge_config_toml(existing, ORCH, WORKER)
    assert status == "merged"
    assert "# agents-teamwork:begin" in new
    assert "# agents-teamwork:end" in new
    data = tomllib.loads(new)
    assert data["mcp"]["command"] == "foo"
    assert data["agents"]["default_subagent_model"] == WORKER


def test_invalid_toml_left_untouched():
    existing = "this is = not [ valid toml\n"
    new, status, warn = generate.merge_config_toml(existing, ORCH, WORKER)
    assert new == existing
    assert status == "left-untouched"
    assert warn is not None


def test_stale_marked_block_replaced():
    fresh, _, _ = generate.merge_config_toml(None, ORCH, WORKER)
    stale = fresh.replace(ORCH, "gpt-4")
    assert stale != fresh
    new, status, warn = generate.merge_config_toml(stale, ORCH, WORKER)
    assert new == fresh
    assert status == "merged"
    data = tomllib.loads(new)
    assert data["model"] == ORCH


def test_write_if_changed_skips_identical():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "sub" / "f.txt"
        assert generate.write_if_changed(p, "hello\n") is True
        mtime1 = p.stat().st_mtime_ns
        assert generate.write_if_changed(p, "hello\n") is False
        assert p.stat().st_mtime_ns == mtime1
        assert generate.write_if_changed(p, "bye\n") is True
        assert p.read_text() == "bye\n"


def test_cli_mode_creates_merges_idempotent():
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "config.toml"
        r1 = subprocess.run(
            [sys.executable, str(GEN), "--merge-config-toml", str(f), "--preset", "pro"],
            capture_output=True, text=True, cwd=str(REPO),
        )
        assert r1.returncode == 0, f"stderr: {r1.stderr}\nstdout: {r1.stdout}"
        assert f.exists()
        data = tomllib.loads(f.read_text())
        assert data["model"] == ORCH
        assert r1.stdout.strip().split()[-1] in ("written", "merged")
        r2 = subprocess.run(
            [sys.executable, str(GEN), "--merge-config-toml", str(f), "--preset", "pro"],
            capture_output=True, text=True, cwd=str(REPO),
        )
        assert r2.returncode == 0, f"stderr: {r2.stderr}\nstdout: {r2.stdout}"
        assert "unchanged" in r2.stdout


def test_setup_sh_e2e_preserves_mcp_keeps_model_adds_agents():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        t.mkdir()
        codex = t / ".codex"
        codex.mkdir()
        pre = 'model = "custom"\n[mcp]\ncommand = "keepme"\n'
        (codex / "config.toml").write_text(pre)
        r = subprocess.run(
            ["sh", str(SETUP), "--target", str(t),
             "--tools", "codex", "--components", "all", "--yes"],
            capture_output=True, text=True, cwd=str(REPO),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}\nstdout: {r.stdout}"
        content = (codex / "config.toml").read_text()
        data = tomllib.loads(content)
        assert data["mcp"]["command"] == "keepme"
        assert data["model"] == "custom"
        assert data["agents"]["default_subagent_model"] == WORKER
        combined = (r.stdout or "") + (r.stderr or "")
        assert "keep" in combined.lower() or "kept" in combined.lower() or "custom" in combined.lower() or "model" in combined.lower()


def test_spaced_agents_header_single_table_parses():
    import re
    existing = f'model = "{ORCH}"\n[ agents ]\nother = "keep"\n'
    new, status, warn = generate.merge_config_toml(existing, ORCH, WORKER)
    assert status == "merged"
    data = tomllib.loads(new)
    assert data["agents"]["other"] == "keep"
    assert data["agents"]["default_subagent_model"] == WORKER
    hdrs = [l for l in new.splitlines()
            if re.match(r"^\s*\[\s*['\"]?agents['\"]?\s*\]\s*(#.*)?$", l)]
    assert len(hdrs) == 1


def test_crlf_existing_merged_output_still_crlf():
    existing = f'model = "{ORCH}"\r\n[mcp]\r\ncommand = "x"\r\n'
    new, status, warn = generate.merge_config_toml(existing, ORCH, WORKER)
    assert status == "merged"
    assert "\r\n" in new
    assert "\n" not in new.replace("\r\n", "")
    data = tomllib.loads(new)
    assert data["agents"]["default_subagent_model"] == WORKER


def test_direct_target_run_conflict_warns_on_stderr():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td) / "out"
        codex = t / ".codex"
        codex.mkdir(parents=True)
        (codex / "config.toml").write_text('model = "custom"\n')
        r = subprocess.run(
            [sys.executable, str(GEN), "--target", str(t),
             "--tools", "codex", "--components", "all", "--preset", "pro"],
            capture_output=True, text=True, cwd=str(REPO),
        )
        assert r.returncode == 0, f"stderr: {r.stderr}\nstdout: {r.stdout}"
        assert "kept-user-values" in (r.stderr or "").lower() or "keeping existing" in (r.stderr or "").lower()
