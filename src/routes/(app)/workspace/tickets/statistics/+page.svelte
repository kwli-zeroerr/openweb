<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { getTicketStats } from '$lib/apis/tickets';
	import ArrowLeft from '$lib/components/icons/ArrowLeft.svelte';
	import ChartBar from '$lib/components/icons/ChartBar.svelte';

	let stats: any = null;
	let loading = true;

	// 检查用户权限
	$: if ($user && $user.role !== 'admin') {
		toast.error('您没有权限访问此页面');
		goto('/workspace/tickets');
	}

	async function loadStats() {
		try {
			loading = true;
			stats = await getTicketStats();
		} catch (error) {
			console.error('Error loading stats:', error);
			toast.error('加载统计数据失败');
		} finally {
			loading = false;
		}
	}

	function goBack() {
		goto('/workspace/tickets');
	}

	onMount(() => {
		loadStats();
	});
</script>

<svelte:head>
	<title>数据统计 - 工单管理系统</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
	<!-- Header -->
	<div class="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="flex items-center justify-between h-16">
				<!-- Back Button -->
				<button
					on:click={goBack}
					class="flex items-center text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors duration-200"
				>
					<ArrowLeft className="w-5 h-5 mr-2" />
					返回工单列表
				</button>

				<!-- Title -->
				<div class="flex items-center">
					<ChartBar className="w-6 h-6 text-blue-600 dark:text-blue-400 mr-3" />
					<h1 class="text-xl font-semibold text-gray-900 dark:text-white">数据统计</h1>
				</div>

				<!-- Empty div for spacing -->
				<div></div>
			</div>
		</div>
	</div>

	<!-- Main Content -->
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{#if loading}
			<!-- Loading State -->
			<div class="flex items-center justify-center h-64">
				<div class="text-center">
					<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
					<p class="text-gray-600 dark:text-gray-400">加载统计数据中...</p>
				</div>
			</div>
		{:else if stats}
			<!-- Statistics Content -->
			<div class="space-y-6">
				<!-- Welcome Card -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
					<div class="flex items-center">
						<div class="flex-shrink-0">
							<div class="w-12 h-12 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
								<ChartBar className="w-6 h-6 text-blue-600 dark:text-blue-400" />
							</div>
						</div>
						<div class="ml-4">
							<h2 class="text-lg font-medium text-gray-900 dark:text-white">工单数据统计</h2>
							<p class="text-sm text-gray-600 dark:text-gray-400">
								查看工单处理效率、完成情况、用户活跃度等关键指标
							</p>
						</div>
					</div>
				</div>

				<!-- Statistics Panel -->
				<div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
					{#if stats}
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
							<!-- Total Tickets -->
							<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
											<ChartBar className="w-4 h-4 text-blue-600 dark:text-blue-400" />
										</div>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-blue-900 dark:text-blue-300">总工单数</p>
										<p class="text-2xl font-bold text-blue-600 dark:text-blue-400">{stats.total || 0}</p>
									</div>
								</div>
							</div>

							<!-- Open Tickets -->
							<div class="bg-yellow-50 dark:bg-yellow-900/20 rounded-lg p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-8 h-8 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center">
											<svg class="w-4 h-4 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
											</svg>
										</div>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-yellow-900 dark:text-yellow-300">待处理</p>
										<p class="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{stats.open || 0}</p>
									</div>
								</div>
							</div>

							<!-- In Progress -->
							<div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
											<svg class="w-4 h-4 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
											</svg>
										</div>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-purple-900 dark:text-purple-300">处理中</p>
										<p class="text-2xl font-bold text-purple-600 dark:text-purple-400">{stats.in_progress || 0}</p>
									</div>
								</div>
							</div>

							<!-- Resolved -->
							<div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
											<svg class="w-4 h-4 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
											</svg>
										</div>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-green-900 dark:text-green-300">已解决</p>
										<p class="text-2xl font-bold text-green-600 dark:text-green-400">{stats.resolved || 0}</p>
									</div>
								</div>
							</div>

							<!-- Closed -->
							<div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-8 h-8 bg-gray-100 dark:bg-gray-600 rounded-lg flex items-center justify-center">
											<svg class="w-4 h-4 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
											</svg>
										</div>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-gray-900 dark:text-gray-300">已关闭</p>
										<p class="text-2xl font-bold text-gray-600 dark:text-gray-400">{stats.closed || 0}</p>
									</div>
								</div>
							</div>

							<!-- AI Generated Stats -->
							{#if stats.ai_generated_total !== undefined}
								<div class="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-6">
									<div class="flex items-center">
										<div class="flex-shrink-0">
											<div class="w-8 h-8 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center">
												<svg class="w-4 h-4 text-indigo-600 dark:text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
												</svg>
											</div>
										</div>
										<div class="ml-3">
											<p class="text-sm font-medium text-indigo-900 dark:text-indigo-300">AI生成工单</p>
											<p class="text-2xl font-bold text-indigo-600 dark:text-indigo-400">{stats.ai_generated_total || 0}</p>
										</div>
									</div>
								</div>
							{/if}
						</div>

						<!-- Progress Bar -->
						<div class="mt-8">
							<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">工单状态分布</h3>
							<div class="space-y-3">
								<div>
									<div class="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
										<span>待处理</span>
										<span>{stats.open || 0}</span>
									</div>
									<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
										<div class="bg-yellow-500 h-2 rounded-full" style="width: {stats.total > 0 ? (stats.open / stats.total * 100) : 0}%"></div>
									</div>
								</div>
								<div>
									<div class="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
										<span>处理中</span>
										<span>{stats.in_progress || 0}</span>
									</div>
									<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
										<div class="bg-purple-500 h-2 rounded-full" style="width: {stats.total > 0 ? (stats.in_progress / stats.total * 100) : 0}%"></div>
									</div>
								</div>
								<div>
									<div class="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
										<span>已解决</span>
										<span>{stats.resolved || 0}</span>
									</div>
									<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
										<div class="bg-green-500 h-2 rounded-full" style="width: {stats.total > 0 ? (stats.resolved / stats.total * 100) : 0}%"></div>
									</div>
								</div>
								<div>
									<div class="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
										<span>已关闭</span>
										<span>{stats.closed || 0}</span>
									</div>
									<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
										<div class="bg-gray-500 h-2 rounded-full" style="width: {stats.total > 0 ? (stats.closed / stats.total * 100) : 0}%"></div>
									</div>
								</div>
							</div>
						</div>
					{:else}
						<div class="text-center py-8">
							<p class="text-gray-500 dark:text-gray-400">暂无统计数据</p>
						</div>
					{/if}
				</div>

				<!-- Additional Info -->
				<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6">
					<div class="flex items-start">
						<div class="flex-shrink-0">
							<div class="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
								<svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
								</svg>
							</div>
						</div>
						<div class="ml-3">
							<h3 class="text-sm font-medium text-blue-900 dark:text-blue-300">统计说明</h3>
							<div class="mt-2 text-sm text-blue-800 dark:text-blue-200">
								<ul class="list-disc list-inside space-y-1">
									<li>数据统计基于最近7天和30天的工单数据</li>
									<li>完成时长统计包含从创建到完成的所有工单</li>
									<li>排行榜显示处理工单最多的用户和部门</li>
									<li>趋势图帮助了解工单处理的时间分布</li>
								</ul>
							</div>
						</div>
					</div>
				</div>
			</div>
		{:else}
			<!-- Error State -->
			<div class="flex items-center justify-center h-64">
				<div class="text-center">
					<div class="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center mx-auto mb-4">
						<svg class="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
						</svg>
					</div>
					<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">加载失败</h3>
					<p class="text-gray-600 dark:text-gray-400 mb-4">无法加载统计数据，请稍后重试</p>
					<button
						on:click={loadStats}
						class="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors duration-200 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
					>
						重新加载
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>
