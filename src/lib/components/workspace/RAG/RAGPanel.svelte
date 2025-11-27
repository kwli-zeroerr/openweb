<!--
  RAG配置面板
  包含RAGFlow检索、Excel迁移和测试工具功能
-->
<script lang="ts">
  import { onMount } from "svelte";
  import TestTools from "./TestTools.svelte";
  import RagflowRetrievalPanel from "../Agent/Retrieval/RagflowRetrievalPanel.svelte";
  import ExcelMigrationPanel from "./ExcelMigrationPanel.svelte";
  import RAGWorkflowCanvas from "../Agent/WorkflowCanvas/RAGWorkflowCanvas.svelte";

  export let knowledgeId: string;

  let activeTab = "ragflow";
  let loading = false;
  let error: string | null = null;

  // 标签页配置
  const tabs = [
    { id: "workflow", label: "工作流画布", icon: "fas fa-project-diagram" },
    { id: "ragflow", label: "RAGFlow检索", icon: "fas fa-search" },
    { id: "excel", label: "Excel迁移", icon: "fas fa-file-excel" },
    { id: "test", label: "测试工具", icon: "fas fa-flask" }
  ];

  function handleTabChange(tabId: string) {
    activeTab = tabId;
  }
</script>

<div class="rag-panel h-full flex flex-col">
  <!-- 头部 -->
  <div class="flex-shrink-0 border-b border-gray-200 dark:border-gray-700">
    <div class="flex items-center justify-between p-4">
      <div class="flex items-center space-x-2">
        <i class="fas fa-brain text-blue-500"></i>
        <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
          RAG 配置
        </h2>
      </div>
    </div>

    <!-- 标签页导航 -->
    <div class="flex border-b border-gray-200 dark:border-gray-700">
      {#each tabs as tab}
        <button
          class="flex items-center space-x-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors
                 {activeTab === tab.id 
                   ? 'border-blue-500 text-blue-600 dark:text-blue-400' 
                   : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'}"
          on:click={() => handleTabChange(tab.id)}
        >
          <i class="{tab.icon}"></i>
          <span>{tab.label}</span>
        </button>
      {/each}
    </div>
  </div>

  <!-- 错误提示 -->
  {#if error}
    <div class="flex-shrink-0 p-4">
      <div class="bg-red-50 border border-red-200 rounded-md p-3">
        <div class="flex">
          <i class="fas fa-exclamation-triangle text-red-400 mt-0.5 mr-2"></i>
          <div>
            <h3 class="text-sm font-medium text-red-800">错误</h3>
            <p class="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- 加载状态 -->
  {#if loading}
    <div class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <i class="fas fa-spinner fa-spin text-2xl text-gray-400 mb-2"></i>
        <p class="text-gray-500 dark:text-gray-400">加载中...</p>
      </div>
    </div>
  {:else}
    <!-- 内容区域 -->
    <div class="flex-1 overflow-hidden">
      {#if activeTab === "workflow"}
        <RAGWorkflowCanvas {knowledgeId} />
      {:else if activeTab === "ragflow"}
        <RagflowRetrievalPanel {knowledgeId} />
      {:else if activeTab === "excel"}
        <ExcelMigrationPanel {knowledgeId} />
      {:else if activeTab === "test"}
        {#if !knowledgeId || knowledgeId.trim() === ''}
          <div class="flex-1 flex items-center justify-center p-8">
            <div class="text-center max-w-md">
              <i class="fas fa-exclamation-triangle text-yellow-500 text-4xl mb-4"></i>
              <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">需要选择知识库</h3>
              <p class="text-gray-600 dark:text-gray-400 mb-4">
                测试工具需要指定一个知识库才能保存 Excel 分段。请前往"知识库"页面选择或创建知识库。
              </p>
              <a 
                href="/workspace/knowledge" 
                class="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                <i class="fas fa-book mr-2"></i>
                前往知识库页面
              </a>
            </div>
          </div>
        {:else}
          <TestTools {knowledgeId} />
        {/if}
      {/if}
    </div>
  {/if}
</div>

<style>
  .rag-panel {
    min-height: 0; /* 确保flex子元素可以收缩 */
  }
</style>