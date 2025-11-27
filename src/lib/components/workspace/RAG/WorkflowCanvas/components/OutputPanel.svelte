<script lang="ts">
  export let executionResult: any;
  export let onClose: () => void;
</script>

{#if executionResult}
  <div class="flex-shrink-0 border-top border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 max-h-64 overflow-y-auto">
    <div class="flex items-center justify-between mb-3">
      <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300">执行结果</h4>
      <button on:click={onClose} class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
        <i class="fas fa-times"></i>
      </button>
    </div>
    <div class="space-y-2">
      {#if executionResult.timings}
        <div class="p-3 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800">
          <div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">执行用时</div>
          <div class="grid grid-cols-2 gap-2 text-xs text-gray-700 dark:text-gray-300">
            {#each Object.entries(executionResult.timings) as [k,v]}
              <div class="flex justify-between"><span>{k}</span><span>{v} ms</span></div>
            {/each}
          </div>
        </div>
      {/if}
      <div class="text-sm text-gray-600 dark:text-gray-400">
        共找到 <span class="font-semibold">{executionResult.total}</span> 个结果
      </div>
      {#if executionResult.retrieved_context}
        <div class="p-3 border border-indigo-200 dark:border-indigo-800 rounded-lg bg-indigo-50 dark:bg-indigo-900/30">
          <div class="text-xs font-semibold text-indigo-700 dark:text-indigo-300 mb-1">拼接的上下文（传递给 LLM 的 retrieved_context）</div>
          <pre class="text-xs whitespace-pre-wrap text-gray-800 dark:text-gray-200">{executionResult.retrieved_context}</pre>
        </div>
      {/if}
      {#each executionResult.documents.slice(0, 5) as doc, idx}
        <div class="p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
          <div class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">结果 #{idx + 1}</div>
          <div class="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">{doc.content || ''}</div>
        </div>
      {/each}
      {#if executionResult.llm_output}
        <div class="p-3 border border-emerald-200 dark:border-emerald-800 rounded-lg bg-emerald-50 dark:bg-emerald-900/30">
          <div class="text-xs font-semibold text-emerald-700 dark:text-emerald-300 mb-1">LLM 输出</div>
          <pre class="text-xs whitespace-pre-wrap text-gray-800 dark:text-gray-200">{executionResult.llm_output}</pre>
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  line-clamp: 2;
    overflow: hidden;
  }
</style>


