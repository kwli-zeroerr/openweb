<script lang="ts">
  import { onMount } from 'svelte';
  
  export let data: {
    date: string;
    daily_active_users: number;
    total_messages: number;
    total_thumbs_up: number;
  }[] = [];
  export let title = '每日趋势';
  export let showActiveUsers = true;
  export let showMessages = true;
  export let showThumbsUp = true;
  export let type: 'primary' | 'secondary' = 'primary';

  let canvas: HTMLCanvasElement;
  let containerWidth = 0;
  let containerHeight = 300;
  
  // 计算最大值
  $: maxValue = data.length > 0 ? Math.max(
    ...data.map(d => Math.max(
      d.daily_active_users || 0, 
      d.total_messages || 0, 
      d.total_thumbs_up || 0
    )), 
    1
  ) : 1;
  
  // 图表尺寸 - 响应式设计
  $: chartWidth = Math.max(containerWidth, 800);
  $: chartHeight = containerHeight;
  $: margin = containerWidth < 600 ? 40 : 50; // 小屏幕减少边距
  $: plotWidth = chartWidth - margin * 2;
  $: plotHeight = chartHeight - margin * 2;
  
  // X轴标签 - 根据数据量和容器宽度智能调整显示密度
  $: xAxisLabels = (() => {
    if (data.length === 0) return [];
    
    // 根据容器宽度和数据量决定最大标签数
    const availableWidth = plotWidth;
    const minLabelSpacing = 60; // 最小标签间距
    const maxLabels = Math.floor(availableWidth / minLabelSpacing);
    
    // 根据数据量决定显示间隔
    let step = 1;
    let targetMaxLabels = Math.min(maxLabels, 20);
    
    if (data.length > 90) {
      targetMaxLabels = Math.min(maxLabels, 12); // 90天最多显示12个标签
    } else if (data.length > 60) {
      targetMaxLabels = Math.min(maxLabels, 15); // 60天最多显示15个标签
    } else if (data.length > 30) {
      targetMaxLabels = Math.min(maxLabels, 10); // 30天最多显示10个标签
    } else if (data.length > 14) {
      targetMaxLabels = Math.min(maxLabels, 7); // 14天最多显示7个标签
    }
    
    step = Math.max(1, Math.ceil(data.length / targetMaxLabels));
    
    const labels = [];
    const usedIndices = new Set();
    
    // 添加第一个标签
    if (data.length > 0) {
      const firstDate = new Date(data[0].date);
      const firstLabel = formatDateLabel(firstDate, data.length);
      labels.push({ label: firstLabel, index: 0 });
      usedIndices.add(0);
    }
    
    // 添加中间标签
    for (let i = step; i < data.length - 1; i += step) {
      if (labels.length >= targetMaxLabels - 1) break; // 为最后一个标签留位置
      
      const date = new Date(data[i].date);
      const label = formatDateLabel(date, data.length);
      labels.push({ label, index: i });
      usedIndices.add(i);
    }
    
    // 确保最后一个数据点总是显示
    if (data.length > 1 && !usedIndices.has(data.length - 1)) {
      const lastDate = new Date(data[data.length - 1].date);
      const lastLabel = formatDateLabel(lastDate, data.length);
      labels.push({ label: lastLabel, index: data.length - 1 });
    }
    
    return labels.sort((a, b) => a.index - b.index);
  })();
  
  // 格式化日期标签
  function formatDateLabel(date: Date, totalDays: number): string {
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const year = date.getFullYear();
    
    if (totalDays > 90) {
      // 超过90天显示年/月格式，更紧凑
      return `${year}/${month}`;
    } else if (totalDays > 60) {
      // 60-90天显示月/日格式
      return `${month}/${day}`;
    } else if (totalDays > 30) {
      // 30-60天显示月/日格式
      return `${month}/${day}`;
    } else {
      // 30天内显示月/日格式
      return `${month}/${day}`;
    }
  }
  
  // 悬停状态
  let hoveredIndex = -1;
  let mouseX = 0;
  let mouseY = 0;
  
  function updateContainerSize() {
    if (canvas && canvas.parentElement) {
      containerWidth = canvas.parentElement.clientWidth;
    }
  }
  
  function drawChart() {
    if (!canvas || !data.length) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // 设置canvas尺寸
    canvas.width = chartWidth;
    canvas.height = chartHeight;
    
    // 设置样式
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.1)';
    ctx.lineWidth = 0.5;
    
    // 绘制网格线
    // 水平网格线
    for (let i = 0; i <= 4; i++) {
      const y = margin + (i * plotHeight / 4);
      ctx.beginPath();
      ctx.moveTo(margin, y);
      ctx.lineTo(margin + plotWidth, y);
      ctx.stroke();
    }
    
    // 垂直网格线
    for (let i = 0; i < data.length; i++) {
      const x = margin + (i * plotWidth / (data.length - 1));
      ctx.beginPath();
      ctx.moveTo(x, margin);
      ctx.lineTo(x, margin + plotHeight);
      ctx.stroke();
    }
    
    // 绘制数据线
    if (showActiveUsers) {
      drawLine(ctx, data.map(d => d.daily_active_users || 0), '#3b82f6', 2.5);
    }
    if (showMessages) {
      drawLine(ctx, data.map(d => d.total_messages || 0), '#10b981', 2.5);
    }
    if (showThumbsUp) {
      drawLine(ctx, data.map(d => d.total_thumbs_up || 0), '#f59e0b', 2.5);
    }
    
    // 绘制数据点
    for (let i = 0; i < data.length; i++) {
      const x = margin + (i * plotWidth / (data.length - 1));
      
      if (showActiveUsers) {
        const y = margin + plotHeight - ((data[i].daily_active_users || 0) / maxValue) * plotHeight;
        drawPoint(ctx, x, y, '#3b82f6', hoveredIndex === i ? 6 : 4);
      }
      if (showMessages) {
        const y = margin + plotHeight - ((data[i].total_messages || 0) / maxValue) * plotHeight;
        drawPoint(ctx, x, y, '#10b981', hoveredIndex === i ? 6 : 4);
      }
      if (showThumbsUp) {
        const y = margin + plotHeight - ((data[i].total_thumbs_up || 0) / maxValue) * plotHeight;
        drawPoint(ctx, x, y, '#f59e0b', hoveredIndex === i ? 6 : 4);
      }
    }
    
    // 绘制Y轴标签
    ctx.fillStyle = '#6b7280';
    ctx.font = '12px system-ui';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    
    for (let i = 0; i <= 4; i++) {
      const value = Math.ceil(maxValue * (4 - i) / 4);
      const y = margin + (i * plotHeight / 4);
      ctx.fillText(value.toString(), margin - 10, y);
    }
  }
  
  function drawLine(ctx: CanvasRenderingContext2D, values: number[], color: string, width: number) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    
    ctx.beginPath();
    for (let i = 0; i < values.length; i++) {
      const x = margin + (i * plotWidth / (values.length - 1));
      const y = margin + plotHeight - (values[i] / maxValue) * plotHeight;
      
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
  }
  
  function drawPoint(ctx: CanvasRenderingContext2D, x: number, y: number, color: string, radius: number) {
    ctx.fillStyle = color;
    ctx.strokeStyle = 'white';
    ctx.lineWidth = 2;
    
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, 2 * Math.PI);
    ctx.fill();
    ctx.stroke();
  }
  
  function handleMouseMove(event: MouseEvent) {
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    mouseX = event.clientX - rect.left;
    mouseY = event.clientY - rect.top;
    
    // 计算悬停的数据点索引
    const relativeX = mouseX - margin;
    const pointWidth = plotWidth / (data.length - 1);
    hoveredIndex = Math.round(relativeX / pointWidth);
    
    // 确保索引在有效范围内
    if (hoveredIndex < 0 || hoveredIndex >= data.length) {
      hoveredIndex = -1;
    }
    
    // 重新绘制以更新悬停效果
    drawChart();
  }
  
  function handleMouseLeave() {
    hoveredIndex = -1;
    drawChart();
  }
  
  // 监听数据变化和容器尺寸变化
  $: if (data.length > 0) {
    drawChart();
  }
  
  onMount(() => {
    updateContainerSize();
    window.addEventListener('resize', updateContainerSize);
    
    return () => {
      window.removeEventListener('resize', updateContainerSize);
    };
  });
