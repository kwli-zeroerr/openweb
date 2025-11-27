import { ragAPI, type LLMModel } from "$lib/apis/rag";

let cachedModels: LLMModel[] | null = null;
let loadingPromise: Promise<LLMModel[]> | null = null;

export async function fetchModelsOnce(): Promise<LLMModel[]> {
  if (cachedModels) return cachedModels;
  if (loadingPromise) return loadingPromise;
  loadingPromise = (async () => {
    try {
      const resp = await ragAPI.getAvailableModels();
      cachedModels = resp.models || [];
      return cachedModels;
    } catch (e) {
      console.error("fetchModelsOnce failed:", e);
      cachedModels = [];
      return cachedModels;
    } finally {
      loadingPromise = null;
    }
  })();
  return loadingPromise;
}

export function getCachedModels(): LLMModel[] | null {
  return cachedModels;
}

