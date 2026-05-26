# 11 · 통합 개발 계획서 (Phase 0 → 25) — 마스터 플랜 v2

> **Single source of truth** for hermes-agent-gui implementation.
> 누구든 본 문서만 보고 어느 Phase 든 PR 단위로 구현할 수 있도록 설계됨.
>
> 작성: 2026-05-25 · 전문가 리뷰 후 v2 갱신: 2026-05-26
>
> **개발 환경 가정** (사용자 컨펌): Hermes Agent 미설치 환경에서도 전 Phase 가 빌드/테스트 가능.
> 모든 Hermes 호출은 `HERMES_GUI_FAKE_BACKEND=echo` 또는 mock 으로 대체.
> 실 Hermes 통합 검증은 개발 완료 후 사용자 환경에서 별도 수행.

---

# 목차

- [§0 공통 표준 (Common Standards)](#0-공통-표준-common-standards)
  - [0.1 코딩 / 디자인 규칙](#01-코딩--디자인-규칙)
  - [0.2 데이터 모델 컨벤션](#02-데이터-모델-컨벤션)
  - [0.3 API 컨벤션](#03-api-컨벤션)
  - [0.4 마이그레이션 / 롤백 정책](#04-마이그레이션--롤백-정책)
  - [0.5 테스트 정책](#05-테스트-정책)
  - [0.6 보안 베이스라인](#06-보안-베이스라인)
  - [0.7 모니터링 / 로깅](#07-모니터링--로깅)
  - [0.8 i18n / a11y 규칙](#08-i18n--a11y-규칙)
  - [0.9 PR 분할 가이드](#09-pr-분할-가이드)
  - [0.10 개발자 onboarding (Day 1)](#010-개발자-onboarding-day-1)
- [§ 진행 현황 한눈에](#-진행-현황-한눈에)
- [§ Phase 0~14 핵심 요약](#-phase-014-핵심-요약)
- [§ Phase 14.5 — Pre-Phase-15 Hotfix](#-phase-145--pre-phase-15-hotfix--production-readiness-gate)
- [§ Phase 15 — Messaging Gateways + Profile Archive](#-phase-15--messaging-gateways--profile-archive)
- [§ Phase 16 — Multi-provider LLM + Slash Commands](#-phase-16--multi-provider-llm--slash-commands)
- [§ Phase 17 — Persona SOUL + FTS5 + Usage](#-phase-17--persona-soul--fts5--usage)
- [§ Phase 18 — Auto-Compress + RAG](#-phase-18--auto-compress--rag)
- [§ Phase 19 — Memory Plugins + PII Redaction](#-phase-19--memory-plugins--pii-redaction)
- [§ Phase 20 — Group Chat + Auto-Updater + Backup](#-phase-20--group-chat--auto-updater--backup)
- [§ Phase 21 — Knowledge Graph (GBrain)](#-phase-21--knowledge-graph-gbrain)
- [§ Phase 22 — Code Knowledge Graph](#-phase-22--code-knowledge-graph)
- [§ Phase 23 — Computer-Use + Browser-Use](#-phase-23--computer-use--browser-use)
- [§ Phase 24 — UX Quick Wins](#-phase-24--ux-quick-wins)
- [§ Phase 25 — Office 3D + Multi-CLI + Marketplace](#-phase-25--office-3d--multi-cli--marketplace)
- [§ 의존성 매트릭스](#-의존성-매트릭스)
- [§ 16주 실행 일정](#-16주-실행-일정)
- [§ 부록 A — 의존성 버전 매트릭스](#-부록-a--의존성-버전-매트릭스)
- [§ 부록 B — 용어집](#-부록-b--용어집)
- [§ 부록 C — FAQ](#-부록-c--faq)

---

# §0 공통 표준 (Common Standards)

이 섹션은 Phase 15~25 의 모든 신규 구현에 자동 적용된다. 각 phase 본문에서 반복 명시하지 않아도 본 표준이 baseline.

## 0.1 코딩 / 디자인 규칙

### 백엔드 (Python)
- **Python 3.11+** 만 지원. `dataclasses`, walrus, `match` 사용 OK.
- **dependency 추가 정책**: 외부 의존성은 `requirements.txt` 에 명시. 신규 추가 시 본 문서의 [§ 부록 A](#-부록-a--의존성-버전-매트릭스) 도 갱신.
- **모듈 크기**: 한 파일 ≤ 500 라인. 초과 시 분할.
- **타입 힌트**: 모든 public 함수에 type hints. mypy `--strict` 통과 (CI 추가 예정).
- **로깅**: `logging.getLogger(__name__)` — print 금지.
- **에러 처리**: 외부 boundary 에서만 `except Exception`. 내부는 좁은 예외만.
- **싱글톤 회피**: module-level state 최소화. test fixture 가 깨끗하게 시작할 수 있도록.

### 프론트엔드 (TypeScript / React)
- **React 19 + TypeScript 5.7** strict mode.
- **함수 컴포넌트** 만. class 금지.
- **상태**: 로컬 → `useState`, 도메인 → zustand store, 서버 캐시 → TanStack Query.
- **라우팅**: TanStack Router file-based. `createFileRoute('/path')`. 새 라우트 추가 시 `pnpm dev` 가 `routeTree.gen.ts` 자동 재생성.
- **CSS**: Tailwind v4 utility 만. `border-token`, `surface`, `text-muted` 같은 테마 토큰 사용 ([§0.8](#08-i18n--a11y-규칙) 참조).
- **컴포넌트 크기**: 한 파일 ≤ 300 라인. 초과 시 분할.

### 파일/디렉토리
- 백엔드: `apps/server/api/<domain>/{__init__,routes,store,models,...}.py`
- 프론트엔드: `apps/web/src/{routes,components,lib,stores,hooks}/`
- 한 도메인 = 한 디렉토리. 도메인간 import 는 `__init__.py` 의 명시적 export 만.

## 0.2 데이터 모델 컨벤션

```python
# 모든 도메인 객체는 frozen=True dataclass + to_dict() / from_dict() 쌍

from dataclasses import dataclass, field

@dataclass
class Foo:
    id: str
    name: str
    created_at: int
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name,
                "created_at": self.created_at, "metadata": self.metadata}

    @staticmethod
    def from_dict(d: dict) -> "Foo":
        return Foo(id=str(d["id"]), name=str(d["name"]),
                   created_at=int(d["created_at"]),
                   metadata=dict(d.get("metadata") or {}))
```

SQLite 컬럼:
- 시간: `INTEGER` (epoch seconds). UTC 만 저장.
- JSON: `TEXT` 컬럼 + 직렬화 (Pydantic 회피).
- 인덱스: 검색에 사용하는 모든 컬럼에 명시.
- WAL 모드 활성화 (`PRAGMA journal_mode=WAL`).

## 0.3 API 컨벤션

### URL
- `/api/<domain>/<action>` — 자원 단수형. domain 은 kebab-case 가 아닌 snake_case (`/api/code_graph` ❌ `/api/codegraph` ✓).
- Path 파라미터: `{snake_case}`.
- Query 파라미터: snake_case.

### Method 시맨틱
| Method | 용도 | 멱등성 |
|--------|------|--------|
| GET | 조회 | ✓ |
| POST | 생성 / 트리거 / 부작용 있는 액션 | ✗ |
| PUT | 전체 교체 | ✓ |
| PATCH | 부분 갱신 (미사용 — PUT 으로 통일) | ✓ |
| DELETE | 삭제 | ✓ |

### 인증
- 모든 `/api/*` 는 [Phase 1 의 `authenticate()`](../../apps/server/api/auth.py) 통과 필수.
- 예외: `/api/health`, `/api/auth/login`, `/api/csp-report`, `/api/auth/oauth/*` (callback 만).

### 응답 형식
성공:
```json
HTTP 200 OK
Content-Type: application/json
{ /* domain payload */ }
```

생성:
```json
HTTP 201 Created
{ "id": "...", ...resource }
```

에러:
```json
HTTP 4xx/5xx
{ "error": "<short_code>", "detail": "<optional human-readable>" }
```

`error` 코드는 snake_case 영문 enum. detail 은 i18n 안 함 (로깅용).

### 페이지네이션
| 쿼리 | 의미 | 기본 |
|------|------|-----|
| `limit` | 결과 최대 갯수 | 50 |
| `cursor` | opaque 토큰 (timestamp + id) | (없음) |

응답에 `next_cursor` 포함. URL 페이지네이션 (`?page=2`) 미사용.

### SSE
- `Content-Type: text/event-stream; charset=utf-8`
- 헤더 `Cache-Control: no-store`, `X-Accel-Buffering: no`
- 이벤트 종료 시 `Connection: close` (curl 친화).
- 표준 이벤트: `ready`, `token`, `tool_call`, `done`, `error`, `ping` (15s 간격).

## 0.4 마이그레이션 / 롤백 정책

### Schema migration
- **새 phase 가 SQLite schema 를 추가**할 때:
  1. **순방향 호환**: 기존 컬럼 추가만 (drop 금지). NULL 허용 + 기본값.
  2. 신규 테이블은 `IF NOT EXISTS` 로 생성.
  3. 마이그레이션 함수는 `api/<domain>/migrations.py` 에 버전별로:
     ```python
     def migrate(conn: sqlite3.Connection, current_version: int) -> int:
         if current_version < 1:
             conn.execute("CREATE TABLE IF NOT EXISTS foo(...)")
             current_version = 1
         if current_version < 2:
             conn.execute("ALTER TABLE foo ADD COLUMN bar TEXT")
             current_version = 2
         return current_version
     ```
  4. 부팅 시 `migrate(conn, get_schema_version(conn))` 호출.
  5. `schema_versions` 메타 테이블에 도메인별 버전 저장.

### Data migration
- **Backfill 필요** 시 별도 worker 스레드로 처리 (서버 부팅 차단 금지).
- 부분 실패해도 다음 부팅 시 계속할 수 있도록 idempotent.

### 롤백
- SQLite migration 은 **순방향만**. 롤백은 SQLite 파일 백업 → 복원 (Phase 20 의 backup 기능 활용).
- 코드 롤백은 git revert. 단, 새 컬럼은 `NULL` 허용이라 구버전 코드도 동작.

## 0.5 테스트 정책

### 정량 목표
| 영역 | 목표 |
|------|------|
| 백엔드 unit (pytest) | 핵심 모듈 라인 커버리지 ≥ 80% |
| 백엔드 통합 (HTTP) | 모든 신규 엔드포인트에 최소 happy-path + 1 에러 케이스 |
| 프론트 unit (vitest) | 모든 lib/ 함수 + store 핵심 분기 |
| 프론트 E2E (playwright) | 로그인 → 챗 1회전 → 세션 복구 (회귀 보호) |

### 테스트 작성 규칙
```python
# pytest naming
def test_<subject>_<scenario>():
    # arrange
    # act
    # assert
```

### Echo 모드 강제
- 모든 backend test 는 `HERMES_GUI_FAKE_BACKEND=echo` + `HERMES_GUI_STATE_DIR=tmp_path/state` 로 격리.
- 실 Hermes / 실 OpenAI 호출 금지 (responses_mock fixture 제공).

### Test fixtures
- `apps/server/tests/conftest.py` 의 `server` + `client` fixture 재사용.
- 새 도메인은 해당 도메인용 builder fixture 추가 (`make_session`, `make_task` 등).

## 0.6 보안 베이스라인

### 자동 적용 (Phase 1 / 14 / 15)
- HMAC SHA-256 쿠키, `secrets.token_hex(32)` 시크릿, 0600 권한.
- `hmac.compare_digest` constant-time.
- Fail-closed remote bind.
- 자동 헤더: CSP / X-Frame-Options: DENY / X-Content-Type-Options: nosniff / Referrer-Policy.
- Global rate limit (POST/PUT/DELETE — auth 외): 300/60s/IP.
- Login rate limit: 5/60s/IP.
- 로그 redaction: 11 패턴 (OpenAI/Anthropic/AWS/JWT/GitHub PAT/Slack/Google/PEM/DB URL/Bearer/API key).

### 신규 Phase 가 추가해야 할 것
- **외부 호출 endpoint**: 화이트리스트 + timeout + retry 한도 + 응답 크기 한도.
- **사용자 입력 path**: `_safe_path()` (Phase 3) 통과.
- **credential 저장**: `~/.hermes-agent-gui/` 하위 + 0600. profile-scoped.
- **SQL**: parameterized query 만. f-string 금지.
- **HTML**: React JSX 만. dangerouslySetInnerHTML 금지 (마크다운은 rehype-sanitize).

### 위협 모델 템플릿
각 phase 의 §보안 위협 모델 섹션은 다음 표 형태:
| 자산 (asset) | 위협 (threat) | 영향 (impact) | 완화 (mitigation) |
|------|------|------|------|
| ... | ... | ... | ... |

## 0.7 모니터링 / 로깅

### 로그 레벨
- `DEBUG`: 개발 시 stdout. 프로덕션 미수집.
- `INFO`: 도메인 이벤트 (session created, cron fired). dashboard logs 에 노출 (redacted).
- `WARNING`: 사용자에게 영향있는 비-실패 (rate limit hit, slow query).
- `ERROR`: 처리 못한 예외, 외부 호출 실패.

### 메트릭 (Phase 17 usage + Phase 20 dashboard 가 시각화)
| 메트릭 | 단위 | 라벨 |
|--------|-----|------|
| `chat_turns_total` | counter | `provider`, `profile`, `success` |
| `chat_tokens` | counter | `provider`, `direction`(in/out) |
| `chat_cost_usd` | counter | `provider`, `model` |
| `chat_latency_ms` | histogram | `provider`, `model` |
| `sessions_active` | gauge | `profile` |
| `auth_login_failures` | counter | `reason` |

저장: SQLite `metrics_events(ts, name, labels_json, value)` 테이블 + Phase 17 의 usage rollup.

## 0.8 i18n / a11y 규칙

### i18n
- 모든 사용자 가시 문자열은 `t('namespace.key')` 사용.
- 새 키 추가 시 `en.json` + `ko.json` 동시 수정 — CI 가 누락 검증 (Phase 14).
- 키 명명: `<domain>.<action>` (`messaging.platform.telegram.label`).
- 문장 부호는 키 값에 포함 (마침표/이모지). 코드에서 `+ '.'` 같은 합성 금지.

각 phase 의 §i18n 키 추가 섹션에 추가될 키 enumeration.

### a11y (접근성)
- 모든 button/link 에 `aria-label` (텍스트만 있는 경우 생략 OK).
- 키보드 nav: Tab 순서 의도적. 명령 팔레트 Cmd+K.
- `role="alert"` for ErrorMsg (Phase 0 의 `Page.tsx` 이미 적용).
- 색상 외에 의미 전달: 아이콘 + 텍스트.
- `<table>` 미사용 (CSS grid). 표의 경우 `<th scope>` 필수.

## 0.9 PR 분할 가이드

각 Phase 는 다음 사이즈 룰을 따른다:
| PR 크기 | 변경 라인 | 리뷰 시간 |
|---------|----------|----------|
| **S** | ≤ 200 라인 (테스트 포함) | 30분 |
| **M** | 200~600 라인 | 1~2시간 |
| **L** | 600~1500 라인 | 반나절 |
| **XL** | > 1500 라인 | **분할 강제** |

각 Phase 본문의 §PR 분할 권장 섹션에 권장 분할안.

### 일반 PR 순서
1. **Backend foundation** — schema + models + base routes (테스트 포함)
2. **API surface 확장** — 핵심 endpoints (테스트 포함)
3. **Frontend route + client** — UI + API client
4. **i18n + a11y + 폴리시** — 마무리
5. **E2E + 문서** — playwright 또는 smoke + README 업데이트

## 0.10 개발자 onboarding (Day 1)

새 개발자가 Phase X 를 할당받았을 때 첫날 따라할 절차:

1. **저장소 클론 + 부팅 검증**:
   ```bash
   git clone https://github.com/your-org/hermes-agent-gui
   cd hermes-agent-gui
   pip install -r apps/server/requirements.txt
   pnpm install
   HERMES_GUI_PASSWORD=demo HERMES_GUI_FAKE_BACKEND=echo \
     python3 apps/server/server.py --port 8800 &
   pnpm dev
   # → http://localhost:5173 에 채팅 동작 확인
   ```
2. **회귀 테스트 통과 확인**:
   ```bash
   cd apps/server && python3 -m pytest -v
   cd ../web && pnpm vitest run
   ```
3. **문서 정주행**:
   - `docs/review/00-overview.md` — 전체 그림
   - `docs/review/06-integration-design.md` — 아키텍처
   - **본 문서 §Phase X** — 본인 phase 상세
   - 의존성 phase 의 코드 (`apps/server/api/<...>` 와 `apps/web/src/...`)
4. **PR 분기 생성**: `feat/phase-X-<short-name>` 또는 phase 가 큰 경우 `feat/phase-X-pr1-foundation` 등.
5. **첫 commit 은 비어있어도 됨** — early signal 로 동료가 알게.

---

# 📊 진행 현황 한눈에

| Phase | 단계 | 상태 | 산출물 한 줄 |
|-------|------|------|--------------|
| 0 | 모노리포 부트스트랩 | ✅ | pnpm + vite + python venv + Hello World |
| 1 | 인증 + 기본 SSE 채팅 | ✅ | password + bearer + cookie + echo/gateway/embedded |
| 2 | 세션 라이프사이클 + repair | ✅ | 5 모듈 + transcript drift repair + alias |
| 3 | 워크스페이스 + 파일 + 터미널 | ✅ | path guard + Monaco-ready + exec allowlist |
| 4 | Skills / MCP / Memory | ✅ | catalog + registry CRUD + memory viewer |
| 5 | Tasks / Kanban / Cron | ✅ | 7 lanes + aging + cron scheduler |
| 6 | Conductor + Swarm | ✅ | mission decompose + tmux/subprocess + dispatch |
| 7 | Health / Dashboard / Inspector | ✅ | agent/system probe + redacted logs |
| 8 | PWA + Mobile | ✅ | vite-plugin-pwa + offline shell + iOS icons |
| 9 | Themes (6) + 3D flag | ✅ | Hermes/Nous/Bronze/Slate/Mono/Glass |
| 10 | Docker + ctl.sh + bootstrap | ✅ | 1/2/3 컨테이너 compose + Caddy |
| 11 | Single-file build | ✅ | `pnpm build:singlefile` + serve_singlefile.py |
| 12 | Electron desktop | ✅ | unsigned dev build + auto-update 설정 |
| 13 | i18n (en + ko) | ✅ | t() + locale store + 30+ 키 |
| 14 | Tests / CI | ✅ | pytest 38 + vitest 13 + GitHub Actions |
| 14.5 | Pre-Phase-15 Hotfix | ✅ | passkey/SPA/lint/PWA/exec/singlefile + pytest 51 |
| **15** | **Messaging Gateways + Profile Archive** | ✅ done | 15a+15b+15c 완료; pytest 82/82 + vitest 16/16 + lint/typecheck/build 통과 |
| 16 | Multi-provider LLM + Slash Commands | ✅ done | 14 provider + 22 slash + model picker |
| 17 | Persona + FTS5 + Usage | ✅ done | SOUL + Cmd/Ctrl+K + Recharts |
| 18 | Auto-Compress + RAG | ⏳ | 자동 요약 + 벡터 검색 |
| 19 | Memory Plugins + PII | ⏳ | 6 plugin + 입력 PII 가드 |
| 20 | Group + Updater + Backup | ⏳ | 멀티 에이전트 + auto-update + tar.gz dump |
| 21 | Knowledge Graph | ⏳ | entity + edges + 합성 답변 |
| 22 | Code Knowledge Graph | ⏳ | tree-sitter pre-index + symbol lookup |
| 23 | Computer/Browser-use | ⏳ | Playwright tool + 스크린샷 |
| 24 | UX Quick Wins | ⏳ | sidebar 그룹 + virtualized + CLI maint |
| 25 | Office 3D + Multi-CLI + Marketplace | ⏳ | Claw3d + Codex/Gemini + preset 라이브러리 |

---

# 📦 Phase 0~14 핵심 요약

각 완료된 phase 의 *핵심 인터페이스* 한 단락 — 다음 phase 가 무엇을 활용 가능한지 빠른 참조.

### Phase 0 — 부트스트랩
모노리포: `apps/{server,web}/` + `packages/` + `docker/` + `electron/`. `pnpm install + python3 apps/server/server.py` 로 동작. 상세: [`07-phase-0-checklist.md`](./07-phase-0-checklist.md).

### Phase 1 — 인증 + SSE 채팅
- `apps/server/api/auth.py`: `authenticate(req, cfg) → Session | None`. Bearer + HMAC 쿠키.
- `apps/server/api/runtime_adapter.py`: `select(cfg) → Adapter`. Echo/Gateway/Embedded/NoBackend.
- `apps/server/api/streaming.py`: `begin_sse()`, `write_event()`, `stream_events()`.
- 신규 phase 가 인증 필요 시: `if auth_module.authenticate(req, cfg) is None: return Response(401, ...)`.
- 신규 SSE endpoint: `streaming.begin_sse(req.raw); streaming.write_event(req.raw, "token", data)`.
상세: [`08-phase-1.md`](./08-phase-1.md).

### Phase 2 — 세션 + Repair
- `apps/server/api/sessions/lifecycle.py`: `SessionStore`. `create/get/list/append_messages/replace_messages/rename/delete`.
- `apps/server/api/sessions/recovery.py`: `session_health()`, `repair_transcript_drift()`.
- `apps/server/api/sessions/events.py`: pub/sub for SSE `/api/sessions/_stream`.
- `apps/server/api/sessions/compression.py`: `register_alias(old, new)`, `alias_resolve(sid)`.
- DB: `~/.hermes-agent-gui/sessions.db` (SQLite WAL).
신규 phase 가 chat 통합 시 `store.append_messages(sid, [Message(...)])` 호출.

### Phase 3 — 워크스페이스 + 터미널
- `apps/server/api/workspace.py`: `_safe_path(rel) → Path` (화이트리스트 가드, 재사용 권장).
- `apps/server/api/terminal.py`: `EXEC_ALLOWED_BINS` + `subprocess.run`.
- `apps/server/api/pty.py`: 진짜 PTY (`/api/pty/*`). xterm.js 통합 가능.

### Phase 4 — Skills / MCP / Memory
- `apps/server/api/{skills,mcp,memory}.py`: 각각 list/CRUD. Hermes Agent gateway 우선 + 로컬 폴백.

### Phase 5 — Tasks / Cron
- `apps/server/api/tasks.py`: 7 lanes (`backlog/ready/running/review/blocked/needs_you/done`) + aging (`DONE_TTL_SECONDS=2h`, `NEEDS_YOU_TTL=12h`).
- `apps/server/api/cron.py`: 5-필드 crontab + 백그라운드 스케줄러 + `run_now`.

### Phase 6 — Conductor + Swarm
- `apps/server/api/swarm/foundation.py`: `SwarmFoundation` — tmux + subprocess fallback. `spawn/list/get/kill/tail_log`.
- `apps/server/api/swarm/missions.py`: `decompose_mission(prompt)` — 휴리스틱 role 분해.
- `apps/server/api/swarm/dispatch.py`: `dispatch(foundation, mission)` — mission 의 sub-task 별 worker spawn.
- `apps/server/api/swarm/conductor.py`: `sanitize_mission(prompt)` — injection 가드.

### Phase 7 — Health / Dashboard
- `apps/server/api/dashboard.py`: `_redact(text)` (11 패턴), `_probe_gateway(cfg)`, `_system_stats()`, `_dashboard_summary()`.
- `/api/health/agent`, `/api/health/system`, `/api/dashboard`, `/api/inspector/logs`.

### Phase 8 — PWA
- `apps/web/vite.config.ts`: `VitePWA` 플러그인 + `navigateFallback: '/offline.html'`.
- `apps/web/src/hooks/use-mobile.ts`: 반응형 hook.
- `apps/web/public/offline.html`, `apple-touch-icon.svg`.

### Phase 9 — 6 Themes
- `apps/web/src/styles/globals.css`: `@custom-variant dark (...)` + 6 테마 변수 (`--color-bg/fg/border/surface/muted-fg/accent`).
- `apps/web/src/stores/theme-store.ts`: `useThemeStore`. THEMES = ['hermes','nous','bronze','slate','mono','glass'].

### Phase 10 — Docker / ctl.sh
- `scripts/ctl.sh`: `start/stop/restart/status/logs`.
- `docker/docker-compose.{yml,two.yml,three.yml}` — 1/2/3 컨테이너.
- `scripts/install.sh` — one-line installer.

### Phase 11 — Single-file
- `pnpm build:singlefile` → `dist/index.html` 단일 ≈800KB.
- `apps/server/serve_singlefile.py` — API + 단일 HTML 동시 서빙.

### Phase 12 — Electron
- `electron/main.cjs` — 백엔드 자식 프로세스 + BrowserWindow + health 대기.
- `electron-builder` 설정 — DMG/EXE/AppImage. unsigned dev build only.

### Phase 13 — i18n
- `apps/web/src/lib/i18n.ts`: `useT()`, `t(key, params)`, `useLocaleStore`.
- `apps/web/src/locales/{en,ko}.json` — 30+ 키.

### Phase 14 — Tests / CI
- `apps/server/tests/conftest.py` — `server` + `client` fixture.
- `.github/workflows/{ci,security}.yml` — pytest + web build + docker smoke + pip-audit + pnpm-audit.

---

# 🛠 Phase 14.5 — Pre-Phase-15 Hotfix / Production Readiness Gate

**기간**: 4.5일 · **목표**: Phase 0~14 완료 정의 강화 후 Phase 15 진입 · **의존성**: Phase 14

Phase 15 Messaging은 API/credential/profile surface를 크게 확장하므로, 그 전에 baseline 배포·보안·품질 gate를 먼저 고정한다.

## 범위

| 순서 | 항목 | 구현 기준 | 테스트 기준 |
|---:|---|---|---|
| 1 | Passkey CBOR/COSE | negative int `-1 - n`, ES256/RS256 golden vector, malformed CBOR 400 | `test_passkeys_cbor.py` |
| 2 | SPA serving | `server.py`가 `apps/web/dist` 서빙, non-API GET은 `index.html` fallback | `/`, `/chat`, `/api/health` smoke |
| 3 | Lint infra | ESLint flat config + `pnpm lint` CI gate | `pnpm lint` |
| 4 | PWA API no-cache | Workbox `/api/*` runtime cache 제거, 기존 `api` cache 삭제 | `dist/sw.js` inspection |
| 5 | Exec feature gate | terminal/PTY/cron/swarm은 `HERMES_GUI_ENABLE_EXEC=1` 필요, remote bind는 추가 opt-in | 403 `exec_disabled` regression |
| 6 | Workspace editor | render-time setState 제거, dirty draft 보존 | typecheck/test + manual smoke |
| 7 | Singlefile path | 기본 HTML 경로 `apps/web/dist/index.html` | `serve_singlefile.py` smoke |
| 8 | Docs | `09`, `11`, `12`, README, SECURITY 동기화 | 명령어 smoke |

## 공통 완료 기준

- `python3 -m pytest apps/server -q`
- `pnpm lint`
- `pnpm typecheck`
- `pnpm --filter @hermes-agent-gui/web test`
- `pnpm build`
- `pnpm --filter @hermes-agent-gui/web build:singlefile`
- backend-only smoke: `/`, `/chat`, `/api/health`

---

# 🌐 Phase 15 — Messaging Gateways + Profile Archive

**기간**: 2주 · **출처**: G(hermes-desktop) + H(hermes-web-ui) · **의존성**: Phase 1, 2(profile), 7(health), 10(docker)

## 구현 상태 (2026-05-26)

- ✅ **Phase 15a 완료**: `apps/server/api/messaging/` foundation, 16 platform registry, 14 delegated wrappers, credential atomic write/merge/0600, behavior YAML, `messaging_status` SQLite schema, delegated Hermes probe, HTTP routes.
- ✅ **Phase 15b 완료**: direct Webhook token/HMAC inbound, 256KB limit, 60/min rate limit, Echo/Gateway adapter invocation, Home Assistant notify REST runtime.
- ✅ **Phase 15c 완료**: 16-platform messaging UI, credential/behavior/status drawer, profile archive export/import/clone, MANIFEST checksum, safe tar import, import 후 재로그인 flow, en/ko i18n.
- ✅ 검증: `python3 -m pytest apps/server -q` → 82 passed, `pnpm --filter @hermes-agent-gui/web test` → 16 passed, `pnpm lint`, `pnpm typecheck`, `pnpm build` 통과.
- ✅ **Phase 16 완료**: 14 provider preset catalog, provider CRUD + `.env` key storage, `/models` discovery with 5-minute cache/provider quirks, OAuth PKCE state TTL, server/client slash parser, Providers route, chat model picker/slash menu.
- ✅ 검증: `python3 -m pytest apps/server -q` → 93 passed, `pnpm --filter @hermes-agent-gui/web test` → 19 passed, `pnpm lint`, `pnpm typecheck`, `pnpm build` 통과.
- ✅ **Phase 17 완료**: SOUL.md persona presets/editor, FTS5 incremental/backfill search + Cmd+K modal, usage_turns rollup/cost calculator, Recharts usage page.
- ✅ 검증: `python3 -m pytest apps/server -q` → 100 passed, `pnpm --filter @hermes-agent-gui/web test` → 20 passed, `pnpm lint`, `pnpm typecheck`, `pnpm build` 통과.
- ⏭️ 다음 순서: Phase 18 Auto-Compress + RAG.

## ✅ 확정 결정 (2026-05-26)

이 Phase 시작 전 컨펌된 두 가지 architectural decisions. 본 Phase 의 모든 산출물은 이 결정 위에 빌드됨.

### 결정 1 — 메시징 통합 모델: **Hybrid (위임 + 2개 직접)**

> **14개 플랫폼 (대다수)**: Hermes Agent 본체에 위임 (우리는 credential / behavior 설정 UI 만 제공).
> **2개 플랫폼**: 우리가 직접 처리.

| 플랫폼 | 모드 | 우리가 만드는 것 | Hermes 본체가 하는 것 |
|--------|------|-------------------|----------------------|
| Telegram | 위임 | bot_token 저장 + behavior YAML 편집 | bot connection, message routing, response 발송 |
| Discord | 위임 | 같음 | 같음 |
| Slack | 위임 | 같음 | 같음 |
| WhatsApp | 위임 | 같음 | 같음 |
| Signal | 위임 | 같음 | 같음 |
| Matrix | 위임 | 같음 | 같음 |
| Mattermost | 위임 | 같음 | 같음 |
| Email | 위임 | IMAP/SMTP 자격증명 저장 | 메일 수신/발송 |
| SMS | 위임 | Twilio/Vonage key 저장 | SMS 송수신 |
| iMessage | 위임 | BlueBubbles bridge URL 저장 | message routing |
| DingTalk | 위임 | App key 저장 | 봇 동작 |
| Feishu / Lark | 위임 | App ID/Secret 저장 | 봇 동작 |
| WeCom | 위임 | Bot ID/Secret 저장 | 봇 동작 |
| WeChat | 위임 | QR login session 관리 | 봇 동작 |
| **Webhook** | **직접** | endpoint 등록 + signature 검증 + LLM 호출 + 응답 | (관여 안 함) |
| **Home Assistant** | **직접** | webhook + HA REST API 호출 | (관여 안 함) |

**근거**:
- 14 플랫폼 = NousResearch 가 이미 본체에서 통합 유지. 우리가 다시 만드는 건 작업 6~8주 + 영구 유지보수 부담.
- Webhook / Home Assistant = 외부 봇 라이브러리 불필요 (사용자 자기 endpoint 임). 우리가 직접 처리해도 부담 적음 + Hermes 미설치 환경에서도 동작.
- "Zero-fork" 원칙 유지: Hermes 본체 미수정.

**의미**:
- 우리 backend 에 `python-telegram-bot`, `discord.py`, `slack-sdk` 같은 16개 라이브러리 **추가하지 않음**.
- 14 플랫폼의 `test_connection()` 은 *credential 형식 검증 + Hermes Agent 로 검증 위임 호출* (예: Hermes 의 `/v1/messaging/test/{platform}` 같은 endpoint 호출 — 본체 지원에 의존).
- 14 플랫폼은 Hermes Agent 가 설치/실행되어야 실연결 가능.
- 2 플랫폼 (Webhook/HA) 은 우리 backend 가 단독으로 동작 → Echo 모드에서도 검증 가능.

### 결정 2 — Profile archive 의 device-specific 제외 정책: **확장 제외 리스트**

> 백업 / archive 파일에서 **device-secret + per-device auth state + 일시 파일** 모두 제외.

```python
# apps/server/api/profile_archive.py 의 상수
ARCHIVE_EXCLUDE_PATTERNS = [
    "secret",                # HMAC 서명 키 — 노출 시 쿠키 위조 가능
    "passkeys.json",         # 디바이스별 WebAuthn 자격증명 (다른 디바이스에서 의미 없음)
    ".login-lock.json",      # IP rate-limit 상태 (디바이스별)
    "*.pid",                 # 프로세스 ID
    "*.lock",                # 파일 lock
    "*.log",                 # 로그 (redact 했어도 민감 가능성)
    "session-aliases.json",  # 머신간 일관성 의문, 새 머신에서 재시작
    "memory_vss.db-shm",     # SQLite WAL/SHM 임시 파일
    "memory_vss.db-wal",
    "sessions.db-shm",
    "sessions.db-wal",
]
```

**의미**:
- 백업 파일을 **클라우드 / 팀 공유** 에 둘 수 있는 안전 수준 확보 (채팅 내용 유출 위험은 별개로 사용자 주의).
- Import 직후 사용자는 **재로그인** 1회 필요. UI 토스트로 안내.
- MANIFEST.json 에 `excludes` 배열로 명시 → import 측에서 표시.

---

## 사용자 스토리

> 사용자 Alice 는 데스크탑에서 Hermes Agent 를 띄워 자신의 Telegram 봇과 Slack 워크스페이스에 연결한다.
> 이동 중 휴대폰에서 같은 봇에게 메시지를 보내면, 에이전트(Hermes 본체)가 같은 컨텍스트로 응답한다 — 우리 GUI 는 설정만 했다.
> Alice 가 자기 홈 서버의 Home Assistant 에서 "Hermes 에게 알림 보내기" 자동화를 추가 → Webhook URL 을 우리 GUI 에서 발급받아 HA 에 입력 → 우리 backend 가 webhook 받아 Hermes 호출 → 응답을 HA 로 보냄.
> Alice 가 새 노트북으로 이사할 때, 기존 GUI 에서 profile 을 tar.gz 로 export 해 새 머신에서 import. **재로그인 1회 필요** (secret 이 device-specific 이라). 채팅 기록 / 스킬 / 메모리 / 메시징 credential 은 그대로 복원.

## 데이터 모델

```python
# apps/server/api/messaging/models.py

from dataclasses import dataclass, field
from typing import Literal

PlatformId = Literal[
    "telegram", "discord", "slack", "whatsapp", "signal", "matrix",
    "mattermost", "email", "sms", "imessage", "dingtalk", "feishu",
    "wecom", "wechat", "webhook", "home_assistant",
]

@dataclass(frozen=True)
class PlatformMeta:
    id: PlatformId
    label: str
    description: str
    credential_fields: list["CredentialField"]
    behavior_schema: dict  # JSON-schema-like for behavior settings
    docs_url: str

@dataclass(frozen=True)
class CredentialField:
    name: str                        # 'bot_token' 등
    label: str                       # UI 라벨
    type: Literal["text", "password", "url", "select", "qr"]
    required: bool = True
    placeholder: str = ""
    pattern: str | None = None       # 정규식 검증
    options: list[str] | None = None # select 용

@dataclass
class PlatformStatus:
    id: PlatformId
    configured: bool
    connected: bool
    last_event_at: int | None
    last_error: str | None
```

## API 스키마

### `GET /api/messaging/platforms`

응답:
```json
{
  "platforms": [
    {
      "id": "telegram",
      "label": "Telegram",
      "description": "Bot token + mention control",
      "credential_fields": [
        {"name":"bot_token","label":"Bot Token","type":"password","required":true,
         "pattern":"^[0-9]+:[A-Za-z0-9_-]+$","placeholder":"123456:ABC-DEF..."}
      ],
      "behavior_schema": {
        "mention_required": {"type": "boolean", "default": false},
        "allowed_chat_ids": {"type": "array", "items": "integer"}
      },
      "configured": true,
      "connected": true,
      "last_event_at": 1779789999,
      "last_error": null,
      "docs_url": "https://hermes-agent.nousresearch.com/docs/integrations/telegram"
    },
    /* ... 15 more ... */
  ]
}
```

### `POST /api/messaging/{platform}/configure`

요청:
```json
{
  "credentials": {"bot_token": "123:abc"},
  "behavior": {"mention_required": true, "allowed_chat_ids": [12345]}
}
```

응답 (성공):
```json
HTTP 200 OK
{ "ok": true, "platform": "telegram", "configured": true }
```

응답 (검증 실패):
```json
HTTP 400 Bad Request
{ "error": "invalid_credential", "detail": "bot_token does not match pattern", "field": "bot_token" }
```

### `POST /api/messaging/{platform}/test`

요청: (body 없음)

응답 (성공):
```json
HTTP 200 OK
{
  "ok": true,
  "latency_ms": 234,
  "test_kind": "echo",       // 또는 'webhook_ping' 등
  "details": {"bot_username":"@my_bot"}
}
```

응답 (실패):
```json
HTTP 502 Bad Gateway
{ "error": "platform_unreachable", "detail": "401: Unauthorized" }
```

### `DELETE /api/messaging/{platform}`

응답:
```json
HTTP 200 OK
{ "ok": true, "purged_credential": true }
```

### Profile Archive

#### `POST /api/profiles/{name}/export`

응답:
```
HTTP 200 OK
Content-Type: application/gzip
Content-Disposition: attachment; filename="hermes-profile-default-20260526.tar.gz"
<gzip stream>
```

내용 (tar 의 file list) — **결정 2 의 ARCHIVE_EXCLUDE_PATTERNS 적용 후**:
```
MANIFEST.json                # 매니페스트 — 아래 형식
hermes/
  └── profiles/<name>/
      ├── config.yaml
      ├── memory/            # 메모리 파일
      ├── skills/            # 설치된 스킬
      ├── SOUL.md            # 페르소나 (Phase 17)
      └── (제외) secret 파일이 있다면 모두
hermes-agent-gui/
  ├── sessions.db            # 채팅 기록 (대용량 가능)
  ├── memory_vss.db          # Phase 18 RAG 벡터 인덱스 (옵션)
  └── (제외) secret / passkeys.json / .login-lock.json / *.pid / *.lock / *.log /
       session-aliases.json / *.db-shm / *.db-wal
```

`MANIFEST.json` 형식:
```json
{
  "version": "1.0",
  "exported_at": 1779700000,
  "source_host": "alice-mbp.local",
  "gui_version": "0.1.0-phase-15",
  "profile_name": "default",
  "excludes": [
    "secret", "passkeys.json", ".login-lock.json", "*.pid", "*.lock", "*.log",
    "session-aliases.json", "*.db-shm", "*.db-wal"
  ],
  "checksums": {
    "sessions.db": "sha256:abc123...",
    "config.yaml": "sha256:def456..."
  },
  "note": "Re-login required after import (device-specific secret regenerates)."
}
```

#### `POST /api/profiles/import`

요청: `multipart/form-data` 의 `file` 필드 (tar.gz).

응답 (성공):
```json
HTTP 201 Created
{
  "imported_profile": "default-imported",
  "manifest": {"version":"1","exported_at":1779700000,"source_host":"alice-mbp"},
  "warnings": ["existing profile renamed to 'default-imported'"]
}
```

응답 (실패):
```json
HTTP 400 Bad Request
{ "error": "invalid_archive", "detail": "manifest missing 'version'" }
```

#### `POST /api/profiles/{name}/clone`

요청:
```json
{ "new_name": "default-copy" }
```

응답:
```json
HTTP 201 Created
{ "name": "default-copy" }
```

## 핵심 알고리즘 — Credential 안전 저장

```python
# apps/server/api/messaging/credentials.py

import os
import tempfile
from pathlib import Path

ENV_PATH = Path.home() / ".hermes" / ".env"

def write_credential(platform: str, key: str, value: str) -> None:
    """Atomic write to ~/.hermes/.env preserving other keys.
    Format: HERMES_<PLATFORM>_<KEY>=value (newline separated).
    """
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    full_key = f"HERMES_{platform.upper()}_{key.upper()}"
    existing: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()
    existing[full_key] = value
    # Atomic via temp file + rename
    fd, tmp_path = tempfile.mkstemp(dir=str(ENV_PATH.parent), prefix=".env.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for k, v in sorted(existing.items()):
                f.write(f"{k}={v}\n")
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, ENV_PATH)
    except Exception:
        try: os.unlink(tmp_path)
        except OSError: pass
        raise
```

## 파일 구조

```
apps/server/api/messaging/
├── __init__.py
├── registry.py            # 16개 PlatformMeta 정의 (mode: 'delegated' | 'direct')
├── credentials.py         # 위 코드 — credential 안전 저장 (모드 무관 공통)
├── behavior.py            # ~/.hermes/config.yaml 채널별 동작 규칙
├── status.py              # connected? + last_event_at (sqlite cache)
├── routes.py
├── delegate_probe.py      # 위임 14개의 test_connection — Hermes 본체에 위임 호출
└── platforms/
    ├── base.py            # AbstractPlatform (validate / test_connection)
    │                      # mode 별 다른 default 구현
    │
    │   ── 위임 모드 (14) — 가벼운 wrapper. credential 형식 검증 + Hermes 본체 위임 ──
    ├── telegram.py        # bot_token 정규식 ^[0-9]+:[A-Za-z0-9_-]+$, test = delegate
    ├── discord.py         # bot_token + permission scope, test = delegate
    ├── slack.py           # xox[abprso]- 형식, test = delegate
    ├── whatsapp.py
    ├── signal.py
    ├── matrix.py
    ├── mattermost.py
    ├── email.py           # IMAP host / SMTP host / user / app password
    ├── sms.py
    ├── imessage.py
    ├── dingtalk.py
    ├── feishu.py
    ├── wecom.py
    ├── wechat.py          # QR login flow (Hermes 본체가 QR 생성, 우리는 표시만)
    │
    │   ── 직접 모드 (2) — 우리 backend 가 단독 처리 ──
    ├── webhook.py         # POST /api/messaging/webhook/{secret}/inbound
    │                      # signature 검증 + chat 모듈로 전달 + 응답 다시 outbound
    └── home_assistant.py  # Webhook 베이스 + HA REST API 호출 (notify.X service)
```

**모드 구분 — `registry.py` 의 메타에 표시**:
```python
@dataclass(frozen=True)
class PlatformMeta:
    id: PlatformId
    label: str
    mode: Literal["delegated", "direct"]    # NEW — Phase 15 결정 1
    description: str
    credential_fields: list[CredentialField]
    behavior_schema: dict
    docs_url: str
    requires_hermes_running: bool           # delegated=True, direct=False
```

**`/api/messaging/{platform}/test` 동작 분기**:
```python
async def test_connection(platform_id: str) -> TestResult:
    meta = REGISTRY[platform_id]
    impl = PLATFORMS[platform_id]
    # 1. credential 형식 검증 (모든 모드 공통)
    if not impl.validate_credentials():
        raise PlatformError("invalid_credential")
    # 2. 실연결 검증
    if meta.mode == "direct":
        return await impl.test_direct()       # 우리 backend 가 직접 호출 (webhook ping 등)
    # delegated
    if not is_hermes_running():
        return TestResult(ok=False, error="hermes_agent_not_running",
                          detail="14 위임 플랫폼은 Hermes Agent 가 실행 중이어야 검증 가능")
    return await delegate_probe.test(platform_id)   # Hermes 의 /v1/messaging/test/X 호출
```

apps/server/api/profile_archive.py
apps/web/src/
├── routes/
│   ├── messaging.tsx
│   └── profiles.tsx
└── components/messaging/
    ├── platform-card.tsx
    ├── credential-form.tsx      # 동적 필드 렌더 (CredentialField 기반)
    ├── behavior-editor.tsx      # JSON-schema-like UI
    ├── qr-code-flow.tsx         # WeChat 전용
    └── status-badge.tsx
```

## 프론트엔드

- **`routes/messaging.tsx`**:
  - 16 PlatformCard 그리드. 카드마다 connected/configured/error 상태 배지.
  - 카드 클릭 → 우측 drawer 에 CredentialForm + BehaviorEditor.
  - "Test connection" 버튼 → POST `/test` → toast 결과.
  - "Disable" 버튼 → DELETE → confirm 모달.
- **`routes/profiles.tsx`**:
  - 프로필 목록 + 활성 표시.
  - "Clone" → 새 이름 입력 → 생성.
  - "Export" → tar.gz 다운로드 (브라우저 직접 download).
  - "Import" → dropzone or file picker → progress → 결과 메시지.

## 에러 케이스 enumeration

| 시나리오 | HTTP | error code | UI 동작 |
|---------|------|-----------|---------|
| credential 형식 검증 실패 | 400 | `invalid_credential` | 필드별 에러 메시지 |
| credential 외부 검증 실패 (direct mode) | 502 | `platform_unreachable` | toast |
| **위임 모드인데 Hermes 미실행** | 503 | `hermes_agent_not_running` | toast: "Hermes Agent 가 실행 중이어야 검증 가능" |
| 테스트 메시지 timeout (10s) | 504 | `test_timeout` | toast |
| Profile 이름 충돌 (clone) | 409 | `name_taken` | "이미 존재" 모달 |
| Profile import 무결성 깨짐 (checksum mismatch) | 400 | `invalid_archive` | 모달: 매니페스트 누락 / 손상 |
| Profile import 버전 미호환 | 400 | `version_incompatible` | "이전 버전 — 마이그레이션 도구 사용" |
| Profile import 후 재로그인 안내 | (200 ok) | (없음) | 토스트: "보안상 재로그인 필요" |
| Webhook signature 검증 실패 (direct) | 401 | `webhook_signature_invalid` | (외부 호출자 응답) |
| Disk full 에서 write | 507 | `insufficient_storage` | toast + log |

## 마이그레이션 / 롤백

### Schema
신규 테이블 (sessions.db):
```sql
CREATE TABLE IF NOT EXISTS messaging_status (
  platform TEXT PRIMARY KEY,
  configured INTEGER NOT NULL DEFAULT 0,
  connected INTEGER NOT NULL DEFAULT 0,
  last_event_at INTEGER,
  last_error TEXT,
  updated_at INTEGER NOT NULL
);
```

### 기존 데이터
- `~/.hermes/.env` 가 이미 있다면 import 시 merge (사용자에게 충돌 알림).

### 롤백
- 신규 테이블이므로 phase 16 코드는 영향받지 않음.
- `~/.hermes/.env` 의 신규 키만 수동 삭제하면 원상태.

## 성능 budget + 보안 위협 모델

### Performance
| 작업 | 목표 |
|------|------|
| `GET /api/messaging/platforms` | < 50ms |
| `POST /api/messaging/{p}/test` (network 호출 포함) | < 5s |
| Profile export 100MB | < 30s |
| Profile import 100MB | < 60s |

### 보안 위협 모델
| 자산 | 위협 | 영향 | 완화 |
|-----|------|------|------|
| `~/.hermes/.env` 의 봇 토큰 | 로컬 파일 노출 | 봇 hijack | 0600 권한, atomic write, **archive 에는 포함 가능 (archive 자체 보호로 충분)** |
| **`secret` 파일 (HMAC 서명 키)** | **archive 유출 → 쿠키 위조** | **계정 탈취** | **결정 2 — archive 에서 제외 (재로그인 1회)** |
| Profile tar.gz 다운로드 링크 | 인증 우회 | 봇 토큰 노출 | 인증된 GET 전용. 토큰 redact OFF (실 봇이 사용 가능해야) |
| 외부 platform API 호출 (direct mode — webhook 만) | 응답 size 크기 attack | OOM | response_size_limit=1MB, timeout=10s |
| **Webhook inbound POST (direct mode)** | **위조 호출 → 임의 LLM 호출 + 비용 청구** | **금전 손실** | **각 webhook 마다 unique secret URL (`/api/messaging/webhook/{token}/inbound`) + HMAC signature 검증** |
| Webhook 등록 시 SSRF | 내부 네트워크 스캔 | 정보 누출 | URL 화이트리스트 + private IP 차단 |
| QR code 가짜 페이지 | 사용자 속임 | credential 도난 | QR 은 Hermes 본체에서 생성, 우리는 표시만 |
| **위임 모드의 Hermes 본체 신뢰** | **Hermes 가 credential 을 외부에 leak** | **봇 hijack** | upstream 신뢰 — Hermes 본체의 보안 정책에 의존 (우리 범위 밖) |
| Archive 무결성 | 변조된 tar.gz import 시 임의 파일 쓰기 | RCE 가능성 | MANIFEST.json 의 SHA-256 checksum 검증 + path traversal 가드 (`_safe_path` 재사용) |
| Archive 클라우드 유출 | 채팅 내용 노출 | 사생활 침해 | MANIFEST 에 `note` 명시 + 사용자에게 export 시 경고 모달 |

## 테스트

| 테스트 | 위치 | 목표 |
|--------|------|------|
| Platform metadata 16 enum + **mode 분류 (14 delegated + 2 direct)** | `tests/test_messaging_registry.py` | 라인 ≥ 90% |
| Credential atomic + 0600 | `tests/test_messaging_creds.py` | race 시나리오 포함 |
| 14 위임 플랫폼 credential 정규식 OK/NG | `tests/test_platforms_delegated.py` | 각 5 케이스 |
| Webhook signature 검증 (direct) | `tests/test_platform_webhook.py` | HMAC OK/NG + replay |
| HA notify 호출 (direct, mock REST) | `tests/test_platform_home_assistant.py` | mock fetch |
| `test_connection` 분기 — delegate vs direct | `tests/test_messaging_test_endpoint.py` | mock |
| Hermes 미실행 시 위임 plt = 503 | 같은 곳 | `hermes_agent_not_running` |
| Profile tar.gz roundtrip — bit-exact | `tests/test_profile_archive.py` | golden checksum |
| **ARCHIVE_EXCLUDE_PATTERNS 적용 검증** | 같은 곳 | secret/passkey/lock/log/.db-wal 모두 제외 확인 |
| **Import 후 secret 재생성** | 같은 곳 | 새 secret ≠ 원본 secret |
| MANIFEST checksum 검증 — 변조 거부 | 같은 곳 | SHA-256 mismatch → 400 |
| Path traversal 가드 (`../../../etc/passwd` 들어간 tar) | 같은 곳 | 거부 |
| Import name conflict | 같은 곳 | 자동 rename + warning |
| 16 플랫폼 base interface | `tests/test_platforms_base.py` | 모두 `validate/test_connection` 구현 |

## i18n 키 추가

```jsonc
// en.json
{
  "messaging.title": "Messaging Gateways",
  "messaging.platform.telegram.label": "Telegram",
  "messaging.platform.telegram.help": "Bot token + mention control",
  "messaging.status.connected": "Connected",
  "messaging.status.configured": "Configured (not connected)",
  "messaging.status.error": "Error",
  "messaging.action.test": "Test connection",
  "messaging.action.disable": "Disable",
  "messaging.error.invalid_credential": "Invalid credential format",
  "messaging.error.platform_unreachable": "Platform unreachable",
  // ... 16 platforms x 2 keys = 32 + 공통 10 = ~42 keys
  "profile.export": "Export",
  "profile.import": "Import",
  "profile.clone": "Clone",
  "profile.imported_renamed": "Existing profile renamed to '{name}'"
}
```

ko.json 동일 키 + 한국어 번역.

## PR 분할 권장

| PR | 크기 | 내용 |
|----|------|------|
| #1 | M | `messaging/registry.py` + `credentials.py` + `routes.py` (메타 GET + configure POST) + 단위 테스트 |
| #2 | M | 14 위임 `platforms/*.py` (얇은 wrapper — 정규식 + delegate_probe) — 분할 OK |
| #3 | M | 2 direct `platforms/{webhook,home_assistant}.py` — 실 inbound + signature + chat 통합 |
| #4 | M | `routes/messaging.tsx` + components (mode 별 다른 UI 분기) |
| #5 | M | `profile_archive.py` + `routes/profiles.tsx` + ARCHIVE_EXCLUDE_PATTERNS + manifest checksum |
| #6 | S | i18n + a11y + import 후 재로그인 토스트 + 마무리 |

총 6 PR (이전 5에서 +1 — direct 플랫폼이 별도로 분리되어서). 1주~10일 소요.

## 실 통합 의존

- ✅ Hermes 없이도 **2 direct 플랫폼 (Webhook + Home Assistant)** 은 완전 동작 + 테스트 가능.
- ✅ Hermes 없이도 14 delegated 플랫폼의 *credential UI + 형식 검증* 동작 + 테스트 가능.
- 🟡 14 delegated 플랫폼의 *실 ping/pong* 은 Hermes Agent 실행 환경에서만 (test endpoint = 503 `hermes_agent_not_running` 반환).
- ✅ Profile archive 전체 자체 — 재로그인 검증 단위 테스트로 충분.

---

# 🔌 Phase 16 — Multi-provider LLM + Slash Commands

**기간**: 1주 · **출처**: G + H · **의존성**: Phase 1, 2, 15(profile)

## 사용자 스토리

> 사용자 Bob 은 OpenAI 와 Anthropic 둘 다 갖고 있다. GUI 의 Providers 페이지에서 두 provider 의 API key 를 등록 → 모델 picker 가 자동으로 GPT-4 / Claude-Opus 등을 노출.
> 채팅 입력에 `/model claude-opus-4` 입력하면 즉시 모델 전환. `/usage` 입력하면 현재 세션 비용 카드.
> 로컬 Ollama 도 추가하면 동일 인터페이스로 노출.

## 데이터 모델

```python
# apps/server/api/providers/models.py

from dataclasses import dataclass, field
from typing import Literal

ProviderKind = Literal[
    "openai", "anthropic", "google", "xai", "openrouter", "nous_portal",
    "qwen", "minimax", "huggingface", "groq",
    "lm_studio", "ollama", "vllm", "llama_cpp", "custom",
]

@dataclass
class Provider:
    id: str                      # uuid hex 12
    kind: ProviderKind
    label: str
    base_url: str
    api_key_env: str             # ~/.hermes/.env 키 이름
    auth_type: Literal["bearer", "oauth", "none"]
    enabled: bool = True
    extra: dict = field(default_factory=dict)  # provider-specific (region 등)

@dataclass
class ModelInfo:
    id: str
    provider_id: str
    context_window: int
    pricing_in_per_1m_usd: float
    pricing_out_per_1m_usd: float
    capabilities: list[Literal["chat", "embed", "vision", "tools"]]
```

## API 스키마

### `GET /api/providers`
```json
{
  "providers": [
    {
      "id": "abc123",
      "kind": "openai",
      "label": "OpenAI Production",
      "base_url": "https://api.openai.com/v1",
      "enabled": true,
      "test_status": "ok",
      "last_tested_at": 1779789999
    }
  ]
}
```

### `POST /api/providers`
요청:
```json
{
  "kind": "openai",
  "label": "OpenAI Production",
  "base_url": "https://api.openai.com/v1",   // 옵션 (preset 의 default)
  "api_key": "sk-..."                        // .env 에 저장됨
}
```
응답: `201 { "id": "abc123", ... }` 또는 `400 { "error": "invalid_api_key" }`.

### `GET /api/providers/{id}/models`
캐시 (5분 TTL):
```json
{
  "provider_id": "abc123",
  "models": [
    {"id":"gpt-4o","context_window":128000,"pricing_in_per_1m_usd":2.5,
     "pricing_out_per_1m_usd":10.0,"capabilities":["chat","vision","tools"]}
  ],
  "fetched_at": 1779789999
}
```

### `POST /api/providers/{id}/test`
1-token chat 으로 ping:
```json
HTTP 200 OK
{ "ok": true, "latency_ms": 412, "model_used": "gpt-4o-mini" }
```

### OAuth (Nous Portal / OpenAI Codex)
- `GET /api/providers/oauth/{provider}/start` → Phase 1 의 OAuth 흐름과 동일 패턴. state TTL 10분, PKCE S256.

## 22개 Slash Commands

```typescript
// apps/web/src/lib/slash-commands.ts

export interface SlashCommand {
  name: string;
  args?: string;
  description: string;
  exec: (args: string, ctx: SlashCtx) => Promise<SlashResult>;
}

interface SlashCtx {
  sessionId: string | undefined;
  setSession: (id: string) => void;
  navigate: (path: string) => void;
  qc: QueryClient;
}

type SlashResult =
  | { kind: 'intercept' }                       // 메시지 안 보냄
  | { kind: 'replace', text: string }           // 입력을 텍스트로 교체
  | { kind: 'system', text: string };           // 시스템 메시지로 표시

export const COMMANDS: SlashCommand[] = [
  // 세션
  { name: 'new', description: 'Start a new session', exec: async (_, ctx) => {
      const s = await Sessions.create('New chat');
      ctx.setSession(s.id);
      return { kind: 'intercept' };
  }},
  { name: 'clear', description: 'Clear current session', /* ... */ },
  { name: 'compact', description: 'Trigger context compression', /* Phase 18 */ },
  { name: 'compress', description: 'Alias for /compact', /* ... */ },
  { name: 'undo', description: 'Remove last assistant turn', /* ... */ },
  { name: 'retry', description: 'Re-generate last assistant turn', /* ... */ },
  // 메타
  { name: 'help', description: 'List all commands', /* ... */ },
  { name: 'version', description: 'Show version', /* ... */ },
  { name: 'status', description: 'Show health summary', /* ... */ },
  { name: 'debug', description: 'Toggle debug overlay', /* ... */ },
  // 도구
  { name: 'tools', description: 'Open tools page', /* ... */ },
  { name: 'skills', description: 'Open skills page', /* ... */ },
  { name: 'model', args: '<model_id>', description: 'Switch model', /* ... */ },
  { name: 'memory', description: 'Open memory page', /* ... */ },
  { name: 'persona', description: 'Open persona editor (Phase 17)', /* ... */ },
  // 운영
  { name: 'usage', description: 'Show usage card', /* Phase 17 */ },
  { name: 'fast', description: 'Switch to faster model', /* ... */ },
  // 외부 도구 (Hermes Agent 가 호출)
  { name: 'web', args: '<query>', description: 'Web search', /* tool call */ },
  { name: 'image', args: '<prompt>', description: 'Image generation', /* tool call */ },
  { name: 'browse', args: '<url>', description: 'Browse URL (Phase 23)', /* ... */ },
  { name: 'code', args: '<task>', description: 'Code generation', /* ... */ },
  { name: 'shell', args: '<cmd>', description: 'Shell exec (Phase 3 allowlist)', /* ... */ },
];
```

## 핵심 알고리즘 — Provider 자동 검증

```python
# apps/server/api/providers/discovery.py

def discover_models(provider: Provider, api_key: str) -> list[ModelInfo]:
    """Fetch /v1/models with provider-specific quirks.

    Provider quirks:
    - Anthropic: no /v1/models; use static known list
    - Google: /v1beta/models endpoint; different schema
    - Ollama: /api/tags
    - Local OpenAI-compat (LM Studio/vLLM): standard /v1/models
    """
    if provider.kind == "anthropic":
        return _ANTHROPIC_KNOWN_MODELS
    if provider.kind == "google":
        return _fetch_google_models(provider, api_key)
    if provider.kind == "ollama":
        return _fetch_ollama_tags(provider)
    # OpenAI compatible default
    return _fetch_openai_compat(provider, api_key)

def _fetch_openai_compat(provider: Provider, api_key: str) -> list[ModelInfo]:
    url = f"{provider.base_url.rstrip('/')}/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    return [
        ModelInfo(id=m["id"], provider_id=provider.id, context_window=m.get("context_length", 8000),
                  pricing_in_per_1m_usd=0.0, pricing_out_per_1m_usd=0.0,
                  capabilities=["chat"])
        for m in data.get("data", [])
    ]
```

## 파일 구조

```
apps/server/api/providers/
├── __init__.py
├── models.py
├── catalog.py             # 14 preset 메타
├── store.py               # SQLite CRUD
├── discovery.py
├── oauth/
│   ├── nous_portal.py
│   └── openai_codex.py
└── routes.py

apps/server/api/slash_commands.py    # 서버측 처리 (compact/usage 등)

apps/web/src/
├── routes/providers.tsx
├── routes/chat.tsx (확장)
├── components/chat/
│   ├── slash-menu.tsx
│   ├── slash-handler.ts
│   └── model-picker.tsx
└── lib/slash-commands.ts
```

## 에러 케이스 enumeration

| 시나리오 | HTTP | error code |
|---------|------|-----------|
| API key 형식 잘못됨 | 400 | `invalid_api_key_format` |
| Test call 401 | 502 | `provider_auth_failed` |
| Test call 5xx | 502 | `provider_server_error` |
| Model 카탈로그 fetch 실패 → 빈 리스트 반환 | 200 | (no error, models=[]) |
| OAuth state expired | 400 | `oauth_state_expired` |
| 같은 label 의 provider 중복 | 409 | `provider_label_taken` |
| Slash 명령 인자 누락 (`/model` 단독) | UI | inline help |

## 마이그레이션 / 롤백
- 신규 테이블 `providers`. 기존 영향 없음.
- API key 는 `~/.hermes/.env` 에 저장 → Phase 15 의 atomic write 재사용.

## 성능 budget + 보안

| 작업 | 목표 |
|------|------|
| `GET /api/providers` | < 30ms |
| `GET /api/providers/{id}/models` (cache hit) | < 10ms |
| `GET /api/providers/{id}/models` (cache miss) | < 5s |
| Slash menu open | < 50ms (메모리 lookup) |

### 보안 위협 모델
| 자산 | 위협 | 영향 | 완화 |
|-----|------|------|------|
| OpenAI sk- 키 | log 노출 | 비용 청구 | Phase 7 의 11 패턴이 자동 redact |
| OAuth state | CSRF | 계정 hijack | PKCE S256 + 1회용 state + 10분 TTL |
| `/api/providers/{id}/test` SSRF | base_url=`http://internal` | 내부 스캔 | private IP 차단 + protocol https/http 만 |
| Slash command `/shell` | RCE | 전체 머신 | Phase 3 allowlist 통과 강제 |

## 테스트

| 테스트 | 목표 |
|--------|------|
| 14 preset metadata enum | line ≥ 90% |
| `/v1/models` cache 5분 만료 | timing 테스트 |
| OAuth PKCE state 정확성 | 단위 |
| Slash command 파싱 (`/model gpt-4 --temp 0.7`) | vitest |
| `/clear` 활성 세션만 영향 | vitest |
| Discovery quirk per provider (mock fetch) | 14개 |

## i18n 키 추가
`providers.title`, `providers.add`, `providers.test_ok/fail`, `chat.slash.<name>.description` × 22.

## PR 분할 권장
| PR | 크기 | 내용 |
|----|------|------|
| #1 | M | providers schema + CRUD + tests |
| #2 | M | discovery + 14 preset + OAuth (Nous Portal/Codex) |
| #3 | M | `routes/providers.tsx` + ModelPicker |
| #4 | S | slash-commands.ts + slash-menu.tsx |
| #5 | S | i18n + 마무리 |

## 실 통합 의존
- ✅ Hermes 없이 빌드/단위 테스트 가능. discovery 는 mock fetch.
- 🟡 실제 OpenAI/Anthropic key 로 검증은 사용자 환경.

---

# 🎭 Phase 17 — Persona SOUL + FTS5 + Usage

**기간**: 1주 · **출처**: G hermes-desktop · **의존성**: Phase 2, 16

## 사용자 스토리

> 사용자 Carol 은 자신의 에이전트에게 "냉정한 코드 리뷰어" 페르소나를 주고 싶다. Persona 페이지에서 6 preset 중 'Reviewer' 를 선택 → SOUL.md 가 자동 채워짐. Monaco 에디터로 미세 조정 → Apply.
> Carol 이 "3주 전에 우리가 결정한 redis 캐싱 정책" 을 찾으려 Cmd+K → "redis caching" 입력 → 그 메시지로 점프.
> 월말에 Usage 페이지에서 자신이 OpenAI 에 $42, Anthropic 에 $18 을 썼다는 카드 + 일별 추세 차트 확인.

## 데이터 모델

```python
@dataclass
class Persona:
    profile_name: str
    soul_md: str
    updated_at: int

@dataclass
class UsageTurn:
    id: str          # uuid12
    session_id: str
    profile: str
    provider_id: str
    model_id: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cache_hit: bool
    created_at: int
```

## API 스키마

### `GET /api/persona`
응답:
```json
{ "profile_name": "default", "soul_md": "# Hermes Agent\n...", "updated_at": 1779789999 }
```

### `PUT /api/persona`
```json
{ "soul_md": "# New persona\n..." }
```
응답: `200 { "ok": true }`.

### `GET /api/persona/presets`
```json
{
  "presets": [
    {"id":"sage","label":"Sage — thoughtful researcher","soul_md":"..."},
    {"id":"trader","label":"Trader — quantitative & blunt","soul_md":"..."},
    {"id":"builder","label":"Builder — pragmatic coder","soul_md":"..."},
    {"id":"scribe","label":"Scribe — writer & editor","soul_md":"..."},
    {"id":"ops","label":"Ops — operational rigor","soul_md":"..."},
    {"id":"coder","label":"Coder — cold code reviewer","soul_md":"..."}
  ]
}
```

### `GET /api/sessions/search?q=...&limit=50`
응답:
```json
{
  "query": "redis caching",
  "results": [
    {
      "session_id": "abc",
      "session_title": "Phase 18 design",
      "message_index": 42,
      "role": "user",
      "snippet": "...we should use <em>redis</em> for hot session <em>caching</em>...",
      "ts": 1779700000,
      "score": 0.91
    }
  ],
  "total": 7
}
```

### `GET /api/usage/summary?from=2026-04-26&to=2026-05-26`
```json
{
  "total_input_tokens": 1234567,
  "total_output_tokens": 234567,
  "total_cost_usd": 42.18,
  "sessions": 87,
  "avg_per_day": 2.9,
  "cache_hit_rate": 0.31,
  "by_model": [
    {"model_id":"gpt-4o","cost_usd":29.0,"tokens":900000},
    {"model_id":"claude-opus","cost_usd":13.18,"tokens":340000}
  ],
  "daily": [
    {"date":"2026-04-26","cost_usd":1.2,"tokens":42000},
    /* ... 30 entries ... */
  ]
}
```

## FTS5 마이그레이션

```sql
-- Phase 2 의 sessions.db 에 추가
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
  session_id UNINDEXED,
  message_index UNINDEXED,
  role UNINDEXED,
  ts UNINDEXED,
  content,
  tokenize = 'porter unicode61 remove_diacritics 2'
);

-- Trigger: sessions.messages_json 의 변경을 fts 로 sync
-- (단순 비교: BEFORE/AFTER 의 messages_json 차이 → 미사용)
-- 대안: 명시적 sync 함수
```

```python
# apps/server/api/sessions/search.py

def _index_messages(conn, session_id: str, messages: list[Message], start_index: int = 0) -> None:
    """Insert messages into FTS5 starting at message_index = start_index."""
    rows = [
        (session_id, start_index + i, m.role, m.created_at, m.content)
        for i, m in enumerate(messages)
    ]
    conn.executemany(
        "INSERT INTO messages_fts(session_id, message_index, role, ts, content) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )

# Phase 2 의 SessionStore.append_messages 의 끝에 hook:
def append_messages(self, sess_id, new_messages):
    # ... 기존 코드 ...
    _index_messages(conn, sess_id, list(new_messages), start_index=len(existing) - len(new_messages))
```

### Backfill (기존 세션)
부팅 시 한 번:
```python
def backfill_fts(store: SessionStore) -> None:
    """기존 세션을 FTS5 에 일괄 인덱싱. idempotent — INSERT OR IGNORE."""
    for sess in store.list(all_profiles=True):
        for i, m in enumerate(sess.messages):
            conn.execute(
                "INSERT OR IGNORE INTO messages_fts(session_id, message_index, role, ts, content) "
                "VALUES (?, ?, ?, ?, ?)",
                (sess.id, i, m.role, m.created_at, m.content),
            )
```

## 핵심 알고리즘 — Usage Cost 계산

```python
def calc_cost(usage_turn: UsageTurn, model_info: ModelInfo) -> float:
    """Per-turn cost in USD, applying cache discount."""
    in_cost = (usage_turn.input_tokens / 1_000_000) * model_info.pricing_in_per_1m_usd
    out_cost = (usage_turn.output_tokens / 1_000_000) * model_info.pricing_out_per_1m_usd
    if usage_turn.cache_hit:
        in_cost *= 0.5   # 대부분 provider 가 cache 절반 가격
    return round(in_cost + out_cost, 6)
```

## 파일 구조

```
apps/server/api/
├── persona.py
├── sessions/search.py
├── usage.py (Phase 14 확장)
└── presets/
    └── personas.py        # 6 preset SOUL.md 텍스트

apps/web/src/
├── routes/persona.tsx
├── routes/usage.tsx
├── components/global-search.tsx     # Cmd+K 모달
└── lib/usage-pricing.ts             # 모델별 단가 (provider catalog 와 동기화)
```

## 에러 케이스

| 시나리오 | HTTP | error code |
|---------|------|-----------|
| SOUL.md 너무 큼 (>100KB) | 413 | `payload_too_large` |
| Persona save 중 file lock | 409 | `concurrent_write` (재시도) |
| FTS5 query 잘못된 syntax | 200 | (자동 escape) |
| Usage from > to | 400 | `invalid_date_range` |

## 성능 + 보안

| 작업 | 목표 |
|------|------|
| FTS5 검색 (1M messages) | < 100ms |
| Usage summary (30일, 1000 turns) | < 200ms |
| FTS5 backfill (10K messages) | < 5s |

### 위협 모델
| 자산 | 위협 | 완화 |
|-----|------|------|
| FTS5 검색 결과 redact | 토큰/PII 노출 | snippet 도 Phase 7 redact 적용 |
| SOUL.md 사용자 입력 | injection | 마크다운 sanitize (Phase 1 의 rehype-sanitize) |

## 테스트

| 테스트 | 목표 |
|--------|------|
| FTS5 검색 정확도 (golden 50건) | 라인 ≥ 80% |
| FTS5 incremental indexing | append 후 즉시 검색 |
| FTS5 backfill idempotent | 두 번 실행 = 같은 결과 |
| 6 preset SOUL.md 파싱 가능 | 각 preset valid markdown |
| Usage cost 0 division | model 단가 0 일 때 0 반환 |
| 30-day daily rollup | 빈 날에 0 채움 |

## i18n 키
`persona.title`, `persona.preset.<id>`, `persona.action.apply`, `persona.action.reset`, `search.placeholder`, `search.no_results`, `usage.title`, `usage.metric.<name>`, ...

## PR 분할
| PR | 크기 | 내용 |
|----|------|------|
| #1 | S | persona.py + 6 preset + persona.tsx |
| #2 | M | FTS5 schema + search.py + backfill + tests |
| #3 | M | global-search.tsx + Cmd+K hotkey |
| #4 | M | usage rollup + summary endpoint |
| #5 | M | usage.tsx + recharts 차트 |

## 실 통합 의존
- ✅ 전부 자체 SQLite + 정적 preset.
- 🟡 Usage 단가는 provider catalog 와 sync — 정확도는 사용자 검증.

---

# 🧠 Phase 18 — Auto-Compress + RAG

**기간**: 2주 · **출처**: A claude-mem · **의존성**: Phase 2, 16

## 사용자 스토리

> Dan 은 한 세션에서 50 turn 째 대화 중. 모델의 context window 가 거의 찼다는 경고 배지가 나타남.
> 자동으로 1~30 turn 이 "초기 설정 + 데이터 모델 결정" 한 단락으로 압축되고, 31~40 turn 이 "Phase 5 의 칸반 구현" 다른 단락으로 압축됨.
> Dan 이 새 질문 "초기 데이터 모델은 뭐였지?" 입력 → 자동으로 vector 검색이 "초기 설정..." 요약을 retrieval → system prompt 에 인젝션 → 정확한 답.

## 데이터 모델

```python
@dataclass
class MemoryChunk:
    id: str
    session_id: str
    range_start: int             # message_index
    range_end: int
    summary: str
    embedding: bytes             # float32 array (dim 1536 등)
    embedding_model: str
    created_at: int
```

## API 스키마

### `POST /api/sessions/{sid}/compact`
```json
{ "trigger": "manual" }   // or "auto"
```
응답:
```json
HTTP 200 OK
{
  "compacted_chunks": [
    {"id":"abc","range_start":0,"range_end":30,"summary":"User defined data model..."}
  ],
  "tokens_saved": 12000
}
```

### `GET /api/sessions/{sid}/memory`
세션에 대한 memory chunks 목록.

### `POST /api/memory/search`
```json
{ "q": "초기 데이터 모델", "k": 5, "session_id_filter": null }
```
응답:
```json
{
  "results": [
    {"chunk_id":"abc","session_id":"xyz","summary":"...","score":0.87}
  ]
}
```

## 핵심 알고리즘 — Compression Trigger

```python
# apps/server/api/compression/trigger.py

COMPACT_TURN_THRESHOLD = 40
COMPACT_TOKEN_THRESHOLD = 8000   # 임시 — provider 별 context_window 의 75% 로 자동 조정
COMPACT_KEEP_TAIL = 10           # 마지막 N turn 은 압축 안 함

def should_compact(session: Session, current_tokens: int, model: ModelInfo) -> bool:
    if len(session.messages) < COMPACT_TURN_THRESHOLD:
        return False
    if current_tokens < model.context_window * 0.75:
        return False
    # 압축할 게 충분한가?
    compactable = len(session.messages) - COMPACT_KEEP_TAIL
    if compactable < 20:
        return False
    return True
```

```python
# apps/server/api/compression/summarizer.py

SUMMARIZE_PROMPT = """Summarize the following conversation turns into a single
paragraph (max 300 words). Preserve all decisions, data models, and code names.
Drop pleasantries and filler.

Turns:
{turns}
"""

async def summarize(adapter: Adapter, turns: list[Message]) -> str:
    body = SUMMARIZE_PROMPT.format(turns=_format(turns))
    chunks = []
    for event, data in adapter.stream(ChatTurn(messages=[{"role":"user","content":body}])):
        if event == "token": chunks.append(data["text"])
        if event == "done": break
        if event == "error": raise RuntimeError(data.get("detail"))
    return "".join(chunks).strip()
```

```python
# apps/server/api/compression/inject.py

def maybe_inject(session: Session, new_user_msg: str, k: int = 3) -> list[Message]:
    """If past memory chunks are highly relevant to new_user_msg, inject them as system messages."""
    if not new_user_msg.strip():
        return []
    embedding = embed(new_user_msg)
    chunks = vss_search(embedding, k=k, session_filter=session.id)
    if not chunks:
        return []
    return [
        Message(role="system",
                content=f"[Past memory from this session]\n{c.summary}",
                tool_calls=[])
        for c in chunks
    ]
```

## 의존성 결정 (사용자 컨펌 필요)

옵션 A: **sqlite-vss** (추천)
- 단일파일, 외부 서버 불필요
- Python wheel 있음 (macOS arm64 / linux x86 / windows)
- 인덱스 = SQLite 가상 테이블

옵션 B: **chromadb**
- 더 성숙한 RAG 인프라
- 외부 server 필요 (또는 in-process 모드)
- 의존성 큼 (numpy, hnswlib)

**추천**: A — 우리 단일파일 빌드 모드 (Phase 11) 와 정합.

## 파일 구조

```
apps/server/api/compression/
├── __init__.py
├── trigger.py
├── summarizer.py
├── embedder.py            # provider /v1/embeddings 또는 로컬 (sentence-transformers)
├── vss_store.py           # sqlite-vss wrapper
├── inject.py
└── routes.py
```

## 에러 케이스

| 시나리오 | HTTP | error code |
|---------|------|-----------|
| Compression LLM 호출 실패 | 502 | `summarize_failed` (재시도 1회) |
| Embedding LLM 호출 실패 | 200 | (chunk 저장 but score=0) |
| sqlite-vss 미설치 | 500 | `vss_not_installed` (UI 에서 가이드) |
| 빈 turns 압축 | 400 | `nothing_to_compact` |

## 마이그레이션
- 새 테이블 `memory_chunks`. 기존 sessions 영향 없음.
- sqlite-vss 의 virtual table 은 별도 sidecar DB (`~/.hermes-agent-gui/memory_vss.db`).

## 성능 + 보안
- 압축 1회 비용: $0.01~0.05 (gpt-4o-mini 기준). 사용자 미리 경고.
- Embedding 캐시: 같은 텍스트 hash → 같은 벡터 (재호출 안 함).
- 위협: 압축된 요약에 secret 포함 → Phase 7 의 redact 를 summarizer output 에 적용.

## 테스트
- Trigger 임계값 (40 turns / 75% window)
- Summary 가 모든 decisions 보존 (golden 10건)
- Inject 가 visible transcript 비변경 (C 정책)
- 압축 후 alias 등록되어 old session_id 도 resolve

## PR 분할
| PR | 내용 |
|----|------|
| #1 | vss_store + embedder + 단위 테스트 |
| #2 | trigger + summarizer + inject |
| #3 | routes + chat 통합 |
| #4 | UI (Compress now 버튼 + memory 사이드패널) |
| #5 | 알림 + 마무리 |

## 실 통합 의존
- 🟡 LLM 호출이 필수 (mock 으로 단위 테스트 가능, 실 압축 품질은 사용자 검증).

---

# 🔐 Phase 19 — Memory Plugins + PII Redaction

**기간**: 1주 · **출처**: G + H · **의존성**: Phase 18

## 사용자 스토리

> Erin 은 자신의 회사가 사용하는 Mem0 클라우드 서비스를 연결하고 싶다.
> Settings → Memory → Provider dropdown 에서 'Mem0' 선택 → API key 입력 → 활성. 이전 SQLite-VSS 데이터는 export → Mem0 으로 import (옵션).
> Erin 이 채팅에 자신의 카드번호를 실수로 입력 → 자동으로 `****-****-****-1234` 로 redact + UI 에 "PII 제거됨" 배지.

## 데이터 모델

```python
class MemoryProvider(ABC):
    @abstractmethod
    def write(self, session_id: str, summary: str, embedding: list[float]) -> str: ...
    @abstractmethod
    def query(self, embedding: list[float], k: int) -> list[MemoryChunk]: ...
    @abstractmethod
    def purge(self, before: int | None = None) -> int: ...
    @abstractmethod
    def test_connection(self) -> bool: ...
```

## API 스키마

### `GET /api/memory/providers`
```json
{
  "active": "local_vss",
  "available": [
    {"id":"local_vss","label":"Local (SQLite-VSS)","configured":true,"requires":[]},
    {"id":"mem0","label":"Mem0 Cloud","configured":false,"requires":["api_key"]},
    {"id":"honcho","label":"Honcho","configured":false,"requires":["api_url","api_key"]},
    {"id":"hindsight","label":"Hindsight","configured":false,"requires":["api_key"]},
    {"id":"retaindb","label":"RetainDB","configured":false,"requires":["api_key","collection"]},
    {"id":"supermemory","label":"Supermemory","configured":false,"requires":["api_key"]},
    {"id":"byterover","label":"ByteRover","configured":false,"requires":["api_key"]}
  ]
}
```

### `POST /api/memory/providers/{name}/activate`
```json
{ "config": {"api_key": "...", "api_url": "..."} }
```

### `POST /api/pii/scan`
```json
{ "text": "My SSN is 123-45-6789 and my card 4111-1111-1111-1234." }
```
응답:
```json
{
  "found": [
    {"kind":"ssn","start":10,"end":21,"redacted":"***-**-****"},
    {"kind":"credit_card","start":34,"end":53,"redacted":"****-****-****-1234"}
  ],
  "redacted": "My SSN is ***-**-**** and my card ****-****-****-1234."
}
```

### `POST /api/pii/config`
```json
{ "enabled": true, "patterns": [{"name":"custom_employee_id","regex":"EMP-\\d{6}"}] }
```

## PII 패턴 (확장 가능)

```python
# apps/server/api/pii.py

DEFAULT_PATTERNS = [
    ("ssn",          r"\b\d{3}-\d{2}-\d{4}\b",                          "***-**-****"),
    ("credit_card",  r"\b(?:\d[ -]?){13,19}\b",                         _mask_cc),
    ("email",        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", _mask_email),
    ("phone_kr",     r"\b01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}\b",       "***-****-****"),
    ("phone_us",     r"\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "***-***-****"),
    ("kr_rrn",       r"\b\d{6}[-.\s]?[1-4]\d{6}\b",                     "******-*******"),  # 한국 주민번호
    ("iban",         r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b",                "****-****"),
    ("ip_v4",        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",                    "***.***.***.***"),
]

def _mask_cc(m: re.Match) -> str:
    digits = re.sub(r"\D", "", m.group())
    if len(digits) < 13: return m.group()
    return "****-****-****-" + digits[-4:]

def _mask_email(m: re.Match) -> str:
    local, _, domain = m.group().partition("@")
    return f"{local[0]}***@{domain}"
```

## 핵심 통합 — Chat 진입부 hook

```python
# apps/server/api/chat.py 의 _stream 진입부에 추가
if pii_module.is_enabled():
    new_messages_safe = [pii_module.redact_message(m) for m in messages_raw]
    if any(orig != safe for orig, safe in zip(messages_raw, new_messages_safe)):
        # client 에게 redaction event 보냄
        streaming.write_event(req.raw, "pii_redacted",
                              {"original_count": len(messages_raw)})
    turn = ChatTurn(messages=new_messages_safe, session_id=resolved_sid)
```

## 파일 구조

```
apps/server/api/
├── pii.py
└── memory_providers/
    ├── base.py
    ├── local_vss.py
    ├── mem0.py
    ├── honcho.py
    ├── hindsight.py
    ├── retaindb.py
    ├── supermemory.py
    ├── byterover.py
    └── registry.py

apps/web/src/
├── routes/settings.tsx (확장)         # Privacy + Memory Provider 섹션
└── components/chat/
    └── pii-redacted-badge.tsx
```

## 에러 케이스
| 시나리오 | HTTP | error |
|---------|------|-------|
| Provider activation key 누락 | 400 | `provider_config_missing` |
| Provider test 실패 | 502 | `provider_unreachable` |
| 잘못된 정규식 (custom pattern) | 400 | `invalid_regex` |

## 성능 + 보안

- PII 스캔: 1KB 텍스트 < 5ms (패턴 8개)
- Memory provider migration (Local → Cloud): export → 10K chunks < 30s

### 위협 모델
| 자산 | 위협 | 완화 |
|-----|------|------|
| PII 패턴 자체 | 우회 (encoded) | base64/unicode normalize 후 재스캔 |
| Custom regex injection | ReDoS | `re.compile(..., flags=...)` + timeout (`signal.alarm`) |
| 외부 memory provider | 데이터 누출 | provider 별 retention policy + UI 경고 |

## 테스트
- 8 기본 패턴 OK/NG 각 5건
- 한국 주민번호 (변형: 점/공백 포함)
- 6 provider base interface 일관성
- Custom regex ReDoS 차단

## PR 분할
| PR | 내용 |
|----|------|
| #1 | pii.py + 패턴 + 테스트 |
| #2 | chat hook + redacted-badge.tsx |
| #3 | memory_providers base + local_vss + Mem0 |
| #4 | 5 plugin 추가 (분할 OK) |
| #5 | Settings UI |

## 실 통합 의존
- ✅ PII 자체.
- 🟡 Memory provider 6종은 각 외부 서비스 가입.

---

# 👥 Phase 20 — Group Chat + Auto-Updater + Backup

**기간**: 1주 · **출처**: H + G · **의존성**: Phase 2, 12, 16

## 사용자 스토리

> Fred 는 다음 주 제품 결정을 위해 'Researcher', 'Builder', 'Reviewer' 3개 페르소나를 같이 굴리고 싶다.
> Groups 페이지에서 "New room" → 3개 페르소나 선택 → 초대 코드 생성.
> 채팅에 `@Researcher Phase 18 RAG 시장 조사` 입력 → Researcher 만 응답. 답을 본 후 `@Reviewer 위 답변 비판해줘` → Reviewer 만 응답.

> Fred 의 데스크탑 GUI 가 새 버전 사용 가능 토스트 표시 → 클릭 → 재시작 + 자동 업데이트.
> Fred 가 매주 Settings → Backup → tar.gz 다운로드.

## 데이터 모델

```python
@dataclass
class GroupParticipant:
    profile_id: str
    persona_id: str             # SOUL preset id
    model_id: str               # provider 등록된 model
    label: str                  # @-mention 시 사용 (e.g. 'Researcher')
    color: str                  # UI bubble 색

@dataclass
class Group:
    id: str
    title: str
    invite_code: str
    participants: list[GroupParticipant]
    owner_user: str
    created_at: int
```

## API 스키마

### `POST /api/groups`
```json
{
  "title": "Phase 18 design review",
  "participants": [
    {"persona_id":"researcher","model_id":"gpt-4o","label":"Researcher","color":"#0ea5e9"},
    {"persona_id":"builder","model_id":"claude-opus","label":"Builder","color":"#10b981"},
    {"persona_id":"reviewer","model_id":"gpt-4o","label":"Reviewer","color":"#f59e0b"}
  ]
}
```
응답: `201 { "id":"...", "invite_code":"ABC123DE", ...}`.

### `POST /api/groups/{gid}/messages`
요청:
```json
{ "content": "@Researcher do market research on RAG providers." }
```
응답: `202 Accepted` (SSE 로 응답).

### `GET /api/groups/{gid}/stream` (SSE)
```
event: ready
data: {"group_id":"..."}

event: turn_start
data: {"participant":"Researcher"}

event: token
data: {"participant":"Researcher","text":"Looking at Mem0..."}

event: turn_done
data: {"participant":"Researcher","turn_id":"..."}
```

## 핵심 알고리즘 — Mention Routing

```python
import re

MENTION_RE = re.compile(r"@([A-Za-z][A-Za-z0-9_-]{0,31})\b")

def route_message(group: Group, content: str) -> list[GroupParticipant]:
    """Return participants who should respond. @-mention takes priority."""
    mentions = {m.lower() for m in MENTION_RE.findall(content)}
    if not mentions:
        # 기본: 첫 번째 참가자 또는 round-robin (옵션)
        return [group.participants[0]] if group.participants else []
    matched = [p for p in group.participants if p.label.lower() in mentions]
    return matched or [group.participants[0]]
```

## Auto-Updater 와이어링

```js
// electron/main.cjs (추가)
const { autoUpdater } = require('electron-updater');
autoUpdater.autoDownload = false;
autoUpdater.checkForUpdates();
autoUpdater.on('update-available', (info) => {
  mainWindow.webContents.send('updater:available', { version: info.version });
});
autoUpdater.on('update-downloaded', () => {
  mainWindow.webContents.send('updater:ready');
});

ipcMain.handle('updater:download', () => autoUpdater.downloadUpdate());
ipcMain.handle('updater:install', () => autoUpdater.quitAndInstall());
```

배포 채널:
- **추천**: GitHub Releases. `electron-builder` 가 `latest-mac.yml`/`latest.yml` 자동 생성.
- 다른 채널 (S3 + 사설 서명): builder config 의 `publish` 섹션 추가.

## Backup / Debug Dump

```python
# apps/server/api/backup.py

BACKUP_INCLUDE = [
    Path.home() / ".hermes-agent-gui",        # sessions, passkeys, etc.
    Path.home() / ".hermes" / "skills",
    Path.home() / ".hermes" / "memory",
    Path.home() / ".hermes" / "profiles",
]
BACKUP_EXCLUDE_PATTERNS = ["secret", "*.pid", "*.lock", "*.log"]

def export_backup() -> bytes:
    """Return tar.gz bytes."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        manifest = {"version": __version__, "exported_at": int(time.time()),
                    "source_host": socket.gethostname()}
        info = tarfile.TarInfo("MANIFEST.json")
        data = json.dumps(manifest).encode()
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
        for path in BACKUP_INCLUDE:
            if path.exists():
                tar.add(path, arcname=path.name, filter=_skip_excluded)
    return buf.getvalue()

def _skip_excluded(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
    if any(fnmatch.fnmatch(info.name, p) for p in BACKUP_EXCLUDE_PATTERNS):
        return None
    return info
```

## 파일 구조

```
apps/server/api/
├── groups/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   └── routing.py            # mention 라우팅
├── backup.py
└── debug_dump.py

electron/
├── main.cjs (확장 — autoUpdater)
└── preload.cjs (확장 — updater bridge)

apps/web/src/
├── routes/groups.tsx
├── routes/groups.$gid.tsx
├── routes/settings.tsx (확장 — backup section)
└── components/
    ├── updater-toast.tsx
    └── group-bubble.tsx
```

## 에러 케이스
| 시나리오 | HTTP | error |
|---------|------|-------|
| 동시 mention 라우팅 충돌 | (해결) | 각 participant SSE 독립 stream |
| 초대 코드 만료 | 400 | `invite_expired` |
| Group 참가자 수 한도 초과 (예: 10) | 400 | `too_many_participants` |
| Backup 파일 크기 초과 (>500MB) | 413 | `backup_too_large` |
| Auto-update 채널 도달 불가 | (UI 알림) | 토스트로 silent fail |

## 마이그레이션
- 새 테이블 `groups`, `group_participants`. 기존 sessions 영향 없음.

## 성능 + 보안

- Group 메시지 발송 → 첫 token until: < 3s (provider 와이어링)
- Backup 100MB tar.gz: < 20s
- Auto-update download: 사용자 네트워크 의존

### 위협 모델
| 자산 | 위협 | 완화 |
|-----|------|------|
| Invite code | 추측 (brute force) | 8자 base32 → 32^8 = 1조 + rate-limit |
| Auto-update payload | MITM / 위조 | electron-builder 의 signed 자동 검증 + HTTPS |
| Backup 파일 | 사용자가 공유 | 매니페스트에 host 명시 + import 시 경고 |

## 테스트
- Mention routing (5 케이스: 무명, 단일, 다중, 잘못된, mention 만)
- Auto-update event handler (electron mock)
- Backup tar.gz roundtrip
- BACKUP_EXCLUDE_PATTERNS 가 모두 제외되는지

## PR 분할
| PR | 내용 |
|----|------|
| #1 | Group schema + routing.py + tests |
| #2 | SSE multi-stream + routes |
| #3 | groups.tsx UI |
| #4 | autoUpdater 와이어링 + toast UI |
| #5 | backup.py + debug_dump + Settings UI |

## 실 통합 의존
- ✅ Group + Backup 은 자체.
- 🟡 Auto-update 는 실제 release 채널 (GitHub) 등록 + signed Electron 빌드 필요 (P2 결정 사항).

---

# 🕸️ Phase 21 — Knowledge Graph (GBrain)

**기간**: 2주 · **출처**: F garrytan/gbrain · **의존성**: Phase 17, 18

## 사용자 스토리

> Grace 는 매일 미팅 노트, 이메일, 트윗을 채팅에 던진다. 6개월 후 "Alice 와 만나기 전에 알아야 할 것 요약" 입력.
> GBrain 이 alice 노드를 찾고 → 연결된 attended/works_at edge 를 traverse → 관련 페이지 (회사 소개, 이전 미팅) 가져옴 → 합성 답변 카드 (3 단락 + 5 인용 + "최근 프로젝트 진척은 모름" gap).

## 데이터 모델

```python
@dataclass
class BrainNode:
    id: int
    type: Literal["person", "company", "event", "idea", "project"]
    canonical_name: str
    aliases: list[str]
    metadata: dict
    first_seen_at: int
    last_seen_at: int

@dataclass
class BrainEdge:
    src_id: int
    dst_id: int
    relation: Literal[
        "works_at", "founded", "invested_in", "advises", "attended",
        "mentioned_in", "owns", "led", "child_of",
    ]
    weight: float
    source_ref: str              # "session:<sid>#msg-<idx>" or "memory:<chunk_id>"
    extracted_at: int
```

## 핵심 알고리즘 — LLM-less Entity Extraction

```python
# apps/server/api/brain/extractor.py

# 우선순위 1: 명시적 @-mention (가장 신뢰도 높음)
MENTION_PATTERN = re.compile(r"@([A-Z][\w-]+)")

# 우선순위 2: Title Case 회사명 (Inc/Corp/AI/Labs 접미사)
COMPANY_PATTERN = re.compile(
    r"\b([A-Z][\w]+(?:\s+[A-Z][\w]+){0,3})\s+(?:Inc|Corp|LLC|Ltd|Co|AI|Labs?|Studio|Capital)\b"
)

# 우선순위 3: 명시적 "X works at Y" / "X founded Y"
PATTERN_WORKS_AT = re.compile(
    r"\b([A-Z][\w]+(?:\s+[A-Z][\w]+){0,2})\s+(?:works?\s+at|joined|leads?\s+engineering\s+at)\s+([A-Z][\w]+(?:\s+[A-Z][\w]+){0,3})"
)

def extract(text: str, source_ref: str) -> tuple[list[BrainNode], list[BrainEdge]]:
    nodes: dict[str, BrainNode] = {}
    edges: list[BrainEdge] = []

    # @ mentions
    for m in MENTION_PATTERN.finditer(text):
        name = m.group(1)
        nodes[name.lower()] = _make_node(name, "person")

    # 회사
    for m in COMPANY_PATTERN.finditer(text):
        name = m.group(1)
        nodes[name.lower()] = _make_node(name, "company")

    # X works at Y → 새 edge
    for m in PATTERN_WORKS_AT.finditer(text):
        person, company = m.group(1), m.group(2)
        p = nodes.setdefault(person.lower(), _make_node(person, "person"))
        c = nodes.setdefault(company.lower(), _make_node(company, "company"))
        edges.append(BrainEdge(
            src_id=p.id, dst_id=c.id, relation="works_at",
            weight=0.9, source_ref=source_ref, extracted_at=int(time.time())
        ))

    # ... (10여개 패턴 더)
    return list(nodes.values()), edges
```

## 합성 답변

```python
# apps/server/api/brain/synthesizer.py

SYNTHESIZE_PROMPT = """You are a knowledge synthesizer. Given the following
context (graph nodes + relevant memories), answer the user's question with
citations.

Format your response as JSON:
{
  "answer": "<3-paragraph synthesized response>",
  "citations": [{"ref":"session:abc#42","claim":"Alice runs eng at Acme"}],
  "gap_analysis": "<what's NOT in the brain that would help>"
}

QUESTION: {question}

GRAPH CONTEXT:
{graph_context}

MEMORIES:
{memories}
"""
```

## 파일 구조 + API

```
apps/server/api/brain/
├── __init__.py
├── models.py
├── extractor.py
├── graph.py             # nodes/edges SQLite
├── traversal.py
├── synthesizer.py
├── daemon.py
└── routes.py
```

### API
```
POST /api/brain/ingest        # 명시적 텍스트 ingest
POST /api/brain/query         # 질문 → 합성 답변
GET  /api/brain/nodes/{id}
GET  /api/brain/graph?root=<id>&depth=2
GET  /api/brain/stats         # nodes/edges 카운트
```

### Schema
```sql
CREATE TABLE brain_nodes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,
  canonical_name TEXT NOT NULL,
  aliases_json TEXT NOT NULL DEFAULT '[]',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  first_seen_at INTEGER NOT NULL,
  last_seen_at INTEGER NOT NULL,
  UNIQUE(type, canonical_name)
);
CREATE TABLE brain_edges (
  src_id INTEGER NOT NULL,
  dst_id INTEGER NOT NULL,
  relation TEXT NOT NULL,
  weight REAL NOT NULL DEFAULT 1.0,
  source_ref TEXT,
  extracted_at INTEGER NOT NULL,
  PRIMARY KEY (src_id, dst_id, relation, source_ref)
);
CREATE INDEX idx_brain_edges_src ON brain_edges(src_id, relation);
CREATE INDEX idx_brain_edges_dst ON brain_edges(dst_id);
```

## 에러 케이스 + 성능 + 보안

- LLM synthesis 가 인용 누락 → 응답 검증 (citations 모두 graph 내 존재)
- 무한 traversal 차단: depth ≤ 3, visited set
- ReDoS: 추출 패턴은 catastrophic backtracking 없게 작성
- 1M node 그래프: traversal 200ms 이하 (인덱스 필수)

## 테스트
- Golden 100 텍스트 → entity/edge 정확도 ≥ 80%
- BrainBench-lite (직접 작성): 30 질문 → P@5 ≥ 50%
- Synthesizer 가 citations.ref 가 실제 source 인지 검증

## PR 분할
| PR | 내용 |
|----|------|
| #1 | extractor + 패턴 라이브러리 + golden tests |
| #2 | graph schema + ingest + traversal |
| #3 | synthesizer + LLM 호출 |
| #4 | UI (brain.tsx + 합성 답변 카드) |
| #5 | daemon + 야간 작업자 |

## 실 통합 의존
- ✅ Entity 추출은 100% LLM-less, Hermes 없이도 동작.
- 🟡 합성 답변은 LLM 호출 필요.

---

# 🧬 Phase 22 — Code Knowledge Graph

**기간**: 1.5~2주 · **출처**: D codegraph · **의존성**: Phase 3

## 사용자 스토리

> Henry 가 채팅에 "use-mobile 훅 어디 있어?" 입력 → 즉시 "src/hooks/use-mobile.ts:1 — useIsMobile(maxWidthPx=768)" 응답.
> 별도 grep tool call 없이 응답 → 토큰 절약.
> Henry 가 코드를 수정하면 0.5초 안에 인덱스 업데이트.

## 데이터 모델 + Schema

```sql
CREATE TABLE code_symbols (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workspace_id TEXT NOT NULL,
  file_path TEXT NOT NULL,
  symbol_name TEXT NOT NULL,
  kind TEXT NOT NULL,            -- function/class/method/const/type/interface
  line_start INTEGER NOT NULL,
  line_end INTEGER NOT NULL,
  signature TEXT,
  docstring TEXT,
  language TEXT NOT NULL,
  indexed_at INTEGER NOT NULL,
  UNIQUE(workspace_id, file_path, symbol_name, line_start)
);
CREATE INDEX idx_code_symbols_name ON code_symbols(symbol_name);
CREATE INDEX idx_code_symbols_file ON code_symbols(workspace_id, file_path);

CREATE TABLE code_refs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  src_symbol_id INTEGER NOT NULL,    -- 호출자
  ref_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  line INTEGER NOT NULL,
  FOREIGN KEY (src_symbol_id) REFERENCES code_symbols(id) ON DELETE CASCADE
);
CREATE INDEX idx_code_refs_name ON code_refs(ref_name);
```

## 핵심 알고리즘 — Incremental Re-indexing

```python
# apps/server/api/codegraph/watcher.py

from watchdog.events import FileSystemEventHandler

class CodeWatcher(FileSystemEventHandler):
    DEBOUNCE_MS = 500

    def __init__(self, indexer: Indexer, workspace_id: str):
        self.indexer = indexer
        self.workspace_id = workspace_id
        self._pending: dict[str, threading.Timer] = {}

    def on_modified(self, event):
        if event.is_directory: return
        path = event.src_path
        if not self._is_supported_lang(path): return
        # Debounce repeated saves
        if path in self._pending:
            self._pending[path].cancel()
        t = threading.Timer(self.DEBOUNCE_MS / 1000, self._reindex, args=(path,))
        self._pending[path] = t
        t.start()

    def _reindex(self, path: str):
        self.indexer.reindex_file(self.workspace_id, path)
        self._pending.pop(path, None)
```

## API + Tools

```
POST /api/codegraph/index/{workspace_id}     # 전체 재인덱싱 트리거
GET  /api/codegraph/symbols?q=...&kind=...
GET  /api/codegraph/file/{path}/outline
GET  /api/codegraph/references?symbol=...
```

Hermes Agent 가 호출 가능한 도구로 노출:
```python
{
  "name": "code_find_definition",
  "input": {"symbol": "useIsMobile"},
  "output": [
    {"file":"src/hooks/use-mobile.ts","line":1,"signature":"useIsMobile(maxWidthPx=768)"}
  ]
}
```

## 의존성

```
tree-sitter==0.21.*
tree-sitter-python==0.23.*
tree-sitter-typescript==0.23.*
tree-sitter-javascript==0.23.*
tree-sitter-go==0.23.*
tree-sitter-rust==0.23.*
watchdog==4.0.*
```

## 에러 케이스
- Grammar 미설치 언어 파일 → 무시 + 로그
- 무한 심볼 (generated code) → 파일당 1000 심볼 한도
- 큰 파일 (>1MB) → 무시 + 경고

## 성능 + 보안
| 작업 | 목표 |
|------|------|
| 첫 인덱싱 (5K 파일) | < 30s |
| Incremental (1 파일) | < 200ms |
| `find_definition` 쿼리 | < 10ms (인덱스 hit) |
| Index disk usage | 워크스페이스 크기의 ≤ 5% |

### 위협
- Workspace 외부 path traversal → Phase 3 `_safe_path` 재사용
- Symbol injection (소스에 nul bytes 등) → indexer 가 sanitize
- 대용량 파일 OOM → 크기 한도

## 테스트
- 5 언어 grammar 파싱 (golden 각 5 파일)
- Watcher debounce 정확성
- Lookup exact + fuzzy
- 인덱싱 시간 benchmark

## PR 분할
| PR | 내용 |
|----|------|
| #1 | tree-sitter 통합 + python parser + schema |
| #2 | 4개 추가 parser (ts/js/go/rust) |
| #3 | watcher + incremental |
| #4 | routes + tools |
| #5 | UI (code-graph.tsx) |

## 실 통합 의존
- ✅ tree-sitter 100% 로컬. Hermes 와 무관.

---

# 🌐 Phase 23 — Computer-Use + Browser-Use

**기간**: 1주 · **출처**: I openagent · **의존성**: 없음 (독립)

## 사용자 스토리

> Ivy 가 채팅에 "GitHub trending 페이지 가서 오늘 1등 trending repo 이름 알려줘" 입력 → Hermes Agent 가 browser tool 호출.
> 백엔드가 Playwright 로 페이지 navigate → 1등 repo 추출 → 스크린샷 저장 → 결과 응답.

## API

```
POST   /api/browser/sessions             # 새 브라우저 세션 생성
GET    /api/browser/sessions             # 활성 세션 목록
POST   /api/browser/{sid}/navigate       # {url} → {title, screenshot_b64}
POST   /api/browser/{sid}/click          # {selector|coords}
POST   /api/browser/{sid}/type           # {selector, text}
GET    /api/browser/{sid}/screenshot
POST   /api/browser/{sid}/extract        # {selector} → text/html
DELETE /api/browser/{sid}
```

## Tool 인터페이스 (Hermes Agent 가 호출)

```python
{
  "name": "browser_navigate",
  "input": {"url": "https://github.com/trending"},
  "output": {
    "title": "Trending repositories on GitHub",
    "status": 200,
    "screenshot_b64": "iVBORw0KG...",
    "extracted_text": "Trending repositories..."
  }
}
```

## 구현 — Playwright Python

```python
# apps/server/api/browser/session.py

from playwright.async_api import async_playwright
import asyncio

class BrowserPool:
    IDLE_TIMEOUT_SECONDS = 300

    def __init__(self):
        self._sessions: dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, sid: str) -> BrowserSession:
        async with self._lock:
            if sid in self._sessions: return self._sessions[sid]
            session = await BrowserSession.start()
            self._sessions[sid] = session
            return session

    async def close_idle(self):
        now = time.time()
        for sid, sess in list(self._sessions.items()):
            if now - sess.last_active > self.IDLE_TIMEOUT_SECONDS:
                await sess.close()
                self._sessions.pop(sid, None)
```

## 화이트리스트 정책

```python
HERMES_GUI_BROWSER_ALLOWLIST = os.environ.get(
    "HERMES_GUI_BROWSER_ALLOWLIST",
    "github.com,stackoverflow.com,wikipedia.org,docs.python.org,developer.mozilla.org"
).split(",")

def is_allowed(url: str) -> bool:
    if "://" not in url: return False
    host = urllib.parse.urlparse(url).hostname or ""
    return any(host == d or host.endswith("." + d) for d in HERMES_GUI_BROWSER_ALLOWLIST)
```

## 에러 케이스
| 시나리오 | HTTP | error |
|---------|------|-------|
| URL 화이트리스트 외 | 403 | `domain_not_allowed` |
| Selector 없음 | 404 | `selector_not_found` |
| Navigation timeout | 504 | `navigation_timeout` |
| Browser crash | 500 | `browser_crashed` (세션 자동 재시작) |

## 성능 + 보안

| 작업 | 목표 |
|------|------|
| `navigate` (cold session) | < 5s |
| `navigate` (warm session) | < 2s |
| `screenshot` | < 1s |
| 동시 세션 수 | ≤ 4 (자원 제약) |

### 위협 모델
| 자산 | 위협 | 완화 |
|-----|------|------|
| Playwright 브라우저 | RCE via malicious page | OS sandbox + 헤드리스 |
| Allowlist 외 사이트 | 데이터 유출 | 명시적 화이트리스트 + 사용자 컨펌 |
| Cookie / 세션 | 인증 도난 | 빈 프로필 + 매 세션 격리 |

## 테스트
- Allowlist 차단 (정상 + 우회 시도)
- Idle timeout 종료
- Screenshot 정확성 (golden 비교)

## PR 분할
| PR | 내용 |
|----|------|
| #1 | session pool + allowlist |
| #2 | 6 actions + routes |
| #3 | UI (browser.tsx) + 라이브 스크린샷 |

## 실 통합 의존
- ✅ Playwright 100% 로컬. Hermes 와 무관.

---

# ✨ Phase 24 — UX Quick Wins

**기간**: 1주 · **출처**: H + E + G · **의존성**: 15, 16

작은 개선 6개 묶음.

## 24-1. 소스-그룹 사이드바 아코디언

```tsx
// routes/sessions.tsx 확장
<details open>
  <summary>Web ({webSessions.length})</summary>
  {webSessions.map(s => <SessionRow ... />)}
</details>
<details>
  <summary>Telegram ({tgSessions.length})</summary>
  {tgSessions.map(s => <SessionRow ... />)}
</details>
```

세션의 `metadata.source` 필드 추가 (Phase 15 와 결합).

## 24-2. Profile-aware Model Selector
Phase 16 model-picker.tsx 가 현재 active profile 의 권한 토큰을 기준으로 필터.

## 24-3. React Virtuoso
```
pnpm add react-virtuoso
```
`chat.tsx` 의 메시지 리스트 → `<Virtuoso data={messages} itemContent={...} />`

## 24-4. CLI 유지보수 명령

```python
# apps/server/cli.py

import argparse, sys
from api import config as config_mod, sessions

def main():
    parser = argparse.ArgumentParser(prog="hermes-agent-gui")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("clear-login-locks")
    sub.add_parser("reset-default-login")
    purge = sub.add_parser("purge-old-sessions")
    purge.add_argument("--older-than", default="90d")
    sub.add_parser("doctor")
    args = parser.parse_args()
    # ... 처리 ...
```

`setup.py` / `pyproject.toml` 에 entry-point 추가:
```toml
[project.scripts]
hermes-agent-gui = "apps.server.cli:main"
```

## 24-5. Channel Behavior YAML

Phase 15 의 `~/.hermes/config.yaml` 를 Hermes Agent 본체와 동일 스키마로:
```yaml
messaging:
  telegram:
    mention_required: true
    allowed_chat_ids: [12345]
  discord:
    auto_thread: true
```

## 24-6. Login Lock UI

`apps/server/api/auth.py` 의 `_LOGIN_ATTEMPTS` 를 SQLite 영속화 → Settings 페이지에서 lock 상태 조회 / 해제.

## PR 분할 (각 1 PR S~M)
6 PR — 각각 작아서 병렬 머지 가능.

## 실 통합 의존
- ✅ 전부 자체.

---

# 🎮 Phase 25 — Office 3D + Multi-CLI + Marketplace

**기간**: 3~4주 · **출처**: G + E + C · **의존성**: 9, 15~24 안정화

가장 큰 phase — 분할 권장 (25a/25b/25c).

## 25-1. Office 3D (Claw3d)

```
apps/web/src/feature-3d/
├── office.tsx                # 메인 3D scene
├── characters/agent-avatar-3d.tsx  # Phase 9 의 lazy chunk 채움
├── interactions/             # 클릭/이동/대화 버블
└── scenes/
    ├── default-office.tsx    # 책상 + 칸반 보드 + 채팅 버블
    └── library.tsx           # 메모리 = 책장
```

의존성 (이미 A 에서 검토): three, @react-three/fiber, @react-three/drei, @react-three/rapier.

**중요**: 이 의존성들은 ≈700KB. lazy chunk 로 격리해서 기본 번들 영향 0.

## 25-2. Multi-CLI Bridge

```python
# apps/server/api/cli_bridges/base.py

class CliBridge(ABC):
    @abstractmethod
    async def spawn(self) -> None: ...
    @abstractmethod
    async def send(self, text: str) -> None: ...
    @abstractmethod
    async def recv_stream(self) -> AsyncIterator[bytes]: ...
    @abstractmethod
    async def kill(self) -> None: ...

# apps/server/api/cli_bridges/claude_code.py

class ClaudeCodeBridge(CliBridge):
    """Spawn 'claude' CLI as subprocess + capture stdin/stdout."""
    BINARY = "claude"   # or full path from settings

    async def spawn(self):
        self.proc = await asyncio.create_subprocess_exec(
            self.BINARY, "--non-interactive",
            stdin=PIPE, stdout=PIPE, stderr=PIPE,
        )
```

각 CLI 의 stdin/stdout 을 SSE 로 노출. `chat.tsx` 에 "Engine" dropdown.

## 25-3. Agent Marketplace

```json
// apps/server/api/marketplace/catalog.json (큐레이션 30~50개)
[
  {
    "id": "deep-researcher",
    "label": "Deep Researcher",
    "category": "research",
    "soul_md": "...",
    "skills": ["web_search", "academic_lookup"],
    "tags": ["research", "writing"]
  }
]
```

`POST /api/marketplace/install/{id}` → 새 profile + SOUL.md + 스킬 자동 설치.

## PR 분할
| PR | 내용 |
|----|------|
| #1 (25a) | 3D office 의존성 추가 + scaffold 씬 |
| #2 (25a) | 캐릭터 + 인터랙션 |
| #3 (25b) | CLI bridge base + Claude Code 통합 |
| #4 (25b) | Codex + Gemini + OpenCode + OpenClaw |
| #5 (25c) | Marketplace catalog + install flow |
| #6 (25c) | UI + 카테고리 그리드 |

## 실 통합 의존
- ✅ 3D, marketplace 자체 동작.
- 🟡 Multi-CLI 는 각 CLI 가 설치된 환경에서만 실증.

---

# 의존성 매트릭스

```
0 ─→ 1 ─→ 2 ─┬─→ 3 ─→ 4 ─→ 5 ─→ 6
             │                    ↓
             │                    7 ─→ 8 ─→ 9 ─→ 10 ─→ 11 ─→ 12 ─→ 13 ─→ 14
             └─→ 17 ─→ 18 ─→ 19 ─→ 21
                        │
                        └─→ 22 (codegraph — Phase 3 끝나면 시작 가능)

15 (messaging) ─┐
                ├─→ 16 (providers) ─→ 24-2 (profile-aware)
                │                    └─→ 25-2 (multi-CLI)
                └─→ 24-5 (channel YAML)

12 (electron) ─→ 20-2 (auto-update)
 9 (3D flag)  ─→ 25-1 (Office 3D)

23 (browser-use) ── 독립 ──┐
                            ↓
                        모든 Phase ─→ 14 (CI 회귀)
```

**Critical path** (sequential bottleneck): `0 → 1 → 2 → 15 → 16 → 17 → 18 → 21`

**병렬 트랙**:
- `3 → 22` (codegraph, Phase 3 후 어디서든)
- `23` (browser-use, Phase 1 후 어디서든)
- `9 → 25-1` (3D office, Phase 9 후 어디서든)

---

# 16주 실행 일정

| Week | Phase | 묶음 | 주력 PR |
|------|-------|------|---------|
| 1 | 15 (1주차) | Messaging — registry + 6 platforms | #1, #2 (3 platforms) |
| 2 | 15 (2주차) | Messaging UI + profile archive | #3, #4, #5 |
| 3 | 16 | Multi-provider + slash | #1~5 (모두) |
| 4 | 17 | Persona + FTS5 + Usage | #1~5 |
| 5 | 18 (1주차) | Compression trigger + summarizer | #1, #2 |
| 6 | 18 (2주차) | RAG inject + UI | #3, #4, #5 |
| 7 | 19 | Memory plugins + PII | #1~5 |
| 8 | 20 | Group chat + Updater + Backup | #1~5 |
| 9 | 21 (1주차) | Brain extractor + graph | #1, #2 |
| 10 | 21 (2주차) | Synthesizer + UI + daemon | #3, #4, #5 |
| 11 | 22 (1주차) | tree-sitter + python parser | #1, #2 |
| 12 | 22 (2주차) | 4 parsers + watcher + UI | #3, #4, #5 |
| 13 | 23 | Browser-use | #1~3 |
| 14 | 24 | UX quick wins (6 sub-tasks) | 병렬 6 PR |
| 15 | 25a | Office 3D | #1, #2 |
| 16 | 25b/c | Multi-CLI + Marketplace | #3~6 |

병렬 진행 시 12주로 단축 가능 (Phase 22, 23, 25-1 을 critical path 와 별도 트랙으로).

---

# 부록 A — 의존성 버전 매트릭스

## Backend (Python)

| 의존성 | 버전 | Phase 첫 도입 | 비고 |
|--------|------|---------------|------|
| Python | ≥ 3.11 | 0 | match, walrus 사용 |
| pyyaml | ≥ 6.0 | 1 | config |
| cryptography | ≥ 42.0 | 1 | passkey + secret rotation |
| pytest | ≥ 8.0 | 14 | test |
| sqlite-vss | ≥ 0.1.* | 18 | RAG (옵션) |
| tree-sitter | == 0.21.* | 22 | code graph |
| tree-sitter-{python,typescript,javascript,go,rust} | == 0.23.* | 22 | grammars |
| watchdog | ≥ 4.0 | 22 | file watcher |
| playwright | ≥ 1.40 | 23 | browser (Python binding) |
| presidio-analyzer | ≥ 2.2 | 19 (옵션) | PII 확장 |

## Frontend (npm)

| 의존성 | 버전 | Phase 첫 도입 |
|--------|------|---------------|
| react / react-dom | ≥ 19.2 | 0 |
| @tanstack/react-router | ≥ 1.166 | 0 |
| @tanstack/react-query | ≥ 5.90 | 0 |
| tailwindcss | ≥ 4.1 | 0 |
| zustand | ≥ 5.0 | 0 |
| vite | ≥ 7 | 0 |
| vite-plugin-pwa | ≥ 0.21 | 8 |
| vite-plugin-singlefile | ≥ 2 | 11 |
| recharts | ≥ 3.7 | 17 |
| react-virtuoso | latest | 24 |
| three / @react-three/* | ≥ 0.184 / ≥ 9 | 25-1 (옵션) |

새 의존성 추가 시 본 표에 행 추가 필수 (PR review에서 검증).

---

# 부록 B — 용어집

| 용어 | 정의 |
|------|------|
| **Phase** | 독립 PR 단위. 본 문서의 한 섹션. |
| **Embedded mode** | Hermes Agent 를 직접 `import` (Phase 1 의 EmbeddedAdapter). |
| **Gateway mode** | Hermes Agent gateway (port 8642) HTTP 호출. zero-fork. |
| **Echo mode** | Hermes 없이 사용자 입력을 단어별로 echo (개발/테스트). |
| **Profile** | Hermes 의 격리된 환경 단위. config + memory + skills + sessions 의 묶음. |
| **Persona / SOUL.md** | 에이전트의 성격 정의 파일. `~/.hermes/profiles/<name>/SOUL.md`. |
| **Transcript drift** | 브라우저↔서버 세션 메시지 카운트 차이. Phase 2 의 repair 대상. |
| **Compression alias** | 세션 압축 후 ID 회전 시 old→new 매핑. Phase 2. |
| **FTS5** | SQLite 의 풀텍스트 검색 가상 테이블. Phase 17. |
| **VSS** | SQLite-VSS = SQLite Vector Similarity Search. Phase 18. |
| **Mission** | Conductor 가 decompose 한 sub-task 묶음. Phase 6 + 21. |

---

# 부록 C — FAQ

### Q. 본 문서 외에 무엇을 봐야 하나?
- 아키텍처 깊이: [`06-integration-design.md`](./06-integration-design.md)
- 완료된 Phase 의 코드: `apps/server/api/<domain>/*.py`
- 의사결정 히스토리: [`05-conflict-resolution.md`](./05-conflict-resolution.md)

### Q. Phase 가 너무 큰데 분할해도 되나?
✅ 환영. PR 분할 권장 표에 따른 분할은 기본이고, 더 세분할 수도 있음. 단, schema migration 같은 깨지면 안 되는 단위는 한 PR 안에 유지.

### Q. Hermes Agent 실설치 환경에서만 가능한 검증은?
각 phase 의 §실 통합 의존 섹션 참조. 대체로 LLM 호출이 필수인 phase (18, 21) 와 외부 서비스 통합 (15 messaging, 19 memory plugins).

### Q. Phase 0~14 도 본 문서 안에 풀어쓰기?
간략 요약만 [§Phase 0~14 핵심 요약](#-phase-014-핵심-요약) 에 포함. 상세는 [`09-phase-2-to-14-summary.md`](./09-phase-2-to-14-summary.md) 가 정답 출처.

### Q. 권장 순서 외 다른 순서로 가능?
의존성 매트릭스의 화살표를 깨지 않는 한 OK. 예: 23(browser-use)은 거의 모든 시점에 가능. 22(codegraph)는 Phase 3 이후 어디든.

### Q. 새 phase 가 본 문서를 변경하면?
신규 PR 의 일부로 본 문서 갱신. 진행 현황 표 + 의존성 매트릭스 + 부록 A 의존성 버전 매트릭스 모두 sync.

---

**문서 끝 — 본 문서를 누구든 받아 어느 Phase 든 구현할 수 있어야 한다. 의문이 생기면 §0 공통 표준 부터 다시 읽는다.**
