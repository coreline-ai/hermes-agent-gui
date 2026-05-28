# Hermes Agent GUI 안정화·전문 보안 리뷰 보고서

- 리뷰 일자: 2026-05-28 KST
- 대상 브랜치/커밋: `main` / `ffc6c95 fix: close post-merge security hardening gaps`
- 리뷰 모드: 안정화 리뷰 + `security-best-practices` 기반 JS/TS/React/Python stdlib 서버 보안 리뷰
- 범위: `apps/server`, `apps/web`, `electron`, CI/Security workflow, Docker packaging

## 1. Executive Summary

현재 상태는 이전 하드닝 패치 이후 **Critical 급 즉시 차단 이슈는 발견되지 않았고**, 인증·실행 게이트·SSRF/redirect 재검증·프로파일 export secret 제외·CI 테스트 범위가 크게 개선되어 있습니다.

다만 LAN/Docker 공개, Electron 배포, 장기 운영 안정화를 기준으로 보면 아래 항목은 다음 패치 라운드에서 우선 처리하는 것을 권장합니다.

| 우선순위 | ID | 심각도 | 요약 | 권장 처리 |
|---:|---|---|---|---|
| 1 | SEC-01 | High | Profile archive import가 압축 크기만 제한하고 uncompressed 총량/파일 수 제한이 없음 | import 총량·파일 수·member size cap 추가 |
| 2 | SEC-02 | Medium | React `dangerouslySetInnerHTML`가 검색 snippet API 응답을 신뢰 | HTML sink 제거 또는 branded sanitized snippet + sanitizer |
| 3 | SEC-03 | Medium | Electron `shell.openExternal(url)`에 scheme allowlist 없음 | `https:`, `mailto:` 등 allowlist 적용 |
| 4 | SEC-04 | Medium | OAuth/Passkey 쿠키의 `Secure` 처리와 CSRF origin guard가 불일치/부재 | 공통 cookie helper + unsafe method origin guard |
| 5 | STAB-01 | Medium | 여러 API의 정수/base64 입력이 400 대신 500으로 떨어질 수 있음 | 공통 parse/clamp helper + 테스트 추가 |
| 6 | SEC-05 | Low-Med | OAuth token error에 provider raw 응답이 그대로 반환될 수 있음 | raw 제거/레드랙션 |
| 7 | SEC-06 | Low-Med | Passkey 구현이 UP/UV/signCount 검증 없이 최소 구현 상태 | WebAuthn 검증 강화 또는 production 제한 명시 |
| 8 | SEC-07 | Low | CSP `unsafe-inline`, production source map 공개 | CSP 강화, source map env-gate |
| 9 | STAB-02 | Low-Med | Vite build chunk warning: `office` chunk 1MB+ | 3D/office 경로 dynamic import/manualChunks |

## 2. 검증 증거

실행 결과:

```bash
python3 -m pytest -q apps/server
# 150 passed in 44.35s

pnpm --filter @hermes-agent-gui/web typecheck
pnpm --filter @hermes-agent-gui/web lint
pnpm --filter @hermes-agent-gui/web test
pnpm --filter @hermes-agent-gui/web build
# typecheck/lint 통과
# Vitest: 8 files / 20 tests passed
# Vite build 통과, 단 chunk size warning 존재

pnpm audit --prod --json > /tmp/hermes-audit-review.json || true
node scripts/pnpm-audit-gate.cjs /tmp/hermes-audit-review.json
# pnpm audit gate: clean for high+ advisories
# 11 stale/false-positive advisory matches ignored

PYTHONPATH=/tmp/hermes-pip-audit python3 -m pip_audit -r apps/server/requirements.txt
# No known vulnerabilities found
```

현재 검증 기준으로 backend/frontend 핵심 checks는 정상입니다. Docker build/smoke는 이전 하드닝 직후 통과했으나 이번 리뷰 턴에서는 재실행하지 않았습니다. 단, `pnpm audit` 정책은 high+ 기준이며 moderate 이하 advisory는 release policy에 따라 별도 triage가 필요합니다.

## 3. 이미 잘 되어 있는 보안 통제

