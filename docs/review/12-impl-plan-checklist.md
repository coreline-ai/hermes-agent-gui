# Implementation Plan: hermes-agent-gui (Phase 0 → 25)

> Phase 별 체크박스 태스크 + 테스트 케이스 + 실행 명령어로 구성된 실행 가능한 구현 계획서.
> Generated: 2026-05-26 (impl-plan skill v1)
> Project: hermes-agent-gui — One GUI for Hermes Agent
> 자매 문서: [`11-implementation-plan-full.md`](./11-implementation-plan-full.md) (설계·아키텍처 상세 — 본 체크리스트의 근거)

---

## 1. Context (배경)

### 1.1 Why (왜 필요한가)
NousResearch / hermes-agent 의 기능을 활용하려면 CLI 만으로 부족. 16 메시징 플랫폼 통합, 멀티 LLM provider, 페르소나 편집, 자동 컨텍스트 압축, 지식 그래프 같은 고가치 기능을 단일 GUI 로 노출. 8개 경쟁 오픈소스(누적 210K stars) 분석 후 best-of-breed 추출.

### 1.2 Current State (현재 상태)
- Phase 0~14 완료: 모노리포, 인증, 세션, 워크스페이스, 칸반, Conductor/Swarm, PWA, Docker, Electron, i18n, 38 pytest + 13 vitest 통과
- Phase 15 결정 확정 (2026-05-26): Hybrid 메시징 (14 위임 + 2 direct), Profile archive 확장 제외 리스트
- 개발 환경: Hermes Agent 미설치 — `HERMES_GUI_FAKE_BACKEND=echo` + mock 으로 빌드/테스트

### 1.3 Target State (목표 상태)
Phase 25 완료 시: 16 메시징 플랫폼 + 14 LLM provider + 22 slash 명령 + 페르소나 편집 + 풀텍스트 검색 + 자동 RAG + 6 메모리 plugin + 지식 그래프 + 코드 그래프 + 브라우저 자동화 + 멀티 CLI + 3D Office + 에이전트 marketplace 까지 갖춘 통합 GUI.

### 1.4 Scope Boundary (범위)
- **In scope**: Phase 0~25 (26 phases, 16주). 모든 백엔드 + 프론트엔드 + Docker + Electron + 단일파일 빌드.
- **Out of scope**:
  - Hermes Agent 본체 수정 (zero-fork 원칙)
  - Hermes Agent 가 제공하는 14 메시징 플랫폼의 실제 봇 구현 (위임)
  - 실 Hermes 환경에서의 통합 검증 (개발 완료 후 사용자 환경에서 별도)
  - Electron 코드사이닝 (사용자 컨펌 후 후행)

---

## 2. Architecture Overview (아키텍처)

### 2.1 Design Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Client (Browser / PWA / Electron / single-file)                          │
│  apps/web — React 19 + TanStack Router/Query + Tailwind v4 + Zustand     │
└──────────────────────────────────────────────────────────────────────────┘
                                   ↓ HTTP + SSE
┌──────────────────────────────────────────────────────────────────────────┐
│  apps/server — Python stdlib HTTP                                         │
│  api/ {auth,sessions,workspace,terminal,skills,mcp,memory,tasks,cron,     │
│        dashboard,swarm,messaging,providers,persona,compression,brain,     │
│        codegraph,browser,backup,...}                                      │
└──────────────────────────────────────────────────────────────────────────┘
                                   ↓ Echo / Gateway HTTP / Embedded import
┌──────────────────────────────────────────────────────────────────────────┐
│  Hermes Agent (NousResearch/hermes-agent) — 본체 미수정                  │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Design Decisions
| 결정 사항 | 선택 | 근거 |
|-----------|------|------|
| 라우팅 | SPA only (TanStack Router) | 인증 GUI SEO 불필요, 단일파일/Electron 호환 |
| 백엔드 언어 | Python stdlib + 2 deps (pyyaml/cryptography) | Hermes 와 같은 언어, 운영 단순도 |
| 단일파일 빌드 | vite-plugin-singlefile | C 패턴 보존 (curl + python = 동작) |
| 메시징 통합 (Phase 15) | **Hybrid**: 14 위임 + 2 direct (Webhook/HA) | Hermes 본체와 중복 회피 + Echo 환경 부분 동작 |
| Archive 정책 (Phase 15) | device-secret 제외 + 확장 패턴 | 클라우드 공유 가능 + 쿠키 위조 방어 |
| 인증 | OAuth + Passkey + Password + Bearer 다층 | best-of-breed (B 패턴) |
| 테마 | 6종 (Hermes/Nous/Bronze/Slate/Mono/Glass) | A 5종 + C glassmorphism |
| i18n | en + ko 1차 | 단일 언어로는 인프라 결함 미검출 |
| 3D | feature flag + lazy chunk | 모바일/단일파일 호환 보존 |
| RAG (Phase 18) | sqlite-vss | 단일파일 정합 |
| 코드 인덱싱 (Phase 22) | tree-sitter | 100% 로컬 |

### 2.3 New Files (Phase 15~25 신규 — 누적 88+)
| 영역 | 신규 파일 수 | 위치 |
|-----|-------------|------|
| Phase 15 messaging + archive | 18 backend + 5 frontend | `apps/server/api/messaging/`, `apps/web/src/routes/{messaging,profiles}.tsx` |
| Phase 16 providers + slash | 9 backend + 5 frontend | `apps/server/api/providers/`, `apps/web/src/components/chat/` |
| Phase 17 persona + fts + usage | 5 backend + 4 frontend | `apps/server/api/{persona,sessions/search,usage}.py` |
| Phase 18 compression + RAG | 6 backend + 1 frontend | `apps/server/api/compression/` |
| Phase 19 memory plugins + PII | 9 backend + 2 frontend | `apps/server/api/{pii.py, memory_providers/}` |
| Phase 20 group + updater + backup | 5 backend + 3 frontend | `apps/server/api/{groups/, backup.py}` |
| Phase 21 brain | 7 backend + 1 frontend | `apps/server/api/brain/` |
| Phase 22 codegraph | 9 backend + 2 frontend | `apps/server/api/codegraph/` |
| Phase 23 browser-use | 6 backend + 2 frontend | `apps/server/api/browser/` |
| Phase 24 UX | 2 backend + 4 frontend | `apps/server/cli.py`, virtuoso 등 |
| Phase 25 3D + multi-CLI + marketplace | 12 backend + 20+ frontend | `apps/web/src/feature-3d/`, `apps/server/api/{cli_bridges/, marketplace/}` |

### 2.4 Modified Files (확장)
- `apps/server/server.py` — Phase 마다 신규 라우터 와이어링
- `apps/server/api/chat.py` — Phase 18 RAG inject hook, Phase 19 PII redaction hook
- `apps/server/api/sessions/lifecycle.py` — Phase 17 FTS5 인덱싱 hook
- `apps/web/src/router.tsx` — Phase 마다 신규 route 추가
- `apps/web/src/components/global-nav.tsx` — 신규 라우트 메뉴 추가
- `apps/web/src/locales/{en,ko}.json` — Phase 마다 키 추가
- `apps/server/requirements.txt` — Phase 18/19/22/23 신규 의존성 추가

---

## 3. Phase Dependencies (페이즈 의존성)

```
0 ── 1 ── 2 ──┬── 3 ── 4 ── 5 ── 6
              │           ↓
              │           7 ── 8 ── 9 ── 10 ── 11 ── 12 ── 13 ── 14
              │
              └─→ 17 ── 18 ── 19 ── 21
                       │
                       └── 22 (Phase 3 끝나면 어디서든 가능)

15 ─┬─→ 16 ─→ 24-2 (profile-aware model)
    │       └→ 25-2 (multi-CLI)
    └─→ 24-5 (channel YAML)

12 ─→ 20-2 (auto-update)
 9 ─→ 25-1 (3D office)

23 ── 독립 (Phase 1 이후 어디서든)

모든 Phase → 14 (CI 회귀)
```

**Critical path**: `0 → 1 → 2 → 15 → 16 → 17 → 18 → 21`
**병렬 가능 트랙**: 22 (codegraph), 23 (browser-use), 25-1 (3D office)

---

## 4. Implementation Phases (구현 페이즈)

### Phase 0: Monorepo Foundation
> 모든 다른 페이즈의 전제 조건
> Status: ✅ Done
> Dependencies: 없음

