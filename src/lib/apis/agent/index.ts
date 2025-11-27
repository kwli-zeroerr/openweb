/**
 * Agent API客户端
 * 包含知识库检索和工作流相关API
 */
import { WEBUI_API_BASE_URL } from '$lib/constants';

// RAGFlow检索接口类型
export interface RagFlowRetrievalRequest {
  question: string; // 查询问题
  dataset_id?: string | null; // Dataset ID（单数，向后兼容）
  dataset_ids?: string[] | null; // Dataset ID列表（支持多知识库检索）
  document_ids?: string[] | null; // 可选的文档ID列表
  page?: number | null; // 页码
  page_size?: number | null; // 每页结果数
  similarity_threshold?: number | null; // 相似度阈值（0-1）
  vector_similarity_weight?: number | null; // 向量相似度权重（0-1）
  top_k?: number | null; // 向量检索的top_k
  keyword?: boolean | null; // 是否启用关键词匹配
  highlight?: boolean | null; // 是否启用高亮
}

export interface RagFlowRetrievalResponse {
  question: string;
  total: number; // 总结果数
  documents: Array<{
    content: string;
    metadata: {
      document_id?: string;
      document_name?: string;
      kb_id?: string;
      chunk_id?: string;
      similarity?: number;
      vector_similarity?: number;
      term_similarity?: number;
      highlight?: string;
    };
  }>;
  scores: number[]; // 相似度分数列表
  retrieval_time?: number | null; // 检索耗时（秒）
}

export interface RagFlowDataset {
  id: string;
  name: string;
  description?: string;
  document_count?: number;
  chunk_count?: number;
}

export interface RagFlowDatasetsResponse {
  datasets: RagFlowDataset[];
  total: number;
}

export interface LLMModel {
  id: string;
  name: string;
  provider: string;
  description: string;
  capabilities: Record<string, any>;
}

export class AgentAPIClient {
  private baseUrl = `${WEBUI_API_BASE_URL}/agent`;

  /**
   * 获取RAGFlow datasets列表（用于前端选择）
   */
  async ragflowListDatasets(): Promise<RagFlowDatasetsResponse> {
    const response = await fetch(`${this.baseUrl}/retrieval/datasets`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.token || ''}`
      }
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  }

  /**
   * RAGFlow知识库检索
   */
  async ragflowRetrieval(req: RagFlowRetrievalRequest): Promise<RagFlowRetrievalResponse> {
    const response = await fetch(`${this.baseUrl}/retrieval`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.token || ''}`
      },
      body: JSON.stringify(req)
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  }
}

// 导出单例实例
export const agentAPI = new AgentAPIClient();

