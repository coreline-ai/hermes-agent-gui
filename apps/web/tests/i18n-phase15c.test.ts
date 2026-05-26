import { describe, expect, it } from 'vitest';
import en from '@/locales/en.json';
import ko from '@/locales/ko.json';

const PLATFORM_IDS = [
  'telegram',
  'discord',
  'slack',
  'whatsapp',
  'signal',
  'matrix',
  'mattermost',
  'email',
  'sms',
  'imessage',
  'dingtalk',
  'feishu',
  'wecom',
  'wechat',
  'webhook',
  'home_assistant',
] as const;

describe('Phase 15c i18n keys', () => {
  it('contains platform label/help keys for all 16 platforms in en and ko', () => {
    for (const locale of [en, ko]) {
      for (const id of PLATFORM_IDS) {
        expect(locale[`messaging.platform.${id}.label` as keyof typeof locale]).toBeTruthy();
        expect(locale[`messaging.platform.${id}.help` as keyof typeof locale]).toBeTruthy();
      }
    }
  });

  it('adds at least 50 messaging/profile keys per locale', () => {
    const count = (catalog: Record<string, string>) =>
      Object.keys(catalog).filter((key) => key.startsWith('messaging.') || key.startsWith('profiles.')).length;
    expect(count(en)).toBeGreaterThanOrEqual(50);
    expect(count(ko)).toBeGreaterThanOrEqual(50);
  });
});
