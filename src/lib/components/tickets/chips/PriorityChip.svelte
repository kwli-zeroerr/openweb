<script lang="ts">
	import { getPriorityInfo } from '$lib/constants/tickets';
	
	export let priority: string;
	export let size: 'sm' | 'md' | 'lg' = 'md';
	
	const priorityInfo = getPriorityInfo(priority);
	
	const sizeClasses = {
		sm: 'px-2 py-1 text-xs',
		md: 'px-3 py-1.5 text-sm',
		lg: 'px-4 py-2 text-base'
	};
	
	// 特殊处理urgent优先级
	const isUrgent = priority === 'urgent';
	const urgentClasses = isUrgent ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 border-red-200 dark:border-red-700' : '';
</script>

<div class="inline-flex items-center gap-2 {sizeClasses[size]} rounded-lg font-medium bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-600 transition-all duration-200 hover:shadow-md hover:scale-105 {urgentClasses}">
	<div class="w-2 h-2 rounded-full {priorityInfo.color.replace('text-', 'bg-')}"></div>
	<span class="whitespace-nowrap text-gray-700 dark:text-gray-300">{priorityInfo.label}优先级</span>
</div>
