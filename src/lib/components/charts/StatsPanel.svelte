<script lang="ts">
	import { THEME_CONFIG } from '$lib/constants/theme';
	import TicketChart from './TicketChart.svelte';
	import type { TicketStats } from '$lib/utils/ticketStats';
	
	export let stats: TicketStats;
	export let type: 'primary' | 'secondary' = 'primary';
	
	$: theme = THEME_CONFIG.colors[type];
	$: bgClass = `bg-gradient-to-br ${theme.light} dark:${theme.dark}`;
	$: borderClass = `border ${theme.border}`;
	$: textClass = theme.text;
</script>

<div class="{bgClass} {borderClass} rounded-lg p-4">
	<div class="text-sm font-medium mb-3 {textClass}">
		{type === 'primary' ? '数据统计' : '维护部门工单统计'}
	</div>
	<div class="space-y-4 text-sm">
		{#if type === 'primary'}
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
		{:else}
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
		{/if}
	</div>
</div>
