/**
 * Single typed REST client. All domain endpoints route through ``apiFetch``
 * which normalises errors into ``ApiError`` and applies same-origin cookies.
 */

export class ApiError extends Error {
  constructor(public status: number, public payload: unknown) {
    super(`API ${status}`);
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
    ...init,
  });
  let payload: unknown = null;
  const ct = res.headers.get('content-type') ?? '';
  if (ct.includes('application/json')) {
    payload = await res.json().catch(() => null);
  } else {
    payload = await res.text().catch(() => '');
  }
  if (!res.ok) throw new ApiError(res.status, payload);
  return payload as T;
}


// ── Auth maintenance ────────────────────────────────────────────────────────

export interface LoginLock { ip: string; attempts: number; window_seconds: number }
export const AuthMaintenance = {
  loginLocks: () => apiFetch<{ locks: LoginLock[] }>('/api/auth/login-locks'),
  clearLoginLocks: (ip?: string) => apiFetch<{ cleared: number }>(`/api/auth/login-locks${ip ? `?ip=${encodeURIComponent(ip)}` : ''}`, { method: 'DELETE' }),
};

// ── Health ───────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: 'ok' | 'degraded';
  version: string;
  phase: string;
  uptime_seconds: number;
  adapter: string;
}
export const getHealth = () => apiFetch<HealthResponse>('/api/health');

// ── Sessions ─────────────────────────────────────────────────────────────────

export interface SessionSummary {
  id: string;
  title: string;
  profile: string;
  created_at: number;
  updated_at: number;
  message_count: number;
}
export interface SessionMessage {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  tool_calls?: unknown[];
  created_at?: number;
}
export interface SessionFull extends SessionSummary {
  messages: SessionMessage[];
  metadata: Record<string, unknown>;
}
export interface SessionHealth {
  session_id: string;
  server_messages: number;
  browser_messages: number | null;
  compact_context_messages: number | null;
  has_tool_evidence_on_server: boolean;
  has_tool_evidence_on_browser: boolean;
  drift: boolean;
  drift_kind: 'browser_ahead' | 'server_ahead' | 'compact_stale' | null;
  repaired: boolean;
  messages: SessionMessage[];
}

export const Sessions = {
  list: () => apiFetch<{ sessions: SessionSummary[] }>('/api/sessions'),
  get: (sid: string) => apiFetch<SessionFull>(`/api/sessions/${sid}`),
  create: (title: string) =>
    apiFetch<SessionFull>('/api/sessions', { method: 'POST', body: JSON.stringify({ title }) }),
  rename: (sid: string, title: string) =>
    apiFetch<SessionSummary>(`/api/sessions/${sid}`, {
      method: 'PUT',
      body: JSON.stringify({ title }),
    }),
  remove: (sid: string) =>
    apiFetch<{ ok: true }>(`/api/sessions/${sid}`, { method: 'DELETE' }),
  health: (sid: string, browserMessages: SessionMessage[], compact?: number) =>
    apiFetch<SessionHealth>(`/api/sessions/${sid}/health`, {
      method: 'POST',
      body: JSON.stringify({
        browser_messages: browserMessages,
        compact_context_messages: compact,
      }),
    }),
};

// ── Workspace ────────────────────────────────────────────────────────────────

export interface WsEntry {
  name: string;
  path: string;
  kind: 'file' | 'dir' | 'symlink' | 'other';
  size: number;
  modified: number;
}

export const Workspace = {
  roots: () => apiFetch<{ roots: string[] }>('/api/workspace/roots'),
  list: (path = '.') =>
    apiFetch<{ path: string; entries: WsEntry[] }>(
      `/api/workspace/list?path=${encodeURIComponent(path)}`,
    ),
  read: (path: string) =>
    apiFetch<{ path: string; encoding: string; content: string }>(
      `/api/workspace/read?path=${encodeURIComponent(path)}`,
    ),
  write: (path: string, content: string) =>
    apiFetch<{ path: string; bytes: number }>('/api/workspace/write', {
      method: 'PUT',
      body: JSON.stringify({ path, content }),
    }),
  remove: (path: string) =>
    apiFetch<{ ok: true }>(`/api/workspace/delete?path=${encodeURIComponent(path)}`, {
      method: 'DELETE',
    }),
};

