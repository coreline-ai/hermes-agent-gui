# 06 · 통합 신규 UI 아키텍처 / 구현 방안

> [`05-conflict-resolution.md`](./05-conflict-resolution.md) 에서 확정된 best-of-breed 결정을
> 구현 가능한 아키텍처로 펼친다.

---

## 1. 시스템 아키텍처

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Client (Browser / PWA / Electron renderer / single-file)                     │
│                                                                              │
│  apps/web — React 19 + TanStack Router/Query + Tailwind v4 + Zustand          │
│    ├─ packages/ui   ← A 컴포넌트 + C glassmorphism 토큰                       │
│    ├─ packages/gateway-client  ← REST + SSE 클라이언트                        │
│    └─ vite-plugin-pwa (B 패턴) / vite-plugin-singlefile (C 모드)              │
│                                                                              │
│         ↓ HTTP + SSE                                                         │
└──────────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│  apps/server — Python stdlib HTTP (B 포팅)                                    │
│                                                                              │
│  api/                                                                        │
│    ├─ auth.py, oauth.py, passkeys.py                  ← B                    │
│    ├─ session_{lifecycle,events,ops,recovery,…}.py   ← B + C 알고리즘 흡수    │
│    ├─ streaming.py (SSE half-close)                  ← B                    │
│    ├─ workspace.py, workspace_git.py, worktrees.py   ← B                    │
│    ├─ kanban_bridge.py + conductor.py (NEW)          ← B + A 재포팅           │
│    ├─ swarm/{foundation,lifecycle,missions,…}.py     ← A 재포팅                │
│    ├─ skills.py, mcp.py, memory.py                   ← B + A 패턴 흡수        │
│    ├─ terminal.py (xterm.js ↔ PTY)                   ← B + A pty-helper       │
│    ├─ {agent,system}_health.py + dashboard_probe.py  ← B                    │
│    └─ profiles.py, metering.py, usage.py             ← B                    │
│                                                                              │
│         ↓ in-process OR HTTP                                                 │
└──────────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────────────┐
│  Hermes Agent (NousResearch/hermes-agent)                                     │
│    ├─ AIAgent (in-process import — C 패턴) ─ "embedded mode"                 │
│    └─ gateway HTTP :8642 (+ dashboard :9119) ─ "zero-fork mode" (A 패턴)     │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 운영 모드 (두 가지 지원)

| 모드 | 사용처 | 진입 |
|------|--------|------|
| **Embedded** | 1-컨테이너, 로컬 self-host, 모바일 (C 처럼 직접 임포트) | `python3 bootstrap.py` |
| **Zero-fork** | 이미 Hermes Agent 가 돌고 있을 때 (A 처럼 gateway+dashboard 호출) | `HERMES_API_URL=... pnpm dev` |

`api/runtime_adapter.py`(B) 가 두 모드를 추상화. UI 는 동일 REST/SSE 만 호출.

---

## 2. 프로젝트 레이아웃 (monorepo)

```
hermes-agent-gui/
├── apps/
│   ├── web/                        # React 19 SPA (Vite)
│   │   ├── src/
│   │   │   ├── components/         # A 포팅 (~80개 — hermesworld 제외)
│   │   │   ├── hooks/              # A 포팅
│   │   │   ├── lib/                # A 포팅 + C 알고리즘 (transcript-repair.ts 등)
│   │   │   ├── routes/             # TanStack 파일 라우팅
│   │   │   ├── screens/            # 페이지 단위 view
│   │   │   ├── stores/             # zustand
│   │   │   ├── styles/             # Tailwind v4 + 6 테마 (Hermes/Nous/Bronze/Slate/Mono/Glass)
│   │   │   └── router.tsx
│   │   ├── public/                 # manifest.json + sw 등록 (vite-plugin-pwa 가 생성)
│   │   ├── index.html
│   │   ├── vite.config.ts          # multi-target: spa / pwa / singlefile / electron
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   └── server/                     # Python stdlib 백엔드
│       ├── api/                    # B 포팅 + 신규 모듈
│       ├── server.py               # thin shell (entry)
│       ├── bootstrap.py            # B 패턴 + C ABI 가드
│       ├── runtime_adapter.py
│       ├── requirements.txt        # pyyaml + cryptography
│       ├── pytest.ini
│       └── docs/
│
├── packages/
│   ├── ui/                         # 공유 UI primitives (CVA + Tailwind) — A `components/ui/`
│   │   ├── src/
│   │   ├── themes/                 # design tokens (5 + glass)
│   │   └── package.json
│   ├── gateway-client/             # REST/SSE 타입 + 클라이언트 — A `lib/gateway-api.ts` 진화형
│   ├── shared-types/               # zod schemas + 공통 타입
│   └── transcript-repair/          # C 알고리즘 TS 포팅
│
├── electron/                       # A 포팅 (옵션 빌드 타깃)
│   ├── main.cjs
│   ├── preload.cjs
│   ├── prod-server.cjs
│   └── electron-builder.config.cjs
│
├── scripts/
│   ├── ctl.sh                      # B 그대로
│   ├── install.sh                  # A one-line installer 변형
│   └── single-file-build.mjs       # vite-plugin-singlefile 산출
│
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml          # 1-컨테이너
│   ├── docker-compose.two.yml      # 2-컨테이너
│   └── docker-compose.three.yml    # 3-컨테이너
│
├── docs/
│   ├── review/                     # 본 문서 세트
│   ├── architecture/
│   ├── onboarding.md
│   ├── docker.md
│   └── why-hermes-agent-gui.md
│
├── e2e/                            # playwright (A 패턴)
├── pnpm-workspace.yaml
├── package.json
└── README.md
```

