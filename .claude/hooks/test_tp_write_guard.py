"""Tests for the TP-write PreToolUse guard (tp_write_guard.py)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import tp_write_guard as guard  # noqa: E402


RAW_POST = (
    "await fetch('https://tpapi.trainingpeaks.com/plans/v1/plans/672143/workouts', "
    "{method: 'POST', body: JSON.stringify(w)})"
)
BLESSED_POST = "/* GG_BLESSED_TP_WRITE */ " + RAW_POST
GET_ONLY = (
    "const r = await fetch('https://tpapi.trainingpeaks.com/plans/v1/plans/672143', "
    "{credentials:'include'}); const body = await r.text();"
)


def kernel_post(publisher_root) -> str:
    """A wrapper that loads a REAL kernel script under <root>/steve-publish/
    and also carries a raw write of its own (the legacy kernel-flow shape)."""
    kernel_dir = publisher_root / "steve-publish"
    kernel_dir.mkdir(parents=True, exist_ok=True)
    (kernel_dir / "apply_plan.js").write_text(RAW_POST)
    return (
        f"state.src = fs.readFileSync('{kernel_dir / 'apply_plan.js'}', 'utf8'); "
        + RAW_POST
    )


AXIOS_POST = "await axios.post('https://peakswaresb.com/rx/activity/v1', body)"
DELETE_CALL = (
    "await fetch('https://tpapi.trainingpeaks.com/plans/v1/plans/672143/workouts/9', "
    "{method: 'DELETE'})"
)

# Confirmed-bypass probes from the adversarial review (sol-commit-wave-review.md).
QUOTED_METHOD_KEY_NO_SPACE = (
    "await fetch('https://tpapi.trainingpeaks.com/plans/v1/plans/1', "
    '{"method":"POST", body: JSON.stringify(w)})'
)
RELATIVE_TP_PATH_NO_HOST = (
    'fetch("/fitness/v1/athletes/1/x", {method:"POST"})'
)


def _is_deny(result: dict) -> bool:
    return (result.get("hookSpecificOutput") or {}).get("permissionDecision") == "deny"


class TestEvaluate:
    def test_raw_tp_post_denied(self):
        result = guard.evaluate("mcp__playwriter__execute", {"code": RAW_POST})
        assert _is_deny(result)
        assert "permissionDecisionReason" in result["hookSpecificOutput"]

    def test_raw_tp_delete_denied(self):
        result = guard.evaluate("mcp__playwriter__execute", {"code": DELETE_CALL})
        assert _is_deny(result)

    def test_axios_style_post_denied(self):
        result = guard.evaluate("mcp__playwriter__execute", {"code": AXIOS_POST})
        assert _is_deny(result)

    def test_blessed_marker_bypasses_guard(self):
        result = guard.evaluate("mcp__playwriter__execute", {"code": BLESSED_POST})
        assert not _is_deny(result)

    def test_kernel_publish_read_bypasses_guard(self, tmp_path, monkeypatch):
        root = tmp_path / "TrainingPeaksPublisher"
        monkeypatch.setenv(guard.PUBLISHER_ROOT_ENV, str(root))
        result = guard.evaluate("mcp__playwriter__execute", {"code": kernel_post(root)})
        assert not _is_deny(result)

    def test_kernel_string_without_real_file_does_not_bypass(self, tmp_path, monkeypatch):
        # Was a bare substring match: a comment naming a -publish/ path
        # used to switch the whole guard off.
        monkeypatch.setenv(guard.PUBLISHER_ROOT_ENV, str(tmp_path / "TrainingPeaksPublisher"))
        code = ("// fs.readFileSync('/tmp/TrainingPeaksPublisher/zz-publish/x.js')\n"
                + RAW_POST)
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert _is_deny(result)

    def test_kernel_path_outside_publisher_root_not_trusted(self, tmp_path, monkeypatch):
        monkeypatch.setenv(guard.PUBLISHER_ROOT_ENV, str(tmp_path / "real-root"))
        elsewhere = tmp_path / "TrainingPeaksPublisher" / "steve-publish"
        elsewhere.mkdir(parents=True)
        (elsewhere / "apply_plan.js").write_text(RAW_POST)
        code = f"const src = fs.readFileSync('{elsewhere / 'apply_plan.js'}', 'utf8');"
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert _is_deny(result)

    def test_get_request_not_denied(self):
        result = guard.evaluate("mcp__playwriter__execute", {"code": GET_ONLY})
        assert not _is_deny(result)
        assert result == {}

    def test_write_verb_without_tp_host_not_denied(self):
        code = "await fetch('https://example.com/api', {method: 'POST'})"
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert not _is_deny(result)

    def test_tp_host_without_write_verb_not_denied(self):
        code = "await fetch('https://tpapi.trainingpeaks.com/plans/v1/plans/672143')"
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert not _is_deny(result)

    def test_non_playwriter_tool_ignored(self):
        result = guard.evaluate("Bash", {"code": RAW_POST, "command": RAW_POST})
        assert result == {}

    def test_missing_code_field_does_not_crash(self):
        result = guard.evaluate("mcp__playwriter__execute", {})
        assert result == {}

    # ---------------------------------------------- widened write-verb detection
    def test_quoted_method_key_no_space_denied(self):
        # Confirmed bypass: '"method":"POST"' (quoted key, zero spaces
        # around the colon) previously slipped past WRITE_VERB_RE.
        result = guard.evaluate(
            "mcp__playwriter__execute", {"code": QUOTED_METHOD_KEY_NO_SPACE})
        assert _is_deny(result)

    def test_single_quoted_method_key_denied(self):
        code = "fetch(url, {'method': 'PUT', body})" + " // https://tpapi.trainingpeaks.com/plans/v1/x"
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert _is_deny(result)

    def test_patch_verb_denied(self):
        code = 'fetch("https://tpapi.trainingpeaks.com/plans/v1/x", {method: "PATCH"})'
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert _is_deny(result)

    def test_xhr_open_post_denied(self):
        code = (
            "var xhr = new XMLHttpRequest(); "
            'xhr.open("POST", "https://tpapi.trainingpeaks.com/plans/v1/x"); xhr.send(body);'
        )
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert _is_deny(result)

    def test_xhr_open_single_quoted_denied(self):
        code = (
            "var xhr = new XMLHttpRequest(); "
            "xhr.open('PUT', 'https://tpapi.trainingpeaks.com/plans/v1/x'); xhr.send(body);"
        )
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert _is_deny(result)

    def test_send_beacon_denied(self):
        code = 'navigator.sendBeacon("https://tpapi.trainingpeaks.com/plans/v1/x", body)'
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert _is_deny(result)

    # -------------------------------------------------- widened host/path detection
    def test_relative_tp_api_path_no_host_denied(self):
        # Confirmed bypass: a host-less /fitness/v1 path (page-context code
        # runs against whatever origin it's already on) previously slipped
        # past TP_HOST_RE, which required a literal tpapi.trainingpeaks.com.
        result = guard.evaluate(
            "mcp__playwriter__execute", {"code": RELATIVE_TP_PATH_NO_HOST})
        assert _is_deny(result)

    def test_relative_fitness_v6_path_denied(self):
        code = 'fetch("/fitness/v6/athletes/1/workouts", {method: "POST"})'
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert _is_deny(result)

    def test_relative_rx_activity_path_denied(self):
        code = 'fetch("/rx/activity/1", {method: "PUT"})'
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert _is_deny(result)

    def test_relative_exerciselibrary_path_denied(self):
        code = 'fetch("/exerciselibrary/1", {method: "DELETE"})'
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert _is_deny(result)

    def test_relative_calendarnote_path_denied(self):
        code = 'fetch("/calendarNote/1", {method: "PUT"})'
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert _is_deny(result)

    def test_any_trainingpeaks_subdomain_denied(self):
        # No hardcoded "tpapi." prefix requirement -- ANY subdomain counts.
        code = 'fetch("https://app.trainingpeaks.com/plans/v1/x", {method: "POST"})'
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert _is_deny(result)

    def test_bare_peakswaresb_domain_denied(self):
        code = 'fetch("https://peakswaresb.com/plans/v1/x", {method: "POST"})'
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert _is_deny(result)

    def test_relative_path_without_write_verb_not_denied(self):
        code = 'fetch("/fitness/v1/athletes/1/workouts")'
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert not _is_deny(result)

    def test_non_tp_relative_path_not_denied(self):
        code = 'fetch("/api/v1/other-thing", {method: "POST"})'
        result = guard.evaluate("mcp__playwriter__execute", {"code": code})
        assert not _is_deny(result)


class TestMain:
    def test_main_reads_stdin_and_prints_deny_json(self, monkeypatch, capsys):
        import io
        import json

        payload = json.dumps({
            "tool_name": "mcp__playwriter__execute",
            "tool_input": {"code": RAW_POST},
        })
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_main_confirmed_bypass_probe_quoted_key_denied(self, monkeypatch, capsys):
        import io
        import json

        payload = json.dumps({
            "tool_name": "mcp__playwriter__execute",
            "tool_input": {"code": QUOTED_METHOD_KEY_NO_SPACE},
        })
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_main_confirmed_bypass_probe_relative_path_denied(self, monkeypatch, capsys):
        import io
        import json

        payload = json.dumps({
            "tool_name": "mcp__playwriter__execute",
            "tool_input": {"code": RELATIVE_TP_PATH_NO_HOST},
        })
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_main_get_only_allowed(self, monkeypatch, capsys):
        import io
        import json

        payload = json.dumps({
            "tool_name": "mcp__playwriter__execute",
            "tool_input": {"code": GET_ONLY},
        })
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out == {}

    def test_main_non_tp_host_allowed(self, monkeypatch, capsys):
        import io
        import json

        payload = json.dumps({
            "tool_name": "mcp__playwriter__execute",
            "tool_input": {"code": "await fetch('https://example.com/api', {method: 'POST'})"},
        })
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out == {}

    def test_main_other_tool_allowed(self, monkeypatch, capsys):
        import io
        import json

        payload = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": RAW_POST},
        })
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out == {}

    # ------------------------------------------------------------- fail closed
    def test_main_handles_empty_stdin_by_failing_closed(self, monkeypatch, capsys):
        import io
        import json

        monkeypatch.setattr(sys, "stdin", io.StringIO(""))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "failing closed" in out["hookSpecificOutput"]["permissionDecisionReason"]

    def test_main_handles_malformed_json_by_failing_closed(self, monkeypatch, capsys):
        import io
        import json

        monkeypatch.setattr(sys, "stdin", io.StringIO("{not valid json"))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_main_handles_json_array_payload_by_failing_closed(self, monkeypatch, capsys):
        import io
        import json

        monkeypatch.setattr(sys, "stdin", io.StringIO("[1, 2, 3]"))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_main_missing_code_field_fails_closed(self, monkeypatch, capsys):
        import io
        import json

        payload = json.dumps({
            "tool_name": "mcp__playwriter__execute",
            "tool_input": {},
        })
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_main_non_string_code_fails_closed(self, monkeypatch, capsys):
        import io
        import json

        payload = json.dumps({
            "tool_name": "mcp__playwriter__execute",
            "tool_input": {"code": 12345},
        })
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_main_missing_tool_name_with_tp_write_code_fails_closed_to_deny(self, monkeypatch, capsys):
        # No tool_name at all -- the guard must not assume this is some
        # other, unguarded tool; it evaluates the code defensively.
        import io
        import json

        payload = json.dumps({"tool_input": {"code": RAW_POST}})
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_main_non_string_tool_name_fails_closed(self, monkeypatch, capsys):
        import io
        import json

        payload = json.dumps({"tool_name": 123, "tool_input": {"code": RAW_POST}})
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

    def test_main_non_object_tool_input_fails_closed(self, monkeypatch, capsys):
        import io
        import json

        payload = json.dumps({
            "tool_name": "mcp__playwriter__execute", "tool_input": "not-an-object",
        })
        monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
        rc = guard.main()
        out = json.loads(capsys.readouterr().out)
        assert rc == 0
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


# ---------------------------------------------------------------- loaded scripts
# Security review of PR #260: a wrapper that reads a script from disk and
# evaluates it carries no write signal in ``code``. The guard resolves the
# literal script path and scans the loaded file too. Round 2 of that review
# (Opus, 2026-09-19) pinned the trusted scripts to resolved absolute paths,
# made the kernel hatch require a real file, and denied non-literal loads.
import os


class TestLoadedScripts:
    T = "mcp__playwriter__execute"

    def _wrapper(self, path) -> str:
        return (
            f"const src = fs.readFileSync('{path}', 'utf8'); "
            "await page.evaluate(src);"
        )

    def _reason(self, result) -> str:
        return result["hookSpecificOutput"]["permissionDecisionReason"]

    # --- scanning of loaded files
    def test_loaded_script_with_tp_write_denied(self, tmp_path):
        script = tmp_path / "apply.js"
        script.write_text(RAW_POST)
        result = guard.evaluate(self.T, {"code": self._wrapper(script)})
        assert _is_deny(result)
        assert "apply.js" in self._reason(result)

    def test_loaded_script_read_only_allowed(self, tmp_path):
        script = tmp_path / "read.js"
        script.write_text(GET_ONLY)
        result = guard.evaluate(self.T, {"code": self._wrapper(script)})
        assert not _is_deny(result)

    def test_loaded_json_payload_ignored(self, tmp_path):
        payload = tmp_path / "plan_payload_final.json"
        payload.write_text('{"method": "POST", "url": "/plans/v1/plans"}')
        code = f"const p = JSON.parse(fs.readFileSync('{payload}', 'utf8'));"
        result = guard.evaluate(self.T, {"code": code})
        assert not _is_deny(result)

    def test_blessed_marker_inside_loaded_file_does_not_bypass(self, tmp_path):
        script = tmp_path / "sneaky.js"
        script.write_text(BLESSED_POST)
        result = guard.evaluate(self.T, {"code": self._wrapper(script)})
        assert _is_deny(result)

    def test_three_link_chain_scanned(self, tmp_path):
        c = tmp_path / "c.js"; c.write_text(RAW_POST)
        b = tmp_path / "b.js"; b.write_text(self._wrapper(c))
        a = tmp_path / "a.js"; a.write_text(self._wrapper(b))
        result = guard.evaluate(self.T, {"code": self._wrapper(a)})
        assert _is_deny(result)
        assert "c.js" in self._reason(result)

    def test_cyclic_loads_terminate(self, tmp_path):
        a = tmp_path / "a.js"; b = tmp_path / "b.js"
        a.write_text(self._wrapper(b)); b.write_text(self._wrapper(a))
        result = guard.evaluate(self.T, {"code": self._wrapper(a)})
        assert not _is_deny(result)

    def test_wrapper_write_still_denied_alongside_clean_load(self, tmp_path):
        script = tmp_path / "read.js"
        script.write_text(GET_ONLY)
        result = guard.evaluate(self.T, {"code": self._wrapper(script) + " " + RAW_POST})
        assert _is_deny(result)

    # --- path shapes
    def test_template_literal_path_denied(self):
        code = "const src = fs.readFileSync(`${dir}/upsert.js`, 'utf8'); await page.evaluate(src);"
        result = guard.evaluate(self.T, {"code": code})
        assert _is_deny(result)
        assert "template literal" in self._reason(result)

    def test_home_interpolation_expands(self, tmp_path, monkeypatch):
        monkeypatch.setenv("HOME", str(tmp_path))
        script = tmp_path / "x.js"
        script.write_text(RAW_POST)
        code = "const src = fs.readFileSync(`${process.env.HOME}/x.js`, 'utf8');"
        result = guard.evaluate(self.T, {"code": code})
        assert _is_deny(result)
        assert "x.js" in self._reason(result)

    def test_missing_script_denied(self, tmp_path):
        result = guard.evaluate(self.T, {"code": self._wrapper(tmp_path / "nope.js")})
        assert _is_deny(result)
        assert "could not be read" in self._reason(result)

    def test_relative_path_resolves_against_project_dir(self, tmp_path, monkeypatch):
        (tmp_path / "tools").mkdir()
        (tmp_path / "tools" / "adhoc.js").write_text(RAW_POST)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        result = guard.evaluate(self.T, {"code": self._wrapper("tools/adhoc.js")})
        assert _is_deny(result)

    def test_variable_path_denied(self, tmp_path):
        script = tmp_path / "evil.js"; script.write_text(RAW_POST)
        code = f"const P = '{script}'; const src = fs.readFileSync(P, 'utf8');"
        result = guard.evaluate(self.T, {"code": code})
        assert _is_deny(result)
        assert "non-literal" in self._reason(result)

    def test_concatenated_path_denied(self, tmp_path):
        code = f"const src = fs.readFileSync('{tmp_path}/' + 'evil.js', 'utf8');"
        result = guard.evaluate(self.T, {"code": code})
        assert _is_deny(result)

    def test_path_join_denied(self, tmp_path):
        code = f"const src = fs.readFileSync(require('path').join('{tmp_path}', 'evil.js'), 'utf8');"
        result = guard.evaluate(self.T, {"code": code})
        assert _is_deny(result)

    def test_extensionless_require_resolves_js(self, tmp_path):
        (tmp_path / "evil.js").write_text(RAW_POST)
        result = guard.evaluate(self.T, {"code": f"require('{tmp_path / 'evil'}')"})
        assert _is_deny(result)

    def test_dynamic_import_scanned(self, tmp_path):
        script = tmp_path / "mod.js"; script.write_text(RAW_POST)
        result = guard.evaluate(self.T, {"code": f'await import("{script}")'})
        assert _is_deny(result)

    def test_file_url_fetch_denied(self, tmp_path):
        code = f"const src = await (await fetch('file://{tmp_path}/evil.js')).text();"
        result = guard.evaluate(self.T, {"code": code})
        assert _is_deny(result)

    def test_commented_out_load_ignored(self):
        code = ("// TODO: was fs.readFileSync('tools/old_packet.js')\n"
                "const x = await page.evaluate(() => window.__WEEKLY_PACKET__);")
        result = guard.evaluate(self.T, {"code": code})
        assert not _is_deny(result)

    def test_block_comment_load_ignored(self):
        code = "/* fs.readFileSync('tools/old.js') */ const y = 1;"
        result = guard.evaluate(self.T, {"code": code})
        assert not _is_deny(result)

    def test_script_name_in_plain_string_ignored(self):
        code = "console.log('run upsert_draft_plan.js next')"
        result = guard.evaluate(self.T, {"code": code})
        assert result == {}

    # --- trusted scripts (pinned by resolved absolute path)
    def test_trusted_packet_script_allowed_under_project_dir(self, tmp_path, monkeypatch):
        (tmp_path / "tools").mkdir()
        # The real packet script carries a POST (TP's PMC reporting query).
        (tmp_path / "tools" / "tp_weekly_packet.js").write_text(
            "call('/fitness/v1/athletes/1/reporting/performancedata/a/b', {method: 'POST'})")
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        result = guard.evaluate(self.T, {"code": self._wrapper("tools/tp_weekly_packet.js")})
        assert not _is_deny(result)
        assert "trusted loaded script" in result.get("systemMessage", "")

    def test_trusted_upsert_script_allowed_under_publisher_root(self, tmp_path, monkeypatch):
        root = tmp_path / "TrainingPeaksPublisher"
        shared = root / "plan-builds" / "_shared"
        shared.mkdir(parents=True)
        (shared / "upsert_draft_plan.js").write_text(RAW_POST)
        monkeypatch.setenv(guard.PUBLISHER_ROOT_ENV, str(root))
        result = guard.evaluate(self.T, {"code": self._wrapper(shared / "upsert_draft_plan.js")})
        assert not _is_deny(result)

    def test_trusted_suffix_outside_pinned_roots_denied(self, tmp_path, monkeypatch):
        # Round-2 blocker: a suffix match was satisfiable by any file the
        # agent wrote. Same name, wrong root -> scanned -> denied.
        monkeypatch.setenv(guard.PUBLISHER_ROOT_ENV, str(tmp_path / "real-root"))
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "real-project"))
        for rel in ("anydir/tools/tp_weekly_packet.js",
                    "anydir/TrainingPeaksPublisher/plan-builds/_shared/upsert_draft_plan.js"):
            fake = tmp_path / rel
            fake.parent.mkdir(parents=True, exist_ok=True)
            fake.write_text(RAW_POST)
            result = guard.evaluate(self.T, {"code": self._wrapper(fake)})
            assert _is_deny(result), rel

    def test_dotdot_traversal_resolved_before_trust_check(self, tmp_path, monkeypatch):
        monkeypatch.setenv(guard.PUBLISHER_ROOT_ENV, str(tmp_path / "real-root"))
        fake = tmp_path / "x" / "tools" / "tp_weekly_packet.js"
        fake.parent.mkdir(parents=True)
        fake.write_text(RAW_POST)
        code = self._wrapper(tmp_path / "x" / ".." / "x" / "tools" / "tp_weekly_packet.js")
        result = guard.evaluate(self.T, {"code": code})
        assert _is_deny(result)

    def test_same_content_under_untrusted_name_denied(self, tmp_path, monkeypatch):
        root = tmp_path / "TrainingPeaksPublisher"
        shared = root / "plan-builds" / "_shared"
        shared.mkdir(parents=True)
        (shared / "upsert_draft_plan_v2.js").write_text(RAW_POST)
        monkeypatch.setenv(guard.PUBLISHER_ROOT_ENV, str(root))
        result = guard.evaluate(
            self.T, {"code": self._wrapper(shared / "upsert_draft_plan_v2.js")})
        assert _is_deny(result)

    def test_kernel_script_that_loads_ad_hoc_writer_denied(self, tmp_path, monkeypatch):
        root = tmp_path / "TrainingPeaksPublisher"
        monkeypatch.setenv(guard.PUBLISHER_ROOT_ENV, str(root))
        evil = tmp_path / "evil.js"; evil.write_text(RAW_POST)
        code = kernel_post(root) + " " + self._wrapper(evil)
        result = guard.evaluate(self.T, {"code": code})
        assert _is_deny(result)
