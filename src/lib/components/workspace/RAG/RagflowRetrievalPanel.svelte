<!--
  RAGFlow检索配置面板
  用于配置和测试RAGFlow知识库检索功能
-->
<script lang="ts">
  import { onMount } from "svelte";
  import { ragAPI, type RagFlowRetrievalRequest, type RagFlowRetrievalResponse, type RagFlowDataset } from "$lib/apis/rag";
  import { toast } from "svelte-sonner";

  export let knowledgeId: string;

  // 检索配置
  let selectedDatasetIds: string[] = []; // 支持多选的知识库ID列表
  let selectedDatasetNames: Map<string, string> = new Map(); // ID到名称的映射
  let documentIds: string = ""; // 逗号分隔的文档ID列表
  let question: string = "";
  let page: number = 1;
  let pageSize: number = 10;
  let similarityThreshold: number = 0.2;
  let vectorSimilarityWeight: number = 0.3;
  let topK: number = 1024;
  let enableKeyword: boolean = true;
  let enableHighlight: boolean = true;

  // Dataset列表
  let datasets: RagFlowDataset[] = [];
  let loadingDatasets: boolean = false;

  // 检索状态
  let searching: boolean = false;
  let retrievalResult: RagFlowRetrievalResponse | null = null;
  let error: string | null = null;

  // 加载datasets列表
  async function loadDatasets() {
    try {
      loadingDatasets = true;
      const response = await ragAPI.ragflowListDatasets();
      datasets = response.datasets || [];
      
      // 构建ID到名称的映射
      selectedDatasetNames = new Map();
      datasets.forEach(ds => {
        selectedDatasetNames.set(ds.id, ds.name);
      });
      
      // 如果有knowledgeId且是dataset_id格式，尝试匹配
      if (knowledgeId && /^[a-f0-9]{32}$/i.test(knowledgeId)) {
        const matched = datasets.find(ds => ds.id === knowledgeId);
        if (matched) {
          selectedDatasetIds = [matched.id];
        } else {
          // 如果没有找到匹配的，仍使用knowledgeId作为dataset_id
          selectedDatasetIds = [knowledgeId];
          selectedDatasetNames.set(knowledgeId, knowledgeId);
        }
      }
    } catch (e: any) {
      console.error("加载datasets失败:", e);
      toast.error("加载知识库列表失败: " + (e.message || "未知错误"));
    } finally {
      loadingDatasets = false;
    }
  }

  // 切换知识库选择状态
  function toggleDataset(datasetId: string) {
    const index = selectedDatasetIds.indexOf(datasetId);
    if (index >= 0) {
      selectedDatasetIds = selectedDatasetIds.filter(id => id !== datasetId);
    } else {
      selectedDatasetIds = [...selectedDatasetIds, datasetId];
    }
  }

  // 全选/取消全选
  function toggleAllDatasets() {
    if (selectedDatasetIds.length === datasets.length) {
      selectedDatasetIds = [];
    } else {
      selectedDatasetIds = datasets.map(ds => ds.id);
    }
  }

  onMount(() => {
    loadDatasets();
  });

  async function performRetrieval() {
    if (selectedDatasetIds.length === 0) {
      toast.error("请至少选择一个知识库");
      return;
    }
    if (!question.trim()) {
      toast.error("请输入查询问题");
      return;
    }

    searching = true;
    error = null;
    retrievalResult = null;

    try {
      const req: RagFlowRetrievalRequest = {
        question: question.trim(),
        dataset_ids: selectedDatasetIds.length > 0 ? selectedDatasetIds : null,
        document_ids: documentIds.trim() 
          ? documentIds.split(",").map(id => id.trim()).filter(id => id)
          : null,
        page: page,
        page_size: pageSize,
        similarity_threshold: similarityThreshold,
        vector_similarity_weight: vectorSimilarityWeight,
        top_k: topK,
        keyword: enableKeyword,
        highlight: enableHighlight,
      };

      const result = await ragAPI.ragflowRetrieval(req);
      retrievalResult = result;
      toast.success(`检索完成，找到 ${result.total} 个结果`);
    } catch (e: any) {
      error = e.message || "检索失败";
      toast.error(error || "检索失败");
      console.error("Retrieval error:", e);
    } finally {
      searching = false;
    }
  }

  function formatScore(score: number): string {
    return (score * 100).toFixed(2) + "%";
  }

  function extractHighlightText(highlight: string | undefined): string {
    if (!highlight) return "";
    // 移除HTML标签，保留高亮标记
    return highlight.replace(/<em>/g, "<mark>").replace(/<\/em>/g, "</mark>");
  }
