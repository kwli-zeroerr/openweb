import { ragAPI, type RagFlowDatasetsResponse, type RagFlowRetrievalRequest, type RagFlowRetrievalResponse } from '$lib/apis/rag';

export async function listDatasets(): Promise<RagFlowDatasetsResponse> {
  return await ragAPI.ragflowListDatasets();
}

export async function retrieval(req: RagFlowRetrievalRequest): Promise<RagFlowRetrievalResponse> {
  return await ragAPI.ragflowRetrieval(req);
}