---

## 3. 빌드 타깃 매트릭스

`apps/web/vite.config.ts` 가 동일 코드베이스에서 **4가지 산출물**을 생성한다.

| 타깃 | 명령 | 산출물 | 용도 |
|------|------|--------|------|
| **spa** (기본) | `pnpm build` | `dist/index.html` + chunks | 일반 self-host |
| **pwa** | `pnpm build --mode pwa` | + `sw.js` + `manifest.json` (vite-plugin-pwa) | 모바일 설치 |
| **singlefile** | `pnpm build --mode singlefile` | `dist/hermes-agent-gui.html` (≈800KB est.) | C 모드 — curl + python 배포 |
| **electron** | `pnpm electron:build` | `.dmg` / `.exe` / `.AppImage` | 데스크탑 |

API URL 은 빌드 시 환경변수 (`VITE_API_BASE`) 또는 런타임 `window.__HERMES_GUI_CONFIG__` 로 주입.

---

## 4. 백엔드 API 표면 (REST + SSE)

> A 의 capability gate 패턴을 유지하기 위해, 모든 endpoint 가 `GET /api/capabilities` 에 자기 자신을 등록.

| 그룹 | 엔드포인트 | 출처 |
|------|-----------|------|
| 메타 | `GET /api/capabilities`, `GET /api/health`, `GET /api/version` | A + B |
| 인증 | `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`, OAuth callback, Passkey register/assert | B |
| 세션 | `GET/POST/DELETE /api/sessions`, `GET /api/sessions/{id}`, `GET /api/sessions/{id}/health` | B + C |
| 채팅 | `POST /api/chat/stream` (SSE), `POST /api/chat/cancel` | B |
| 워크스페이스 | `GET /api/workspaces`, `POST /api/workspaces`, `GET /api/workspaces/{id}/tree`, `GET/PUT/DELETE /api/workspaces/{id}/files`, git/worktree ops | B + C 가드 |
| 터미널 | `WS /api/terminal/{id}` (PTY) | B + A pty-helper |
| 작업 / 칸반 | `GET/POST /api/tasks`, `POST /api/conductor/dispatch`, `GET /api/conductor/missions/{id}` | B + A |
| Swarm | `GET /api/swarm/workers`, `POST /api/swarm/dispatch`, `GET /api/swarm/checkpoints` | A 재포팅 |
| Cron | `GET/POST/PUT/DELETE /api/cron`, `POST /api/cron/{id}/run` | B + A |
| Skills / MCP | `GET /api/skills`, `GET /api/mcp/catalog`, `POST /api/mcp/install` | A 패턴 + B 백엔드 |
| Memory | `GET /api/memory`, `PUT /api/memory/{path}` | A + B |
| Profiles | `GET /api/profiles`, profile-scoped 쿼리 (`?all_profiles=1`) | B |
| Usage / Metering | `GET /api/usage`, `GET /api/metering` | B |
| Upload | `POST /api/upload` (750MB 한도, 비디오 path-only) | B + C 패턴 |
| Telemetry | `POST /api/client-event` (rate-limited), `POST /api/csp-report` | B |

---

