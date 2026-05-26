# 13 · Docs 전문가 분석 및 구현 항목 정리

작성 일시: `2026-05-26 21:02:00 KST`

이 문서는 `docs/review/*.md` 전체를 기준으로 현재 설계 의도, 구현 상태, 문서 간 불일치, 우선순위별 구현 항목을 재정리한 전문가 분석 문서다.

## 분석 대상

| 문서 | 역할 | 전문가 판단 |
|---|---|---|
| `00-overview.md` | 3개 upstream GUI 분석의 결론 및 채택 방향 | 방향성의 source of truth. 다만 현재 README는 Phase 0~14 완료로 확장되어 1차 PR 범위 설명은 과거 맥락이다. |
| `01-hermes-workspace.md` | A: React/Electron/Swarm 중심 분석 | 프론트·고급 UX 자산의 근거. 실제 이식은 아직 vertical-slice 수준이라 Monaco/xterm/shiki 등은 후속 구현 대상이다. |
| `02-hermes-webui.md` | B: Python stdlib backend/PWA/운영 분석 | 서버/인증/운영 표준의 근거. 현재 코드도 B 패턴을 가장 많이 따른다. |
| `03-hermes-ui.md` | C: 단일파일/복구/Glass/운영 패치 분석 | session repair, alias, tool evidence, glass theme의 핵심 근거. |
| `04-feature-matrix.md` | A/B/C 기능 비교 | 채택 근거가 잘 정리되어 있으나, 현재 구현 완료 여부와는 별도다. |
| `05-conflict-resolution.md` | 중복 기능 채택 결정표 | 아키텍처 결정 근거. “선택한 방향”과 “실제 구현 깊이”를 구분해야 한다. |
| `06-integration-design.md` | 통합 아키텍처/운영 모드/API/보안 | 설계 기준 문서. 현재 구현의 여러 누락을 이 문서 기준으로 검증할 수 있다. |
| `07-phase-0-checklist.md` | Phase 0 bootstrap 체크리스트 | 완료 기록. 현재와 비교 시 과거 스냅샷이다. |
| `08-phase-1.md` | 인증 + SSE 채팅 설계 | 핵심 API 계약의 기준. OAuth/Passkey 상태 설명은 최신 코드와 동기화 필요. |
| `09-phase-2-to-14-summary.md` | Phase 2~14 구현 요약 | 현재 README와 함께 “완료 주장”의 근거. 일부 항목은 실제 code review에서 보강 필요가 확인됨. |
| `10-feature-roadmap-v2.md` | 경쟁 분석 기반 Phase 15~25 제안 | 제품 확장 backlog. 기능은 매력적이지만 먼저 안정화 gate가 필요하다. |
| `11-implementation-plan-full.md` | Phase 0~25 마스터 설계 | 가장 상세한 설계 원천. 구현 시 phase별 세부 schema/API/test를 여기서 확인해야 한다. |
| `12-impl-plan-checklist.md` | 실행 가능한 체크리스트 | 실제 실행 문서로 가장 적합. 다만 체크박스 상태를 현재 코드와 동기화해야 한다. |

## 전체 결론

문서 세트는 “3개 GUI의 장점을 합친 personal Hermes Agent GUI”라는 제품 방향을 명확히 제시한다. 핵심 결정은 다음과 같다.

1. **Frontend는 A 계열**: React 19, TanStack Router/Query, Tailwind v4, Electron, 고급 UX 자산을 기준으로 한다.
2. **Backend는 B 계열**: Python stdlib HTTP 서버, 낮은 의존성, 운영 스크립트, PWA/모바일 안정성, 다층 인증을 기준으로 한다.
3. **Recovery와 단일파일 철학은 C 계열**: transcript repair, compression alias, tool evidence, glass theme, single-file fallback을 흡수한다.
4. **Phase 0~14는 vertical-slice로 완료된 상태**로 문서화되어 있으나, production-readiness 기준에서는 여러 안정화 항목이 먼저 필요하다.
5. **Phase 15~25는 매력적인 제품 확장 backlog**지만, 지금 바로 들어가면 RCE/캐시/배포/문서 불일치 리스크가 증폭된다.

## 문서 기반 핵심 아키텍처

### 채택 모델

