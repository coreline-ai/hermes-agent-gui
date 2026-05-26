# A · outsourc-e/hermes-workspace — 코드 레벨 상세 분석

> **Repo**: https://github.com/outsourc-e/hermes-workspace
> **Version**: 2.3.0 · **Language**: TypeScript / JavaScript · **License**: MIT
> **Stars**: 4,837 · **Last push**: 2026-05-24
> **Tagline**: "Native web workspace for Hermes Agent — chat, terminal, memory, skills, inspector."

---

## 1. 정체성 한 줄 요약

**Electron 데스크탑/웹 듀얼 빌드를 지원하는, React 19 + TanStack 기반의 풀스펙 에이전트 워크스페이스.**
Hermes Agent 본체에는 손대지 않는 "zero-fork" 정책으로, 외부 Gateway(`:8642`) + Dashboard API(`:9119`) 만 호출하는 thin client 구조.

---

## 2. 기술 스택

### Frontend
| Layer | 채택 라이브러리 |
|------|-----------------|
| Framework | **React 19.2** + **react-dom 19.2** |
| Routing | **@tanstack/react-router 1.166** (file-based) · `@tanstack/react-router-ssr-query` |
| Server runtime | **@tanstack/react-start 1.166** (Vinxi 후속, SSR 가능) |
| Data | **@tanstack/react-query 5.90** |
| State | **zustand 5.0** |
| Styling | **Tailwind CSS v4** (`@tailwindcss/vite`) · `class-variance-authority` · `clsx` · `tailwind-merge` |
| UI primitives | **@base-ui/react** (Radix 후속), `react-joyride` (온보딩 투어) |
| Icons | `@hugeicons/react`, `@lobehub/icons`, `@lobehub/icons-static-png` |
| Markdown | `react-markdown` + `remark-gfm` + `remark-breaks` + `rehype-raw` + `rehype-sanitize` · `marked` · `shiki` (코드 하이라이트) |
| Charts | `recharts 3.7` |
| Animation | `framer-motion 12` · `motion` |
| Code editor | **@monaco-editor/react 4.7** |
| Terminal | **xterm 5.3** + addons (`fit`, `search`, `web-links`) |
| 3D | **three 0.184** + `@react-three/fiber 9` + `@react-three/drei 10` + `@react-three/rapier 2` (물리) + `@react-three/postprocessing 3` · `ecctrl` (캐릭터 컨트롤러) |
| Schema | `zod 3.25` · `yaml` |
| WebSocket | `ws 8.20` |
| Browser automation | `playwright 1.58` + `playwright-extra` + `puppeteer-extra-plugin-stealth` |

### Desktop
| | |
|---|---|
| Shell | **electron 40.8** |
| Updates | `electron-updater 6.6` |
| Builder | `electron-builder 26.8` |
| Server bundle | esbuild (CJS bundle for embedded Node server) |

### Backend (TanStack Start server)
TypeScript 서버. `src/server/` 디렉토리에 비즈니스 로직이 모여 있음. 외부 Hermes Agent gateway 와 dashboard API 를 래핑.

### Test / Tooling
| | |
|---|---|
| Unit | vitest 3 · @testing-library/react 16 · jsdom 27 |
| E2E | playwright (`e2e/chat-flicker-duplicate.spec.ts` 등) |
| Lint | eslint 10 (@tanstack/eslint-config) + prettier 3 |
| Package manager | **pnpm** (workspace 모드 — `playground-ws-worker` 서브패키지 존재) |
| Node | **>= 22.0** |

---

## 3. 코드 구조

### 3.1 디렉토리 톱레벨

```
hermes-workspace/
├── agents/              ← 에이전트 페르소나 README 들 (builder/inbox-triage/km-agent/maintainer/
│                          ops-watch/orchestrator/qa/researcher/reviewer/strategist)
├── docs/                ← 방대한 설계/UX/Hermesworld 문서
│   ├── design/
│   ├── hermesworld/     ← MMO/agentic 게임 설계 문서 (별도 트랙)
│   ├── swarm/
│   └── screenshots/
├── e2e/                 ← playwright 스펙
├── electron/            ← Electron main/preload/prod-server (CJS)
├── memory/              ← 에이전트 메모리 sandbox (goals/, swarm/)
├── nix/                 ← Nix flake + module
├── playground-ws-worker/ ← Cloudflare Worker (wrangler.toml) 서브패키지
├── public/              ← 정적 자산 (avatars, ascii-portraits, claude-*.png/webp)
├── scripts/             ← managed-companion-smoke, playground-ws 등
└── src/
    ├── components/      ← 100+ React 컴포넌트
    ├── hooks/           ← 36+ custom hook
    ├── lib/             ← 40+ 클라이언트 유틸리티
    ├── routes/          ← TanStack 파일 라우팅 (chat/dashboard/files/jobs/mcp/memory/operations/
    │                      playground/profiles/settings/skills/swarm/swarm2/tasks/terminal/...)
    ├── screens/         ← 페이지 단위 view (agents/agora/chat/crew/dashboard/files/gateway/jobs/
    │                      mcp/memory/playground/profiles/settings/skills/swarm/swarm2/tasks)
    ├── server/          ← 80+ TypeScript 백엔드 모듈
    ├── stores/          ← zustand 스토어
    ├── types/, utils/
    ├── router.tsx, routeTree.gen.ts
    ├── styles.css, scifi-theme.css
```