#### Tasks
- [x] 루트 `package.json` (pnpm workspace) + `pnpm-workspace.yaml`
- [x] `apps/web/` Vite + React 19 + TanStack Router + Tailwind v4 + TypeScript
- [x] `apps/server/` Python stdlib HTTP server (`server.py`)
- [x] `/api/health` 엔드포인트 + `apps/server/api/health.py`
- [x] `apps/web/src/styles/globals.css` Tailwind v4 base
- [x] `LICENSE` (MIT) + `NOTICE` (3 upstream 출처) + `README.md`
- [x] `.gitignore` + `.editorconfig`

#### Success Criteria
- `python3 apps/server/server.py --port 8800` 부팅 + `/api/health` HTTP 200 반환
- `pnpm install && pnpm dev` 부팅 + `http://localhost:5173` 페이지 로드

#### Test Cases
- [x] TC-0.1: 서버 부팅 후 `curl http://127.0.0.1:8800/api/health` → `{"status":"ok"}`
- [x] TC-0.E1: 잘못된 경로 `curl /api/unknown` → HTTP 404 + `{"error":"not_found"}`

#### Testing Instructions
```bash
cd /Users/hwanchoi/project_202605/hermes-agent-gui
python3 apps/server/server.py --port 8800 &
curl -fsS http://127.0.0.1:8800/api/health
```

**테스트 실패 시 워크플로우**: 에러 분석 → 근본 원인 수정 → 재테스트 → 통과 후 다음 Phase 진행.

---

### Phase 1: Auth + SSE Chat
> 인증 (Password + Bearer + HMAC 쿠키) + SSE 채팅 (Echo/Gateway/Embedded adapter)
> Status: ✅ Done
> Dependencies: Phase 0

#### Tasks
- [x] `api/config.py` — env 로딩 + `~/.hermes-agent-gui/secret` 자동 생성
- [x] `api/auth.py` — login/logout/me + HMAC 쿠키 + bearer token + rate limit
- [x] `api/router.py` — path → handler 디스패처 (Request/Response/Router)
- [x] `api/streaming.py` — SSE half-close 처리 + token/done/error 이벤트
- [x] `api/runtime_adapter.py` — Echo/Gateway/Embedded/NoBackend 어댑터
- [x] `api/chat.py` — POST /api/chat/stream + 세션 자동 저장
- [x] `api/oauth.py` + `api/passkeys.py` — 실 구현 (OIDC + PKCE / WebAuthn ES256+RS256)
- [x] `apps/web/src/routes/{login,chat}.tsx` + `lib/{auth,chat-stream}.ts` + `stores/auth-store.ts`

#### Success Criteria
- 비밀번호 로그인 → 쿠키 발급 → `/api/auth/me` 200 응답
- 채팅 메시지 → SSE 4개 이상의 `token` 이벤트 + 1개의 `done` 이벤트
- `HERMES_GUI_FAKE_BACKEND=echo` 환경에서 Hermes 없이 1회전 동작

#### Test Cases
- [x] TC-1.1: 비밀번호 정답 → HTTP 200 + Set-Cookie 헤더
- [x] TC-1.2: 비밀번호 오답 5회 → HTTP 429 `rate_limited`
- [x] TC-1.3: Bearer 토큰으로 `/api/auth/me` 인증
- [x] TC-1.4: 채팅 stream → token + done 이벤트
- [x] TC-1.E1: 쿠키 없이 `/api/auth/me` → HTTP 401 `not_authenticated`
- [x] TC-1.E2: OAuth provider env 미설정 → HTTP 501 `oauth_not_configured`

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_auth_flow.py -v
```

---

### Phase 2: Sessions + Transcript Repair
> 세션 5 모듈 + transcript drift repair + compression alias
> Status: ✅ Done
> Dependencies: Phase 1

#### Tasks
- [x] `api/sessions/lifecycle.py` — `SessionStore` SQLite WAL CRUD
- [x] `api/sessions/recovery.py` — `session_health()` + `repair_transcript_drift()`
- [x] `api/sessions/events.py` — pub/sub for `/api/sessions/_stream`
- [x] `api/sessions/compression.py` — alias persistence
- [x] `api/sessions/ops.py` — HTTP CRUD 라우트
- [x] `api/chat.py` 확장 — turn 자동 영속화 (user + assistant)
- [x] `api/runtime_adapter.py` `EmbeddedAdapter` — `AIAgent` 다중 시그니처 감지

#### Success Criteria
- Session create → get → append → drift repair → delete 사이클 동작
- Browser_ahead drift 감지 + 자동 repair (browser 메시지 더 많을 때)

#### Test Cases
- [x] TC-2.1: Session CRUD (create/list/rename/delete)
- [x] TC-2.2: Drift `browser_ahead` 감지 + 자동 merge
- [x] TC-2.3: Drift `server_ahead` 감지 (repair 안 함)
- [x] TC-2.4: `compact_stale` 감지
- [x] TC-2.5: Compression alias 다중 hop 해소
- [x] TC-2.E1: 존재하지 않는 session_id → HTTP 404 `session_not_found`

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_sessions.py tests/test_repair_alias.py -v
```

---

