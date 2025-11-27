<script lang="ts">
	export let isVisible: boolean = false;
</script>

{#if isVisible}
	<div class="sticky top-0 z-30 bg-white/70 dark:bg-gray-900/70 backdrop-blur border-b border-gray-200 dark:border-gray-700 transition-all duration-200">
		<div class="max-w-7xl mx-auto px-6 py-3">
			<div class="flex items-center justify-between">
				<!-- 左侧：紧凑状态信息 -->
				<div class="flex items-center gap-3">
					<div class="flex items-center gap-2">
						<div class="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
						<span class="text-sm font-medium text-gray-900 dark:text-white">待处理</span>
					</div>
					<div class="w-px h-4 bg-gray-300 dark:bg-gray-600"></div>
					<span class="text-sm text-gray-600 dark:text-gray-400">中优先级</span>
				</div>
				
				<!-- 右侧：主要操作按钮 -->
				<div class="flex items-center gap-3">
					<button class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm transition-all duration-200 hover:scale-105 active:scale-95">
						提交交付
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}
