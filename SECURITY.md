# SECURITY

## 보안 기본값

- `HERMES_GUI_PASSWORD` 또는 `HERMES_GUI_TOKEN`을 설정해 인증을 켠 상태로 실행하는 것을 권장한다.
- non-loopback bind(`0.0.0.0`, LAN, Docker publish 등)에서 인증이 없으면 서버는 fail-closed 된다.
- API 응답은 `Cache-Control: no-store`를 기본으로 하며, PWA service worker는 `/api/*`를 캐시하지 않는다.

## 명령 실행 표면

다음 API는 로컬 명령 실행/RCE 표면으로 취급한다.

- `/api/terminal/exec`
- `/api/pty*`
- `/api/cron*`의 create/run-now
- `/api/swarm/workers`, conductor dispatch
- `/api/cli-bridges/{name}/run`

보호 정책:

1. 기본값은 비활성화다.
2. 로컬에서 사용하려면 `HERMES_GUI_ENABLE_EXEC=1`을 설정한다.
3. 서버가 non-loopback에 bind된 상태에서 실행까지 허용하려면 `HERMES_GUI_ALLOW_REMOTE_EXEC=1`을 추가로 설정해야 한다.
4. CLI bridge, cron background runner까지 동일한 exec gate를 통과한다.
5. PTY cwd는 workspace `_safe_path()`를 통과해야 하며, terminal one-shot exec는 allowlist를 유지한다.

## Passkey / WebAuthn

- Passkey는 ES256(`alg=-7`)과 RS256(`alg=-257`) COSE public key를 지원한다.
- CBOR negative integer는 spec 방식(`-1 - n`)으로 디코딩한다.
- malformed CBOR/authData는 500이 아니라 400 계열 응답으로 처리한다.
- 향후 강화 후보: authenticator counter 기반 replay 방어와 더 넓은 WebAuthn conformance vector.

## PWA 캐시 정책

- `/api/*`는 service worker runtime cache 대상이 아니다.
- 이전 버전에서 생성된 `api` Cache Storage는 service worker activate 시 삭제된다.
- 정적 asset은 장기 캐시 가능하지만 `index.html`, service worker, manifest는 no-store/no-cache 계열로 제공한다.

## Messaging Webhook / Home Assistant

- Direct webhook inbound endpoint는 로그인 쿠키 대신 random URL token과 `X-Hermes-Signature: sha256=<hmac>` 검증을 사용한다.
- HMAC은 raw request body와 server-side signing secret으로 계산한다.
- Webhook payload는 256KB로 제한되며 token당 60 requests/minute rate limit을 적용한다.
- Home Assistant direct mode는 사용자가 저장한 HA URL/token/notify service로만 outbound REST 호출을 수행한다.
- 14 delegated messaging platforms는 실제 연결을 Hermes Agent 본체에 위임하며, Hermes 미실행 시 `hermes_agent_not_running`으로 실패한다.

## Profile Archive

- Profile archive export/import은 `MANIFEST.json`의 SHA-256 checksum을 모든 regular file에 대해 검증한다.
- Import는 absolute path, `..` path traversal, symlink/hardlink/device member를 거부한다.
- Archive에는 `.env*`, `secret`, `passkeys.json`, `.login-lock.json`, `*.key`, `*.pem`, `*.pid`, `*.lock`, `*.log`, `*token*`, `session-aliases.json`, `sessions.db-{wal,shm}`, `memory_vss.db-{wal,shm}`를 포함하지 않는다.
- Hermes home export는 `skills`, `memory`, `profiles` 하위 디렉터리만 allowlist 방식으로 포함한다.
- Import 후 device secret은 새로 생성되며 UI는 재로그인 안내 후 자동 logout을 수행한다.

## Provider / Model Discovery

- Provider API keys are written through the same atomic `~/.hermes/.env` path used by Phase 15 credentials.
- New provider records store keys in provider-specific env names (`HERMES_PROVIDER_<ID>_API_KEY`) to avoid same-kind providers overwriting each other.
- Provider labels are unique case-insensitively to avoid accidental secret overwrite/confusion.
- Remote provider discovery accepts only HTTP(S) base URLs and blocks private/loopback/link-local/reserved IP resolution for non-local provider kinds.
- Provider and browser fetch redirect targets are re-validated before following redirects; provider model discovery also blocks cross-host redirects to avoid leaking Authorization headers.
- Local runtimes (`ollama`, `lm_studio`, `vllm`, `llama_cpp`) are the only provider kinds allowed to target loopback URLs.
- OAuth provider setup uses PKCE S256, one-time state, and a 10-minute state TTL.

## 민감정보 저장

- 서버 secret은 `HERMES_GUI_STATE_DIR/secret`에 `0600` 권한으로 저장된다.
- Passkey credential store는 `HERMES_GUI_STATE_DIR/passkeys.json`에 `0600` 권한으로 저장된다.
- 로그/대시보드 노출 전 redaction 패턴을 적용한다.