| 영역 | 채택 | 구현 방향 |
|---|---|---|
| UI framework | A | React SPA + TanStack Router/Query |
| Backend | B | Python stdlib server + modular `api/*` |
| Auth | B + A guard | Password/Bearer/HMAC cookie, OAuth/Passkey optional, remote bind fail-closed |
| Session repair | B skeleton + C algorithm | SQLite session store, health check, repair, alias persistence |
| Workspace | C safety + A UI 목표 | root whitelist, path traversal guard, future Monaco |
| Terminal | A target, 현재 minimal | 현재 one-shot exec/PT​​Y, future xterm.js/WebSocket 또는 SSE PTY hardening |
| PWA | B pattern via Vite | service worker/manifest, but API cache policy needs hardening |
| Docker/daemon | B | Dockerfile, compose 1/2/3, ctl.sh, install.sh |
| Singlefile | C philosophy via Vite | `vite-plugin-singlefile` + Python serving path sync 필요 |
| Swarm/Conductor | A ported to Python | tmux/subprocess worker foundation, heuristic decomposition |

### 핵심 불변 조건

- Hermes Agent 본체는 fork하지 않는다.
- `HERMES_GUI_FAKE_BACKEND=echo`에서도 모든 phase가 빌드/테스트 가능해야 한다.
- 외부 노출 시 auth 없이 bind하지 않는다.
- 신규 phase는 기존 auth/session/SSE 계약을 깨지 않는다.
- SQLite migration은 DROP/RENAME 없이 additive로만 진행한다.
- 사용자 가시 텍스트는 en/ko i18n을 동시에 추가한다.
- 보안·redaction·rate limit은 phase가 진행될수록 강화만 한다.

## 문서와 현재 구현 사이의 주요 불일치

아래 항목은 문서 기반 구현 계획을 진행하기 전에 먼저 정리해야 한다.

| 우선순위 | 불일치/리스크 | 근거 | 조치 |
|---|---|---|---|
| P0 | Docker/Electron은 웹 UI가 뜬다고 가정하지만 `server.py`는 `/`와 `/index.html`을 서빙하지 않는다. | Dockerfile은 `apps/web/dist`를 복사하고 Electron은 `http://HOST:PORT`를 열도록 설계되어 있음. | `server.py`에 dist static serving + SPA fallback 추가 또는 Caddy/static server 분리. |
| P0 | `pnpm lint`가 문서상 품질 gate처럼 보이지만 실제로 `eslint` dependency/config가 없다. | `apps/web/package.json` lint script 존재, dependency 없음. | ESLint config/deps 추가, CI에 lint 단계 추가. |
| P1 | PWA 문서의 API NetworkFirst 전략은 민감 API 캐싱 위험이 있다. | `/api/*` GET 캐싱은 sessions/logs/memory/workspace 데이터 잔존 가능. | `/api/*` 캐싱 제거 또는 `/api/health` 등 safe endpoint만 NetworkOnly/NetworkFirst. |
| P1 | Passkey/OAuth 상태 문서가 혼재되어 있다. | `08/09` 일부는 stub로 설명, 현재 코드는 passkey 구현을 포함. | 실제 구현 가능 수준/테스트 결과에 맞춰 문서 동기화. |
| P1 | 명령 실행 기능이 여러 곳에 분산되어 있으나 보안 모델이 문서만큼 명확하지 않다. | terminal/pty/cron/swarm 모두 authenticated RCE 표면. | `HERMES_GUI_ENABLE_EXEC=1` 같은 explicit opt-in, local-only 기본값, allowlist/confirm/audit 추가. |
| P2 | Single-file 산출물 경로가 문서와 스크립트에서 다르다. | Vite는 `dist/index.html`, `serve_singlefile.py`는 `apps/server/hermes-agent-gui.html` 기본값. | script가 dist 산출물을 자동 찾거나 docs/README 명령 정정. |
| P2 | Phase 2~14 완료 요약의 테스트 수가 최신 상태와 어긋난다. | `09`는 7 pytest, 현재는 38 pytest + 13 vitest. | `09`, README, `12` 체크리스트 동기화. |
| P2 | A의 고급 UX 자산(Monaco/xterm/shiki 등)이 “채택”과 “구현 완료” 사이에서 혼동될 수 있다. | 분석/결정표는 채택 방향, 실제 앱은 minimal route 중심. | 문서에 “adopted target vs implemented now” 상태 컬럼 추가. |

