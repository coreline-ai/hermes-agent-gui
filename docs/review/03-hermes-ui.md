# C · pyrate-llama/hermes-ui — 코드 레벨 상세 분석

> **Repo**: https://github.com/pyrate-llama/hermes-ui
> **Version**: 3.3.18 · **Language**: HTML (single file) · **License**: MIT
> **Stars**: 142 · **Last push**: 2026-05-22
> **Tagline**: "The command center for Hermes Agent — a single glassmorphic HTML app."

---

## 1. 정체성 한 줄 요약

**`hermes-ui.html` 단일 파일(621 KB) + `serve_lite.py`(Python stdlib) 라이트 프록시.**
"Single-file HTML application with React 18, real-time log streaming, file browsing, memory inspection — all through a lightweight Python proxy server." Glassmorphism 디자인, Tailscale/SSH 터널 환경 친화, 빌드 단계 0.

---

## 2. 기술 스택

### Client (단일 HTML)
| Layer | 채택 |
|------|------|
| Framework | **React 18.2** (Babel standalone — 브라우저 내 JSX 트랜스파일) |
| Style | Tailwind 또는 인라인 CSS + **Glassmorphism** (backdrop-filter blur, transparency) |
| 진입점 | `hermes-ui.html` (621006 bytes) — JSX + CSS + 자산 인라인 |
| 추가 자산 | `assets/hermes-agent-avatar.png`, `hermes-agent-wordmark.png`, `filler-bg.png` |
| 다국어 | `README.zh-CN.md` 존재 (UI 자체 i18n 여부는 불명; 단일 HTML 내부에 인라인 가능성) |

### Server
| Layer | 채택 |
|------|------|
| HTTP | **Python stdlib 만** (`http.server`) — `serve_lite.py` |
| 의존성 | **0개** (`requirements.txt` 가 주석만) |
| 인증 | 비밀번호 환경변수 (`HERMES_UI_PASSWORD` / `HERMES_WEBUI_PASSWORD`) + HMAC 쿠키 + 시크릿 파일(`~/.hermes/ui-auth-secret`) |
| 상태 | `~/.hermes/ui-workspaces.json`, `~/.hermes/ui-last-workspace.txt`, `~/.hermes/ui-conversations.json` |
| 연동 | **Hermes Agent AIAgent 를 직접 임포트** (gateway 미경유) |
| 스트리밍 | SSE |
| 파일 | 업로드 한도 750MB · 워크스페이스 picker (Home/Desktop/Documents/Downloads + OneDrive + Windows 드라이브) |

### Backwards-compat
- `serve.py` — `serve_lite.py` 로 exec 하는 deprecation shim (구 systemd unit 호환)
- `serve.py 8080` (positional port) → `serve_lite.py --port 8080` 자동 변환

### Behavior / Safety
- Python 인터프리터 ABI 검사 — `~/.hermes/hermes-agent/venv` 의 Python minor 와 다르면 자동 re-exec 또는 명확한 에러
- `_check_interpreter_matches_venv()` — pydantic_core 등 C 확장이 ABI 깨질 때 "Stream ended without a completion event" 같은 무성 실패 방지

---

## 3. 코드 구조

```
hermes-ui/
├── hermes-ui.html              ← 단일 React SPA (621 KB)
├── serve_lite.py               ← canonical proxy server (Python stdlib)
├── serve.py                    ← deprecation shim → execv serve_lite.py
├── requirements.txt            ← (comments only — 0 deps)
├── README.md, README.zh-CN.md
├── TESTING.md, TODO.md, CLAUDE.md
├── behavioral_guidelines.md
├── assets/
│   ├── hermes-agent-avatar.png
│   └── hermes-agent-wordmark.png
├── filler-bg.png
├── screenshots/
│   ├── chat.png, chat-light.png, chat-logs.png
│   ├── tasks.png, dashboard.png, files.png, terminal.png
│   ├── skills.png, mcp-tools.png, cron-jobs.png
└── .github/ISSUE_TEMPLATE/{bug_report,config,feature_request}
```

### 3.1 `hermes-ui.html` — 단일파일 SPA

크기 621KB. README 스크린샷 기반으로 추정한 화면 구성:

| 영역 | 기능 |
|------|------|
| **Chat** | 인라인 이미지 생성 + 라이브 터미널 패널 분할 + 스트리밍 응답 가시화 + 라이트/다크 |
| **Tasks** | Active tool work + 백그라운드 follow-up 트래킹 (Done 2h 후 만료, Needs You/blocked 12h 후) |
| **Dashboard** | 라이브 통계, 최근 활동, 설치된 스킬 |
| **Skills Browser** | 설치된 스킬 목록 + 관리 |
| **Cron Jobs** | 편집/일시정지/즉시실행 컨트롤 포함 |
| **MCP Tools** | 연결된 MCP 서버 (카테고리 그룹) |
| **File Browser** | 활성 워크스페이스 파일/인라인 미리보기 |
| **Terminal** | Hermes 와 Claude Code 탭 분리 |
| **Health** | Hermes heartbeat, agent/model/provider 상태, Scrapling/web extraction, redacted recent logs |
| **Sidebar** | 핵심 작업 영역 우선 + 보조 도구는 expander |
| **Composer** | 활성 Hermes work 와 task follow-ups 가 메시지 박스 위 상시 표시 (banner) |