</script>

<div class="h-full flex flex-col bg-white dark:bg-gray-800">
  <!-- 配置区域 -->
  <div class="flex-shrink-0 p-4 border-b border-gray-200 dark:border-gray-700 space-y-4 overflow-y-auto" style="max-height: 70vh;">
    <div class="flex items-center space-x-2 mb-4">
      <i class="fas fa-search text-indigo-500"></i>
      <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">RAGFlow检索配置</h3>
    </div>

    <!-- 知识库多选 -->
    <div>
      <div class="flex items-center justify-between mb-1">
        <label for="dataset-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300">
          知识库 <span class="text-red-500">*</span>
        </label>
        {#if datasets.length > 0}
          <button
            type="button"
            on:click={toggleAllDatasets}
            class="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300"
          >
            {selectedDatasetIds.length === datasets.length ? '取消全选' : '全选'}
          </button>
        {/if}
      </div>
      {#if loadingDatasets}
        <div class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 flex items-center">
          <i class="fas fa-spinner fa-spin mr-2"></i>
          加载知识库列表...
        </div>
      {:else if datasets.length === 0}
        <div class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
          暂无可用知识库
        </div>
      {:else}
        <div class="max-h-64 overflow-y-auto border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 p-3 space-y-2">
          {#each datasets as dataset}
            {@const isSelected = selectedDatasetIds.includes(dataset.id)}
            <label class="flex items-center space-x-3 px-3 py-2.5 rounded hover:bg-gray-50 dark:hover:bg-gray-600 cursor-pointer transition-colors">
              <input
                type="checkbox"
                checked={isSelected}
                on:change={() => toggleDataset(dataset.id)}
                class="w-5 h-5 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500 flex-shrink-0"
              />
              <div class="flex-1 min-w-0">
                <div class="text-base font-medium text-gray-900 dark:text-gray-100">
                  {dataset.name}
                </div>
                <div class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                  {#if dataset.document_count !== undefined}
                    文档: {dataset.document_count} | 分段: {dataset.chunk_count || 0}
                  {/if}
                </div>
              </div>
            </label>
          {/each}
        </div>
        {#if selectedDatasetIds.length > 0}
          <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
            <i class="fas fa-info-circle mr-1"></i>
            已选择 <span class="font-semibold">{selectedDatasetIds.length}</span> 个知识库:
            <span class="ml-1">
              {selectedDatasetIds.map(id => selectedDatasetNames.get(id) || id).join(', ')}
            </span>
          </p>
        {/if}
      {/if}
    </div>

    <!-- 查询问题 -->
    <div>
      <label for="question" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        查询问题 <span class="text-red-500">*</span>
      </label>
      <textarea
        id="question"
        bind:value={question}
        placeholder="输入要查询的问题..."
        rows="2"
        class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:focus:ring-indigo-800 resize-none"
      ></textarea>
    </div>

    <!-- 高级配置 - 折叠面板 -->
    <details class="group">
      <summary class="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-indigo-600 dark:hover:text-indigo-400 flex items-center">
        <i class="fas fa-cog mr-2"></i>
        高级配置
        <i class="fas fa-chevron-down ml-auto group-open:rotate-180 transition-transform"></i>
      </summary>
      
      <div class="mt-3 space-y-3 pl-6 border-l-2 border-gray-200 dark:border-gray-600">
        <!-- 文档ID过滤 -->
        <div>
          <label for="document-ids" class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
            文档ID过滤（可选，逗号分隔）
          </label>
          <input
            id="document-ids"
            type="text"
            bind:value={documentIds}
            placeholder="留空则检索所有文档"
            class="w-full px-2 py-1.5 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700"
          />
        </div>

        <!-- 分页设置 -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="page" class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">页码</label>
            <input
              id="page"
              type="number"
              bind:value={page}
              min="1"
              class="w-full px-2 py-1.5 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700"
            />
          </div>
          <div>
            <label for="page-size" class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">每页结果数</label>
            <input
              id="page-size"
              type="number"
              bind:value={pageSize}
              min="1"
              max="100"
              class="w-full px-2 py-1.5 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700"
            />
          </div>
        </div>

        <!-- 相似度阈值 -->
        <div>
          <label for="similarity-threshold" class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
            相似度阈值: <span class="font-mono">{similarityThreshold.toFixed(2)}</span>
          </label>
          <input
            id="similarity-threshold"
            type="range"
            bind:value={similarityThreshold}
            min="0"
            max="1"
            step="0.01"
            class="w-full"
          />
        </div>

        <!-- 向量相似度权重 -->
        <div>
          <label for="vector-weight" class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
            向量相似度权重: <span class="font-mono">{vectorSimilarityWeight.toFixed(2)}</span>
          </label>
          <input
            id="vector-weight"
            type="range"
            bind:value={vectorSimilarityWeight}
            min="0"
            max="1"
            step="0.01"
            class="w-full"
          />
        </div>

        <!-- Top K -->
        <div>
          <label for="top-k" class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Top K (向量检索候选数)</label>
          <input
            id="top-k"
            type="number"
            bind:value={topK}
            min="1"
            max="10000"
            class="w-full px-2 py-1.5 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700"
          />
        </div>

        <!-- 功能开关 -->
        <div class="flex items-center space-x-4">
          <label class="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              bind:checked={enableKeyword}
              class="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
            />
            <span class="text-xs text-gray-700 dark:text-gray-300">启用关键词匹配</span>
          </label>
          <label class="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              bind:checked={enableHighlight}
              class="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
            />
            <span class="text-xs text-gray-700 dark:text-gray-300">启用高亮显示</span>
          </label>
        </div>
      </div>
    </details>

    <!-- 刷新知识库列表按钮 -->
    <button
      on:click={loadDatasets}
      disabled={loadingDatasets}
      class="w-full px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 mb-2"
    >
      <i class="fas fa-sync-alt {loadingDatasets ? 'fa-spin' : ''}"></i>
      <span>{loadingDatasets ? '加载中...' : '刷新知识库列表'}</span>
    </button>

    <!-- 检索按钮 -->
    <button
      on:click={performRetrieval}
      disabled={searching || selectedDatasetIds.length === 0 || !question.trim()}
      class="w-full px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
    >
      {#if searching}
        <i class="fas fa-spinner fa-spin"></i>
        <span>检索中...</span>
      {:else}
        <i class="fas fa-search"></i>
        <span>开始检索</span>
      {/if}
    </button>
  </div>

  <!-- 结果区域 -->
  <div class="flex-1 overflow-y-auto p-4">
    {#if error}
      <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <div class="flex items-start">
          <i class="fas fa-exclamation-circle text-red-500 mt-0.5 mr-2"></i>
          <div>
            <h4 class="text-sm font-medium text-red-800 dark:text-red-400">检索失败</h4>
            <p class="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
          </div>
        </div>
      </div>
    {:else if retrievalResult}
      <!-- 检索结果统计 -->
      <div class="mb-4 p-3 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg">
        <div class="flex items-center justify-between">
          <div>
            <span class="text-sm font-medium text-indigo-900 dark:text-indigo-300">检索结果</span>
            <span class="ml-2 text-sm text-indigo-700 dark:text-indigo-400">
              共找到 <span class="font-bold">{retrievalResult.total}</span> 个结果
            </span>
          </div>
          {#if retrievalResult.retrieval_time}
            <span class="text-xs text-indigo-600 dark:text-indigo-400">
              耗时: {retrievalResult.retrieval_time.toFixed(3)}s
            </span>
          {/if}
        </div>
      </div>

      <!-- 结果列表 -->
      {#if retrievalResult.documents.length === 0}
        <div class="text-center py-8 text-gray-500 dark:text-gray-400">
          <i class="fas fa-inbox text-3xl mb-2"></i>
          <p>未找到相关结果</p>
        </div>
      {:else}
        <div class="space-y-4">
          {#each retrievalResult.documents as doc, idx}
            {@const score = retrievalResult.scores[idx]}
            {@const metadata = doc.metadata}
            <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow">
              <!-- 结果头部 -->
              <div class="flex items-start justify-between mb-3">
                <div class="flex-1">
                  <div class="flex items-center flex-wrap gap-2 mb-2">
                    <span class="px-2 py-0.5 bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 text-xs font-medium rounded">
                      结果 #{idx + 1}
                    </span>
                    <!-- 总体相似度 -->
                    {#if metadata.similarity !== undefined || score !== undefined}
                      {@const similarity = metadata.similarity ?? score}
                      <span class="px-2 py-0.5 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 text-xs font-mono rounded font-semibold" title="总体相似度">
                        总相似度: {formatScore(similarity)}
                      </span>
                    {/if}
                    <!-- 向量相似度 -->
                    {#if metadata.vector_similarity !== undefined}
                      <span class="px-2 py-0.5 bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 text-xs font-mono rounded" title="向量相似度（余弦相似度）">
                        向量: {formatScore(metadata.vector_similarity)}
                      </span>
                    {/if}
                    <!-- 关键词相似度 -->
                    {#if metadata.term_similarity !== undefined}
                      <span class="px-2 py-0.5 bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 text-xs font-mono rounded" title="关键词相似度（BM25）">
                        关键词: {formatScore(metadata.term_similarity)}
                      </span>
                    {/if}
                  </div>
                  
                  {#if metadata.document_name}
                    <p class="text-xs font-medium text-gray-700 dark:text-gray-300 truncate mb-1">
                      <i class="fas fa-file-alt mr-1"></i>
                      {metadata.document_name}
                    </p>
                  {/if}
                  
                  <!-- 详细分数信息（可折叠） -->
                  {#if metadata.similarity !== undefined || metadata.vector_similarity !== undefined || metadata.term_similarity !== undefined}
                    <details class="mt-1">
                      <summary class="cursor-pointer text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300">
                        <i class="fas fa-info-circle mr-1"></i>
                        查看详细分数
                      </summary>
                      <div class="mt-2 p-2 bg-gray-50 dark:bg-gray-900 rounded text-xs space-y-1">
                        {#if metadata.similarity !== undefined}
                          <div class="flex justify-between">
                            <span class="text-gray-600 dark:text-gray-400">总体相似度 (similarity):</span>
                            <span class="font-mono font-semibold">{metadata.similarity.toFixed(6)}</span>
                          </div>
                        {/if}
                        {#if metadata.vector_similarity !== undefined}
                          <div class="flex justify-between">
                            <span class="text-gray-600 dark:text-gray-400">向量相似度 (vector_similarity):</span>
                            <span class="font-mono font-semibold">{metadata.vector_similarity.toFixed(6)}</span>
                          </div>
                        {/if}
                        {#if metadata.term_similarity !== undefined}
                          <div class="flex justify-between">
                            <span class="text-gray-600 dark:text-gray-400">关键词相似度 (term_similarity):</span>
                            <span class="font-mono font-semibold">{metadata.term_similarity.toFixed(6)}</span>
                          </div>
                        {/if}
                        <div class="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700 text-xs text-gray-500 dark:text-gray-400">
                          <p class="mb-1"><strong>说明：</strong></p>
                          <ul class="list-disc list-inside space-y-0.5">
                            <li><strong>总体相似度</strong> = 向量相似度 × 权重 + 关键词相似度 × (1 - 权重)</li>
                            <li><strong>向量相似度</strong>：基于embedding的余弦相似度</li>
                            <li><strong>关键词相似度</strong>：基于BM25算法的关键词匹配分数</li>
                          </ul>
                        </div>
                      </div>
                    </details>
                  {/if}
                </div>
                
                {#if metadata.chunk_id}
                  <span class="text-xs text-gray-400 dark:text-gray-500 font-mono flex-shrink-0 ml-2">
                    Chunk: {metadata.chunk_id.substring(0, 8)}...
                  </span>
                {/if}
              </div>

              <!-- 内容 -->
              <div class="bg-gray-50 dark:bg-gray-900 rounded p-3 text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
                {#if metadata.highlight && enableHighlight && metadata.highlight}
                  {@html extractHighlightText(metadata.highlight)}
                {:else}
                  {doc.content || ''}
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {/if}
    {:else}
      <div class="flex items-center justify-center h-full text-gray-400 dark:text-gray-500">
        <div class="text-center">
          <i class="fas fa-search text-4xl mb-3"></i>
          <p>输入查询问题并点击"开始检索"</p>
        </div>
      </div>
    {/if}
  </div>
</div>

<style>
  :global(mark) {
    background-color: #fef08a;
    color: #92400e;
    padding: 0.1em 0.2em;
    border-radius: 0.2em;
  }
  
  :global(.dark mark) {
    background-color: #78350f;
    color: #fbbf24;
  }
</style>

