# 04 · 기능별 3종 비교 매트릭스

> 범례
> - ✓✓ = 본 카테고리의 최강자
> - ✓  = 구현은 있으나 보강 필요
> - 〜 = 부분/제한 구현
> - ✗  = 없음

## 1. 스택 / 빌드

| 항목 | A · hermes-workspace | B · hermes-webui | C · hermes-ui |
|------|----------------------|------------------|----------------|
| 프론트 프레임워크 | React 19 + TanStack Router/Query | Vanilla JS | React 18 + Babel standalone |
| 빌드 도구 | Vite + Electron + esbuild | 없음 (no build) | 없음 (no build, Babel CDN) |
| TypeScript | ✓✓ (전면) | ✗ | ✗ |
| 패키지 매니저 | pnpm | pip | pip |
| 백엔드 언어 | TypeScript (Node ≥22) | Python (stdlib) | Python (stdlib) |
| 외부 의존성 | 80+ npm 패키지 | pyyaml + cryptography | **0개** |
| 진입 명령 | `pnpm dev` | `python3 bootstrap.py` 또는 `./start.sh` | `python3 serve_lite.py` |
| 데스크탑 빌드 | Electron (.dmg/.exe) | ✗ | ✗ |
| 단일 HTML 빌드 | ✗ | ✗ | ✓✓ (621KB) |
| PWA | ✓ | ✓✓ (sw.js + manifest) | ✗ |
| Docker | ✓ (compose dev+prod) | ✓✓ (1/2/3-컨테이너) | ✗ |
| Nix flake | ✓ | ✗ | ✗ |
| CI workflows | 3 (ci/docker/security) | 4 (tests/docker-smoke/win/release) | ✗ |

## 2. UI / UX

| 항목 | A | B | C |
|------|---|---|---|
| 레이아웃 | 가변 (싱크 가능 패널) | 3-panel 고정 (left/center/right + footer) | 가변 (사이드바 + 메인) |
| 테마 수 | ✓✓ 5종 (Hermes/Nous/Bronze/Slate/Mono × light/dark) | 〜 light/dark | ✓ Glassmorphism (라이트 + Dawn 등) |
| 모바일 우선 | 〜 `mobile-*` 컴포넌트 별도 | ✓✓ 3-panel 가 모바일 적응 + PWA + 햅틱 | 〜 (반응형) |
| 컴포넌트 라이브러리 | Base UI (Radix 후속) | 수기 (CSS) | 수기 (CSS, glass utilities) |
| 아이콘 | HugeIcons + Lobehub | 수기 SVG (`icons.js`) | 수기 |
| 다국어 (i18n) | ✓ `lib/i18n.ts` | ✓ `static/i18n.js` | 〜 (zh-CN README만) |
| 키보드 단축키 | ✓✓ command-palette + global-shortcut | 〜 | 〜 |
| 명령 팔레트 | ✓ `command-palette.tsx` | ✗ | ✗ |
| 애니메이션 | ✓ framer-motion + motion | 〜 CSS | 〜 |
| 음성 입력 (STT) | ✓ `use-voice-input` + `use-voice-recorder` + stt-* | ✗ | ✗ |
| 햅틱 | ✓ `lib/haptics.ts` | 〜 | ✗ |
| 사운드 | ✓ `lib/sounds.ts` | ✗ | ✗ |
| 온보딩 마법사 | ✓ react-joyride | ✓✓ `bootstrap.py` + 첫-실행 마법사 | ✗ |

## 3. 채팅

| 항목 | A | B | C |
|------|---|---|---|
| SSE 스트리밍 | ✓ | ✓ | ✓ |
| 멀티 세션 | ✓ | ✓ | ✓ |
| 마크다운 렌더 | ✓ react-markdown + gfm + breaks + raw + sanitize | ✓ 수기 | ✓ react-markdown 추정 |
| 코드 하이라이트 | ✓✓ shiki (VSCode 동급) | ✓ 수기 | ✓ |
| 슬래시 명령 | ✓ `slash-command-menu` | ✓ commands.js | ✓ |
| 도구 호출 카드 | ✓ | ✓ | ✓ |
| 인라인 이미지 생성 | 〜 | ✗ | ✓✓ (스크린샷 명시) |
| 인라인 비디오 업로드 | 〜 | 〜 | ✓✓ (v3.3.9) |
| 파일 첨부 | ✓ attachment-button/preview | ✓ upload.py | ✓ |
| 컨텍스트 미터 | ✓✓ `context-meter` + composer ring | ✓✓ circular context ring | ✓ |
| 컴포저 footer | 〜 | ✓✓ model/profile/workspace 토글 + ring | ✓ |
| Compose work banner | ✗ | ✗ | ✓✓ (v3.3.2) |
| Tool honesty guard | ✗ | ✗ | ✓✓ (v3.3.2) |

## 4. 세션 관리