## 5. 핵심 통합 로직 — 6가지 코어 패턴

### 5.1 Capability Gate (A 패턴 유지)

```ts
// apps/web/src/lib/feature-gates.ts (A에서 포팅)
const caps = useQuery({ queryKey: ['caps'], queryFn: getCaps });
if (!caps.data?.conductor) return <PlaceholderPane feature="Conductor" />;
```

→ gateway 가 endpoint 미지원이어도 UI 가 깨지지 않음.

### 5.2 Session Health + Transcript Repair (C 알고리즘)

```python
# apps/server/api/session_recovery.py
def session_health(session_id):
    return {
        "server_messages": ...,        # 서버 세션 파일
        "browser_messages": ...,       # 브라우저 캐시 카운트 (요청 body)
        "compact_context_messages": ..., # compaction 후 model-facing 카운트
    }

def repair_transcript_drift(session, browser_transcript):
    # C v3.3.4~3.3.11 알고리즘:
    # 1) browser_messages > server_messages 이고 visible text 가 더 풍부 → 브라우저로 repair
    # 2) tool evidence (toolCalls) 있는 쪽 보존 — 단순 텍스트로 덮지 않음
    # 3) compression rotation alias 유지 (old_session_id → new_session_id)
    ...
```

### 5.3 Tool Honesty Guard (C v3.3.2)

```tsx
// apps/web/src/components/chat-panel/tool-honesty.tsx
{message.claimsLocalWork && !message.toolCalls.length && (
  <FlagBanner>Local work claimed but no tool ran — verify before trusting.</FlagBanner>
)}
```

### 5.4 Compose Work Banner (C v3.3.2)

컴포저 위에 활성 도구 호출 + 백그라운드 작업 + "Open Tasks" 액션 상시 표시.

### 5.5 Conductor / Swarm 디스패치 (A 재포팅)

```python
# apps/server/api/conductor.py
def dispatch_mission(prompt: str, mode: str = "decomposed") -> Mission:
    """A의 conductor-mission-sanitize.ts + swarm-missions.ts 의 Python 포팅."""
    sanitized = sanitize_mission(prompt)
    if mode == "decomposed":
        sub_tasks = decompose(sanitized)
        return spawn_workers(sub_tasks)
    return run_native_swarm(sanitized)
```

`api/swarm/foundation.py` 가 tmux 세션 매니저(A 의 `swarm-foundation.ts` 포팅) → role-based 워커.

### 5.6 Profile-Scoped Filtering (B 패턴)

모든 세션/프로젝트 쿼리는 기본적으로 `active_profile` 만 보여줌. `?all_profiles=1` 로 우회. `_profiles_match()` 가 default 와 renamed-root 충돌 처리.

---

## 6. 인증 흐름 (B 다층 통합)

```
사용자 진입
  ├─ 토큰 (Bearer) 헤더 있음 → API 토큰 인증
  ├─ 쿠키 있음 → HMAC 검증
  └─ 없음 → /login
       ├─ Passkey 등록/사용 (WebAuthn)
       ├─ OAuth (provider)
       └─ Password (HERMES_GUI_PASSWORD)
```

`api/auth.py` 가 미들웨어로 모든 라우트 보호. fail-closed remote bind (A 정책) — 외부 노출 시 password/Token 둘 다 없으면 거부.

---

## 7. 테마 시스템

```
apps/web/src/styles/themes/
├── hermes.css       # A 기본
├── nous.css         # A
├── bronze.css       # A
├── slate.css        # A
├── mono.css         # A
└── glass.css        # C — backdrop-filter, transparency, frosted utilities
```

Tailwind v4 의 CSS-first 토큰. `data-theme="glass"` 토글로 활성. Firefox 시 자동으로 blur off (C v3.3.13 성능 모드).

---

## 8. 단일파일 빌드 모드 (C 모드 대체)

```ts
// apps/web/vite.config.ts (mode === 'singlefile' branch)
import { viteSingleFile } from 'vite-plugin-singlefile';

export default defineConfig(({ mode }) => ({
  plugins: [
    react(), tailwind(),
    ...(mode === 'singlefile' ? [viteSingleFile()] : []),
    ...(mode === 'pwa' ? [VitePWA({/* B sw.js 정책 */})] : []),
  ],
  build: {
    target: 'es2022',
    rollupOptions: mode === 'singlefile' ? { /* inline assets */ } : undefined,
  },
}));
```

