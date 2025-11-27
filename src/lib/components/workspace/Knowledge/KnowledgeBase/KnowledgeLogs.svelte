<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';

	const dispatch = createEventDispatcher();

	export let knowledgeId: string;
	export let logs: any[] = [];
	export let loading = false;

	let searchQuery = '';
	let filterType = 'all';
	let filteredLogs = [];

	// 过滤日志
	$: {
		filteredLogs = logs.filter(log => {
			const matchesSearch = !searchQuery || 
				log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
				log.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
				log.user_name?.toLowerCase().includes(searchQuery.toLowerCase());
			
			const matchesType = filterType === 'all' || log.action_type === filterType;
			
			return matchesSearch && matchesType;
		});
	}

	// 格式化文件大小
	const formatFileSize = (bytes: number) => {
		if (!bytes) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
	};

	// 格式化时间
	const formatTime = (timestamp: number) => {
		try {
			const now = new Date();
			const logTime = new Date(timestamp * 1000);
			const diffInSeconds = Math.floor((now.getTime() - logTime.getTime()) / 1000);
			
			if (diffInSeconds < 60) {
				return '刚刚';
			} else if (diffInSeconds < 3600) {
				const minutes = Math.floor(diffInSeconds / 60);
				return `${minutes}分钟前`;
			} else if (diffInSeconds < 86400) {
				const hours = Math.floor(diffInSeconds / 3600);
				return `${hours}小时前`;
			} else if (diffInSeconds < 2592000) {
				const days = Math.floor(diffInSeconds / 86400);
				return `${days}天前`;
			} else {
				return logTime.toLocaleDateString('zh-CN');
			}
		} catch (error) {
			return '未知时间';
		}
	};

	// 获取操作图标
	const getActionIcon = (actionType: string) => {
		switch (actionType) {
			case 'file_add':
				return '📄';
			case 'file_update':
				return '🔄';
			case 'file_delete':
				return '🗑️';
			case 'knowledge_create':
				return '📚';
			case 'knowledge_update':
				return '✏️';
			case 'knowledge_delete':
				return '❌';
			default:
				return '📝';
		}
	};

	// 获取操作颜色
	const getActionColor = (actionType: string) => {
		switch (actionType) {
			case 'file_add':
				return 'text-green-600 dark:text-green-400';
			case 'file_update':
				return 'text-blue-600 dark:text-blue-400';
			case 'file_delete':
				return 'text-red-600 dark:text-red-400';
			case 'knowledge_create':
				return 'text-purple-600 dark:text-purple-400';
			case 'knowledge_update':
				return 'text-orange-600 dark:text-orange-400';
			case 'knowledge_delete':
				return 'text-red-600 dark:text-red-400';
			default:
				return 'text-gray-600 dark:text-gray-400';
		}
	};

	// 刷新日志
	const refreshLogs = () => {
		dispatch('refresh');
	};

	// 清空日志
	const clearLogs = () => {
		const confirmText = prompt('⚠️ 警告：此操作将永久删除所有日志记录，无法恢复！\n\n请输入"确定删除"来确认操作：');
		if (confirmText === "确定删除") {
			dispatch('clear', { confirm: confirmText });
		} else if (confirmText !== null) {
			alert('确认文本不正确，操作已取消。');
		}
	};
</script>

