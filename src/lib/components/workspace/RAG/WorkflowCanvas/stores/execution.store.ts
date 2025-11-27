import { writable } from 'svelte/store';

export interface ExecutionState {
  question: string;
  retrieved_context: string | null;
  llm_output: string | null;
  total?: number;
  documents?: any[];
  timings?: Record<string, number>;
}

export const executionStore = writable<ExecutionState>({
  question: '',
  retrieved_context: null,
  llm_output: null
});