| 항목 | A | B | C |
|------|---|---|---|
| 세션 라이프사이클 | ✓ `local-session-store` + `run-store` | ✓✓ 5종 모듈 (`agent_sessions`/`events`/`lifecycle`/`ops`/`recovery`) | ✓ in-memory + ui-conversations.json |
| 세션 복구 (drift repair) | 〜 | ✓ `session_recovery.py` | ✓✓ 브라우저↔서버 transcript drift 복구 (v3.3.4~3.3.11) |
| `/api/session/health` | 〜 | ✓ | ✓✓ (server/browser/compact counts) |
| Compression session alias | ✗ | 〜 | ✓✓ (v3.3.1, 재시작 후에도 유지) |
| Tool evidence repair | ✗ | 〜 | ✓✓ (v3.3.5~3.3.7) |
| Profile-scoped 필터 | ✓ | ✓✓ `profiles.py:_profiles_match` | ✗ |
| 사이드바 고정 | ✓ `use-pinned-sessions` | ✓ (별표) | ✓ (별표) |

## 5. 워크스페이스 / 파일

| 항목 | A | B | C |
|------|---|---|---|
| 파일 브라우저 | ✓✓ `file-explorer` + Monaco | ✓ `workspace.js` + 인라인 미리보기 | ✓ 인라인 미리보기 |
| 코드 에디터 | ✓✓ Monaco | 〜 plain text | 〜 plain text |
| Git 통합 | ✓ via dashboard | ✓✓ `workspace_git.py`, `worktrees.py` | ✗ |
| 워크스페이스 picker | ✓ | ✓ | ✓✓ (화이트리스트 + Windows 드라이브 + OneDrive) |
| Path traversal 가드 | ✓ | ✓ | ✓✓ `_path_is_within_any` |

## 6. 터미널

| 항목 | A | B | C |
|------|---|---|---|
| 라이브러리 | ✓✓ xterm.js 5 + addons (fit/search/web-links) | 〜 수기 `terminal.js` | 〜 수기 |
| PTY | ✓✓ Node + `pty-helper.py` 크로스플랫폼 | ✓ Python | ✓ Python |
| 멀티탭 | ✓ | ✗ | ✓✓ Hermes / Claude Code 분리 탭 |
| 검색 | ✓ addon | ✗ | ✗ |
| 웹 링크 | ✓ addon | ✗ | ✗ |

## 7. 스킬 / MCP

| 항목 | A | B | C |
|------|---|---|---|
| 스킬 브라우저 | ✓✓ 2000+ 카탈로그 + 필터 + 마켓플레이스 | ✓ 자가-개선 (Hermes 가 스킬 작성/저장) | ✓ 브라우저 |
| MCP 카탈로그 | ✓✓ `/mcp` 페이지 (catalog + marketplace + sources) | ✓ `extensions.py` | ✓ MCP tools 그룹 |
| MCP CLI 브리지 | ✓ `mcp-cli-bridge.ts` | 〜 | 〜 |
| MCP 입력 검증 | ✓ `mcp-input-validate.ts` | 〜 | 〜 |
| MCP 프리셋 | ✓ `mcp-presets-store.ts` | 〜 | 〜 |

## 8. 메모리

| 항목 | A | B | C |
|------|---|---|---|
| 메모리 뷰어 | ✓ `memory-viewer/` + 마크다운 라이브 에디터 | ✓ 텍스트 뷰 | ✓ 인스펙션 |
| 메모리 검색 | ✓ | 〜 | 〜 |
| 메모리 브라우저 API | ✓ `memory-browser.ts` | ✓ `agent_sessions` 일부 | 〜 |

## 9. 작업 / 칸반 / Cron

| 항목 | A | B | C |
|------|---|---|---|
| 칸반 보드 | ✓✓ `kanban-backend` + `swarm-kanban-store` + Conductor 미션 보드 | ✓ `kanban_bridge.py` | ✓ Tasks (active + background) |
| 백로그 / 레인 | ✓ backlog/ready/running/review/blocked/done | ✓ | ✓ active/needs-you/done |
| 작업 만료 (aging) | ✗ | ✗ | ✓✓ Done 2h / Needs-you 12h |
| Cron 잡 UI | ✓ `cron-manager/` | ✓ | ✓ 편집/pause/run-now |
| Cron 잡 백엔드 | ✓ `hermes-cron-profiles` | ✓✓ `_RUNNING_CRON_JOBS` 트래킹 | ✓ |
| 자가-호스팅 스케줄 | ✓ | ✓✓ (Telegram/Discord/Slack/Signal 알림) | ✓ |

## 10. 멀티 에이전트 / Conductor / Swarm

| 항목 | A | B | C |
|------|---|---|---|
| Conductor (mission dispatch + decomposition) | ✓✓ 유일 | ✗ | ✗ |
| Native swarm fallback | ✓ | ✗ | ✗ |
| 영구 tmux 워커 | ✓✓ swarm-foundation/lifecycle/missions | ✗ | ✗ |
| Role-based 라우팅 | ✓ builder/reviewer/docs/research/ops/triage/QA/lab | ✗ | ✗ |
| Agent View 패널 | ✓ | ✗ | ✗ |
| Swarm Kanban 보드 | ✓ | ✗ | ✗ |

## 11. 운영 / 헬스

