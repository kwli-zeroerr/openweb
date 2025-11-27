import { writable } from 'svelte/store';
import type { LLMModel } from '$lib/apis/rag';

export const modelsStore = writable<LLMModel[]>([]);

