/**
 * 统一RAG API客户端
 */
import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface RAGConfig {
  embedding: {
    engine: string;
    model: string;
    batch_size: number;
    query_prefix?: string;
    content_prefix?: string;
  };
  reranking: {
    engine: string;
    model: string;
  };
  vector_db: {
    db_type: string;
    data_path: string;
    uri?: string;
    dimension: number;
  };
  llm: {
    provider: string;
    model: string;
    temperature: number;
    max_tokens: number;
  };
  retrieval: {
    limit: number;
    rerank_limit: number;
    similarity_threshold: number;
  };
  cache: {
    enable: boolean;
    ttl: number;
  };
  performance: {
    max_concurrent_requests: number;
    request_timeout: number;
  };
}

export interface ExcelExtractRequest {
  dir_path?: string;
  limit_per_file?: number;
}

export interface ExcelSegment {
  file: string;
  sheet: string;
  row: number;
  title: string;
  content: string;
  questions: string;
}

export interface ExcelExtractResponse {
  total_files: number;
  total_segments: number;
  segments: ExcelSegment[];
  groups?: Array<{ file: string; sheets: Array<{ name: string; count: number; segments: ExcelSegment[] }>; }>;
}

export interface SaveExcelSegmentsRequest {
  knowledge_id: string;
  dir_path?: string;
  limit_per_file?: number;
}

export interface SaveExcelSegmentsResponse {
  knowledge_id: string;
  total_segments: number;
  total_files_created: number;
  file_ids: string[];
}

export interface SavedExcelFile {
  file_id: string;
  filename: string;
  original_file: string;
  sheet: string;
  segment_count: number;
  created_at?: string;
}

export interface GetSavedExcelFilesResponse {
  knowledge_id: string;
  knowledge_name: string;
  total_files: number;
  files: SavedExcelFile[];
}

export interface SavedFileSegmentsResponse {
  file_id: string;
  original_file: string;
  sheets: Array<{ name: string; segments: Array<{ title: string; content: string; questions?: string }>; }>;
}

export interface ListExcelFilesRequest {
  dir_path: string; // 目录路径
  knowledge_id?: string | null; // 可选，用于构建知识库目录路径
}

export interface ListExcelFilesResponse {
  files: Array<{ filename: string; size: number; mtime: number }>; // 文件列表
  dir_path: string; // 实际使用的目录路径
  total: number; // 文件总数
}

export interface MigrateExcelDirectToRagFlowRequest {
  dir_path: string; // 目录路径
  selected_files: string[]; // 用户选择的文件名列表
  dataset_id?: string | null; // 如果提供，使用现有dataset；否则创建新dataset
  dataset_name?: string | null; // 创建新dataset时的名称
  document_name?: string | null; // 文档名称，默认为Excel文件名
  mode?: 'skip' | 'overwrite'; // skip | overwrite
  limit_segments?: number | null; // 限制每个sheet处理的分段数量
  auto_delete_duplicates?: boolean | null; // 自动删除重名的数据集或文档
}

export interface MigrateExcelDirectToRagFlowResponse {
  dataset_id: string;
  document_id: string; // 第一个document_id作为参考
  documents: Array<{ file_name?: string; sheet_name: string; document_id: string }>; // 所有创建的documents
  files_processed: number;
  sheets_processed: number;
  segments_processed: number;
  chunks_created: number;
  message: string;
}

// RAGFlow检索接口
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

export interface TestQueryRequest {
  query: string;
  knowledge_id: string;
  limit?: number;
  rerank_limit?: number;
}

export interface TestQueryResponse {
  query: string;
  answer: string;
  document_count: number;
  processing_time: number;
  metadata?: Record<string, any>;
  sample_documents?: Array<{
    content: string;
    metadata: Record<string, any>;
  }>;
}

export interface ServiceInfo {
  embedding: {
    engine: string;
    model: string;
    batch_size: number;
    cached_models: string[];
    query_prefix?: string;
    content_prefix?: string;
  };
  reranking: {
    engine: string;
    model: string;
    cached_models: string[];
    api_base_url?: string;
  };
  vector_db: {
    type: string;
    data_path: string;
  };
  config: {
    retrieval_limit: number;
    rerank_limit: number;
    similarity_threshold: number;
  };
}

export interface HealthCheck {
  status: string;
  config_loaded: boolean;
  services: {
    embedding: string;
    reranking: string;
    vector_db: string;
  };
  error?: string;
}

export interface LLMModel {
  id: string;
  name: string;
  provider: string;
  description: string;
  capabilities: Record<string, any>;
}

export interface ModelsResponse {
  models: LLMModel[];
  total: number;
}