## 구현 항목 우선순위

### Gate 0 — Phase 15 진입 전 안정화 필수

이 Gate를 통과하지 않으면 Phase 15~25 확장은 기능 수는 늘지만 운영 리스크가 같이 커진다.

#### G0-1. 배포 진입점 복구
- [ ] `apps/server/server.py`에 `apps/web/dist` 정적 파일 서빙 추가
- [ ] SPA route fallback: `/chat`, `/settings` 등 non-API GET은 `index.html` 반환
- [ ] Docker smoke에서 `/` 200 + `text/html` 검증
- [ ] Electron health 이후 `loadURL('/')` 실제 렌더 검증
- [ ] `serve_singlefile.py`와 일반 server의 역할 구분 문서화

#### G0-2. Quality gate 복구
- [ ] ESLint dependency/config 추가
- [ ] `pnpm lint`가 exit 0 또는 실제 lint failure를 반환하도록 수정
- [ ] CI `web-build` job에 `pnpm lint` 추가
- [ ] generated file(`routeTree.gen.ts`) lint 제외 정책 명시
- [ ] `.gitignore`와 현재 생성물 상태 정리: `dist`, `__pycache__`, `.pytest_cache` 제외/삭제

#### G0-3. PWA 민감 데이터 캐시 차단
- [ ] Workbox runtimeCaching에서 `/api/*` 제거
- [ ] 필요 시 `/api/health`만 별도 NetworkOnly/NetworkFirst 허용
- [ ] Cache Storage에 session/memory/log/workspace 응답이 남지 않는 테스트 추가
- [ ] service worker update 후 기존 `api` cache 삭제 로직 추가

#### G0-4. 명령 실행 표면 hardening
- [ ] terminal/pty/cron/swarm을 explicit env flag 뒤로 이동
- [ ] remote bind 상태에서는 exec 계열 기본 비활성화
- [ ] cron `shell=True` 제거 또는 `allow_shell` opt-in + confirm UI
- [ ] PTY cwd를 workspace `_safe_path()`로 강제
- [ ] swarm worker command allowlist/profile policy 추가
- [ ] 실행 감사 로그는 redaction 후 저장

#### G0-5. Passkey/WebAuthn 신뢰성 검증
- [ ] CBOR/COSE parsing을 검증된 라이브러리 또는 정확한 spec 구현으로 교체
- [ ] ES256/RS256 golden vector 테스트 추가
- [ ] authenticator counter/replay 방어 추가 여부 결정
- [ ] passkey가 “지원”인지 “실험적”인지 README/SECURITY에 명시

#### G0-6. 문서 동기화
- [ ] `09-phase-2-to-14-summary.md` 테스트 수/실제 endpoint 현황 갱신
- [ ] `12-impl-plan-checklist.md` Phase 0~14 체크박스를 실제 상태로 갱신
- [ ] `README.md` Quick start에 backend-only와 web dev 모드 차이 명시
- [ ] `SECURITY.md`에 exec/cron/swarm/PTY threat model 추가

### Phase 15 — Messaging + Profile Archive

문서상 다음 우선순위. 단, Gate 0 후 진행한다.

#### 15a. Messaging Foundation + 14 delegated platforms
- [ ] `api/messaging/models.py`: `PlatformMeta`, `CredentialField`, `PlatformStatus`
- [ ] `api/messaging/registry.py`: 16 platform registry, 14 delegated + 2 direct
- [ ] `api/messaging/credentials.py`: atomic credential write, 0600 permission, merge semantics
- [ ] `api/messaging/behavior.py`: `~/.hermes/config.yaml` read/write
- [ ] `api/messaging/status.py`: SQLite status table + event recording
- [ ] `api/messaging/delegate_probe.py`: Hermes Agent delegated test endpoint probe
- [ ] 14 delegated platform wrappers: telegram/discord/slack/whatsapp/signal/matrix/mattermost/email/sms/imessage/dingtalk/feishu/wecom/wechat
- [ ] Tests: registry count, credential validation, 0600, merge, Hermes unavailable 503

