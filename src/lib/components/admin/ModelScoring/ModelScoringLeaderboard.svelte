<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { models } from '$lib/stores';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	export let feedbacks = [];

	let modelScores = [];
	let loadingScores = true;
	let query = '';
	let debounceTimer;

	let orderBy: string = 'average_rating'; // default sort column
	let direction: 'asc' | 'desc' = 'desc'; // default sort order

	type ModelScore = {
		model_id: string;
		model_name: string;
		total_feedback: number;
		positive_feedback: number;
		negative_feedback: number;
		thumbs_up: number;
		thumbs_down: number;
		average_rating: number;
		win_rate: number;
		total_messages: number;
		last_updated: number;
	};

	// 获取模型评分数据
	async function fetchModelScores() {
		try {
			loadingScores = true;
			const response = await fetch(`${WEBUI_BASE_URL}/api/v1/model-scoring/leaderboard?sort_by=${orderBy}&order=${direction}&limit=100`);
			
			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}
			
			const data = await response.json();
			modelScores = data.models || [];
		} catch (error) {
			console.error('获取模型评分失败:', error);
			modelScores = [];
		} finally {
			loadingScores = false;
		}
	}

	// 搜索功能
	function handleSearch() {
		clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			filterModelScores();
		}, 300);
	}

	function filterModelScores() {
		if (!query.trim()) {
			return modelScores;
		}
		
		const searchTerm = query.toLowerCase();
		return modelScores.filter(score => 
			score.model_name.toLowerCase().includes(searchTerm) ||
			score.model_id.toLowerCase().includes(searchTerm)
		);
	}

	// 排序功能
	function handleSort(column: string) {
		if (orderBy === column) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = column;
			direction = 'desc';
		}
		fetchModelScores();
	}

	// 格式化数字
	function formatNumber(num: number): string {
		if (num >= 1000000) {
			return (num / 1000000).toFixed(1) + 'M';
		} else if (num >= 1000) {
			return (num / 1000).toFixed(1) + 'K';
		}
		return num.toString();
	}

	// 格式化百分比
	function formatPercentage(num: number): string {
		return (num * 100).toFixed(1) + '%';
	}

	// 格式化时间
	function formatTime(timestamp: number): string {
		const date = new Date(timestamp);
		return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN');
	}

	// 获取评分颜色
	function getRatingColor(rating: number): string {
		if (rating >= 0.5) return 'text-green-600 dark:text-green-400';
		if (rating >= 0) return 'text-yellow-600 dark:text-yellow-400';
		return 'text-red-600 dark:text-red-400';
	}

	// 获取胜率颜色
	function getWinRateColor(winRate: number): string {
		if (winRate >= 0.7) return 'text-green-600 dark:text-green-400';
		if (winRate >= 0.5) return 'text-yellow-600 dark:text-yellow-400';
		return 'text-red-600 dark:text-red-400';
	}

	onMount(() => {
		fetchModelScores();
	});

	$: filteredScores = filterModelScores();
</script>

