import { describe, expect, it } from 'vitest';
import { estimateCost } from '@/lib/usage-pricing';

describe('usage pricing', () => {
  it('matches backend gpt-4o input pricing', () => {
    expect(estimateCost('gpt-4o', 1_000_000, 0)).toBe(2.5);
  });
});
