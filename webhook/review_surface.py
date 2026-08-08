"""Escaped, dependency-free HTML for the Phase 2 coach review surface."""

from __future__ import annotations

import json
from html import escape
from typing import Any, Dict, Iterable

from fulfillment_state import approval_matches_release


def _e(value: Any) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def _value(value: Any, unit: str | None = None) -> str:
    if isinstance(value, (dict, list)):
        rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)
    elif value is None:
        rendered = "null"
    elif isinstance(value, bool):
        rendered = "true" if value else "false"
    else:
        rendered = str(value)
    suffix = f" {_e(unit)}" if unit else ""
    return f'<pre class="value">{_e(rendered)}{suffix}</pre>'


def _cards(items: Iterable[Dict[str, Any]], *, controls: str = "") -> str:
    cards = []
    for item in items:
        item_id = _e(item.get("item_id"))
        control = ""
        if controls == "waiver" and item.get("waivable"):
            control = (
                '<label class="choice"><input type="checkbox" name="waive_item" '
                f'value="{item_id}"> Waive this blocker</label>'
            )
        elif controls == "waiver":
            control = (
                '<p class="remediation"><strong>Required remediation:</strong> '
                + _e(item.get("remediation") or "Fix and regenerate.") + "</p>"
            )
        elif controls in {"required", "fact", "soft"}:
            label = {
                "required": "I confirm this reviewed value",
                "fact": "I reviewed this sealed fact",
                "soft": "Confirm this optional item",
            }[controls]
            required = " required" if controls in {"required", "fact"} else ""
            control = (
                '<label class="choice"><input type="checkbox" name="confirm_item" '
                f'value="{item_id}"{required}> {_e(label)}</label>'
            )
        policy = ""
        if item.get("type") == "blocker":
            policy = (
                '<span class="pill danger">'
                + ("waivable with reason" if item.get("waivable")
                   else "non-waivable")
                + "</span>"
            )
        disposition = ""
        if item.get("disposition"):
            disposition = (
                f'<div><dt>Disposition</dt><dd>{_e(item.get("disposition"))}</dd></div>'
            )
        cards.append(
            '<article class="card">'
            f'<div class="card-head"><code>{item_id}</code>{policy}</div>'
            f'<p>{_e(item.get("message"))}</p>'
            + _value(item.get("value"), item.get("display_unit"))
            + '<dl class="meta">'
            f'<div><dt>Source</dt><dd>{_e(item.get("source"))}</dd></div>'
            f'<div><dt>Basis</dt><dd>{_e(item.get("basis"))}</dd></div>'
            f'<div><dt>Sensitivity</dt><dd>{_e(item.get("sensitivity"))}</dd></div>'
            f'<div><dt>Revision</dt><dd>{_e(item.get("revision"))}</dd></div>'
            + disposition + '</dl>' + control + '</article>'
        )
    return "".join(cards) or '<p class="empty">None.</p>'


def render_bootstrap(nonce: str) -> str:
    """Generic login shell. It contains no order- or athlete-derived data."""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Coach review sign-in</title></head>