### Phase 3: Workspace + Terminal + Real PTY
> 파일 CRUD with path guard + terminal allowlist + 실 PTY (P1#5)
> Status: ✅ Done
> Dependencies: Phase 1

#### Tasks
- [x] `api/workspace.py` — `_safe_path()` + list/read/write/delete + 2MB inline
- [x] `api/terminal.py` — allowlist (ls/grep/git/python3/etc) + 30s timeout
- [x] `api/pty.py` — stdlib `pty` + SSE 양방향 + idle timeout 30분
- [x] `apps/web/src/routes/{workspace,terminal}.tsx`

#### Success Criteria
- 워크스페이스 외부 경로 (`../../../etc/passwd`) 접근 차단
- Allowlist 외 명령 (`rm -rf /`) 차단
- 실 PTY 세션 → SSE 양방향 입출력

#### Test Cases
- [x] TC-3.1: 워크스페이스 내 파일 read/write 성공
- [x] TC-3.2: `ls` exec → exit_code 0 + stdout
- [x] TC-3.E1: `../../../etc/passwd` → HTTP 400 `bad_path`
- [x] TC-3.E2: `rm -rf /` → HTTP 403 `command_not_in_allowlist`

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_workspace_terminal.py -v
```

---

### Phase 4: Skills + MCP + Memory
> Hermes 본체 카탈로그 우선 + 로컬 폴백
> Status: ✅ Done
> Dependencies: Phase 1

#### Tasks
- [x] `api/skills.py` — gateway `/v1/skills` 또는 `~/.hermes/skills/` 스캔
- [x] `api/mcp.py` — `~/.hermes/mcp.json` CRUD + gateway 프록시
- [x] `api/memory.py` — `~/.hermes/memory/*.md` 브라우저

#### Success Criteria
- 3 영역 모두 Hermes 미실행 시 로컬 폴백 동작
- MCP server CRUD (add/list/remove)

#### Test Cases
- [x] TC-4.1: Skills 로컬 폴백 (~/.hermes/skills 없으면 빈 배열)
- [x] TC-4.2: MCP add → list → remove 사이클
- [x] TC-4.3: Memory 루트 미존재 시 `exists: false`

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_skills_mcp_memory.py -v
```

---

### Phase 5: Tasks (Kanban) + Cron
> 7 lanes + aging + 5-field crontab + background scheduler
> Status: ✅ Done
> Dependencies: Phase 1

#### Tasks
- [x] `api/tasks.py` — backlog/ready/running/review/blocked/needs_you/done + aging (2h/12h)
- [x] `api/cron.py` — 5-field 파서 + 백그라운드 스케줄러 + `run_now`
- [x] Lane transition + bad lane 검증

#### Success Criteria
- Task 생성 → 레인 전환 → 만료 (done > 2h) 자동 삭제
- Cron 잡 생성 → 다음 분에 자동 실행

#### Test Cases
- [x] TC-5.1: Task create → lane=done → 만료 검증
- [x] TC-5.2: Cron `*/5 * * * *` 형식 파싱
- [x] TC-5.E1: 잘못된 lane → HTTP 400 `bad_lane`
- [x] TC-5.E2: 잘못된 cron 표현 → HTTP 400 `bad_schedule`

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_tasks_cron.py -v
```

---

### Phase 6: Conductor + Swarm
> Mission decompose + tmux/subprocess workers + dispatch
> Status: ✅ Done
> Dependencies: Phase 1, 5

#### Tasks
- [x] `api/swarm/foundation.py` — `SwarmFoundation` tmux 우선 + subprocess 폴백
- [x] `api/swarm/missions.py` — `decompose_mission(prompt)` 휴리스틱 role 분해
- [x] `api/swarm/conductor.py` — `sanitize_mission()` injection 가드
- [x] `api/swarm/dispatch.py` — Mission → workers spawn (P1#6)
- [x] `api/swarm/routes.py` — workers + missions HTTP API

#### Success Criteria
- Mission decompose → builder/reviewer/qa 등 role 자동 분류
- `dispatch: true` 시 sub-task 별 worker spawn

#### Test Cases
- [x] TC-6.1: Conductor decompose — 3 문장 → 3 sub_tasks
- [x] TC-6.2: Auto-dispatch — workers 카운트 = sub_tasks 카운트
- [x] TC-6.3: Worker spawn → kill 사이클

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_swarm_conductor.py -v
```

---

### Phase 7: Health + Dashboard + Inspector
> Agent probe + system stats + redacted logs + dashboard 합계
> Status: ✅ Done
> Dependencies: Phase 1, 2, 5

#### Tasks
- [x] `api/dashboard.py` — 11 redaction 패턴 (OpenAI/AWS/JWT/PEM/DB/Anthropic 등)
- [x] `_probe_gateway()` + `_system_stats()` + `_dashboard_summary()`
- [x] `/api/inspector/logs?lines=N` (redacted)

#### Success Criteria
- 11 redaction 패턴이 적용되어 로그 노출 시 secret 0
- Dashboard 합계 (sessions/tasks/cron) 정확

#### Test Cases
- [x] TC-7.1: OpenAI sk- 키 redact
- [x] TC-7.2: AWS access key (AKIA...) redact
- [x] TC-7.3: JWT 토큰 redact
- [x] TC-7.4: PEM 블록 redact
- [x] TC-7.5: DB connection string redact
- [x] TC-7.E1: `/api/health/agent` Hermes 미실행 시 `configured: false`

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_dashboard_redact.py -v
```

---

### Phase 8: PWA + Mobile
> vite-plugin-pwa + offline shell + iOS icons + mobile hook
> Status: ✅ Done
> Dependencies: Phase 0

#### Tasks
- [x] `apps/web/vite.config.ts` — VitePWA 플러그인 + service worker
- [x] `apps/web/public/{offline.html, apple-touch-icon.svg}` — iOS web-app 메타
- [x] `apps/web/src/hooks/use-mobile.ts` — 반응형 hook

#### Success Criteria
- 빌드 산출물에 `manifest.webmanifest` + `sw.js` 포함
- 오프라인 상태에서 `/offline.html` fallback

#### Test Cases
- [x] TC-8.1: `pnpm build` → `dist/manifest.webmanifest` 존재
- [x] TC-8.2: Service worker 등록 후 navigation cache 동작

#### Testing Instructions
```bash
cd apps/web && pnpm build && ls dist/manifest.webmanifest dist/sw.js
```

---

### Phase 9: Themes (6) + 3D Feature Flag
> Hermes/Nous/Bronze/Slate/Mono/Glass + custom dark variant + 3D opt-in
> Status: ✅ Done
> Dependencies: Phase 0

#### Tasks
- [x] `apps/web/src/styles/globals.css` — `@custom-variant dark` + 6 테마 변수
- [x] `apps/web/src/stores/theme-store.ts` — `THEMES` + localStorage 영속화
- [x] `apps/web/src/components/agent-avatar.tsx` — `VITE_FEATURE_3D` lazy chunk

#### Success Criteria
- 6 테마 모두에서 border 가 visible (모노/슬레이트/글래스 dark variant 발화)
- Glass 테마에서 Firefox 자동 backdrop-filter off (CPU 보호)

#### Test Cases
- [x] TC-9.1: Theme store 기본값 `hermes`
- [x] TC-9.2: `setTheme('glass')` → `data-theme="glass"` + localStorage 저장
- [x] TC-9.3: 컴파일된 CSS 에 `[data-theme="mono"]` 셀렉터 ≥ 25개

#### Testing Instructions
```bash
cd apps/web && pnpm vitest run tests/theme-store.test.ts
```

---

### Phase 10: Docker + ctl.sh + bootstrap.py + install.sh
> 1/2/3-컨테이너 compose + daemon wrapper + first-run installer
> Status: ✅ Done
> Dependencies: Phase 0, 1

#### Tasks
- [x] `docker/Dockerfile` — node22 build → python3.12 runtime multi-stage
- [x] `docker/{docker-compose.yml, docker-compose.two.yml, docker-compose.three.yml}` + `Caddyfile`
- [x] `scripts/ctl.sh` — start/stop/restart/status/logs
- [x] `apps/server/bootstrap.py` — interpreter ABI check + Hermes auto-installer + health 대기
- [x] `scripts/install.sh` — one-line installer

#### Success Criteria
- `./ctl.sh start` → 백그라운드 데몬 + PID 파일 + `/api/health` 응답
- `python3 bootstrap.py` → Hermes 미설치 감지 + 옵션 설치 prompt

#### Test Cases
- [x] TC-10.1: `ctl.sh start` → PID 파일 + 5초 내 health probe 200
- [x] TC-10.2: `ctl.sh status` → "running: pid X" 출력
- [x] TC-10.3: `ctl.sh stop` → PID 파일 제거

#### Testing Instructions
```bash
./scripts/ctl.sh start && sleep 2 && ./scripts/ctl.sh status && ./scripts/ctl.sh stop
```

---

### Phase 11: Single-File Build
> vite-plugin-singlefile + 단일 HTML + Python proxy
> Status: ✅ Done
> Dependencies: Phase 0, 1

#### Tasks
- [x] `apps/web/vite.config.ts` — `mode === 'singlefile'` 분기
- [x] `apps/server/serve_singlefile.py` — API + 단일 HTML 동시 서빙

#### Success Criteria
- `pnpm build:singlefile` → `dist/index.html` ≤ 1MB
- `serve_singlefile.py` 부팅 → 단일 HTML 응답

#### Test Cases
- [x] TC-11.1: 빌드 후 `dist/index.html` 존재 + 외부 chunk 0
- [x] TC-11.2: serve_singlefile.py → `GET /` 200 + Content-Type text/html

#### Testing Instructions
```bash
cd apps/web && pnpm build:singlefile && du -h dist/index.html
```

---

### Phase 12: Electron Desktop
> main + preload + builder + auto-update 설정 (와이어링 Phase 20)
> Status: ✅ Done
> Dependencies: Phase 0, 11

#### Tasks
- [x] `electron/main.cjs` — Python child + BrowserWindow + health 대기
- [x] `electron/preload.cjs` — context bridge
- [x] `electron/package.json` — electron-builder DMG/EXE/AppImage 설정

#### Success Criteria
- `pnpm electron:dev` 실행 → Python 백엔드 자동 spawn + BrowserWindow 표시

#### Test Cases
- [x] TC-12.1: electron 패키지 메타 + entry point `main.cjs`
- [x] TC-12.E1: 백엔드 health probe 실패 → 자동 종료

---

### Phase 13: i18n (en + ko)
> 자체 t() + locale store + 30+ keys + fallback chain
> Status: ✅ Done
> Dependencies: Phase 0

#### Tasks
- [x] `apps/web/src/lib/i18n.ts` — `useT()` + `t(key, params)` + locale store
- [x] `apps/web/src/locales/{en,ko}.json` — 30+ 키
- [x] Settings 페이지에 언어 토글

#### Success Criteria
- 로케일 전환 시 모든 컴포넌트 재렌더
- 키 누락 시 영어 fallback → 마지막엔 키 자체 반환

#### Test Cases
- [x] TC-13.1: 기본 영어 → `t('auth.signIn')` = "Sign in"
- [x] TC-13.2: 한국어 전환 → "로그인"
- [x] TC-13.E1: 알 수 없는 키 → 키 자체 반환

#### Testing Instructions
```bash
cd apps/web && pnpm vitest run tests/i18n.test.ts
```

---

### Phase 14: Tests + CI + Security Audit
> pytest 38 + vitest 13 + GitHub Actions + pip-audit/pnpm-audit
> Status: ✅ Done
> Dependencies: 모든 Phase

#### Tasks
- [x] `apps/server/tests/conftest.py` — `server` + `client` fixture
- [x] `apps/server/tests/test_*.py` 10 파일 → 38 케이스
- [x] `apps/web/tests/*.test.ts` 4 파일 → 13 케이스
- [x] `.github/workflows/ci.yml` — pytest + web build + docker smoke
- [x] `.github/workflows/security.yml` — pip-audit + pnpm-audit (주간)

#### Success Criteria
- pytest 38/38 통과 (라인 커버리지 ≥ 70%)
- vitest 13/13 통과
- CI 모든 잡 green

#### Test Cases
- [x] TC-14.1: 전체 pytest 통과
- [x] TC-14.2: 전체 vitest 통과
- [x] TC-14.3: docker build → health 30s 내 응답

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest -v
cd ../web && pnpm vitest run
```

---

### Phase 14.5: Pre-Phase-15 Hotfix / Production Readiness Gate
> Phase 15 진입 전 baseline 결함 제거
> Status: ✅ Implemented + verified (`pytest` 51/51)
> Dependencies: Phase 14

#### Tasks
- [x] P1-4 Passkey CBOR/COSE negative integer decoding 수정 (`-1 - n`)
- [x] P0-1 `server.py` SPA static serving + history fallback 추가
- [x] P0-2 ESLint dependency/config + `pnpm lint` CI gate 추가
- [x] P1-3 Workbox `/api/*` runtime cache 제거 + 기존 `api` cache cleanup 추가
- [x] P1-5 terminal/PTY/cron/swarm 공통 exec feature gate 추가
- [x] P2-6 workspace editor render-time draft overwrite 제거
- [x] P2-7 singlefile 기본 HTML 경로를 `apps/web/dist/index.html`로 정렬
- [x] README/SECURITY/plan 문서 동기화

#### Success Criteria
- `/`, `/chat` → 200 `text/html`
- `/api/health` → 200 JSON
- `HERMES_GUI_ENABLE_EXEC` 미설정 시 exec 계열 API → 403 `exec_disabled`
- `dist/sw.js`에 `/api/` NetworkFirst cache 없음
- `pnpm build:singlefile` 산출물을 `serve_singlefile.py` 기본값으로 서빙 가능

#### Test Cases
- [x] TC-14.5.1: ES256 COSE `alg=-7` decode
- [x] TC-14.5.2: RS256 COSE `alg=-257` decode
- [x] TC-14.5.3: malformed CBOR reject
- [x] TC-14.5.4: SPA root/history/static asset/API passthrough
- [x] TC-14.5.5: terminal/cron/swarm exec-disabled regression

#### Testing Instructions
```bash
python3 -m pytest apps/server -q
pnpm lint
pnpm typecheck
pnpm --filter @hermes-agent-gui/web test
pnpm build
pnpm --filter @hermes-agent-gui/web build:singlefile
```

---

### Phase 15a: Messaging — Foundation + 14 Delegated Platforms
> Hermes 본체 위임 모드 — 14 플랫폼의 credential UI + behavior YAML 편집
> Status: ✅ Implemented + verified (`pytest` 69/69)
> Dependencies: Phase 1, 2 (profile), 7 (health)

#### Tasks
- [x] `api/messaging/models.py` — `PlatformMeta`, `CredentialField`, `PlatformStatus` dataclasses
- [x] `api/messaging/registry.py` — 16 PlatformMeta 정의 (14 mode='delegated' + 2 mode='direct')
- [x] `api/messaging/credentials.py` — `write_credential()` atomic 0600 + merge
- [x] `api/messaging/behavior.py` — `~/.hermes/config.yaml` 읽기/쓰기 (pyyaml)
- [x] `api/messaging/status.py` — `messaging_status` SQLite 테이블 + `record_event()`
- [x] `api/messaging/delegate_probe.py` — 위임 14의 `test_connection` → Hermes `/v1/messaging/test/{platform}` 호출
- [x] `api/messaging/platforms/{base, telegram, discord, slack, whatsapp, signal, matrix, mattermost, email, sms, imessage, dingtalk, feishu, wecom, wechat}.py` — 얇은 wrapper

#### Success Criteria
- `GET /api/messaging/platforms` → 16 PlatformMeta 반환 (14 delegated + 2 direct 분류 명확)
- 14 위임 플랫폼 `POST /configure` → credential 0600 권한으로 `~/.hermes/.env` 저장
- Telegram bot_token 정규식 `^[0-9]+:[A-Za-z0-9_-]+$` 검증
- Hermes 미실행 시 `POST /test` → HTTP 503 `hermes_agent_not_running`

#### Test Cases
- [x] TC-15a.1: `GET /api/messaging/platforms` → 16 행 응답 + 모드 분류
- [x] TC-15a.2: Telegram credential 정규식 OK 케이스 5개
- [x] TC-15a.E1: Telegram credential 정규식 NG → HTTP 400 `invalid_credential`
- [x] TC-15a.3: Credential write atomic + 0600 권한 검증
- [x] TC-15a.4: Credential merge — 기존 키 보존
- [x] TC-15a.E2: Hermes 미실행 → `test_connection` HTTP 503 `hermes_agent_not_running`
- [x] TC-15a.5: `messaging_status` 테이블 schema 생성 + index

#### Testing Instructions
```bash
# 1. 단위 테스트
cd apps/server && python3 -m pytest tests/test_messaging_registry.py tests/test_messaging_creds.py tests/test_platforms_delegated.py -v

# 2. 통합 smoke
HERMES_GUI_PASSWORD=x HERMES_GUI_FAKE_BACKEND=echo HERMES_GUI_STATE_DIR=/tmp/p15a python3 server.py --port 18815 &
curl -sS -c /tmp/c.txt -X POST localhost:18815/api/auth/login -d '{"password":"x"}' -H 'content-type: application/json'
curl -b /tmp/c.txt localhost:18815/api/messaging/platforms | python3 -m json.tool
```

---

### Phase 15b: Messaging — 2 Direct Platforms (Webhook + HA)
> 직접 구현 — Hermes 미실행 환경에서도 동작
> Status: ✅ Implemented + verified (`pytest` 75/75)
> Dependencies: Phase 15a, 1, 16 (chat 호출 위해 provider 필요할 수도 — adapter 가 처리)

#### Tasks
- [x] `api/messaging/platforms/webhook.py` — endpoint 등록 + 고유 secret URL 발급 + HMAC signature 검증
- [x] `api/messaging/webhook_inbound.py` — `POST /api/messaging/webhook/{token}/inbound` 핸들러
- [x] `api/messaging/platforms/home_assistant.py` — webhook 기반 + HA REST API 호출 (`notify.X` service)
- [x] Webhook 입력 → `chat.py` 의 stream 호출 위임 → 결과를 outbound 호출
- [x] `messaging_status` 업데이트 (last_event_at) — Phase 15a 의 status 모듈 활용
- [x] Rate limit (분당 60 req/webhook) + payload size 한도 (256KB)

#### Success Criteria
- `POST /api/messaging/webhook/{token}/inbound` → 메시지 chat 흐름 통과 → HTTP 200
- 잘못된 signature → HTTP 401 `webhook_signature_invalid`
- HA notify 호출 → mock REST 응답 검증

#### Test Cases
- [x] TC-15b.1: Webhook 등록 → secret URL 발급
- [x] TC-15b.2: 유효 signature 인바운드 → chat 응답 outbound
- [x] TC-15b.E1: 잘못된 signature → HTTP 401
- [x] TC-15b.E2: Payload > 256KB → HTTP 413
- [x] TC-15b.3: HA notify 호출 mock 응답 검증
- [x] TC-15b.4: Rate limit 60/분 초과 → HTTP 429

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_platform_webhook.py tests/test_platform_home_assistant.py -v
```

---

### Phase 15c: Messaging Frontend + Profile Archive
> 16 카드 그리드 UI + tar.gz 백업/복구
> Status: ✅ Implemented + verified (`pytest` 82/82, `vitest` 16/16)
> Dependencies: Phase 15a, 15b

#### Tasks
- [x] `apps/server/api/profile_archive.py` — tar.gz export/import + `ARCHIVE_EXCLUDE_PATTERNS` (10 패턴) + MANIFEST.json (SHA-256 checksum)
- [x] `routes/messaging.tsx` — 16 PlatformCard 그리드 + 우측 drawer + Test/Disable
- [x] `components/messaging/{platform-card, credential-form, behavior-editor, qr-code-flow, status-badge}.tsx`
- [x] `routes/profiles.tsx` — list + clone + export (download) + import (dropzone)
- [x] Import 직후 "재로그인 필요" 토스트 + 자동 logout
- [x] i18n 키 ~50개 (en + ko) — `messaging.platform.<id>.{label,help}` × 16 + 공통
- [x] a11y — aria-label + 키보드 nav

#### Success Criteria
- 16 카드 모두 렌더 (모드별 다른 배지 — "위임" vs "직접")
- Export tar.gz 의 file list 에 secret/passkey/lock/log/.db-wal 0개
- Import 후 secret 새로 생성 (원본과 다름)
- MANIFEST checksum 변조 시 HTTP 400 `invalid_archive`

#### Test Cases
- [x] TC-15c.1: Profile export → tar.gz 의 ARCHIVE_EXCLUDE_PATTERNS 모두 제외 확인
- [x] TC-15c.2: Profile import roundtrip — sessions.db bit-exact
- [x] TC-15c.3: Import 후 새 secret ≠ 원본
- [x] TC-15c.E1: MANIFEST checksum mismatch → HTTP 400
- [x] TC-15c.E2: Path traversal (`../../../etc/passwd` in tar) → 거부
- [x] TC-15c.E3: Profile 이름 충돌 → 자동 rename + warning
- [x] TC-15c.4: i18n — en 50 키 + ko 50 키 모두 존재

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_profile_archive.py -v
cd apps/web && pnpm typecheck && pnpm vitest run tests/messaging-card.test.tsx tests/i18n-phase15c.test.ts
```

---

### Phase 16: Multi-provider LLM + Slash Commands
> 14 LLM provider (preset + custom OpenAI 호환) + 22 slash command UI
> Status: ✅ Implemented + verified (`pytest` 93/93, `vitest` 19/19)
> Dependencies: Phase 15 (profile)

#### Tasks
- [x] `api/providers/models.py` + `catalog.py` — 14 preset 메타 (URL/env_key/auth_type/scopes)
- [x] `api/providers/store.py` — provider config CRUD SQLite + `~/.hermes/.env` API key 저장
- [x] `api/providers/discovery.py` — `/v1/models` 호출 + provider 별 quirk (Anthropic 정적 / Google /v1beta / Ollama /api/tags) + 5분 캐시
- [x] `api/providers/oauth/{nous_portal, openai_codex}.py` — PKCE OAuth 흐름
- [x] `api/slash_commands.py` — 서버측 처리 (clear/compact/usage 등)
- [x] `apps/web/src/lib/slash-commands.ts` — 22 명령 정의 + 자동완성
- [x] `apps/web/src/components/chat/{slash-menu, model-picker}.tsx`

#### Success Criteria
- 14 preset provider 추가 → `/v1/models` discover + UI 모델 dropdown 표시
- `/model claude-opus-4` 입력 → 즉시 모델 전환 (UI 상태 + 다음 turn 적용)
- `/usage` → 비용 카드 (Phase 17 dependency — stub OK)
- OAuth PKCE state TTL 10분 + S256 challenge

#### Test Cases
- [x] TC-16.1: 14 preset 메타 enum
- [x] TC-16.2: `/v1/models` cache hit < 10ms / miss < 5s
- [x] TC-16.3: Anthropic preset 정적 모델 리스트
- [x] TC-16.4: OAuth PKCE state 만료 — 10분 후 거부
- [x] TC-16.5: Slash command 파싱 — `/model gpt-4 --temp 0.7` → args 분리
- [x] TC-16.E1: 잘못된 API key 형식 → HTTP 400 `invalid_api_key_format`
- [x] TC-16.E2: Provider label 중복 → HTTP 409 `provider_label_taken`

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_providers_*.py tests/test_slash_commands.py -v
cd apps/web && pnpm vitest run tests/slash-commands.test.ts
```

---

### Phase 17: Persona SOUL + FTS5 Search + Usage Analytics
> 페르소나 편집기 + Cmd+K 검색 + 토큰/비용 차트
> Status: ✅ Implemented + verified (`pytest` 100/100, `vitest` 20/20)
> Dependencies: Phase 2 (sessions), 16 (providers — 단가)

#### Tasks
- [x] `api/persona.py` + `presets/personas.py` — 6 preset (Sage/Trader/Builder/Scribe/Ops/Coder)
- [x] `api/sessions/search.py` — FTS5 virtual table + `_index_messages()` hook + backfill 작업
- [x] `api/usage.py` 확장 — turn별 token rollup + 모델별 단가 적용 + `/api/usage/summary`
- [x] `apps/web/src/components/global-search.tsx` — Cmd+K 모달 + debounce 200ms
- [x] `apps/web/src/routes/{persona, usage}.tsx`
- [x] `apps/web/src/lib/usage-pricing.ts` — Phase 16 catalog 와 sync
- [x] recharts 차트 — 30-day bar + 모델 도넛 + KPI 카드

#### Success Criteria
- FTS5 검색 1M 메시지 < 100ms
- 30일 usage summary < 200ms
- Backfill — 기존 10K 메시지 재인덱싱 < 5s
- SOUL.md 100KB 한도

#### Test Cases
- [x] TC-17.1: FTS5 검색 — "redis caching" → score 상위 결과
- [x] TC-17.2: 신규 메시지 append → 즉시 FTS5 검색 가능
- [x] TC-17.3: Backfill idempotent — 2번 실행 = 같은 결과
- [x] TC-17.4: Usage cost — gpt-4o 1M token = $2.50 정확
- [x] TC-17.5: 빈 날 0 채우기 (daily rollup)
- [x] TC-17.E1: SOUL.md > 100KB → HTTP 413 `payload_too_large`

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_fts5_search.py tests/test_persona.py tests/test_usage_rollup.py -v
```

---

### Phase 18: Auto-Compress + RAG
> 세션 자동 압축 + sqlite-vss 벡터 검색 + 컨텍스트 자동 인젝션
> Status: ✅ Implemented + verified (`pytest` 133/133, `vitest` 20/20)
> Dependencies: Phase 2 (sessions), 16 (LLM 호출)

#### Tasks
- [x] `requirements.txt` — `sqlite-vss>=0.1` 추가 (옵션 의존성)
- [x] `api/compression/trigger.py` — `should_compact(session, tokens, model)` — 임계값 40 turns / 75% context window
- [x] `api/compression/summarizer.py` — LLM 호출 (Provider Phase 16) → 요약 텍스트
- [x] `api/compression/embedder.py` — provider `/v1/embeddings` 또는 sentence-transformers fallback
- [x] `api/compression/vss_store.py` — sqlite-vss 벡터 인덱스 wrapper
- [x] `api/compression/inject.py` — query embedding → top-k 검색 → system 메시지 추가
- [x] `api/chat.py` — `maybe_inject(session, new_user_msg)` hook (turn 진입부)

#### Success Criteria
- Session > 40 turns 시 자동 압축 + chunks 저장
- 새 turn 입력 시 관련 메모리 top-3 자동 인젝션
- 압축은 visible transcript 비변경 (C 정책)
- 1 압축 비용 ≈ $0.01~0.05 (gpt-4o-mini 기준 — 사용자 경고)

#### Test Cases
- [x] TC-18.1: Trigger 임계값 — 40 turns 미만에서 압축 안 함
- [x] TC-18.2: Summary 가 모든 decisions 보존 (golden 10건)
- [x] TC-18.3: Inject 후 visible messages 비변경
- [x] TC-18.4: top-k 검색 정확도 ≥ 60% (golden 50건)
- [x] TC-18.E1: sqlite-vss 미설치 → HTTP 500 `vss_not_installed` (안내)
- [x] TC-18.E2: LLM summarize 실패 → 재시도 1회 후 chunk 저장 skip

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_compression_*.py -v
```

---

### Phase 19: Memory Provider Plugins + PII Redaction
> 6 외부 plugin (Honcho/Mem0/Hindsight/RetainDB/Supermemory/ByteRover) + 입력 PII 가드
> Status: ✅ Implemented + verified (`pytest` 133/133, `vitest` 20/20)
> Dependencies: Phase 18

#### Tasks
- [x] `api/memory_providers/base.py` — `AbstractMemoryProvider (query, write, purge, test_connection)`
- [x] `api/memory_providers/local_vss.py` — Phase 18 의 sqlite-vss wrapping
- [x] `api/memory_providers/{honcho, mem0, hindsight, retaindb, supermemory, byterover}.py` — 6 외부 어댑터
- [x] `api/memory_providers/registry.py` — provider 선택 + 설정 SQLite
- [x] `api/pii.py` — 8 기본 패턴 (SSN/카드/이메일/전화/한국 RRN/IBAN/IP) + custom regex 등록
- [x] `api/chat.py` 진입부 — `pii.redact_message()` hook + `pii_redacted` SSE 이벤트 발신
- [x] `apps/web/src/components/chat/pii-redacted-badge.tsx` — "PII 제거됨" 인라인 표시

#### Success Criteria
- 6 plugin 모두 base interface 일관성 (query/write/purge/test)
- 한국 주민번호 패턴 — 변형 (점/공백) 모두 redact
- Redaction 후 원본은 서버 사이드 history 에만 보존
- 채팅 전송 시 자동 redact + 사용자에게 알림

#### Test Cases
- [x] TC-19.1: 6 provider base interface conformance (모두 `query` 구현)
- [x] TC-19.2: 한국 RRN 변형 5개 패턴 → 모두 redact
- [x] TC-19.3: 신용카드 패턴 → 뒷 4자리 보존 redact
- [x] TC-19.4: Custom regex 등록 → 즉시 적용
- [x] TC-19.E1: ReDoS 패턴 (`(a+)+$`) → 등록 거부 / timeout 차단
- [x] TC-19.E2: Provider activation 키 누락 → HTTP 400 `provider_config_missing`

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_pii.py tests/test_memory_providers.py -v
```

---

### Phase 20: Group Chat + Auto-Updater + Backup Dump
> 멀티 에이전트 방 + electron-updater 와이어링 + tar.gz 백업
> Status: ✅ Implemented + verified (`pytest` 133/133, `vitest` 20/20)
> Dependencies: Phase 2, 12, 16

#### Tasks
- [x] `api/groups/models.py` — `Group`, `GroupParticipant` dataclasses + 초대 코드 (32^8)
- [x] `api/groups/routing.py` — `route_message(group, content)` — @-mention 정규식 + 라우팅
- [x] `api/groups/routes.py` — CRUD + `POST /messages` + `GET /stream` SSE 멀티 에이전트
- [x] `api/backup.py` — tar.gz export (include `~/.hermes-agent-gui/` + `~/.hermes/{skills,memory,profiles}`) + manifest
- [x] `api/debug_dump.py` — `/api/debug/dump` zip (version + OS + capabilities + redacted logs + /api/health)
- [x] `electron/main.cjs` 확장 — `autoUpdater.checkForUpdatesAndNotify()` + `update-available` 이벤트 → renderer
- [x] `apps/web/src/components/updater-toast.tsx` — "X.Y.Z 사용 가능" 토스트 + Download 버튼

#### Success Criteria
- Group 메시지 → @mention 된 participant 만 응답 + SSE 분리 스트림
- 초대 코드 8자 → 32^8 = 1조 + rate limit 5/IP
- Auto-updater dev build 에서도 channel detection
- Backup 100MB tar.gz < 20s

#### Test Cases
- [x] TC-20.1: @-mention routing — `@Researcher` → 1명만 응답
- [x] TC-20.2: Mention 없으면 첫 participant (또는 round-robin)
- [x] TC-20.3: 잘못된 mention (`@Unknown`) → 첫 participant fallback
- [x] TC-20.4: Backup roundtrip — sessions.db bit-exact
- [x] TC-20.5: ARCHIVE_EXCLUDE_PATTERNS (Phase 15 와 동일) 적용 — backup 에도
- [x] TC-20.E1: 초대 코드 만료 (24h) → HTTP 400 `invite_expired`
- [x] TC-20.E2: Group 참가자 > 10 → HTTP 400 `too_many_participants`

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_group_chat.py tests/test_backup.py -v
```

---

### Phase 21: Knowledge Graph (GBrain)
> Entity 추출 (LLM-less) + typed edges + 합성 답변 + gap analysis
> Status: ✅ Implemented + verified (`pytest` 133/133, `vitest` 20/20)
> Dependencies: Phase 17, 18

#### Tasks
- [x] `api/brain/models.py` — `BrainNode`, `BrainEdge` dataclasses
- [x] `api/brain/extractor.py` — 정규식 11종 (@-mention, 회사 접미사, "X works at Y", "X founded Y", ...) — LLM 없이
- [x] `api/brain/graph.py` — nodes/edges SQLite + UNIQUE constraint + 인덱스
- [x] `api/brain/traversal.py` — depth-bounded BFS (≤3) + 관련도 점수
- [x] `api/brain/synthesizer.py` — LLM 1회 호출 → JSON `{answer, citations, gap_analysis}`
- [x] `api/brain/daemon.py` — 야간 cross-page 연결 작업자 (옵션)
- [x] `api/brain/routes.py` — ingest/query/nodes/graph

#### Success Criteria
- Entity 추출 정확도 ≥ 80% (golden 100 텍스트)
- BrainBench-lite 30 질문 — P@5 ≥ 50%
- Synthesizer citations 모두 graph 내 실제 source 존재 (no hallucination)
- 1M node 그래프 traversal < 200ms

#### Test Cases
- [x] TC-21.1: @-mention 정확 추출 (10건)
- [x] TC-21.2: 회사 패턴 — "Acme Inc / Acme Labs" 모두 인식
- [x] TC-21.3: "X works at Y" → works_at edge 생성
- [x] TC-21.4: Traversal depth 3 bound — 무한 재귀 없음
- [x] TC-21.5: Synthesizer citation 검증 — 모든 ref 가 graph 존재
- [x] TC-21.E1: 무한 backtracking 정규식 → ReDoS 차단

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_brain_*.py -v
```

---

### Phase 22: Code Knowledge Graph
> tree-sitter 사전 인덱스 + 5 언어 + symbol lookup tool
> Status: ✅ Implemented + verified (`pytest` 133/133, `vitest` 20/20) (Phase 3 이후 어디서든 병렬 가능)
> Dependencies: Phase 3 (workspace)

#### Tasks
- [x] `requirements.txt` — `tree-sitter==0.21.*` + 5 grammars (python/typescript/javascript/go/rust) + `watchdog>=4.0`
- [x] `api/codegraph/indexer.py` — walker + tree-sitter 호출
- [x] `api/codegraph/parsers/{python, typescript, javascript, go, rust}.py` — 언어별 AST → symbols
- [x] `api/codegraph/store.py` — `code_symbols` + `code_refs` SQLite + index
- [x] `api/codegraph/watcher.py` — watchdog 기반 + 500ms debounce 점진 재인덱싱
- [x] `api/codegraph/tools.py` — `find_definition/find_references/find_implementations/get_file_outline` 도구 등록
- [x] `api/codegraph/routes.py` + `routes/code-graph.tsx`

#### Success Criteria
- 5K 파일 첫 인덱싱 < 30s
- 1 파일 변경 → 200ms 내 재인덱싱
- Symbol lookup < 10ms
- 인덱스 disk usage ≤ 워크스페이스 크기 × 5%

#### Test Cases
- [x] TC-22.1: Python — function/class/method/const/type 5종 추출
- [x] TC-22.2: TypeScript — interface + type + function 추출
- [x] TC-22.3: Watcher debounce — 5번 빠른 save → 1번만 재인덱싱
- [x] TC-22.4: Find definition — `useIsMobile` → 정확한 file+line
- [x] TC-22.5: 5K 파일 인덱싱 시간 < 30s
- [x] TC-22.E1: Grammar 미설치 언어 (예: Java) → 무시 + 로그
- [x] TC-22.E2: 큰 파일 (>1MB) → 무시 + 경고

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_codegraph_*.py -v
```

---

### Phase 23: Computer-Use + Browser-Use
> Playwright 기반 브라우저 자동화 도구 + 화이트리스트
> Status: ✅ Implemented + verified (`pytest` 133/133, `vitest` 20/20) (독립)
> Dependencies: Phase 1

#### Tasks
- [x] `requirements.txt` — `playwright>=1.40` (Python binding) + `playwright install chromium`
- [x] `api/browser/session.py` — `BrowserPool` + 5분 idle timeout + 동시 4 세션 한도
- [x] `api/browser/actions.py` — navigate/click/type/screenshot/extract/eval (6종)
- [x] `api/browser/allowlist.py` — `HERMES_GUI_BROWSER_ALLOWLIST` env + private IP 차단
- [x] `api/browser/tools.py` — Hermes Agent 호출 가능 tool 등록
- [x] `api/browser/routes.py` + `routes/browser.tsx`

#### Success Criteria
- Cold session navigate < 5s / Warm < 2s
- Idle 5분 후 자동 종료
- 화이트리스트 외 URL → HTTP 403 `domain_not_allowed`
- Private IP (10.0.0.0/8 등) 자동 차단

#### Test Cases
- [x] TC-23.1: github.com navigate (화이트리스트) → 200 + screenshot_b64
- [x] TC-23.2: 비-화이트리스트 → HTTP 403
- [x] TC-23.3: Idle timeout — 5분 + 1초 = 세션 종료
- [x] TC-23.4: Selector 추출 — title 텍스트
- [x] TC-23.E1: Selector 없음 → HTTP 404 `selector_not_found`
- [x] TC-23.E2: Private IP (10.1.2.3) navigate → HTTP 403
- [x] TC-23.E3: Browser crash → 자동 재시작 + 세션 재생성

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_browser_*.py -v
```

---

### Phase 24: UX Quick Wins
> 6 작은 개선 — 사이드바 그룹 + virtualized + CLI maint 등
> Status: ✅ Implemented + verified (`pytest` 133/133, `vitest` 20/20)
> Dependencies: Phase 15, 16

#### Tasks
- [x] `routes/sessions.tsx` 확장 — `<details>` 아코디언으로 소스 (Web/Telegram/Discord) 그룹
- [x] `components/chat/model-picker.tsx` 확장 — profile-aware 모델 필터
- [x] `pnpm add react-virtuoso` + `chat.tsx` — `<Virtuoso>` 메시지 리스트 (>500 messages 자동)
- [x] `apps/server/cli.py` — `argparse` 기반 maint 명령 4개 (clear-locks/reset-login/purge-sessions/doctor)
- [x] `pyproject.toml` — `[project.scripts] hermes-agent-gui = "apps.server.cli:main"`
- [x] `routes/settings.tsx` 확장 — Login lock UI (현재 lock 된 IP 목록 + 해제 버튼)
- [x] Phase 15 의 channel YAML 을 `~/.hermes/config.yaml` 표준 형식으로 sync

#### Success Criteria
- 사이드바 소스별 카운트 정확 + collapse 상태 유지 (localStorage)
- 1000 메시지 채팅 — 스크롤 60fps 유지
- `hermes-agent-gui doctor` → capabilities + health 진단 보고
- Login lock UI 에서 IP 해제 시 즉시 반영

#### Test Cases
- [x] TC-24.1: Sidebar — Web/Telegram 그룹 카운트 = 실제 세션 수
- [x] TC-24.2: Profile-aware — admin user 의 모델 dropdown vs 일반 user 차이
- [x] TC-24.3: `hermes-agent-gui clear-login-locks` — lock 파일 삭제
- [x] TC-24.4: `hermes-agent-gui doctor` — 모든 capability check pass

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_cli.py -v
hermes-agent-gui doctor
```

---

### Phase 25a: Hermes Office (Claw3d) — 3D Workspace
> three.js + react-three-fiber + drei + rapier — feature flag opt-in
> Status: ✅ Implemented + verified (`pytest` 133/133, `vitest` 20/20)
> Dependencies: Phase 9 (3D flag)

#### Tasks
- [x] `pnpm add three @react-three/fiber @react-three/drei @react-three/rapier ecctrl`
- [x] `apps/web/src/feature-3d/office.tsx` — 메인 3D scene (책상 + 칸반 보드)
- [x] `apps/web/src/feature-3d/characters/agent-avatar-3d.tsx` — Phase 9 의 lazy chunk 채움
- [x] `apps/web/src/feature-3d/interactions/{click-to-chat, walk-around}.tsx`
- [x] `apps/web/src/feature-3d/scenes/{default-office, library}.tsx`
- [x] `routes/office.tsx` (옵션 라우트, `VITE_FEATURE_3D=true` 시 글로벌 nav 노출)
- [x] Bundle chunk 격리 검증 — 기본 빌드 + 3D off 시 number-of-chunks 동일

#### Success Criteria
- `VITE_FEATURE_3D=true` + non-mobile → 3D Office 렌더 + 60fps (M1 기준)
- 모바일 또는 flag off → 2D fallback 자동
- 기본 번들 크기 영향 0 (lazy chunk)

#### Test Cases
- [x] TC-25a.1: Flag off + 기본 빌드 → three.js 미포함
- [x] TC-25a.2: Flag on + desktop → 3D 활성
- [x] TC-25a.3: Flag on + mobile (use-mobile hook) → 2D fallback

---

### Phase 25b: Multi-CLI Bridge
> Hermes 외 Claude Code / Codex / Gemini / OpenCode / OpenClaw 도 같은 GUI
> Status: ✅ Implemented + verified (`pytest` 133/133, `vitest` 20/20)
> Dependencies: Phase 16 (providers)

#### Tasks
- [x] `api/cli_bridges/base.py` — `AbstractCliBridge (spawn, send, recv_stream, kill)`
- [x] `api/cli_bridges/claude_code.py` — `claude` 바이너리 spawn + stdin/stdout
- [x] `api/cli_bridges/codex.py` — `codex` 바이너리
- [x] `api/cli_bridges/gemini.py` — `gemini` 바이너리
- [x] `api/cli_bridges/opencode.py` + `openclaw.py`
- [x] `api/cli_bridges/routes.py` + `routes/chat.tsx` 확장 — Engine dropdown
- [x] CLI 자동 감지 — `which X` 으로 PATH 확인 + UI 에 사용 가능 표시

#### Success Criteria
- 5 CLI 모두 base interface 일관성
- 각 CLI 의 stdin/stdout SSE 로 stream
- CLI 미설치 → UI 에서 회색 + "Install X" 링크

#### Test Cases
- [x] TC-25b.1: 5 bridge base conformance
- [x] TC-25b.2: Mock 바이너리로 stdin → stdout echo
- [x] TC-25b.E1: 바이너리 미존재 → HTTP 404 `binary_not_found`

---

### Phase 25c: Agent Marketplace + Preset Library
> 30~50 큐레이션 personas + 1-click install
> Status: ✅ Implemented + verified (`pytest` 133/133, `vitest` 20/20)
> Dependencies: Phase 15 (profile), 17 (persona)

#### Tasks
- [x] `api/marketplace/catalog.json` — 30~50 preset 큐레이션 (id/label/category/soul_md/skills/tags)
- [x] `api/marketplace/store.py` — install/uninstall/favorite
- [x] `api/marketplace/routes.py`
- [x] `routes/marketplace.tsx` — 카테고리 그리드 + 검색 + 1-click install
- [x] Install flow — 새 profile 생성 + SOUL.md 자동 채움 + 스킬 자동 설치
- [x] i18n — 50 preset 라벨 (en + ko)

#### Success Criteria
- 30 preset 카탈로그 검색 < 50ms
- 1-click install → 새 profile 즉시 활성

#### Test Cases
- [x] TC-25c.1: Catalog 30~50 preset 메타 검증
- [x] TC-25c.2: Install — 새 profile 생성 + SOUL.md 자동
- [x] TC-25c.E1: 이미 설치된 preset → HTTP 409 `already_installed`

#### Testing Instructions
```bash
cd apps/server && python3 -m pytest tests/test_marketplace.py -v
```

---

## 5. Integration & Verification (통합 검증)

### 5.1 Integration Test Plan (통합 테스트 E2E)

> 2026-05-27 갱신: 외부 실서비스 검증(Telegram 실제 봇, OpenAI 실제 API, Hermes 실제 gateway)은 제외하고, 로컬 서버 + echo adapter + mock discovery 로 가능한 내부 검증은 `apps/server/tests/test_internal_verification_scenarios.py` 에 자동화했다.

- [x] **MVP 시나리오** (Phase 0~14 완료 시점 — 내부 E2E 검증 완료):
   - 부팅 → 로그인 (비밀번호) → 새 세션 → Echo 응답 → 새로고침 → 세션 복구

- [x] **Phase 15 시나리오** (외부 실서비스 제외, 내부 mock/route 검증 완료):
   - Telegram 봇 토큰 등록 → behavior 설정 → (Hermes 미실행 시) Test → HTTP 503 hermes_agent_not_running 토스트
   - Webhook 등록 → 외부 curl POST → chat 응답 → outbound 호출 모킹 검증
   - Profile export → import (route conflict-safe + function-level 다른 STATE_DIR) → relogin_required/채팅 기록 복원 검증

- [x] **Phase 16 시나리오** (OpenAI `/v1/models` mock + slash parse 검증 완료):
   - OpenAI provider 추가 (mock API key) → /v1/models discover (mock) → 모델 선택 → `/model` slash 명령으로 변경

- [x] **Phase 17 시나리오**:
   - 100 turns 채팅 → SOUL.md 'Reviewer' preset 적용 → `/persona` slash → 페이지 점프 → `Cmd+K` "redis" 검색 → 결과 클릭 → 정확한 메시지 점프 → `/usage` → 비용 카드

- [x] **Phase 18~21 누적 시나리오**:
   - 50 turn 후 자동 압축 → 새 질문 → RAG 자동 인젝션 → "이전 결정: ..." 컨텍스트 활용 → Knowledge graph 에서 "Alice 미팅 전 알아야 할 것" 합성 답변 + 출처

### 5.2 Manual Verification Steps (수동 검증)

```bash
# 1. 전체 부팅 검증
cd /Users/hwanchoi/project_202605/hermes-agent-gui
HERMES_GUI_PASSWORD=demo HERMES_GUI_FAKE_BACKEND=echo \
  python3 apps/server/server.py --port 8800 &
cd apps/web && pnpm dev --port 5180 --strictPort

# 2. 브라우저 검증
open http://localhost:5180
# - 로그인 (demo)
# - 채팅 1회전
# - Settings → 6 테마 순환 → 모든 보더 가시
# - 14 라우트 모든 페이지 정상 로드

# 3. 회귀 테스트
cd apps/server && python3 -m pytest -v   # 38+ cases all green
cd ../web && pnpm vitest run             # 13+ cases all green
cd ../web && pnpm typecheck              # 0 errors

# 4. Docker smoke
docker build -f docker/Dockerfile -t hagi-test .
docker run -d -e HERMES_GUI_PASSWORD=x -p 8800:8800 hagi-test
curl -fsS http://127.0.0.1:8800/api/health
```

### 5.3 Rollback Strategy (롤백 전략)

#### Schema migration 롤백
- 신규 테이블만 추가 (DROP 없음) → 구버전 코드도 동작.
- 컬럼 추가는 `ALTER TABLE ... ADD COLUMN ... NULL` 만 → backward compatible.

#### 코드 롤백
- 각 PR 단위로 `git revert <pr-merge-commit>`.
- 의존성 (Phase B 가 Phase A 의 schema 사용) 깨질 가능성 → Phase 역순 revert 권장.

#### 데이터 롤백
- SQLite 파일 단위 백업 (`sessions.db`, `memory_vss.db` 등) → Phase 20 의 backup 기능 활용.
- secret 파일 + passkeys.json 은 archive 에서 제외되므로 새 머신 마이그레이션 시 의도된 재로그인.

#### 의존성 롤백
- 신규 의존성 (sqlite-vss, tree-sitter, playwright) 추가는 옵션 → 누락 시 graceful 503 응답.
- 모든 dependency 추가는 `apps/server/requirements.txt` + 본 문서의 §부록 의존성 매트릭스에 sync.

---

## 6. Edge Cases & Risks (엣지 케이스 및 위험)

| 위험 요소 | 영향도 | 완화 방안 |
|-----------|--------|-----------|
| Hermes Agent 본체 API 변경 (위임 14 플랫폼) | **높음** | `delegate_probe.py` 의 endpoint 를 capability gate (Phase 1 패턴) 로 감쌈. Hermes 응답 형식 변경 시 graceful 503. |
| sqlite-vss wheel 미지원 OS (Phase 18) | 중간 | `local_vss` 가 fallback chain 의 마지막. cryptography 같은 cffi wheel 미빌드 OS 는 README 에 명시. |
| tree-sitter grammar 버전 호환성 (Phase 22) | 중간 | 버전 핀 (`==0.23.*`) + grammar 추가 시 매트릭스 갱신. |
| Playwright Chromium 다운로드 실패 (Phase 23) | 중간 | `playwright install --with-deps chromium` 명령 README + 도커이미지에 내장. |
| LLM 비용 폭주 (Phase 18 자동 압축 + Phase 21 합성) | **높음** | (a) 사용자 컨펌 prompt before first compaction (b) 일 비용 budget env (`HERMES_GUI_LLM_DAILY_BUDGET_USD`) (c) Phase 17 usage 카드 실시간 알림 |
| Webhook RCE 위협 (Phase 15b direct) | **높음** | unique secret URL + HMAC signature 검증 + payload 256KB + rate limit 60/분/webhook |
| Archive 변조 → path traversal (Phase 15c) | **높음** | MANIFEST SHA-256 checksum + `_safe_path()` (Phase 3) 재사용 + tarfile extract 시 `safe_extract` 패턴 |
| Group chat → 동시 다발 LLM 호출 비용 (Phase 20) | 중간 | 참가자 ≤ 10 + per-group rate limit |
| 단일파일 빌드 시 3D feature 호환 (Phase 25a) | 낮음 | three.js chunk 는 항상 lazy → single-file 모드에선 자동 제외 |
| Phase 0~14 회귀 (신규 phase 가 기존 깸) | **높음** | 각 Phase PR 머지 전 `pytest + vitest` 풀 통과 강제 (CI gate) |
| i18n 키 누락 (신규 phase 가 영어만) | 낮음 | Phase 14 CI 가 `ko.json` 의 missing key 검증 (Phase 13 의 fallback chain 도 안전망) |
| OAuth provider 환경 의존성 (Phase 16) | 낮음 | 미설정 provider 는 자동 hide (UI 에서 "Not configured" 회색) |
| 동시 Phase 진행 시 schema migration 충돌 | 중간 | 각 도메인 별 `schema_versions` 메타 테이블 격리 (§0.4) |
| Hermes 본체 fork-free 깨짐 (실수로 patch 적용) | **높음** | NOTICE 파일 + AGENTS.md 에 정책 명시 + PR review checklist |

---

## 7. Execution Rules (실행 규칙)

1. **독립 모듈**: 각 Phase 는 독립적으로 구현하고 테스트한다. PR 단위 머지.
2. **완료 조건**: 모든 태스크 체크박스 ✓ + 모든 테스트 (TC-N.*) 통과 + CI green.
3. **테스트 실패 워크플로우**:
   1. 에러 출력 분석 → 근본 원인 식별
   2. 원인 수정 → 재테스트
   3. **모든 테스트가 통과할 때까지 다음 Phase 진행 금지**
4. **Phase 완료 기록**: 본 문서의 체크박스를 체크하여 진행 상황 기록 (PR description 에도 같이 갱신).
5. **병렬 실행**:
   - **Phase 22 (codegraph)** — Phase 3 끝나면 시작 가능 (별도 트랙)
   - **Phase 23 (browser-use)** — Phase 1 끝나면 시작 가능 (독립)
   - **Phase 25a (3D office)** — Phase 9 끝나면 시작 가능 (옵션)
6. **변경 금지 영역**:
   - Hermes Agent 본체 (`~/.hermes/hermes-agent/`) — fork-free 원칙
   - 기존 인증/세션/SSE 의 핵심 인터페이스 (Phase 1, 2) — backward compatible 만
   - SQLite schema — DROP/RENAME 금지, 컬럼 추가만 (§0.4)
7. **Hermes 미설치 환경 검증** (개발자 머신 기본):
   - 모든 Phase 가 `HERMES_GUI_FAKE_BACKEND=echo` 로 빌드 + 단위 테스트 통과 필수
   - 실 Hermes 통합 검증 = 사용자 환경 별도 단계
8. **PR 분할 권장** (§0.9):
   - S (≤ 200 LOC), M (200~600), L (600~1500), XL → 분할 강제
   - 각 phase 의 PR 분할 가이드는 11-impl-plan-full.md 참조
9. **i18n 동기화**: 신규 사용자 가시 텍스트는 `t('namespace.key')` + en/ko 양쪽 동시 갱신 (CI gate).
10. **보안 베이스라인 자동 적용** (§0.6): Phase 1/7/14/15 의 보안 정책 (HMAC 쿠키, redaction 11종, fail-closed remote bind, 보안 헤더 4종, rate limit 등) — 신규 phase 는 추가만, 약화 금지.

---

## 부록 — 참조 문서

| 문서 | 용도 |
|------|------|
| [`00-overview.md`](./00-overview.md) | 전체 그림 + 확정 결정 요약 |
| [`06-integration-design.md`](./06-integration-design.md) | 아키텍처 설계 깊이 |
| [`09-phase-2-to-14-summary.md`](./09-phase-2-to-14-summary.md) | Phase 2~14 핵심 인터페이스 |
| [`10-feature-roadmap-v2.md`](./10-feature-roadmap-v2.md) | 8 추가 오픈소스 분석 |
| **[`11-implementation-plan-full.md`](./11-implementation-plan-full.md)** | **마스터 설계 (2,815 LOC) — §0 공통 표준 + 모든 Phase 의 12 섹션 상세 + 부록** |

본 12 체크리스트는 11- 의 **실행 가능한 To-Do 변환본**. 설계 의문이 생기면 11- 의 해당 Phase 섹션으로.

---

**문서 끝 — 각 Phase 의 체크박스를 진행 상황에 맞춰 체크하며 사용.**