<div class="flex flex-col space-y-4">
	<!-- 标题和搜索 -->
	<div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
		<div>
			<h2 class="text-2xl font-bold text-gray-900 dark:text-gray-100">
				ZeroErr GPT 模型评分排行榜
			</h2>
			<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
				基于用户反馈和点赞点踩数据的模型性能评估
			</p>
		</div>
		
		<div class="flex items-center space-x-2">
			<div class="relative">
				<Search class="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
				<input
					type="text"
					placeholder="搜索模型..."
					bind:value={query}
					on:input={handleSearch}
					class="pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				/>
			</div>
		</div>
	</div>

	<!-- 加载状态 -->
	{#if loadingScores}
		<div class="flex justify-center items-center py-8">
			<Spinner />
			<span class="ml-2 text-gray-600 dark:text-gray-400">正在加载模型评分数据...</span>
		</div>
	{:else if filteredScores.length === 0}
		<div class="text-center py-8">
			<div class="text-gray-500 dark:text-gray-400">
				{#if query}
					没有找到匹配的模型
				{:else}
					暂无模型评分数据
				{/if}
			</div>
		</div>
	{:else}
		<!-- 评分统计表格 -->
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
			<div class="overflow-x-auto">
				<table class="w-full text-sm text-left text-gray-600 dark:text-gray-300">
					<thead class="bg-gradient-to-r from-blue-500 to-purple-600 text-white">
						<tr>
							<th class="px-4 py-3 font-semibold text-sm first:rounded-tl-xl last:rounded-tr-xl">
								<div class="flex items-center gap-2">
									<span>排名</span>
								</div>
							</th>
							<th class="px-4 py-3 font-semibold text-sm">
								<button
									class="flex items-center gap-2 hover:text-blue-200 transition-colors"
									on:click={() => handleSort('model_name')}
								>
									<span>模型名称</span>
									{#if orderBy === 'model_name'}
										{#if direction === 'asc'}
											<ChevronUp class="w-4 h-4" />
										{:else}
											<ChevronDown class="w-4 h-4" />
										{/if}
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 font-semibold text-sm">
								<button
									class="flex items-center gap-2 hover:text-blue-200 transition-colors"
									on:click={() => handleSort('average_rating')}
								>
									<span>平均评分</span>
									{#if orderBy === 'average_rating'}
										{#if direction === 'asc'}
											<ChevronUp class="w-4 h-4" />
										{:else}
											<ChevronDown class="w-4 h-4" />
										{/if}
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 font-semibold text-sm">
								<button
									class="flex items-center gap-2 hover:text-blue-200 transition-colors"
									on:click={() => handleSort('win_rate')}
								>
									<span>胜率</span>
									{#if orderBy === 'win_rate'}
										{#if direction === 'asc'}
											<ChevronUp class="w-4 h-4" />
										{:else}
											<ChevronDown class="w-4 h-4" />
										{/if}
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 font-semibold text-sm">
								<button
									class="flex items-center gap-2 hover:text-blue-200 transition-colors"
									on:click={() => handleSort('total_feedback')}
								>
									<span>总反馈数</span>
									{#if orderBy === 'total_feedback'}
										{#if direction === 'asc'}
											<ChevronUp class="w-4 h-4" />
										{:else}
											<ChevronDown class="w-4 h-4" />
										{/if}
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 font-semibold text-sm">
								<span>点赞/点踩</span>
							</th>
							<th class="px-4 py-3 font-semibold text-sm">
								<span>总消息数</span>
							</th>
							<th class="px-4 py-3 font-semibold text-sm">
								<span>最后更新</span>
							</th>
						</tr>
					</thead>
					<tbody class="bg-white dark:bg-gray-800">
						{#each filteredScores as score, index}
							<tr class="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-150 {index % 2 === 0 ? 'bg-white dark:bg-gray-800' : 'bg-gray-50/50 dark:bg-gray-750'}">
								<td class="px-4 py-3 text-gray-900 dark:text-gray-100 font-medium">
									#{index + 1}
								</td>
								<td class="px-4 py-3 text-gray-900 dark:text-gray-100">
									<div class="flex flex-col">
										<span class="font-medium">{score.model_name}</span>
										<span class="text-xs text-gray-500 dark:text-gray-400">{score.model_id}</span>
									</div>
								</td>
								<td class="px-4 py-3">
									<span class="font-medium {getRatingColor(score.average_rating)}">
										{score.average_rating.toFixed(2)}
									</span>
								</td>
								<td class="px-4 py-3">
									<span class="font-medium {getWinRateColor(score.win_rate)}">
										{formatPercentage(score.win_rate)}
									</span>
								</td>
								<td class="px-4 py-3 text-gray-900 dark:text-gray-100">
									<div class="flex flex-col">
										<span class="font-medium">{formatNumber(score.total_feedback)}</span>
										<div class="text-xs text-gray-500 dark:text-gray-400">
											<span class="text-green-600 dark:text-green-400">+{score.positive_feedback}</span>
											<span class="mx-1">/</span>
											<span class="text-red-600 dark:text-red-400">-{score.negative_feedback}</span>
										</div>
									</div>
								</td>
								<td class="px-4 py-3 text-gray-900 dark:text-gray-100">
									<div class="flex items-center gap-2">
										<div class="flex items-center gap-1">
											<span class="text-green-600 dark:text-green-400">👍</span>
											<span class="text-sm">{score.thumbs_up}</span>
										</div>
										<div class="flex items-center gap-1">
											<span class="text-red-600 dark:text-red-400">👎</span>
											<span class="text-sm">{score.thumbs_down}</span>
										</div>
									</div>
								</td>
								<td class="px-4 py-3 text-gray-900 dark:text-gray-100">
									{formatNumber(score.total_messages)}
								</td>
								<td class="px-4 py-3 text-gray-500 dark:text-gray-400 text-xs">
									{formatTime(score.last_updated)}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>

		<!-- 统计摘要 -->
		<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
			<div class="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
				<div class="text-sm text-gray-600 dark:text-gray-400">总模型数</div>
				<div class="text-2xl font-bold text-gray-900 dark:text-gray-100">{modelScores.length}</div>
			</div>
			<div class="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
				<div class="text-sm text-gray-600 dark:text-gray-400">总反馈数</div>
				<div class="text-2xl font-bold text-gray-900 dark:text-gray-100">
					{formatNumber(modelScores.reduce((sum, score) => sum + score.total_feedback, 0))}
				</div>
			</div>
			<div class="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
				<div class="text-sm text-gray-600 dark:text-gray-400">平均评分</div>
				<div class="text-2xl font-bold text-gray-900 dark:text-gray-100">
					{(modelScores.reduce((sum, score) => sum + score.average_rating, 0) / modelScores.length).toFixed(2)}
				</div>
			</div>
			<div class="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
				<div class="text-sm text-gray-600 dark:text-gray-400">平均胜率</div>
				<div class="text-2xl font-bold text-gray-900 dark:text-gray-100">
					{formatPercentage(modelScores.reduce((sum, score) => sum + score.win_rate, 0) / modelScores.length)}
				</div>
			</div>
		</div>
	{/if}
</div>
