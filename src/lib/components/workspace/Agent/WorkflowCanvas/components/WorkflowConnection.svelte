<!--
  工作流连接线组件
  表现层：负责连接线的渲染和交互
-->
<script lang="ts">
  import type { WorkflowConnection, WorkflowNode } from "../types";
  import { calculatePolylinePath } from "../services/connectionService";
  
  export let connection: WorkflowConnection;
  export let fromNode: WorkflowNode;
  export let toNode: WorkflowNode;
  export let isEditing: boolean;
  export let canvas: HTMLElement;
  export let onConnectionClick: (connId: string) => void = (_: string) => {};
  export let onConnectionRightClick: (connId: string) => void = (_: string) => {};
  export let onToggleType: (connId: string) => void = (_: string) => {};
  export let onAddControlPoint: (connId: string, x: number, y: number) => void = (_c: string, _x: number, _y: number) => {};
  export let onDeleteControlPoint: (connId: string, pointIndex: number) => void = (_c: string, _i: number) => {};
  export let onControlPointMouseDown: (connId: string, pointIndex: number, event: MouseEvent) => void = (_c: string, _i: number, _e: MouseEvent) => {};

  // A11y: 键盘回车等效点击
  function onKeyActivate(handler: (e: any) => void) {
    return (e: KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handler(e as any);
      }
    };
  }
  
  let isBidirectional: boolean;
  let pathData: string;
  let reversePathData: string;
  let fromPoint: { x: number; y: number };
  let toPoint: { x: number; y: number };
  let midX: number;
  let midY: number;

  $: isBidirectional = connection.type === "bidirectional";
  $: pathData = calculatePolylinePath(
    fromNode,
    connection.fromSide,
    toNode,
    connection.toSide,
    connection.controlPoints
  );
  $: reversePathData = isBidirectional
    ? calculatePolylinePath(toNode, connection.toSide, fromNode, connection.fromSide)
    : "";
  // 计算中点用于显示类型指示器（随节点位置变化自动更新）
  $: fromPoint = {
    x:
      fromNode.x +
      fromNode.width / 2 +
      (connection.fromSide === "left"
        ? -fromNode.width / 2
        : connection.fromSide === "right"
        ? fromNode.width / 2
        : 0),
    y:
      fromNode.y +
      fromNode.height / 2 +
      (connection.fromSide === "top"
        ? -fromNode.height / 2
        : connection.fromSide === "bottom"
        ? fromNode.height / 2
        : 0)
  };
  $: toPoint = {
    x:
      toNode.x +
      toNode.width / 2 +
      (connection.toSide === "left"
        ? -toNode.width / 2
        : connection.toSide === "right"
        ? toNode.width / 2
        : 0),
    y:
      toNode.y +
      toNode.height / 2 +
      (connection.toSide === "top"
        ? -toNode.height / 2
        : connection.toSide === "bottom"
        ? toNode.height / 2
        : 0)
  };
  $: midX = (fromPoint.x + toPoint.x) / 2;
  $: midY = (fromPoint.y + toPoint.y) / 2;
  
  // 计算折线中点（如果已有控制点，使用第一个；否则使用端点中点）
  $: midpoint = (connection.controlPoints && connection.controlPoints.length > 0)
    ? connection.controlPoints[0]
    : { x: midX, y: midY };
  
  // 计算连接类型指示器位置（避免与中点控制点重合，偏移35像素）
  $: indicatorOffset = 35;
  $: indicatorPos = (() => {
    // 计算指示器应该放在路径上的位置（偏移中点）
    const dx = toPoint.x - fromPoint.x;
    const dy = toPoint.y - fromPoint.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    
    if (dist < 80) {
      // 如果距离太短，垂直偏移
      return { x: midpoint.x, y: midpoint.y - indicatorOffset };
    }
    
    // 根据路径方向，在垂直方向偏移
    const angle = Math.atan2(dy, dx);
    const offsetX = -Math.sin(angle) * indicatorOffset;
    const offsetY = Math.cos(angle) * indicatorOffset;
    
    return { x: midpoint.x + offsetX, y: midpoint.y + offsetY };
  })();
  
  function handleClick(e: MouseEvent) {
    if (isEditing) {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      onAddControlPoint(connection.id, x, y);
    } else {
      onConnectionClick(connection.id);
    }
  }
  
  // 拖动中点控制点（索引为0，如果没有会自动创建）
  function handleMidpointMouseDown(e: MouseEvent) {
    e.stopPropagation();
    // 直接触发拖动第一个控制点，父组件会自动创建（如果没有）
    onControlPointMouseDown(connection.id, 0, e);
  }

  function handleMainKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onConnectionClick(connection.id);
    }
  }

  function handleToggleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onToggleType(connection.id);
    }
  }
</script>

