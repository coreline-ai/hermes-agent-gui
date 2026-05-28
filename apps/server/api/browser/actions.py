from __future__ import annotations

import base64
import html
import re
import urllib.parse
import urllib.request

from .allowlist import validate_url
from .session import BrowserSession

_DUMMY_PNG = base64.b64encode(b"hermes-browser-screenshot").decode("ascii")


class _ValidatingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-apply browser URL policy to every redirect target.

    ``urllib`` follows redirects automatically. Without this hook, an allowed
    public URL could redirect to a private address after the initial allowlist
    check and bypass the browser SSRF guard.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        target = urllib.parse.urljoin(req.full_url, newurl.replace(" ", "%20"))
        ok, err = validate_url(target)
        if not ok:
            raise PermissionError(err or "redirect_not_allowed")
        return super().redirect_request(req, fp, code, msg, headers, target)


_OPENER = urllib.request.build_opener(_ValidatingRedirectHandler)


def navigate(sess: BrowserSession, url: str) -> dict:
    ok, err = validate_url(url)
    if not ok:
        raise PermissionError(err or "domain_not_allowed")
    req = urllib.request.Request(url, headers={"User-Agent": "hermes-agent-gui/phase23"})
    with _OPENER.open(req, timeout=5) as resp:
        raw = resp.read(512_000)
        charset = resp.headers.get_content_charset() or "utf-8"
        sess.html = raw.decode(charset, errors="replace")
        sess.url = resp.geturl()
    return {"session_id": sess.id, "url": sess.url, "title": title(sess), "screenshot_b64": _DUMMY_PNG}


def title(sess: BrowserSession) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", sess.html, re.I | re.S)
    return html.unescape(" ".join(m.group(1).split())) if m else ""


def extract(sess: BrowserSession, selector: str) -> dict:
    if selector == "title":
        value = title(sess)
        if not value:
            raise LookupError("selector_not_found")
        return {"selector": selector, "text": value}
    if selector.startswith("text="):
        needle = selector[5:]
        if needle in sess.html:
            return {"selector": selector, "text": needle}
    raise LookupError("selector_not_found")


def screenshot(sess: BrowserSession) -> dict:
    return {"session_id": sess.id, "screenshot_b64": _DUMMY_PNG, "url": sess.url}