</script>

<div class="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700 w-full">
  <h3 class="text-base font-semibold text-gray-900 dark:text-white mb-4">{title}</h3>
  
  <div class="relative w-full">
    <!-- Canvas 图表 -->
    <canvas
      bind:this={canvas}
      class="w-full cursor-crosshair"
      style="height: {chartHeight}px;"
      on:mousemove={handleMouseMove}
      on:mouseleave={handleMouseLeave}
    ></canvas>
    
    <!-- X轴标签 - 使用Canvas坐标精确对齐 -->
    <div class="relative mt-3" style="height: 20px;">
      {#each xAxisLabels as { label, index }}
        <span 
          class="absolute text-xs sm:text-sm text-gray-500 dark:text-gray-400" 
          style="left: {margin + (index * plotWidth / (data.length - 1))}px; transform: translateX(-50%);"
        >
          {label}
        </span>
      {/each}
    </div>
    
    <!-- 悬停提示框 -->
    {#if hoveredIndex >= 0 && hoveredIndex < data.length}
      <div
        class="absolute bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 pointer-events-none z-10"
        style="left: {mouseX + 10}px; top: {mouseY - 10}px; transform: translateY(-100%);"
      >
        <div class="text-sm font-medium text-gray-900 dark:text-white mb-2">
          {new Date(data[hoveredIndex].date).toLocaleDateString('zh-CN')}
        </div>
        <div class="space-y-1 text-xs">
          {#if showActiveUsers}
            <div class="flex items-center gap-2">
              <div class="w-3 h-0.5 bg-blue-500"></div>
              <span class="text-gray-600 dark:text-gray-400">活跃用户:</span>
              <span class="font-medium text-gray-900 dark:text-white">{data[hoveredIndex].daily_active_users}</span>
            </div>
          {/if}
          {#if showMessages}
            <div class="flex items-center gap-2">
              <div class="w-3 h-0.5 bg-green-500"></div>
              <span class="text-gray-600 dark:text-gray-400">对话数:</span>
              <span class="font-medium text-gray-900 dark:text-white">{data[hoveredIndex].total_messages}</span>
            </div>
          {/if}
          {#if showThumbsUp}
            <div class="flex items-center gap-2">
              <div class="w-3 h-0.5 bg-yellow-500"></div>
              <span class="text-gray-600 dark:text-gray-400">点赞数:</span>
              <span class="font-medium text-gray-900 dark:text-white">{data[hoveredIndex].total_thumbs_up}</span>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
  
  <!-- 图例 -->
  <div class="flex items-center justify-center space-x-6 mt-4 text-xs">
    {#if showActiveUsers}
      <div class="flex items-center space-x-2">
        <div class="w-3 h-0.5 bg-blue-500"></div>
        <span class="text-gray-500 dark:text-gray-400">活跃用户</span>
      </div>
    {/if}
    {#if showMessages}
      <div class="flex items-center space-x-2">
        <div class="w-3 h-0.5 bg-green-500"></div>
        <span class="text-gray-500 dark:text-gray-400">对话数</span>
      </div>
    {/if}
    {#if showThumbsUp}
      <div class="flex items-center space-x-2">
        <div class="w-3 h-0.5 bg-yellow-500"></div>
        <span class="text-gray-500 dark:text-gray-400">点赞数</span>
      </div>
    {/if}
  </div>
</div>