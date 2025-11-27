<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	
	// 导入组件
	import PromptsPanel from './Prompts.svelte';
	import RAGPanel from './RAG/RAGPanel.svelte';
	
	const i18n = getContext('i18n');
	const t = (i18n as any)?.t || ((key: string) => key);

	let activeNavTab = 'prompts'; // 默认显示提示词
	let loading = false;

	// 切换导航标签
	const handleNavTabChange = (tab: string) => {
		activeNavTab = tab;
	};

	onMount(() => {
		// Agent 面板初始化
	});
</script>

<div class="flex flex-col w-full h-full translate-y-1">
	{#if loading}
		<div class="flex-1 flex items-center justify-center">
			<Spinner className="size-5" />
		</div>
	{:else}
		<!-- 主内容区域 -->
		<div class="flex flex-1 h-full max-h-full">
			<!-- 左侧导航栏 -->
			<div class="w-48 bg-gray-50 dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
				<div class="p-4 border-b border-gray-200 dark:border-gray-700">
					<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100">功能面板</h3>
				</div>
				<nav class="flex-1 p-2 overflow-y-auto">
					<div class="space-y-1">
						<button
							class="w-full text-left px-3 py-2 text-sm rounded-md transition-colors {activeNavTab === 'prompts' ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}"
							on:click={() => handleNavTabChange('prompts')}
						>
							<i class="fas fa-comment-dots mr-2"></i>
							提示词
						</button>
						<button
							class="w-full text-left px-3 py-2 text-sm rounded-md transition-colors {activeNavTab === 'rag' ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}"
							on:click={() => handleNavTabChange('rag')}
						>
							<i class="fas fa-brain mr-2"></i>
							RAG
						</button>
					</div>
				</nav>
			</div>

			<!-- 右侧内容区域 -->
			<div class="flex-1 flex flex-col h-full overflow-hidden">
				{#if activeNavTab === 'prompts'}
					<!-- 提示词面板 -->
					<div class="flex-1 h-full overflow-auto p-4">
						<PromptsPanel />
					</div>
				{:else if activeNavTab === 'rag'}
					<!-- RAG面板 -->
					<div class="flex-1 h-full overflow-hidden">
						<RAGPanel knowledgeId={""} />
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>