<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 h-full flex flex-col">
	<!-- Header -->
	<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
		<div class="flex items-center gap-3">
			<div class="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
				<svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
				</svg>
			</div>
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">操作日志</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">知识库操作历史记录</p>
			</div>
		</div>
		<div class="flex items-center gap-2">
			<button
				class="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
				on:click={refreshLogs}
				disabled={loading}
				title="刷新日志"
			>
				<svg class="w-4 h-4 {loading ? 'animate-spin' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
				</svg>
			</button>
			<button
				class="p-2 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
				on:click={clearLogs}
				title="清空日志"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
				</svg>
			</button>
		</div>
	</div>

	<!-- Filters -->
	<div class="p-4 border-b border-gray-200 dark:border-gray-700">
		<div class="flex flex-col sm:flex-row gap-3">
			<!-- Search -->
			<div class="flex-1">
				<input
					type="text"
					bind:value={searchQuery}
					placeholder="搜索操作日志..."
					class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg
						bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
						focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				/>
			</div>
			
			<!-- Filter -->
			<div class="sm:w-48">
				<select
					bind:value={filterType}
					class="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg
						bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
						focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				>
					<option value="all">所有操作</option>
					<option value="file_add">文件添加</option>
					<option value="file_update">文件更新</option>
					<option value="file_delete">文件删除</option>
					<option value="knowledge_create">知识库创建</option>
					<option value="knowledge_update">知识库更新</option>
					<option value="knowledge_delete">知识库删除</option>
				</select>
			</div>
		</div>
	</div>

	<!-- Logs List -->
	<div class="flex-1 overflow-y-auto min-h-0">
		{#if loading}
			<div class="flex items-center justify-center h-32">
				<div class="flex items-center gap-2 text-gray-500 dark:text-gray-400">
					<svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					<span>加载日志中...</span>
				</div>
			</div>
		{:else if filteredLogs.length === 0}
			<div class="flex flex-col items-center justify-center h-32 text-gray-500 dark:text-gray-400">
				<svg class="w-12 h-12 mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
				</svg>
				<div class="text-sm">暂无操作日志</div>
			</div>
		{:else}
			<div class="p-2 space-y-2">
				{#each filteredLogs as log, index}
					<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors p-3">
						<div class="flex items-center gap-3">
							<!-- Action Icon -->
							<div class="flex-shrink-0 w-8 h-8 bg-blue-50 dark:bg-blue-900/20 rounded-lg flex items-center justify-center">
								<div class="text-blue-600 dark:text-blue-400 text-sm">
									{getActionIcon(log.action_type)}
								</div>
							</div>

							<!-- Log Content -->
							<div class="flex-1 min-w-0">
								<!-- Header -->
								<div class="flex items-center justify-between mb-1">
									<div class="flex items-center gap-2">
										<h4 class="text-sm font-semibold text-gray-900 dark:text-gray-100">
											{log.action}
										</h4>
										<span class="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
											{log.action_type}
										</span>
									</div>
									<div class="flex items-center gap-1">
										<div class="w-1.5 h-1.5 rounded-full {log.status === 'success' ? 'bg-green-500' : log.status === 'error' ? 'bg-red-500' : 'bg-yellow-500'}"></div>
										<span class="text-xs text-gray-500 dark:text-gray-400">
											{log.status === 'success' ? '成功' : log.status === 'error' ? '失败' : '警告'}
										</span>
									</div>
								</div>
								
								<!-- Description -->
								{#if log.description}
									<p class="text-xs text-gray-600 dark:text-gray-400 mb-2 leading-relaxed">
										{log.description}
									</p>
								{/if}

								<!-- Details -->
								<div class="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
									{#if log.user_name}
										<span class="flex items-center gap-1">
											<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
											</svg>
											{log.user_name}
										</span>
									{/if}
									
									<span class="flex items-center gap-1">
										<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
										</svg>
										{formatTime(log.timestamp)}
									</span>

									{#if log.file_name}
										<span class="flex items-center gap-1 truncate" title={log.file_name}>
											<svg class="w-3 h-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
											</svg>
											<span class="truncate">{log.file_name}</span>
										</span>
									{/if}

									{#if log.file_size}
										<span class="flex items-center gap-1">
											<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 4V2a1 1 0 011-1h8a1 1 0 011 1v2m-9 0h10a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2z"></path>
											</svg>
											{formatFileSize(log.file_size)}
										</span>
									{/if}
								</div>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Footer -->
	<div class="p-4 border-t border-gray-200 dark:border-gray-700">
		<div class="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
			<span>共 {filteredLogs.length} 条记录</span>
			<span>显示最近 100 条</span>
		</div>
	</div>
</div>