| 항목 | A | B | C |
|------|---|---|---|
| 대시보드 | ✓✓ aggregator (sessions/cost/attention) | ✓ | ✓ live stats |
| 인스펙터 | ✓ `inspector/` | 〜 | ✓ |
| Health 화면 | 〜 | ✓ `agent_health` + `system_health` + `dashboard_probe` + `gateway_watcher` | ✓✓ heartbeat + agent/model/provider + redacted logs |
| 업데이트 알림 | ✓ `update-center-notifier` | ✓ `updates.py` | ✓ |
| 사용량/비용 미터 | ✓ `usage-meter` | ✓ `metering.py`, `usage.py` | 〜 |
| 백그라운드 워커 | 〜 | ✓ `background.py` | ✓ task follow-up |

## 12. 인증 / 보안

| 항목 | A | B | C |
|------|---|---|---|
| Auth middleware | ✓✓ `auth-middleware.ts` (테스트 포함) | ✓✓ `api/auth.py` | ✓ HMAC 쿠키 |
| Password | ✓ | ✓ `HERMES_WEBUI_PASSWORD` | ✓ `HERMES_UI_PASSWORD` |
| OAuth | 〜 | ✓✓ `api/oauth.py` | ✗ |
| Passkeys / WebAuthn | ✗ | ✓✓ `api/passkeys.py` + cryptography | ✗ |
| Gateway 토큰 (API_SERVER_KEY) | ✓ `HERMES_API_TOKEN` | ✓ | 〜 |
| CSP | ✓ (README 명시) | ✓✓ CSP report endpoint + rate limit | ✓ |
| Path traversal 가드 | ✓ | ✓ | ✓✓ |
| Fail-closed remote bind | ✓ (README 명시) | ✓ (외부 노출 시 password 필수) | 〜 |
| Rate limit | ✓ `rate-limit.ts` | ✓✓ CSP/client-event 별도 윈도우 | 〜 |
| Log redaction | 〜 | 〜 | ✓✓ (UI 노출 로그 토큰/키 redact) |

## 13. 데스크탑 / 모바일 / 네트워크

| 항목 | A | B | C |
|------|---|---|---|
| Electron 데스크탑 | ✓✓ | ✗ | ✗ |
| PWA 설치 가능 | ✓ | ✓✓ | ✗ |
| Service Worker | ✓ | ✓✓ `sw.js` (캐싱 + offline) | ✗ |
| Tailscale / LAN | ✓ (URL override 설정) | ✓✓ SSE half-close 정상 처리 | ✓ Tailscale 토픽 명시 |
| SSH 터널 access | ✓ | ✓✓ (CLI 패리티 + 1-cmd start) | ✓ |
| Windows 네이티브 | ✓ | 〜 (커뮤니티 가이드 별도) | ✓ 드라이브 letter 스캔 |

## 14. 테스트 / 품질

| 항목 | A | B | C |
|------|---|---|---|
| 유닛 테스트 | ✓ vitest + RTL | ✓ pytest | 〜 |
| E2E 테스트 | ✓ playwright | ✗ | ✗ |
| 타입 시스템 | ✓✓ TS 5.7 strict | ✗ | ✗ |
| 린트 | ✓ eslint + prettier | 〜 | 〜 |
| 보안 워크플로 | ✓ `security.yml` | 〜 | ✗ |

## 15. 운영 자동화

| 항목 | A | B | C |
|------|---|---|---|
| 설치 자동화 | one-line `install.sh` | ✓✓ `bootstrap.py` (Agent 자동 설치) | 수동 git clone |
| 데몬 lifecycle | ✗ (Electron 자체) | ✓✓ `ctl.sh start/status/logs/restart/stop` | 〜 |
| Docker multi-arch | ✓ amd64+arm64 | ✓✓ GHCR amd64+arm64 | ✗ |
| Compose 변형 | 2 (dev/prod) | 3 (1/2/3-컨테이너) | ✗ |
| WSL2 자동 시작 | ✗ | ✓ `docs/wsl-autostart.md` | ✗ |
| 인터프리터 ABI 가드 | ✗ | 〜 | ✓✓ venv 미스매치 자동 re-exec |

---

## 카테고리별 우승자 요약

| 카테고리 | 1위 |
|---------|-----|
| 프론트엔드 아키텍처 / 컴포넌트 깊이 | **A** |
| 백엔드 API / 세션 모델 | **B** |
| 세션 복구 / Transcript repair | **C** |
| 코드 에디터 + 터미널 | **A** |
| 스킬 / MCP UI | **A** |
| Conductor / Swarm 멀티에이전트 | **A** (유일) |
| 인증 (OAuth/Passkey) | **B** |
| PWA / Service Worker | **B** |
| 단일파일 배포 / Glassmorphism | **C** |
| Docker / 데몬 운영 | **B** |
| Electron 데스크탑 | **A** (유일) |
| 모바일 첫 SSE 안정성 | **B** |
| ABI/환경 가드 | **C** |

→ 통합 결정 매트릭스는 [`05-conflict-resolution.md`](./05-conflict-resolution.md) 으로 이어진다.
