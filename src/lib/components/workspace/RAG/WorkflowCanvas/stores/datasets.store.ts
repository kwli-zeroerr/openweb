import { writable } from 'svelte/store';
import type { RagFlowDataset } from '$lib/apis/rag';

export const datasetsStore = writable<RagFlowDataset[]>([]);

