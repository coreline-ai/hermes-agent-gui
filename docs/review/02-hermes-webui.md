# B · nesquena/hermes-webui — 코드 레벨 상세 분석

> **Repo**: https://github.com/nesquena/hermes-webui
> **Language**: Python (서버) + Vanilla JS (클라이언트) · **License**: MIT
> **Stars**: 8,587 · **Last push**: 2026-05-25
> **Tagline**: "The best way to use Hermes Agent from the web or from your phone!"

---

## 1. 정체성 한 줄 요약

**Python stdlib HTTP 서버 + 빌드 단계 없는 Vanilla JS PWA.**
"No build step, no framework, no bundler. Just Python and vanilla JS." 모바일 우선, SSH 터널/Tailscale 환경에 최적화. CLI 와의 **거의 1:1 패리티**가 목표.

---

## 2. 기술 스택

### Server
| Layer | 채택 |
|------|------|
| HTTP | **Python stdlib 만** (`http.server` 계열로 추정) — `server.py` thin shell + `api/routes.py` 핸들러 |
| 의존성 | `pyyaml>=6.0`, `cryptography>=42.0` (passkey/WebAuthn 용) — **그게 전부** |
| 데이터 | SQLite (`sqlite3` stdlib), 파일 기반 JSON 사이드카 |
| 스트리밍 | SSE |
| 배포 | `bootstrap.py` · `ctl.sh` (데몬 래퍼) · `start.sh` / `start.ps1` |

### Client
| Layer | 채택 |
|------|------|
| Framework | **없음** — `static/*.js` 의 vanilla JS 모듈 |
| PWA | `static/sw.js` (service worker) + `static/manifest.json` |
| Icons | `static/icons.js`, `favicon.svg` (CSS 인라인) |
| Style | `static/style.css` (수기 CSS) |
| i18n | `static/i18n.js` |

### Quality
| | |
|---|---|
| Container | `Dockerfile` + **3종 compose** (`docker-compose.yml`, `.two-container.yml`, `.three-container.yml`) |
| CI | `.github/workflows/`: `tests.yml`, `docker-smoke.yml`, `native-windows-startup.yml`, `release.yml` |
| Docs | `ARCHITECTURE.md`, `DESIGN.md`, `THEMES.md`, `TESTING.md`, `ROADMAP.md`, `SPRINTS.md`, `BUGS.md`, `docs/onboarding-agent-checklist.md`, `docs/CONTRACTS.md`, `docs/EXTENSIONS.md` |
| Pre-built images | GHCR amd64 + arm64 (release-pinned) |

---

## 3. 코드 구조

```
hermes-webui/
├── api/                       ← 40+ Python 모듈 (핵심 자산)
├── docs/                      ← 사용자/온보딩/통합/스크린샷
│   ├── images/                ← ui-sessions.png, ui-workspace.png 등
│   ├── pr-assets/             ← PR 비교 스크린샷
│   └── pr-media/{1257,1321,...}/ ← 이슈별 미디어
├── static/                    ← Vanilla JS PWA 프론트엔드
│   ├── boot.js, commands.js, i18n.js, icons.js, login.js,
│   ├── messages.js, onboarding.js, panels.js, pwa-startup.js,
│   ├── sessions.js, terminal.js, ui.js, workspace.js (≈26KB),
│   ├── sw.js (service worker), manifest.json, index.html, style.css,
│   └── vendor/
├── scripts/                   ← repair_workspace_user_turns.py, windows/, wsl/
├── bootstrap.py               ← 설치 + venv + 실행 통합 진입점
├── server.py                  ← thin shell
├── mcp_server.py              ← MCP 통합 서버
├── ctl.sh                     ← 데몬 lifecycle (start/status/logs/restart/stop)
├── docker-compose.yml
├── docker-compose.two-container.yml
├── docker-compose.three-container.yml
├── docker_init.bash
├── requirements.txt           ← pyyaml, cryptography
├── pytest.ini
└── start.ps1 / start.sh
```