### 3.2 `src/components/` — 분야별 컴포넌트 인벤토리

| 카테고리 | 대표 컴포넌트 |
|---------|--------------|
| 에이전트 | `agent-avatar`, `agent-card`, `agent-chat/`, `agent-swarm/`, `agent-view/`, `orchestrator-avatar` |
| 채팅 | `chat-panel`, `chat-panel-toggle`, `prompt-kit/`, `slash-command-menu`, `attachment-button`, `attachment-preview`, `mobile-prompt/` |
| 워크스페이스 | `file-explorer/`, `terminal/`, `terminal-panel`, `workspace-shell` |
| 시스템 | `command-palette`, `keyboard-shortcuts-modal`, `theme-toggle`, `global-shortcut-listener`, `terminal-shortcut-listener` |
| 상태 / 연결 | `claude-health-banner`, `claude-reconnect-banner`, `backend-unavailable-state`, `connection-overlay`, `connection-startup-screen`, `status-indicator`, `system-metrics-footer`, `context-meter` |
| 운영 | `cron-manager/`, `inspector/`, `memory-viewer/`, `dashboard-overflow-panel`, `update-center-notifier`, `usage-meter/` |
| 모드 | `apply-mode-dialog`, `manage-modes-modal`, `mode-selector`, `rename-mode-dialog`, `save-mode-dialog` |
| 모바일 | `mobile-hamburger-menu`, `mobile-page-header`, `mobile-sessions-panel`, `mobile-tab-bar` |
| Auth / Onboarding | `auth/`, `onboarding/` |
| 검색 | `search/` |
| 설정 | `settings/`, `settings-dialog/` |
| Swarm | `swarm/`, `agent-swarm/` |
| 기본 UI | `ui/` (Base UI 기반 primitive 래퍼) |

### 3.3 `src/hooks/` — 36+ 훅 인벤토리 (발췌)

`use-agent-behaviors`, `use-agent-outputs`, `use-agent-view`, `use-chat-mode`, `use-chat-settings`, **`use-chat-stream`**, `use-cli-agents`, `use-crew-status`, `use-feature-available`, `use-feature-capability`, `use-gateway-caps`, `use-global-shortcuts`, `use-mobile-keyboard`, `use-model-suggestions`, `use-modes`, `use-onboarding`, `use-orchestrator-state`, `use-pinned-models`, `use-pinned-sessions`, `use-pull-to-refresh`, `use-research-card`, `use-search-data`, `use-search-modal`, `use-settings`, `use-sounds`, `use-swarm-chat`, `use-swipe-navigation`, **`use-voice-input`**, **`use-voice-recorder`**.

### 3.4 `src/lib/` — 핵심 클라이언트 유틸 (발췌)

- `gateway-api.ts` — Hermes Agent gateway (`:8642`) 클라이언트
- `cron-api.ts`, `jobs-api.ts`, `tasks-api.ts` — 도메인 API 래퍼
- `claude-auth.ts` — Claude/Anthropic 인증 헬퍼
- `i18n.ts` (테스트 동반) — 다국어
- `feature-gates.ts` — capability 기반 기능 토글 (gateway 가 endpoint 미지원 시 placeholder 표시)
- `connection-errors.ts` — 연결 오류 분류
- `model-info.ts`, `provider-catalog.ts` — 모델/공급자 메타
- `workspace-message-scope.ts`, `workspace-checkpoints.ts`, `workspace-agents.ts` — 워크스페이스 로컬 상태
- `stt-config.ts`, `stt-transcription.ts` — 음성 STT
- `haptics.ts`, `sounds.ts`, `clipboard.ts` — 환경 통합
- `local-chat-threads.ts` — 로컬 채팅 스레드 캐시

### 3.5 `src/server/` — 80+ TypeScript 서버 모듈 (요약)

