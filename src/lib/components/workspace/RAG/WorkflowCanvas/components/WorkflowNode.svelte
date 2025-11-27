<!--
  工作流节点组件
  表现层：负责节点的渲染和交互
-->
<script lang="ts">
  import type { WorkflowNode, ConnectionSide, NodeTemplate } from "../types";
  
  export let node: WorkflowNode;
  export let template: NodeTemplate;
  export let isSelected: boolean;
  export let connectingFrom: string | null;
  export let onNodeMouseDown: (node: WorkflowNode, event: Event) => void;
  export let onNodeContextMenu: (node: WorkflowNode, event: MouseEvent) => void;
  export let onConnectionPointMouseDown: (nodeId: string, side: ConnectionSide, event: Event) => void;
  export let onConnectionPointMouseUp: (nodeId: string, side: ConnectionSide, event: Event) => void;
  
  const sides: ConnectionSide[] = ["top", "bottom", "left", "right"];
  const sideColors = {
    top: "border-green-600",
    bottom: "border-indigo-600",
    left: "border-purple-600",
    right: "border-orange-600"
  };
  
  function getSidePosition(side: ConnectionSide) {
    const positions = {
      top: "top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2",
      bottom: "bottom-0 left-1/2 transform -translate-x-1/2 translate-y-1/2",
      left: "left-0 top-1/2 transform -translate-x-1/2 -translate-y-1/2",
      right: "right-0 top-1/2 transform translate-x-1/2 -translate-y-1/2"
    };
    return positions[side];
  }
</script>

<div
  class="workflow-node absolute border-2 rounded-lg shadow-lg cursor-move {isSelected ? 'ring-2 ring-indigo-500 border-indigo-500' : 'border-gray-300 dark:border-gray-600'} {template.color}"
  style="left: {node.x}px; top: {node.y}px; width: {node.width}px; height: {node.height}px; z-index: 2;"
  role="button"
  tabindex="0"
  on:mousedown={(e) => {
    const target = e.target;
    if (target instanceof HTMLElement) {
      if (target.classList.contains('connection-point') || target.closest('.connection-point')) {
        return;
      }
    }
    if (e.button === 0) {
      onNodeMouseDown(node, e);
    }
  }}
  on:contextmenu|preventDefault={(e) => onNodeContextMenu(node, e)}
  on:keydown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      onNodeMouseDown(node, e);
    }
  }}
>
  <div class="h-full flex flex-col items-center justify-center text-white p-2">
    <i class="{template.icon} text-2xl mb-1"></i>
    <div class="text-xs font-medium text-center">{node.label}</div>
    {#if node.type === "input"}
      <div class="text-[10px] mt-1 opacity-90 max-w-[140px] text-center truncate">
        {node.config?.user_input || '点击右侧配置面板输入'}
      </div>
    {/if}
    {#if node.type === "dataSource" && (node.config.selected_datasets?.length || 0) > 0}
      <div class="text-xs mt-1 opacity-90">
        {(node.config.selected_datasets?.length || 0)} 个知识库
      </div>
    {/if}
  </div>
  
  <!-- 连接点容器 - 四个方向的连接点 -->
  <div class="absolute inset-0 pointer-events-none" style="z-index: 30;">
    {#each sides as side}
      <button
        type="button"
        class="connection-point absolute {getSidePosition(side)} w-4 h-4 bg-white dark:bg-gray-800 border border-1 {sideColors[side]} rounded-full cursor-crosshair hover:scale-150 transition-all shadow-md pointer-events-auto {connectingFrom && connectingFrom !== node.id ? 'ring-2 ring-opacity-70 animate-pulse' : ''}"
        title="{side}连接点 - 输入/输出{connectingFrom ? ' - 连接中...' : ''}"
        aria-label="{side} connection point"
        style="box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.1);"
        on:mousedown|stopPropagation={(e) => {
          if (!connectingFrom) {
            onConnectionPointMouseDown(node.id, side, e);
          }
        }}
        on:mouseup|stopPropagation={(e) => {
          if (connectingFrom && connectingFrom !== node.id) {
            onConnectionPointMouseUp(node.id, side, e);
          }
        }}
        on:keydown|stopPropagation={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            if (!connectingFrom) {
              onConnectionPointMouseDown(node.id, side, e);
            } else if (connectingFrom && connectingFrom !== node.id) {
              onConnectionPointMouseUp(node.id, side, e);
            }
          }
        }}
      >
        <span class="absolute inset-0 flex items-center justify-center">
          <span class="w-1.5 h-1.5 rounded-full {side === 'top' ? 'bg-green-600' : side === 'bottom' ? 'bg-indigo-600' : side === 'left' ? 'bg-purple-600' : 'bg-orange-600'}"></span>
        </span>
      </button>
    {/each}
  </div>
</div>

