# Hermes Agent GUI — 통합 UI 리뷰 개요

> 본 문서 세트는 **NousResearch/hermes-agent** 를 GUI로 확장한 3종의 오픈소스 프로젝트를
> 코드 레벨에서 상세 분석한 1차 리뷰 결과물이다.
> 분석 일자: **2026-05-25**

---

## 분석 대상

| # | Repository | Lang | ⭐ Stars | License | Last Push | 정체성 |
|---|-----------|------|--------|---------|-----------|--------|
| **Base** | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | Python | 166,436 | MIT | 2026-05-25 | Hermes Agent 본체 (gateway, mcp, providers, skills, tools, ui-tui, web) |
| **A** | [outsourc-e/hermes-workspace](https://github.com/outsourc-e/hermes-workspace) | TS/JS | 4,837 | MIT | 2026-05-24 | React 19 + Electron 데스크탑/웹 워크스페이스 |
| **B** | [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui) | Python | 8,587 | MIT | 2026-05-25 | Python stdlib 서버 + Vanilla JS PWA |
| **C** | [pyrate-llama/hermes-ui](https://github.com/pyrate-llama/hermes-ui) | HTML | 142 | MIT | 2026-05-22 | 단일 HTML(React 18 + Babel) + Python stdlib 프록시 |

## 리뷰 문서 구성

| 파일 | 내용 |
|------|------|
| [`00-overview.md`](./00-overview.md) | 본 문서 — 메타 정보 + 결론 요약 |
| [`01-hermes-workspace.md`](./01-hermes-workspace.md) | A 코드 레벨 상세 분석 |
| [`02-hermes-webui.md`](./02-hermes-webui.md) | B 코드 레벨 상세 분석 |
| [`03-hermes-ui.md`](./03-hermes-ui.md) | C 코드 레벨 상세 분석 |
| [`04-feature-matrix.md`](./04-feature-matrix.md) | 기능별 3종 비교 매트릭스 |
| [`05-conflict-resolution.md`](./05-conflict-resolution.md) | 중복 기능 충돌 해소 결정표 |
| [`06-integration-design.md`](./06-integration-design.md) | 통합 신규 UI 아키텍처/구현안 |

---

## TL;DR — 결론 요약

### 각 프로젝트의 강점 (best-of-breed)

- **A · hermes-workspace** → **프론트엔드 아키텍처의 표준**
  React 19 + TanStack Router/Query + Tailwind v4 + Vite + Electron. 100+ 컴포넌트, Monaco·xterm.js·three.js 까지 풀스택 UI 자산. Swarm/Conductor 멀티에이전트 컨트롤플레인은 유일.

- **B · hermes-webui** → **백엔드/서버 능력의 표준**
  순수 Python stdlib(`pyyaml`+`cryptography` 외 의존성 없음). 40+ API 모듈(OAuth, Passkeys, 세션 라이프사이클/복구, 칸반 브리지, 메트로닝, 워크트리). PWA + 서비스워커. `ctl.sh` 데몬 래퍼.

- **C · hermes-ui** → **단일파일 배포 철학의 표준**
  `hermes-ui.html` 621KB 단일 React SPA + `serve_lite.py` stdlib 프록시. Glassmorphism 디자인. Tailscale 친화. 트랜스크립트 복구/세션 헬스 체크 로직이 가장 실전 검증됨(v3.3.x 패치 히스토리).

### 통합 신규 UI 결정 (요약)

| 영역 | 채택 | 근거 |
|------|-----|------|
| 프론트엔드 프레임워크 | **A** (React 19 + TanStack) | TS, 파일기반 라우팅, SSR-가능. B의 vanilla JS는 확장성↓, C의 Babel-CDN은 코드 스플릿 불가 |
| 백엔드 / API | **B** (Python stdlib) | 가장 깊은 서버 기능. Hermes Agent 호환성↑. 외부 의존성 최소 |
| 단일파일 fallback | **C** 철학 | `vite-plugin-singlefile` 로 옵션 빌드 모드 유지 |
| 인증 | **B** (OAuth + Passkeys + Password) | 가장 견고. A의 미들웨어 + B 인증 스택 결합 |
| 터미널 | **A** (xterm.js + 탭) | full PTY + addons + C의 멀티탭 패턴 |
| 코드 에디터 | **A** (Monaco) | 표준 |
| 세션 복구 / 헬스 | **C 로직** + **B `/api/session/health`** | 두 프로젝트 모두 실전 검증된 부분 결합 |
| 칸반/Tasks | **A UI** + **B 백엔드** | Conductor missions + kanban_bridge |
| Cron | **A UI** + **B 실행기** | cron-manager + cron_runner |
| Skills/MCP | **A** | 카탈로그/마켓플레이스가 가장 성숙 |
| PWA / 모바일 | **B** (manifest + sw.js) → vite-plugin-pwa 로 재구성 |
| Swarm / Conductor | **A** (유일) |
| 3D / 아바타 | **A** (선택적) | feature flag 로 lazy 로드 |
| 테마 | **A** 5개 + **C** Glassmorphism = 6개 |
| Docker / Daemon | **B** (`ctl.sh` + 3종 compose) |
| Electron 데스크탑 | **A** (선택적) |

상세 결정 근거는 [`05-conflict-resolution.md`](./05-conflict-resolution.md) 참조.

---

## 신규 프로젝트 구조 제안

```
hermes-agent-gui/
├── docs/
│   ├── review/           ← 본 리뷰 문서
│   └── architecture/
├── apps/
│   ├── server/           ← Python stdlib 백엔드 (B의 api/ 포팅)
│   └── web/              ← React 19 + Vite (A 포팅)
├── packages/
│   ├── ui/               ← A의 components/ui/ + C의 glassmorphism 토큰
│   ├── gateway-client/   ← A의 gateway-api.ts + B의 runtime_adapter.py
│   └── single-file/      ← vite-plugin-singlefile 빌드 타깃 (C 모드)
├── electron/             ← A의 Electron 패키징 (옵션)
└── scripts/
    └── ctl.sh            ← B의 데몬 래퍼
```

상세 다이어그램과 phase 별 구현은 [`06-integration-design.md`](./06-integration-design.md) 참조.

---

## 확정 결정 (2026-05-25)

6개 비-결정 사항이 모두 확정되었다 (상세는 [`05-conflict-resolution.md`](./05-conflict-resolution.md) 참조).

| # | 항목 | 확정 |
|---|------|-----|
| 1 | 라우팅 모드 | **SPA only** (TanStack Start 제거) |
| 2 | Electron 데스크탑 | **Phase 12 로 이연** |
| 3 | Conductor / Swarm 포팅 | **Phase 6 로 이연** |
| 4 | 단일파일 빌드 | **Phase 11 로 이연** |
| 5 | 3D / 아바타 | **feature flag + lazy chunk** |
| 6 | 다국어 | **영어 + 한국어** (1차 2종) |

### 1차 PR 범위

**Phase 0 + 1 + 2 + 10** = "Self-host → 로그인 → 채팅 → 세션 복구" MVP.

| Phase | 범위 |
|-------|------|
| 0 | 모노리포 부트스트랩 + Vite SPA + Python `/api/health` |
| 1 | 인증 (OAuth/Passkey/Password) + SSE 채팅 |
| 2 | 세션 5종 + transcript repair + `/api/session/health` |
| 10 | bootstrap.py + ctl.sh + 3종 docker-compose + install.sh |

나머지 Phase 3~9, 11~14 는 독립 PR.

---

## 다음 단계

✅ Phase 0 부트스트랩 진행 중 — [`07-phase-0-checklist.md`](./07-phase-0-checklist.md) 참조