| 영역 | 관찰 내용 |
|---|---|
| 인증 fail-closed | non-loopback bind에서 인증이 없으면 서버가 종료됨: `apps/server/server.py:280-289` |
| 명령 실행 게이트 | exec 기본 비활성화, remote bind는 `HERMES_GUI_ALLOW_REMOTE_EXEC=1` 추가 요구: `apps/server/api/exec_policy.py:37-52` |
| CLI/Cron/PTY exec 보호 | CLI bridge, cron background runner, PTY 모두 `exec_policy.require_exec`를 통과 |
| SSRF/redirect | Browser fetch와 provider discovery가 redirect target을 재검증: `apps/server/api/browser/actions.py:15-28`, `apps/server/api/providers/discovery.py:77-92` |
| Profile export | `.env*`, key/pem/token류, passkeys/session secret 제외 및 Hermes home allowlist 적용 |
| Cache | API 응답 `Cache-Control: no-store`; PWA는 `/api/*` cache denylist 적용 |
| CI | backend pytest, frontend lint/typecheck/test/build, Docker build+health smoke 포함 |
| Dependency audit | `pip-audit`, `pnpm audit` workflow 존재 |

## 4. 보안 상세 Findings

### SEC-01 — Profile archive import uncompressed expansion DoS

- Severity: High
- Location:
  - `apps/server/api/profile_archive.py:39` — `MAX_ARCHIVE_BYTES = 200 * 1024 * 1024`
  - `apps/server/api/profile_archive.py:340-387` — tar.gz member 전체를 `src.read()` 후 `write_bytes()`
  - `apps/server/api/profile_archive.py:512-531` — 요청 body / base64 payload 제한은 compressed/input 기준
- Evidence:
  - import 경로가 tar.gz 압축 payload 크기는 제한하지만, `tf.getmembers()` 후 각 member를 `src.read()`로 전부 메모리에 올리고 파일에 씁니다.
  - 파일 수, member별 크기, 총 uncompressed bytes 제한이 없습니다.
- Impact:
  - 인증된 사용자가 crafted archive를 업로드하면 메모리/디스크/CPU를 고갈시킬 수 있습니다.
  - LAN/Docker로 공개된 환경에서는 계정 탈취 후 persistence/DoS로 이어질 수 있습니다.
- Fix:
  - `MAX_ARCHIVE_FILES`, `MAX_ARCHIVE_UNCOMPRESSED_BYTES`, `MAX_ARCHIVE_MEMBER_BYTES` 추가.
  - `member.size`를 먼저 검증하고, `src.read()` 대신 chunked copy + running total checksum으로 처리.
  - manifest 자체 크기도 제한.
- Tests:
  - small valid archive 통과.
  - compressed body는 작지만 `member.size`가 cap 초과인 archive 400.
  - 총 member size cap 초과 archive 400.
  - file count cap 초과 archive 400.
- False positive notes:
  - route는 인증 필요라 unauthenticated 공격은 아닙니다. 그래도 import endpoint는 파일 처리 표면이므로 공개 배포 전 필수 하드닝 권장입니다.

### SEC-02 — React `dangerouslySetInnerHTML` 검색 snippet sink

- Severity: Medium 현재는 server-side escaping이 있어 exploit 가능성은 낮음. 단 API 계약이 깨지면 High로 상승.
- Location:
  - Sink: `apps/web/src/components/global-search.tsx:63`
  - Source sanitization: `apps/server/api/sessions/search.py:89-104`
- Evidence:
  - UI가 `result.snippet`을 `dangerouslySetInnerHTML`로 렌더링합니다.
  - 서버 `_snippet()`은 content를 `_escape_html()` 처리 후 검색어에 `<em>`만 삽입합니다.
- Impact:
  - 현재 서버 구현만 보면 XSS는 직접 확인되지 않습니다.
  - 그러나 API 응답이 변경되거나 다른 source가 snippet 필드를 공급하면 React escaping을 우회하는 XSS sink가 됩니다.
  - CSP가 현재 `script-src 'self' 'unsafe-inline'`라 방어 여지도 약합니다.
- Fix:
  - 최선: snippet을 `{ text, highlights }` 구조로 내려 보내고 React component로 `<em>`를 직접 렌더링.
  - 차선: 서버에서 branded sanitized field 명확화 + DOMPurify 등 sanitizer 적용 + 테스트로 `<script>`, `<img onerror>`, `</em>` 회귀 방지.
