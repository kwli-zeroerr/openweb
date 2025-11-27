<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getTickets, deleteTicket, type Ticket, type TicketListResponse } from '$lib/apis/tickets';
	import { getGroups } from '$lib/apis/groups';
	import { user } from '$lib/stores';
	import { filterTicketsByTab, getStatusInfo, getPriorityInfo, getCategoryInfo, formatTicketDate, TICKET_CATEGORY_OPTIONS } from '$lib/constants/tickets';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import Trash from '$lib/components/icons/Trash.svelte';
	import ExclamationTriangle from '$lib/components/icons/ExclamationTriangle.svelte';
	import InformationCircle from '$lib/components/icons/InformationCircle.svelte';
	import CheckCircle from '$lib/components/icons/CheckCircle.svelte';
	import BugAnt from '$lib/components/icons/BugAnt.svelte';
	import LightBulb from '$lib/components/icons/LightBulb.svelte';
	import ChatBubbleLeftRight from '$lib/components/icons/ChatBubbleLeftRight.svelte';
	import WrenchScrewdriver from '$lib/components/icons/WrenchScrewdriver.svelte';
	import Tag from '$lib/components/icons/Tag.svelte';
	import ChartBar from '$lib/components/icons/ChartBar.svelte';
	import CreateTicketModal from '$lib/components/tickets/CreateTicketModal.svelte';
	import TicketCard from '$lib/components/tickets/TicketCard.svelte';

	let tickets: Ticket[] = [];
	let allTickets: Ticket[] = [];
	let total = 0;
	let loading = true;
	let showCreateModal = false;
	let currentPage = 0;
	let pageSize = 20;
	let selectedTab: 'all' | 'todo' | 'unassigned' | 'assigned' | 'archived' | 'pending_verification' = 'todo';
	let selectedCategory: string | null = null;
	let groups: any[] = [];


	function applyTabFilter(source: Ticket[]): Ticket[] {
		let filtered = filterTicketsByTab(source, selectedTab, $user?.id);
		
		// 如果选择了特定分类，进一步过滤
		if (selectedCategory) {
			filtered = filtered.filter(ticket => ticket.category === selectedCategory);
		}
		
		return filtered;
	}

	// 按分类分组工单
	function groupTicketsByCategory(tickets: Ticket[]) {
		const groups: { [key: string]: Ticket[] } = {};
		
		tickets.forEach(ticket => {
			const category = ticket.category || 'other';
			if (!groups[category]) {
				groups[category] = [];
			}
			groups[category].push(ticket);
		});
		
		return groups;
	}

	async function loadGroups() {
		try {
			const token = localStorage.token || '';
			const response = await getGroups(token);
			groups = Array.isArray(response) ? response : (response?.groups || []);
		} catch (error) {
			console.error('Failed to load groups:', error);
			// 如果加载失败，使用空数组
			groups = [];
		}
	}

	async function loadTickets() {
		loading = true;
		try {
			const params: any = {
				skip: currentPage * pageSize,
				limit: pageSize
			};

		// 管理员和有查看全部工单权限的用户可以看到所有工单
		// 普通用户只能看到自己创建的工单和分配给自己的工单
		if ($user?.role !== 'admin') {
			// 检查是否有查看全部工单的权限
			const hasViewAllPermission = $user?.permissions?.workspace?.tickets_view_all ?? false;
			
			console.log('权限检查:', {
				userRole: $user?.role,
				hasViewAllPermission,
				userPermissions: $user?.permissions?.workspace,
				groups: $user?.permissions?.groups
			});
			
			if (!hasViewAllPermission) {
				params.user_id = $user?.id;
			}
		}

			const response: TicketListResponse = await getTickets(params);
			allTickets = response.tickets || [];
			tickets = applyTabFilter(allTickets);
			total = response.total;
		} catch (error) {
			console.error('Error loading tickets:', error);
			toast.error('加载工单失败');
		} finally {
			loading = false;
		}
	}


	async function handleDeleteTicket(ticketId: string) {
		// 检查删除权限
		if ($user?.role !== 'admin') {
			toast.error('权限不足，无法删除工单。请联系管理员申请权限，或在工单下留言说明删除原因。');
			return;
		}
		
		if (!confirm('确定要删除这个工单吗？此操作不可撤销。')) {
			return;
		}

		try {
			await deleteTicket(ticketId);
			toast.success('工单已删除');
			await loadTickets();
		} catch (error) {
			console.error('Error deleting ticket:', error);
			const errorMessage = error instanceof Error ? error.message : String(error);
			
			// 根据错误类型显示不同的提示
			if (errorMessage.includes('403') || errorMessage.includes('Forbidden')) {
				toast.error('权限不足，无法删除工单。请联系管理员申请权限，或在工单下留言说明删除原因。');
			} else if (errorMessage.includes('404') || errorMessage.includes('not found')) {
				toast.error('工单不存在或已被删除');
			} else {
				toast.error('删除工单失败，请稍后重试');
			}
		}
	}

	function handleCreateSuccess() {
		showCreateModal = false;
		loadTickets();
	}

	onMount(async () => {
		// 先加载权限组数据
		await loadGroups();
		
		// Check if user has tickets permission
		const hasTicketsPermission = $user?.role === 'admin' || 
			($user?.permissions?.workspace?.tickets ?? false) ||
			($user?.permissions?.workspace?.tickets_view_all ?? false);
		
		if (!hasTicketsPermission) {
			// 先尝试加载工单，检查用户是否有被分配的工单
			try {
				await loadTickets();
				
				// 如果没有任何工单（既不是创建者也不是被分配者），则拒绝访问
				if (allTickets.length === 0) {
					toast.error('您没有权限访问工单系统。请联系管理员申请权限，或在工单下留言说明访问需求。');
					goto('/');
					return;
				}
			} catch (error) {
				toast.error('您没有权限访问工单系统。请联系管理员申请权限，或在工单下留言说明访问需求。');
				goto('/');
				return;
			}
		} else {
			await loadTickets();
		}
	});
