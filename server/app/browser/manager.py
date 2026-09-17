from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
from typing import Awaitable, Callable

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from ..config import Settings, get_settings
from ..models.events import EventType, SentinelEvent, ev

EmitFn = Callable[[SentinelEvent], Awaitable[None]]


def _browser_ready(marker: str) -> None:
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", marker)


class BrowserManager:
    """Owns the real Chromium instance. One browser, isolated contexts per
    session. Every observation and interaction happens against real pages."""

    def __init__(self, settings: Settings | None = None, emit: EmitFn | None = None) -> None:
        self.settings = settings or get_settings()
        self.emit = emit or (lambda e: asyncio.sleep(0))
        _browser_ready(self.settings.browser_binaries_dir)
        self._pw: async_playwright | None = None
        self._browser: Browser | None = None
        self._contexts: dict[str, BrowserContext] = {}
        self._pages: dict[str, Page] = {}
        self._started = False
        self._start_lock = asyncio.Lock()
        self._last_shot: dict[str, str] = {}

    async def ensure_started(self, session_id: str) -> None:
        async with self._start_lock:
            if self._browser is not None and self._browser.is_connected():
                return
            self._pw = await async_playwright().start()
            try:
                self._browser = await self._pw.chromium.launch(
                    headless=self.settings.browser_headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--autoplay-policy=user-gesture-required",
                    ],
                )
                self._started = True
            except Exception as exc:  # pragma: no cover - env dependent
                await self._pw.stop()
                self._pw = None
                raise RuntimeError(f"Browser could not start: {exc}") from exc

    async def page_for(self, session_id: str) -> Page:
        await self.ensure_started(session_id)
        page = self._pages.get(session_id)
        if page is None:
            context = self._contexts.get(session_id)
            if context is None or context.is_closed():
                assert self._browser is not None
                context = await self._browser.new_context(
                    viewport={
                        "width": self.settings.viewport_width,
                        "height": self.settings.viewport_height,
                    },
                    device_scale_factor=1,
                    locale="en-US",
                    color_scheme="light",
                    ignore_https_errors=False,
                )
                self._contexts[session_id] = context
            page = await context.new_page()
            page.set_default_timeout(self.settings.nav_timeout_ms)
            self._pages[session_id] = page
        return page

    async def status(self) -> str:
        if self._browser is None or not self._browser.is_connected():
            return "DISCONNECTED"
        return "READY"

    async def navigate(self, session_id: str, url: str) -> None:
        page = await self.page_for(session_id)
        response = await page.goto(url, timeout=self.settings.nav_timeout_ms, wait_until="domcontentloaded")
        if response is None:
            return
        if response.status >= 400:
            raise RuntimeError(f"Page responded with HTTP {response.status}")

    async def screenshot_b64(self, session_id: str) -> str:
        page = await self.page_for(session_id)
        raw = await page.screenshot(type="jpeg", quality=self.settings.shot_quality, animations="disabled")
        digest = hashlib.sha256(raw).hexdigest()
        if self._last_shot.get(session_id) == digest:
            return ""
        self._last_shot[session_id] = digest
        return base64.b64encode(raw).decode("ascii")

    async def stream_screenshot(self, session_id: str) -> None:
        shot = await self.screenshot_b64(session_id)
        if shot:
            await self.emit(ev(session_id, 0, EventType.SCREENSHOT, {"image": shot}))

    async def observe(self, session_id: str) -> dict:
        page = await self.page_for(session_id)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        snapshot = await page.evaluate(_OBSERVE_JS)
        return snapshot

    async def interactive_snapshot(self, session_id: str) -> dict:
        page = await self.page_for(session_id)
        return {"elements": await page.evaluate(_INTERACTIVE_JS), "viewport": self.settings.viewport_width}

    async def human_input(self, session_id: str, payload: dict) -> None:
        page = await self.page_for(session_id)
        kind = payload.get("kind")
        if kind == "move":
            await page.mouse.move(payload["x"], payload["y"])
        elif kind == "down":
            await page.mouse.down(button=payload.get("button", "left"))
        elif kind == "up":
            await page.mouse.up(button=payload.get("button", "left"))
        elif kind == "click":
            await page.mouse.click(payload["x"], payload["y"], button=payload.get("button", "left"))
        elif kind == "dblclick":
            await page.mouse.dblclick(payload["x"], payload["y"])
        elif kind == "wheel":
            await page.mouse.wheel(payload.get("dx", 0), payload.get("dy", 120))
        elif kind == "key":
            await page.keyboard.press(payload["key"])
        elif kind == "type":
            await page.keyboard.type(payload.get("text", ""), delay=25)

    async def close_session(self, session_id: str) -> None:
        page = self._pages.pop(session_id, None)
        if page:
            try:
                await page.close()
            except Exception:
                pass
        context = self._contexts.pop(session_id, None)
        if context:
            try:
                await context.close()
            except Exception:
                pass

    async def shutdown(self) -> None:
        for context in self._contexts.values():
            try:
                await context.close()
            except Exception:
                pass
        self._contexts.clear()
        self._pages.clear()
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._pw:
            try:
                await self._pw.stop()
            except Exception:
                pass
            self._pw = None