// ── Terminal ─────────────────────────────────────────────────────────────────

export interface ExecResult {
  exit_code: number;
  stdout: string;
  stderr: string;
  truncated: boolean;
  cwd: string;
}
export interface TerminalStatus {
  exec_enabled: boolean;
  exec_available: boolean;
  exec_allow_remote: boolean;
  blocked_reason: string | null;
  bind_host?: string | null;
  allowlist: string[];
  detail: string;
}
export const Terminal = {
  status: () => apiFetch<TerminalStatus>('/api/terminal/status'),
  exec: (cmd: string, cwd?: string, allow_unsafe = false) =>
    apiFetch<ExecResult>('/api/terminal/exec', {
      method: 'POST',
      body: JSON.stringify({ cmd, cwd, allow_unsafe }),
    }),
};

// ── Skills / MCP / Memory ────────────────────────────────────────────────────

export interface SkillItem {
  id: string;
  name: string;
  origin: string;
  path?: string;
  description?: string;
}
export const Skills = {
  list: () => apiFetch<{ source: string; skills: SkillItem[] }>('/api/skills'),
};

export interface McpServer {
  name: string;
  command: string[];
  env?: Record<string, string>;
}
export const Mcp = {
  list: () => apiFetch<{ source: string; servers: McpServer[] }>('/api/mcp/servers'),
  add: (server: McpServer) =>
    apiFetch<{ ok: true; server: { name: string } }>('/api/mcp/servers', {
      method: 'POST',
      body: JSON.stringify(server),
    }),
  remove: (name: string) =>
    apiFetch<{ ok: true }>(`/api/mcp/servers/${encodeURIComponent(name)}`, {
      method: 'DELETE',
    }),
};

export interface MemoryEntry {
  path: string;
  size: number;
  modified: number;
}
export const Memory = {
  list: () =>
    apiFetch<{ root: string; entries: MemoryEntry[]; exists: boolean }>('/api/memory'),
  read: (path: string) =>
    apiFetch<{ path: string; content: string }>(
      `/api/memory/read?path=${encodeURIComponent(path)}`,
    ),
  write: (path: string, content: string) =>
    apiFetch<{ ok: true; path: string }>('/api/memory/write', {
      method: 'PUT',
      body: JSON.stringify({ path, content }),
    }),
};


// ── Auto-compress / RAG ─────────────────────────────────────────────────────

export interface MemoryChunk {
  id: string;
  session_id: string;
  range_start: number;
  range_end: number;
  summary: string;
  embedding_model: string;
  created_at: number;
  score?: number;
}

export const Rag = {
  compact: (sessionId: string, trigger = 'manual') =>
    apiFetch<{ compacted_chunks: MemoryChunk[]; tokens_saved: number; skipped?: boolean; fallback?: string }>(
      `/api/sessions/${encodeURIComponent(sessionId)}/compact`,
      { method: 'POST', body: JSON.stringify({ trigger }) },
    ),
  sessionMemory: (sessionId: string) =>
    apiFetch<{ chunks: MemoryChunk[] }>(`/api/sessions/${encodeURIComponent(sessionId)}/memory`),
  search: (q: string, k = 5, sessionId?: string) =>
    apiFetch<{ results: MemoryChunk[] }>('/api/memory/search', {
      method: 'POST',
      body: JSON.stringify({ q, k, session_id_filter: sessionId || undefined }),
    }),
};

// ── Tasks / Cron ─────────────────────────────────────────────────────────────

export type TaskLane =
  | 'backlog'
  | 'ready'
  | 'running'
  | 'review'
  | 'blocked'
  | 'done'
  | 'needs_you';

export interface TaskRow {
  id: string;
  title: string;
  lane: TaskLane;
  profile: string;
  created_at: number;
  updated_at: number;
  done_at: number | null;
  metadata: Record<string, unknown>;
}

