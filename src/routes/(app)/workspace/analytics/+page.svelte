<script lang="ts">
	import { onMount } from 'svelte';
	import { user } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { getAnalyticsSummary, getUserActivityStats, getDailyStats, type AnalyticsSummary, type UserActivityStats, type DailyStats } from '$lib/apis/analytics';
	import { getChatListByUserIdWithFeedback } from '$lib/apis/chats';
	import { getTicketStats } from '$lib/apis/tickets';
	import ChatsModalWithFeedback from '$lib/components/layout/ChatsModalWithFeedback.svelte';
	import { getContext } from 'svelte';
	import ChartBar from '$lib/components/icons/ChartBar.svelte';
	import Users from '$lib/components/icons/Users.svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import Heart from '$lib/components/icons/Heart.svelte';
	import ExclamationTriangle from '$lib/components/icons/ExclamationTriangle.svelte';
	import ArrowUpCircle from '$lib/components/icons/ArrowUpCircle.svelte';
	import Calendar from '$lib/components/icons/Calendar.svelte';
	import ClockRotateRight from '$lib/components/icons/ClockRotateRight.svelte';
	import QueueList from '$lib/components/icons/QueueList.svelte';
	import DailyTrendsChart from '$lib/components/charts/DailyTrendsChart.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let summary: AnalyticsSummary | null = null;
	let userStats: UserActivityStats[] = [];
	let dailyStats: DailyStats[] = [];
	let ticketStats: any = null;
	let selectedDays = 30;
	let selectedTab = 'overview';
	let selectedUser: any = null;
	let showUserChatsModal = false;
	let chatList: any = null;
	let chatListLoading = false;
	let allChatsLoaded = false;
	let page = 1;
	let query = '';
	let orderBy = 'updated_at';
	let direction = 'desc';

	// 图表数据
	let chartData: any = null;

	async function loadAnalytics() {
		loading = true;
		try {
			// 检查用户权限（管理员自动拥有所有权限）
			if (!$user?.permissions?.workspace?.analytics && $user?.role !== 'admin') {
				toast.error('您没有权限访问运营分析数据。请联系管理员申请权限。');
				return;
			}

			// 并行加载所有数据
			const [summaryData, userStatsData, dailyStatsData, ticketStatsData] = await Promise.all([
				getAnalyticsSummary(selectedDays),
				getUserActivityStats(undefined, selectedDays, 20),
				getDailyStats(selectedDays),
				getTicketStats()
			]);

			summary = summaryData;
			userStats = userStatsData;
			dailyStats = dailyStatsData;
			ticketStats = ticketStatsData;

			// 准备图表数据
			prepareChartData();

		} catch (error) {
			console.error('Error loading analytics:', error);
			const errorMessage = error instanceof Error ? error.message : String(error);

			if (errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
				toast.error('您没有权限访问运营分析数据。请联系管理员申请权限。');
			} else {
				toast.error('加载运营数据失败');
			}
		} finally {
			loading = false;
		}
	}

	function prepareChartData() {
		if (!dailyStats.length) return;

		// 准备每日活跃用户图表数据
		chartData = {
			labels: dailyStats.slice(0, 14).reverse().map(d => d.date),
			datasets: [
				{
					label: '日活用户',
					data: dailyStats.slice(0, 14).reverse().map(d => d.daily_active_users),
					borderColor: 'rgb(59, 130, 246)',
					backgroundColor: 'rgba(59, 130, 246, 0.1)',
					tension: 0.4
				},
				{
					label: '对话数',
					data: dailyStats.slice(0, 14).reverse().map(d => d.total_messages),
					borderColor: 'rgb(16, 185, 129)',
					backgroundColor: 'rgba(16, 185, 129, 0.1)',
					tension: 0.4
				}
			]
		};
	}

	function formatNumber(num: number): string {
		if (num >= 1000000) {
			return (num / 1000000).toFixed(1) + 'M';
		} else if (num >= 1000) {
			return (num / 1000).toFixed(1) + 'K';
		}
		return num.toString();
	}

	function formatPercentage(ratio: number): string {
		return (ratio * 100).toFixed(1) + '%';
	}

	async function viewUserChats(userId: string, userName: string) {
		try {
			console.log('点击用户:', userName, 'ID:', userId); // 调试信息
			
			// 设置选中的用户
			selectedUser = { id: userId, name: userName };
			
			// 重置状态
			page = 1;
			query = '';
			orderBy = 'updated_at';
			direction = 'desc';
			chatList = [];
			allChatsLoaded = false;
			chatListLoading = false;
			
			// 显示聊天列表模态框
			showUserChatsModal = true;
			
		} catch (error) {
			console.error('Error loading user chats:', error);
			toast.error('无法加载用户聊天记录');
		}
	}

	function closeUserChatsModal() {
		showUserChatsModal = false;
		selectedUser = null;
		chatList = [];
		page = 1;
		query = '';
	}

	async function loadChatList() {
		if (!selectedUser) return;
		
		chatListLoading = true;
		try {
			const filter = {
				...(query ? { query } : {}),
				...(orderBy ? { order_by: orderBy } : {}),
				...(direction ? { direction } : {})
			};
			
			const newChats = await getChatListByUserIdWithFeedback(localStorage.token, selectedUser.id, page, filter);
			
			console.log('API返回的聊天数据:', newChats); // 调试信息
			
			if (page === 1) {
				chatList = newChats || [];
			} else {
				chatList = [...(chatList || []), ...(newChats || [])];
			}
			
			allChatsLoaded = (newChats || []).length === 0;
		} catch (error) {
			console.error('Error loading chat list:', error);
			toast.error('加载聊天列表失败');
		} finally {
			chatListLoading = false;
		}
	}

	async function loadMoreChats() {
		page += 1;
		await loadChatList();
	}

	async function updateChatList() {
		page = 1;
		await loadChatList();
	}

	// 响应式语句
	$: if (showUserChatsModal && selectedUser) {
		loadChatList();
	}

	$: if (query !== undefined || orderBy !== undefined || direction !== undefined) {
		if (showUserChatsModal && selectedUser) {
			updateChatList();
		}
	}

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
	}

	function handleDaysChange() {
		loadAnalytics();
	}

	onMount(() => {
		loadAnalytics();
	});