- Tests:
  - message content `<img src=x onerror=alert(1)> redis` 검색 시 DOM에 event handler가 생기지 않는지 확인.
  - 검색어에 HTML-like 문자가 들어와도 `<em>` 외 markup이 생성되지 않는지 확인.

### SEC-03 — Electron external URL scheme allowlist 미적용

- Severity: Medium
- Location: `electron/main.cjs:151-153`
- Evidence:
  - `setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: 'deny' }; })`
  - scheme/host 검증 없이 OS external opener로 전달합니다.
- Impact:
  - 현재 코드 검색상 `window.open`/외부 target link가 많지는 않지만, 향후 UI/문서/마켓플레이스 링크가 추가되면 `file:`, `javascript:`, custom protocol 등 위험 scheme을 OS에 전달할 수 있습니다.
- Fix:
  - `new URL(url)` parse 후 `https:`, `http:` 필요 시, `mailto:` 정도만 허용.
  - `file:`, `javascript:`, `data:`, unknown custom protocol은 deny 및 log.
  - 가능하면 외부 링크 컴포넌트 계층에서 `rel="noopener noreferrer"`도 강제.
- Tests:
  - `https://example.com` 허용.
  - `javascript:alert(1)`, `file:///etc/passwd`, `vscode://...` deny.

### SEC-04 — Session cookie hardening/CSRF origin guard 불일치

- Severity: Medium for deployed HTTPS/proxy environments, Low for localhost-only
- Location:
  - Login cookie conditional Secure: `apps/server/api/auth.py:151-155`
  - OAuth cookie lacks conditional Secure: `apps/server/api/oauth.py:204-212`
  - Passkey cookie lacks conditional Secure: `apps/server/api/passkeys.py:416-421`
  - Cookie auth path: `apps/server/api/auth.py:76-89`
- Evidence:
  - password login은 `x-forwarded-proto == https`일 때만 `Secure`를 붙입니다.
  - OAuth/passkey success path는 동일 쿠키를 발급하지만 `Secure` 조건 처리가 없습니다.
  - Cookie-authenticated unsafe methods에 대한 공통 `Origin`/`Sec-Fetch-Site` 검증은 보이지 않습니다.
- Impact:
  - HTTPS reverse proxy 환경에서 OAuth/passkey 발급 세션만 `Secure` 누락 가능.
  - SameSite=Lax가 대부분의 cross-site POST를 줄이지만, cookie auth 기반 admin/API 앱은 origin guard가 있으면 방어층이 더 명확합니다.
- Fix:
  - `auth_module.session_cookie_header(req, cfg, cookie, max_age)` 공통 helper 도입.
  - 모든 Set-Cookie에 `HttpOnly; SameSite=Lax; Path=/; Max-Age=...` + HTTPS 감지 시 `Secure` 일관 적용.
  - `POST/PUT/PATCH/DELETE`에 대해 cookie auth 사용 시 `Origin` 또는 `Sec-Fetch-Site`가 cross-site면 403 처리. Bearer token API 호출은 예외 가능.
- Tests:
  - `x-forwarded-proto: https`에서 login/oauth/passkey 모두 `Secure` 포함.
  - cross-site `Origin`으로 unsafe method 호출 시 403.
  - same-origin 또는 no-origin CLI/local request는 기존 동작 유지.

### SEC-05 — OAuth token error raw response disclosure

- Severity: Low-Medium
- Location: `apps/server/api/oauth.py:177-189`
- Evidence:
  - token exchange 후 `access_token`이 없으면 `{"error":"token_response_invalid", "raw": token_resp}`를 반환합니다.
- Impact:
  - provider 에러 응답에 민감한 token-like 필드, debug detail, client metadata가 포함되면 authenticated browser/API caller에게 그대로 노출됩니다.
  - 일반적으로 공격자보다 운영자 노출에 가깝지만, 로그/스크린샷/bug report로 재유출될 수 있습니다.
- Fix:
  - response body에서는 `raw` 제거.
  - 필요 시 allowlist 필드(`error`, `error_description` 최대 길이 제한)만 redaction 후 반환.
  - server log에도 redaction 적용.
- Tests:
  - token endpoint mock이 `{refresh_token:"secret", error:"x"}` 반환 시 API 응답에 secret 미포함.

### SEC-06 — Passkey/WebAuthn production hardening gap

