<script lang="ts">
	import { THEME_CONFIG } from '$lib/constants/theme';
	import type { DeliveryFileStats } from '$lib/utils/ticketStats';
	
	export let deliveryStats: DeliveryFileStats;
	export let type: 'primary' | 'secondary' = 'primary';
	
	$: theme = THEME_CONFIG.colors[type];
	$: bgClass = `bg-gradient-to-br ${theme.light} dark:${theme.dark}`;
	$: borderClass = `border ${theme.border}`;
	$: textClass = theme.text;
</script>

<div class="{bgClass} {borderClass} rounded-lg p-4">
	<div class="text-sm font-medium mb-3 {textClass} flex items-center">
		<svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
			<path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd"></path>
		</svg>
		交付文件总览
	</div>
	
	<div class="space-y-4 text-sm">
		<!-- 交付率 -->
		<div class="flex items-center justify-between">
			<span class="text-gray-500 dark:text-gray-400">交付完成率</span>
			<span class="font-medium text-lg {textClass}">{deliveryStats.deliveryRate}%</span>
		</div>
		
		<!-- 文件统计 -->
		<div class="bg-white/50 dark:bg-gray-800/50 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-xs font-medium text-gray-600 dark:text-gray-400">交付文件</p>
					<p class="text-lg font-semibold text-gray-900 dark:text-white">
						{deliveryStats.totalFiles}
					</p>
				</div>
				<svg class="w-6 h-6 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
					<path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"></path>
				</svg>
			</div>
		</div>
		
		<!-- 文字统计 -->
		<div class="bg-white/50 dark:bg-gray-800/50 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-xs font-medium text-gray-600 dark:text-gray-400">文字说明</p>
					<p class="text-lg font-semibold text-gray-900 dark:text-white">
						{deliveryStats.totalTextLength} 字符
					</p>
				</div>
				<svg class="w-6 h-6 text-purple-500" fill="currentColor" viewBox="0 0 20 20">
					<path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"></path>
				</svg>
			</div>
		</div>
		
		<!-- 工单统计 -->
		<div class="flex items-center justify-between">
			<span class="text-gray-500 dark:text-gray-400">有交付的工单</span>
			<span class="font-medium">{deliveryStats.ticketsWithDelivery} / {deliveryStats.totalTickets}</span>
		</div>
		
		<!-- 平均交付量 -->
		<div class="text-xs text-gray-500 dark:text-gray-400 bg-white/30 dark:bg-gray-800/30 rounded p-2">
			<div class="flex justify-between mb-1">
				<span>平均每工单文件数:</span>
				<span class="font-medium">
					{deliveryStats.ticketsWithDelivery > 0 ? Math.round(deliveryStats.totalFiles / deliveryStats.ticketsWithDelivery * 10) / 10 : 0}
				</span>
			</div>
			<div class="flex justify-between">
				<span>平均每工单图片数:</span>
				<span class="font-medium">
					{deliveryStats.ticketsWithDelivery > 0 ? Math.round(deliveryStats.totalImages / deliveryStats.ticketsWithDelivery * 10) / 10 : 0}
				</span>
			</div>
		</div>
	</div>
</div>
