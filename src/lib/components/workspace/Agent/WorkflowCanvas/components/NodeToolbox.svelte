<!--
  节点工具箱组件
  表现层：负责节点类型的展示和拖拽
-->
<script lang="ts">
  import type { NodeTemplate } from "../types";
  
  export let nodeTemplates: Record<string, NodeTemplate>;
  
  function handleDragStart(event: DragEvent, nodeType: string) {
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "copy";
      event.dataTransfer.setData("text/plain", nodeType);
    }
  }
</script>

<div class="flex-shrink-0 w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 p-4 overflow-y-auto">
  <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">节点工具箱</h4>
  <div class="space-y-2">
    {#each Object.entries(nodeTemplates) as [type, template]}
      <div
        class="p-3 border border-gray-200 dark:border-gray-700 rounded-lg cursor-move hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        draggable="true"
        on:dragstart={(e) => handleDragStart(e, type)}
      >
        <div class="flex items-center space-x-2">
          <div class="w-8 h-8 {template.color} rounded-lg flex items-center justify-center text-white">
            <i class="{template.icon} text-sm"></i>
          </div>
          <div>
            <div class="text-sm font-medium text-gray-900 dark:text-gray-100">{template.label}</div>
            <div class="text-xs text-gray-500 dark:text-gray-400">拖拽到画布</div>
          </div>
        </div>
      </div>
    {/each}
  </div>
</div>