- Severity: Low-Medium, passkey를 production primary auth로 쓰면 Medium
- Location:
  - Registration authData parsing: `apps/server/api/passkeys.py:271-329`
  - Authentication finish: `apps/server/api/passkeys.py:361-421`
- Evidence:
  - rpIdHash, origin, challenge, signature는 검증합니다.
  - 그러나 registration/authentication flags의 UP/User Presence, UV/User Verification 요구 조건과 signCount replay/counter 업데이트가 보이지 않습니다.
  - registration attestationObject CBOR도 heuristic search 기반입니다.
- Impact:
  - 표준 WebAuthn implementation 대비 replay/cloned authenticator 탐지와 user verification enforcement가 약합니다.
- Fix:
  - `authData[32]` flags에서 UP 필수 확인, UV는 policy에 따라 required/preferred 명확화.
  - `signCount` 저장 및 증가 검증. zero-counter authenticator 처리 정책 문서화.
  - 가능하면 검증된 WebAuthn 라이브러리 도입 또는 production passkey feature flag 분리.
- Tests:
  - UP flag unset → 400/401.
  - signCount 감소/동일 counter → 401 또는 warning+deny 정책.
  - valid platform authenticator path 유지.

### SEC-07 — CSP `unsafe-inline` 및 production source map 공개

- Severity: Low-Medium
- Location:
  - CSP: `apps/server/server.py:217-230`
  - Vite source map: `apps/web/vite.config.ts:77-80`
- Evidence:
  - CSP가 `script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';`입니다.
  - production build가 `.map` 파일을 생성하고 정적 서버가 dist 파일을 그대로 제공합니다.
- Impact:
  - XSS가 발생했을 때 CSP 방어력이 약합니다.
  - source map은 코드 구조, 내부 경로, feature flag, endpoint 힌트를 공개합니다. 오픈소스라도 운영 배포에서는 공격자 reconnaissance 비용을 낮춥니다.
- Fix:
  - 우선 `script-src 'self'`로 줄이고 필요한 inline은 nonce/hash 기반으로 전환.
  - style은 Tailwind/Vite 빌드 요구사항 확인 후 가능하면 nonce/hash 또는 `'unsafe-inline'` 유지 사유 문서화.
  - `sourcemap: process.env.HERMES_GUI_PUBLISH_SOURCEMAPS === '1'`처럼 opt-in 처리.
  - static server에서 `.map`을 no-store 또는 404 처리하는 production mode 옵션도 가능.
- Tests:
  - runtime에서 주요 페이지가 CSP violation 없이 로드.
  - default production build에 `.map` 파일 미생성 또는 미서빙.

### SEC-08 — Security workflow가 PR/push 필수 gate가 아님

- Severity: Low-Medium process risk
- Location: `.github/workflows/security.yml:3-7`
- Evidence:
  - security workflow trigger가 schedule + workflow_dispatch만 있습니다.
  - CI workflow에는 dependency audit gate가 없습니다.
- Impact:
  - 취약 dependency가 main으로 들어간 뒤 주간 job에서 늦게 발견될 수 있습니다.
- Fix:
  - 최소한 `pull_request` 또는 `push: main`에도 high+ audit gate를 실행.
  - 또는 CI workflow에 `pnpm audit gate`와 `pip-audit` job을 추가하고 required checks로 지정.

## 5. 안정화 상세 Findings

### STAB-01 — 입력 parsing 오류가 400 대신 500으로 떨어지는 경로

- Severity: Medium stability / Low security
- Location:
  - PTY base64: `apps/server/api/pty.py:234-240`
  - PTY resize int: `apps/server/api/pty.py:264-266`
  - dashboard logs lines: `apps/server/api/dashboard.py:179-185`
  - brain query depth: `apps/server/api/brain/routes.py:37-39`
  - sessions search limit: `apps/server/api/sessions/search.py:147-149`
  - memory search k: `apps/server/api/compression/routes.py:61-64`
- Evidence:
  - `int(...)`와 `base64.b64decode(...)`가 route 내부에서 validation wrapper 없이 호출됩니다.
  - server boundary가 exception을 잡아 500을 반환하므로 process crash는 아니지만, 사용자 입력 오류가 내부 오류로 기록됩니다.
- Impact:
  - 잘못된 입력이 500과 exception log를 유발해 운영 noise를 늘립니다.
  - 큰 `rows/cols/depth/k/lines` 값은 비정상 리소스 사용을 만들 수 있습니다.
