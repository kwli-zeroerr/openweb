import { writable, type Writable } from 'svelte/store';

type TableCollapseState = Record<string, boolean>;

const isBrowser = typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';

const STORAGE_PREFIX = 'table-collapse-v2:';

function storageKey(key: string): string {
  return `${STORAGE_PREFIX}${key}`;
}

function readFromStorage(key: string): boolean | undefined {
  if (!isBrowser) return undefined;
  try {
    const raw = window.localStorage.getItem(storageKey(key));
    if (raw == null) return undefined;
    return JSON.parse(raw) as boolean;
  } catch {
    return undefined;
  }
}

function writeToStorage(key: string, value: boolean): void {
  if (!isBrowser) return;
  try {
    window.localStorage.setItem(storageKey(key), JSON.stringify(value));
  } catch {
    // ignore
  }
}

const internalStore: Writable<TableCollapseState> = writable({});

export function getCollapsed(key: string, defaultCollapsed: boolean): boolean {
  let current: TableCollapseState = {};
  let value: boolean | undefined;
  internalStore.update((s) => {
    current = s;
    return s;
  });
  if (key in current) return current[key];
  const stored = readFromStorage(key);
  return stored !== undefined ? stored : defaultCollapsed;
}

export function setCollapsed(key: string, collapsed: boolean): void {
  internalStore.update((s) => ({ ...s, [key]: collapsed }));
  writeToStorage(key, collapsed);
}