### 3.2 `serve_lite.py` — 라이트 프록시 서버 핵심 흐름

```python
PROJECT_ROOT       = Path(__file__).resolve().parent
UPLOAD_MAX_BYTES   = 750 * 1024 * 1024
HERMES_HOME        = ~/.hermes
AGENT_DIR          = HERMES_HOME / "hermes-agent"
PORT               = 3333
WORKSPACES_FILE    = HERMES_HOME / "ui-workspaces.json"
LAST_WORKSPACE_FILE= HERMES_HOME / "ui-last-workspace.txt"
AUTH_PASSWORD      = env(HERMES_UI_PASSWORD or HERMES_WEBUI_PASSWORD)
AUTH_COOKIE_NAME   = "hermes_ui_auth"
AUTH_SECRET_FILE   = HERMES_HOME / "ui-auth-secret"

# Hermes Agent AIAgent 를 직접 임포트하는 경로
sys.path.insert(0, AGENT_DIR)
from hermes.agent import AIAgent     # (예상 import 경로)

# Workspace picker — 허용된 루트만 노출
def _workspace_picker_roots():
    defaults = [Home, Desktop, Documents, Downloads, "Hermes UI", ...]
    + OneDrive variants (Win 환경변수 OneDrive/OneDriveCommercial/OneDriveConsumer)
    + Windows 드라이브 letter 스캔
    + Unix "Computer" = "/"
    return roots
```

핵심 디자인 결정:
1. **Gateway 미경유** — `serve_lite.py` 가 `AIAgent` 를 직접 import 해서 호출. 이것이 `serve.py` deprecation 의 이유 ("reference UI" 와 같은 두-단계 SSE API surface 로 통일).
2. **Workspace 격리** — picker 가 화이트리스트 루트 외부 접근을 거부 (`_path_is_within_any` 가드).
3. **Path safety** — `_workspace_target` 가 `..` , 절대경로, `\` 정규화 처리.
4. **인터프리터 sanity check** — 잘못된 Python 으로 실행 시 venv Python 으로 자동 re-exec.

### 3.3 패치 히스토리에서 드러나는 운영 노하우 (v3.3.x 발췌)

| 버전 | 핵심 패치 |
|------|----------|
| 3.3.18 | Crash recovery — recovery context 가 최신 user turn 유지, 오래된 워크플로 취소 명시 |
| 3.3.16 | 사이드바 캐시 우회 + JSON no-store 헤더 |
| 3.3.15 | 취소 클린업 + 컨텍스트 안전 + 최근 채팅 정렬 |
| 3.3.14 | 대화 dedup (session id) |
| 3.3.13 | Firefox 성능 모드 (애니메이션/blur off) + 모델 picker dedupe |
| 3.3.11 | 스테일 compact context 복구 (백엔드 tail 만 가지고 답하지 않도록) |
| 3.3.10 | 보이지 않는 tail-trim 제거 — agent 가 직접 compression 이벤트 발행 |
| 3.3.9 | 비디오 업로드 (Kimi 등) — uploads/ 폴더 저장, 바이트 인라인 금지 |
| 3.3.8 | 짧은 채팅의 silent narrowing 수정 (<40 turn 은 full transcript 사용) |
| 3.3.7 | 복구된 UI tool 영수증을 provider-native 로 위조하지 않음 (provenance 라벨) |
| 3.3.6 | `~/.hermes/ui-conversations.json` 에서 toolCalls 복구 — equal-count 케이스에서도 repair |
| 3.3.5 | tool evidence 없을 때 즉시 self-contradiction 방지 — 도구로 검증 강제 |
| 3.3.4 | 브라우저↔서버 transcript repair 의 model-facing tail 도 갱신 + `/api/session/health` 추가 |
| 3.3.3 | transcript safety check + Tasks 보드 aging (Done 2h, Needs You 12h) |
| 3.3.2 | Composer work banner + tool honesty guard |
| 3.3.1 | 컨텍스트 압축 후 세션 ID 회전 시 alias 유지 (재시작 후에도) |
| 3.3 | Health 화면 + log redaction + 긴 채팅 smoothing + 사이드바 단일 별표 |

**관찰** — 본 프로젝트의 가장 큰 자산은 **transcript / tool evidence repair 로직과 session lifecycle 안전망**. 동일 문제(컨텍스트 압축 회전, transcript drift) 를 B 와 A 도 다루지만, C 의 패치 노트가 가장 구체적이고 실전 검증되어 있음.

### 3.4 `CLAUDE.md` 코멘트 (그대로 발췌)

```
## Architecture
- hermes-ui.html: Single-file React 18 + Babel standalone app
- serve_lite.py: Python proxy server on port 3333 (stdlib only) — canonical server
- serve.py: Deprecation shim that execs serve_lite.py
- Hermes Agent runs at localhost:8642
- GitHub: pyrate-llama/hermes-ui
```

---

## 4. 핵심 기능 (스크린샷 기준)

- 채팅 (인라인 이미지 생성, 라이브 로그 split, 스트리밍)
- Tasks 보드 (live work tracking + aging)
- Dashboard (라이브 통계 + 최근 활동 + 설치 스킬)
- Skills 브라우저
- Cron Jobs (편집/pause/run-now)
- MCP Tools (카테고리 그룹)
- File Browser (인라인 미리보기)
- Terminal (Hermes / Claude Code 탭)
- Health 화면 (heartbeat, model/provider 상태, redacted logs)
- 비디오 업로드

---

## 5. 연동 모델

```
┌────────────────────────────────────────────────────────┐
│  Browser — hermes-ui.html (React 18 + Babel runtime)   │
│   ↑ fetch + SSE (/api/chat/stream 등)                  │
│   ↓                                                    │
│  serve_lite.py — Python stdlib                         │
│   └── (in-process) AIAgent  ← from ~/.hermes/hermes-agent│
└────────────────────────────────────────────────────────┘
                Port 3333
