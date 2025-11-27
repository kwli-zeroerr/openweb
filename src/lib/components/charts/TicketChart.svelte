<script lang="ts">
	import { CHART_CONFIG } from '$lib/constants/theme';
	
	export let data: { date: string; submitted: number; completed: number }[] = [];
	export let title = '工单趋势';
	export let showSubmitted = true;
	export let showCompleted = true;
	export let type: 'daily' | 'maintenance' = 'daily';
	
	$: chartId = `chart-${Math.random().toString(36).substr(2, 9)}`;
	$: submittedGradientId = `${chartId}-submitted`;
	$: completedGradientId = `${chartId}-completed`;
	$: maintenanceGradientId = `${chartId}-maintenance`;
	
	$: maxValue = data.length > 0 ? Math.max(
		...data.map(d => Math.max(d.submitted || 0, d.completed || 0)), 
		1
	) : 1;
	
	$: chartWidth = CHART_CONFIG.dimensions.width;
	$: chartHeight = CHART_CONFIG.dimensions.height;
	$: margin = CHART_CONFIG.dimensions.margin;
	$: plotWidth = chartWidth - margin * 2;
	$: plotHeight = chartHeight - margin * 2;
	
	// 计算X轴标签
	$: xAxisLabels = type === 'maintenance' 
		? data.filter((_, i) => i % 5 === 0).map(d => d.date.split('-')[1] + '-' + d.date.split('-')[2])
		: data.map(d => d.date.split('-')[1] + '-' + d.date.split('-')[2]);
</script>