<g>
  <!-- 主连接线 -->
  <path
    d={pathData}
    stroke={isBidirectional ? "#10b981" : "#6366f1"}
    stroke-width="2"
    fill="none"
    marker-end={isBidirectional ? "url(#arrowhead-bidirectional)" : "url(#arrowhead)"}
    class="pointer-events-auto"
    style="cursor: {isEditing ? 'default' : 'pointer'};"
    stroke-dasharray={isBidirectional ? "4,3" : "none"}
    on:click|stopPropagation={handleClick}
    role="button"
    tabindex="0"
    aria-label={isBidirectional ? "双向连接线" : "单向连接线"}
    on:keydown={handleMainKeydown}
  />
  
  <!-- 点击区域（用于添加控制点） -->
  {#if isEditing}
    <g>
      <title>点击添加编辑点</title>
      <path
        d={pathData}
        stroke="transparent"
        stroke-width="20"
        fill="none"
        class="pointer-events-auto"
        style="cursor: crosshair;"
        on:click|stopPropagation={handleClick}
        role="button"
        tabindex="0"
        aria-label="添加编辑点"
        on:keydown={handleMainKeydown}
      />
    </g>
  {/if}
  
  <!-- 双向连接的反向线 -->
  {#if isBidirectional}
    <path
      d={reversePathData}
      stroke="#10b981"
      stroke-width="2"
      fill="none"
      marker-end="url(#arrowhead-bidirectional-reverse)"
      class="pointer-events-auto"
      style="cursor: pointer;"
      stroke-dasharray="4,3"
      opacity="0.6"
    />
  {/if}
  
  <!-- 中点控制点（始终可见且可拖动，即使没有 controlPoints） -->
  <g>
    <title>拖动中点调整折线形状</title>
    <!-- 中点控制点中心 -->
    <circle
      cx={midpoint.x}
      cy={midpoint.y}
      r={isEditing ? "6" : "5"}
      fill={isEditing ? "#fbbf24" : "#6366f1"}
      stroke="white"
      stroke-width={isEditing ? "2" : "2"}
      class="pointer-events-auto"
      style="cursor: move; opacity: {isEditing ? 1 : 0.8};"
      on:mousedown={handleMidpointMouseDown}
      role="button"
      tabindex="0"
      aria-label="拖动中点"
    />
    <!-- 更大的拖拽区域 -->
    <circle
      cx={midpoint.x}
      cy={midpoint.y}
      r="18"
      fill="transparent"
      stroke="none"
      class="pointer-events-auto"
      style="cursor: move;"
      on:mousedown={handleMidpointMouseDown}
      on:contextmenu|preventDefault|stopPropagation={() => {
        if (connection.controlPoints && connection.controlPoints.length > 0 && confirm("确定要删除这个控制点吗？")) {
          onDeleteControlPoint(connection.id, 0);
        }
      }}
      role="button"
      tabindex="0"
      aria-label="拖动或删除中点"
    />
  </g>
  
  <!-- 额外的控制点（如果有多个） -->
  {#if connection.controlPoints && connection.controlPoints.length > 1}
    {#each connection.controlPoints.slice(1) as controlPoint, idx}
      <g>
        <title>拖拽编辑点调整折线形状 - 右键删除</title>
        <!-- 控制点中心 -->
        <circle
          cx={controlPoint.x}
          cy={controlPoint.y}
          r={isEditing ? "6" : "4"}
          fill={isEditing ? "#fbbf24" : "#6366f1"}
          stroke="white"
          stroke-width={isEditing ? "2" : "1.5"}
          class="pointer-events-auto"
          style="cursor: move; opacity: {isEditing ? 1 : 0.7};"
          on:mousedown={(e) => onControlPointMouseDown(connection.id, idx + 1, e)}
          role="button"
          tabindex="0"
          aria-label="拖动控制点"
        />
        <!-- 更大的拖拽区域 -->
        <circle
          cx={controlPoint.x}
          cy={controlPoint.y}
          r="15"
          fill="transparent"
          stroke="none"
          class="pointer-events-auto"
          style="cursor: move;"
          on:mousedown={(e) => onControlPointMouseDown(connection.id, idx + 1, e)}
          on:contextmenu|preventDefault|stopPropagation={() => {
            if (confirm("确定要删除这个控制点吗？")) {
              onDeleteControlPoint(connection.id, idx + 1);
            }
          }}
          role="button"
          tabindex="0"
          aria-label="删除控制点"
        />
      </g>
    {/each}
  {/if}
  
  <!-- 连接类型指示器（位置偏移，避免与中点控制点重合） -->
  <g>
    <title>{isBidirectional ? "双向连接 - 点击切换为单向" : "单向连接 - 点击切换为双向"}</title>
    <circle
      cx={indicatorPos.x}
      cy={indicatorPos.y}
      r="8"
      fill={isBidirectional ? "#10b981" : "#6366f1"}
      stroke="white"
      stroke-width="2"
      class="pointer-events-auto"
      style="cursor: pointer;"
      on:click|stopPropagation={() => onToggleType(connection.id)}
      role="button"
      tabindex="0"
      aria-label="切换连接类型"
      on:keydown={handleToggleKeydown}
    />
    {#if isBidirectional}
      <text
        x={indicatorPos.x}
        y={indicatorPos.y + 4}
        text-anchor="middle"
        fill="white"
        font-size="10"
        font-weight="bold"
        pointer-events="none"
      >↔</text>
    {:else}
      <text
        x={indicatorPos.x}
        y={indicatorPos.y + 4}
        text-anchor="middle"
        fill="white"
        font-size="10"
        font-weight="bold"
        pointer-events="none"
      >→</text>
    {/if}
  </g>
  
  <!-- 右键删除区域 -->
  {#if !isEditing}
    <g>
      <title>右键删除连接</title>
      <path
        d={pathData}
        stroke="transparent"
        stroke-width="20"
        fill="none"
        class="pointer-events-auto"
        style="cursor: pointer;"
        on:contextmenu|preventDefault|stopPropagation={() => onConnectionRightClick(connection.id)}
        role="button"
        tabindex="0"
        aria-label="删除连接"
      />
    </g>
  {/if}
</g>