산출물 `dist/hermes-agent-gui.html` 을 `serve_static.py`(B 의 thin shell 변형) 와 함께 배포 → "curl + python = 동작" 의 C 철학 보존.

---

## 9. PWA 전략 (B 패턴 + vite-plugin-pwa)

- `manifest.json` — B 와 동일 구조 + 다국어 name (i18n)
- 서비스워커 — vite-plugin-pwa 가 생성. B 의 캐싱 정책 (`network-first` for API, `cache-first` for assets) 이식.
- 오프라인 시 핵심 UI 셸 + 마지막 세션 캐시 표시.

---

## 10. Docker / 배포

```
docker/
├── Dockerfile                      # B 베이스 + Node22 (Vite 빌드용 멀티스테이지)
├── docker-compose.yml              # 1-컨테이너 (embedded)
├── docker-compose.two.yml          # webui + agent 분리
└── docker-compose.three.yml        # + 보조 서비스 (redis/postgres 등 옵션)
```

- 멀티 아키텍처 GHCR 이미지 (amd64 + arm64) — B 패턴
- `~/.hermes`, `~/workspace` bind mount — B 패턴
- `WANTED_UID/WANTED_GID` 호스트 UID 매칭 — B 패턴

데몬 운영: `scripts/ctl.sh` (B 그대로).
- `./ctl.sh start|stop|restart|status|logs`
- PID: `~/.hermes/gui.pid`
- log: `~/.hermes/gui.log`

---

## 11. 보안 / 로그

| 항목 | 정책 |
|------|------|
| Path traversal | C 화이트리스트 (`_path_is_within_any`) + B 정규화 |
| Upload 한도 | 750MB (C), 비디오는 path-only |
| CSP report | B endpoint + rate limit (100/60s) |
| Client event | B endpoint + 화이트리스트 필드 + rate limit (30/60s) |
| Log redaction | C 정책 — UI 노출 로그는 토큰/키 패턴 자동 redact |
| Fail-closed remote bind | A 정책 — 외부 노출 시 auth 필수 |
| HTTPS | reverse proxy (Caddy/nginx) 권장 — README 가이드 |

---

## 12. Phase 기반 구현 로드맵

> 각 Phase 는 PR 단위로 머지 가능한 크기.

