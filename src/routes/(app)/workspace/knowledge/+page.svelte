<script>
	import { onMount } from 'svelte';
	import { knowledge } from '$lib/stores';
	import { toast } from 'svelte-sonner';

	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import Knowledge from '$lib/components/workspace/Knowledge.svelte';

	let loading = true;
	let error = null;

	onMount(async () => {
		try {
			loading = true;
			const knowledgeData = await getKnowledgeBases(localStorage.token);
			knowledge.set(knowledgeData);
		} catch (err) {
			console.error('Error loading knowledge bases:', err);
			error = err;
			toast.error('加载知识库失败，请稍后重试');
		} finally {
			loading = false;
		}
	});
</script>

{#if loading}
	<div class="flex items-center justify-center h-64">
		<div class="text-center">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
			<p class="text-gray-600 dark:text-gray-400">加载知识库中...</p>
		</div>
	</div>
{:else if error}
	<div class="flex items-center justify-center h-64">
		<div class="text-center">
			<div class="text-red-500 mb-4">
				<svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
				</svg>
			</div>
			<p class="text-gray-600 dark:text-gray-400 mb-4">加载知识库失败</p>
			<button 
				on:click={() => window.location.reload()} 
				class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
			>
				重新加载
			</button>
		</div>
	</div>
{:else if $knowledge !== null}
	<Knowledge />
{/if}
