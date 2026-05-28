import { Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Search, type SearchResult } from '@/lib/api';

export function SearchSnippet({ result }: { result: Pick<SearchResult, 'snippet' | 'snippet_parts'> }) {
  const parts = result.snippet_parts?.length
    ? result.snippet_parts
    : [{ text: result.snippet, highlight: false }];

  return (
    <>
      {parts.map((part, index) =>
        part.highlight ? (
          <em key={index} className="rounded bg-sky-500/15 px-0.5 font-semibold not-italic text-sky-700 dark:text-sky-200">
            {part.text}
          </em>
        ) : (
          <span key={index}>{part.text}</span>
        ),
      )}
    </>
  );
}

export function GlobalSearch() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [debounced, setDebounced] = useState('');

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setOpen(true);
      }
      if (event.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(input.trim()), 200);
    return () => window.clearTimeout(id);
  }, [input]);

  const results = useQuery({
    queryKey: ['global-search', debounced],
    queryFn: () => Search.messages(debounced, 20),
    enabled: open && debounced.length > 1,
  });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/40 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Global search">
      <div className="mx-auto mt-16 max-w-2xl overflow-hidden rounded-2xl border border-black/10 bg-white shadow-2xl dark:border-white/15 dark:bg-slate-950">
        <div className="border-b border-black/5 p-3 dark:border-white/10">
          <input
            autoFocus
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Search sessions…"
            className="w-full bg-transparent px-2 py-2 text-sm outline-none"
          />
        </div>
        <div className="max-h-[60vh] overflow-auto p-2">
          {results.isFetching && <p className="p-3 text-xs text-black/55 dark:text-white/55">Searching…</p>}
          {debounced.length <= 1 && <p className="p-3 text-xs text-black/55 dark:text-white/55">Type at least 2 characters.</p>}
          {results.data?.results.length === 0 && <p className="p-3 text-xs text-black/55 dark:text-white/55">No results.</p>}
          {results.data?.results.map((result) => (
            <Link
              key={`${result.session_id}-${result.message_index}`}
              to="/sessions"
              onClick={() => setOpen(false)}
              className="block rounded-lg p-3 hover:bg-sky-500/10 focus:bg-sky-500/10 focus:outline-none"
            >
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium">{result.session_title}</p>
                <span className="text-[10px] text-black/45 dark:text-white/45">#{result.message_index}</span>
              </div>
              <p className="mt-1 text-xs leading-5 text-black/65 dark:text-white/65">
                <SearchSnippet result={result} />
              </p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
