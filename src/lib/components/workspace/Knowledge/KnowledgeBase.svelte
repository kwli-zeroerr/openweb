<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getKnowledgeById, getKnowledgeLogs, clearKnowledgeLogs, updateKnowledgeById, removeFileFromKnowledgeById } from '$lib/apis/knowledge';
	import { updateFileMetadataById, updateFileById } from '$lib/apis/files';
	import { getGroups } from '$lib/apis/groups';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import CategorizedFiles from './KnowledgeBase/CategorizedFiles.svelte';
	import FileViewer from './KnowledgeBase/FileViewer.svelte';
	import KnowledgeHeader from './KnowledgeBase/KnowledgeHeader.svelte';
	import FileUploadHandler from './KnowledgeBase/FileUploadHandler.svelte';
	import FileOperations from './KnowledgeBase/FileOperations.svelte';
	import FileUpdateModal from './KnowledgeBase/FileUpdateModal.svelte';
	import KnowledgeLogs from './KnowledgeBase/KnowledgeLogs.svelte';
	import AddTextContentModal from './KnowledgeBase/AddTextContentModal.svelte';
	import BatchOwnerModal from './KnowledgeBase/BatchOwnerModal.svelte';
	import BatchCategoryModal from './KnowledgeBase/BatchCategoryModal.svelte';
import DataCleaningPanel from './KnowledgeBase/DataCleaningPanel.svelte';
	import CleaningResultsPanel from './KnowledgeBase/CleaningResultsPanel.svelte';
	import SyncConfirmDialog from '../../common/ConfirmDialog.svelte';
	import DeleteConfirmDialog from '../../common/ConfirmDialog.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import FilesOverlay from '$lib/components/chat/MessageInput/FilesOverlay.svelte';
	import Drawer from '$lib/components/common/Drawer.svelte';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n') as any;
	const t = (i18n as any)?.t || ((key: string) => key);

	export let id: string;

	let knowledge: any = null;
	let loading = true;
	let error: string | null = null;
	let selectedFileId: string | null = null;
	let searchQuery = '';
	let largeScreen = true;
	let showSyncConfirmModal = false;
	let showAccessControlModal = false;
	let showDeleteFileConfirm = false;
	let showFileUpdateModal = false;
	let showLogsPanel = false;
	let showBatchOwnerModal = false;
	let showBatchCategoryModal = false;
	let batchMode = false;
