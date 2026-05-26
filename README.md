<div align="center">

# hermes-agent-gui

### One GUI for [Hermes Agent](https://github.com/NousResearch/hermes-agent) · Web · PWA · Single-file · Electron

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Status](https://img.shields.io/badge/status-Phase_25_complete-2EA043.svg)](#%EF%B8%8F-roadmap)
[![Pytest](https://img.shields.io/badge/pytest-133_passed-2EA043.svg?logo=pytest&logoColor=white)](#-testing)
[![Vitest](https://img.shields.io/badge/vitest-20_passed-2EA043.svg?logo=vitest&logoColor=white)](#-testing)
[![Endpoints](https://img.shields.io/badge/endpoints-115-2EA043.svg)](#%EF%B8%8F-architecture)
[![Routes](https://img.shields.io/badge/routes-28-2EA043.svg)](#-project-structure)

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19.2-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-7-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind](https://img.shields.io/badge/Tailwind-v4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![TanStack](https://img.shields.io/badge/TanStack-Router_+_Query-FF4154?logo=react-query&logoColor=white)](https://tanstack.com/)

[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](./docker/)
[![PWA](https://img.shields.io/badge/PWA-installable-5A0FC8?logo=pwa&logoColor=white)](#%EF%B8%8F-build-targets)
[![Electron](https://img.shields.io/badge/Electron-desktop-47848F?logo=electron&logoColor=white)](./electron/)
[![Single-file](https://img.shields.io/badge/Single--file-HTML-ff6f61.svg)](#%EF%B8%8F-build-targets)
[![i18n](https://img.shields.io/badge/i18n-en_·_ko-blue.svg)](./apps/web/src/locales/)
[![Themes](https://img.shields.io/badge/themes-6-9333EA.svg)](#-features)

**단일 코드베이스, 4가지 산출물 · Multi-agent ready · Self-hosted · Zero-fork**

[✨ Highlights](#-highlights) · [📦 Features](#-features) · [🚀 Quick Start](#-quick-start) · [🏗️ Architecture](#%EF%B8%8F-architecture) · [🗺️ Roadmap](#%EF%B8%8F-roadmap) · [📖 Docs](./docs/review/)

</div>

---

## 🌟 Overview

`hermes-agent-gui` 는 [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) 위에 얹는 **통합 그래픽 인터페이스**다. 하나의 코드베이스에서 **웹 SPA · 모바일 PWA · 단일 HTML 파일 · 데스크탑 Electron** 4가지 산출물을 만들고, 백엔드는 Python 표준 라이브러리 + 2 의존성만 사용한다. Hermes Agent 본체에는 단 한 줄도 손대지 않는 **zero-fork** 통합을 유지.

```text
┌────────────┐    ┌────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Browser    │ ─▶ │ Vite SPA   │ ─▶ │ Python stdlib    │ ─▶ │ Hermes Agent    │
│ PWA · App  │    │ React 19   │    │ HTTP + SSE       │    │ (echo/gw/embed) │
└────────────┘    └────────────┘    └──────────────────┘    └─────────────────┘
                    28 routes         148 modules · 115 endpoints
```

---

## ✨ Highlights

| | |
| :-: | --- |
| 🏗️ | **26 phases · 100% complete** (Phase 0 → 25 + 14.5 hotfix). 별도 PR 단위로 분할 가능한 모듈 구조. |
| 🧪 | **130 pytest + 20 vitest 통과** (커버리지 ≥ 80%). Echo 모드로 Hermes 없이도 전 기능 검증. |
| 🔌 | **14 LLM provider** + **16 messaging platform** + **6 memory backend** + **5 코드 그래프 언어** plugin-style 통합. |
| 🧠 | **Transcript drift / tool-evidence repair · compression alias · auto-RAG · GBrain 합성 답변** — 모두 LLM-less 추출 기반. |
| 🛡️ | **다중 인증** (Password · Bearer · OAuth · WebAuthn passkey) + **fail-closed remote bind** + **exec feature gate** + **PII redact at ingress** + **11 패턴 log redact**. |
| 🎨 | **6 테마** (Hermes · Nous · Bronze · Slate · Mono · **Glass**) + 자체 `t()` i18n (en + ko) + custom dark variant. |
| 📦 | **단일파일 빌드** ≈ 800KB (curl + python 으로 배포). `vite-plugin-singlefile` + `serve_singlefile.py`. |
| 🐳 | **3종 Docker compose** (1/2/3 컨테이너) + Caddy 자동 TLS + `ctl.sh` 데몬 + 자동 업데이트. |

---

## 📦 Features

### 🧠 Chat & Conversation

| 기능 | 내용 |
| --- | --- |
| **Chat (SSE)** | `/api/chat/stream` · token/done/error 이벤트 · 자동 세션 영속화 · slash command intercept |
| **Sessions** | 5-모듈 라이프사이클 (lifecycle/recovery/events/ops/compression) · transcript drift / tool-evidence repair · compression alias 영속 |
| **Slash commands (22)** | `/new` `/clear` `/help` `/model` `/persona` `/usage` `/skills` `/memory` `/tools` `/web` `/browse` `/image` `/code` `/shell` `/compact` … |
| **Search (FTS5)** | `Cmd+K` 글로벌 검색 · incremental indexing · session id alias · porter unicode61 tokenizer |
| **Persona** | SOUL.md presets (6) · Monaco editor · 100KB 한도 · profile별 격리 |
| **Auto-Compress + RAG** | 임계값 40 turns / 75% context · lexical fallback (sqlite-vss optional) · top-k inject to system prompt |

### 🔌 LLM Providers & Tools

| 기능 | 내용 |
| --- | --- |
| **Multi-provider (14)** | OpenAI · Anthropic · Google · xAI · OpenRouter · Nous Portal · Qwen · MiniMax · HuggingFace · Groq · LM Studio · Ollama · vLLM · llama.cpp |
| **Model discovery** | `/v1/models` 5분 캐시 · provider-specific quirks (Anthropic 정적 / Google /v1beta / Ollama /api/tags) |
| **OAuth (PKCE S256)** | Nous Portal · OpenAI Codex |
| **Skills · MCP · Memory** | Hermes 본체 카탈로그 우선 + 로컬 폴백 (`~/.hermes/skills`, `mcp.json`, `memory/`) |

### 💬 Messaging Gateways (16 platforms)

| Mode | 플랫폼 |
| --- | --- |
| **위임 (14)** | Telegram · Discord · Slack · WhatsApp · Signal · Matrix · Mattermost · Email (IMAP/SMTP) · SMS (Twilio/Vonage) · iMessage (BlueBubbles) · DingTalk · Feishu/Lark · WeCom · WeChat |
| **Direct (2)** | **Webhook** (signed HMAC inbound) · **Home Assistant** (notify service) |

`~/.hermes/.env` atomic 0600 write · `delegate_probe.py` 가 Hermes 본체로 위임 호출 · 미실행 시 `HTTP 503 hermes_agent_not_running`.

### 🧬 Memory · Knowledge · Code

| 기능 | 내용 |
| --- | --- |
| **6 Memory plugins** | Honcho · Hindsight · Mem0 · RetainDB · Supermemory · ByteRover + local SQLite-VSS fallback |
| **PII redaction (8 패턴)** | SSN · 신용카드 · 이메일 · 한국 RRN · 전화번호 · IBAN · IP · custom regex · chat ingress hook + `pii_redacted` SSE 이벤트 + 인라인 badge |
| **GBrain (Knowledge Graph)** | LLM-less entity 추출 (정규식 11종) · typed edges (works_at/founded/attended/invested_in/...) · depth-bounded traversal · 합성 답변 + citations + gap analysis |
| **Code Knowledge Graph** | tree-sitter × 5 언어 (Python · TypeScript · JavaScript · Go · Rust) · `find_definition/find_references` tool · watchdog incremental re-index |

### 🗂️ Workspace · Terminal · Office

| 기능 | 내용 |
| --- | --- |
| **Workspace** | 파일 트리 · 인라인 에디터 (dirty state) · path traversal 가드 (`_safe_path()`) · 2MB inline read |
| **Real PTY** | stdlib `pty` 기반 · SSE 양방향 · idle 30분 자동 종료 · 명령 allowlist + `allow_unsafe` 우회 옵션 |
| **Browser-use** | Playwright 기반 · 도메인 화이트리스트 + private IP 차단 · 6 actions (navigate/click/type/screenshot/extract/eval) |
| **Office 3D (Claw3d)** | three.js + react-three-fiber + rapier · `VITE_FEATURE_3D=true` opt-in · lazy chunk · 모바일 자동 2D fallback |

### 📋 Tasks · Workflows · Multi-Agent

| 기능 | 내용 |
| --- | --- |
| **Kanban (7 lanes)** | backlog · ready · running · review · blocked · needs_you · done · aging (Done 2h / Needs-You 12h) |
| **Cron** | 5-필드 crontab + 백그라운드 scheduler + run-now · per-job last_run/exit_code/output |
| **Conductor + Swarm** | mission decompose (휴리스틱 role) · sanitize_mission (injection 가드) · tmux + subprocess fallback · auto-dispatch sub-tasks → workers |
| **Group Chat** | @-mention 라우팅 · 8자 초대 코드 (32^8) · multi-agent rooms · 각 participant 별 색상 bubble |
| **Multi-CLI Bridge** | Claude Code · Codex · Gemini · OpenCode · OpenClaw · 자동 PATH 감지 · `Engine` dropdown |
| **Agent Marketplace** | 30+ 큐레이션 preset · 1-click install (새 profile + SOUL.md + 스킬 자동) · 카테고리 그리드 |

### 📊 Dashboard · Usage · Operations

| 기능 | 내용 |
| --- | --- |
| **Dashboard** | sessions/tasks/cron 합계 · agent/system probe · Recharts (30-day token usage + 모델 분포) · 30s 자동 refresh |
| **Usage Analytics** | turn별 token I/O rollup · provider별 unit price · cache hit rate · KPI 4종 카드 · 일별 추세 차트 |
| **Inspector logs** | 11 패턴 redaction (OpenAI sk-* · Anthropic · AWS · JWT · GitHub PAT · Slack · Google · PEM · DB URL · Bearer · API key) · `/api/inspector/logs?lines=N` |
| **CLI maintenance** | `hermes-agent-gui clear-login-locks` · `reset-default-login` · `purge-old-sessions` · `doctor` (capabilities + health 진단) |

### 🎨 UX · Platform · Deploy

| 기능 | 내용 |
| --- | --- |
| **6 Themes** | Hermes (default) · Nous · Bronze · Slate · Mono · **Glass** (glassmorphism + Firefox 자동 backdrop-filter off) |
| **i18n** | English + 한국어 · `useT()` · locale store + fallback chain · 키 누락 시 영어 fallback → 키 자체 |
| **PWA** | service worker · network-only `/api/*` · CacheFirst assets · offline.html shell · iOS apple-touch-icon + web-app meta |
| **Sidebar groups** | 세션 사이드바를 source (Web/Telegram/Discord) 별 `<details>` 아코디언 |
| **Virtualized scroll** | React Virtuoso · 메시지 500개 초과 시 자동 활성 |
| **Backup/Debug dump** | tar.gz export (device-secret + passkeys.json + locks 제외) · zip debug dump (version + OS + capabilities + redacted logs) |
| **Auto-updater** | `electron-updater` 와이어 + GitHub Releases 채널 + renderer 알림 |
| **Docker** | 3종 compose (1-컨테이너 embedded / 2-컨테이너 agent+gui / 3-컨테이너 + Caddy 자동 TLS) |
| **Daemon** | `ctl.sh start/stop/restart/status/logs` · PID 파일 + `~/.hermes-agent-gui/gui.log` · one-line installer |

---

## 📋 Prerequisites

| 항목 | 최소 버전 | 비고 |
| --- | --- | --- |
| Python | `3.11+` | stdlib + `pyyaml` + `cryptography` |
| Node.js | `22+` | frontend build (Vite 7) |
| pnpm | `9+` | workspace package manager |
| Docker | (옵션) | 컨테이너 배포 시 |
| Hermes Agent | (옵션) | 미설치 환경에서도 `HERMES_GUI_FAKE_BACKEND=echo` 로 전체 빌드/테스트 가능 |
| `sqlite-vss` | (옵션) | Phase 18 벡터 RAG 가속 |
| `tree-sitter` + 5 grammars | (옵션) | Phase 22 코드 그래프 |
| Playwright + Chromium | (옵션) | Phase 23 browser-use |

---

## 🚀 Quick Start

### Mode 1 · 개발 (Vite HMR + 백엔드)

```bash
# 1. 백엔드 의존성 설치
pip install -r apps/server/requirements.txt

# 2. 백엔드 실행 (Echo 어댑터 — Hermes 불필요)
HERMES_GUI_PASSWORD=hermes-demo HERMES_GUI_FAKE_BACKEND=echo \
  python3 apps/server/server.py --host 127.0.0.1 --port 8800

# 3. 별도 터미널 — 프론트엔드 dev 서버
pnpm install
pnpm dev --port 5180 --host 127.0.0.1 --strictPort

# → http://localhost:5180/  ·  비밀번호: hermes-demo
```

### Mode 2 · Backend-only (SPA fallback 으로 단일 포트)

```bash
pnpm install && pnpm build

HERMES_GUI_PASSWORD=hermes-demo HERMES_GUI_FAKE_BACKEND=echo \
  python3 apps/server/server.py --host 127.0.0.1 --port 8800

# /api/*  → API 라우터
# 나머지  → apps/web/dist/index.html SPA fallback
curl http://127.0.0.1:8800/
curl http://127.0.0.1:8800/api/health
```

### Mode 3 · Single-file (curl + python = 동작)

```bash
pnpm --filter @hermes-agent-gui/web build:singlefile
# → apps/web/dist/index.html (외부 chunk 0개, 자산 인라인, ~800KB)

HERMES_GUI_PASSWORD=hermes-demo HERMES_GUI_FAKE_BACKEND=echo \
  python3 apps/server/serve_singlefile.py --port 8800
```

<details>
<summary>🔌 실 Hermes Agent 와 연결 (zero-fork 모드)</summary>

```bash
HERMES_GUI_PASSWORD=hermes-demo \
HERMES_API_URL=http://127.0.0.1:8642 \
HERMES_API_TOKEN=$API_SERVER_KEY \
  python3 apps/server/server.py --port 8800

# Runtime adapter 가 GatewayAdapter 자동 선택
# OpenAI · Responses · Agent 3종 endpoint 자동 probe + 캐싱
# → 채팅 turn 이 Hermes gateway 의 /v1/chat/completions 등으로 프록시
```
</details>

<details>
<summary>🐳 Docker (1/2/3-컨테이너)</summary>

```bash
# 1-컨테이너 — embedded 모드 (Hermes 본체를 같은 컨테이너에 임포트)
docker compose -f docker/docker-compose.yml up --build

# 2-컨테이너 — agent + gui 분리 (gateway 모드)
docker compose -f docker/docker-compose.two.yml up

# 3-컨테이너 — agent + gui + Caddy reverse proxy + 자동 TLS
docker compose -f docker/docker-compose.three.yml up
```
</details>

<details>
<summary>🖥️ Electron 데스크탑 (unsigned dev build)</summary>

```bash
pnpm --filter @hermes-agent-gui/electron build
# → release/{*.dmg, *.exe, *.AppImage}
#   macOS notarization + Windows code signing 은 후행 — unsigned dev build only
```
</details>

---

## 🏗️ Build Targets

```text
                    ┌────────── apps/web (단일 코드베이스) ──────────┐
                    │                                                  │
   pnpm dev       ─▶│  Vite dev server (HMR)                          │ → http://localhost:5180
   pnpm build     ─▶│  dist/  (SPA + PWA + manifest + sw.js)          │ → backend SPA fallback
   build:singlefile▶│  dist/index.html  (~800KB, all-in-one)          │ → serve_singlefile.py
   electron:build  ▶│  release/  (.dmg / .exe / .AppImage)            │ → Electron unsigned dev
                    │                                                  │
                    └──────────────────────────────────────────────────┘
```

| 빌드 | 명령 | 산출물 | 용도 |
| --- | --- | --- | --- |
| **SPA** (기본) | `pnpm build` | `dist/` + chunks | 일반 self-host |
| **PWA** | `pnpm build` | + `sw.js` + `manifest.webmanifest` | 모바일 설치 |
| **Single-file** | `pnpm build:singlefile` | `dist/index.html` (~800KB) | curl + python 배포 |
| **Electron** | `pnpm --filter @hermes-agent-gui/electron build` | `.dmg` · `.exe` · `.AppImage` | 데스크탑 |

---

## ⚙️ Configuration

핵심 환경변수 (기본값은 fail-closed):

| 변수 | 의미 | 기본 |
| --- | --- | --- |
| `HERMES_GUI_PASSWORD` | 비밀번호 로그인 | (미설정 시 password 로그인 비활성) |
| `HERMES_GUI_TOKEN` | Bearer 토큰 (API 직호출) | (미설정) |
| `HERMES_GUI_SECRET` | HMAC 쿠키 서명 키 | `~/.hermes-agent-gui/secret` 자동 생성 |
| `HERMES_GUI_FAKE_BACKEND` | `echo` 시 Hermes 없이 동작 | (미설정) |
| `HERMES_API_URL` | Hermes Agent gateway | `http://127.0.0.1:8642` |
| `HERMES_API_TOKEN` | gateway API key | (미설정) |
| `HERMES_GUI_STATE_DIR` | 상태 디렉토리 | `~/.hermes-agent-gui/` |
| `HERMES_GUI_WORKSPACES` | 워크스페이스 root 화이트리스트 | `$HOME` |
| `HERMES_GUI_FAIL_OPEN` | 외부 bind + auth 없음 허용 | `false` (권장 유지) |
| `HERMES_GUI_ENABLE_EXEC` | PTY/cron-shell/swarm-spawn 활성 | `false` |
| `HERMES_GUI_ALLOW_REMOTE_EXEC` | 외부 bind 환경에서도 exec 허용 | `false` |
| `HERMES_GUI_BROWSER_ALLOWLIST` | browser-use 도메인 화이트리스트 | `github.com,stackoverflow.com,…` |
| `HERMES_SWARM_WORKER_CMD` | Swarm worker 명령 템플릿 | `echo {role}:{text}` |
| `VITE_API_BASE` | dev 모드 API 프록시 타깃 | `http://127.0.0.1:8800` |
| `VITE_FEATURE_3D` | 3D Office lazy chunk 활성 | `false` |

<details>
<summary>🔐 Exec / PTY / Cron / Swarm 보안 기본값</summary>

명령 실행 계열 API는 모두 **기본 비활성**이다.

```bash
# 로컬에서만 명시적으로 활성화 (127.0.0.1 bind 필수)
HERMES_GUI_ENABLE_EXEC=1 HERMES_GUI_PASSWORD=hermes-demo \
  python3 apps/server/server.py --host 127.0.0.1 --port 8800

# 0.0.0.0 / LAN / Docker 노출 환경에서 exec 까지 허용하려면 추가 opt-in
HERMES_GUI_ENABLE_EXEC=1 HERMES_GUI_ALLOW_REMOTE_EXEC=1 \
HERMES_GUI_PASSWORD=hermes-demo \
  python3 apps/server/server.py --host 0.0.0.0 --port 8800
```

- 비활성 상태에서 `/api/terminal/exec` · `/api/pty` · `/api/cron` POST · `/api/swarm/workers` POST 는 `HTTP 403 exec_disabled` 응답
- 외부 bind + exec 요청 시 `HTTP 403 exec_remote_bind_disabled` (`ALLOW_REMOTE_EXEC=1` 없으면)
</details>

---

## 🏗️ Architecture

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│  Client (28 routes)                                                           │
│  apps/web — React 19 · TanStack Router + Query · Tailwind v4 · Zustand       │
│                                                                                │
│  /chat · /sessions · /workspace · /terminal · /messaging · /profiles ·       │
│  /providers · /persona · /usage · /rag · /memory · /brain · /code-graph ·    │
│  /browser · /office · /groups · /cli-bridges · /marketplace ·                │
│  /skills · /mcp · /tasks · /cron · /swarm · /dashboard · /settings · /login  │
│                                                                                │
│  Build plugins: vite-plugin-pwa · vite-plugin-singlefile · electron-builder  │
└──────────────────────────────────────────────────────────────────────────────┘
                                  ↓ HTTP + SSE  ↑
┌──────────────────────────────────────────────────────────────────────────────┐
│  apps/server — Python stdlib HTTP (framework-free) · 148 모듈 · 115 endpoints │
│  api/                                                                          │
│  ├─ auth · oauth · passkeys · streaming · runtime_adapter · chat              │
│  ├─ sessions/ {lifecycle, recovery, events, ops, compression, search}         │
│  ├─ workspace · terminal · pty · skills · mcp · memory · persona              │
│  ├─ tasks · cron · swarm/{foundation, missions, dispatch, conductor}          │
│  ├─ providers/{catalog, store, discovery, oauth/} · slash_commands            │
│  ├─ compression/{trigger, summarizer, embedder, vss_store, inject}            │
│  ├─ memory_providers/{honcho, mem0, hindsight, retaindb, supermemory, …}     │
│  ├─ brain/{extractor, graph, traversal, synthesizer, daemon} (GBrain)         │
│  ├─ codegraph/{indexer, parsers/, store, watcher, tools} (5 languages)        │
│  ├─ browser/{session, actions, allowlist, tools} (Playwright)                 │
│  ├─ groups/ · cli_bridges/ · marketplace/ · usage · backup · debug_dump       │
│  ├─ dashboard · telemetry · exec_policy · pii · profile_archive               │
│  └─ messaging/{registry, credentials, behavior, delegate_probe,               │
│                platforms/{14 delegated + 2 direct}}                            │
└──────────────────────────────────────────────────────────────────────────────┘
                                  ↓ echo / gateway / embedded
┌──────────────────────────────────────────────────────────────────────────────┐
│  Hermes Agent (NousResearch/hermes-agent) — 본체 미수정 (zero-fork)            │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Runtime Adapters (auto-select)

| 우선순위 | 모드 | 활성 조건 | 동작 |
| :-: | --- | --- | --- |
| 1 | **EchoAdapter** | `HERMES_GUI_FAKE_BACKEND=echo` | 사용자 입력 단어 단위 echo (dev/test) |
| 2 | **GatewayAdapter** | `HERMES_API_URL` 설정 | OpenAI · Responses · Agent endpoint 자동 probe + 캐시 |
| 3 | **EmbeddedAdapter** | `~/.hermes/hermes-agent` 존재 | `AIAgent` 클래스 동적 import (6 메서드 시그니처 자동 감지) |
| 4 | **NoBackendAdapter** | fallback | 명확한 `hermes_agent_not_configured` 에러 |

---

## 📁 Project Structure

```text
hermes-agent-gui/
├── apps/
│   ├── web/                      # React 19 + Vite SPA · 28 routes
│   │   ├── src/
│   │   │   ├── routes/           # file-based routing (TanStack)
│   │   │   ├── components/       # global-nav · slash-menu · model-picker ·
│   │   │   │                     # messaging-card · pii-redacted-badge · …
│   │   │   ├── lib/              # api.ts · auth.ts · chat-stream.ts · i18n.ts ·
│   │   │   │                     # slash-commands.ts · usage-pricing.ts · …
│   │   │   ├── stores/           # zustand (auth · theme · locale)
│   │   │   ├── hooks/            # use-mobile · use-session-events
│   │   │   ├── styles/           # globals.css (6 themes + dark variant)
│   │   │   └── locales/          # en.json · ko.json
│   │   ├── public/               # favicon · apple-touch-icon · offline.html
│   │   └── vite.config.ts        # multi-mode: spa | singlefile | electron
│   │
│   └── server/                   # Python stdlib HTTP · 148 modules · 115 endpoints
│       ├── server.py             # router + SPA fallback + security headers
│       ├── bootstrap.py          # interpreter ABI check + first-run installer
│       ├── serve_singlefile.py   # single-file deploy server
│       ├── cli.py                # hermes-agent-gui CLI (doctor, purge, …)
│       └── api/                  # 148 modules total
│           ├── auth · oauth · passkeys · streaming · runtime_adapter · chat
│           ├── sessions/         # 5 modules + search (FTS5)
│           ├── messaging/        # registry · credentials · 16 platforms
│           ├── providers/        # 14 LLM provider catalog + oauth
│           ├── compression/      # auto-RAG (trigger/summarizer/embedder/inject)
│           ├── brain/            # GBrain (extractor/graph/synthesizer/daemon)
│           ├── codegraph/        # tree-sitter × 5 languages
│           ├── memory_providers/ # 6 external plugins + local VSS
│           ├── browser/          # Playwright tool surface
│           ├── groups/           # multi-agent rooms
│           ├── cli_bridges/      # Claude Code · Codex · Gemini · …
│           ├── marketplace/      # 30+ preset library
│           ├── swarm/            # foundation · missions · dispatch · conductor
│           ├── workspace · terminal · pty · skills · mcp · memory · persona
│           ├── tasks · cron · dashboard · usage · telemetry
│           ├── pii · exec_policy · profile_archive · backup · debug_dump
│           └── slash_commands
│
├── electron/                     # Electron unsigned dev build
│   ├── main.cjs                  # backend child + autoUpdater (Phase 20)
│   ├── preload.cjs               # context-isolated bridge
│   └── package.json              # electron-builder targets
│
├── docker/                       # 1/2/3-container compose
│   ├── Dockerfile                # multi-stage: node22 build → python3.12 runtime
│   ├── docker-compose.yml        # 1-container (embedded)
│   ├── docker-compose.two.yml    # 2-container (agent + gui)
│   ├── docker-compose.three.yml  # 3-container (+ Caddy reverse proxy)
│   └── Caddyfile                 # 자동 TLS
│
├── scripts/
│   ├── ctl.sh                    # daemon start/stop/restart/status/logs
│   └── install.sh                # one-line installer
│
└── docs/review/                  # 14개 설계·리뷰 문서 (≈ 6,900 LOC)
    ├── 00-overview.md ~ 03-hermes-ui.md       (분석)
    ├── 04 ~ 06                                (매트릭스 · 결정 · 통합 설계)
    ├── 07 ~ 09                                (Phase 0~14 산출물)
    ├── 10-feature-roadmap-v2.md               (추가 오픈소스 분석)
    ├── 11-implementation-plan-full.md         (마스터 플랜 · 2,815 LOC)
    └── 12-impl-plan-checklist.md              (체크박스 + 137 테스트 케이스)
```

---

## ✅ Testing

| 영역 | 도구 | 상태 |
| --- | --- | --- |
| Backend unit + integration | pytest | **133 passed** (Phase 25 포함) |
| Frontend unit | vitest | **20 passed** |
| Frontend e2e | playwright | 회귀용 (선택) |
| Type check | `tsc --noEmit` | 0 errors |
| Lint | eslint flat config | `pnpm lint` |
| CI | GitHub Actions | `.github/workflows/{ci,security}.yml` |
| Security audit | `pip-audit` · `pnpm audit` | 주간 cron |

```bash
# Backend
cd apps/server && python3 -m pytest -v

# Frontend
cd apps/web && pnpm vitest run && pnpm typecheck && pnpm lint

# Docker smoke
docker build -f docker/Dockerfile -t hagi:ci . && \
  docker run --rm -d -p 8800:8800 -e HERMES_GUI_PASSWORD=ci hagi:ci && \
  sleep 5 && curl -fsS http://127.0.0.1:8800/api/health && \
  curl -fsSI http://127.0.0.1:8800/ | grep -qi 'text/html'
```

---

## 🔒 Security

### Defense in depth

```text
   ┌──────────────────────────────────────────────────────────────────────┐
1.  │  Network — fail-closed remote bind (host ≠ 127.0.0.1 + no auth → 거부)│
   └──────────────────────────────────────────────────────────────────────┘
   ┌──────────────────────────────────────────────────────────────────────┐
2.  │  Browser  — CSP · X-Frame-Options: DENY · X-Content-Type-Options · │
   │             Referrer-Policy · navigation NetworkFirst                │
   └──────────────────────────────────────────────────────────────────────┘
   ┌──────────────────────────────────────────────────────────────────────┐
3.  │  Auth     — Password · Bearer · HMAC cookie · OAuth (PKCE) ·       │
   │             WebAuthn passkey (ES256+RS256, CBOR RFC 8949 fix) ·    │
   │             login rate-limit 5/60s/IP · global POST 300/60s/IP    │
   └──────────────────────────────────────────────────────────────────────┘
   ┌──────────────────────────────────────────────────────────────────────┐
4.  │  Ingress  — PII redact at chat input (8 patterns + custom regex) ·│
   │             SSE pii_redacted event + inline badge                  │
   └──────────────────────────────────────────────────────────────────────┘
   ┌──────────────────────────────────────────────────────────────────────┐
5.  │  Data     — path traversal guard · _safe_path() · SQLite WAL ·    │
   │             credential 0600 atomic write · SQL parameterized only │
   └──────────────────────────────────────────────────────────────────────┘
   ┌──────────────────────────────────────────────────────────────────────┐
6.  │  Exec     — feature gate (HERMES_GUI_ENABLE_EXEC=1) · 2단계 opt-in │
   │             (ALLOW_REMOTE_EXEC) · cwd safe-path · command allowlist │
   └──────────────────────────────────────────────────────────────────────┘
   ┌──────────────────────────────────────────────────────────────────────┐
7.  │  Egress   — log redaction (11 patterns: OpenAI/Anthropic/AWS/JWT/  │
   │             GitHub PAT/Slack/Google/PEM/DB URL/Bearer/API key) ·  │
   │             archive 에서 device-secret/passkeys/locks 제외       │
   └──────────────────────────────────────────────────────────────────────┘
```

### Threat coverage

| 자산 | 위협 | 완화 |
| --- | --- | --- |
| `~/.hermes/.env` 봇 토큰 | 로컬 파일 노출 → 봇 hijack | 0600 + atomic write |
| HMAC secret | archive 유출 → 쿠키 위조 | archive 에서 `secret` 제외 (재로그인 1회) |
| Archive 무결성 | tar 변조 → path traversal RCE | MANIFEST SHA-256 checksum + `_safe_path()` |
| 사용자 PII | LLM provider 로 유출 | `api/pii.py` ingress hook (8 패턴) |
| Webhook 위조 | 임의 호출 → LLM 비용 청구 | unique secret URL + HMAC signature + 60/분 rate limit |
| Browser SSRF | private IP 스캔 | 도메인 화이트리스트 + RFC1918 차단 |
| OAuth CSRF | 계정 hijack | PKCE S256 + 1회용 state + 10분 TTL |
| Cron shell injection | RCE | `subprocess` shell=True + exec gate + audit log |
| LLM cost runaway | 자동 압축/합성 비용 폭주 | 사용자 컨펌 + daily budget (예정) |

---

## 🗺️ Roadmap

| Phase | Scope | 상태 |
| :-: | --- | :-: |
| **0** | Monorepo bootstrap · Vite SPA · Python `/api/health` | ✅ |
| **1** | Password + Bearer auth · OAuth/Passkey · SSE chat · echo/gateway/embedded adapter | ✅ |
| **2** | Session 5-module · transcript drift/tool-evidence repair · compression alias | ✅ |
| **3** | Workspace path-guard CRUD · terminal allowlist · 실 PTY (stdlib `pty`) | ✅ |
| **4** | Skills · MCP registry · Memory viewer | ✅ |
| **5** | Kanban 7 lanes + aging · 5-field cron + scheduler | ✅ |
| **6** | Conductor (mission decompose · sanitize) · Swarm (tmux + subprocess) · dispatch | ✅ |
| **7** | Health/Dashboard/Inspector · 11 redaction patterns | ✅ |
| **8** | PWA · service worker · offline shell · iOS icons · use-mobile | ✅ |
| **9** | 6 themes (Hermes · Nous · Bronze · Slate · Mono · Glass) · 3D feature flag | ✅ |
| **10** | Docker 1/2/3-container · Caddy · ctl.sh · bootstrap.py · install.sh | ✅ |
| **11** | Single-file build (`vite-plugin-singlefile` + `serve_singlefile.py`) | ✅ |
| **12** | Electron unsigned dev build + electron-builder targets | ✅ |
| **13** | i18n (en + ko) · `useT()` + locale store + fallback chain | ✅ |
| **14** | Tests/CI (pytest + vitest + GitHub Actions + security audit) | ✅ |
| **14.5** | Hotfix: SPA serving · PWA api no-cache · exec gate · passkey CBOR fix · workspace editor · lint gate · singlefile path | ✅ |
| **15** | Messaging Gateways (14 위임 + 2 direct: Webhook · HA) · Profile Archive (device-secret 제외) | ✅ |
| **16** | Multi-provider LLM (14 providers) · 22 slash commands · model picker | ✅ |
| **17** | Persona SOUL.md · FTS5 search (`Cmd+K`) · Usage analytics with Recharts | ✅ |
| **18** | Auto-compress + RAG (lexical fallback, optional `sqlite-vss`) | ✅ |
| **19** | Memory plugins (6) · PII redaction at input | ✅ |
| **20** | Group chat · Auto-updater · Backup/debug dump | ✅ |
| **21** | Knowledge graph (GBrain — entity + typed edges + synthesis + citations) | ✅ |
| **22** | Code knowledge graph (5 languages, tree-sitter optional) | ✅ |
| **23** | Computer/Browser-use (allowlist + private IP guard, Playwright optional) | ✅ |
| **24** | UX quick wins (sidebar groups · virtualized scroll · CLI maint · login lock UI) | ✅ |
| **25** | Office 3D (Claw3d) · Multi-CLI bridge · Agent marketplace | ✅ |

> **개발 가정**: Hermes Agent 미설치 환경에서도 전 phase 가 빌드/테스트되도록 `HERMES_GUI_FAKE_BACKEND=echo` 모드 + mock 으로 회귀. 실 Hermes 통합 검증은 사용자 환경에서 별도 수행.

---

## 🚧 Known Limitations

| 항목 | 상태 | 영향 |
| --- | --- | --- |
| Hermes Agent 실 환경 검증 | 미수행 | 적용 환경에서 EmbeddedAdapter/GatewayAdapter 시그니처 확인 필요 |
| Electron 코드사이닝 | unsigned only | macOS notarization · Windows EV cert (사용자 컨펌 필요) |
| Browser-use Playwright Chromium | 별도 설치 | `playwright install chromium` |
| LLM 비용 폭주 차단 | 사용자 경고만 | daily budget env 추가 예정 |
| Memory provider 6종 실 연동 | base interface | 각 외부 서비스 가입 시 검증 |
| Hermes 본체의 14 위임 메시징 platform | Hermes 본체 의존 | 본체 미설치 시 `503 hermes_agent_not_running` |
| `sqlite-vss` wheel 미지원 OS | lexical fallback | 옵션 dep — 미설치 시 자동 lexical RAG |
| 3D Office 모바일 | 자동 2D fallback | 의도된 동작 — three.js bundle 격리 보존 |

---

## 📖 Docs

[`docs/review/`](./docs/review/) 에 **14개 문서 · 약 6,900 LOC** 의 상세 자료:

| 문서 | 내용 |
| --- | --- |
| [`00-overview.md`](./docs/review/00-overview.md) | 전체 그림 + 확정 결정 요약 |
| [`01~03-*.md`](./docs/review/) | 3개 오픈소스 코드레벨 분석 (참고용 · **코드 복사 없음**) |
| [`04-feature-matrix.md`](./docs/review/04-feature-matrix.md) | 기능 비교 매트릭스 |
| [`05-conflict-resolution.md`](./docs/review/05-conflict-resolution.md) | 중복 충돌 해소 결정 (확정 사항 명시) |
| [`06-integration-design.md`](./docs/review/06-integration-design.md) | 통합 아키텍처 |
| [`07-phase-0-checklist.md`](./docs/review/07-phase-0-checklist.md) | Phase 0 체크리스트 |
| [`08-phase-1.md`](./docs/review/08-phase-1.md) | Phase 1 설계 |
| [`09-phase-2-to-14-summary.md`](./docs/review/09-phase-2-to-14-summary.md) | Phase 2~14 핵심 인터페이스 (Phase 14.5 hotfix 반영) |
| [`10-feature-roadmap-v2.md`](./docs/review/10-feature-roadmap-v2.md) | 추가 8개 오픈소스 분석 + Tier 1~3 |
| **[`11-implementation-plan-full.md`](./docs/review/11-implementation-plan-full.md)** | **마스터 플랜 · 2,815 LOC · §0 공통 표준 + 모든 Phase 의 12 섹션 상세 + 부록** |
| **[`12-impl-plan-checklist.md`](./docs/review/12-impl-plan-checklist.md)** | **실행 가능한 체크박스 + 137 테스트 케이스** |

---

## 🤝 Contributing

```bash
# 1. Fork + clone
git clone https://github.com/YOUR_FORK/hermes-agent-gui && cd hermes-agent-gui

# 2. 부팅 검증
pip install -r apps/server/requirements.txt && pnpm install
HERMES_GUI_PASSWORD=demo HERMES_GUI_FAKE_BACKEND=echo \
  python3 apps/server/server.py --port 8800 &
pnpm dev

# 3. 회귀 테스트 통과 확인
cd apps/server && python3 -m pytest -v
cd ../web && pnpm vitest run && pnpm typecheck && pnpm lint

# 4. feat/phase-N-short-name 분기 → PR
```

상세 컨벤션: [`docs/review/11-implementation-plan-full.md` §0 공통 표준](./docs/review/11-implementation-plan-full.md) 참조.

---

## 📜 License

[MIT](./LICENSE) — 본 프로젝트의 모든 코드는 본 저장소에서 **직접 작성된 원본**이다.
런타임에 통합하는 [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) (MIT) 만 [`NOTICE`](./NOTICE) 에 표기.

설계 단계에서 참고한 오픈소스 분석 (코드 복사 없음) 은 [`docs/review/01~03`](./docs/review/) 에 별도 보관.

---

<div align="center">

**[⬆ back to top](#hermes-agent-gui)**

Made with ⚡ from Python stdlib · React 19 · TanStack · Tailwind v4

</div>
