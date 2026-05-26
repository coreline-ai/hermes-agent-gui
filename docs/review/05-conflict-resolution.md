# 05 · 중복 충돌 해소 결정표

> 본 문서는 3종에서 **동일/유사 기능이 중복**되는 경우, 어느 구현을 채택하고 어느 것을 흡수/폐기할지를 결정한다.
> 결정 원칙(우선순위):
> 1. **장기 유지보수성** — TypeScript > 빌드 없는 vanilla > Babel-CDN
> 2. **확장성** — 모듈/컴포넌트 분리 가능한가
> 3. **실전 검증** — 패치 히스토리·테스트·운영 자산이 있는가
> 4. **언어 통일** — 백엔드는 Hermes Agent 와 같은 Python 으로
> 5. **배포 간소화** — 단일 명령 `start` 가능한가

---

## ⚖️ 결정 매트릭스

| # | 중복 영역 | A | B | C | **채택** | 근거 |
|---|----------|---|---|---|---------|------|
| 1 | **UI 프레임워크** | React 19 + TanStack + TS | Vanilla JS | React 18 + Babel | **A** | TypeScript + 파일라우팅 + 모듈성. B 의 vanilla 는 100+ 컴포넌트 규모 유지 불가. C 의 Babel-CDN 은 코드스플릿/지연로딩 불가 |
| 2 | **백엔드 언어** | TypeScript (Node22+) | Python stdlib | Python stdlib | **B (Python)** | Hermes Agent 본체와 동일 언어 → in-process 임베드 가능. Node 의존성 제거. A 의 `pty-helper.py` 가 이미 Python 인 점이 방향성 입증 |
| 3 | **HTTP 서버** | TanStack Start (Vinxi) | `server.py` + stdlib | `serve_lite.py` stdlib | **B** | stdlib 만으로 30+ 모듈 운영 실적. C 는 stdlib 지만 단일 파일이라 모듈 분할 부재 |
| 4 | **인증** | middleware + CSP + rate-limit | OAuth + Passkeys + Password + CSP + rate-limit | Password + HMAC 쿠키 | **B + A 가드 결합** | B 가 다층 인증 + WebAuthn 까지 커버. A 의 fail-closed remote bind 정책과 결합 |
| 5 | **세션 라이프사이클** | `local-session-store` + `run-store` | 5종 모듈 세트 | in-memory + repair | **B 베이스 + C 알고리즘 흡수** | B 의 5 모듈을 골격, C 의 transcript drift / tool evidence repair / compression alias 알고리즘을 그대로 이식 |
| 6 | **`/api/session/health`** | 〜 | ✓ | ✓✓ (server/browser/compact counts) | **C 스키마 채택** | C 의 카운트 비교 응답이 가장 디버깅 친화 |
| 7 | **SSE 스트리밍** | `claude-agent.ts` / `responses-api.ts` | `streaming.py` (half-close 처리) | 직접 AIAgent 호출 | **B** | Tailscale/모바일 절단을 1급 처리 |
| 8 | **칸반 백엔드** | `kanban-backend.ts` (TS) | `kanban_bridge.py` | Tasks (in-mem) | **B 베이스 + A UI** | 백엔드 = Python, UI = A 의 swarm-kanban + conductor 보드 |
| 9 | **칸반 / Tasks UI** | TaskBoard + Conductor 미션 | 단순 보드 | aging-aware (Done 2h / Needs You 12h) | **A UI + C aging 규칙** | A 컴포넌트에 C 의 만료 정책 추가 |
| 10 | **Cron 잡** | `cron-manager` UI + profiles | 실행기 + 메시징 알림 | UI(편집/pause/run-now) | **A UI + B 실행기** | UI 는 A, 실제 fire/알림은 B (이미 메시징 통합 깊음) |
| 11 | **파일 브라우저 / 에디터** | Monaco + file-explorer | workspace.js + 인라인 | 인라인 | **A** (Monaco 표준) | Monaco 는 산업 표준 |
| 12 | **워크스페이스 git** | dashboard 경유 | `workspace_git.py`, `worktrees.py` | ✗ | **B** | 깊이 우위 |
| 13 | **워크스페이스 picker / path 가드** | 기본 | path safety | **whitelist + Windows 드라이브 + OneDrive + traversal 가드** | **C 가드 알고리즘 채택** | C 의 `_path_is_within_any` 가 가장 견고 |
| 14 | **터미널** | xterm.js + addons + `pty-helper.py` | 수기 `terminal.js` | 수기 + 멀티탭 (Hermes/Claude Code) | **A 라이브러리 + C 탭 패턴** | xterm.js 위에 다중 탭 매니저 |
| 15 | **PTY 백엔드** | Node 호출 → `pty-helper.py` (Python) | `terminal.py` | 직접 spawn | **B 통합** (A 의 helper 흡수) | 백엔드가 Python 이므로 helper 가 1급 모듈로 승격 |
| 16 | **스킬 / MCP UI** | `/mcp` 카탈로그 + 마켓플레이스 + sources | `extensions.py` | 그룹 뷰 | **A** | UI 자산 최고 |
| 17 | **메모리 뷰어** | `memory-viewer/` + 라이브 에디터 | 텍스트 뷰 | 인스펙션 | **A** | 마크다운 라이브 에디터 |
| 18 | **대시보드** | aggregator (sessions/cost/attention) | live stats | live stats | **A** | aggregator 패턴 채택 + B 의 `dashboard_probe.py` 데이터 소스 |
| 19 | **Health 화면** | 〜 | `agent_health` + `system_health` + `dashboard_probe` + `gateway_watcher` | heartbeat + redacted logs | **B 데이터 + C UI 패턴 + log redaction** | B 의 4종 모듈로 데이터 수집, C 의 단일 화면 + redaction 정책 |
| 20 | **테마 시스템** | 5종 (Hermes/Nous/Bronze/Slate/Mono × light/dark) | light/dark | Glassmorphism + Dawn 등 | **A 5종 + C Glassmorphism** = 6종 | Glass 는 토큰 단위로 추가 |
| 21 | **PWA / Service Worker** | 〜 | `sw.js` + `manifest.json` | ✗ | **B 기반 + vite-plugin-pwa 재구성** | 동작은 B, 빌드는 framework-managed |
| 22 | **Compose work banner / Tool honesty guard** | ✗ | ✗ | ✓ (v3.3.2) | **C 채택** | 환각 방어 UX, A 컴포넌트로 구현 |
| 23 | **컴포저 footer** | 분산 | model/profile/workspace 토글 + ring | 컨텍스트 표시 | **B 레이아웃 + A 컴포넌트** | 3-panel 의 footer 패턴 유지, 컴포넌트는 A |
| 24 | **명령 팔레트** | `command-palette.tsx` | ✗ | ✗ | **A** | 유일 |
| 25 | **글로벌 단축키** | `global-shortcut-listener` + `use-global-shortcuts` | ✗ | 〜 | **A** | 유일 |
| 26 | **음성 입력 (STT)** | `use-voice-*` + `stt-transcription.ts` | ✗ | ✗ | **A** | 유일 — Python 으로 재이식 |
| 27 | **i18n** | `lib/i18n.ts` + 테스트 | `static/i18n.js` | 〜 | **A 패턴 + B 키맵 흡수** | TS 표준, 메시지 카탈로그는 흡수 |
| 28 | **다국어 README** | 영어만 | 영어 | 영어 + zh-CN | **C 패턴 (지역화 README)** | docs 패턴 |
| 29 | **컨텍스트 미터** | `context-meter` + ring | composer ring | 컨텍스트 디스플레이 | **A 컴포넌트 + B 위치 (composer footer)** | UX 통합 |
| 30 | **온보딩** | react-joyride 투어 | bootstrap 마법사 (Agent 설치까지) | ✗ | **B 마법사 + A 투어** | 첫-실행은 B, 이후 신규 기능 투어는 A |
| 31 | **알림 / 토스트** | `error-toast`, `model-suggestion-toast` 등 | 〜 | 〜 | **A** | 컴포넌트 풍부 |
| 32 | **모바일 컴포넌트** | `mobile-hamburger-menu`, `mobile-sessions-panel`, `mobile-tab-bar`, `mobile-prompt`, `use-mobile-keyboard`, `use-pull-to-refresh`, `use-swipe-navigation` | 3-panel 가 적응 | 〜 | **A 컴포넌트** + **B 3-panel 적응 로직** |
| 33 | **데몬 lifecycle** | Electron 자체 | `ctl.sh` start/stop/status/logs/restart | 〜 | **B `ctl.sh`** | 그대로 채택 |
| 34 | **Docker 배포** | 2 compose (dev/prod) | 3 compose (1/2/3-컨테이너) | ✗ | **B** 3종 모두 채택 |
| 35 | **인터프리터 ABI 가드** | ✗ | 〜 | venv 미스매치 자동 re-exec | **C 채택** | bootstrap.py 에 통합 |
| 36 | **Hermes 와 Claude Code 분리 터미널 탭** | ✗ | ✗ | ✓ | **C 채택** | 멀티 어시스턴트 패턴 |
| 37 | **비디오 업로드** | 〜 | 〜 | v3.3.9 (uploads/ + path 전달) | **C 채택** | 바이너리 인라인 금지 정책 |
| 38 | **로그 redaction** | 〜 | 〜 | UI 표시 로그 redact | **C 정책 채택** | 토큰 노출 방지 |
| 39 | **사이드바 정렬 / dedup** | `use-pinned-sessions` | 일반 | conversation dedup + 정렬 정규화 (v3.3.14~16) | **C 알고리즘** | A 의 store 위에 |
| 40 | **Conductor + Swarm** | 유일 | ✗ | ✗ | **A 채택 (Python 재포팅)** | 미션 분해/디스패치, tmux 워커 매니저 |
| 41 | **3D / hermesworld / agora / vt-capital** | 별도 트랙 | ✗ | ✗ | **본 통합에서 제외** | 별도 프로젝트로 fork |
| 42 | **Electron** | ✓ main/preload/prod-server + builder | ✗ | ✗ | **A 채택 (옵션 빌드)** | 데스크탑 타깃이 필요할 때만 |
| 43 | **테스트** | vitest + RTL + playwright | pytest | TESTING.md 만 | **A 프론트 + B 백엔드** | 양쪽 결합 |