#### 15b. Direct Webhook + Home Assistant
- [ ] Webhook secret URL issuance
- [ ] HMAC signature verification
- [ ] inbound payload size/rate limit
- [ ] inbound → chat adapter → outbound response flow
- [ ] Home Assistant notify REST integration
- [ ] Tests: valid/invalid signature, 256KB limit, 60/min rate limit, HA mock

#### 15c. Messaging frontend + Profile Archive
- [ ] 16 platform card grid + mode badge
- [ ] credential form + behavior editor + status badge
- [ ] profile export/import/clone routes
- [ ] tar.gz `MANIFEST.json` + SHA-256 checksum
- [ ] archive exclude patterns: secret/passkey/log/db-wal/device-specific files
- [ ] safe tar extraction path traversal guard
- [ ] import 후 재로그인 flow
- [ ] i18n en/ko 50+ keys

### Phase 16 — Multi-provider LLM + Slash Commands

Phase 15의 profile/credential 기반 위에 얹는 것이 자연스럽다.

- [ ] 14 provider catalog: OpenAI, Anthropic, Google, xAI, OpenRouter, Nous Portal, Qwen, MiniMax, HuggingFace, Groq, LM Studio, Ollama, vLLM, llama.cpp
- [ ] provider config CRUD + API key safe storage
- [ ] `/v1/models` discovery with provider-specific quirks
- [ ] OAuth PKCE for Nous Portal/OpenAI Codex if retained
- [ ] model picker UI
- [ ] 22 slash commands parser/autocomplete
- [ ] `/model`, `/usage`, `/persona`, `/memory`, `/tools`, `/compact` 등 chat integration
- [ ] Tests: preset enum, cache hit/miss, slash parsing, duplicate provider label, invalid key format

### Phase 17 — Persona + FTS5 + Usage

사용자가 체감하는 생산성 개선 폭이 큰 phase다.

- [ ] `SOUL.md` CRUD + 6 persona presets
- [ ] SQLite FTS5 virtual table for messages
- [ ] append hook 자동 indexing
- [ ] backfill job idempotent 구현
- [ ] Cmd/Ctrl+K global search modal
- [ ] usage rollup: token, cost, model distribution, 30-day trend
- [ ] dashboard or `/usage` route with charts
- [ ] Tests: FTS ranking, append indexing, backfill idempotency, price calculation, SOUL.md size limit

### Phase 18~21 — Memory/Intelligence 고도화

이 구간은 기능 매력은 크지만 비용·의존성·정확성 리스크가 높다. 작게 쪼개야 한다.

| Phase | 구현 핵심 | 선행 조건 | 리스크 |
|---|---|---|---|
| 18 Auto-Compress + RAG | summarizer/embedder/vss/inject hook | Phase 16 provider | LLM 비용, sqlite-vss wheel, 요약 품질 |
| 19 Memory Provider + PII | memory provider interface + redaction | Phase 18 | 외부 API 다양성, ReDoS, 원본 보존 정책 |
| 20 Group Chat + Backup | group routing, backup/debug dump, auto-updater | Phase 12/16 | 동시 LLM 비용, archive safety |
| 21 Knowledge Graph | entity extraction, graph traversal, synthesis | Phase 17/18 | hallucination-free citations, graph scale |

권장: Phase 18 전 반드시 Phase 17 usage budget를 먼저 넣고, 첫 자동 압축 전 사용자 confirmation + daily budget env를 추가한다.

### 독립 병렬 트랙

문서상 병렬 가능한 phase다. 단, 보안 review를 별도 gate로 둔다.

#### Phase 22 — Code Knowledge Graph
- [ ] tree-sitter + 5 language grammar 도입 여부 결정
- [ ] workspace indexer + symbol/ref store
- [ ] watchdog debounce reindex
- [ ] tool registration: find_definition/references/outline
- [ ] tests: 5K files <30s, symbol lookup <10ms, big file skip

#### Phase 23 — Browser/Computer Use
- [ ] Playwright dependency + browser install strategy
- [ ] BrowserPool with session limits and idle timeout
- [ ] URL allowlist + private IP/SSRF block
- [ ] navigate/click/type/screenshot/extract/eval actions
- [ ] tests: allowlist, private IP block, crash recovery

