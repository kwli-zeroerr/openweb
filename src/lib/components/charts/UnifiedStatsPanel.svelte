<script lang="ts">
	import { THEME_CONFIG } from '$lib/constants/theme';
	import TicketChart from './TicketChart.svelte';
	import type { TicketStats } from '$lib/utils/ticketStats';
	
	export let stats: TicketStats;
	
	// 当前选中的标签页
	let activeTab: 'overview' | 'maintenance' | 'delivery' = 'overview';
	
	$: theme = THEME_CONFIG.colors.primary;
	$: bgClass = `bg-gradient-to-br ${theme.light} dark:${theme.dark}`;
	$: borderClass = `border ${theme.border}`;
	$: textClass = theme.text;
	
	// 标签页配置
	const tabs = [
		{ id: 'overview' as const, label: '数据统计' },
		{ id: 'maintenance' as const, label: '维护统计' },
		{ id: 'delivery' as const, label: '交付统计' }
	];
</script>

<div class="{bgClass} {borderClass} rounded-lg p-4">
	<!-- 标签页导航 -->
	<div class="mb-4">
		<div class="flex space-x-1 border-b border-gray-200 dark:border-gray-600">
			{#each tabs as tab}
				<button
					class="px-3 py-2 text-sm font-medium transition-colors {activeTab === tab.id 
						? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400' 
						: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
					on:click={() => activeTab = tab.id}
				>
					{tab.label}
				</button>
			{/each}
		</div>
	</div>
	
	<!-- 内容区域 -->
	<div class="space-y-4 text-sm">
		{#if activeTab === 'overview'}
			<!-- 数据统计内容 -->
			<div class="flex items-center justify-between">
				<span class="text-gray-500 dark:text-gray-400">近7天平均完成时长</span>
				<span class="font-medium">{stats.avgCompletionHours} 小时</span>
			</div>
			
			<!-- 每日工单数量折线图 -->
			<TicketChart 
				data={stats.last7Days} 
				title="近7天工单趋势"
				showSubmitted={true}
				showCompleted={true}
				type="daily"
			/>
			
			<div>
				<div class="text-gray-500 dark:text-gray-400 mb-1">维护者完成量 Top</div>
				<div class="space-y-1">
					{#each stats.completedByMaintainer as m}
						<div class="flex items-center justify-between">
							<span class="text-sm">{m.name}</span>
							<span class="text-sm font-medium">{m.count}</span>
						</div>
					{/each}
				</div>
			</div>
			
			<div>
				<div class="text-gray-500 dark:text-gray-400 mb-1">提交者排行 Top</div>
				<div class="space-y-1">
					{#each stats.submittedByUser as user}
						<div class="flex items-center justify-between">
							<span class="text-sm">{user.name}</span>
							<span class="text-sm font-medium">{user.count}</span>
						</div>
					{/each}
				</div>
			</div>
			
		{:else if activeTab === 'maintenance'}
			<!-- 维护部门工单统计内容 -->
			<div class="flex items-center justify-between">
				<span class="text-gray-500 dark:text-gray-400">近30天完成总数</span>
				<span class="font-medium text-lg text-blue-600 dark:text-blue-400">{stats.maintenanceCompletedTotal}</span>
			</div>
			
			<!-- 维护部门工单趋势图 -->
			<TicketChart 
				data={stats.last30Days} 
				title="近30天完成趋势"
				showSubmitted={false}
				showCompleted={true}
				type="maintenance"
			/>
			
			<!-- 周统计 -->
			<div>
				<div class="text-gray-500 dark:text-gray-400 mb-1">近4周完成量</div>
				<div class="space-y-1">
					{#each stats.maintenanceCompletedByWeek as week}
						<div class="flex items-center justify-between">
							<span class="text-xs text-gray-500 dark:text-gray-400">
								{week.week.split('-')[1]}-{week.week.split('-')[2]}周
							</span>
							<span class="text-xs font-medium">{week.count}</span>
						</div>
					{/each}
				</div>
			</div>
			
			<!-- 解决部门排行 -->
			<div>
				<div class="text-gray-500 dark:text-gray-400 mb-1">解决部门排行 Top</div>
				<div class="space-y-1">
					{#each stats.resolvedByDepartment as dept}
						<div class="flex items-center justify-between">
							<span class="text-sm">{dept.department}</span>
							<span class="text-sm font-medium">{dept.count}</span>
						</div>
					{/each}
				</div>
			</div>
			
		{:else if activeTab === 'delivery'}
			<!-- 交付文件统计内容 -->
			<div class="flex items-center justify-between">
				<span class="text-gray-500 dark:text-gray-400">交付完成率</span>
				<span class="font-medium text-lg {textClass}">{stats.deliveryStats.deliveryRate}%</span>
			</div>
			
			<!-- 工单交付情况列表 -->
			<div>
				<div class="text-gray-500 dark:text-gray-400 mb-2">工单交付情况</div>
				<div class="space-y-2 max-h-48 overflow-y-auto">
					{#each stats.deliveryStats.ticketsWithDeliveryDetails || [] as ticket}
						<div class="bg-white/50 dark:bg-gray-800/50 rounded-lg p-3 border border-gray-200 dark:border-gray-700 cursor-pointer hover:bg-white/70 dark:hover:bg-gray-800/70 transition-colors"
							 on:click={() => window.open(`/tickets/${ticket.id}`, '_blank')}
							 on:keydown={(e) => e.key === 'Enter' && window.open(`/tickets/${ticket.id}`, '_blank')}
							 role="button"
							 tabindex="0">
							<div class="flex items-center justify-between mb-2">
								<div class="text-sm font-medium text-gray-900 dark:text-white truncate">
									{ticket.title || `工单 #${ticket.id.slice(-6)}`}
								</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{ticket.status === 'verified' ? '✅' : ticket.status === 'submitted' ? '⏳' : '❌'}
								</div>
							</div>
							<div class="grid grid-cols-2 gap-2 text-xs">
								<div class="flex items-center">
									<svg class="w-3 h-3 text-blue-500 mr-1" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"></path>
									</svg>
									<span class="text-gray-600 dark:text-gray-400">{ticket.filesCount || 0} 文件</span>
								</div>
								<div class="flex items-center">
									<svg class="w-3 h-3 text-purple-500 mr-1" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"></path>
									</svg>
									<span class="text-gray-600 dark:text-gray-400">{ticket.textLength || 0} 字符</span>
								</div>
							</div>
							{#if ticket.deliveryText}
								<div class="mt-2 text-xs text-gray-500 dark:text-gray-400 truncate">
									{ticket.deliveryText}
								</div>
							{/if}
						</div>
					{:else}
						<div class="text-center text-gray-500 dark:text-gray-400 py-4">
							<div class="text-sm">暂无交付数据</div>
							<div class="text-xs mt-1">工单完成后会显示交付情况</div>
						</div>
					{/each}
				</div>
			</div>
			
			<!-- 总体统计 -->
			<div class="text-xs text-gray-500 dark:text-gray-400 bg-white/30 dark:bg-gray-800/30 rounded p-2">
				<div class="flex justify-between mb-1">
					<span>总工单数:</span>
					<span class="font-medium">{stats.deliveryStats.totalTickets}</span>
				</div>
				<div class="flex justify-between mb-1">
					<span>有交付工单:</span>
					<span class="font-medium">{stats.deliveryStats.ticketsWithDelivery}</span>
				</div>
				<div class="flex justify-between">
					<span>交付率:</span>
					<span class="font-medium">{stats.deliveryStats.deliveryRate}%</span>
				</div>
			</div>
		{/if}
	</div>
</div>