---

## 채택 결과 한 줄 요약

> **신규 통합 UI =**
> · **프론트엔드 = A** (React 19 + TanStack + Tailwind v4 + Vite)
> · **백엔드 = B** (Python stdlib, OAuth/Passkey, 세션 5종, kanban_bridge, 메트로닝 등)
> · **세션/회복 알고리즘 = C** (transcript drift / tool evidence / compression alias)
> · **로그 redaction · ABI 가드 · 단일파일 빌드 모드 = C**
> · **Conductor + Swarm = A → Python 으로 재포팅**
> · **테마 = A 5종 + C Glassmorphism = 6종**
> · **PWA = B 패턴 + vite-plugin-pwa**
> · **데몬/Docker = B**
> · **Electron = A 옵션 빌드**
> · **컴포저 footer = B 레이아웃 + A 컴포넌트 + C banner/honesty guard**

상세 구현 설계는 [`06-integration-design.md`](./06-integration-design.md) 참조.

---

## 폐기 항목 (의도적 제외)

| 항목 | 폐기 이유 |
|------|----------|
| B 의 vanilla JS frontend (`static/*.js`) | A 의 React 컴포넌트로 동등 이상 구현 |
| C 의 단일 HTML `hermes-ui.html` | `vite-plugin-singlefile` 빌드 모드로 동등 산출물 제공 |
| C 의 `serve_lite.py` 자체 | B 의 `api/` 모듈식 구조가 상위 호환 |
| A 의 TanStack Start (Node 서버) | 백엔드 = Python(B) 로 통일. A 의 `src/server/*` 는 Python 으로 재포팅 |
| A 의 hermesworld / 3D 게임 트랙 | 본 통합 범위 밖 |
| A 의 playground Cloudflare Worker 서브패키지 | 본 통합 범위 밖 |

