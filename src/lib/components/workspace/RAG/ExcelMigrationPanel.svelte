<!--
  Excel迁移到RAGFlow面板
  用于将Excel文件直接迁移到RAGFlow知识库
-->
<script lang="ts">
  import { ragAPI, type MigrateExcelDirectToRagFlowResponse, type ListExcelFilesResponse } from "$lib/apis/rag";
  import { toast } from "svelte-sonner";
  import { onMount } from "svelte";

  export let knowledgeId: string;

  // Excel迁移相关状态
  let excelDir: string = "/home/zeroerr-ai72/openwebui-zeroerr/backend/data/uploads/knowledge/748b54f6-73b0-4efb-87c3-15c166556d6f/manual";
  let datasetId: string = '';
  let datasetName: string = '';
  let documentName: string = '';
  let migrateMode: 'skip' | 'overwrite' = 'skip';
  let autoDeleteDuplicates: boolean = true;
  let migrating: boolean = false;
  let migrateResult: MigrateExcelDirectToRagFlowResponse | null = null;
  
  // 进度相关状态
  let migrationProgress: {
    stage: string;
    progress: number; // 0-100
    current: number;
    total: number;
    message: string;
  } | null = null;

  // 文件列表相关状态
  let loadingFiles: boolean = false;
  let fileList: ListExcelFilesResponse | null = null;
  let selectedFiles: Set<string> = new Set();

  async function loadFiles() {
    if (!excelDir.trim()) {
      toast.error('请先输入目录路径');
      return;
    }

    try {
      loadingFiles = true;
      selectedFiles.clear();
      const res = await ragAPI.listExcelFiles({
        dir_path: excelDir.trim(),
        knowledge_id: knowledgeId || null
      });
      fileList = res;
      toast.success(`加载了 ${res.total} 个Excel文件`);
    } catch (e: any) {
      console.error(e);
      toast.error(e.message || '加载文件列表失败');
      fileList = null;
    } finally {
      loadingFiles = false;
    }
  }

  function toggleFile(filename: string) {
    if (selectedFiles.has(filename)) {
      selectedFiles.delete(filename);
    } else {
      selectedFiles.add(filename);
    }
    selectedFiles = selectedFiles; // 触发响应式更新
  }

  function toggleSelectAll() {
    if (!fileList || fileList.files.length === 0) return;
    
    if (selectedFiles.size === fileList.files.length) {
      selectedFiles.clear();
    } else {
      selectedFiles = new Set(fileList.files.map(f => f.filename));
    }
    selectedFiles = selectedFiles; // 触发响应式更新
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }

  function formatDate(timestamp: number): string {
    return new Date(timestamp * 1000).toLocaleString('zh-CN');
  }

  async function performMigration() {
    if (!excelDir.trim()) {
      toast.error('请先输入目录路径');
      return;
    }

    if (selectedFiles.size === 0) {
      toast.error('请至少选择一个文件进行迁移');
      return;
    }

    try {
      migrating = true;
      migrateResult = null;
      
      // 初始化进度
      migrationProgress = {
        stage: '准备中',
        progress: 0,
        current: 0,
        total: selectedFiles.size,
        message: '正在准备迁移...'
      };
      
      // 模拟进度更新（因为后端是同步的，我们只能估计）
      const progressInterval = setInterval(() => {
        if (migrationProgress && migrationProgress.progress < 90) {
          // 渐进式增加进度（最多到90%，完成时会设置为100%）
          migrationProgress.progress = Math.min(
            migrationProgress.progress + 2,
            90
          );
          migrationProgress = migrationProgress; // 触发响应式更新
        }
      }, 500);
      
      // 更新阶段提示
      setTimeout(() => {
        if (migrationProgress) {
          migrationProgress.stage = '检查重名数据集';
          migrationProgress.message = '正在检查并删除重名的数据集...';
          migrationProgress = migrationProgress;
        }
      }, 1000);
      
      setTimeout(() => {
        if (migrationProgress) {
          migrationProgress.stage = '处理文件';
          migrationProgress.message = `正在处理 ${selectedFiles.size} 个文件...`;
          migrationProgress = migrationProgress;
        }
      }, 3000);
      
      const res = await ragAPI.migrateExcelDirectToRagFlow({
        dir_path: excelDir.trim(),
        selected_files: Array.from(selectedFiles),
        dataset_id: datasetId.trim() || null,
        dataset_name: datasetName.trim() || null,
        document_name: documentName.trim() || null,
        mode: migrateMode,
        auto_delete_duplicates: autoDeleteDuplicates,
      });
      
      // 完成进度
      clearInterval(progressInterval);
      migrationProgress = {
        stage: '完成',
        progress: 100,
        current: selectedFiles.size,
        total: selectedFiles.size,
        message: '迁移完成！'
      };
      
      migrateResult = res;
      
      // 如果用户没有指定dataset_id，自动填充返回的dataset_id以便后续使用
      if (!datasetId.trim()) {
        datasetId = res.dataset_id;
      }
      
      toast.success(`迁移成功！处理了 ${res.sheets_processed} 个章节，${res.segments_processed} 个分段，创建了 ${res.chunks_created} 个chunks`);
      
      // 延迟清除进度条
      setTimeout(() => {
        migrationProgress = null;
      }, 2000);
    } catch (e: any) {
      console.error(e);
      migrationProgress = null;
      toast.error(e.message || '迁移到RAGFlow失败');
    } finally {
      migrating = false;
    }
  }

  function clearResult() {
    migrateResult = null;
  }

  // 组件挂载时自动加载文件列表（如果提供了knowledgeId）
  onMount(async () => {
    if (knowledgeId && excelDir.trim()) {
      await loadFiles();
    }
  });
