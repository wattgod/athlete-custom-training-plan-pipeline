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
KERNEL_POST = (
    "state.src = fs.readFileSync('/Users/coach/TrainingPeaksPublisher/steve-publish/"
    "apply_plan.js', 'utf8'); " + RAW_POST
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

    def test_kernel_publish_read_bypasses_guard(self):
        result = guard.evaluate("mcp__playwriter__execute", {"code": KERNEL_POST})
        assert not _is_deny(result)

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