---

## 확정 결정 (2026-05-25)

다음 6개 항목은 사용자 컨펌으로 확정되었다.

| # | 항목 | **확정** | Phase | 근거 요약 |
|---|------|---------|-------|----------|
| 1 | 라우팅 모드 | **SPA only** | Phase 0 | 인증 GUI → SEO 불필요. 백엔드 Python 단일언어 원칙 보존. Single-file/Electron 빌드와 호환. TanStack **Router + Query** 만 사용, **TanStack Start 는 제거** |
| 2 | Electron 데스크탑 | **Phase 12 로 이연** | Phase 12 | 코드사이닝/notarization 비용 ($99~$300/년) 1차 가치 대비 큼. 1차는 PWA "Install to home screen" 만으로 충분. A 의 electron 자산은 의존성 격리되어 후행 통합 쉬움 |
| 3 | Conductor / Swarm 포팅 | **Phase 6 로 이연** | Phase 6 | 8 모듈 Python 재포팅 1~2주. 1차 MVP 의 차단요소 아님. subprocess 우회는 단일언어 원칙 깨므로 비채택 |
| 4 | 단일파일 빌드 트랙 | **Phase 11 로 이연** | Phase 11 | Phase 0~5 안정화 후 추가. 다만 **1차 코드 작성 시 "동적 import 외부 chunk 강제 금지" 원칙은 처음부터 준수** → Phase 11 통합 비용 ↓ |
| 5 | 3D / 아바타 | **feature flag + lazy** | Phase 9 | `VITE_FEATURE_3D=false` 기본. 모바일 자동 2D fallback. 활성화 시에만 `lazy(() => import('./avatar-3d'))` dynamic chunk |
| 6 | 다국어 (i18n) | **영어 + 한국어** | Phase 13 | en + ko 2종 카탈로그가 i18n 인프라 누락 검출 최소단위. zh-CN 은 C 의 README 다국어 패턴만 1차 채택, UI 번역은 커뮤니티 PR |

