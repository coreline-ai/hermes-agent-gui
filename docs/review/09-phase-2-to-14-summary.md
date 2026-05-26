# 09 · Phase 2 ~ 14 구현 요약

> 본 문서는 Phase 0·1 완료 후 1회차 push 로 Phase 2 ~ 14 까지를 **vertical-slice + 핵심 와이어링** 으로 구현한 결과를 요약한다. 후행 깊이 보강은 phase 별 후속 PR.

## 산출물 목록

### Phase 2 — Sessions
- `apps/server/api/sessions/__init__.py` · `lifecycle.py` · `recovery.py` · `events.py` · `ops.py` · `compression.py`
- C v3.3.4~3.3.11 의 transcript drift / tool evidence repair 알고리즘 이식
- compression session alias persistence
- SSE 이벤트 스트림 (`/api/sessions/_stream`)
- chat 엔드포인트 — 세션 자동 저장
- **EmbeddedAdapter** — Hermes Agent `AIAgent` 클래스 동적 import + best-effort 호출 + 명확한 실패 메시지
- **7 pytest 케이스 100% 통과**

### Phase 3 — Workspace + Files + Terminal
- `apps/server/api/workspace.py` — 화이트리스트 path 가드(C 패턴), list/read/write/delete, 2MB 인라인 한도
- `apps/server/api/terminal.py` — 명령 allowlist + cwd 안전성 + 30s 타임아웃

### Phase 4 — Skills / MCP / Memory
- `apps/server/api/skills.py` — gateway 우선 + 로컬 `~/.hermes/skills` 폴백
- `apps/server/api/mcp.py` — `~/.hermes/mcp.json` CRUD + gateway 프록시
- `apps/server/api/memory.py` — `~/.hermes/memory/*.md` 브라우징/편집

### Phase 5 — Tasks / Kanban / Cron
- `apps/server/api/tasks.py` — 7 레인(A) + aging 정책(C v3.3.3)
- `apps/server/api/cron.py` — 5-필드 cron 평가기 + 백그라운드 스케줄러 + run-now

### Phase 6 — Conductor + Swarm (Python 포팅)
- `apps/server/api/swarm/foundation.py` — tmux 매니저 + 서브프로세스 폴백
- `apps/server/api/swarm/lifecycle.py` — 워커 상태 머신
- `apps/server/api/swarm/missions.py` — 휴리스틱 역할 분해
- `apps/server/api/swarm/conductor.py` — sanitize_mission (injection 가드)
- `apps/server/api/swarm/routes.py` — 워커/미션 HTTP API

### Phase 7 — Health / Dashboard / Inspector
- `apps/server/api/dashboard.py` — agent/system 헬스 + 대시보드 요약 + 로그 redaction(C 정책)

### Phase 8 — PWA + Mobile
- `vite-plugin-pwa` 통합 (API no-cache + cache-first assets, B 패턴)
- `manifest.json` (Vite 자동생성)
- `apps/web/src/hooks/use-mobile.ts` — 반응형 훅
- `public/favicon.svg`

