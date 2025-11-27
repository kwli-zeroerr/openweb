import { agentAPI, type RagFlowDatasetsResponse, type RagFlowRetrievalRequest, type RagFlowRetrievalResponse } from '$lib/apis/agent';

export async function listDatasets(): Promise<RagFlowDatasetsResponse> {
  return await agentAPI.ragflowListDatasets();
}

export async function retrieval(req: RagFlowRetrievalRequest): Promise<RagFlowRetrievalResponse> {
  return await agentAPI.ragflowRetrieval(req);
}

