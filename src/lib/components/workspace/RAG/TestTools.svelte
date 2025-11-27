<!--
  Excel分段管理组件
  用于提取和管理Excel文件中的分段内容
-->
<script lang="ts">
  import { onMount } from "svelte";
  import { toast } from "svelte-sonner";
  import { ragAPI, type SavedExcelFile, type SavedFileSegmentsResponse } from "$lib/apis/rag";

  export let knowledgeId: string;

  // Excel 分段显示
  let excelSegments: Array<{file: string; sheet: string; row: number; title: string; content: string; questions: string;}> = [];
  let excelGroups: Array<{ file: string; sheets: Array<{ name: string; count: number; segments: typeof excelSegments }>}> = [];
  type ViewLevel = 'files' | 'sheets' | 'segments' | 'detail';
  let viewLevel: ViewLevel = 'files';
  let selectedFileIdx: number = 0;
  let selectedSheetIdx: number = 0;
  let selectedSegment: { file: string; sheet: string; row: number; title: string; content: string; questions: string } | null = null;
  let excelLoading = false;
  let excelDir = "/home/zeroerr-ai72/openwebui-zeroerr/backend/data/uploads/knowledge/748b54f6-73b0-4efb-87c3-15c166556d6f/manual";
  let saving = false;
  let lastSaved: { files: string[]; total: number } | null = null;
  
  
  // 已保存文件列表
  let savedFiles: SavedExcelFile[] = [];
  let savedFilesGrouped: Map<string, SavedExcelFile[]> = new Map();
  let loadingSavedFiles = false;
  let showSavedFiles = false;
  let savedFileView: { fileId: string | null; sheets: SavedFileSegmentsResponse['sheets'] } = { fileId: null, sheets: [] };
  let sheetFilter = '';
  // 记录是否从"已保存文件视图"进入，用于返回路径一致
  let cameFromSaved = false;
  

  async function extractExcel() {
    try {
      excelLoading = true;
      const res = await ragAPI.extractExcel({ dir_path: excelDir, limit_per_file: 2000 });
      excelSegments = res.segments || [];
      excelGroups = res.groups || [];
      viewLevel = 'files';
      selectedFileIdx = 0;
      selectedSheetIdx = 0;
      selectedSegment = null;
      toast.success(`提取完成：${res.total_segments} 段，来自 ${res.total_files} 个文件`);
    } catch (e) {
      console.error(e);
      toast.error("Excel分段提取失败");
    } finally {
      excelLoading = false;
    }
  }

  async function saveToKnowledge() {
    if (!knowledgeId || knowledgeId.trim() === '') {
      toast.error("请先选择知识库");
      return;
    }
    
    try {
      saving = true;
      const res = await ragAPI.saveExcelSegments({ knowledge_id: knowledgeId, dir_path: excelDir, limit_per_file: 2000 });
      lastSaved = { files: res.file_ids, total: res.total_files_created };
      toast.success(`已保存到知识库：${res.total_files_created} 个文件 / ${res.total_segments} 段`);
      // 保存后自动刷新已保存文件列表
      await loadSavedFiles();
    } catch (e) {
      console.error(e);
      const errorMessage = e instanceof Error ? e.message : String(e);
      if (errorMessage.includes('知识库不存在')) {
        toast.error("知识库不存在，请检查知识库ID是否正确");
      } else {
        toast.error(`保存到知识库失败: ${errorMessage}`);
      }
    } finally {
      saving = false;
    }
  }

  async function loadSavedFiles() {
    if (!knowledgeId || knowledgeId.trim() === '') {
      savedFiles = [];
      savedFilesGrouped = new Map();
      return;
    }
    
    try {
      loadingSavedFiles = true;
      const res = await ragAPI.getSavedExcelFiles(knowledgeId);
      savedFiles = res.files || [];
      // 按original_file分组
      const grouped = new Map<string, SavedExcelFile[]>();
      for (const file of savedFiles) {
        const key = file.original_file || '未知文件';
        if (!grouped.has(key)) {
          grouped.set(key, []);
        }
        grouped.get(key)!.push(file);
      }
      savedFilesGrouped = grouped;
      showSavedFiles = true;
      toast.success(`加载了 ${res.total_files} 个已保存文件`);
    } catch (e) {
      console.error(e);
      toast.error("加载已保存文件失败");
    } finally {
      loadingSavedFiles = false;
    }
  }

  async function deleteExcelFile(fileId: string, event: Event) {
    event.stopPropagation(); // 阻止触发卡片点击
    if (!confirm('确定要删除这个文件吗？')) {
      return;
    }
    try {
      await ragAPI.deleteSavedExcelFile(fileId);
      toast.success('文件已删除');
      // 重新加载已保存文件列表
      await loadSavedFiles();
    } catch (e) {
      console.error(e);
      toast.error('删除文件失败');
    }
  }

  async function viewSavedFileSegments(file: SavedExcelFile) {
    try {
      loadingSavedFiles = true;
      const res = await ragAPI.getSavedFileSegments(file.file_id);
      savedFileView = { fileId: file.file_id, sheets: res.sheets || [] };
      // 切换到分段视图（重用右侧层级区）
      excelGroups = [{ file: res.original_file || file.original_file || file.filename, sheets: res.sheets.map(s => ({ 
        name: s.name, 
        count: s.segments?.length || 0, 
        segments: (s.segments || []).map(seg => ({ 
          file: res.original_file, 
          sheet: s.name, 
          row: 0, 
          title: seg.title || '', 
          content: seg.content || '', 
          questions: seg.questions || '' 
        }))
      })) }];
      viewLevel = 'sheets';
      selectedFileIdx = 0;
      selectedSheetIdx = 0;
      selectedSegment = null;
      // 标记来源于已保存列表，返回时回到已保存
      cameFromSaved = true;
      showSavedFiles = false;
      toast.success('已加载分段');
    } catch (e) {
      console.error(e);
      toast.error('加载分段失败');
    } finally {
      loadingSavedFiles = false;
    }
  }

  onMount(async () => {
    try {
      // 默认进入时直接显示"已保存的分段"
      await loadSavedFiles();
      showSavedFiles = true;
    } catch (e) {
      console.error(e);
    }
  });
