import { writable } from 'svelte/store';
import type { RagFlowDataset } from '$lib/apis/agent';

export const datasetsStore = writable<RagFlowDataset[]>([]);