### 3.1 `api/` — 40+ 모듈 (전체 인벤토리)

| 도메인 | 모듈 |
|--------|------|
| 라우팅 | `routes.py` (메인 핸들러 — ≈수천 LOC) |
| 인증 | `auth.py`, `oauth.py`, `passkeys.py` (WebAuthn) |
| 세션 (5종!) | `agent_sessions.py`, `session_events.py`, `session_lifecycle.py`, `session_ops.py`, `session_recovery.py` |
| 컨텍스트 | `compression_anchor.py`, `state_sync.py`, `turn_journal.py`, `run_journal.py` |
| 헬스 / 진단 | `agent_health.py`, `system_health.py`, `dashboard_probe.py`, `gateway_watcher.py`, `request_diagnostics.py` |
| 스트리밍 | `streaming.py` |
| 백그라운드 | `background.py` |
| 작업 / 명령 | `commands.py`, `clarify.py`, `goals.py` |
| 칸반 | `kanban_bridge.py` |
| 워크스페이스 | `workspace.py`, `workspace_git.py`, `worktrees.py` |
| 터미널 | `terminal.py` |
| 업로드 | `upload.py` |
| 모델/공급자 | `models.py`, `providers.py`, `profiles.py` |
| 청구/사용량 | `metering.py`, `usage.py` |
| 확장 | `extensions.py` |
| 온보딩 | `onboarding.py` |
| 부팅 | `startup.py` |
| 어댑터 | `runtime_adapter.py` |
| 롤백 | `rollback.py` |
| 업데이트 | `updates.py` |
| 설정 | `config.py` |
| 모델 정의 | `models.py` (Pydantic-less, dataclass/dict 추정) |
| 헬퍼 | `helpers.py`, `__init__.py` |

### 3.2 `routes.py` 발췌 코멘트 (실제 코드에서 추출)

```python
# Treat stalled/closed HTTP clients as normal disconnects.
# Long-lived SSE connections often end this way when a browser tab sleeps,
# a phone switches networks, or Tailscale leaves the socket half-closed.
_CLIENT_DISCONNECT_ERRORS = (BrokenPipeError, ConnectionResetError,
                             ConnectionAbortedError, TimeoutError, OSError)

# ── Cron run tracking ──
_RUNNING_CRON_JOBS: dict[str, float] = {}
_MANUAL_COMPRESSION_JOBS: dict[str, dict] = {}
_MANUAL_COMPRESSION_JOB_TTL_SECONDS = 10 * 60

# CSP report rate limiting
_CSP_REPORT_RATE_LIMIT_WINDOW_SECONDS = 60
_CSP_REPORT_RATE_LIMIT_MAX = 100
_CSP_REPORT_MAX_BODY_BYTES = 64 * 1024

# Client event rate limiting
_CLIENT_EVENT_ALLOWED_FIELDS = {
    "event": 64, "source": 80, "session_id": 128, "stream_id": 128,
    "visibility_state": 32, "url_path": 256, "reason": 160,
}

# Profile-scoped session/project filtering (#1611, #1614)
# Sessions and projects scoped to active profile by default,
# `?all_profiles=1` opts into aggregate mode.
# Renamed-root profile handling (#1612).
from api.profiles import _profiles_match
```

**관찰** — Tailscale/모바일/SSH 터널 환경에서의 SSE 절단을 1급 시민으로 처리. CSP 리포트와 클라이언트 이벤트의 레이트 리밋과 필드 화이트리스트가 박혀 있어 프로덕션 운영 흔적이 짙다.

### 3.3 `static/` — Vanilla JS PWA

3-panel layout:
- **Left** — sessions/navigation (`sessions.js`)
- **Center** — chat (`messages.js`)
- **Right** — workspace file browser (`workspace.js`, ≈26KB)
- **Composer footer** — model/profile/workspace 토글 + circular context ring
- **Hermes Control Center** — 사이드바 하단 런처에서 설정/세션툴 진입

