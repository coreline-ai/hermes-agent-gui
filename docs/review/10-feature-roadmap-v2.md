# 10 · 신규 기능 로드맵 v2 — 추가 오픈소스 분석 후 제안

> 본 문서는 1차 분석(00~09) 이후 **새로 발견한 6~78K-star 급 Hermes Agent GUI 오픈소스 8종** 을
> 추가 분석해, 우리에게 없는 강력한 기능을 추출하고 우선순위별 도입 방안을 정리한 것이다.
>
> 조사일: 2026-05-26

---

## 새로 발견한 8개 프로젝트

| # | Repo | ⭐ | 정체성 | 우리에게 주는 영감 |
|---|------|----|--------|------|
| A | [thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) | **78,260** | Persistent context across sessions (ChromaDB + embeddings) | **세션 간 자동 메모리 압축 + RAG** |
| B | [nexu-io/open-design](https://github.com/nexu-io/open-design) | 52,532 | Local-first Claude Design alternative · 19 Skills | (디자인 트랙 — 본 통합 범위 밖) |
| C | [CherryHQ/cherry-studio](https://github.com/CherryHQ/cherry-studio) | **46,317** | AI productivity studio · 300+ assistants | **에이전트 마켓플레이스 / preset 라이브러리** |
| D | [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | **26,673** | Pre-indexed code knowledge graph · 35% cheaper · 70% fewer tool calls | **코드 시맨틱 인덱스** |
| E | [iOfficeAI/AionUi](https://github.com/iOfficeAI/AionUi) | **26,602** | 24/7 Cowork app · 20+ CLI 지원 (Hermes + Claude Code + Codex + Gemini CLI + …) | **멀티-CLI 브리지** |
| F | [garrytan/gbrain](https://github.com/garrytan/gbrain) | **19,047** | Knowledge graph + 합성 답변 + gap analysis · 24/7 ingest 데몬 | **지식 그래프 + 합성 레이어** |
| G | [fathah/hermes-desktop](https://github.com/fathah/hermes-desktop) | **7,343** | Native desktop · 22 slash commands · 16 messaging gateways · 14 toolsets | **메시징 게이트웨이 / 슬래시 / 페르소나 / SOUL.md** |
| H | [EKKOLearnAI/hermes-web-ui](https://github.com/EKKOLearnAI/hermes-web-ui) | **6,119** | Vue 3 web dashboard · 8 platform channels · Group chat | **플랫폼 채널 UI / 그룹 채팅 / FTS5 검색** |
| I | [the-open-agent/openagent](https://github.com/the-open-agent/openagent) | 4,966 | Go 단일 바이너리 · computer-use + browser-use + coding agent | **Playwright 기반 컴퓨터/브라우저 use** |

---

## 우리 현재 능력 vs 경쟁 평균

| 차원 | 우리 | 경쟁 평균 (G/H 기준) | gap |
|------|------|---------------------|-----|
| 채팅 SSE | ✓ | ✓ (Socket.IO) | small |
| 세션 CRUD | ✓ | ✓ | none |
| Transcript repair | ✓✓ (C 알고리즘) | 미보유 | **우리 우위** |
| 파일/터미널 | ✓ | ✓ | none |
| **메시징 게이트웨이** | ✗ | **16종** | **🔴 큼** |
| **Multi-provider LLM** | embedded/gateway 2개 | **13~14개** (OpenAI/Anthropic/Google/xAI/OpenRouter/Nous Portal/Groq/HuggingFace/Qwen/MiniMax + Ollama/LM Studio/vLLM/llama.cpp) | **🔴 큼** |
| **Slash commands** | ✗ | **22개** | **🔴 큼** |
| **Persona / SOUL.md** | ✗ | ✓ | 🔴 중 |
| **세션 FTS5 검색** | ✗ | ✓ (Ctrl+K) | 🔴 중 |
| **Usage analytics 차트** | dashboard 카드만 | 30-day trend + 모델 분포 + cost | 🟠 중 |
| **Profile import/export** | profile 격리만 | clone + `.tar.gz` archive | 🟠 중 |
| **Group chat (멀티 에이전트 방)** | ✗ | ✓ (Socket.IO + @-mention) | 🟠 중 |
| **Memory providers (Honcho/Mem0/...)** | local file만 | 6개 plug-in | 🟠 중 |
| **Auto-compress + RAG (claude-mem 식)** | manual compaction | 자동 + 벡터 | 🟠 중 |
| **Knowledge graph (gbrain 식)** | ✗ | ✓ | 🟢 옵션 |
| **Code knowledge graph (codegraph)** | ✗ | ✓ | 🟢 옵션 |
| **Computer/browser-use (openagent)** | ✗ | ✓ Playwright | 🟢 옵션 |
| **Auto-updater 와이어링** | config 만 | Electron 자동 | 🟢 작음 |
| **Backup/import/debug dump** | ✗ | ✓ | 🟢 작음 |
| **PWA / 글래스 / Conductor+Swarm** | ✓✓ | 미보유 | **우리 우위** |
| **i18n (en+ko)** | ✓ | en만 (대부분) | **우리 우위** |
| **테마 6종 / 단일파일 빌드** | ✓ | 미보유 | **우리 우위** |

---

## 🔴 Tier 1 — Killer features missing (P0 add)

이 카테고리의 누락은 사용자가 "이건 GUI 가 아니다" 라고 느낄 정도. 다른 6~7K star 경쟁자도 다 있음.

### T1-1. 메시징 게이트웨이 16종 (출처: G hermes-desktop · H hermes-web-ui)

Hermes Agent 의 **킬러 기능**(다른 에이전트와의 결정적 차별점)인 메시징 플랫폼 통합 UI 가 우리에게 없음.

| 플랫폼 | 채널 |
|--------|------|
| Telegram | Bot token, mention, reactions |
| Discord | Bot token, auto-thread, channel allow/ignore |
| Slack | Bot token, mention control |
| WhatsApp | mention patterns |
| Signal | (signald 기반) |
| Matrix | Access token, homeserver, DM threads |
| Mattermost | webhook + bot |
| Email | IMAP / SMTP credentials |
| SMS | Twilio / Vonage |
| iMessage | BlueBubbles bridge |
| DingTalk | App key |
| Feishu / Lark | App ID / Secret |
| WeCom | Bot ID / Secret |
| WeChat | QR code login |
| Webhooks | 임의 endpoint |
| Home Assistant | bridge |

**구현 방안**:
- 신규 `apps/server/api/messaging/` 모듈
- 각 플랫폼별 **credential write → `~/.hermes/.env`**, **behavior write → `~/.hermes/config.yaml`** (H 패턴)
- 신규 라우트 `routes/messaging.tsx` — 8~16 플랫폼 카드 + 활성/비활성 토글 + 설정 폼
- Hermes Agent 본체의 `hermes-agent/integrations/*` 가 실제 연결을 담당 → 우리는 *설정 UI 만* 제공

**예상 작업량**: 1주 (UI 8~10일, 백엔드 credential 저장 + 검증 1~2일)

---

### T1-2. Multi-provider LLM 매니저 (출처: G hermes-desktop · H hermes-web-ui)

| 제공자 | 현재 | 추가 필요 |
|--------|------|----------|
| OpenAI | 〜 (Echo 만) | OAuth + key |
| Anthropic | 〜 | key |
| Google (Gemini) | ✗ | key |
| xAI (Grok) | ✗ | key |
| OpenRouter | ✗ | key |
| Nous Portal | ✗ | **OAuth login** (H 가 가지고 있음) |
| Qwen | ✗ | key |
| MiniMax | ✗ | key |
| HuggingFace | ✗ | key |
| Groq | ✗ | key |
| LM Studio (local) | ✗ | base URL |
| Ollama (local) | ✗ | base URL |
| vLLM (local) | ✗ | base URL |
| llama.cpp (local) | ✗ | base URL |

**구현 방안**:
- 신규 `apps/server/api/providers.py` — provider config CRUD + `/v1/models` 발견
- `apps/server/api/runtime_adapter.py` 의 `GatewayAdapter` 가 provider별 endpoint 자동 선택
- 신규 `routes/providers.tsx` — preset (`@openai/anthropic/...`) + custom OpenAI 호환 추가
- 모델 카탈로그를 `~/.hermes/auth.json` 또는 별도 DB 에 캐시 (H 패턴)

**예상 작업량**: 3~5일

---

### T1-3. Slash Commands 22종 (출처: G hermes-desktop)

채팅 입력창에서 `/...` 로 빠른 액션. 채팅 UX 의 표준.

| 카테고리 | 명령어 |
|----------|--------|
| 세션 | `/new`, `/clear`, `/compact`, `/compress`, `/undo`, `/retry` |
| 메타 | `/help`, `/version`, `/status`, `/debug` |
| 도구 | `/tools`, `/skills`, `/model`, `/memory`, `/persona` |
| 운영 | `/usage`, `/fast` |
| 외부 도구 | `/web`, `/image`, `/browse`, `/code`, `/shell` |

**구현 방안**:
- `apps/web/src/components/slash-command-menu.tsx` (A의 패턴 차용 — 이미 인벤토리에 식별)
- `apps/web/src/lib/slash-commands.ts` — 명령어 정의 + 자동완성
- 채팅 입력에서 첫 글자가 `/` 면 메뉴 띄움

**예상 작업량**: 2~3일

---

### T1-4. 페르소나 / SOUL.md 에디터 (출처: G hermes-desktop)

Hermes Agent 의 페르소나는 `~/.hermes/profiles/<name>/SOUL.md` 에 저장. 편집 UI 가 없으면 사용자는 CLI 로 vim 해야 함.

**구현 방안**:
- `apps/server/api/persona.py` — SOUL.md CRUD + 기본 reset (Hermes 디폴트로 되돌리기)
- `apps/web/src/routes/persona.tsx` — Monaco 에디터 + "Reset to default" + "Apply"
- 페르소나 라이브러리(추후): "Sage / Trader / Builder / Scribe / Ops" preset (A 가 가지고 있음)

**예상 작업량**: 1~2일

---

### T1-5. 세션 FTS5 풀텍스트 검색 (출처: G hermes-desktop)

`Ctrl+K` → 모든 세션 메시지에서 검색 → 클릭하면 해당 세션의 정확한 메시지로 점프.

**구현 방안**:
- SQLite FTS5 가상 테이블 생성 (`messages_fts(content, session_id, ts)`)
- `api/sessions/lifecycle.py` 의 append 시 자동 인덱싱
- 신규 `/api/sessions/search?q=...` 엔드포인트
- `routes/__root.tsx` 에 `Ctrl+K` 글로벌 단축키 + 모달 (A 의 `command-palette` 패턴 차용)

**예상 작업량**: 2~3일

---

### T1-6. Usage Analytics with Charts (출처: G hermes-desktop · H hermes-web-ui)

| 메트릭 | 시각화 |
|--------|--------|
| Total tokens (input/output) | KPI 카드 |
| 세션 수 + 일평균 | KPI 카드 |
| 예상 비용 (model별 단가) | KPI 카드 |
| Cache hit rate | KPI 카드 |
| 모델별 분포 | 도넛 차트 |
| 30일 추세 | 막대 차트 + 데이터 테이블 |

**구현 방안**:
- `recharts` 추가 (A 가 사용 — 호환됨)
- `apps/server/api/usage.py` — turn별 token count 누적 + provider별 unit price 적용
- `routes/dashboard.tsx` 확장 또는 신규 `routes/usage.tsx`

**예상 작업량**: 3~4일

---

### T1-7. Profile Clone + Import/Export `.tar.gz` (출처: H hermes-web-ui)

```
[Profile A] → [Clone] → [Profile A-copy]
[Profile A] → [Export] → profile-A-2026-05-26.tar.gz
[Profile A-copy] ← [Import] ← profile-A-2026-05-26.tar.gz
```

각 profile 은 격리된: config / cache / uploads / sessions / jobs / usage / memory / skills / plugins / providers / model visibility 를 가짐.

**구현 방안**:
- `apps/server/api/profiles.py` — clone/export/import
- 파일 형식: `tarfile.open(..., mode='w:gz')` 로 `~/.hermes/profiles/<name>/**` 압축
- 신규 라우트 `routes/profiles.tsx` (또는 settings 페이지 확장)

**예상 작업량**: 2일

---

## 🟠 Tier 2 — Strong adds (P1)

### T2-1. 자동 컨텍스트 압축 + RAG (출처: A claude-mem)

세션이 길어지면 자동으로 LLM이 메시지를 요약 → ChromaDB(또는 SQLite-VSS)에 embedding 저장 → 다음 턴에 유사도 검색으로 컨텍스트 재주입.

```
turn 100 → summary "1-50 turn 요약" → embed → chromadb
새 질문 "Phase 5 에서 우리가 결정한 게…?" → embedding query → top-3 요약 인젝션
```

**구현 방안**:
- 옵션 의존성: `chromadb` 또는 `sqlite-vss` (단일 파일이라 stdlib 친화)
- `apps/server/api/memory_compress.py` — 트리거 기준 (40+ turns?) + 압축 → 임베딩 → 인덱스
- chat.py 가 매 턴 query → top-k 결과 → system prompt 에 인젝션

**예상 작업량**: 1주 (LLM 호출 + embedding pipeline 검증 비용 큼)

---

### T2-2. 지식 그래프 + 합성 답변 (출처: F gbrain)

Garry Tan 의 GBrain 패턴: 페이지/메시지를 쓸 때 entity (people/companies/events) 와 typed edges (works_at, invested_in, attended) 를 LLM 없이 추출 → 쿼리 시 그래프 traversal 로 합성 답변 + 출처 + gap analysis.

```
질문: "Alice 와의 미팅 전 뭘 알고 있어야 해?"
응답: "Alice 는 Acme(series-B fintech)의 엔지니어링 리드. 마지막 대화는 2026-04-22 pricing 관련.
       Gap: 그녀의 최근 프로젝트 진척은 모름."
출처: [people/alice, meetings/2026-04-22, customers/acme]
```

**구현 방안**:
- entity 추출: 정규식 (#mention) + 명명규칙 (`@person`, `Acme Corp`) — LLM 없이
- 그래프 저장: SQLite (edges, nodes 테이블) 또는 NetworkX
- 합성: gather → LLM 1회 호출 → cited answer + gap

**예상 작업량**: 2주 — 가장 큼

---

### T2-3. 메모리 백엔드 플러그인 (출처: G hermes-desktop)

`Honcho / Hindsight / Mem0 / RetainDB / Supermemory / ByteRover` 중 사용자가 선택.

**구현 방안**:
- `apps/server/api/memory_providers/` — 추상 베이스 + 6개 어댑터
- 각 provider 는 `query(text)` / `write(facts)` / `purge()` 인터페이스
- `routes/memory.tsx` 에 provider 선택 dropdown

**예상 작업량**: 5~7일 (각 provider 1일씩)

---

### T2-4. Group Chat — 멀티 에이전트 방 (출처: H hermes-web-ui)

A 의 Swarm 보다 가벼운 "여러 에이전트가 같은 방에 들어가서 @-mention 으로 대화" UX.

| 기능 | 동작 |
|------|------|
| 방 생성 / 초대 코드 | A-Z 8자 |
| Per-agent profile | 각 멤버가 다른 페르소나/모델 |
| @mention 라우팅 | `@builder do X` → builder 응답 |
| 자동 요약 | 토큰 임계 초과시 |
| 타이핑 상태 / 진행 인디케이터 | Socket.IO |

**구현 방안**:
- 세션 모델 확장: `is_group` boolean + `participants: list[ProfileID]`
- 메시지에 `mentions: list[ProfileID]` 메타데이터
- 라우팅: mentioned profile 에게만 chat completion 요청

**예상 작업량**: 5~7일

---

### T2-5. Computer-use + Browser-use (출처: I openagent)

Playwright 기반 자동 브라우저 + 데스크탑 컨트롤. A 가 dep 으로 가지고 있는 `playwright` 와 `puppeteer-extra-plugin-stealth` 를 활용.

**구현 방안**:
- `apps/server/api/tools/browser.py` — 신규 tool, Hermes Agent 가 호출 가능하도록 등록
- 헤드리스 Playwright 컨테이너 (옵션) 또는 사용자 머신 직접
- `routes/swarm.tsx` 에 "browser session" 카드 추가

**예상 작업량**: 1주

---

### T2-6. Code Knowledge Graph (출처: D codegraph)

워크스페이스의 모든 코드를 사전 인덱싱 → tree-sitter 로 정의/참조 추출 → SQLite. 채팅에서 "X 함수 정의 어디 있어?" → 즉시 응답, tool call 불필요.

**구현 방안**:
- 의존성: `tree-sitter` Python binding + 언어별 grammar (ts/js/py/go/rust)
- 워크스페이스 인덱스 작업자 (background job)
- 신규 tool `/api/tools/code_lookup` — `find_definition(symbol)`, `find_references(symbol)`

**예상 작업량**: 1.5~2주

---

### T2-7. PII Redaction at Input (출처: H hermes-web-ui)

사용자가 보낸 메시지에 SSN/카드번호/이메일/전화번호 등이 포함되면 자동 redact (provider 호출 전).

**구현 방안**:
- `apps/server/api/pii.py` — 패턴 라이브러리 (Dashboard 의 redact 패턴 재활용 + 확장)
- chat.py 의 turn 처리 진입부에 hook
- 설정에서 on/off + custom 패턴 추가

**예상 작업량**: 1~2일

---

### T2-8. Auto-updater 와이어링 (출처: G hermes-desktop)

`electron-updater` 가 이미 dep 에 있음. wiring 만 하면 됨.

**구현 방안**:
- `electron/main.cjs` 의 `autoUpdater.checkForUpdatesAndNotify()` 호출
- GitHub Releases 또는 자체 update 서버
- 사용자에게 "X.Y.Z 사용 가능" 토스트

**예상 작업량**: 0.5~1일

---

### T2-9. Backup / Import / Debug Dump (출처: G hermes-desktop)

```
Settings → Backup → backup-2026-05-26.tar.gz
   포함: ~/.hermes-agent-gui/{secret, sessions.db, passkeys.json, ...}
        ~/.hermes/{config.yaml, .env, memory/, skills/, profiles/}
Settings → Debug Dump → debug-2026-05-26.zip
   포함: GUI version, OS, recent logs(redacted), endpoint capabilities, /api/health 결과
```

**구현 방안**:
- `apps/server/api/backup.py` — tar.gz/zip 빌더 + restore
- `routes/settings.tsx` 에 카드 추가

**예상 작업량**: 1~2일

---

## 🟢 Tier 3 — Nice-to-haves (P2)

### T3-1. 소스-그룹 사이드바 아코디언 (H)
세션 사이드바를 소스(Telegram/Discord/Slack/Web) 별 그룹으로 묶기. 1일.

### T3-2. Profile-aware 모델 selector (H)
로그인된 profile 의 권한에 따라 사용 가능한 모델만 보여주기. 1일.

### T3-3. Hermes Office / Claw3d 3D 워크스페이스 (G)
공간형 3D 인터페이스. 우리 Phase 9 의 3D feature flag 와 결합. 2~3주.

### T3-4. 멀티-CLI 브리지 (E AionUi)
Hermes 외에 Claude Code / Codex / Gemini CLI / OpenCode 도 같은 GUI 에서 사용. 신규 adapter 5~6개. 2~3주.

### T3-5. React Virtuoso (E)
긴 세션의 메시지 리스트를 virtualized scrolling 으로. 1일.

### T3-6. CLI 유지보수 명령 (H)
```
hermes-agent-gui clear-login-locks
hermes-agent-gui reset-default-login
```
0.5일.

### T3-7. 채널 behavior YAML (H)
플랫폼별 mention 패턴, auto-thread, allow/ignore 리스트 — `config.yaml` 으로. T1-1 과 함께. 0.5일.

### T3-8. 에이전트 marketplace / preset 라이브러리 (C cherry-studio)
300+ assistants 같은 preset 카탈로그. 우리는 6 personas(A) 부터 시작 가능. 1주.

---

## 📋 권장 도입 순서 (10 주 로드맵 가정)

| Week | Phase | 묶음 |
|------|-------|------|
| 1-2 | **Phase 15** | T1-1 메시징 게이트웨이 (8 플랫폼 우선) + T1-7 profile import/export |
| 3 | **Phase 16** | T1-2 multi-provider LLM + T1-3 slash commands |
| 4 | **Phase 17** | T1-4 SOUL.md + T1-5 FTS5 검색 + T1-6 usage analytics |
| 5-6 | **Phase 18** | T2-1 auto-compress + RAG (claude-mem 스타일) |
| 7 | **Phase 19** | T2-3 memory provider plugins + T2-7 PII redaction |
| 8 | **Phase 20** | T2-4 Group chat + T2-8 auto-updater + T2-9 backup/debug |
| 9-10 | **Phase 21** | T2-2 knowledge graph (gbrain) **또는** T2-6 code knowledge graph (codegraph) |

후행 Phase 22+ : T2-5 computer-use, T3 항목들.

---

## 🎯 의사결정

1. **메시징 게이트웨이 — 직접 통합 vs Hermes 본체 위임** ✅ **확정 (2026-05-26)**: **Hybrid**
   - 14개 플랫폼 (Telegram/Discord/Slack/WhatsApp/Signal/Matrix/Mattermost/Email/SMS/iMessage/DingTalk/Feishu/WeCom/WeChat) = **Hermes 본체에 위임** (우리는 credential UI + behavior YAML 만)
   - 2개 플랫폼 (**Webhook + Home Assistant**) = **직접 처리** (외부 봇 라이브러리 불필요 + Hermes 미설치 환경에서도 동작)
   - 상세: [`11-implementation-plan-full.md` §Phase 15 확정 결정 1](./11-implementation-plan-full.md)

2. **Memory 백엔드 전략**
   - (a) **자체 ChromaDB 임베디드** — 의존성 ↑, 무엇이든 동작
   - (b) **provider plugin 6종** — 사용자가 외부 서비스에 종속
   - (c) **둘 다** — 기본 자체 + 플러그인 선택

3. **Knowledge Graph 채택 여부**
   - 우리 GUI 가 *agent control plane* 인지 *brain* 인지의 정체성 결정
   - 채택하면 gbrain-style 합성 답변이 새 1급 시민이 됨 (큰 가치) → 2주 투자

4. **컴퓨터/브라우저 use 통합**
   - Playwright 가 이미 A 의존성에 있음 — 재사용 쉬움
   - 다만 보안 분리 (sandbox) 결정 필요

5. **AionUi 스타일 멀티-CLI 지원**
   - Hermes 외에 Claude Code / Codex / Gemini 도 같이 → 시장 확장
   - 단, 본 프로젝트 정체성이 "Hermes Agent GUI" 인지 "AI Agent 통합 GUI" 인지 재정의 필요

---

## 부록 — 우리만의 차별점 (계속 유지)

다음은 위 8개 경쟁자가 **하나도 가지고 있지 않은** 우리 우위. 도입 결정 시 이걸 잃지 않도록.

| 차별점 | 출처 | 가치 |
|--------|------|------|
| Transcript drift / tool evidence repair | C pyrate-llama 알고리즘 이식 | 환각 방어 |
| Compression session aliases (재시작 후 유지) | C v3.3.1 | 컨텍스트 안정성 |
| Conductor + Swarm 멀티에이전트 control plane | A outsourc-e | 유일 |
| 6 테마 (Hermes/Nous/Bronze/Slate/Mono/Glass) | A + C 결합 | UX 강도 |
| 단일파일 빌드 모드 (`pnpm build:singlefile`) | C 철학 | curl + python 으로 배포 |
| Python stdlib 백엔드 (의존성 2개만) | B 패턴 | 운영 단순도 |
| Tool honesty guard + composer work banner | C v3.3.2 | 환각 방어 |
| Fail-closed remote bind | A 정책 | 보안 |
| OAuth + Passkey + Password 3층 인증 | B + 자체 구현 | 보안 |
| i18n (en + ko) | A 패턴 | 한국어 사용자 |

→ Tier 1~2 도입 시 위 항목들이 깨지지 않도록 통합 테스트 필수.
