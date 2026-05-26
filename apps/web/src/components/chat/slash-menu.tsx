import { COMMANDS, slashMatches, type SlashCommand } from '@/lib/slash-commands';

export function SlashMenu({ input, onPick }: { input: string; onPick: (command: SlashCommand) => void }) {
  const matches = slashMatches(input);
  if (!input.startsWith('/') || matches.length === 0) return null;
  return (
    <div
      role="listbox"
      aria-label="Slash command suggestions"
      className="rounded-lg border border-black/10 bg-white p-2 text-xs shadow-lg dark:border-white/15 dark:bg-slate-950"
    >
      {matches.map((cmd) => (
        <button
          key={cmd.name}
          type="button"
          role="option"
          onClick={() => onPick(cmd)}
          className="flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left hover:bg-sky-500/10 focus:bg-sky-500/10 focus:outline-none"
        >
          <span className="font-medium">/{cmd.name} {cmd.args ?? ''}</span>
          <span className="truncate text-black/55 dark:text-white/55">{cmd.description}</span>
        </button>
      ))}
      <p className="mt-1 px-2 text-[10px] text-black/45 dark:text-white/45">{COMMANDS.length} commands available</p>
    </div>
  );
}