<div class="relative">
	<div class="text-gray-500 dark:text-gray-400 mb-3">{title}</div>
	<div class="relative">
		<!-- SVG 图表 -->
		<svg width="100%" height="120" viewBox="0 0 {chartWidth} {chartHeight}" class="overflow-visible">
			<!-- 渐变定义 -->
			<defs>
				{#if showSubmitted}
					<linearGradient id={submittedGradientId} x1="0%" y1="0%" x2="0%" y2="100%">
						<stop offset="0%" style="stop-color:{CHART_CONFIG.gradients.submitted.color};stop-opacity:{CHART_CONFIG.gradients.submitted.opacity}" />
						<stop offset="100%" style="stop-color:{CHART_CONFIG.gradients.submitted.color};stop-opacity:0" />
					</linearGradient>
				{/if}
				{#if showCompleted}
					<linearGradient id={completedGradientId} x1="0%" y1="0%" x2="0%" y2="100%">
						<stop offset="0%" style="stop-color:{CHART_CONFIG.gradients.completed.color};stop-opacity:{CHART_CONFIG.gradients.completed.opacity}" />
						<stop offset="100%" style="stop-color:{CHART_CONFIG.gradients.completed.color};stop-opacity:0" />
					</linearGradient>
				{/if}
				{#if type === 'maintenance'}
					<linearGradient id={maintenanceGradientId} x1="0%" y1="0%" x2="0%" y2="100%">
						<stop offset="0%" style="stop-color:{CHART_CONFIG.gradients.maintenance.color};stop-opacity:{CHART_CONFIG.gradients.maintenance.opacity}" />
						<stop offset="100%" style="stop-color:{CHART_CONFIG.gradients.maintenance.color};stop-opacity:0" />
					</linearGradient>
				{/if}
			</defs>
			
			<!-- 网格线 -->
			{#each Array(5) as _, i}
				<line x1={margin} y1={margin + i * plotHeight / 4} x2={margin + plotWidth} y2={margin + i * plotHeight / 4} 
					  stroke={CHART_CONFIG.colors.grid} stroke-width="0.5" opacity={CHART_CONFIG.colors.gridOpacity} />
			{/each}
			
			<!-- 图表内容 -->
			{#if data.length > 0}
				<!-- 填充区域 -->
				{#if showSubmitted}
					<path d="M {margin},{margin + plotHeight} 
						{data.map((d, i) => `L${margin + i * plotWidth / (data.length - 1)}, ${margin + plotHeight - (d.submitted / maxValue) * plotHeight}`).join(' ')}
						L {margin + plotWidth},{margin + plotHeight} Z"
						fill="url(#{submittedGradientId})" />
				{/if}
				{#if showCompleted}
					<path d="M {margin},{margin + plotHeight} 
						{data.map((d, i) => `L${margin + i * plotWidth / (data.length - 1)}, ${margin + plotHeight - (d.completed / maxValue) * plotHeight}`).join(' ')}
						L {margin + plotWidth},{margin + plotHeight} Z"
						fill="url(#{completedGradientId})" />
				{/if}
				{#if type === 'maintenance'}
					<path d="M {margin},{margin + plotHeight} 
						{data.map((d, i) => `L${margin + i * plotWidth / (data.length - 1)}, ${margin + plotHeight - (d.completed / maxValue) * plotHeight}`).join(' ')}
						L {margin + plotWidth},{margin + plotHeight} Z"
						fill="url(#{maintenanceGradientId})" />
				{/if}
				
				<!-- 折线 -->
				{#if showSubmitted}
					<path d="M{margin + 0}, {margin + plotHeight - (data[0]?.submitted || 0) / maxValue * plotHeight}
						{data.map((d, i) => `L${margin + i * plotWidth / (data.length - 1)}, ${margin + plotHeight - (d.submitted / maxValue) * plotHeight}`).join(' ')}"
						fill="none" stroke={CHART_CONFIG.gradients.submitted.color} stroke-width={CHART_CONFIG.colors.strokeWidth} stroke-linecap="round" stroke-linejoin="round" />
				{/if}
				{#if showCompleted}
					<path d="M{margin + 0}, {margin + plotHeight - (data[0]?.completed || 0) / maxValue * plotHeight}
						{data.map((d, i) => `L${margin + i * plotWidth / (data.length - 1)}, ${margin + plotHeight - (d.completed / maxValue) * plotHeight}`).join(' ')}"
						fill="none" stroke={CHART_CONFIG.gradients.completed.color} stroke-width={CHART_CONFIG.colors.strokeWidth} stroke-linecap="round" stroke-linejoin="round" />
				{/if}
				{#if type === 'maintenance'}
					<path d="M{margin + 0}, {margin + plotHeight - (data[0]?.completed || 0) / maxValue * plotHeight}
						{data.map((d, i) => `L${margin + i * plotWidth / (data.length - 1)}, ${margin + plotHeight - (d.completed / maxValue) * plotHeight}`).join(' ')}"
						fill="none" stroke={CHART_CONFIG.gradients.maintenance.color} stroke-width={CHART_CONFIG.colors.strokeWidth} stroke-linecap="round" stroke-linejoin="round" />
				{/if}
				
				<!-- 数据点 -->
				{#each data as d, i}
					{#if showSubmitted}
						<circle cx={margin + i * plotWidth / (data.length - 1)} cy={margin + plotHeight - (d.submitted / maxValue) * plotHeight} 
								r={CHART_CONFIG.colors.pointRadius} fill={CHART_CONFIG.gradients.submitted.color} stroke="white" stroke-width={CHART_CONFIG.colors.pointStrokeWidth} class="hover:r-5 transition-all duration-200" />
					{/if}
					{#if showCompleted}
						<circle cx={margin + i * plotWidth / (data.length - 1)} cy={margin + plotHeight - (d.completed / maxValue) * plotHeight} 
								r={CHART_CONFIG.colors.pointRadius} fill={CHART_CONFIG.gradients.completed.color} stroke="white" stroke-width={CHART_CONFIG.colors.pointStrokeWidth} class="hover:r-5 transition-all duration-200" />
					{/if}
					{#if type === 'maintenance' && d.completed > 0}
						<circle cx={margin + i * plotWidth / (data.length - 1)} cy={margin + plotHeight - (d.completed / maxValue) * plotHeight} 
								r={CHART_CONFIG.colors.pointRadius} fill={CHART_CONFIG.gradients.maintenance.color} stroke="white" stroke-width={CHART_CONFIG.colors.pointStrokeWidth} class="hover:r-5 transition-all duration-200" />
					{/if}
				{/each}
			{/if}
		</svg>
		
		<!-- X轴标签 -->
		<div class="flex justify-between mt-2 px-2">
			{#each xAxisLabels as label}
				<span class="text-xs text-gray-500 dark:text-gray-400">{label}</span>
			{/each}
		</div>
		
		<!-- Y轴标签 -->
		<div class="absolute left-0 top-0 h-full flex flex-col justify-between py-2">
			{#each [maxValue, Math.ceil(maxValue * 0.75), Math.ceil(maxValue * 0.5), Math.ceil(maxValue * 0.25), 0] as value}
				<span class="text-xs text-gray-400 dark:text-gray-500">{value}</span>
			{/each}
		</div>
	</div>
	
	<!-- 图例 -->
	<div class="flex items-center justify-center space-x-4 mt-3 text-xs">
		{#if showSubmitted}
			<div class="flex items-center space-x-2">
				<div class="w-3 h-0.5 bg-blue-500"></div>
				<span class="text-gray-500 dark:text-gray-400">提交</span>
			</div>
		{/if}
		{#if showCompleted}
			<div class="flex items-center space-x-2">
				<div class="w-3 h-0.5 bg-green-500"></div>
				<span class="text-gray-500 dark:text-gray-400">完成</span>
			</div>
		{/if}
		{#if type === 'maintenance'}
			<div class="flex items-center space-x-2">
				<div class="w-3 h-0.5 bg-purple-500"></div>
				<span class="text-gray-500 dark:text-gray-400">维护部门完成</span>
			</div>
		{/if}
	</div>
</div>