PWA 구성:
- `manifest.json` (설치 가능 앱)
- `sw.js` (service worker, 캐싱 + 오프라인)
- `pwa-startup.js` (런타임 부팅)
- `favicon-{192,512}.png` + `favicon-512.svg` (iOS/Android 아이콘 셋)

i18n: `static/i18n.js` 모듈 단독 (JSON 키맵 추정).
온보딩: `onboarding.js` — 첫 실행 마법사 (Hermes Agent 미설치 시 공식 인스톨러 자동 실행 — `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash`)

### 3.4 `bootstrap.py` 플로우

```
1. Hermes Agent 감지 → 없으면 공식 인스톨러 시도
2. WebUI 의존성을 가진 Python venv 탐색/생성
3. 웹 서버 시작 + /health 대기
4. 브라우저 자동 열기 (--no-browser 로 끌 수 있음)
5. 첫-실행 온보딩 마법사 진입
```

### 3.5 `ctl.sh` — 데몬 래퍼

```sh
./ctl.sh start              # background daemon, PID at ~/.hermes/webui.pid
./ctl.sh status             # PID, uptime, host/port, log path, /health
./ctl.sh logs --lines 100   # tail ~/.hermes/webui.log
./ctl.sh restart
./ctl.sh stop
```

`fuser`/`pkill` 없이도 동작하도록 의도된 자체 PID 관리. 홈랩 self-host 시나리오에 최적화.

### 3.6 Docker — 3종 compose

| 파일 | 시나리오 |
|------|---------|
| `docker-compose.yml` | 1-컨테이너 (in-process agent) — 5분 quickstart |
| `docker-compose.two-container.yml` | 2-컨테이너 (agent + webui 분리) |
| `docker-compose.three-container.yml` | 3-컨테이너 (agent + webui + ?) — 풀 프로덕션 |
| Mount | `~/.hermes`, `~/workspace` |
| Port | `127.0.0.1:8787` 기본 (외부 노출시 비밀번호 필수) |
| Auth | `HERMES_WEBUI_PASSWORD` env |

---

## 4. 핵심 기능 (README 발췌)

```
✔ Persistent memory — user profile, agent notes, skills system
✔ Self-hosted scheduling — cron jobs (offline-fire) → Telegram/Discord/Slack/Signal/email
✔ 10+ messaging platforms — same agent in terminal + phone
✔ Self-improving skills — Hermes writes/saves its own skills from experience
✔ Provider-agnostic — OpenAI/Anthropic/Google/DeepSeek/OpenRouter/...
✔ Orchestrates other agents — can spawn Claude Code or Codex for heavy coding
✔ Self-hosted — your conversations, your memory, your hardware
```

UI:
- 3-panel + composer footer + circular context ring
- 라이트/다크 모드 (테마 시스템은 `THEMES.md`)
- Hermes Control Center 사이드바 하단 런처

---

## 5. 연동 모델

```
┌─────────────────────────────────────────────────────────┐
│  Browser / PWA (mobile-first)                            │
│   ↑ fetch + SSE                                          │
│   ↓                                                      │
│  Python stdlib HTTP server (server.py + api/*.py)        │
│   ↓ in-process or HTTP                                   │
│   └── Hermes Agent (AIAgent)  ← 직접 임베드 또는 :8642  │
└─────────────────────────────────────────────────────────┘
```

운영 모드:
- **In-process** (1-컨테이너) — Hermes Agent 를 WebUI 가 직접 임포트
- **분리** (2~3 컨테이너) — Agent 와 WebUI 별도, gateway 호출

---

## 6. 보안 / 운영 자산