export const Tasks = {
  list: () =>
    apiFetch<{
      lanes: TaskLane[];
      tasks: TaskRow[];
      by_lane: Record<TaskLane, TaskRow[]>;
    }>('/api/tasks'),
  create: (title: string, lane: TaskLane = 'backlog') =>
    apiFetch<{ id: string }>('/api/tasks', {
      method: 'POST',
      body: JSON.stringify({ title, lane }),
    }),
  update: (id: string, patch: { lane?: TaskLane; title?: string }) =>
    apiFetch<{ ok: true }>(`/api/tasks/${id}`, {
      method: 'PUT',
      body: JSON.stringify(patch),
    }),
  remove: (id: string) =>
    apiFetch<{ ok: true }>(`/api/tasks/${id}`, { method: 'DELETE' }),
};

export interface CronJob {
  id: string;
  name: string;
  schedule: string;
  command: string;
  enabled: boolean;
  last_run_at: number | null;
  last_exit_code: number | null;
  last_output: string | null;
}
export const Cron = {
  list: () => apiFetch<{ jobs: CronJob[] }>('/api/cron'),
  create: (job: Pick<CronJob, 'name' | 'schedule' | 'command'>) =>
    apiFetch<{ id: string }>('/api/cron', { method: 'POST', body: JSON.stringify(job) }),
  runNow: (id: string) =>
    apiFetch<{ ok: true }>(`/api/cron/${id}/run`, { method: 'POST' }),
  remove: (id: string) =>
    apiFetch<{ ok: true }>(`/api/cron/${id}`, { method: 'DELETE' }),
};

// ── Swarm / Conductor ────────────────────────────────────────────────────────

export interface SwarmWorker {
  id: string;
  role: string;
  cmd: string[];
  created_at: number;
  pid: number | null;
  tmux_session: string | null;
  log_path: string;
  state: string;
  meta: Record<string, unknown>;
}
export const Swarm = {
  list: () =>
    apiFetch<{ tmux: boolean; workers: SwarmWorker[] }>('/api/swarm/workers'),
  spawn: (role: string, cmd: string[]) =>
    apiFetch<SwarmWorker>('/api/swarm/workers', {
      method: 'POST',
      body: JSON.stringify({ role, cmd }),
    }),
  kill: (wid: string) =>
    apiFetch<{ ok: boolean }>(`/api/swarm/workers/${wid}`, { method: 'DELETE' }),
};

export interface Mission {
  id: string;
  prompt: string;
  sub_tasks: { text: string; role: string; order: number }[];
}
export const Conductor = {
  dispatch: (prompt: string) =>
    apiFetch<Mission>('/api/conductor/missions', {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    }),
};






// ── CLI Bridges + Marketplace ───────────────────────────────────────────────

export interface CliBridge { name: string; binary: string; available: boolean; path: string | null; install_url: string }
export const CliBridges = {
  list: () => apiFetch<{ bridges: CliBridge[] }>('/api/cli-bridges'),
  run: (name: string, prompt: string) => apiFetch<{ output: string }>(`/api/cli-bridges/${encodeURIComponent(name)}/run`, { method: 'POST', body: JSON.stringify({ prompt }) }),
};