_OBSERVE_JS = r"""
() => {
  const el = (node, max = 120) => {
    const txt = ((node.innerText || node.value || node.textContent || '').trim()).slice(0, max);
    return txt;
  };
  const elements = [];
  const seen = new Set();
  const nodes = document.querySelectorAll('a,button,input,select,textarea,[role=button],[role=link],[data-sn]');
  nodes.forEach((n) => {
    const rect = n.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    const label = (n.getAttribute('aria-label') || el(n, 80) || '').trim();
    const id = n.id || '';
    const name = n.getAttribute('name') || '';
    const ref = id ? `#${CSS.escape(id)}` : (name ? `[name="${CSS.escape(name)}"]` : '');
    const fr = n.closest('form');
    const formId = fr && fr.id ? fr.id : '';
    const formName = fr && !formId ? (fr.getAttribute('name') || '') : '';
    const formRef = formId ? `#${CSS.escape(formId)}` : (formName ? `[name="${CSS.escape(formName)}"]` : '');
    if (!ref || seen.has(ref)) return;
    seen.add(ref);
    elements.push({
      ref, id, name, form_ref: formRef,
      tag: n.tagName.toLowerCase(),
      role: n.getAttribute('role') || '',
      type: n.getAttribute('type') || '',
      href: n.getAttribute('href') || '',
      label: label.slice(0, 80),
      value: (n.value || '').slice(0, 120),
      rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) }
    });
  });
  const forms = [];
  document.querySelectorAll('form').forEach((f) => {
    const action = f.getAttribute('action') || location.pathname;
    const id = f.id || '';
    const ref = id ? `#${CSS.escape(id)}` : (f.getAttribute('name') ? `[name="${CSS.escape(f.getAttribute('name'))}"]` : '');
    const fields = [];
    f.querySelectorAll('input,select,textarea').forEach((i) => {
      const fid = i.id || '';
      const fname = i.getAttribute('name') || '';
      const fref = fid ? `#${CSS.escape(fid)}` : (fname ? `[name="${CSS.escape(fname)}"]` : '');
      fields.push({ ref: fref, name: fname, type: i.getAttribute('type') || 'text', label: (i.getAttribute('aria-label') || i.placeholder || '').slice(0, 60), value: (i.value || '').slice(0, 40) });
    });
    if (ref) forms.push({ ref, action, fields });
    else if (fields.length) forms.push({ ref: '', action, fields });
  });
  const mainText = (document.body ? document.body.innerText || '' : '').slice(0, 8000);
  return {
    url: location.href,
    host: location.host,
    title: (document.title || '').slice(0, 200),
    text: mainText,
    elements,
    forms,
  };
}
"""


_INTERACTIVE_JS = r"""
() => {
  const out = [];
  document.querySelectorAll('a,button,input,select,textarea,[role=button],[role=link]').forEach((n) => {
    const rect = n.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    out.push({
      x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height),
      label: (n.getAttribute('aria-label') || (n.innerText || n.value || n.placeholder || '').trim() || n.tagName).slice(0, 60),
      tag: n.tagName.toLowerCase()
    });
  });
  return out;
}
"""