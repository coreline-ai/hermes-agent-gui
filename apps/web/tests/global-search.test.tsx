import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SearchSnippet } from '@/components/global-search';

describe('SearchSnippet', () => {
  it('renders snippet parts as React text, not raw HTML', () => {
    render(
      <SearchSnippet
        result={{
          snippet: '<img src=x onerror=alert(1)> redis',
          snippet_parts: [
            { text: '<img src=x onerror=alert(1)> ', highlight: false },
            { text: 'redis', highlight: true },
          ],
        }}
      />,
    );

    expect(document.querySelector('img')).toBeNull();
    expect(screen.getByText(/<img src=x onerror=alert\(1\)>/)).toBeTruthy();
    expect(screen.getByText('redis').tagName.toLowerCase()).toBe('em');
  });
});