export interface VectorizeRequest {
  text: string;
  prefix?: string;
  knowledge_id: string;
}

export interface VectorizeResponse {
  embedding: number[];
  dimension: number;
  model: string;
}

export interface BatchVectorizeRequest {
  texts: string[];
  prefix?: string;
  knowledge_id: string;
}

export interface BatchVectorizeResponse {
  embeddings: number[][];
  dimensions: number[];
  model: string;
}

export class RAGAPIClient {
  private baseUrl = `${WEBUI_API_BASE_URL}/agent`;  // 迁移到Agent API
  private async tryFetchJson(url: string): Promise<any | null> {
    try {
      const resp = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.token || ''}`
        }
      });
      if (!resp.ok) return null;
      const contentType = resp.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) return null;
      return await resp.json();
    } catch {
      return null;
    }
  }

  private normalizeModelsPayload(payload: any): ModelsResponse {
    if (!payload) return { models: [], total: 0 };
    // 常见字段：models | data | items
    const arr = Array.isArray(payload?.models)
      ? payload.models
      : Array.isArray(payload?.data)
      ? payload.data
      : Array.isArray(payload?.items)
      ? payload.items
      : Array.isArray(payload)
      ? payload
      : [];
    const models: LLMModel[] = arr.map((m: any) => ({
      id: m?.id ?? m?.model ?? m?.name ?? String(Math.random()).slice(2),
      name: m?.name ?? m?.id ?? m?.model ?? 'model',
      provider: m?.provider ?? m?.owner ?? 'unknown',
      description: m?.description ?? '',
      capabilities: m?.capabilities ?? {}
    }));
    return { models, total: models.length };
  }

  /**
   * 获取RAG配置
   */
  async getConfig(): Promise<RAGConfig> {
    try {
      const response = await fetch(`${this.baseUrl}/config`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.token || ''}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error("Failed to get RAG config:", error);
      throw error;
    }
  }

  /**
   * 更新RAG配置
   */
  async updateConfig(config: Partial<RAGConfig>): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/config`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.token || ''}`
        },
        body: JSON.stringify(config)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error("Failed to update RAG config:", error);
      throw error;
    }
  }



  /**
   * Excel 分段提取
   */
  async extractExcel(request: ExcelExtractRequest): Promise<ExcelExtractResponse> {
    const response = await fetch(`${this.baseUrl}/extract-excel`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(request || {})
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  }

  /**
   * 保存Excel分段到知识库
   */
  async saveExcelSegments(request: SaveExcelSegmentsRequest): Promise<SaveExcelSegmentsResponse> {
    // 获取 token，优先从 localStorage，如果没有则从 sessionStorage，最后尝试从 document.cookie
    let token = '';
    if (typeof localStorage !== 'undefined') {
      token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
    }
    if (!token && typeof sessionStorage !== 'undefined') {
      token = sessionStorage.getItem('token') || sessionStorage.getItem('access_token') || '';
    }
    
    const headers: Record<string, string> = {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${this.baseUrl}/save-excel-segments`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request)
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
    }
    
    return await response.json();
  }

  /**
   * 获取已保存的Excel文件列表
   */
  async getSavedExcelFiles(knowledge_id: string): Promise<GetSavedExcelFilesResponse> {
    const response = await fetch(`${this.baseUrl}/saved-excel-files/${knowledge_id}`, {
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

  // removed duplicate deleteSavedExcelFile definition above

  /**
   * 获取已保存聚合文件的分段
   */
  async getSavedFileSegments(file_id: string): Promise<SavedFileSegmentsResponse> {
    const response = await fetch(`${this.baseUrl}/saved-excel-file/${file_id}/segments`, {
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
   * 列出目录下的Excel文件（仅返回文件名，不暴露完整路径）
   */
  async listExcelFiles(req: ListExcelFilesRequest): Promise<ListExcelFilesResponse> {
    const response = await fetch(`${this.baseUrl}/ragflow/list-excel-files`, {
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

  /**
   * 直接从Excel文件迁移到RAGFlow（不需要先保存到知识库）
   */
  async migrateExcelDirectToRagFlow(req: MigrateExcelDirectToRagFlowRequest): Promise<MigrateExcelDirectToRagFlowResponse> {
    const response = await fetch(`${this.baseUrl}/ragflow/migrate-excel-direct`, {
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

  /**
   * 获取RAGFlow datasets列表（用于前端选择）
   */
  async ragflowListDatasets(): Promise<RagFlowDatasetsResponse> {
    const response = await fetch(`${this.baseUrl}/ragflow/datasets`, {
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
    const response = await fetch(`${this.baseUrl}/ragflow/retrieval`, {
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


  /**
   * 删除单个已保存的Excel提取文件
   */
  async deleteSavedExcelFile(file_id: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${this.baseUrl}/saved-excel-file/${file_id}`, {
      method: 'DELETE',
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
   * 删除指定知识库下所有已保存的Excel提取文件
   */
  async deleteAllSavedExcelFiles(knowledge_id: string): Promise<{ success: boolean; message: string; deleted_count: number }> {
    const response = await fetch(`${this.baseUrl}/saved-excel-files/${knowledge_id}/all`, {
      method: 'DELETE',
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
   * 测试查询
   */
  async testQuery(request: TestQueryRequest): Promise<TestQueryResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/test`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.token || ''}`
        },
        body: JSON.stringify(request)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error("Failed to execute test query:", error);
      throw error;
    }
  }

  /**
   * 获取服务信息
   */
  async getServiceInfo(): Promise<ServiceInfo> {
    try {
      const response = await fetch(`${this.baseUrl}/service-info`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.token || ''}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error("Failed to get service info:", error);
      throw error;
    }
  }

  /**
   * 清空缓存
   */
  async clearCache(): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/clear-cache`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.token || ''}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
    } catch (error) {
      console.error("Failed to clear cache:", error);
      throw error;
    }
  }

  /**
   * 健康检查
   */
  async healthCheck(): Promise<HealthCheck> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error("Failed to perform health check:", error);
      throw error;
    }
  }

  /**
   * 获取可用的LLM模型列表
   */
  async getAvailableModels(): Promise<ModelsResponse> {
    // 多端点探测，命中即用
    const candidates = [
      `${this.baseUrl}/models`,
      `${WEBUI_API_BASE_URL}/api/v1/models`,
      `${WEBUI_API_BASE_URL}/llm/models`,
      `${WEBUI_API_BASE_URL}/models`,
      `${WEBUI_API_BASE_URL}/v1/models`,
      `${WEBUI_API_BASE_URL}/openai/models`
    ];
    for (const url of candidates) {
      const payload = await this.tryFetchJson(url);
      const res = this.normalizeModelsPayload(payload);
      if (res.total > 0) return res;
    }
    return { models: [], total: 0 };
  }

  /**
   * 向量化单个文本
   */
  async vectorizeText(request: VectorizeRequest): Promise<VectorizeResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/vectorize`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.token || ''}`
        },
        body: JSON.stringify(request)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error("Failed to vectorize text:", error);
      throw error;
    }
  }

  /**
   * 批量向量化文本
   */
  async batchVectorizeTexts(request: BatchVectorizeRequest): Promise<BatchVectorizeResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/vectorize/batch`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.token || ''}`
        },
        body: JSON.stringify(request)
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error("Failed to batch vectorize texts:", error);
      throw error;
    }
  }


  /**
   * 获取配置摘要
   */
  async getConfigSummary(): Promise<{
    embedding_model: string;
    reranking_model: string;
    vector_db_type: string;
    retrieval_limit: number;
    similarity_threshold: number;
  }> {
    try {
      const config = await this.getConfig();
      return {
        embedding_model: config.embedding.model,
        reranking_model: config.reranking.model,
        vector_db_type: config.vector_db.db_type,
        retrieval_limit: config.retrieval.limit,
        similarity_threshold: config.retrieval.similarity_threshold
      };
    } catch (error) {
      console.error("Failed to get config summary:", error);
      throw error;
    }
  }


  /**
   * 验证配置
   */
  async validateConfig(config: Partial<RAGConfig>): Promise<{
    valid: boolean;
    errors: string[];
  }> {
    const errors: string[] = [];

    // 验证嵌入配置
    if (config.embedding) {
      if (!config.embedding.model) {
        errors.push("嵌入模型不能为空");
      }
      if (config.embedding.batch_size && config.embedding.batch_size < 1) {
        errors.push("批处理大小必须大于0");
      }
    }

    // 验证重排配置
    if (config.reranking) {
      if (config.reranking.engine && !config.reranking.model) {
        errors.push("启用重排时必须指定重排模型");
      }
    }

    // 验证检索配置
    if (config.retrieval) {
      if (config.retrieval.limit && config.retrieval.limit < 1) {
        errors.push("检索限制必须大于0");
      }
      if (config.retrieval.similarity_threshold && 
          (config.retrieval.similarity_threshold < 0 || config.retrieval.similarity_threshold > 1)) {
        errors.push("相似度阈值必须在0-1之间");
      }
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }
}

// 导出单例实例
export const ragAPI = new RAGAPIClient();