let activeNavTab = 'files'; // 默认切到知识库维护

	let fileToRemoveId: string | null = null;
	let fileToUpdateId: string | null = null;
	let batchFileIds: string[] = [];
	let knowledgeLogs: any[] = [];
	let logsLoading = false;
	let fileUploadHandler: any;
	let accessControl: any = null;

	// 响应式变量
	$: filteredItems = knowledge?.files?.filter((file: any) => {
		if (!searchQuery) return true;
		const query = searchQuery.toLowerCase();
		const fileName = (file.meta?.name || file.name || '').toLowerCase();
		const fileCategory = (file.meta?.category || '').toLowerCase();
		const fileOwner = (file.meta?.owner || '').toLowerCase();
		return fileName.includes(query) || fileCategory.includes(query) || fileOwner.includes(query);
	}) || [];

	// 同步访问控制状态
	$: if (knowledge) {
		accessControl = knowledge.access_control;
	}

	// 监听id变化，自动加载数据
	$: if (id) {
		loadKnowledge();
	}

	// 加载知识库数据
	const loadKnowledge = async () => {
		if (!id) {
			console.error('Knowledge ID is undefined');
			error = 'Knowledge ID is missing';
			loading = false;
			return;
		}
		
		try {
			loading = true;
			const data = await getKnowledgeById(localStorage.token, id);
			knowledge = data;
		} catch (err: any) {
			error = err.message || 'Failed to load knowledge base';
			toast.error(error || 'Unknown error');
		} finally {
			loading = false;
		}
	};

	// 加载知识库日志
	const loadKnowledgeLogs = async () => {
		if (!id) {
			console.error('Knowledge ID is undefined for logs');
			return;
		}
		
		try {
			logsLoading = true;
			const logs = await getKnowledgeLogs(localStorage.token, id);
			knowledgeLogs = logs || [];
		} catch (err: any) {
			console.error('Failed to load knowledge logs:', err);
			knowledgeLogs = [];
		} finally {
			logsLoading = false;
		}
	};

	// 清空日志
	const clearLogs = async (event: any) => {
		if (!id) {
			console.error('Knowledge ID is undefined for clearing logs');
			return;
		}
		
		const confirmText = event.detail;
		if (confirmText === '确定删除') {
			try {
				await clearKnowledgeLogs(localStorage.token, id, confirmText);
				knowledgeLogs = [];
				toast.success('日志已清空');
			} catch (err: any) {
				console.error('Failed to clear logs:', err);
				toast.error('清空日志失败');
			}
		}
	};

	// 切换导航标签
	const handleNavTabChange = (tab: string) => {
		activeNavTab = tab;
		// 关闭其他面板
		showLogsPanel = false;
	};


	// 切换批量选择模式
	const handleToggleBatchMode = () => {
		batchMode = !batchMode;
	};

	// 切换日志面板
	const handleToggleLogsPanel = () => {
		showLogsPanel = !showLogsPanel;
		if (showLogsPanel && knowledgeLogs.length === 0) {
			loadKnowledgeLogs();
		}
	};

	// 显示添加文本内容模态框
	const showAddTextContent = () => {
		// 实现添加文本内容的逻辑
	};

	// 处理文件点击
	const handleFileClick = (event: any) => {
		const fileId = event.detail;
		selectedFileId = fileId;
	};

	// 处理返回文件列表
	const handleBackToList = () => {
		selectedFileId = null;
	};

	// 处理知识库更新
	const handleKnowledgeUpdate = async (event: any) => {
		const { name, description } = event.detail;
		try {
			const updatedKnowledge = await updateKnowledgeById(localStorage.token, id, { name, description });
			knowledge = { ...knowledge, ...updatedKnowledge };
			toast.success('知识库更新成功');
		} catch (err: any) {
			console.error('Failed to update knowledge:', err);
			toast.error('更新失败');
		}
	};

	// 处理知识库更新（从FileViewer）
	const handleKnowledgeUpdated = () => {
		loadKnowledge();
	};

	// 处理确认删除文件
	const handleConfirmDelete = async (event: any) => {
		const fileId = event.detail;
		fileToRemoveId = fileId;
		showDeleteFileConfirm = true;
	};

	// 处理删除文件
	const handleDeleteFile = async () => {
		if (!fileToRemoveId) return;
		
		try {
			await removeFileFromKnowledgeById(localStorage.token, id, fileToRemoveId);
			// 从本地状态中移除文件
			knowledge.files = knowledge.files.filter((f: any) => f.id !== fileToRemoveId);
			knowledge = { ...knowledge };
			toast.success('文件删除成功');
		} catch (err: any) {
			console.error('Failed to delete file:', err);
			toast.error('删除失败');
		} finally {
			showDeleteFileConfirm = false;
			fileToRemoveId = null;
		}
	};

	// 处理更新文件
	const handleUpdateFile = (event: any) => {
		const fileId = event.detail;
		fileToUpdateId = fileId;
		showFileUpdateModal = true;
	};

	// 处理文件更新完成
	const handleFileUpdateComplete = () => {
		showFileUpdateModal = false;
		fileToUpdateId = null;
		loadKnowledge();
	};

	// 处理批量设置负责人
	const handleBatchOwnerAssignment = (event: any) => {
		batchFileIds = event.detail.fileIds;
		showBatchOwnerModal = true;
	};

	// 批量负责人设置成功回调
	const handleBatchOwnerSuccess = (event: any) => {
		const { fileIds, owner, successCount, failCount } = event.detail;
		
		// 更新本地状态
		fileIds.forEach((fileId: string) => {
			const fileIndex = knowledge.files.findIndex((f: any) => f.id === fileId);
			if (fileIndex !== -1) {
				knowledge.files[fileIndex].meta = { 
					...knowledge.files[fileIndex].meta, 
					owner: owner 
				};
			}
		});
		
		knowledge = { ...knowledge }; // 触发响应式更新
		
		showBatchOwnerModal = false;
		batchFileIds = [];
	};

	// 处理批量设置分类
	const handleBatchCategoryAssignment = (event: any) => {
		batchFileIds = event.detail.fileIds;
		showBatchCategoryModal = true;
	};

	// 批量分类设置成功回调
	const handleBatchCategorySuccess = (event: any) => {
		const { fileIds, category, successCount, failCount } = event.detail;
		
		// 更新本地状态
		fileIds.forEach((fileId: string) => {
			const fileIndex = knowledge.files.findIndex((f: any) => f.id === fileId);
			if (fileIndex !== -1) {
				knowledge.files[fileIndex].meta = { 
					...knowledge.files[fileIndex].meta, 
					category: category 
				};
			}
		});
		
		knowledge = { ...knowledge }; // 触发响应式更新
		
		showBatchCategoryModal = false;
		batchFileIds = [];
	};

	// 处理显示访问控制
	const handleShowAccessControl = () => {
		showAccessControlModal = true;
	};

	// 处理错误
	const handleError = (event: any) => {
		error = event.detail;
		toast.error(error || 'Unknown error');
	};

	// 组件挂载时初始化
	onMount(() => {
		// 监听窗口大小变化
		const handleResize = () => {
			largeScreen = window.innerWidth >= 1024;
		};
		
		handleResize();
		window.addEventListener('resize', handleResize);
		
		return () => {
			window.removeEventListener('resize', handleResize);
		};
	});
