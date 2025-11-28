<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');
	const t = (i18n as any)?.t || ((key: string) => key);

	export let knowledgeId: string;
	export let files: any[] = [];

	let loading = false;
	let error: string | null = null;

	onMount(() => {
		// 初始化数据清洗面板
	});
</script>

<div class="flex flex-col h-full p-4">
	<div class="mb-4">
		<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
			{@html t('数据清洗') || '数据清洗'}
		</h2>
		<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
			{@html t('对知识库文件进行数据清洗和预处理') || '对知识库文件进行数据清洗和预处理'}
		</p>
	</div>

	{#if loading}
		<div class="flex-1 flex items-center justify-center">
			<Spinner className="size-8" />
		</div>
	{:else if error}
		<div class="flex-1 flex items-center justify-center">
			<div class="text-center">
				<p class="text-red-500 mb-4">{error}</p>
				<button
					class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
					on:click={() => (error = null)}
				>
					{@html t('重试') || '重试'}
				</button>
			</div>
		</div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="space-y-4">
				<div class="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
					<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
						{@html t('数据清洗功能') || '数据清洗功能'}
					</h3>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						{@html t('数据清洗功能正在开发中...') || '数据清洗功能正在开发中...'}
					</p>
				</div>
			</div>
		</div>
	{/if}
</div>