### 1차 PR 범위 (확정 결정의 자연스러운 귀결)

| Phase | 범위 | 산출물 |
|-------|------|--------|
| **0** | 모노리포 부트스트랩 | pnpm workspace + Vite SPA + Python venv + Hello World + `/api/health` |
| **1** | 인증 + 기본 채팅 | OAuth/Passkey/Password 로그인 + SSE 채팅 1회전 |
| **2** | 세션 라이프사이클 | 세션 5종 + C transcript repair + `/api/session/health` |
| **10** | 배포 인프라 | `bootstrap.py` (C ABI 가드 통합) + `ctl.sh` + 3종 docker-compose + install.sh |

**1차 MVP 정의**: "Self-host → 로그인 → 채팅 → 새로고침/네트워크 단절 후 세션 복구". Phase 3~9, 11~14 는 독립 PR.

### 비-1차 (independent PR) 로 분리되는 Phase

```
Phase 3   워크스페이스 + 파일 + 터미널
Phase 4   스킬 / MCP / 메모리
Phase 5   Tasks / 칸반 / Cron
Phase 6   Conductor + Swarm  ← 확정 #3
Phase 7   헬스 / 대시보드 / 인스펙터
Phase 8   PWA + 모바일
Phase 9   테마 (Glassmorphism 포함) + 3D feature flag  ← 확정 #5
Phase 11  단일파일 빌드 트랙  ← 확정 #4
Phase 12  Electron  ← 확정 #2
Phase 13  i18n (en + ko)  ← 확정 #6
Phase 14  테스트 / CI 자동화
```