| 도메인 | 모듈 |
|--------|-----|
| 인증 | `auth-middleware.ts` (+테스트) |
| 채팅 | `chat-backends.ts`, `chat-event-bus.ts`, `chat-mode.ts`, `claude-agent.ts` (+테스트), `claude-api.ts`, `responses-api.ts` |
| Claude 통합 | `claude-paths.ts`, `claude-dashboard-api.ts`, `claude-tasks-backend.ts` |
| Conductor | `conductor-mission-sanitize.ts` |
| Dashboard | `dashboard-aggregator.ts` |
| Gateway | `gateway.ts`, `gateway-capabilities.ts` |
| Config | `hermes-config-store.ts`, `hermes-config-migration.ts`, `hermes-config-route.ts` |
| Cron | `hermes-cron-profiles.ts` |
| Integration | `integration-detection.ts` |
| Kanban | `kanban-backend.ts`, `kanban-dashboard-proxy.ts` |
| Knowledge | `knowledge-browser.ts`, `knowledge-config.ts` |
| Local | `local-provider-discovery.ts`, `local-session-store.ts` |
| MCP | `mcp-cli-bridge.ts`, `mcp-hub/`, `mcp-hub-sources-store.ts`, `mcp-input-validate.ts`, `mcp-normalize.ts`, `mcp-presets-store.ts`, `mcp-tools-cache.ts` |
| Memory | `memory-browser.ts` |
| Name reservation | `name-reservations.ts` |
| OpenAI | `openai-compat-api.ts` |
| Plugins | `plugins-browser.ts` |
| Portable history | `portable-history.ts` |
| Profiles | `profiles-browser.ts` |
| Provider | `provider-usage.ts` |
| PTY (terminal) | `pty-helper.py` (Python helper invoked by Node) |
| Rate limit | `rate-limit.ts` |
| Runs | `run-store.ts`, `send-run-tracker.ts` |
| Session | `session-utils.ts` |
| STT | `stt-transcription.ts` |
| Swarm | `swarm-chat-reader.ts`, `swarm-checkpoints.ts`, `swarm-environment.ts`, `swarm-foundation.ts`, `swarm-kanban-store.ts`, `swarm-lifecycle.ts`, `swarm-memory.ts`, `swarm-missions.ts` |

> 주목 — **`pty-helper.py`**: Node 측 xterm.js 가 PTY 를 띄울 때 OS 추상화 헬퍼로 Python 스크립트를 사용. 크로스플랫폼 PTY 관리.

### 3.6 `src/routes/` — 톱레벨 페이지

`/agora`, `/chat/...`, `/conductor`, `/dashboard`, `/early-access`, `/files`, `/hermes-world`, `/jobs`, `/mcp`, `/memory`, `/operations`, `/playground`, `/profiles`, `/reserve`, `/settings/...`, `/skills`, `/swarm`, `/swarm2`, `/tasks`, `/terminal`, `/vt-capital`, `/world`.

`agora`/`hermes-world`/`world`/`vt-capital` 는 **Hermesworld** 라 불리는 별도 MMO/agentic-game 트랙으로 보임 (docs/hermesworld/ 참조). 일반 워크스페이스 핵심 경로는 굵게 표시한 `/chat`, `/dashboard`, `/files`, `/jobs`, `/mcp`, `/memory`, `/operations`, `/profiles`, `/settings`, `/skills`, `/swarm`, `/tasks`, `/terminal`.

---

## 4. 핵심 기능 — README 발췌

```
💬 Chat — Real-time SSE streaming, tool call rendering, multi-session, markdown + syntax highlighting
🧠 Memory — Browse, search, and edit agent memory; markdown live editor
🧩 Skills — Browse 2,000+ skills with origin badges, filters, source paths, marketplace
🔌 MCP — Full /mcp page (catalog + marketplace + sources), or fallback to local config CRUD
📁 Files + Terminal — Full workspace file browser with Monaco; cross-platform PTY terminal
🎮 Operations — Multi-agent dashboard with profile presets (Sage/Trader/Builder/Scribe/Ops)
📡 Conductor — Mission dispatch + decomposition; native-swarm fallback
👥 Agent View — Live agent panel with avatar, queue, history, usage meter
🐝 Swarm Mode — Persistent tmux-backed Hermes Agent workers with role-based dispatch
🗄 Dashboard — Aggregated overview: sessions, model mix, cost ledger, attention card, ops strip
🎨 Themes — Hermes, Nous, Bronze, Slate, Mono (light + dark)
🔒 Security — Auth middleware on every route, CSP, path-traversal guard, fail-closed remote bind
📱 PWA + Tailscale — Install as a native-feeling app
⚙ Capability gates — Features that need upstream endpoints show a clean placeholder
```

