#!/usr/bin/env python3
"""hermes-agent-gui — bootstrap (P2#10).

End-to-end first-run installer + launcher. Pattern from B (nesquena/hermes-webui's
bootstrap.py) plus C's interpreter ABI sanity check.

Steps:
  1. Sanity-check the interpreter against ~/.hermes/hermes-agent's venv.
     If they mismatch, auto re-exec with the venv's python.
  2. Detect Hermes Agent at ~/.hermes/hermes-agent; if missing, offer to run
     the official installer (curl | bash). Skippable with --no-install or
     --skip-agent (gateway mode).
  3. Ensure GUI dependencies (pyyaml, cryptography) — if missing, instruct
     the user (we don't shell out to pip without consent).
  4. Start the GUI server, wait for /api/health.
  5. Print the URL + (optionally) open the browser.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

HERMES_HOME = Path.home() / ".hermes"
AGENT_DIR = HERMES_HOME / "hermes-agent"
GUI_ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

logger = logging.getLogger("hermes-agent-gui.bootstrap")

REEXEC_FLAG = "HERMES_GUI_BOOTSTRAP_REEXECED"


# ── Interpreter ABI sanity check (C pattern) ────────────────────────────────


def _check_interpreter_matches_venv() -> None:
    """If a Hermes Agent venv exists and runs a different Python minor than
    the current interpreter, re-exec under the venv's Python so embedded mode
    can import compiled C extensions (pydantic_core et al.).
    """
    if os.environ.get(REEXEC_FLAG):
        return
    if not AGENT_DIR.exists():
        return
    candidates = list((AGENT_DIR / "venv" / "lib").glob("python*"))
    if not candidates:
        return
    venv_minor = candidates[0].name.replace("python", "")
    cur_minor = f"{sys.version_info.major}.{sys.version_info.minor}"
    if venv_minor == cur_minor:
        return
    venv_py = AGENT_DIR / "venv" / "bin" / "python3"
    if not venv_py.exists():
        return
    print(
        f"[bootstrap] python {cur_minor} ≠ hermes-agent venv ({venv_minor}); "
        f"re-launching with {venv_py}",
        file=sys.stderr,
    )
    env = os.environ.copy()
    env[REEXEC_FLAG] = "1"
    os.execve(str(venv_py), [str(venv_py), *sys.argv], env)


# ── Hermes Agent detection + install ────────────────────────────────────────


def _is_agent_installed() -> bool:
    return AGENT_DIR.exists() and any(AGENT_DIR.iterdir())


def _install_agent(non_interactive: bool) -> None:
    print("[bootstrap] Hermes Agent not found at ~/.hermes/hermes-agent")
    if not non_interactive:
        reply = input("[bootstrap] Run the official installer (curl | bash) now? [y/N] ").strip().lower()
        if reply != "y":
            print("[bootstrap] skipping; embedded mode disabled until installed.")
            return
    cmd = (
        "curl -fsSL "
        "https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"
    )
    print(f"[bootstrap] $ {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"[bootstrap] installer failed (exit {exc.returncode}); continuing without embedded mode.")


# ── GUI deps check ──────────────────────────────────────────────────────────


def _check_gui_deps() -> list[str]:
    missing: list[str] = []
    for mod in ("yaml", "cryptography"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    return missing


# ── port + health ──────────────────────────────────────────────────────────


def _pick_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def _wait_for_health(url: str, timeout: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(0.4)
    return False


# ── main ────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hermes-agent-gui-bootstrap")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8800)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--no-install", action="store_true",
                        help="Skip the Hermes Agent installer prompt.")
    parser.add_argument("--skip-agent", action="store_true",
                        help="Don't try to detect/install Hermes Agent — gateway mode.")
    parser.add_argument("--yes", action="store_true",
                        help="Non-interactive: assume 'yes' on prompts.")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # 1. interpreter sanity
    _check_interpreter_matches_venv()

    # 2. Hermes Agent detection / install
    if not args.skip_agent:
        if not _is_agent_installed() and not args.no_install:
            _install_agent(non_interactive=args.yes)

    # 3. GUI deps
    missing = _check_gui_deps()
    if missing:
        print(f"[bootstrap] missing GUI deps: {missing}")
        print(f"[bootstrap] run: pip install -r {GUI_ROOT}/apps/server/requirements.txt")
        return 2

    # 4. start server
    port = _pick_port(args.port)
    print(f"[bootstrap] starting server on {args.host}:{port}")
    from server import main as server_main  # noqa: WPS433 — late import to keep deps clean

    import threading

    def _run() -> None:
        server_main(["--host", args.host, "--port", str(port)])

    threading.Thread(target=_run, daemon=True, name="bootstrap-server").start()

    base = f"http://{args.host}:{port}"
    if not _wait_for_health(base + "/api/health"):
        print("[bootstrap] server never became healthy — aborting.")
        return 1
    print(f"[bootstrap] ready · {base}")

    if not args.no_browser and shutil.which("open") or shutil.which("xdg-open") or sys.platform == "win32":
        try:
            webbrowser.open(base)
        except webbrowser.Error:
            pass

    # Keep the main thread alive so the server thread can serve.
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n[bootstrap] bye")
        return 0


if __name__ == "__main__":
    sys.exit(main())