</script>

<div class="h-full flex flex-col bg-white dark:bg-gray-800">
  <!-- 头部说明 -->
  <div class="flex-shrink-0 p-4 border-b border-gray-200 dark:border-gray-700">
    <div class="flex items-center space-x-2 mb-2">
      <i class="fas fa-file-excel text-green-500"></i>
      <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Excel迁移到RAGFlow</h3>
    </div>
    <p class="text-sm text-gray-600 dark:text-gray-400">
      从目录中选择Excel文件迁移到RAGFlow知识库。每个Sheet将创建为独立的Document。
    </p>
  </div>

  <!-- 配置区域 -->
  <div class="flex-1 overflow-y-auto p-4 space-y-4">
    <!-- 目录路径 -->
    <div>
      <label for="excel-dir" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        目录路径 <span class="text-red-500">*</span>
      </label>
      <div class="flex gap-2">
        <input 
          id="excel-dir"
          type="text"
          bind:value={excelDir}
          placeholder="输入包含Excel文件的目录路径..."
          class="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:focus:ring-indigo-800 transition-all"
        />
        <button
          on:click={loadFiles}
          disabled={loadingFiles || !excelDir.trim()}
          class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
        >
          {#if loadingFiles}
            <i class="fas fa-spinner fa-spin"></i>
            <span>加载中...</span>
          {:else}
            <i class="fas fa-folder-open"></i>
            <span>加载文件</span>
          {/if}
        </button>
      </div>
      <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
        点击"加载文件"按钮列出目录下的所有Excel文件
      </p>
    </div>

    <!-- 文件列表 -->
    {#if fileList}
      <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-900/50">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center space-x-2">
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
              找到 {fileList.total} 个Excel文件
            </span>
            <span class="text-xs text-gray-500 dark:text-gray-400">
              （已选择 {selectedFiles.size} 个）
            </span>
          </div>
          <button
            on:click={toggleSelectAll}
            class="text-xs px-3 py-1 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded transition-colors"
          >
            {selectedFiles.size === fileList.files.length ? '取消全选' : '全选'}
          </button>
        </div>
        
        {#if fileList.files.length === 0}
          <div class="text-center py-8 text-gray-500 dark:text-gray-400">
            <i class="fas fa-inbox text-3xl mb-2"></i>
            <p>目录中没有Excel文件</p>
          </div>
        {:else}
          <div class="max-h-64 overflow-y-auto space-y-2">
            {#each fileList.files as file}
              {@const isSelected = selectedFiles.has(file.filename)}
              <label
                class="flex items-center space-x-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors {isSelected ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20' : 'border-gray-200 dark:border-gray-700'}"
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  on:change={() => toggleFile(file.filename)}
                  class="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                />
                <div class="flex-1 min-w-0">
                  <div class="flex items-center space-x-2">
                    <i class="fas fa-file-excel text-green-500 flex-shrink-0"></i>
                    <span class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {file.filename}
                    </span>
                  </div>
                  <div class="flex items-center space-x-3 mt-1 text-xs text-gray-500 dark:text-gray-400">
                    <span><i class="fas fa-weight-hanging mr-1"></i>{formatFileSize(file.size)}</span>
                    <span><i class="fas fa-clock mr-1"></i>{formatDate(file.mtime)}</span>
                  </div>
                </div>
              </label>
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    <!-- Dataset配置 -->
    <div class="grid grid-cols-2 gap-4">
      <div>
        <label for="dataset-id" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Dataset ID
        </label>
        <input 
          id="dataset-id"
          type="text"
          bind:value={datasetId}
          placeholder="可选，留空自动创建"
          class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:focus:ring-indigo-800"
        />
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">如果提供，将使用现有Dataset</p>
      </div>
      <div>
        <label for="dataset-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          Dataset名称
        </label>
        <input 
          id="dataset-name"
          type="text"
          bind:value={datasetName}
          placeholder="可选，新数据集名称"
          class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:focus:ring-indigo-800"
        />
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">仅创建新Dataset时使用</p>
      </div>
    </div>

    <!-- 文档名称 -->
    <div>
      <label for="document-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
        文档名称前缀
      </label>
      <input 
        id="document-name"
        type="text"
        bind:value={documentName}
        placeholder="可选，默认为Excel文件名"
        class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:focus:ring-indigo-800"
      />
      <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
        Document名称格式：{documentName || "文件名"}_Sheet名称
      </p>
    </div>

    <!-- 迁移模式和选项 -->
    <div class="space-y-3">
      <div>
        <label for="migrate-mode" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          迁移模式
        </label>
        <select 
          id="migrate-mode"
          bind:value={migrateMode}
          class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:focus:ring-indigo-800"
        >
          <option value="skip">跳过已存在（推荐）</option>
          <option value="overwrite">覆盖重写</option>
        </select>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
          <strong>跳过已存在：</strong>检测到重复的chunk时跳过，不创建重复数据<br/>
          <strong>覆盖重写：</strong>清空现有Document的chunks后重新创建
        </p>
      </div>

      <div class="flex items-center space-x-2">
        <input
          type="checkbox"
          id="auto-delete-duplicates"
          bind:checked={autoDeleteDuplicates}
          class="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
        />
        <label for="auto-delete-duplicates" class="text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
          自动删除重名的数据集或文档
        </label>
      </div>
      <p class="text-xs text-gray-500 dark:text-gray-400 ml-6">
        如果检测到重名的Dataset或Document，将自动删除后再创建新的
      </p>
    </div>

    <!-- 迁移按钮 -->
    <button
      on:click={performMigration}
      disabled={migrating || !excelDir.trim() || selectedFiles.size === 0}
      class="w-full px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 shadow-sm hover:shadow-md"
    >
      {#if migrating}
        <i class="fas fa-spinner fa-spin"></i>
        <span>迁移中...</span>
      {:else}
        <i class="fas fa-upload"></i>
        <span>开始迁移 ({selectedFiles.size} 个文件)</span>
      {/if}
    </button>

    <!-- 进度条 -->
    {#if migrationProgress}
      <div class="p-4 bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-lg">
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center space-x-2">
            <i class="fas fa-sync-alt fa-spin text-indigo-600 dark:text-indigo-400"></i>
            <span class="text-sm font-medium text-indigo-900 dark:text-indigo-300">
              {migrationProgress.stage}
            </span>
          </div>
          <span class="text-sm font-semibold text-indigo-700 dark:text-indigo-400">
            {migrationProgress.progress}%
          </span>
        </div>
        
        <!-- 进度条 -->
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-2 overflow-hidden">
          <div
            class="bg-gradient-to-r from-indigo-500 to-indigo-600 h-3 rounded-full transition-all duration-300 ease-out flex items-center justify-end pr-2"
            style="width: {migrationProgress.progress}%"
          >
            {#if migrationProgress.progress > 10}
              <span class="text-[10px] text-white font-medium">
                {migrationProgress.progress}%
              </span>
            {/if}
          </div>
        </div>
        
        <!-- 进度信息 -->
        <div class="flex items-center justify-between text-xs text-indigo-700 dark:text-indigo-400">
          <span>{migrationProgress.message}</span>
          <span>
            {migrationProgress.current} / {migrationProgress.total} 文件
          </span>
        </div>
      </div>
    {/if}

    <!-- 迁移结果 -->
    {#if migrateResult}
      <div class="mt-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
        <div class="flex items-start justify-between mb-2">
          <div class="flex items-center space-x-2">
            <i class="fas fa-check-circle text-green-600 dark:text-green-400"></i>
            <h4 class="text-sm font-semibold text-green-800 dark:text-green-300">迁移成功</h4>
          </div>
          <button
            on:click={clearResult}
            class="text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-200"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>
        
        <div class="space-y-2 text-sm text-green-700 dark:text-green-300">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <span class="font-medium">Dataset ID:</span>
              <span class="ml-2 font-mono text-xs break-all">{migrateResult.dataset_id}</span>
            </div>
            <div>
              <span class="font-medium">处理文件数:</span>
              <span class="ml-2">{migrateResult.files_processed}</span>
            </div>
          </div>
          
          <div class="grid grid-cols-3 gap-4 pt-2 border-t border-green-200 dark:border-green-700">
            <div>
              <span class="font-medium">章节:</span>
              <span class="ml-2">{migrateResult.sheets_processed}</span>
            </div>
            <div>
              <span class="font-medium">分段:</span>
              <span class="ml-2">{migrateResult.segments_processed}</span>
            </div>
            <div>
              <span class="font-medium">Chunks:</span>
              <span class="ml-2 font-semibold">{migrateResult.chunks_created}</span>
            </div>
          </div>

          <div class="pt-2 border-t border-green-200 dark:border-green-700">
            <div class="flex items-center justify-between mb-2">
              <span class="font-medium">Documents ({migrateResult.documents?.length || 0}个):</span>
              <span class="text-xs text-green-600 dark:text-green-400">每个Sheet一个Document</span>
            </div>
            
            {#if migrateResult.documents && migrateResult.documents.length > 0}
              <div class="max-h-60 overflow-y-auto space-y-1">
                {#each migrateResult.documents as doc, idx}
                  <div class="p-2 bg-white dark:bg-gray-800 rounded border border-green-200 dark:border-green-700 text-xs">
                    <div class="flex items-start justify-between gap-2">
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center space-x-2 mb-1">
                          <span class="px-1.5 py-0.5 bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-300 rounded text-[10px] font-medium">
                            #{idx + 1}
                          </span>
                          {#if doc.file_name}
                            <span class="text-gray-500 dark:text-gray-400 truncate text-[10px]">{doc.file_name}</span>
                          {/if}
                        </div>
                        <div class="font-medium text-gray-800 dark:text-gray-200 truncate">{doc.sheet_name}</div>
                      </div>
                      <span class="text-gray-400 dark:text-gray-500 font-mono text-[9px] flex-shrink-0 ml-2" title={doc.document_id}>
                        {doc.document_id.substring(0, 12)}...
                      </span>
                    </div>
                  </div>
                {/each}
              </div>
            {/if}
          </div>

          <div class="pt-2 border-t border-green-200 dark:border-green-700">
            <p class="text-xs text-green-600 dark:text-green-400 italic">{migrateResult.message}</p>
          </div>
        </div>
      </div>
    {/if}

    <!-- 使用说明 -->
    <div class="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
      <h4 class="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-2 flex items-center">
        <i class="fas fa-info-circle mr-2"></i>
        使用说明
      </h4>
      <ul class="text-xs text-blue-700 dark:text-blue-300 space-y-1 list-disc list-inside">
        <li>输入目录路径后，点击"加载文件"按钮列出所有Excel文件</li>
        <li>勾选要迁移的文件，支持全选/取消全选</li>
        <li>每个Excel文件中的每个Sheet（工作表）将创建为独立的Document</li>
        <li>Document命名格式：<code class="bg-blue-100 dark:bg-blue-900 px-1 rounded">文件名_Sheet名称</code></li>
        <li>Excel中的分段标题、分段内容、问题列会被正确提取并创建为chunks</li>
        <li>启用"自动删除重名"选项时，会自动删除重名的Dataset和Document</li>
        <li>中文文件名和Sheet名称会正确显示，不会出现乱码</li>
      </ul>
    </div>
  </div>
</div>

<style>
  code {
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
  }
</style>