<body><main><h1>Coach review</h1><p id="status">Opening your secure review session…</p>
<noscript>This secure review link requires JavaScript for the one-time sign-in.</noscript></main>
<script nonce="{_e(nonce)}">(function(){{
  const token = new URLSearchParams(window.location.hash.slice(1)).get('token');
  const status = document.getElementById('status');
  history.replaceState(null, '', window.location.pathname);
  if (!token) {{ status.textContent = 'Open the signed link from the coach notification.'; return; }}
  const form = document.createElement('form'); form.method = 'post'; form.action = window.location.pathname + '/session';
  const input = document.createElement('input'); input.type = 'hidden'; input.name = 'token'; input.value = token;
  form.appendChild(input); document.body.appendChild(form); form.submit();
}})();</script></body></html>"""


_STYLE = """
:root{color-scheme:light;--ink:#17231d;--muted:#607067;--paper:#f5f2eb;--card:#fff;--line:#d9d6ce;--accent:#1f6849;--danger:#9f3029}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.5 system-ui,-apple-system,sans-serif}
main{width:min(980px,calc(100% - 32px));margin:32px auto 80px}h1{font-size:clamp(1.8rem,4vw,3rem);margin:.15em 0}h2{margin:2rem 0 .75rem}
.eyebrow,.meta,small{color:var(--muted)}.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin:20px 0}.summary div,.card,.action{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}.summary dt,.meta dt{font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}.summary dd,.meta dd{margin:3px 0;overflow-wrap:anywhere}.card{margin:10px 0}.card-head{display:flex;justify-content:space-between;gap:12px;align-items:center}.pill{border-radius:99px;padding:3px 9px;font-size:.78rem}.danger{background:#f8dfdc;color:var(--danger)}.value{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f5f2;padding:12px;border-radius:8px;font-size:.86rem}.meta{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px}.meta div{min-width:0}.choice{display:block;margin-top:14px;padding:12px;border:1px solid var(--line);border-radius:8px}.choice input{width:18px;height:18px;vertical-align:-3px;margin-right:8px}.remediation,.error{border-left:4px solid var(--danger);padding:10px 12px;background:#fff2f0}.success{border-left:4px solid var(--accent);padding:10px 12px;background:#edf8f1}.waiver-reason{width:100%;min-height:88px;padding:10px;font:inherit}.button{display:inline-block;border:0;border-radius:8px;padding:12px 18px;background:var(--accent);color:#fff;font-weight:700;text-decoration:none;cursor:pointer}.button.secondary{background:#40544a}.button[disabled]{opacity:.5;cursor:not-allowed}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:20px}.empty{color:var(--muted)}code{overflow-wrap:anywhere}@media(max-width:560px){main{width:min(100% - 20px,980px);margin-top:18px}.card-head{align-items:flex-start;flex-direction:column}}
"""


def render_review_page(
    state: Dict[str, Any], *, csrf_token: str, download_available: bool = False,
    error: str = "",
) -> str:
    status = str(state.get("status") or "")
    authoritative = approval_matches_release(state)
    release_labeled = status in {"APPROVED", "APPLIED", "CONFIRMED"}
    invalid_approval = release_labeled and not authoritative
    items = (
        (state.get("approval") or {}).get("confirmations") or []
        if authoritative else state.get("review_items") or []
    )
    by_type = {
        item_type: [item for item in items if item.get("type") == item_type]
        for item_type in ("blocker", "required_confirmation", "soft_confirmation", "verified_fact")
    }
    non_waivable = any(
        not item.get("waivable") for item in by_type["blocker"]
    )
    error_html = f'<p class="error" role="alert">{_e(error)}</p>' if error else ""
    download_html = (
        '<button class="button secondary" type="submit" '
        f'formaction="/review/{_e(state.get("order_id"))}/bundle" '
        'formmethod="post" formnovalidate>Download sealed review bundle</button>'
        if download_available
        else '<p class="error">Review download is unavailable; do not approve.</p>'
    )
    blocker_cards = _cards(by_type["blocker"], controls="waiver")
    required_cards = _cards(by_type["required_confirmation"], controls="required")
    soft_cards = _cards(by_type["soft_confirmation"], controls="soft")
    fact_cards = _cards(by_type["verified_fact"], controls="fact")
    waiver_reason = ""
    if any(item.get("waivable") for item in by_type["blocker"]):
        waiver_reason = """
<label for="waiver_reason"><strong>Waiver reason</strong></label>
<textarea class="waiver-reason" id="waiver_reason" name="waiver_reason" placeholder="Record the business or coaching judgment for every waived blocker."></textarea>"""
    approval_form = ""
    if invalid_approval:
        approval_form = """
<p class="error" role="alert"><strong>Approval not authoritative — regenerate/re-approve.</strong> The recorded approval is incomplete, stale, legacy, or not bound to the current release seal. No download or later action is available.</p>"""
    elif not authoritative:
        disabled = " disabled" if non_waivable or not download_available else ""
        approval_form = f"""
<form method="post" action="/review/{_e(state.get('order_id'))}/approve">
<input type="hidden" name="csrf_token" value="{_e(csrf_token)}">
<input type="hidden" name="generation_revision" value="{_e(state.get('generation_revision'))}">
<input type="hidden" name="review_catalog_digest" value="{_e(state.get('review_catalog_digest'))}">
<section><h2>1. Blockers</h2>{blocker_cards}{waiver_reason}</section>
<section><h2>2. Required confirmations</h2>{required_cards}</section>
<section><h2>3. Soft confirmations</h2>{soft_cards}</section>
<section><h2>4. Verified facts</h2>{fact_cards}</section>
<div class="actions">{download_html}<button class="button" type="submit"{disabled}>Approve sealed revision</button></div>
</form>"""
    else:
        approval_form = f"""
<p class="success"><strong>Approved.</strong> This decision is bound to revision {_e(state.get('generation_revision'))}, its release seal, and the values shown below.</p>
<section><h2>Blockers reviewed</h2>{_cards(by_type['blocker'])}</section>
<section><h2>Required confirmations</h2>{_cards(by_type['required_confirmation'])}</section>
<section><h2>Soft confirmations</h2>{_cards(by_type['soft_confirmation'])}</section>
<section><h2>Verified facts</h2>{_cards(by_type['verified_fact'])}</section>
<form method="post" action="/review/{_e(state.get('order_id'))}/bundle">
<input type="hidden" name="csrf_token" value="{_e(csrf_token)}">
<div class="actions">{download_html}</div>
</form>"""

    post_approval = ""
    if authoritative:
        post_approval = """
<section class="action"><h2>Application</h2><p>The sealed revision is approved. Automated platform application, readback verification, guide release, and draft/confirm controls remain disabled until their later rollout phases. Use the established operator-controlled manual procedure.</p></section>"""

    effective_status = (
        "APPROVAL NOT AUTHORITATIVE" if invalid_approval else status
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review order {_e(state.get('order_id'))}</title><style>{_STYLE}</style></head>
<body><main><p class="eyebrow">Coach review · sealed fulfilment</p><h1>Order {_e(state.get('order_id'))}</h1>
<dl class="summary"><div><dt>Status</dt><dd>{_e(effective_status)}</dd></div><div><dt>Athlete</dt><dd>{_e(state.get('athlete_id'))}</dd></div><div><dt>Platform</dt><dd>{_e(state.get('delivery_platform'))}</dd></div><div><dt>Revision</dt><dd>{_e(state.get('generation_revision'))}</dd></div></dl>
{error_html}{approval_form}{post_approval}</main></body></html>"""
