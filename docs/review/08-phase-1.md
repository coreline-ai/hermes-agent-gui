# 08 · Phase 1 — 인증 + 기본 SSE 채팅

> **목표**: 사용자가 로그인하고, 채팅 한 회전을 SSE 스트리밍으로 주고받는다.
> Hermes Agent 가 설치/실행 중이면 실제 호출, 아니면 명확한 503 응답.
> (dev 환경에서 `HERMES_GUI_FAKE_BACKEND=echo` 로 에코 모드 사용 가능.)

---

## 결정 (Phase 1 범위 안에서)

### 인증 — 1차 우선순위 재조정

`05` 의 매트릭스는 OAuth + Passkey + Password 3종을 1차에 포함하도록 적혀 있으나, **현실적 1차 범위**로 다음과 같이 조정한다:

| 인증 수단 | Phase 1 | 후행 |
|----------|---------|------|
| **Password (HMAC 쿠키)** | ✅ 완전 구현 | — |
| **Bearer Token** (`Authorization: Bearer …`) | ✅ 완전 구현 | — |
| **OAuth** | 🟡 라우트 스캐폴드 (501) | 별도 phase 에서 채움 |
| **Passkey / WebAuthn** | 🟡 라우트 스캐폴드 (501) | 별도 phase 에서 채움 |

**근거**:
- OAuth 는 provider 별 client_id/secret + 콜백 URL 등록이 필요 → 라이브 서비스 의존성
- Passkey 는 cryptography 기반 WebAuthn 구현 + relying-party 등록 + 디바이스 테스트 필요
- 1차 MVP "self-host → 로그인 → 채팅" 에는 Password + Token 만으로 충분
- B(`hermes-webui`) 의 인증 모듈 3종은 패키지 분할이 잘 되어 있어 후행 phase 에서 *덧붙이는* 비용 작음

### Hermes Agent 연결 어댑터 — 3 모드

`api/runtime_adapter.py` 가 다음 우선순위로 백엔드를 선택:

```
1. HERMES_GUI_FAKE_BACKEND=echo    → EchoAdapter (dev 테스트용, Agent 없이 SSE 파이프라인 검증)
2. HERMES_API_URL                  → GatewayAdapter (A 의 zero-fork 모드)
3. ~/.hermes/hermes-agent 존재     → EmbeddedAdapter (C 의 직접 import 모드)
4. 위 어느 것도 아님                → 503 ("Hermes Agent not configured")
```

Phase 1 에서는 **EchoAdapter** 와 **GatewayAdapter** 두 개를 실제 동작시키고, EmbeddedAdapter 는 stub (Phase 2 에서 충실히 구현).

### SSE 이벤트 스키마

```
event: token
data: {"text":"부분 문자열"}

event: token
data: {"text":"다음 청크"}

event: done
data: {"session_id":"<id>","turn_id":"<id>"}
```

B 의 `streaming.py` 와 동일하게:
- `BrokenPipeError` / `ConnectionResetError` / `TimeoutError` 는 정상 disconnect 로 처리 (Tailscale/모바일 대응)
- 헤더 `X-Accel-Buffering: no` + `Cache-Control: no-store` 로 버퍼링 방지

---

## API 표면 (Phase 1)

| Method | Path | 인증 | 출처 |
|--------|------|-----|------|
| GET    | `/api/health` | open | Phase 0 |
| POST   | `/api/auth/login` | open | B `auth.py` 패턴 |
| POST   | `/api/auth/logout` | session | B |
| GET    | `/api/auth/me` | session | B |
| GET    | `/api/auth/oauth/{provider}/start` | open | **501 stub** |
| GET    | `/api/auth/oauth/{provider}/callback` | open | **501 stub** |
| POST   | `/api/auth/passkey/register/begin` | session | **501 stub** |
| POST   | `/api/auth/passkey/register/finish` | session | **501 stub** |
| POST   | `/api/auth/passkey/authenticate/begin` | open | **501 stub** |
| POST   | `/api/auth/passkey/authenticate/finish` | open | **501 stub** |
| POST   | `/api/chat/stream` | session | NEW (SSE) |

## 환경 변수

| 변수 | 의미 | 기본 |
|------|------|------|
| `HERMES_GUI_PASSWORD` | 로그인 비밀번호 (단일 사용자) | (없으면 패스워드 로그인 비활성) |
| `HERMES_GUI_TOKEN` | Bearer 토큰 | (없으면 토큰 인증 비활성) |
| `HERMES_GUI_SECRET` | HMAC 쿠키 서명 키 | `~/.hermes-agent-gui/secret` 자동생성 |
| `HERMES_GUI_FAKE_BACKEND` | `echo` 시 EchoAdapter 사용 | 미설정 |
| `HERMES_API_URL` | Hermes Agent gateway URL | `http://127.0.0.1:8642` (없으면 사용 안 함) |
| `HERMES_API_TOKEN` | gateway API key | 미설정 |
| `HERMES_DASHBOARD_URL` | Hermes dashboard URL | `http://127.0.0.1:9119` |
| `HERMES_GUI_FAIL_OPEN` | true 시 외부 노출에서도 auth 없이 허용 | false (fail-closed) |

## 보안 정책 (Phase 1 부터 박힘)

1. **Fail-closed remote bind** (A 정책) — host 가 `127.0.0.1` 이 아니고 `HERMES_GUI_PASSWORD` / `HERMES_GUI_TOKEN` 둘 다 비어 있으면 부팅 거부
2. **HMAC 쿠키** — `~/.hermes-agent-gui/secret` (`secrets.token_hex(32)`) 로 서명. 30일 TTL
3. **Constant-time 비교** — `hmac.compare_digest` 사용
4. **Rate limit** — `/api/auth/login` 만 적용 (분당 5회) — Phase 1 minimal. CSP/client-event 는 Phase 7

## 프론트엔드 변화

- `routes/login.tsx` 신규
- `routes/chat.tsx` 신규
- `routes/index.tsx` → 인증되면 `/chat` redirect, 아니면 `/login`
- `__root.tsx` → AuthGuard wrapper (loader 에서 `/api/auth/me` 호출)
- `lib/auth.ts` — login/logout/me
- `lib/chat-stream.ts` — fetch + ReadableStream → SSE 파서
- `stores/auth-store.ts` — zustand (user 상태)

---

## 검증 시나리오

```bash
# 1. 백엔드 부팅 (password + echo mode)
HERMES_GUI_PASSWORD=hello HERMES_GUI_FAKE_BACKEND=echo \
  python3 apps/server/server.py --port 8800

# 2. 로그인
curl -sS -c /tmp/c.txt -X POST http://127.0.0.1:8800/api/auth/login \
  -H 'content-type: application/json' -d '{"password":"hello"}'
# → {"user":{"name":"local"},"expires_at":...}

# 3. 인증 확인
curl -sS -b /tmp/c.txt http://127.0.0.1:8800/api/auth/me
# → {"user":{"name":"local"}}

# 4. SSE 채팅
curl -sS -N -b /tmp/c.txt -X POST http://127.0.0.1:8800/api/chat/stream \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"hello world"}]}'
# → event: token / data: {"text":"hello "} ... event: done / data: {...}
```

---

## 다음 Phase

**Phase 2**: 세션 라이프사이클 5종 + transcript repair + `/api/session/health`.
Phase 1 의 chat.py 는 매 호출이 단발이지만, Phase 2 가 세션 ID 와 turn journal 을 도입.
