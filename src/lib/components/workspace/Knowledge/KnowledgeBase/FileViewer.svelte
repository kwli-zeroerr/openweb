<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher } from 'svelte';
	import { onMount, onDestroy } from 'svelte';
	import { getFileById } from '$lib/apis/files';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import FileMetadata from './FileMetadata.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import PDFViewer from '$lib/components/common/PDFViewer.svelte';
	import OCRCompareViewer from './OCRCompareViewer.svelte';
	import VLMViewer from './VLMViewer.svelte';
	import AutoSegmentsPanel from './AutoSegmentsPanel.svelte';

	const dispatch = createEventDispatcher();

	export let selectedFile: any = null;
	export let knowledge: any = null;
	export let i18n: any;

	let selectedFileContent = '';
	let viewMode = 'preview'; // 'preview', 'text', 'vector', 'ocr-compare', or 'vlm'
	let fileContentCache = new Map();
	let lastOcrStatus = new Map(); // 跟踪每个文件的最后 OCR 状态
	let ocrMarkdownContent = ''; // OCR 处理后的 Markdown 内容
	let loadingOCRMarkdown = false; // 是否正在加载 OCR Markdown
	let processingOCRMarkdown = false; // 是否正在处理 OCR Markdown（大文件异步处理）
	let lastLoadedTaskId: string | null = null; // 上次加载的任务 ID，用于防止重复加载
	// 获取文件的 OCR 任务 ID
	const getOCRTaskId = async (fileId: string): Promise<string | null> => {
		try {
			const response = await getFileById(localStorage.token, fileId);
			console.log('📋 getFileById 响应:', response);
			if (response && response.data) {
				const taskId = response.data.ocr_task_id || null;
				console.log('📋 OCR 任务 ID:', taskId);
				return taskId;
			} else {
				console.warn('⚠️ 响应中没有 data 字段:', response);
			}
		} catch (e) {
			console.error('❌ 获取 OCR 任务 ID 失败:', e);
		}
		return null;
	};

	let ocrTaskId: string | null = null;

	// 切换到依赖 OCR 的视图时获取任务 ID
	$: if (
		selectedFile?.id &&
		(viewMode === 'ocr-compare' || viewMode === 'vlm' || viewMode === 'text' || viewMode === 'auto-split')
	) {
		getOCRTaskId(selectedFile.id).then((id) => {
			ocrTaskId = id;
		});
	}

	// 获取i18n的t方法
	const t = (i18n as any)?.t || ((key: string) => key);

	const yieldToUI = () =>
		new Promise<void>((resolve) => {
			if (typeof requestIdleCallback !== 'undefined') {
				requestIdleCallback(() => resolve(), { timeout: 50 });
			} else if (typeof requestAnimationFrame !== 'undefined') {
				requestAnimationFrame(() => resolve());
			} else {
				setTimeout(() => resolve(), 0);
			}
		});

	const convertMarkdownImages = async (markdownContent: string, taskId: string) => {
		const imageRegex = /!\[([^\]]*)\]\((\.?\/?)(images\/[^)]+)\)/g;
		let result = '';
		let lastIndex = 0;
		let matchCount = 0;
		let match: RegExpExecArray | null;

		while ((match = imageRegex.exec(markdownContent)) !== null) {
			const [fullMatch, alt, _prefix, imagePath] = match;
			result += markdownContent.slice(lastIndex, match.index);
			const relativeImagePath = `ocr_result_${taskId}/${imagePath}`;
			const imageUrl = `/api/v1/knowledge/${knowledge.id}/files/${encodeURIComponent(relativeImagePath)}`;
			result += `![${alt}](${imageUrl})`;
			lastIndex = imageRegex.lastIndex;

			matchCount += 1;
			if (matchCount % 50 === 0) {
				await yieldToUI();
			}
		}

		result += markdownContent.slice(lastIndex);
		return result;
	};

	// 加载 OCR 处理后的 Markdown 内容
	const loadOCRMarkdown = async (taskId: string) => {
		// 防止重复加载：如果正在加载相同的任务，直接返回
		if (loadingOCRMarkdown && lastLoadedTaskId === taskId) {
			console.log('⏭️ 正在加载相同的任务，跳过重复调用');
			return;
		}
		
		// 如果已经有内容且是同一个任务，也跳过
		if (ocrMarkdownContent && lastLoadedTaskId === taskId && !loadingOCRMarkdown) {
			console.log('⏭️ 内容已加载，跳过重复调用');
			return;
		}
		
		if (!knowledge?.id) {
			console.warn('⚠️ 知识库 ID 不存在，无法加载 OCR Markdown');
			ocrMarkdownContent = '';
			return;
		}

		if (!taskId) {
			console.warn('⚠️ OCR 任务 ID 为空，无法加载 Markdown');
			ocrMarkdownContent = '';
			return;
		}

		try {
			loadingOCRMarkdown = true;
			lastLoadedTaskId = taskId; // 记录当前加载的任务 ID
			const resultPath = `ocr_result_${taskId}/result.mmd`;
			const fileUrl = `/api/v1/knowledge/${knowledge.id}/files/${encodeURIComponent(resultPath)}`;
			
			console.log(`📥 尝试加载 OCR Markdown: ${fileUrl}`);
			console.log(`📋 任务 ID: ${taskId}, 知识库 ID: ${knowledge.id}`);
			
			const response = await fetch(fileUrl, {
				headers: {
					'authorization': `Bearer ${localStorage.token}`
				}
			});

			console.log(`📊 响应状态: ${response.status} ${response.statusText}`);

			if (response.ok) {
				const markdownContent = await response.text();
				console.log(`✅ 成功加载 Markdown，长度: ${markdownContent.length} 字符`);
				
				console.log(`⏳ 使用异步处理 Markdown 内容以避免阻塞界面...`);
				processingOCRMarkdown = true;
				try {
					const processedContent = await convertMarkdownImages(markdownContent, taskId);
					ocrMarkdownContent = processedContent;
					console.log(`✅ Markdown 内容处理完成，已更新 UI`);
				} finally {
					processingOCRMarkdown = false;
				}
			} else if (response.status === 404) {
				// 文件不存在，可能是 OCR 还没处理完
				console.warn(`⚠️ 文件不存在 (404): ${fileUrl}`);
				console.warn(`⚠️ 可能原因: OCR 处理尚未完成，或文件路径不正确`);
				ocrMarkdownContent = '';
				lastLoadedTaskId = null; // 清除记录，允许重试
			} else {
				const errorText = await response.text().catch(() => '');
				console.error(`❌ 加载 OCR Markdown 失败 (${response.status}):`, response.statusText);
				console.error(`❌ 错误详情:`, errorText);
				ocrMarkdownContent = '';
				lastLoadedTaskId = null; // 清除记录，允许重试
			}
		} catch (e) {
			console.error('❌ 加载 OCR Markdown 异常:', e);
			ocrMarkdownContent = '';
			lastLoadedTaskId = null; // 清除记录，允许重试
		} finally {
			loadingOCRMarkdown = false;
		}
	};

	// Check if file is PDF
	const isPdfFile = (file: any) => {
		return file?.meta?.name?.toLowerCase().endsWith('.pdf') || 
			   file?.meta?.mime_type === 'application/pdf';
	};

	// Check if file is Markdown
	const isMarkdownFile = (file: any) => {
		const name = file?.meta?.name?.toLowerCase() || '';
		const mime = file?.meta?.mime_type || file?.meta?.content_type || '';
		return name.endsWith('.md') || name.endsWith('.markdown') || mime === 'text/markdown' || mime === 'text/x-markdown';
	};

	// Check if file is DOCX
	const isDocxFile = (file: any) => {
		const name = file?.meta?.name?.toLowerCase() || '';
		const mime = file?.meta?.mime_type || file?.meta?.content_type || '';
		return name.endsWith('.docx') || mime === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
	};

	// 刷新文件内容（强制从服务器获取最新内容）
	const refreshFileContent = async (fileId: string, showToast: boolean = false) => {
		try {
			// 清除缓存
			fileContentCache.delete(fileId);
			
			const response = await getFileById(localStorage.token, fileId);
			if (response) {
				const newContent = response.data.content || '';
				selectedFileContent = newContent;
				// 更新缓存
				fileContentCache.set(fileId, newContent);
				
				if (showToast) {
					toast.success(t('File content refreshed.'));
				}
				return true;
			} else {
				if (showToast) {
					toast.error(t('No content found in file.'));
				}
				return false;
			}
		} catch (e) {
			console.error('Failed to refresh file content:', e);
			if (showToast) {
				toast.error(t('Failed to refresh file content.'));
			}
			return false;
		}
	};

	// 文件选择处理
	const fileSelectHandler = async (file: any, forceRefresh: boolean = false) => {
		try {
			// 只有在选择不同文件时才重置 viewMode
			const isNewFile = !selectedFile || selectedFile.id !== file.id;
			const previousViewMode = viewMode; // 保存之前的 viewMode
			selectedFile = file;
			// Reset view mode only when selecting a different file
			if (isNewFile) {
				viewMode = 'preview';
			} else {
				// 如果是同一个文件，保持当前的 viewMode
				viewMode = previousViewMode;
			}
			console.log('fileSelectHandler - selectedFile:', file?.id, 'viewMode:', viewMode, 'isNewFile:', isNewFile);

			// 如果需要强制刷新，直接调用 refreshFileContent
			if (forceRefresh) {
				await refreshFileContent(file.id, false);
				return;
			}

			// Check cache first (但如果是 PDF 文件且可能有 OCR 更新，不缓存)
			if (fileContentCache.has(file.id) && !isPdfFile(file)) {
				selectedFileContent = fileContentCache.get(file.id);
				return;
			}

			const response = await getFileById(localStorage.token, file.id);
			if (response) {
				const content = response.data.content || '';
				selectedFileContent = content;
				// 对于 PDF 文件，不缓存内容（因为 OCR 处理可能会更新内容）
				if (!isPdfFile(file)) {
					fileContentCache.set(file.id, content);
				}
			} else {
				toast.error(t('No content found in file.'));
			}
		} catch (e) {
			toast.error(t('Failed to load file content.'));
		}
	};


	// 解码字符串
	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};

	// 监听 selectedFile 变化
	$: if (selectedFile && selectedFile.id) {
		// 只有在 selectedFile 有 id 时才处理，避免重复处理
		const currentFileId = selectedFile.id;
		if (!fileContentCache.has(currentFileId) || selectedFileContent === '') {
			fileSelectHandler(selectedFile);
		}
	}

	// 监听 knowledge 变化，检测 OCR 完成事件
	$: if (knowledge && selectedFile) {
		// 查找当前文件在 knowledge.files 中的状态
		const currentFileInKnowledge = knowledge.files?.find((f: any) => f.id === selectedFile.id);
		
		if (currentFileInKnowledge) {
			const fileId = selectedFile.id;
			const currentOcrStatus = currentFileInKnowledge.ocrStatus;
			const lastStatus = lastOcrStatus.get(fileId);
			
			// 检查 OCR 状态是否从非 completed 变为 completed
			const ocrJustCompleted = currentOcrStatus === 'completed' && 
									 currentFileInKnowledge.hasMarkdown === true &&
									 lastStatus !== 'completed';
			
			// 更新最后状态
			lastOcrStatus.set(fileId, currentOcrStatus);
			
			// 如果 OCR 刚完成，且当前正在查看该文件，自动刷新内容
			if (ocrJustCompleted) {
				console.log(`🔄 OCR 完成，自动刷新文件内容: ${fileId}`);
				// 延迟一下，确保后端已经保存了内容
				setTimeout(() => {
					refreshFileContent(fileId, true);
					// 如果当前在 Markdown 文本模式，重新加载 OCR Markdown 内容
					if (viewMode === 'text' && ocrTaskId) {
						loadOCRMarkdown(ocrTaskId);
					}
				}, 1000); // 延迟 1 秒，确保后端已保存
			}
		}
	}

	// 导出方法供父组件使用
	export { fileSelectHandler, refreshFileContent };
