export const USAGE_PRICING_USD_PER_1M: Record<string, { input: number; output: number }> = {
  'gpt-4o': { input: 2.5, output: 10 },
  'gpt-4o-mini': { input: 0.15, output: 0.6 },
  'claude-opus-4': { input: 15, output: 75 },
  'claude-sonnet-4': { input: 3, output: 15 },
  'gemini-2.5-pro': { input: 1.25, output: 10 },
};

export function estimateCost(modelId: string, inputTokens: number, outputTokens: number): number {
  const price = USAGE_PRICING_USD_PER_1M[modelId] ?? { input: 0, output: 0 };
  return Number(((inputTokens / 1_000_000) * price.input + (outputTokens / 1_000_000) * price.output).toFixed(6));
}