</script>

<div class="flex flex-col w-full h-full translate-y-1" id="collection-container">
	{#if id && knowledge}
		<!-- 知识库头部 -->
		<KnowledgeHeader
			bind:knowledge
			{i18n}
			on:updateKnowledge={handleKnowledgeUpdate}
			on:showAccessControl={handleShowAccessControl}
			on:error={handleError}
		/>

		<!-- 主内容区域 -->
		<div class="flex flex-1 h-full max-h-full">
			<!-- 左侧导航栏 -->
			<div class="w-48 bg-gray-50 dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col">
				<div class="p-4 border-b border-gray-200 dark:border-gray-700">
					<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100">功能面板</h3>
						</div>
				<nav class="flex-1 p-2">
                    <div class="space-y-1">
						<button
							class="w-full text-left px-3 py-2 text-sm rounded-md transition-colors {activeNavTab === 'files' ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}"
							on:click={() => handleNavTabChange('files')}
						>
                            知识库维护
						</button>
						<button
							class="w-full text-left px-3 py-2 text-sm rounded-md transition-colors {activeNavTab === 'cleaning' ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}"
							on:click={() => handleNavTabChange('cleaning')}
						>
                            知识清洗
						</button>
						<button
							class="w-full text-left px-3 py-2 text-sm rounded-md transition-colors {activeNavTab === 'cleaning-results' ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300' : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}"
							on:click={() => handleNavTabChange('cleaning-results')}
						>
                            清洗结果
						</button>
					</div>
				</nav>
			</div>

			<!-- 右侧内容区域 -->
			<div class="flex-1 flex flex-col h-full">
				{#if activeNavTab === 'files'}
					<!-- 知识库文件面板 -->
					<div class="flex flex-col flex-1 h-full max-h-full pb-2.5 gap-3">
						{#if showLogsPanel}
							<!-- Knowledge Logs Panel -->
							<div class="h-screen">
								<KnowledgeLogs
									knowledgeId={id}
									logs={knowledgeLogs}
									loading={logsLoading}
									on:refresh={loadKnowledgeLogs}
									on:clear={clearLogs}
								/>
							</div>
						{:else if largeScreen}
							<div class="flex-1 flex flex-col w-full h-full max-h-full">
								{#if selectedFileId}
									<!-- File Content View -->
									<FileViewer
										selectedFile={knowledge?.files?.find(f => f.id === selectedFileId)}
										bind:knowledge
										{i18n}
										on:backToList={handleBackToList}
										on:knowledgeUpdated={handleKnowledgeUpdated}
									/>
								{:else}
									<!-- File Categories Grid -->
									<div class="w-full h-full overflow-y-auto scrollbar-hidden">
										<div class="p-4">
											<div class="mb-4">
												<div class="flex items-center justify-between">
													<div>
                                                    <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">知识库维护</h2>
														<p class="text-sm text-gray-600 dark:text-gray-400">点击文件卡片查看内容</p>
													</div>
													<div class="flex items-center gap-2">
														<!-- 批量选择按钮 -->
														<button
															class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
															type="button"
															on:click={handleToggleBatchMode}
														>
															<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
															</svg>
															<div class="text-sm font-medium shrink-0">
																批量选择
															</div>
														</button>
														
														<!-- 日志按钮 -->
														<button
															class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
															type="button"
															on:click={handleToggleLogsPanel}
														>
															<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
															</svg>
															<div class="text-sm font-medium shrink-0">
																日志
															</div>
														</button>
														
														<!-- 添加文件按钮 -->
														<button
															class="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-md transition-colors flex items-center gap-2"
															on:click={() => {
																const input = document.createElement('input');
																input.type = 'file';
																input.multiple = true;
																input.onchange = (e) => {
																	const target = e.target;
																	if (target && 'files' in target) {
																		const files = Array.from(target.files || []);
																		files.forEach(file => {
																			fileUploadHandler.uploadFileHandler(file);
																		});
																	}
																};
																input.click();
															}}
														>
															<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
															</svg>
															添加文件
														</button>
													</div>
												</div>
											</div>

											{#if filteredItems.length > 0}
												<CategorizedFiles
													files={filteredItems}
													selectedFileId={selectedFileId || null}
													batchMode={batchMode}
													on:click={handleFileClick}
													on:delete={handleConfirmDelete}
													on:update={handleUpdateFile}
													on:batchOwnerAssignment={handleBatchOwnerAssignment}
													on:batchCategoryAssignment={handleBatchCategoryAssignment}
													on:toggleBatchMode={handleToggleBatchMode}
												/>
											{:else}
												<div class="text-center text-gray-500 dark:text-gray-400 py-12">
                                                    <div class="text-lg mb-2">暂无内容</div>
													<div class="text-sm">上传文件或添加内容到知识库</div>
							</div>
											{/if}
							</div>
						</div>
					{/if}
				</div>
						{:else}
							<!-- Mobile view -->
							<div class="flex-1 flex flex-col w-full h-full max-h-full">
								{#if selectedFileId}
									<!-- File Content View -->
									<FileViewer
										selectedFile={knowledge?.files?.find(f => f.id === selectedFileId)}
										bind:knowledge
										{i18n}
										on:backToList={handleBackToList}
										on:knowledgeUpdated={handleKnowledgeUpdated}
									/>
								{:else}
									<!-- File Categories Grid -->
									<div class="w-full h-full overflow-y-auto scrollbar-hidden">
										<div class="p-4">
											<div class="mb-4">
												<div class="flex items-center justify-between">
													<div>
                                                    <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">知识库维护</h2>
														<p class="text-sm text-gray-600 dark:text-gray-400">点击文件卡片查看内容</p>
													</div>
													<div class="flex items-center gap-2">
														<!-- 批量选择按钮 -->
														<button
															class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
															type="button"
															on:click={handleToggleBatchMode}
														>
															<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
															</svg>
															<div class="text-sm font-medium shrink-0">
																批量选择
															</div>
														</button>
														
														<!-- 日志按钮 -->
														<button
															class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
															type="button"
															on:click={handleToggleLogsPanel}
														>
															<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
															</svg>
															<div class="text-sm font-medium shrink-0">
																日志
															</div>
														</button>
														
														<!-- 添加文件按钮 -->
														<button
															class="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white text-sm rounded-md transition-colors flex items-center gap-2"
															on:click={() => {
																const input = document.createElement('input');
																input.type = 'file';
																input.multiple = true;
																input.onchange = (e) => {
																	const target = e.target;
																	if (target && 'files' in target) {
																		const files = Array.from(target.files || []);
																		files.forEach(file => {
																			fileUploadHandler.uploadFileHandler(file);
																		});
																	}
																};
																input.click();
															}}
														>
															<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
															</svg>
															添加文件
														</button>
													</div>
												</div>
											</div>

											{#if filteredItems.length > 0}
												<CategorizedFiles
													files={filteredItems}
													selectedFileId={selectedFileId || null}
													batchMode={batchMode}
													on:click={handleFileClick}
													on:delete={handleConfirmDelete}
													on:update={handleUpdateFile}
													on:batchOwnerAssignment={handleBatchOwnerAssignment}
													on:batchCategoryAssignment={handleBatchCategoryAssignment}
													on:toggleBatchMode={handleToggleBatchMode}
												/>
											{:else}
												<div class="text-center text-gray-500 dark:text-gray-400 py-12">
                                                    <div class="text-lg mb-2">暂无内容</div>
													<div class="text-sm">上传文件或添加内容到知识库</div>
											</div>
										{/if}
										</div>
								</div>
								{/if}
							</div>
						{/if}
					</div>
				{:else if activeNavTab === 'cleaning'}
					<!-- 数据清洗面板 -->
					<div class="flex-1 h-full">
						<DataCleaningPanel
							knowledgeId={id}
							files={knowledge?.files || []}
						/>
					</div>
				{:else if activeNavTab === 'cleaning-results'}
					<!-- 清洗结果面板 -->
					<div class="flex-1 h-full">
						<CleaningResultsPanel
							knowledgeId={id}
						/>
					</div>
				{/if}
			</div>
		</div>
	{:else}
		<Spinner className="size-5" />
	{/if}
</div>

<!-- 文件上传处理器 -->
<FileUploadHandler 
	bind:this={fileUploadHandler} 
	{knowledge} 
	{id}
	settings={{}}
	config={{}}
	{i18n}
	on:knowledgeUpdated={handleKnowledgeUpdated}
/>

<!-- 文件更新模态框 -->
{#if showFileUpdateModal && fileToUpdateId}
	<FileUpdateModal
		show={showFileUpdateModal}
		file={knowledge?.files?.find(f => f.id === fileToUpdateId)}
		on:close={() => {
			showFileUpdateModal = false;
			fileToUpdateId = null;
		}}
		on:success={handleFileUpdateComplete}
	/>
{/if}

<!-- 删除确认对话框 -->
<DeleteConfirmDialog
	show={showDeleteFileConfirm}
	title="删除文件"
	message="确定要删除这个文件吗？此操作不可撤销。"
	input={true}
	inputPlaceholder="请输入'确定删除'来确认删除操作"
	onConfirm={handleDeleteFile}
/>

<!-- 访问控制模态框 -->
{#if knowledge}
	<AccessControlModal
		show={showAccessControlModal}
		bind:accessControl={accessControl}
		onChange={() => {
			knowledge.access_control = accessControl;
			showAccessControlModal = false;
		}}
	/>
{/if}

<!-- 批量设置负责人模态框 -->
<BatchOwnerModal
	bind:isOpen={showBatchOwnerModal}
	fileIds={batchFileIds}
	files={knowledge?.files || []}
	on:close={() => {
		showBatchOwnerModal = false;
		batchFileIds = [];
	}}
	on:success={handleBatchOwnerSuccess}
/>

<!-- 批量设置分类模态框 -->
<BatchCategoryModal
	bind:isOpen={showBatchCategoryModal}
	fileIds={batchFileIds}
	files={knowledge?.files || []}
	on:close={() => {
		showBatchCategoryModal = false;
		batchFileIds = [];
	}}
	on:success={handleBatchCategorySuccess}
/>