- Fix:
  - `parse_int(value, default, min, max)` 공통 helper.
  - PTY b64는 `base64.b64decode(b64, validate=True)` + `binascii.Error` 처리.
  - terminal rows/cols clamp 예: cols 20-300, rows 5-100.
  - `lines`, `depth`, `k`, `limit`도 endpoint별 cap.
- Tests:
  - malformed `b64` → 400.
  - `cols=abc`, `rows=-1`, extremely large → 400 또는 clamped OK.
  - `limit=abc`, `k=abc`, `depth=abc`, `lines=abc` → 400.

### STAB-02 — Frontend build chunk size warning

- Severity: Low-Medium performance/stability
- Evidence:
  - Vite build output: `office-BNOUfdgB.js 1,078.22 kB`, `usage-DACGIe60.js 371.79 kB`, root `index-DwYQioHi.js 353.79 kB`.
  - Vite warning: `Some chunks are larger than 500 kB after minification`.
- Impact:
  - 느린 네트워크/저사양 환경에서 initial/route load 지연.
  - Electron packaged app에서도 cold start 체감 지연 가능.
- Fix:
  - 3D/office feature는 `VITE_FEATURE_3D`가 off일 때 heavy deps가 main route graph에 묶이지 않게 lazy import 확인.
  - `manualChunks`로 `three`, `@react-three/*`, `recharts`, router/query vendor 분리.
  - route-level dynamic import가 실제 chunk boundary를 만드는지 bundle analyzer로 확인.
- Tests:
  - default build에서 >500KB chunk 없음 또는 warning budget을 문서화.
  - 3D feature off 상태에서 three 관련 chunk가 office route 진입 전 load되지 않음.

### STAB-03 — Swarm worker role이 path/session identifier에 직접 사용됨

- Severity: Low when exec disabled by default; Medium if remote exec intentionally enabled
- Location: `apps/server/api/swarm/foundation.py:62-79`, `apps/server/api/swarm/routes.py:48-52`
- Evidence:
  - `role`이 `SWARM_DIR / f"{role}-{wid}.log"`, tmux session name `hermes-{role}-{wid}`에 직접 사용됩니다.
  - route는 exec gate로 보호되지만 role 자체 slug validation은 없습니다.
- Impact:
  - exec enabled 사용자는 이미 명령 실행 권한이 있으나, path traversal/invalid tmux session name으로 예측 불가능한 파일 생성/실패를 만들 수 있습니다.
- Fix:
  - `role_slug = re.sub(r"[^a-zA-Z0-9_.-]", "-", role)[:64]` 같은 slug helper.
  - log path는 resolve 후 `relative_to(SWARM_DIR)` 확인.
- Tests:
  - role `../../tmp/x`가 log path escape를 만들지 않음.
  - long/space/unicode role도 stable slug로 처리.

## 6. 권장 패치 순서

1. **Archive import cap 패치**: uncompressed 총량·파일 수·member size 제한 + chunked checksum copy.
2. **입력 validation 공통화**: PTY/dashboard/brain/search/memory numeric/base64 parsing 400화.
3. **Cookie/CSRF 공통 helper**: login/oauth/passkey Set-Cookie 통일 + unsafe method origin guard.
4. **React snippet sink 제거**: `dangerouslySetInnerHTML` 제거 또는 sanitizer/branded type 도입.
5. **Electron external URL allowlist**: `shell.openExternal` scheme 제한.
6. **OAuth error redaction**: token response raw 제거.
7. **CSP/source map hardening**: source map opt-in, CSP inline 제거 계획.
8. **Passkey hardening**: UP/UV/signCount 및 CBOR 검증 개선.
9. **Bundle split**: 3D/office/vendor manualChunks 및 lazy import 확인.
10. **Security workflow PR gate**: high+ audit를 PR/main 필수 체크에 포함.

## 7. 결론

- 현재 main은 테스트와 high+ dependency audit 기준으로는 안정적입니다.
- 공개/LAN 배포 전에는 SEC-01, SEC-03, SEC-04, STAB-01을 우선 패치하는 것이 안전합니다.
- XSS 방어 관점에서는 SEC-02와 SEC-07을 함께 처리해야 CSP와 React sink가 같은 방향으로 강화됩니다.