export interface MarketplacePreset {
  id: string; label: string; category: string; soul_md: string; skills: string[]; tags: string[]; installed: boolean; install?: { profile: string; favorite: boolean; installed_at: number };
}
export const Marketplace = {
  catalog: (q = '') => apiFetch<{ items: MarketplacePreset[]; total: number }>(`/api/marketplace/catalog?q=${encodeURIComponent(q)}`),
  install: (id: string) => apiFetch<{ ok: true; preset_id: string; profile: string }>(`/api/marketplace/${encodeURIComponent(id)}/install`, { method: 'POST', body: JSON.stringify({}) }),
  uninstall: (id: string) => apiFetch<{ ok: boolean }>(`/api/marketplace/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  favorite: (id: string, favorite: boolean) => apiFetch<{ ok: true }>(`/api/marketplace/${encodeURIComponent(id)}/favorite`, { method: 'POST', body: JSON.stringify({ favorite }) }),
};

// ── Browser / Computer Use ──────────────────────────────────────────────────

export interface BrowserNavigateResult { session_id: string; url: string; title: string; screenshot_b64: string }
export const BrowserUse = {
  navigate: (url: string, sessionId?: string) =>
    apiFetch<BrowserNavigateResult>('/api/browser/navigate', { method: 'POST', body: JSON.stringify({ url, session_id: sessionId }) }),
  extract: (sessionId: string, selector = 'title') =>
    apiFetch<{ selector: string; text: string }>('/api/browser/extract', { method: 'POST', body: JSON.stringify({ session_id: sessionId, selector }) }),
  screenshot: (sessionId: string) =>
    apiFetch<{ session_id: string; screenshot_b64: string; url: string }>('/api/browser/screenshot', { method: 'POST', body: JSON.stringify({ session_id: sessionId }) }),
};

// ── Code Knowledge Graph ────────────────────────────────────────────────────

export interface CodeSymbol { name: string; kind: string; file: string; line: number; column: number }
export const CodeGraph = {
  index: (root = '.') => apiFetch<{ root: string; files: number; symbols: number; skipped: number; elapsed_ms: number }>('/api/codegraph/index', { method: 'POST', body: JSON.stringify({ root }) }),
  symbols: (q = '') => apiFetch<{ symbols: CodeSymbol[] }>(`/api/codegraph/symbols?q=${encodeURIComponent(q)}`),
  definition: (symbol: string) => apiFetch<CodeSymbol>(`/api/codegraph/definition?symbol=${encodeURIComponent(symbol)}`),
  outline: (file: string) => apiFetch<{ symbols: CodeSymbol[] }>(`/api/codegraph/outline?file=${encodeURIComponent(file)}`),
};

// ── Knowledge Graph / GBrain ────────────────────────────────────────────────

export interface BrainNode { id: string; label: string; kind: string; source: string }
export interface BrainEdge { id: string; src: string; dst: string; kind: string; source: string }
export interface BrainQueryResponse {
  graph: { seeds: BrainNode[]; paths: { src: BrainNode; dst: BrainNode; kind: string; score: number }[] };
  synthesis: { answer: string; citations: { node_id: string; label: string; edge: string }[]; gap_analysis: string[] };
}

export const Brain = {
  ingest: (text: string, source = 'manual') =>
    apiFetch<{ extracted: { nodes: BrainNode[]; edges: BrainEdge[] }; stats: Record<string, number> }>('/api/brain/ingest', {
      method: 'POST',
      body: JSON.stringify({ text, source }),
    }),
  query: (q: string, depth = 3) =>
    apiFetch<BrainQueryResponse>('/api/brain/query', { method: 'POST', body: JSON.stringify({ q, depth }) }),
  nodes: (q = '') => apiFetch<{ nodes: BrainNode[] }>(`/api/brain/nodes?q=${encodeURIComponent(q)}`),
  graph: () => apiFetch<{ nodes: BrainNode[]; edges: BrainEdge[] }>('/api/brain/graph'),
};

// ── Groups / Backup / Debug ─────────────────────────────────────────────────

export interface GroupParticipant {
  name: string;
  profile: string;
  model: string;
}

export interface Group {
  id: string;
  name: string;
  invite_code: string;
  invite_expires_at: number;
  invite_expired: boolean;
  created_at: number;
  participants: GroupParticipant[];
}

export interface GroupMessage {
  id: string;
  group_id: string;
  participant: string;
  content: string;
  created_at: number;
}

export const Groups = {
  list: () => apiFetch<{ groups: Group[] }>('/api/groups'),
  create: (payload: { name: string; participants: Pick<GroupParticipant, 'name' | 'profile' | 'model'>[] }) =>
    apiFetch<Group>('/api/groups', { method: 'POST', body: JSON.stringify(payload) }),
  get: (id: string) => apiFetch<Group & { messages: GroupMessage[] }>(`/api/groups/${encodeURIComponent(id)}`),
  send: (id: string, content: string) =>
    apiFetch<{ message: GroupMessage; routed_to: GroupParticipant }>(`/api/groups/${encodeURIComponent(id)}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
};

export const Backup = {
  exportUrl: () => '/api/backup/export',
  debugDumpUrl: () => '/api/debug/dump',
};

// ── Dashboard / Health ───────────────────────────────────────────────────────

export interface DashboardData {
  summary: {
    sessions: number;
    tasks: number;
    cron_jobs: number;
    recent_sessions: { id: string; title: string; updated_at: number }[];
  };
  agent: Record<string, unknown>;
  system: Record<string, unknown>;
}
export const Dashboard = {
  get: () => apiFetch<DashboardData>('/api/dashboard'),
  agentHealth: () => apiFetch<Record<string, unknown>>('/api/health/agent'),
  systemHealth: () => apiFetch<Record<string, unknown>>('/api/health/system'),
  logs: (lines = 100) =>
    apiFetch<{ path: string; lines: string[] }>(`/api/inspector/logs?lines=${lines}`),
};

// ── Messaging / Profile Archive ─────────────────────────────────────────────

export type CredentialType = 'text' | 'password' | 'url' | 'select' | 'qr';
export type PlatformMode = 'delegated' | 'direct';

export interface CredentialField {
  name: string;
  label: string;
  type: CredentialType;
  required: boolean;
  placeholder: string;
  pattern: string | null;
  options: string[] | null;
}

export interface PlatformMeta {
  id: string;
  label: string;
  mode: PlatformMode;
  description: string;
  credential_fields: CredentialField[];
  behavior_schema: Record<string, { type?: string; default?: unknown; items?: string }>;
  docs_url: string;
  requires_hermes_running: boolean;
  configured: boolean;
  connected: boolean;
  last_event_at: number | null;
  last_error: string | null;
  behavior: Record<string, unknown>;
}

export interface WebhookConfigureResponse {
  ok: true;
  platform: 'webhook';
  configured: true;
  token: string;
  url: string;
  secret: string;
}

export const Messaging = {
  platforms: () => apiFetch<{ platforms: PlatformMeta[] }>('/api/messaging/platforms'),
  configure: (platform: string, payload: { credentials: Record<string, string>; behavior?: Record<string, unknown>; rotate?: boolean }) =>
    apiFetch<{ ok: true; platform: string; configured: boolean } | WebhookConfigureResponse>(
      `/api/messaging/${encodeURIComponent(platform)}/configure`,
      { method: 'POST', body: JSON.stringify(payload) },
    ),
  test: (platform: string) =>
    apiFetch<Record<string, unknown>>(`/api/messaging/${encodeURIComponent(platform)}/test`, {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  disable: (platform: string) =>
    apiFetch<{ ok: true; platform: string; purged_credential: boolean }>(
      `/api/messaging/${encodeURIComponent(platform)}`,
      { method: 'DELETE' },
    ),
};

export interface ProfileInfo {
  name: string;
  session_count: number;
  has_profile_dir: boolean;
  updated_at: number | null;
}

export interface ProfileImportResult {
  imported_profile: string;
  manifest: Record<string, unknown>;
  warnings: string[];
  relogin_required: boolean;
}

export const Profiles = {
  list: () => apiFetch<{ profiles: ProfileInfo[] }>('/api/profiles'),
  clone: (name: string, newName: string) =>
    apiFetch<{ name: string }>(`/api/profiles/${encodeURIComponent(name)}/clone`, {
      method: 'POST',
      body: JSON.stringify({ new_name: newName }),
    }),
  exportUrl: (name: string) => `/api/profiles/${encodeURIComponent(name)}/export`,
  importArchive: async (file: File) => {
    const data = new FormData();
    data.append('file', file);
    const res = await fetch('/api/profiles/import', {
      method: 'POST',
      credentials: 'same-origin',
      body: data,
    });
    const payload = (await res.json().catch(() => null)) as ProfileImportResult | unknown;
    if (!res.ok) throw new ApiError(res.status, payload);
    return payload as ProfileImportResult;
  },
};

// ── Providers / Models ──────────────────────────────────────────────────────

export type ProviderKind =
  | 'openai'
  | 'anthropic'
  | 'google'
  | 'xai'
  | 'openrouter'
  | 'nous_portal'
  | 'qwen'
  | 'minimax'
  | 'huggingface'
  | 'groq'
  | 'lm_studio'
  | 'ollama'
  | 'vllm'
  | 'llama_cpp'
  | 'custom';

export interface ProviderPreset {
  kind: ProviderKind;
  label: string;
  base_url: string;
  api_key_env: string;
  auth_type: 'bearer' | 'oauth' | 'none';
  scopes: string[];
  default_models: string[];
  extra: Record<string, unknown>;
}

export interface ProviderConfig {
  id: string;
  kind: ProviderKind;
  label: string;
  base_url: string;
  api_key_env: string;
  auth_type: 'bearer' | 'oauth' | 'none';
  enabled: boolean;
  extra: Record<string, unknown>;
  test_status: string | null;
  last_tested_at: number | null;
}

export interface ProviderModel {
  id: string;
  provider_id: string;
  context_window: number;
  pricing_in_per_1m_usd: number;
  pricing_out_per_1m_usd: number;
  capabilities: string[];
}

export const Providers = {
  presets: () => apiFetch<{ presets: ProviderPreset[] }>('/api/providers/presets'),
  list: () => apiFetch<{ providers: ProviderConfig[] }>('/api/providers'),
  create: (payload: { kind: ProviderKind; label: string; base_url?: string; api_key?: string }) =>
    apiFetch<ProviderConfig>('/api/providers', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  remove: (id: string) =>
    apiFetch<{ ok: boolean }>(`/api/providers/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  models: (id: string) =>
    apiFetch<{ provider_id: string; models: ProviderModel[]; fetched_at: number; cache_hit: boolean }>(
      `/api/providers/${encodeURIComponent(id)}/models`,
    ),
  test: (id: string) =>
    apiFetch<{ ok: true; latency_ms: number; model_used: string }>(
      `/api/providers/${encodeURIComponent(id)}/test`,
      { method: 'POST', body: JSON.stringify({}) },
    ),
  oauthStart: (provider: 'nous_portal' | 'openai_codex') =>
    apiFetch<{
      provider: string;
      state: string;
      code_challenge: string;
      code_challenge_method: 'S256';
      expires_at: number;
      authorization_url: string;
    }>(`/api/providers/oauth/${provider}/start`),
};

// ── Persona / Search / Usage ────────────────────────────────────────────────

export interface PersonaDoc {
  profile_name: string;
  soul_md: string;
  updated_at: number;
}

export interface PersonaPreset {
  id: string;
  label: string;
  soul_md: string;
}

export const Persona = {
  get: (profile = 'default') => apiFetch<PersonaDoc>(`/api/persona?profile=${encodeURIComponent(profile)}`),
  save: (soulMd: string, profile = 'default') =>
    apiFetch<{ ok: true; profile_name: string; updated_at: number }>(
      `/api/persona?profile=${encodeURIComponent(profile)}`,
      { method: 'PUT', body: JSON.stringify({ soul_md: soulMd }) },
    ),
  presets: () => apiFetch<{ presets: PersonaPreset[] }>('/api/persona/presets'),
};

export interface SearchResult {
  session_id: string;
  session_title: string;
  message_index: number;
  role: string;
  snippet: string;
  snippet_parts?: { text: string; highlight: boolean }[];
  ts: number;
  score: number;
}

export const Search = {
  messages: (q: string, limit = 20) =>
    apiFetch<{ query: string; results: SearchResult[]; total: number }>(
      `/api/sessions/search?q=${encodeURIComponent(q)}&limit=${limit}`,
    ),
};

export interface UsageSummary {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  sessions: number;
  avg_per_day: number;
  cache_hit_rate: number;
  by_model: { model_id: string; cost_usd: number; tokens: number }[];
  daily: { date: string; cost_usd: number; tokens: number }[];
}

export const Usage = {
  summary: (from?: string, to?: string) => {
    const params = new URLSearchParams();
    if (from) params.set('from', from);
    if (to) params.set('to', to);
    const suffix = params.toString() ? `?${params.toString()}` : '';
    return apiFetch<UsageSummary>(`/api/usage/summary${suffix}`);
  },
};
