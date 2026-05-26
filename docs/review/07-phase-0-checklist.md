# 07 · Phase 0 — 모노리포 부트스트랩 체크리스트

> **목표**: pnpm 워크스페이스 + Vite SPA + Python 백엔드 골격을 만든다.
> 산출물: `pnpm dev` 로 React Hello World, `python3 apps/server/server.py` 로 `/api/health` 응답.
> 확정 결정 적용: SPA only · TanStack Start 없음 · 단일파일/Electron/Swarm/3D 모두 후행 phase.

---

## 파일 인벤토리 (Phase 0 최종)

```
hermes-agent-gui/
├── package.json                    # 루트 (pnpm workspace)
├── pnpm-workspace.yaml
├── .gitignore
├── .editorconfig
├── README.md
├── LICENSE                         # MIT
├── NOTICE                          # 3개 upstream 출처 명시
├── docs/
│   ├── review/                     # 본 리뷰 세트 (이미 있음)
│   └── architecture/               # 후행
├── apps/
│   ├── web/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── vite.config.ts
│   │   ├── index.html
│   │   ├── postcss.config.cjs
│   │   ├── tailwind.config.ts      # Tailwind v4 토큰
│   │   └── src/
│   │       ├── main.tsx            # 엔트리
│   │       ├── router.tsx          # TanStack Router
│   │       ├── routes/
│   │       │   ├── __root.tsx      # 루트 레이아웃
│   │       │   └── index.tsx       # / Hello World
│   │       ├── lib/
│   │       │   └── api.ts          # `/api/health` 호출
│   │       └── styles/
│   │           └── globals.css     # Tailwind directives
│   └── server/
│       ├── server.py               # thin shell, http.server
│       ├── requirements.txt        # pyyaml, cryptography (Phase 1 부터 사용)
│       ├── pytest.ini
│       ├── bootstrap.py            # 진입점 (Phase 0 minimal)
│       └── api/
│           ├── __init__.py
│           └── health.py           # GET /api/health
└── scripts/
    └── ctl.sh                      # Phase 10 에서 채울 stub (헤더만)
```

---

## 체크리스트

### ▸ 루트 모노리포
- [ ] `package.json` (workspaces: apps/*, packages/*)
- [ ] `pnpm-workspace.yaml`
- [ ] `.gitignore` (node_modules, dist, .venv, .DS_Store, *.pyc)
- [ ] `.editorconfig`
- [ ] `README.md` (한 줄 소개 + 빠른 시작 + 리뷰 문서 링크)
- [ ] `LICENSE` (MIT)
- [ ] `NOTICE` (NousResearch/hermes-agent + outsourc-e/hermes-workspace + nesquena/hermes-webui + pyrate-llama/hermes-ui)

### ▸ apps/web (Vite + React 19 + TanStack Router + Tailwind v4)
- [ ] `apps/web/package.json` (react 19, @tanstack/react-router, @tanstack/react-query, zustand, tailwindcss v4, vite, typescript)
- [ ] `apps/web/tsconfig.json` (strict, ES2022, paths alias `@/*` → `src/*`)
- [ ] `apps/web/vite.config.ts` (react, tailwind, dev proxy `/api → http://127.0.0.1:8800`)
- [ ] `apps/web/index.html`
- [ ] `apps/web/postcss.config.cjs`
- [ ] `apps/web/tailwind.config.ts`
- [ ] `apps/web/src/main.tsx` (createRoot, RouterProvider)
- [ ] `apps/web/src/router.tsx` (createRouter)
- [ ] `apps/web/src/routes/__root.tsx` (Outlet + 기본 레이아웃)
- [ ] `apps/web/src/routes/index.tsx` (Hello World + health probe 상태 표시)
- [ ] `apps/web/src/lib/api.ts` (fetch wrapper)
- [ ] `apps/web/src/styles/globals.css` (Tailwind v4 imports)

### ▸ apps/server (Python stdlib)
- [ ] `apps/server/server.py` (BaseHTTPRequestHandler, 라우팅 디스패처)
- [ ] `apps/server/requirements.txt` (주석만 — Phase 0 는 stdlib 만)
- [ ] `apps/server/pytest.ini`
- [ ] `apps/server/bootstrap.py` (venv 감지 + 인터프리터 ABI sanity check stub — C 패턴, 최소형)
- [ ] `apps/server/api/__init__.py`
- [ ] `apps/server/api/health.py` (`get_health()` returns dict)

### ▸ scripts
- [ ] `scripts/ctl.sh` (헤더 + TODO 마커만 — Phase 10 채움)

---

## 검증

Phase 0 가 끝났을 때 다음이 동작해야 한다:

```bash
# 백엔드
cd apps/server
python3 server.py --port 8800
# → 콘솔: "[hermes-agent-gui] listening on http://127.0.0.1:8800"

# 다른 터미널 — 프론트
cd apps/web
pnpm install
pnpm dev
# → http://localhost:5173 에서 Hello World + "API: healthy" 배지

# 직접 헬스 체크
curl http://127.0.0.1:8800/api/health
# → {"status":"ok","version":"0.1.0-phase-0"}
```

## Phase 0 의 의도적 제약

- **테스트 인프라 없음** — Phase 14 에서 일괄 추가
- **인증 없음** — Phase 1 에서 추가
- **세션 없음** — Phase 2
- **PWA / Service Worker 없음** — Phase 8
- **Docker 없음** — Phase 10
- **i18n 인프라 없음** — Phase 13. 다만 Phase 0 의 텍스트는 `t('...')` 대신 직접 작성해도 OK (Phase 13 에서 일괄 마이그레이션)
- **`packages/` 디렉토리 미생성** — 공유 패키지가 실제로 필요해질 때(Phase 2~3) 만들기

---

## 다음 액션

Phase 0 완료 → Phase 1 (인증 + 기본 채팅).
Phase 1 시작 시 `apps/server/api/auth.py`, `oauth.py`, `passkeys.py` (B 포팅) 와 `apps/web/src/routes/login.tsx` 추가.
