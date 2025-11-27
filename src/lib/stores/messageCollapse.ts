import { writable, type Writable } from 'svelte/store';

type MessageCollapseState = Record<string, boolean>;

const isBrowser = typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';

const STORAGE_PREFIX = 'message-collapse-v1:';

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

const internalStore: Writable<MessageCollapseState> = writable({});

export function getMessageCollapsed(key: string, defaultCollapsed: boolean = false): boolean {
  let current: MessageCollapseState = {};
  let value: boolean | undefined;
  internalStore.update((s) => {
    current = s;
    return s;
  });
  if (key in current) return current[key];
  const stored = readFromStorage(key);
  return stored !== undefined ? stored : defaultCollapsed;
}

export function setMessageCollapsed(key: string, collapsed: boolean): void {
  internalStore.update((s) => ({ ...s, [key]: collapsed }));
  writeToStorage(key, collapsed);
}

export function toggleMessageCollapsed(key: string): boolean {
  const current = getMessageCollapsed(key, false);
  const next = !current;
  setMessageCollapsed(key, next);
  return next;
}