```

운영 모드: **In-process 만** (A 의 zero-fork 와 다르게 Agent 본체를 직접 임포트).

---

## 6. 보안 / 운영 자산

- HMAC 서명 쿠키 + 시크릿 파일 회전
- 환경변수 비밀번호 (`HERMES_UI_PASSWORD` 또는 `HERMES_WEBUI_PASSWORD` — B 와 호환)
- 워크스페이스 picker 화이트리스트 (path traversal 방어)
- 업로드 750MB 한도
- Python 인터프리터 ABI 검사 (silent failure 방지)
- `redacted` log 표시 (토큰/API key 노출 차단)
- 비디오 등 바이너리는 파일 path + MIME + size 만 전달 (히스토리에 바이트 인라인 금지)

---

## 7. 강점

1. **단일파일 배포의 결정판** — curl 하나로 받고 `python3 serve_lite.py` 만 치면 동작
2. **세션 회복 로직의 깊이** — 3.3.x 패치 히스토리가 곧 자산. transcript drift, compression rotation, tool evidence repair 가 가장 단단함
3. **Glassmorphism 디자인** — 시각적 정체성이 가장 또렷
4. **Hermes 와 Claude Code 멀티 탭 터미널** — 유일한 분리 디자인
5. **ABI sanity check** — venv Python 미스매치를 명확히 alert 하고 자동 복구
6. **Honesty guard** — "도구 없이 narrate 만 한 작업"을 UI 에서 플래그 (환각 대응)

## 8. 약점

1. **Babel standalone 의 런타임 비용** — 모든 브라우저가 JSX 를 매번 컴파일 → 첫 페인트 지연
2. **단일 HTML 621KB** — 코드 스플릿/lazy load 불가
3. **별점이 적음(142)** — 커뮤니티 베이스 작음
4. **테스트 인프라 부재** — `TESTING.md` 는 있으나 자동화 분명치 않음
5. **React 18 (19 가 아님)** — 최신 동시성 기능 부족
6. **인증이 비밀번호 1개** — OAuth/Passkey 없음 (B 보다 얇음)
7. **확장이 어려움** — 단일 HTML 에 모든 React 컴포넌트가 인라인되어 있어 유지보수 비용↑

---

## 9. 통합 시 활용 결정

| 이식 / 채택 대상 | 이유 |
|------------------|------|
| **Transcript / tool evidence repair 알고리즘** | 표준 채택 — 백엔드는 Python(B 기반)로, 알고리즘만 옮김 |
| **`/api/session/health` 응답 스키마** (server/browser/compact counts) | 표준 채택 |
| **Compression session aliases** (회전 후 ID 매핑 유지) | 표준 채택 |
| **Compose work banner** UI 컨셉 | A 컴포넌트로 구현 시 채택 |
| **Tool honesty guard** | 표준 채택 (도구 미사용 narrate 플래깅) |
| **Tasks aging** (Done 2h / Needs You 12h) | 표준 채택 |
| **터미널 탭** (Hermes / Claude Code / shell) | A 의 xterm.js 위에 채택 |
| **Glassmorphism 토큰** | 6번째 테마로 채택 |
| **Workspace picker 화이트리스트** | path safety 가드 표준 |
| **Python interpreter ABI sanity check** | `bootstrap.py`(B) + 본 검사 결합 |
| **`hermes-ui.html` (단일 HTML)** | **포기** — A 컴포넌트 + Vite + `vite-plugin-singlefile` 로 동등 빌드 모드 제공 |
| **`serve_lite.py` 자체** | **참고만** — 백엔드는 B 채택 |
| **HMAC 쿠키 인증** | B 의 OAuth/Passkey 가 상위 호환이라 흡수 |
| **비디오 업로드 패턴** | 채택 — uploads/ + 파일경로 전달 |

상세 통합 방안은 [`06-integration-design.md`](./06-integration-design.md) 참조.