### Phase 24~25 — UX/Optional Experience

- [ ] Phase 24: source-group sidebar, virtualized chat, profile-aware model picker, CLI maintenance commands, login lock UI
- [ ] Phase 25a: feature-flagged 3D Office lazy chunk
- [ ] Phase 25b: Claude Code/Codex/Gemini/OpenCode/OpenClaw CLI bridges
- [ ] Phase 25c: agent marketplace + persona preset install

권장: Phase 25a/25c는 core 기능 안정화 이후. Phase 25b는 exec 표면을 크게 넓히므로 Gate 0의 command hardening 없이는 금지한다.

## 권장 실행 순서

| 순서 | 작업 | 이유 |
|---:|---|---|
| 1 | Gate 0 안정화 | 현재 배포/보안/품질 gate가 가장 큰 리스크 |
| 2 | Phase 15a | messaging foundation은 Hermes Agent GUI의 killer feature 기반 |
| 3 | Phase 15b | direct webhook/HA는 Hermes 미실행에서도 제품 가치 제공 |
| 4 | Phase 15c | UI + archive로 실제 사용자 workflow 완성 |
| 5 | Phase 16 | provider/slash는 이후 usage/persona/RAG의 기반 |
| 6 | Phase 17 | 검색·페르소나·usage는 즉시 체감 가치가 큼 |
| 7 | Phase 18 | usage/budget가 생긴 뒤 자동 압축/RAG 도입 |
| 8 | Phase 19~21 | memory/graph intelligence 확장 |
| 병렬 | Phase 22, 23 | core와 분리 가능하지만 security gate 필수 |
| 후순위 | Phase 24~25 | UX/optional 확장 |

## 이번 문서 분석에서 나온 즉시 생성할 개발 계획 후보

### 후보 A — Production Readiness Gate
- 목적: Phase 15 진입 전 배포/품질/보안 구멍을 닫는다.
- 범위: static serving, lint, PWA API cache, exec hardening, passkey 검증, docs sync.
- 예상 PR 수: 3~5개.
- 추천도: **최우선**.

### 후보 B — Phase 15 Messaging Foundation
- 목적: 16 messaging platform registry와 credential/behavior 저장 기반을 만든다.
- 범위: 15a backend only.
- 선행: 후보 A 중 P0/P1 완료.

### 후보 C — Profile Archive Safety
- 목적: import/export를 안전하게 구현한다.
- 범위: tar.gz manifest, exclude patterns, safe_extract, roundtrip tests.
- 선행: profile model 확정.

### 후보 D — Search/Usage Quick Value
- 목적: FTS5 검색과 usage dashboard로 즉시 체감 기능 제공.
- 범위: Phase 17 일부를 Phase 15와 병렬로 분리.
- 조건: schema migration 충돌 방지.

## 전문가 권고

1. **문서상 다음 phase는 15이지만, 실제 개발 순서는 Gate 0 안정화가 먼저다.** 현재는 배포 진입점과 lint가 깨져 있고, PWA API cache/exec 표면이 보안 리스크다.
2. **“채택 결정”과 “구현 완료”를 문서에서 분리해야 한다.** A의 Monaco/xterm/shiki/command palette 같은 항목은 target architecture이지 현재 완료물이 아니다.
3. **Phase 15는 backend foundation과 frontend UX를 분리해야 한다.** 15a backend registry/credential이 먼저이고, 15c UI는 그 다음이다.
4. **Phase 18 이후는 비용 제어 없이는 진행하지 않는다.** 자동 압축, RAG, graph synthesis는 usage budget/사용자 확인/실패 복구가 선행되어야 한다.
5. **exec 계열 기능은 모든 future phase의 공통 보안 gate다.** terminal, PTY, cron, swarm, browser-use, CLI bridge가 같은 위험군이므로 하나의 policy layer가 필요하다.

## 다음 액션

- [ ] `dev-plan/implement_<timestamp>.md`로 **Production Readiness Gate** 계획 생성
- [ ] Gate 0를 3~5개 PR로 분할
- [ ] `12-impl-plan-checklist.md` Phase 0~14 상태를 실제 테스트 결과 기준으로 갱신
- [ ] Gate 0 통과 후 Phase 15a 착수