</script>

<!-- File Content View - 始终显示，即使 selectedFile 为 null 也显示选项卡 -->
<div class="flex flex-col w-full h-full file-viewer-container" style="display: flex !important; visibility: visible !important; opacity: 1 !important; min-height: 100%;">
		<!-- 选项卡区域 - 固定在顶部，始终显示，不能隐藏 -->
		<div class="shrink-0 mb-2 flex items-center tabs-header-container" id="file-viewer-tabs-header" style="position: sticky !important; top: 0 !important; z-index: 1000 !important; background: var(--bg-color, white) !important; display: flex !important; visibility: visible !important; opacity: 1 !important; width: 100% !important;">
			<!-- Back Button -->
			<div class="mr-3">
				<button
					class="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-all duration-200"
					on:click={() => {
						dispatch('backToList');
					}}
				>
					<ChevronLeft strokeWidth="2.5" />
					<span>返回文件列表</span>
				</button>
			</div>

			<div class="flex-1 text-xl font-medium">
				<span
					class="grow line-clamp-1 cursor-default"
					title={decodeString(selectedFile?.meta?.name) || '未选择文件'}
				>
					{decodeString(selectedFile?.meta?.name) || '未选择文件'}
				</span>
			</div>

			<div class="flex items-center gap-2" style="display: flex !important; visibility: visible !important; opacity: 1 !important;">
				<!-- 选项卡始终显示，不能隐藏 - 使用固定样式确保始终可见 -->
				<div class="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-1 view-mode-tabs-container" style="display: flex !important; visibility: visible !important; opacity: 1 !important;">
					<button
						class="px-3 py-1 text-xs rounded-md transition-all duration-150 view-mode-tab {viewMode === 'preview' 
							? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
							: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'}"
						style="display: inline-block !important; visibility: visible !important; opacity: 1 !important;"
						on:click={() => viewMode = 'preview'}
					>
						预览
					</button>
					<button
						class="px-3 py-1 text-xs rounded-md transition-all duration-150 view-mode-tab {viewMode === 'text' 
							? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
							: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'}"
						style="display: inline-block !important; visibility: visible !important; opacity: 1 !important;"
						on:click={async (e) => {
							// 防止事件冒泡和默认行为
							e.preventDefault();
							e.stopPropagation();
							
							viewMode = 'text';
							// 获取 OCR 任务 ID 并加载 Markdown 内容
							if (selectedFile?.id) {
								const taskId = await getOCRTaskId(selectedFile.id);
								ocrTaskId = taskId;
								if (taskId) {
									await loadOCRMarkdown(taskId);
								} else {
									ocrMarkdownContent = '';
									lastLoadedTaskId = null;
								}
							}
						}}
					>
						Markdown文本
					</button>
					<button
						class="px-3 py-1 text-xs rounded-md transition-all duration-150 view-mode-tab {viewMode === 'ocr-compare' 
							? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
							: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'}"
						style="display: inline-block !important; visibility: visible !important; opacity: 1 !important;"
						on:click={async () => {
							viewMode = 'ocr-compare';
							// 获取 OCR 任务 ID
							if (selectedFile?.id) {
								const taskId = await getOCRTaskId(selectedFile.id);
								ocrTaskId = taskId;
								if (!taskId) {
									toast.error('未找到 OCR 处理结果，请先完成 OCR 处理');
									viewMode = 'preview';
								}
							}
						}}
					>
						OCR对比
					</button>
					<button
						class="px-3 py-1 text-xs rounded-md transition-all duration-150 view-mode-tab {viewMode === 'vlm' 
							? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
							: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'}"
						style="display: inline-block !important; visibility: visible !important; opacity: 1 !important;"
						on:click={async () => {
							viewMode = 'vlm';
			// 获取 OCR 任务 ID（人工处理需要基于 OCR 结果）
							if (selectedFile?.id) {
								const taskId = await getOCRTaskId(selectedFile.id);
								ocrTaskId = taskId;
								if (!taskId) {
									toast.error('未找到 OCR 处理结果，请先完成 OCR 处理');
									viewMode = 'preview';
								}
							}
						}}
					>
						人工处理
					</button>
					<button
						class="px-3 py-1 text-xs rounded-md transition-all duration-150 view-mode-tab {viewMode === 'auto-split' 
							? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
							: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'}"
						style="display: inline-block !important; visibility: visible !important; opacity: 1 !important;"
						on:click={() => (viewMode = 'auto-split')}
					>
						自动分段
					</button>
					<button
						class="px-3 py-1 text-xs rounded-md transition-all	duration-150 view-mode-tab {viewMode === 'vector' 
							? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm' 
							: 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover	text-gray-100'}"
						style="display: inline-block !important; visibility: visible !important; opacity: 1 !important;"
						on:click={() => viewMode = 'vector'}
					>
						向量知识库
					</button>
				</div>

				{#if selectedFile?.id}
					<a
						href={`/api/v1/files/${selectedFile.id}/content?attachment=true`}
						class="self-center w-fit text-sm py-1 px-2.5 bg-gray-900 text-white hover:bg-black/80 dark:bg-white dark:text-black dark:hover:bg-white/90 rounded-lg transition"
						download={decodeString(selectedFile?.meta?.name)}
					>
						下载
					</a>
				{/if}
			</div>
		</div>

		<!-- File Metadata -->
		<FileMetadata {selectedFile} {knowledge} />

		<div
			class="flex-1 w-full h-full max-h-full text-sm bg-transparent outline-hidden overflow-y-auto scrollbar-hidden"
		>
			{#key selectedFile?.id || 'no-file'}
				{#if viewMode === 'text'}
					{#if loadingOCRMarkdown || processingOCRMarkdown}
						<div class="w-full h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
							<div class="text-center">
								<div class="text-sm mb-2">
									{loadingOCRMarkdown ? '正在加载 OCR 处理结果...' : '正在处理 Markdown 内容（大文件，请稍候）...'}
								</div>
								<div class="w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mt-4"></div>
								{#if processingOCRMarkdown}
									<div class="text-xs text-gray-400 dark:text-gray-500 mt-2">
										文件较大，正在异步处理以避免界面卡顿
									</div>
								{/if}
							</div>
						</div>
					{:else if ocrMarkdownContent}
						<!-- Markdown文本模式：显示 OCR 处理后的 Markdown 内容 -->
						<div class="w-full h-full overflow-y-auto">
							<div class="knowledge-markdown-viewer markdown-prose">
								<Markdown 
									id={`ocr-markdown-${selectedFile?.id || 'no-file'}`} 
									content={ocrMarkdownContent} 
									done={true}
									editCodeBlock={true}
									topPadding={true}
								/>
							</div>
						</div>
					{:else}
						<div class="w-full h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
							<div class="text-center">
								<div class="text-sm mb-2">OCR 处理尚未完成</div>
								<div class="text-xs text-gray-400 dark:text-gray-500 mt-2">
									{ocrTaskId ? `任务 ID: ${ocrTaskId}` : '未找到 OCR 任务'}
								</div>
							</div>
						</div>
					{/if}
				{:else if viewMode === 'preview' && isPdfFile(selectedFile)}
					<div class="w-full h-full">
						<PDFViewer 
							fileUrl={selectedFile.id ? `/api/v1/files/${selectedFile.id}/content` : ''}
							authToken={typeof localStorage !== 'undefined' ? localStorage.token : null}
							initialScale={1.0}
							showToolbar={true}
							enableTextSelection={true}
							on:loaded={(e) => {
								console.log('PDF loaded:', e.detail);
								dispatch('pdfLoaded', e.detail);
							}}
							on:pagechange={(e) => {
								console.log('Page changed:', e.detail);
								dispatch('pageChanged', e.detail);
							}}
						/>
					</div>
				{:else if viewMode === 'preview' && isMarkdownFile(selectedFile)}
					<!-- 预览模式：使用与聊天界面相同的 Markdown 组件渲染 -->
					<div class="w-full h-full overflow-y-auto">
						<div class="knowledge-markdown-viewer markdown-prose">
							<Markdown 
								id={selectedFile.id} 
								content={selectedFileContent} 
								done={true}
								editCodeBlock={true}
								topPadding={true}
							/>
						</div>
					</div>
				{:else if viewMode === 'preview' && isDocxFile(selectedFile)}
					<!-- 预览模式：使用与聊天界面相同的 Markdown 组件渲染 -->
					<div class="w-full h-full overflow-y-auto">
						<div class="knowledge-markdown-viewer markdown-prose">
							<Markdown 
								id={selectedFile.id} 
								content={selectedFileContent} 
								done={true}
								editCodeBlock={true}
								topPadding={true}
							/>
						</div>
					</div>
				{:else if viewMode === 'ocr-compare'}
					{#if ocrTaskId}
						<div class="w-full h-full">
							<OCRCompareViewer 
								knowledgeId={knowledge.id} 
								ocrTaskId={ocrTaskId}
								{i18n}
							/>
						</div>
					{:else}
						<div class="w-full h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
							<div class="text-center">
								<div class="text-sm mb-2">加载 OCR 任务信息...</div>
								<div class="w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mt-4"></div>
							</div>
						</div>
					{/if}
				{:else if viewMode === 'vlm'}
					{#if ocrTaskId}
						<div class="w-full h-full overflow-hidden">
							<VLMViewer 
								knowledgeId={knowledge.id} 
								ocrTaskId={ocrTaskId}
								selectedFile={selectedFile}
								{i18n}
							/>
						</div>
					{:else}
						<div class="w-full h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
							<div class="text-center">
								<div class="text-sm mb-2">加载 OCR 任务信息...</div>
								<div class="w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mt-4"></div>
							</div>
						</div>
					{/if}
				{:else if viewMode === 'auto-split'}
					<div class="w-full h-full overflow-hidden">
						<AutoSegmentsPanel
							knowledgeId={knowledge?.id}
							ocrTaskId={ocrTaskId}
							fileName={selectedFile?.meta?.name || selectedFile?.name || ''}
						/>
					</div>
				{:else if viewMode === 'vector'}
					<div class="w-full h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
						<div class="text-center">
							<div class="text-sm mb-2">向量知识库</div>
							<div class="text-xs">显示文档的向量化内容和检索信息</div>
							<div class="text-xs mt-2 text-gray-400 dark:text-gray-500">
								文档ID: {selectedFile?.id}
							</div>
						</div>
					</div>
				{:else}
					<div class="w-full h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
						<div class="text-center">
							<div class="text-sm mb-2">预览模式仅支持PDF文件</div>
						</div>
					</div>
				{/if}
			{/key}
		</div>
	</div>

<style>
	/* 确保整个文件查看器容器始终显示 */
	.file-viewer-container,
	div.file-viewer-container {
		display: flex !important;
		visibility: visible !important;
		opacity: 1 !important;
	}
	
	/* 确保选项卡区域始终显示，不能被隐藏 */
	.tabs-header-container,
	div.tabs-header-container,
	div[style*="position: sticky"].tabs-header-container {
		display: flex !important;
		visibility: visible !important;
		opacity: 1 !important;
		position: sticky !important;
		top: 0 !important;
		z-index: 100 !important;
	}
	
	/* 确保选项卡容器始终显示 - 使用类选择器 */
	.view-mode-tabs-container,
	div.view-mode-tabs-container,
	div[style*="display: flex !important"].view-mode-tabs-container {
		display: flex !important;
		visibility: visible !important;
		opacity: 1 !important;
		pointer-events: auto !important;
	}
	
	/* 确保每个选项卡按钮始终显示 */
	.view-mode-tab,
	button.view-mode-tab,
	button[class*="view-mode-tab"] {
		display: inline-block !important;
		visibility: visible !important;
		opacity: 1 !important;
		pointer-events: auto !important;
	}
	
	/* 确保选项卡父容器始终显示 */
	div.flex.items-center.gap-2[style*="display: flex !important"] {
		display: flex !important;
		visibility: visible !important;
		opacity: 1 !important;
	}
	
	/* 知识库 Markdown 渲染与聊天保持一致 */
	:global(.knowledge-markdown-viewer) {
		width: 100%;
		max-width: none;
	}
</style>