| Phase | 범위 | 산출물 | 의존성 |
|-------|------|--------|--------|
| **0. 부트스트랩** | 모노리포 골격, pnpm workspace, vite + python venv | `apps/web` Hello World, `apps/server` `/api/health` | - |
| **1. 인증 + 기본 채팅** | B `auth.py`/`oauth.py`/`passkeys.py` 이식, A `chat-panel`/`prompt-kit`/`use-chat-stream` 이식, SSE 스트리밍 | 로그인 → 채팅 1회전 | 0 |
| **2. 세션 라이프사이클** | B 5종 모듈 + C transcript repair · `/api/session/health` | 세션 생성/목록/스위치/복구 | 1 |
| **3. 워크스페이스 + 파일 + 터미널** | B `workspace*` + C path 가드, A `file-explorer` + Monaco, xterm.js + B PTY (A helper 흡수) | 파일 편집 + 터미널 | 2 |
| **4. 스킬 / MCP / 메모리** | A `/skills` `/mcp` `/memory` 페이지 + B skills 자가-개선 백엔드 | 카탈로그 + 메모리 라이브 편집 | 2 |
| **5. Tasks / 칸반 / Cron** | A TaskBoard + cron-manager, B `kanban_bridge.py` + cron 실행기, C aging 정책 | 칸반 보드 + cron 실행 | 2 |
| **6. Conductor + Swarm** | A `conductor*`/`swarm-*` Python 포팅, tmux 워커, role-based 디스패치 | 미션 분해 + Swarm 보드 | 5 |
| **7. 헬스 / 대시보드 / 인스펙터** | B health 모듈 4종 + C log redaction + A `dashboard-aggregator` 패턴 + A `inspector` | Health + Dashboard 페이지 | 1 |
| **8. PWA + 모바일** | vite-plugin-pwa + B manifest + A mobile-* 컴포넌트 + 3-panel 적응 + 비디오 업로드 (C) | 모바일에서 설치/사용 | 1~3 |
| **9. 테마 / 글래스모피즘** | A 5 테마 + C glass 토큰 + Firefox 가드 | 6 테마 토글 | 1 |
| **10. Docker / 데몬 / 인스톨러** | B `ctl.sh` + 3 compose + `bootstrap.py` (C ABI 가드 통합) + install.sh | self-host 1-cmd 부팅 | 0 |
| **11. 단일파일 빌드 모드** | `vite-plugin-singlefile` + `serve_static.py` | `hermes-agent-gui.html` 산출 | 1~9 일부 |
| **12. Electron** | A electron/* + builder + auto-update | DMG / EXE | 9 |
| **13. i18n + 다국어 README** | A i18n.ts + ko/en/zh-CN 카탈로그 | UI 언어 스위치 | 1 |
| **14. 테스트 / CI** | vitest + RTL + playwright + pytest + GitHub Actions (CI / docker / security) | 자동 회귀 | 모든 phase |

### 1차 PR 목표 권장 (제안)

**Phase 0 + 1 + 2 + 10 (인스톨러)** = "로그인하고 한 번 대화하고 세션이 복구되는 1차 self-hostable MVP". 이후 Phase 3~9 을 독립 PR 로.

---

## 13. 리스크 / 미해결 사항

| 리스크 | 영향 | 완화 |
|--------|------|------|
| A 의 Swarm/Conductor 를 Python 으로 포팅하는 비용 | Phase 6 작업량 큼 | TypeScript 로직을 그대로 두고 `subprocess.run(node, ...)` 호출하는 옵션 — 단, 의존성 트레이드오프 검토 |
| B 의 vanilla JS 에 박힌 UX 패턴(컴포저 footer ring 등) 재현 정확도 | 디자인 불일치 우려 | B 의 `static/style.css` + 스크린샷 비교 검증 단계 phase 별 포함 |
| C 의 transcript repair 가 v3.3.x 에 걸쳐 누적된 case-by-case 로직 | 일부 누락 가능성 | C 의 패치 노트를 테스트 케이스로 변환 (`tests/transcript_repair/v3.3.{n}.spec.py`) |
| Tailwind v4 의 안정성 | 일부 플러그인 미호환 | 필요 시 v3.4 fallback 유지 |
| Electron 빌드 종속성 | macOS 코드사이닝/notarization 비용 | 1차에는 unsigned dev build 만, 사용자 컨펌 후 정식 사이닝 |
| 라이선스 / NOTICE | MIT × 3 — 통합 가능하나 출처 명시 의무 | `NOTICE` 파일 + README "Built on the work of" 섹션 |

---

## 14. 인터페이스 호환성 약속

신규 GUI 는 다음을 보장한다:

1. **Hermes Agent 본체 미수정** — zero-fork, embedded 양쪽 모두에서 동작
2. **HERMES_API_URL / HERMES_DASHBOARD_URL / HERMES_API_TOKEN** 환경변수 호환 (A 와 동일)
3. **`HERMES_WEBUI_PASSWORD`** 환경변수 호환 (B 와 동일) — 비밀번호 단일 키로 통합
4. **`~/.hermes/` 디렉토리 호환** — workspaces.json, conversations.json 스키마는 B 와 C 의 union
5. **Hermes Agent 공식 인스톨러 자동 호출** (B `bootstrap.py` 패턴)

---

## 15. 다음 액션

1. 본 리뷰 문서 세트 (`docs/review/00-06`) 사용자 검토
2. [`05-conflict-resolution.md`](./05-conflict-resolution.md) 의 "비-결정 사항" 6개 컨펌
3. Phase 0 (모노리포 부트스트랩) 시작 — `apps/web` Hello World + `apps/server` `/api/health`
4. 이후 Phase 1~14 순차 PR

---

## 부록 A — 라이선스 / NOTICE 초안

```
hermes-agent-gui

Copyright (c) 2026 (your org)
Licensed under MIT.

Built on the work of:
- NousResearch / hermes-agent (MIT) — agent core
- outsourc-e / hermes-workspace (MIT) — frontend architecture, components, Swarm/Conductor
- nesquena / hermes-webui (MIT) — Python backend, PWA pattern, session lifecycle
- pyrate-llama / hermes-ui (MIT) — single-file build philosophy, transcript repair algorithms,
                                   glassmorphism design

See LICENSES/ for the full text of each upstream license.
```

## 부록 B — README 한줄 소개 (초안)

> **hermes-agent-gui** — One GUI for Hermes Agent.
> Web · PWA · Single-file · Electron. Multi-agent ready. Self-hosted.
> Born from three great open-source GUIs (workspace + webui + ui), unified into one.