</script>

<div class="h-full flex flex-col p-6 overflow-hidden">
  <div class="max-w-none w-full mx-auto flex-1 flex flex-col min-h-0 overflow-hidden">
    
  
  <!-- Excel 分段提取（精简模式） -->
    <div class="bg-white dark:bg-gray-800 rounded-xl shadow-md border border-gray-200 dark:border-gray-700 flex-1 flex flex-col min-h-0 overflow-hidden">
      <div class="px-6 py-5 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex-shrink-0">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-xl font-bold text-gray-900 dark:text-gray-100 flex items-center">
            <i class="fas fa-file-excel mr-3 text-teal-500 dark:text-teal-400"></i>
            Excel 分段提取
            </h3>
            <p class="text-sm text-gray-600 dark:text-gray-400 mt-2 ml-7">
            从 Excel 的 sheet 作为章节，提取 标题/内容/问题，并在右侧显示
            </p>
          </div>
        <div class="flex items-center space-x-3"></div>
        </div>
      </div>
      
      <!-- 主体布局：左侧控制 1/4 ，右侧结果 3/4 -->
      <div class="px-6 pb-6 grid grid-cols-4 gap-4 flex-1 min-h-0 overflow-hidden">
      <!-- 左侧：Excel目录与提取按钮（1/4） -->
        <div class="space-y-4 col-span-1">
        <!-- Excel 分段提取 -->
          <div class="space-y-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div class="space-y-2">
              <label class="text-sm font-medium text-gray-700 dark:text-gray-300">Excel目录:</label>
              <input class="w-full px-4 py-2.5 text-sm border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 dark:focus:ring-teal-800 transition-all" bind:value={excelDir} placeholder="输入Excel目录路径..." />
            </div>
            <div class="space-y-3">
              <div class="flex flex-col gap-2">
                <button on:click={extractExcel} class="w-full px-4 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-lg shadow-sm hover:shadow disabled:bg-gray-400 disabled:shadow-none transition-all duration-200 font-medium flex items-center justify-center" disabled={excelLoading}>
                  {#if excelLoading}
                    <i class="fas fa-spinner fa-spin mr-2"></i>
                    <span>提取中...</span>
                  {:else}
                    <i class="fas fa-file-excel mr-2"></i>
                    <span>提取Excel分段</span>
                  {/if}
            </button>
                <button on:click={saveToKnowledge} class="w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-sm hover:shadow disabled:bg-gray-400 disabled:shadow-none transition-all duration-200 font-medium flex items-center justify-center" disabled={saving}>
                  {#if saving}
                    <i class="fas fa-spinner fa-spin mr-2"></i>
                    <span>保存中...</span>
              {:else}
                    <i class="fas fa-database mr-2"></i>
                    <span>保存到知识库</span>
              {/if}
            </button>
                <button on:click={loadSavedFiles} class="w-full px-4 py-2.5 bg-gray-700 hover:bg-gray-800 dark:bg-gray-600 dark:hover:bg-gray-700 text-white rounded-lg shadow-sm hover:shadow disabled:bg-gray-400 disabled:shadow-none transition-all duration-200 font-medium flex items-center justify-center" disabled={loadingSavedFiles}>
                  {#if loadingSavedFiles}
                    <i class="fas fa-spinner fa-spin mr-2"></i>
                    <span>加载中...</span>
                  {:else}
                    <i class="fas fa-folder-open mr-2"></i>
                    <span>查看已保存</span>
                  {/if}
            </button>
              </div>
              <p class="text-xs text-gray-500 dark:text-gray-400 leading-relaxed pt-1">从各 Excel 的 sheet 作为章节，提取 标题/内容/问题</p>
            </div>
          </div>
          
        </div>

        <!-- 右侧：结果区域（3/4） -->
        <div class="border-l border-gray-200 dark:border-gray-700 pl-4 col-span-3 flex flex-col min-h-0 overflow-hidden">
        {#if showSavedFiles && savedFiles.length > 0}
          <!-- 已保存文件视图 -->
            <div class="space-y-4 flex-1 flex flex-col min-h-0">
            <div class="flex items-center justify-between flex-shrink-0">
              <div class="text-sm font-medium text-gray-700 dark:text-gray-300">
                已保存文件 ({savedFiles.length} 个)
              </div>
              <div class="flex items-center gap-2">
                <button class="text-xs px-2 py-1 border rounded bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600" on:click={() => { showSavedFiles = false; }}>
                  返回提取视图
                </button>
              </div>
            </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 flex-1 overflow-y-auto pr-1 min-h-0 pb-4">
            {#each Array.from(savedFilesGrouped.entries()) as [originalFile, files]}
              {#if files && files.length}
                <div class="bg-white dark:bg-gray-700 rounded-lg p-5 border border-gray-200 dark:border-gray-600 cursor-pointer hover:shadow-md hover:border-gray-300 dark:hover:border-gray-500 hover:bg-gray-50 dark:hover:bg-gray-600 transition-all duration-200 flex flex-col justify-between group relative" on:click={() => viewSavedFileSegments(files[0])} on:keydown={(e) => e.key === 'Enter' && viewSavedFileSegments(files[0])} role="button" tabindex="0">
                  <button 
                    class="absolute top-2 right-2 p-1.5 text-gray-400 hover:text-red-500 dark:hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity z-10"
                    on:click={(e) => deleteExcelFile(files[0].file_id, e)}
                    title="删除文件"
                  >
                    <i class="fas fa-trash text-xs"></i>
                  </button>
                  <div>
                    <div class="text-sm font-bold text-gray-900 dark:text-gray-100 mb-3 line-clamp-2 flex items-start pr-8">
                      <i class="fas fa-file-excel text-teal-500 dark:text-teal-400 mr-2 mt-0.5 group-hover:scale-110 transition-transform"></i>
                      <span>{originalFile}</span>
                    </div>
                    <div class="text-xs text-gray-500 dark:text-gray-400 truncate mb-3 pl-5">{files[0].filename}</div>
                  </div>
                  <div class="mt-auto pt-3 border-t border-gray-200 dark:border-gray-600 flex items-center justify-between">
                    <span class="px-3 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs font-medium">{files[0].segment_count || 0} 段</span>
                    <span class="text-[10px] text-gray-400 dark:text-gray-500 font-mono">ID: {files[0].file_id.substring(0,8)}...</span>
                  </div>
                </div>
              {/if}
            {/each}
          </div>
                  </div>
        {:else if excelGroups && excelGroups.length > 0}
          <div class="flex-1 flex flex-col min-h-0 space-y-0">
              <div class="flex items-center justify-between flex-shrink-0 bg-gradient-to-r from-white/95 to-gray-50/95 dark:from-gray-800/95 dark:to-gray-900/95 backdrop-blur-sm z-10 py-3 px-1 border-b border-gray-200 dark:border-gray-700 shadow-sm">
              <div class="flex items-center gap-3">
                {#if viewLevel !== 'files'}
                  <button class="text-xs px-3 py-1.5 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 hover:border-teal-400 dark:hover:border-teal-500 transition-all font-medium" on:click={() => {
                    if (viewLevel === 'detail') viewLevel = 'segments';
                    else if (viewLevel === 'segments') viewLevel = 'sheets';
                    else if (viewLevel === 'sheets') {
                      if (cameFromSaved) { showSavedFiles = true; cameFromSaved = false; }
                      else { viewLevel = 'files'; }
                    }
                  }}>
                    <i class="fas fa-arrow-left mr-1.5"></i> 返回
                  </button>
                {/if}
                <div class="text-base font-bold text-gray-900 dark:text-gray-100">
                  {viewLevel === 'files' ? '文件列表' : viewLevel === 'sheets' ? `${excelGroups[selectedFileIdx]?.file} · 章节` : viewLevel === 'segments' ? `${excelGroups[selectedFileIdx]?.file} · ${excelGroups[selectedFileIdx]?.sheets[selectedSheetIdx]?.name} · 分段` : '分段详情'}
                </div>
                  </div>
              {#if viewLevel === 'sheets'}
                <div class="flex items-center gap-3">
                  <input class="px-3 py-1.5 text-xs border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 dark:focus:ring-teal-800 transition-all" placeholder="筛选章节..." bind:value={sheetFilter} />
                  <span class="text-xs font-semibold px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">{excelGroups[selectedFileIdx]?.sheets.length} 章</span>
                </div>
              {/if}
                </div>
                
            <div class="flex-1 flex flex-col min-h-0 overflow-hidden">
            {#if viewLevel === 'files'}
              <div class="grid grid-cols-2 gap-3 max-h-[420px] overflow-y-auto" role="list">
                {#each excelGroups as g, i}
                  <button type="button" class="text-left rounded border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 p-3 hover:shadow" on:click={() => { selectedFileIdx = i; viewLevel = 'sheets'; }}>
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">{g.file}</div>
                    <div class="text-xs text-gray-600 dark:text-gray-300">{g.sheets.length} 个章节</div>
                  </button>
                {/each}
                      </div>
            {:else if viewLevel === 'sheets'}
              {#key sheetFilter}
              <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-3 gap-4 flex-1 overflow-y-auto min-h-0 pb-4" role="list">
                {#each (excelGroups[selectedFileIdx]?.sheets || []).filter(s => !sheetFilter || s.name.toLowerCase().includes(sheetFilter.toLowerCase())) as s, si}
                  <button type="button" class="text-left rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 p-5 hover:shadow-md hover:border-gray-300 dark:hover:border-gray-500 hover:bg-gray-50 dark:hover:bg-gray-600 transition-all duration-200 h-32 flex flex-col justify-between group" on:click={() => { 
                    selectedSheetIdx = si;
                    viewLevel = 'segments';
                  }}>
                    <div class="text-sm font-semibold text-gray-900 dark:text-gray-100 line-clamp-2 group-hover:text-gray-700 dark:group-hover:text-gray-200 transition-colors leading-snug">
                      {s.name}
                    </div>
                    <div class="text-xs mt-3"><span class="px-3 py-1.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 font-medium">{s.count} 段</span></div>
                  </button>
                {/each}
                    </div>
              {/key}
            {:else if viewLevel === 'segments'}
              <div class="flex-1 overflow-y-auto pr-1 min-h-0 pb-4">
                <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 pb-2">
                  {#each excelGroups[selectedFileIdx]?.sheets[selectedSheetIdx]?.segments || [] as seg}
                    <button type="button" class="text-left rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 p-4 hover:shadow-md hover:border-gray-300 dark:hover:border-gray-500 hover:bg-gray-50 dark:hover:bg-gray-600 transition-all duration-200 h-auto min-h-[8rem] flex flex-col justify-between group" on:click={() => { selectedSegment = seg; viewLevel = 'detail'; }}>
                      <div class="text-xs font-semibold text-gray-900 dark:text-gray-100 line-clamp-2 group-hover:text-gray-700 dark:group-hover:text-gray-200 transition-colors mb-2">
                        {seg.title || `行 ${seg.row}`}
                      </div>
                      <div class="text-[11px] text-gray-600 dark:text-gray-400 line-clamp-2 leading-relaxed mb-2 flex-1">
                        {seg.content}
                      </div>
                      {#if seg.questions && seg.questions.trim()}
                        <div class="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600">
                          <div class="text-[10px] text-gray-500 dark:text-gray-500 mb-1">问题:</div>
                          <div class="text-[11px] text-gray-700 dark:text-gray-300 line-clamp-2">{seg.questions}</div>
                        </div>
                      {/if}
                    </button>
                  {/each}
                </div>
                            </div>
            {:else if viewLevel === 'detail'}
              <div class="flex-1 overflow-y-auto min-h-0 pr-1">
                <div class="rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 p-6 shadow-md pb-4">
                  <div class="text-lg font-bold text-gray-900 dark:text-gray-100 mb-3 pb-3 border-b border-gray-200 dark:border-gray-600">{selectedSegment?.title || '无标题'}</div>
                  <div class="text-xs text-gray-500 dark:text-gray-400 mb-4 flex items-center gap-2">
                    <span class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-600">{selectedSegment?.file}</span>
                    <span>·</span>
                    <span class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-600">{selectedSegment?.sheet}</span>
                    <span>·</span>
                    <span class="px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-600">行 {selectedSegment?.row}</span>
                  </div>
                  <div class="text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap leading-relaxed mb-4">{selectedSegment?.content}</div>
                  {#if selectedSegment?.questions}
                    <div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
                      <div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">问题（选填，单元格内一行一个）：</div>
                      <div class="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed pl-4 border-l-2 border-gray-200 dark:border-gray-600">{selectedSegment?.questions}</div>
                    </div>
                              {/if}
                            </div>
                {#if lastSaved}
                  <div class="mt-4 text-xs text-gray-500 dark:text-gray-400 px-2 py-1 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300">最近保存：{lastSaved.total} 个文件</div>
                {/if}
                            </div>
                          {/if}
            </div>
                        </div>
        {:else if excelSegments && excelSegments.length > 0}
            <div class="space-y-4 h-full">
              <div class="flex items-center justify-between">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">Excel 分段（{excelSegments.length}）</label>
                <div class="text-xs text-gray-500 dark:text-gray-400">仅显示每段前 200 字</div>
              </div>
              <div class="space-y-2 max-h-[420px] overflow-y-auto">
                {#each excelSegments as seg, idx}
                  <div class="bg-white dark:bg-gray-600 p-2 rounded text-xs border border-gray-200 dark:border-gray-500">
                    <div class="flex items-center justify-between mb-1">
                      <div class="font-medium text-gray-700 dark:text-gray-200">{seg.file} · {seg.sheet} · 行 {seg.row}</div>
                    </div>
                    {#if seg.title}
                      <div class="text-gray-700 dark:text-gray-200 mb-1">标题：{seg.title}</div>
                    {/if}
                    <div class="text-gray-900 dark:text-gray-100">{seg.content.substring(0, 200)}...</div>
                    {#if seg.questions}
                      <div class="text-gray-600 dark:text-gray-300 mt-1">问题：{seg.questions}</div>
                    {/if}
                  </div>
                {/each}
              </div>
            </div>
          {:else}
            <div class="flex items-center justify-center h-full min-h-[200px]">
              <div class="text-center text-gray-400 dark:text-gray-500">
                <i class="fas fa-clipboard-list text-4xl mb-3"></i>
              <p class="text-sm">暂无提取结果</p>
              </div>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</div>