</script>

<svelte:head>
	<title>运营分析 • Open WebUI</title>
</svelte:head>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="flex flex-col border-b border-gray-200 dark:border-gray-700">
		<!-- 主标题栏 -->
		<div class="flex items-center justify-between p-6">
			<div class="flex items-center gap-3">
				<ChartBar className="w-6 h-6 text-blue-600" />
				<h1 class="text-2xl font-bold text-gray-900 dark:text-white">运营分析</h1>
			</div>

			<div class="flex items-center gap-4">
				<!-- 刷新按钮 -->
				<button
					on:click={loadAnalytics}
					disabled={loading}
					class="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-md transition-colors"
				>
					<ClockRotateRight className="w-4 h-4" />
					{loading ? '刷新中...' : '刷新数据'}
				</button>

				<!-- 时间范围选择 -->
				<div class="flex items-center gap-2">
					<Calendar className="w-4 h-4 text-gray-500" />
					<select
						bind:value={selectedDays}
						on:change={handleDaysChange}
						class="px-3 py-1.5 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-sm min-w-[120px] focus:outline-none focus:ring-2 focus:ring-blue-500"
					>
						<option value={7}>最近7天</option>
						<option value={30}>最近30天</option>
						<option value={90}>最近90天</option>
					</select>
				</div>
			</div>
		</div>

		<!-- 导航栏 -->
		<div class="flex items-center px-6 pb-4">
			<nav class="flex space-x-8">
				<button
					on:click={() => selectedTab = 'overview'}
					class="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors {selectedTab === 'overview'
						? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
						: 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'}"
				>
					<ChartBar className="w-4 h-4" />
					概览
				</button>
				<button
					on:click={() => selectedTab = 'users'}
					class="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors {selectedTab === 'users'
						? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
						: 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'}"
				>
					<Users className="w-4 h-4" />
					用户分析
				</button>
				<button
					on:click={() => selectedTab = 'tickets'}
					class="flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-md transition-colors {selectedTab === 'tickets'
						? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
						: 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-200'}"
				>
					<QueueList className="w-4 h-4" />
					工单分析
				</button>
			</nav>
		</div>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto p-6">
		{#if loading}
			<div class="flex items-center justify-center h-64">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
			</div>
		{:else if summary}
			{#if selectedTab === 'overview'}
				<!-- 概览页面 -->
				<div class="space-y-6">
					<!-- 概览卡片 -->
					<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
						<!-- 总用户数 -->
						<div class="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
							<div class="flex items-center justify-between">
								<div>
									<p class="text-sm font-medium text-gray-600 dark:text-gray-400">总用户数</p>
									<p class="text-xl font-bold text-gray-900 dark:text-white">{formatNumber(summary.total_users)}</p>
								</div>
								<Users className="w-6 h-6 text-blue-600" />
							</div>
						</div>

						<!-- 今日活跃用户 -->
						<div class="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
							<div class="flex items-center justify-between">
								<div>
									<p class="text-sm font-medium text-gray-600 dark:text-gray-400">今日活跃</p>
									<p class="text-xl font-bold text-gray-900 dark:text-white">{formatNumber(summary.active_users_today)}</p>
								</div>
								<ClockRotateRight className="w-6 h-6 text-green-600" />
							</div>
						</div>

						<!-- 总对话数 -->
						<div class="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
							<div class="flex items-center justify-between">
								<div>
									<p class="text-sm font-medium text-gray-600 dark:text-gray-400">总对话数</p>
									<p class="text-xl font-bold text-gray-900 dark:text-white">{formatNumber(summary.total_messages)}</p>
								</div>
								<ChatBubble className="w-6 h-6 text-purple-600" />
							</div>
						</div>

						<!-- 总点赞数 -->
						<div class="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
							<div class="flex items-center justify-between">
								<div>
									<p class="text-sm font-medium text-gray-600 dark:text-gray-400">总点赞数</p>
									<p class="text-xl font-bold text-green-600 dark:text-green-400">{formatNumber(summary.total_thumbs_up)}</p>
								</div>
								<ArrowUpCircle className="w-6 h-6 text-green-600" />
							</div>
						</div>

						<!-- 总点踩数 -->
						<div class="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
							<div class="flex items-center justify-between">
								<div>
									<p class="text-sm font-medium text-gray-600 dark:text-gray-400">总点踩数</p>
									<p class="text-xl font-bold text-red-600 dark:text-red-400">{formatNumber(summary.total_thumbs_down)}</p>
								</div>
								<ExclamationTriangle className="w-6 h-6 text-red-600" />
							</div>
						</div>
					</div>

					<!-- 每日趋势曲线图 -->
					<DailyTrendsChart 
						data={dailyStats.slice(0, selectedDays).reverse()} 
						title="每日趋势 (最近{selectedDays}天)"
						showActiveUsers={true}
						showMessages={true}
						showThumbsUp={true}
						type="primary"
					/>
					
					<!-- 详细统计 -->
					<div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
						<!-- 本周活跃用户 -->
						<div class="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">活跃用户统计</h3>
							<div class="space-y-3">
								<div class="flex justify-between items-center">
									<span class="text-sm text-gray-600 dark:text-gray-400">本周活跃</span>
									<span class="font-semibold text-gray-900 dark:text-white">{formatNumber(summary.active_users_this_week)}</span>
								</div>
								<div class="flex justify-between items-center">
									<span class="text-sm text-gray-600 dark:text-gray-400">本月活跃</span>
									<span class="font-semibold text-gray-900 dark:text-white">{formatNumber(summary.active_users_this_month)}</span>
								</div>
							</div>
						</div>

						<!-- 点赞点踩统计 -->
						<div class="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">用户反馈</h3>
							<div class="space-y-3">
								<div class="flex justify-between items-center">
                                    <div class="flex items-center gap-2">
                                         <Heart className="w-4 h-4 text-green-600" />
                                        <span class="text-sm text-gray-600 dark:text-gray-400">点赞</span>
                                    </div>
                                    <span class="font-semibold text-gray-900 dark:text-white">{formatNumber(summary.total_thumbs_up)}</span>
								</div>
								<div class="flex justify-between items-center">
                                    <div class="flex items-center gap-2">
                                         <ExclamationTriangle className="w-4 h-4 text-red-600" />
                                        <span class="text-sm text-gray-600 dark:text-gray-400">点踩</span>
                                    </div>
                                    <span class="font-semibold text-gray-900 dark:text-white">{formatNumber(summary.total_thumbs_down)}</span>
								</div>
							</div>
						</div>

						<!-- 功能使用统计 -->
						<div class="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">功能使用</h3>
							<div class="space-y-3">
								<div class="flex justify-between items-center">
									<span class="text-sm text-gray-600 dark:text-gray-400">模型使用</span>
									<span class="font-semibold text-gray-900 dark:text-white">{formatNumber(summary.total_messages)}</span>
								</div>
								<div class="flex justify-between items-center">
									<span class="text-sm text-gray-600 dark:text-gray-400">知识库访问</span>
									<span class="font-semibold text-gray-900 dark:text-white">-</span>
								</div>
								<div class="flex justify-between items-center">
									<span class="text-sm text-gray-600 dark:text-gray-400">工具使用</span>
									<span class="font-semibold text-gray-900 dark:text-white">-</span>
								</div>
							</div>
						</div>
					</div>

					<!-- 用户排行榜 -->
					<div class="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
						<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-6">活跃用户排行榜</h3>
						<div class="overflow-x-auto">
							<table class="w-full">
								<thead>
									<tr class="border-b border-gray-200 dark:border-gray-700">
										<th class="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">排名</th>
										<th class="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">用户</th>
										<th class="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">对话数</th>
										<th class="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">点赞数</th>
										<th class="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">点踩数</th>
										<th class="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">点赞比例</th>
										<th class="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">最后活跃</th>
									</tr>
								</thead>
								<tbody>
									{#each userStats as row, index}
										<tr class="border-b border-gray-100 dark:border-gray-700">
											<td class="py-3 px-4">
												<span class="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 text-sm font-medium">
													{index + 1}
												</span>
											</td>
											<td class="py-3 px-4">
												<button class="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md p-2 -m-2 transition-colors w-full text-left" 
														on:click={() => viewUserChats(row.user_id, row.user_name)}
														aria-label={`查看 ${row.user_name} 的聊天记录`}>
													<p class="font-medium text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400">{row.user_name}</p>
													<p class="text-sm text-gray-500 dark:text-gray-400">{row.user_email}</p>
												</button>
											</td>
											<td class="py-3 px-4 font-medium text-gray-900 dark:text-white">{formatNumber(row.total_messages)}</td>
											<td class="py-3 px-4">
												<div class="flex items-center gap-1">
													<ArrowUpCircle className="w-4 h-4 text-green-600" />
													<span class="font-medium text-green-600 dark:text-green-400">{formatNumber(row.total_thumbs_up)}</span>
												</div>
											</td>
											<td class="py-3 px-4">
												<div class="flex items-center gap-1">
													<ExclamationTriangle className="w-4 h-4 text-red-600" />
													<span class="font-medium text-red-600 dark:text-red-400">{formatNumber(row.total_thumbs_down)}</span>
												</div>
											</td>
											<td class="py-3 px-4">
												<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {row.thumbs_up_ratio >= 0.7 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' : row.thumbs_up_ratio >= 0.5 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'}">
													{formatPercentage(row.thumbs_up_ratio)}
												</span>
											</td>
											<td class="py-3 px-4 text-sm text-gray-500 dark:text-gray-400">
												{row.last_active ? new Date(row.last_active).toLocaleDateString('zh-CN') : '-'}
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					</div>

				</div>
			{:else if selectedTab === 'users'}
				<!-- 用户分析页面 -->
				<div class="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-6">用户详细分析</h3>
					<div class="overflow-x-auto">
						<table class="w-full">
							<thead>
								<tr class="border-b border-gray-200 dark:border-gray-700">
									<th class="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">用户</th>
									<th class="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">对话数</th>
									<th class="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">点赞数</th>
									<th class="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">点踩数</th>
									<th class="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">点赞比例</th>
									<th class="text-left py-3 px-4 font-medium text-gray-600 dark:text-gray-400">最后活跃</th>
								</tr>
							</thead>
							<tbody>
								{#each userStats as row, index}
									<tr class="border-b border-gray-100 dark:border-gray-700">
										<td class="py-3 px-4">
											<div>
												<p class="font-medium text-gray-900 dark:text-white">{row.user_name}</p>
												<p class="text-sm text-gray-500 dark:text-gray-400">{row.user_email}</p>
											</div>
										</td>
										<td class="py-3 px-4 font-medium text-gray-900 dark:text-white">{formatNumber(row.total_messages)}</td>
										<td class="py-3 px-4 font-medium text-green-600">{formatNumber(row.total_thumbs_up)}</td>
										<td class="py-3 px-4 font-medium text-red-600">{formatNumber(row.total_thumbs_down)}</td>
										<td class="py-3 px-4">
											<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium {row.thumbs_up_ratio >= 0.7 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300' : row.thumbs_up_ratio >= 0.5 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300' : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'}">
												{formatPercentage(row.thumbs_up_ratio)}
											</span>
										</td>
										<td class="py-3 px-4 text-sm text-gray-500 dark:text-gray-400">
											{row.last_active ? new Date(row.last_active).toLocaleDateString('zh-CN') : '-'}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			{:else if selectedTab === 'tickets'}
				<!-- 工单分析页面 -->
				<div class="space-y-6">
					{#if ticketStats}
						<!-- 工单统计卡片 -->
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
							<!-- 总工单数 -->
							<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6">
								<div class="flex items-center">
									<div class="flex-shrink-0">
										<div class="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
											<ChartBar className="w-4 h-4 text-blue-600 dark:text-blue-400" />
										</div>
									</div>
									<div class="ml-3">
										<p class="text-sm font-medium text-blue-900 dark:text-blue-300">总工单数</p>
										<p class="text-2xl font-bold text-blue-600 dark:text-blue-400">{ticketStats.total || 0}</p>
									</div>
								</div>
							</div>

							<!-- 待处理 -->
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
										<p class="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{ticketStats.open || 0}</p>
									</div>
								</div>
							</div>

							<!-- 处理中 -->
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
										<p class="text-2xl font-bold text-purple-600 dark:text-purple-400">{ticketStats.in_progress || 0}</p>
									</div>
								</div>
							</div>

							<!-- 已解决 -->
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
										<p class="text-2xl font-bold text-green-600 dark:text-green-400">{ticketStats.resolved || 0}</p>
									</div>
								</div>
							</div>

							<!-- 已关闭 -->
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
										<p class="text-2xl font-bold text-gray-600 dark:text-gray-400">{ticketStats.closed || 0}</p>
									</div>
								</div>
							</div>

							<!-- AI生成工单 -->
							{#if ticketStats.ai_generated_total !== undefined}
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
											<p class="text-2xl font-bold text-indigo-600 dark:text-indigo-400">{ticketStats.ai_generated_total || 0}</p>
										</div>
									</div>
								</div>
							{/if}
						</div>

						<!-- 工单状态分布进度条 -->
						<div class="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
							<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">工单状态分布</h3>
							<div class="space-y-3">
								<div>
									<div class="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
										<span>待处理</span>
										<span>{ticketStats.open || 0}</span>
									</div>
									<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
										<div class="bg-yellow-500 h-2 rounded-full" style="width: {ticketStats.total > 0 ? (ticketStats.open / ticketStats.total * 100) : 0}%"></div>
									</div>
								</div>
								<div>
									<div class="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
										<span>处理中</span>
										<span>{ticketStats.in_progress || 0}</span>
									</div>
									<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
										<div class="bg-purple-500 h-2 rounded-full" style="width: {ticketStats.total > 0 ? (ticketStats.in_progress / ticketStats.total * 100) : 0}%"></div>
									</div>
								</div>
								<div>
									<div class="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
										<span>已解决</span>
										<span>{ticketStats.resolved || 0}</span>
									</div>
									<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
										<div class="bg-green-500 h-2 rounded-full" style="width: {ticketStats.total > 0 ? (ticketStats.resolved / ticketStats.total * 100) : 0}%"></div>
									</div>
								</div>
								<div>
									<div class="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-1">
										<span>已关闭</span>
										<span>{ticketStats.closed || 0}</span>
									</div>
									<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
										<div class="bg-gray-500 h-2 rounded-full" style="width: {ticketStats.total > 0 ? (ticketStats.closed / ticketStats.total * 100) : 0}%"></div>
									</div>
								</div>
							</div>
						</div>

						<!-- 部门完成工单统计 -->
						{#if ticketStats.department_stats && Object.keys(ticketStats.department_stats).length > 0}
							<div class="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
								<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">部门完成工单统计</h3>
								<div class="space-y-4">
									{#each Object.entries(ticketStats.department_stats) as [department, count]}
										<div class="border border-gray-200 dark:border-gray-600 rounded-lg overflow-hidden">
											<!-- 部门标题行 -->
											<div class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700">
												<div class="flex items-center space-x-3">
													<div class="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
														<Users className="w-4 h-4 text-blue-600 dark:text-blue-400" />
													</div>
													<span class="font-semibold text-gray-900 dark:text-white">{department}</span>
												</div>
												<div class="flex items-center space-x-2">
													<span class="text-2xl font-bold text-blue-600 dark:text-blue-400">{count}</span>
													<span class="text-sm text-gray-500 dark:text-gray-400">个工单</span>
												</div>
											</div>
											
											<!-- 部门成员统计 -->
											{#if ticketStats.department_member_stats && ticketStats.department_member_stats[department]}
												<div class="p-4 bg-white dark:bg-gray-800">
													<h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">部门成员完成情况</h4>
													<div class="space-y-2">
														{#each Object.entries(ticketStats.department_member_stats[department]) as [memberId, memberCount]}
															<div class="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-700 rounded-md">
																<div class="flex items-center space-x-2">
																	<div class="w-6 h-6 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
																		<span class="text-xs font-medium text-green-600 dark:text-green-400">M</span>
																	</div>
																	<span class="text-sm text-gray-700 dark:text-gray-300">{memberId}</span>
																</div>
																<div class="flex items-center space-x-1">
																	<span class="text-lg font-semibold text-green-600 dark:text-green-400">{memberCount}</span>
																	<span class="text-xs text-gray-500 dark:text-gray-400">个</span>
																</div>
															</div>
														{/each}
													</div>
												</div>
											{/if}
										</div>
									{/each}
								</div>
							</div>
						{/if}

						<!-- 统计说明 -->
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
					{:else}
						<div class="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
							<div class="text-center py-12">
								<QueueList className="w-16 h-16 text-gray-400 mx-auto mb-4" />
								<p class="text-gray-500 dark:text-gray-400">暂无工单统计数据</p>
								<p class="text-sm text-gray-400 dark:text-gray-500 mt-2">请稍后重试或联系管理员</p>
							</div>
						</div>
					{/if}
				</div>
			{/if}
		{:else}
			<div class="flex items-center justify-center h-64">
				<p class="text-gray-500 dark:text-gray-400">暂无数据</p>
			</div>
		{/if}
	</div>
</div>

<!-- 用户聊天列表模态框 -->
<ChatsModalWithFeedback
	bind:show={showUserChatsModal}
	bind:query
	bind:orderBy
	bind:direction
	title={selectedUser ? `${selectedUser.name} 的聊天记录` : '聊天记录'}
	emptyPlaceholder="该用户暂无聊天记录"
	shareUrl={true}
	bind:chatList
	{allChatsLoaded}
	{chatListLoading}
	onUpdate={updateChatList}
	loadHandler={loadMoreChats}
/>