### Phase 9 — Themes(6) + 3D feature flag
- `apps/web/src/styles/globals.css` — Hermes/Nous/Bronze/Slate/Mono/**Glass** 6 테마, Firefox 성능 모드(C v3.3.13)
- `apps/web/src/stores/theme-store.ts` — localStorage 영속화 + DOM `data-theme` 적용
- `apps/web/src/components/agent-avatar.tsx` — `VITE_FEATURE_3D` 게이트, 모바일 자동 2D fallback

### Phase 10 — Docker + ctl.sh + install.sh
- `scripts/ctl.sh` — daemon start/stop/restart/status/logs (B 패턴)
- `scripts/install.sh` — one-line installer (A 패턴)
- `docker/Dockerfile` — multi-stage (node 빌드 → python 런타임)
- `docker/docker-compose.yml` — 1-컨테이너 (embedded)
- `docker/docker-compose.two.yml` — agent + gui 분리
- `docker/docker-compose.three.yml` — agent + gui + Caddy 리버스 프록시
- `docker/Caddyfile` — 자동 TLS

### Phase 11 — Single-file build
- `apps/web/vite.config.ts` — `mode === 'singlefile'` 분기 + `vite-plugin-singlefile`
- `apps/server/serve_singlefile.py` — API + 단일 HTML 동시 서빙 (C 패턴)
- `pnpm build:singlefile` 스크립트

### Phase 12 — Electron
- `electron/main.cjs` — 백엔드 자식 프로세스 + health 대기 + BrowserWindow
- `electron/preload.cjs` — context-isolated bridge
- `electron/package.json` — electron-builder 설정 (mac/win/linux 타깃)
- unsigned dev build 만 지원, 사이닝은 후행 phase 결정

### Phase 13 — i18n (en + ko)
- `apps/web/src/locales/en.json` · `ko.json` — 30+ 메시지 키
- `apps/web/src/lib/i18n.ts` — `useT()`, `t()`, locale store, fallback chain

### Phase 14 — Tests / CI
- `apps/server/tests/conftest.py` — pytest fixture (ephemeral 서버)
- `apps/server/tests/test_*.py` — Phase 14 기준 **38+**, Phase 14.5 후 **51 케이스 통과**
- `apps/web/tests/i18n.test.ts` — vitest
- `apps/web/vitest.config.ts`
- `.github/workflows/ci.yml` — server tests + web build + docker smoke
- `.github/workflows/security.yml` — pip-audit + pnpm-audit (주간)

### Phase 14.5 — Pre-Phase-15 Hotfix / Production Readiness Gate
- `apps/server/api/passkeys.py` — COSE/CBOR negative integer spec fix (`-1 - n`) + malformed CBOR 400 처리
- `apps/server/server.py` — `apps/web/dist` 정적 파일 serving + SPA fallback + 정적/HTML/API cache 분리
- `apps/web/eslint.config.js` — ESLint flat config + `pnpm lint` 품질 gate 복구
- `apps/web/vite.config.ts`, `public/sw-cleanup.js` — `/api/*` service worker cache 제거 + 기존 `api` cache 삭제
- `apps/server/api/exec_policy.py` — terminal/PTY/cron/swarm 공통 `HERMES_GUI_ENABLE_EXEC` feature gate
- `apps/web/src/routes/workspace.tsx` — render-time draft overwrite 제거 + dirty state
- `apps/server/serve_singlefile.py` — 기본 HTML 경로를 `apps/web/dist/index.html`로 정렬

---

## 검증 결과

### 백엔드 pytest (Phase 14.5 후 51/51 통과)

```
tests/test_auth_flow.py::test_login_logout_cycle          PASSED
tests/test_auth_flow.py::test_oauth_passkey_stubs         PASSED
tests/test_health.py::test_health_open                    PASSED
tests/test_sessions.py::test_session_crud                 PASSED
tests/test_sessions.py::test_session_health_drift_repair  PASSED
tests/test_workspace_terminal.py::test_workspace_crud     PASSED
tests/test_workspace_terminal.py::test_terminal_allowlist PASSED
```

### 라우터 총괄 (각 Phase 누적)

| 그룹 | 엔드포인트 수 | 출처 |
|------|--------------|------|
| Auth | 9 | Phase 1 (OAuth/Passkey 501 포함) |
| Sessions | 7 | Phase 2 |
| Workspace | 4 | Phase 3 |
| Terminal | 1 | Phase 3 |
| Skills | 1 | Phase 4 |
| MCP | 3 | Phase 4 |
| Memory | 3 | Phase 4 |
| Tasks | 4 | Phase 5 |
| Cron | 4 | Phase 5 |
| Swarm | 3 | Phase 6 |
| Conductor | 1 | Phase 6 |
| Health/Dashboard | 4 | Phase 7 |
| **합계** | **44** | |

---

## 강화된 완료 정의 (Phase 14.5 이후)

- backend-only/Docker/Electron 진입점에서 `/`, `/chat`, `/api/health`가 모두 정상 응답해야 한다.
- `pnpm lint`, `pnpm typecheck`, `pnpm build`, `pnpm --filter @hermes-agent-gui/web test`, `python3 -m pytest apps/server -q`가 모두 통과해야 한다.
- service worker는 `/api/*` 응답을 Cache Storage에 저장하지 않아야 한다.
- 명령 실행 계열 API는 `HERMES_GUI_ENABLE_EXEC=1` 없이는 403 `exec_disabled`를 반환해야 한다.
- passkey COSE `alg=-7`, `alg=-257` golden vector가 통과해야 한다.

## 의도적 한계 (후행 작업)

- **EmbeddedAdapter** — Hermes Agent 의 실제 메서드 시그니처에 따라 추가 어댑팅 필요
- **GatewayAdapter** — OpenAI 호환 SSE 만 처리. Hermes 의 richer endpoint 는 후행
- **Terminal** — 단일 명령 실행만. xterm.js + WebSocket PTY 는 별도 라이브러리 필요
- **Conductor 미션 → 실제 워커 디스패치** — 본 phase 는 분해만 함. 워커 spawn 과 결합은 후행
- **OAuth / Passkey** — OAuth는 provider 설정 전 501/not configured. Passkey는 ES256/RS256 구현 및 CBOR regression test 포함.
- **Electron** — unsigned dev build. macOS notarization 은 사용자 컨펌 필요
- **TypeScript / 프론트 라우트** — 각 백엔드 모듈에 대응하는 frontend route 추가는 점진적
- **Backend redact 강도** — Phase 7 의 redact 패턴은 기본 셋. 사이트별 보강 가능

---

## 다음 액션 후보

1. **각 phase 별 frontend 라우트 추가** — sessions/workspace/skills/mcp/memory/tasks/cron/dashboard/swarm 페이지
2. **EmbeddedAdapter 실 환경 검증** — 실제 Hermes Agent 깔린 머신에서
3. **xterm.js + WebSocket PTY** — `websockets` 라이브러리 추가하여 진짜 터미널
4. **OAuth provider 연결 검증 + Passkey 실기기 smoke** — WebAuthn conformance 범위 확대
5. **Electron 사이닝** — Apple Developer Program 가입 + notarization
