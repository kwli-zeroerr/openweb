<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');
	const t = (i18n as any)?.t || ((key: string) => key);

	export let knowledgeId: string;

	let loading = false;
	let error: string | null = null;
	let results: any[] = [];

	onMount(async () => {
		// 加载清洗结果
		loading = true;
		try {
			// TODO: 调用 API 获取清洗结果
			results = [];
		} catch (e: any) {
			error = e.message || '加载清洗结果失败';
			toast.error(error);
		} finally {
			loading = false;
		}
	});
</script>

<div class="flex flex-col h-full p-4">
	<div class="mb-4">
		<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
			{@html t('清洗结果') || '清洗结果'}
		</h2>
		<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
			{@html t('查看知识库文件的清洗结果') || '查看知识库文件的清洗结果'}
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
	{:else if results.length === 0}
		<div class="flex-1 flex items-center justify-center">
			<div class="text-center">
				<p class="text-gray-500 dark:text-gray-400">
					{@html t('暂无清洗结果') || '暂无清洗结果'}
				</p>
			</div>
		</div>
	{:else}
		<div class="flex-1 overflow-y-auto">
			<div class="space-y-4">
				{#each results as result}
					<div class="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
						<!-- 清洗结果项 -->
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>