추가로 `package.json` 의 스크립트에서 드러나는 빌드 타깃:
- `pnpm dev` — Vite dev server
- `pnpm electron:dev` / `electron:build:mac|win` — Electron 데스크탑 빌드
- `pnpm electron:bundle-server` — esbuild 로 Node 서버를 CJS 번들로 묶어 Electron 내부에 임베드
- `pnpm playground:ws` — Cloudflare Worker(playground) 별도 실행

---

## 5. 연동 모델 (zero-fork)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser / Electron renderer                                          │
│   ↓ TanStack Router/Query                                             │
│  TanStack Start server (Node)  ◀─ src/server/* — pty, auth, etc.      │
│   ↓ HTTP                                                              │
│   ├──► hermes gateway run        (:8642)  ← gateway-api.ts            │
│   └──► hermes dashboard          (:9119)  ← claude-dashboard-api.ts   │
└──────────────────────────────────────────────────────────────────────┘
```

ENV:
- `HERMES_API_URL` (gateway, 기본 `http://127.0.0.1:8642`)
- `HERMES_DASHBOARD_URL` (기본 `http://127.0.0.1:9119`)
- `HERMES_API_TOKEN` (gateway 가 `API_SERVER_KEY` 로 켜진 경우)

**Capability gate** 메커니즘: gateway 가 특정 endpoint 를 지원하지 않으면 UI 가 깨지지 않고 placeholder 를 띄움 (`src/lib/feature-gates.ts`).

---

## 6. 보안 / 운영 자산

- 모든 라우트에 `auth-middleware.ts` (테스트 동반)
- CSP, path-traversal guard, fail-closed remote bind (README 명시)
- `rate-limit.ts`
- `.github/workflows/`: `ci.yml`, `docker-publish.yml`, `security.yml`
- `Dockerfile` + `docker-compose.dev.yml` + `docker-compose.yml`
- `flake.nix` (Nix), `electron-builder.config.cjs` (DMG/EXE/AppImage 빌드)
- `install.sh` (one-line installer)

---

## 7. 강점

1. **프론트엔드 깊이** — React 19 + TanStack 풀스택, 100+ 컴포넌트, 36+ 훅, TypeScript 타이트한 타이핑
2. **데스크탑/웹/PWA 트리플 타깃** — Vite SPA, Electron DMG/EXE, PWA 설치 — 단일 코드베이스
3. **Swarm + Conductor** — 3종 중 유일한 멀티에이전트 control plane
4. **풀스펙 UX 자산** — Monaco, xterm.js, three.js (캐릭터/물리 포함), shiki, recharts
5. **capability gate** — gateway 버전 변동에 안전
6. **테스트 인프라** — vitest + playwright

## 8. 약점

1. **빌드 복잡성** — pnpm + Vite + Electron + esbuild + playwright. Node 22+ 필요
2. **저장소 크기** — 257MB · 모든 hermesworld 게임 자산 포함
3. **단순 self-host 어려움** — Python 만 깔린 환경에서는 즉시 못 띄움
4. **모바일 PWA 가 B 만큼 깊지 않음** — `mobile-*` 컴포넌트는 있으나 서비스워커 전략은 B 가 우수
5. **Babel/CDN 단일파일 모드 없음** — 어디든 던지면 띄우는 C 의 철학 부재
6. **백엔드가 TypeScript (Node)** — Hermes Agent 본체(Python)와 언어 갭. 운영 환경 의존성↑

---

## 9. 통합 시 활용 결정

| 이식 / 채택 대상 | 이유 |
|------------------|------|
| `src/components/**` (대부분) | UI 표준으로 채택 |
| `src/hooks/use-*` | 표준 채택 |
| `src/lib/gateway-api.ts`, `cron-api.ts`, `jobs-api.ts`, `tasks-api.ts` | API 클라이언트 표준 |
| `src/lib/feature-gates.ts` | capability gate 패턴 채택 |
| `src/routes/` 의 핵심 경로 | 채택 (hermesworld 트랙은 제외) |
| Tailwind v4 + 5 테마 | 채택 (Glassmorphism 6번째로 추가) |
| Monaco · xterm.js · shiki | 채택 |
| `src/server/swarm-*`, `conductor-mission-sanitize.ts`, `dashboard-aggregator.ts` | Swarm/Conductor 로직 — **Python 으로 재포팅** (백엔드는 B 채택이므로) |
| Electron 패키징 (`electron/`, `electron-builder.config.cjs`) | 선택적 타깃 |
| 3D / hermesworld | 별도 트랙. 본 통합에서는 제외 |
| TanStack Start 서버 | **제외** — 백엔드는 Python(B)로 통일. Vite SPA + Python API 로 단순화 |

상세 통합 방안은 [`06-integration-design.md`](./06-integration-design.md) 참조.
