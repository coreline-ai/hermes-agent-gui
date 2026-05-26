export interface SlashCommand {
  name: string;
  args?: string;
  description: string;
  category: 'session' | 'meta' | 'tools' | 'ops' | 'external';
}

export interface ParsedSlashCommand {
  raw: string;
  command: string;
  args: string[];
  options: Record<string, string | boolean>;
}

export const COMMANDS: SlashCommand[] = [
  { name: 'new', description: 'Start a new session', category: 'session' },
  { name: 'clear', description: 'Clear current session', category: 'session' },
  { name: 'compact', description: 'Trigger context compression', category: 'session' },
  { name: 'compress', description: 'Alias for /compact', category: 'session' },
  { name: 'undo', description: 'Remove last assistant turn', category: 'session' },
  { name: 'retry', description: 'Re-generate last assistant turn', category: 'session' },
  { name: 'help', description: 'List all commands', category: 'meta' },
  { name: 'version', description: 'Show version', category: 'meta' },
  { name: 'status', description: 'Show health summary', category: 'meta' },
  { name: 'debug', description: 'Toggle debug overlay', category: 'meta' },
  { name: 'tools', description: 'Open tools page', category: 'tools' },
  { name: 'skills', description: 'Open skills page', category: 'tools' },
  { name: 'model', args: '<model_id>', description: 'Switch model', category: 'tools' },
  { name: 'memory', description: 'Open memory page', category: 'tools' },
  { name: 'persona', description: 'Open persona editor', category: 'tools' },
  { name: 'usage', description: 'Show usage card', category: 'ops' },
  { name: 'fast', description: 'Switch to a faster model', category: 'ops' },
  { name: 'web', args: '<query>', description: 'Web search', category: 'external' },
  { name: 'image', args: '<prompt>', description: 'Image generation', category: 'external' },
  { name: 'browse', args: '<url>', description: 'Browse URL', category: 'external' },
  { name: 'code', args: '<task>', description: 'Code generation', category: 'external' },
  { name: 'shell', args: '<cmd>', description: 'Shell exec through allowlist', category: 'external' },
];

export function parseSlashCommand(text: string): ParsedSlashCommand | null {
  const raw = text.trim();
  if (!raw.startsWith('/')) return null;
  const parts = tokenize(raw.slice(1));
  if (parts.length === 0) return null;
  const command = parts[0] ?? '';
  const args: string[] = [];
  const options: Record<string, string | boolean> = {};
  for (let i = 1; i < parts.length; i += 1) {
    const token = parts[i] ?? '';
    if (token.startsWith('--') && token.length > 2) {
      const key = token.slice(2);
      if (key.includes('=')) {
        const [name, ...rest] = key.split('=');
        if (name) options[name] = rest.join('=');
      } else if (parts[i + 1] && !parts[i + 1]?.startsWith('--')) {
        options[key] = parts[i + 1] ?? '';
        i += 1;
      } else {
        options[key] = true;
      }
    } else {
      args.push(token);
    }
  }
  return { raw, command, args, options };
}

export function slashMatches(input: string): SlashCommand[] {
  if (!input.startsWith('/')) return [];
  const needle = input.slice(1).split(/\s+/, 1)[0]?.toLowerCase() ?? '';
  return COMMANDS.filter((cmd) => cmd.name.startsWith(needle)).slice(0, 8);
}

function tokenize(input: string): string[] {
  const out: string[] = [];
  let cur = '';
  let quote: '"' | "'" | null = null;
  for (let i = 0; i < input.length; i += 1) {
    const ch = input[i] ?? '';
    if (quote) {
      if (ch === quote) quote = null;
      else cur += ch;
    } else if (ch === '"' || ch === "'") {
      quote = ch;
    } else if (/\s/.test(ch)) {
      if (cur) {
        out.push(cur);
        cur = '';
      }
    } else {
      cur += ch;
    }
  }
  if (cur) out.push(cur);
  return out;
}
