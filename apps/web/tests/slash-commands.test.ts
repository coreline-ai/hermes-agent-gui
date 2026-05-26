import { describe, expect, it } from 'vitest';
import { COMMANDS, parseSlashCommand, slashMatches } from '@/lib/slash-commands';

describe('slash commands', () => {
  it('defines 22 commands', () => {
    expect(COMMANDS).toHaveLength(22);
    expect(COMMANDS.map((cmd) => cmd.name)).toContain('model');
  });

  it('parses /model args and options', () => {
    expect(parseSlashCommand('/model gpt-4 --temp 0.7')).toEqual({
      raw: '/model gpt-4 --temp 0.7',
      command: 'model',
      args: ['gpt-4'],
      options: { temp: '0.7' },
    });
  });

  it('returns prefix matches', () => {
    expect(slashMatches('/mo').map((cmd) => cmd.name)).toEqual(['model']);
  });
});