</script>

<svelte:head>
	<title>问题工单 • Open WebUI</title>
</svelte:head>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
		<div>
			<h1 class="text-2xl font-bold text-gray-900 dark:text-white">问题工单</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
				提交问题反馈，我们会尽快处理您的请求
			</p>
		</div>
		<div class="flex items-center space-x-3">
			{#if $user?.role === 'admin'}
				<button
					on:click={() => goto('/workspace/tickets/statistics')}
					class="flex items-center px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
				>
					<ChartBar className="w-4 h-4 mr-2" />
					数据统计
				</button>
			{/if}
			{#if selectedTab !== 'archived' && selectedTab !== 'pending_verification'}
			<button
				on:click={() => showCreateModal = true}
					class="flex items-center px-4 py-2 text-sm font-medium text-white bg-gray-900 border border-transparent rounded-md hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
			>
				<Plus className="w-4 h-4 mr-2" />
				新建工单
			</button>
			{/if}
		</div>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto">
		<!-- Tabs -->
		<div class="px-6 pt-4">
			<div class="flex flex-col space-y-4">
				<!-- 状态标签 -->
				<div class="flex space-x-1">
					<button
						class={"px-3 py-2 text-sm rounded-md transition-colors " + (selectedTab === 'all' ? 'bg-gray-900 text-white' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700')}
						on:click={() => { selectedTab = 'all'; tickets = applyTabFilter(allTickets); }}
					>
						全部
					</button>
					{#if $user?.role === 'admin'}
						<button
							class={"px-3 py-2 text-sm rounded-md transition-colors " + (selectedTab === 'unassigned' ? 'bg-gray-900 text-white' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700')}
							on:click={() => { selectedTab = 'unassigned'; tickets = applyTabFilter(allTickets); }}
						>
							待分配
						</button>
						<button
							class={"px-3 py-2 text-sm rounded-md transition-colors " + (selectedTab === 'assigned' ? 'bg-gray-900 text-white' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700')}
							on:click={() => { selectedTab = 'assigned'; tickets = applyTabFilter(allTickets); }}
						>
							已分配
						</button>
					{/if}
					<button
						class={"px-3 py-2 text-sm rounded-md transition-colors " + (selectedTab === 'todo' ? 'bg-gray-900 text-white' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700')}
						on:click={() => { selectedTab = 'todo'; tickets = applyTabFilter(allTickets); }}
					>
						待办
					</button>
					{#if $user?.role === 'admin'}
						<button
							class={"px-3 py-2 text-sm rounded-md transition-colors " + (selectedTab === 'pending_verification' ? 'bg-gray-900 text-white' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700')}
							on:click={() => { selectedTab = 'pending_verification'; tickets = applyTabFilter(allTickets); }}
						>
							待验收
						</button>
					{/if}
					<button
						class={"px-3 py-2 text-sm rounded-md transition-colors " + (selectedTab === 'archived' ? 'bg-gray-900 text-white' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700')}
						on:click={() => { selectedTab = 'archived'; tickets = applyTabFilter(allTickets); }}
					>
						已归档
					</button>
				</div>
				
				<!-- 问题类型筛选 -->
				<div class="flex items-center space-x-2">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-300">问题类型：</span>
					<div class="flex flex-wrap gap-2">
						<button
							class={"px-3 py-1 text-sm rounded-full border transition-colors " + 
								(selectedCategory === null 
									? 'bg-gray-900 text-white border-gray-900' 
									: 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700')}
							on:click={() => { selectedCategory = null; tickets = applyTabFilter(allTickets); }}
						>
							全部类型
						</button>
						{#each TICKET_CATEGORY_OPTIONS as category}
							<button
								class={"px-3 py-1 text-sm rounded-full border transition-colors flex items-center space-x-1 " + 
									(selectedCategory === category.value 
										? 'bg-gray-900 text-white border-gray-900' 
										: 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700')}
								on:click={() => { selectedCategory = category.value; tickets = applyTabFilter(allTickets); }}
							>
								<svelte:component this={category.icon} className="w-3 h-3" />
								<span>{category.label}</span>
							</button>
						{/each}
					</div>
				</div>
			</div>
		</div>
		{#if loading}
			<div class="flex items-center justify-center h-64">
				<Spinner />
			</div>
		{:else}
			<div class="p-6">
				<!-- Tickets container -->
				<div class="w-full">
					{#if tickets.length === 0}
						<div class="flex flex-col items-center justify-center h-64 text-center">
							<div class="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-4">
								<Tag className="w-8 h-8 text-gray-400" />
							</div>
							<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">暂无工单</h3>
							<p class="text-gray-500 dark:text-gray-400 mb-4">
								{selectedTab === 'archived' ? '暂无已归档的工单' : 
								 selectedTab === 'pending_verification' ? '暂无待验收的工单' : 
								 '您还没有提交任何工单'}
							</p>
							{#if selectedTab !== 'archived' && selectedTab !== 'pending_verification'}
							<button
								on:click={() => showCreateModal = true}
								class="px-4 py-2 text-sm font-medium text-white bg-gray-900 hover:bg-gray-800 rounded-md dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700"
							>
								创建第一个工单
							</button>
							{/if}
						</div>
					{:else}
						{#if selectedCategory}
							<!-- 显示特定分类的工单 -->
							<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
								{#each tickets as ticket}
									<TicketCard ticket={ticket} on:delete={(e) => handleDeleteTicket(e.detail)} />
								{/each}
							</div>
						{:else}
							<!-- 按分类分组显示工单 -->
							{@const ticketGroups = groupTicketsByCategory(tickets)}
							{#each Object.entries(ticketGroups) as [categoryKey, categoryTickets]}
								{@const categoryInfo = getCategoryInfo(categoryKey)}
								<div class="mb-8">
									<!-- 分类标题 -->
									<div class="flex items-center space-x-2 mb-4">
										<svelte:component this={categoryInfo.icon} className="w-5 h-5 {categoryInfo.color}" />
										<h3 class="text-lg font-semibold text-gray-900 dark:text-white">
											{categoryInfo.label}
										</h3>
										<span class="px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 rounded-full">
											{categoryTickets.length} 个工单
										</span>
									</div>
									
									<!-- 该分类的工单卡片 -->
									<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
										{#each categoryTickets as ticket}
											<TicketCard ticket={ticket} on:delete={(e) => handleDeleteTicket(e.detail)} />
										{/each}
									</div>
								</div>
							{/each}
						{/if}
						
						<!-- Pagination -->
						{#if total > pageSize}
							<div class="mt-6 flex items-center justify-between">
								<div class="text-sm text-gray-700 dark:text-gray-300">
									显示第 {currentPage * pageSize + 1} - {Math.min((currentPage + 1) * pageSize, total)} 条，共 {total} 条
								</div>
								<div class="flex items-center space-x-2">
									<button
										on:click={() => currentPage > 0 && (currentPage -= 1)}
										disabled={currentPage === 0}
										class="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
									>
										上一页
									</button>
									<span class="text-sm text-gray-700 dark:text-gray-300">
										{currentPage + 1} / {Math.ceil(total / pageSize)}
									</span>
									<button
										on:click={() => (currentPage += 1)}
										disabled={(currentPage + 1) * pageSize >= total}
										class="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
									>
										下一页
									</button>
								</div>
							</div>
						{/if}
					{/if}
				</div>
			</div>
		{/if}
	</div>
</div>

<!-- Create Ticket Modal -->
<CreateTicketModal bind:show={showCreateModal} on:close={handleCreateSuccess} />
