<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	export let files = [];
	export let selectedFileId = null;
	export let batchMode = false; // 从外部控制批量模式

	// 批量选择状态
	let selectedFiles = new Set();
	let showBatchActions = false;

	// Group files by category
	$: categorizedFiles = files.reduce((acc, file) => {
		const category = file.meta?.category || '未分类';
		if (!acc[category]) {
			acc[category] = [];
		}
		acc[category].push(file);
		return acc;
	}, {});

	// 显示批量操作按钮
	$: showBatchActions = batchMode && selectedFiles.size > 0;

	// Get category colors - 更柔和的颜色
	const getCategoryColor = (category) => {
		const colors = [
			{
				header: 'bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-750',
				border: 'border-gray-200 dark:border-gray-700',
				dot: 'bg-gray-500',
				text: 'text-gray-900 dark:text-gray-100'
			},
			{
				header: 'bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-750',
				border: 'border-slate-200 dark:border-slate-700',
				dot: 'bg-slate-500',
				text: 'text-slate-900 dark:text-slate-100'
			},
			{
				header: 'bg-gradient-to-r from-zinc-50 to-zinc-100 dark:from-zinc-800 dark:to-zinc-750',
				border: 'border-zinc-200 dark:border-zinc-700',
				dot: 'bg-zinc-500',
				text: 'text-zinc-900 dark:text-zinc-100'
			},
			{
				header: 'bg-gradient-to-r from-neutral-50 to-neutral-100 dark:from-neutral-800 dark:to-neutral-750',
				border: 'border-neutral-200 dark:border-neutral-700',
				dot: 'bg-neutral-500',
				text: 'text-neutral-900 dark:text-neutral-100'
			}
		];
		
		const categoryNames = Object.keys(categorizedFiles);
		const index = categoryNames.indexOf(category);
		return colors[index % colors.length];
	};

	// 批量操作处理函数
	const toggleBatchMode = () => {
		dispatch('toggleBatchMode');
		if (!batchMode) {
			selectedFiles.clear();
		}
	};

	const toggleFileSelection = (fileId) => {
		if (selectedFiles.has(fileId)) {
			selectedFiles.delete(fileId);
		} else {
			selectedFiles.add(fileId);
		}
		selectedFiles = selectedFiles; // 触发响应式更新
	};

	const selectAllFiles = () => {
		selectedFiles.clear();
		files.forEach(file => selectedFiles.add(file.id));
		selectedFiles = selectedFiles; // 触发响应式更新
	};

	const clearSelection = () => {
		selectedFiles.clear();
		selectedFiles = selectedFiles; // 触发响应式更新
	};

	const handleBatchOwnerAssignment = () => {
		dispatch('batchOwnerAssignment', { fileIds: Array.from(selectedFiles) });
	};

	const handleBatchCategoryAssignment = () => {
		dispatch('batchCategoryAssignment', { fileIds: Array.from(selectedFiles) });
	};

	const handleFileClick = (fileId) => {
		// 检查文件是否正在处理 OCR
		const file = files.find(f => f.id === fileId);
		if (file && isFileProcessingOCR(file)) {
			// 如果正在处理，不允许点击
			return;
		}
		
		if (batchMode) {
			toggleFileSelection(fileId);
		} else {
			dispatch('click', fileId);
		}
	};

	// 检查文件是否正在处理 OCR
	const isFileProcessingOCR = (file) => {
		if (!file) return false;
		const isProcessing = file?.ocrStatus === 'pending' ||
		       file?.ocrStatus === 'processing' || 
		       file?.ocrStatus === 'exporting' || 
		       file?.ocrStatus === 'extracting' ||
		       file?.status === 'processing' ||
		       file?.status === 'pending';
		// 调试日志（开发时使用）
		if (isProcessing && typeof window !== 'undefined' && window.location.hostname === 'localhost') {
			console.log('文件处理中:', file.meta?.name || file.name, '状态:', file.ocrStatus || file.status);
		}
		return isProcessing;
	};

	// 获取 OCR 处理状态文本
	const getOCRStatusText = (file) => {
		if (file?.ocrStatus === 'pending') {
			return '等待处理...';
		} else if (file?.ocrStatus === 'processing') {
			return `处理中 ${file?.ocrProgress || 0}%`;
		} else if (file?.ocrStatus === 'exporting') {
			return '导出中...';
		} else if (file?.ocrStatus === 'extracting') {
			return '解压中...';
		} else if (file?.ocrStatus === 'completed') {
			return '已完成';
		} else if (file?.ocrStatus === 'failed') {
			return '处理失败';
		}
		return '';
	};

	const handleFileDelete = (fileId) => {
		dispatch('delete', fileId);
	};

	const handleFileUpdate = (fileId) => {
		dispatch('update', fileId);
	};

	const formatFileSize = (bytes) => {
		if (!bytes) return '';
		const sizes = ['B', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(1024));
		return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
	};

	const truncateFileName = (name, maxLength = 35) => {
		if (!name) return '';
		return name.length > maxLength ? name.substring(0, maxLength) + '...' : name;
	};