- OAuth + WebAuthn(passkeys) + 비밀번호 + WebUI 토큰 (multi-layer auth)
- CSP report endpoint + 레이트 리밋
- 클라이언트 이벤트 로깅 + 필드 화이트리스트 (XSS/abuse 방어)
- Profile-scoped 세션 필터 (다중 사용자/프로파일 격리)
- `/api/session/health` — 서버/브라우저/컴팩트 컨텍스트 메시지 카운트
- 브라우저↔서버 transcript drift 자동 복구
- Cron 잡 추적 + manual compression job TTL
- SSE half-close 정상 처리 (Tailscale 친화)
- 메시징 세션 정체성 캐시 + lock (멀티 플랫폼 식별)

---

## 7. 강점

1. **외부 의존성 거의 0** — `pyyaml`+`cryptography` 만으로 동작. 환경 충돌 거의 없음
2. **API 모듈의 깊이** — 40+ 모듈이 세션 라이프사이클, 복구, 칸반, 워크트리, 메트링, 메시징, OAuth, Passkeys 등을 망라
3. **PWA / 모바일 first** — service worker, manifest, 모바일 SSE 절단 대응까지 견고
4. **운영 친화** — `ctl.sh` 데몬, 3종 compose, GHCR multi-arch 이미지, daemon log
5. **CLI 패리티 목표** — 터미널에서 되는 건 다 됨 (워크스페이스, 세션, 칸반, 크론)
6. **Hermes Agent 와 같은 언어(Python)** — 임베드 모드 가능, 의존성 단일화

## 8. 약점

1. **프론트 확장성** — Vanilla JS 라 기능 100+ 이상으로 확장 시 코드 응집도/리팩토링 비용↑
2. **빌드 시스템 부재** — 코드 스플릿/트리쉐이킹/TypeScript 없음
3. **에디터/터미널 격이 낮음** — Monaco/xterm.js 미사용 (별도 `terminal.js` 단순 구현)
4. **3D / 고급 UX 자산 부족** — A 에 비해 비주얼 임팩트 낮음
5. **테마 시스템이 워크스페이스만큼 풍부하진 않음**
6. **Swarm / Conductor 멀티에이전트 미지원** — 단일 에이전트 인터페이스

---

## 9. 통합 시 활용 결정

| 이식 / 채택 대상 | 이유 |
|------------------|------|
| `api/auth.py`, `oauth.py`, `passkeys.py` | 인증 백엔드 표준 채택 (다층 인증) |
| `api/agent_sessions.py`, `session_events.py`, `session_lifecycle.py`, `session_ops.py`, `session_recovery.py` | 세션 5종 세트 — 표준 채택 |
| `api/compression_anchor.py`, `turn_journal.py`, `run_journal.py`, `state_sync.py` | 컨텍스트 안전 표준 |
| `api/streaming.py` | SSE 표준 (절단/half-close 처리 포함) |
| `api/agent_health.py`, `system_health.py`, `dashboard_probe.py`, `gateway_watcher.py`, `request_diagnostics.py` | 헬스/진단 표준 |
| `api/workspace.py`, `workspace_git.py`, `worktrees.py` | 워크스페이스 표준 |
| `api/kanban_bridge.py` | 칸반 백엔드 (UI 는 A) |
| `api/profiles.py` (profile-scoped filter) | 멀티유저/프로파일 격리 표준 |
| `api/metering.py`, `usage.py` | 비용/사용량 |
| `api/onboarding.py` + 마법사 플로우 | 첫-실행 UX 표준 |
| `api/runtime_adapter.py` | 임베드/원격 어댑터 패턴 |
| `bootstrap.py` | 진입점 패턴 |
| `ctl.sh` | 데몬 lifecycle |
| `docker-compose.{,.two,.three}-container.yml` | 배포 옵션 3종 |
| `static/sw.js`, `manifest.json` | **재구성** — vite-plugin-pwa 로 마이그레이션 |
| `static/*.js` (vanilla) | **포기** — 동등한 React 컴포넌트(A)로 교체 |
| `static/style.css` | **참고만** — Tailwind v4 로 재작성 |
| `static/index.html` | **재작성** — Vite 진입점 |

상세 통합 방안은 [`06-integration-design.md`](./06-integration-design.md) 참조.
