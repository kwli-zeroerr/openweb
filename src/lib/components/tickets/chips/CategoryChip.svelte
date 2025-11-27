<script lang="ts">
	import { getCategoryInfo } from '$lib/constants/tickets';
	
	export let category: string;
	export let size: 'sm' | 'md' | 'lg' = 'md';
	
	const categoryInfo = getCategoryInfo(category);
	
	const sizeClasses = {
		sm: 'px-2 py-1 text-xs',
		md: 'px-3 py-1.5 text-sm',
		lg: 'px-4 py-2 text-base'
	};
</script>

<div class="inline-flex items-center gap-2 {sizeClasses[size]} rounded-lg font-medium bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-600 transition-all duration-200 hover:shadow-md hover:scale-105">
	<svelte:component this={categoryInfo.icon} className="w-4 h-4 {categoryInfo.color}" />
	<span class="whitespace-nowrap text-gray-700 dark:text-gray-300">{categoryInfo.label}</span>
</div>