</script>

		<!-- 批量操作控制栏 -->
	{#if batchMode}
		<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-3 mb-3">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<span class="text-sm font-medium text-blue-900 dark:text-blue-100">
						批量选择模式
					</span>
					<span class="text-xs text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-800 px-2 py-1 rounded-full">
						已选择 {selectedFiles.size} 个文件
					</span>
				</div>
				<div class="flex items-center gap-2">
					<button
						class="px-3 py-1 bg-green-500 hover:bg-green-600 text-white text-xs rounded-md transition-colors"
						on:click={selectAllFiles}
					>
						全选
					</button>
					{#if selectedFiles.size > 0}
						<button
							class="px-3 py-1 bg-purple-500 hover:bg-purple-600 text-white text-xs rounded-md transition-colors"
							on:click={handleBatchCategoryAssignment}
						>
							批量设置分类
						</button>
						<button
							class="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white text-xs rounded-md transition-colors"
							on:click={handleBatchOwnerAssignment}
						>
							批量设置负责人
						</button>
						<button
							class="px-3 py-1 bg-gray-500 hover:bg-gray-600 text-white text-xs rounded-md transition-colors"
							on:click={clearSelection}
						>
							清空选择
						</button>
					{/if}
					<button
						class="px-3 py-1 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 text-xs rounded-md transition-colors"
						on:click={toggleBatchMode}
					>
						退出批量模式
					</button>
				</div>
			</div>
		</div>
	{/if}

	<div class="max-h-full flex flex-col w-full space-y-3">
			{#each Object.entries(categorizedFiles) as [category, categoryFiles]}
				{@const categoryColor = getCategoryColor(category)}
				<div class="bg-white dark:bg-gray-800 rounded-lg border {categoryColor.border} overflow-hidden shadow-sm hover:shadow-md transition-shadow">
					<!-- Category Header -->
					<div class="px-3 py-2 border-b border-gray-100 dark:border-gray-700 {categoryColor.header}">
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-2">
								<div class="w-2 h-2 rounded-full {categoryColor.dot}"></div>
								<span class="text-sm font-medium {categoryColor.text}">{category}</span>
								<span class="text-xs text-gray-500 dark:text-gray-400 bg-white/60 dark:bg-gray-800/60 px-1.5 py-0.5 rounded-full backdrop-blur-sm">
									{categoryFiles.length}
								</span>
							</div>
						</div>
					</div>

					<!-- Files Grid -->
					<div class="p-2">
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-4">
					{#each categoryFiles as file}
						{@const isProcessing = isFileProcessingOCR(file)}
						<div 
							class="group flex items-center gap-3 p-6 rounded border transition-all duration-200 min-h-[120px] {isProcessing ? 
								'cursor-not-allowed opacity-70 bg-gray-50 dark:bg-gray-800/50 border-gray-300 dark:border-gray-600' :
								'cursor-pointer hover:shadow-sm ' + (batchMode ? 
									(selectedFiles.has(file.id) ? 
										'bg-blue-100 dark:bg-blue-900/30 border-blue-400 dark:border-blue-500 shadow-lg ring-2 ring-blue-200 dark:ring-blue-800' : 
										'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
									) : 
									(selectedFileId === file.id ? 
										'bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-600 shadow-md' : 
										'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
									)
								)
							}"
							on:click={(e) => {
								if (isProcessing) {
									e.preventDefault();
									e.stopPropagation();
									return false;
								}
								handleFileClick(file.id);
							}}
							on:keydown={(e) => {
								if (isProcessing) {
									e.preventDefault();
									e.stopPropagation();
									return false;
								}
								if (e.key === 'Enter' || e.key === ' ') {
									e.preventDefault();
									handleFileClick(file.id);
								}
							}}
							role="button"
							tabindex={isProcessing ? -1 : 0}
							aria-disabled={isProcessing}
						>
							<!-- 批量选择复选框 -->
							{#if batchMode}
								<div class="flex-shrink-0 w-5 h-5 flex items-center justify-center">
									<div class="relative">
										<input
											type="checkbox"
											checked={selectedFiles.has(file.id)}
											class="w-4 h-4 text-blue-600 bg-white border-2 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600 cursor-pointer appearance-none checked:bg-blue-600 checked:border-blue-600"
											on:click|stopPropagation={() => toggleFileSelection(file.id)}
										/>
										{#if selectedFiles.has(file.id)}
											<svg class="absolute top-0 left-0 w-4 h-4 text-white pointer-events-none" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
											</svg>
										{/if}
									</div>
								</div>
							{/if}

							<!-- File Icon -->
							<div class="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded bg-gray-100 dark:bg-gray-700 group-hover:bg-gray-200 dark:group-hover:bg-gray-600 transition-colors relative">
								{#if isProcessing}
									<!-- 处理中时显示 loading spinner -->
									<div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
								{:else if file.meta?.name?.toLowerCase().endsWith('.pdf')}
									<div class="w-8 h-8 bg-red-100 dark:bg-red-900/30 rounded text-red-600 dark:text-red-400 text-sm flex items-center justify-center font-bold">P</div>
								{:else if file.meta?.name?.toLowerCase().endsWith('.md') || file.meta?.name?.toLowerCase().endsWith('.markdown')}
									<div class="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded text-blue-600 dark:text-blue-400 text-sm flex items-center justify-center font-bold">M</div>
								{:else if file.meta?.name?.toLowerCase().endsWith('.docx')}
									<div class="w-8 h-8 bg-green-100 dark:bg-green-900/30 rounded text-green-600 dark:text-green-400 text-sm flex items-center justify-center font-bold">D</div>
								{:else}
									<div class="w-8 h-8 bg-gray-100 dark:bg-gray-600 rounded text-gray-600 dark:text-gray-400 text-sm flex items-center justify-center font-bold">F</div>
								{/if}
							</div>

							<!-- File Info -->
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 mb-1">
									<div class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate flex-1">
										{truncateFileName(file.meta?.name || file.name, 40)}
									</div>
									<!-- OCR 处理状态指示器 -->
									{#if isFileProcessingOCR(file)}
										<div class="flex items-center gap-1.5 flex-shrink-0 bg-blue-50 dark:bg-blue-900/30 px-2 py-0.5 rounded-full">
											<div class="w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
											<span class="text-xs text-blue-600 dark:text-blue-400 font-medium whitespace-nowrap">
												{getOCRStatusText(file)}
											</span>
										</div>
									{:else if file?.ocrStatus === 'completed'}
										<div class="flex items-center gap-1 flex-shrink-0">
											<svg class="w-3 h-3 text-green-500" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
											</svg>
											<span class="text-xs text-green-600 dark:text-green-400">已完成</span>
										</div>
									{:else if file?.ocrStatus === 'failed'}
										<div class="flex items-center gap-1 flex-shrink-0">
											<svg class="w-3 h-3 text-red-500" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
											</svg>
											<span class="text-xs text-red-600 dark:text-red-400">失败</span>
										</div>
									{/if}
								</div>
								<div class="flex items-center gap-1 mb-1">
									{#if file.meta?.version}
										<span class="inline-flex items-center px-1 py-0.5 rounded text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
											v{file.meta.version}
										</span>
									{/if}
									{#if file.meta?.owner}
										<span class="inline-flex items-center px-1 py-0.5 rounded text-xs bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
											{file.meta.owner}
										</span>
									{/if}
									{#if file.created_at}
										<span class="text-xs text-gray-500 dark:text-gray-400">
											{#if file.created_at > 1000000000}
												{new Date(file.created_at * 1000).toLocaleDateString('zh-CN')}
											{:else}
												{new Date(file.created_at).toLocaleDateString('zh-CN')}
											{/if}
										</span>
									{/if}
								</div>
								<div class="flex items-center justify-between">
									<div class="flex items-center gap-2">
										<span class="text-xs text-gray-500 dark:text-gray-400">
											{formatFileSize(file.meta?.size || file.size)}
										</span>
										{#if isFileProcessingOCR(file) && file?.ocrMessage}
											<span class="text-xs text-blue-600 dark:text-blue-400 truncate max-w-[150px]" title={file.ocrMessage}>
												{file.ocrMessage}
											</span>
										{/if}
									</div>
									<div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-all {isFileProcessingOCR(file) ? 'opacity-0' : ''}">
										<button
											class="p-0.5 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded text-blue-600 dark:text-blue-400"
											on:click|stopPropagation={() => handleFileUpdate(file.id)}
											title="更新文件"
										>
											<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path>
											</svg>
										</button>
										<button
											class="p-0.5 hover:bg-red-100 dark:hover:bg-red-900/30 rounded text-red-600 dark:text-red-400"
											on:click|stopPropagation={() => handleFileDelete(file.id)}
											title="删除文件"
										>
											<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
											</svg>
										</button>
									</div>
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		</div>
	{/each}

	{#if Object.keys(categorizedFiles).length === 0}
		<div class="text-center text-gray-500 dark:text-gray-400 py-16">
			<div class="text-xl mb-2">📁</div>
			<div class="text-lg mb-2">暂无文件</div>
			<div class="text-sm">上传文件或添加内容到知识库</div>
		</div>
	{/if}
</div>
