<script lang="ts">
	import { onMount } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';

	export let knowledgeId: string;
	export let ocrTaskId: string;
	export let i18n: any;

	const t = (i18n as any)?.t || ((key: string) => key);

	let currentPage = 1;
	let totalPages = 0;
	let pages: string[] = [];
	let pageResults: string[] = [];
	let loading = true;
	let error: string | null = null;

	// 加载页面列表
	const loadPages = async () => {
		try {
			loading = true;
			error = null;

			// 获取 pages 目录下的所有 PNG 文件
			const pagesDir = `ocr_result_${ocrTaskId}/pages`;
			const pageResultsDir = `ocr_result_${ocrTaskId}/page_results`;

			// 使用后端 API 获取文件列表
			const [pagesResponse, pageResultsResponse] = await Promise.all([
				fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files-list/${encodeURIComponent(pagesDir)}`, {
					headers: {
						'authorization': `Bearer ${localStorage.token}`
					}
				}).catch(() => null),
				fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files-list/${encodeURIComponent(pageResultsDir)}`, {
					headers: {
						'authorization': `Bearer ${localStorage.token}`
					}
				}).catch(() => null)
			]);

			// 处理 pages 目录
			if (pagesResponse && pagesResponse.ok) {
				const pagesData = await pagesResponse.json();
				pages = (pagesData.files || [])
					.filter((f: any) => f.extension === '.png' && f.name.startsWith('page_'))
					.map((f: any) => f.path)
					.sort((a: string, b: string) => {
						const numA = parseInt(a.match(/page_(\d+)\.png/)?.[1] || '0');
						const numB = parseInt(b.match(/page_(\d+)\.png/)?.[1] || '0');
						return numA - numB;
					});
			} else {
				// 如果 API 不可用，回退到逐个检查的方式
				console.warn('文件列表 API 不可用，使用回退方案');
				const maxPages = 200;
				for (let i = 1; i <= maxPages; i++) {
					const pageNum = String(i).padStart(3, '0');
					const pagePath = `${pagesDir}/page_${pageNum}.png`;
					
					try {
						const response = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(pagePath)}`, {
							headers: {
								'authorization': `Bearer ${localStorage.token}`
							},
							method: 'HEAD'
						});
						
						if (response.ok) {
							pages.push(pagePath);
						} else {
							break; // 文件不存在，停止查找
						}
					} catch (e) {
						break;
					}
				}
			}

			// 处理 page_results 目录
			if (pageResultsResponse && pageResultsResponse.ok) {
				const pageResultsData = await pageResultsResponse.json();
				pageResults = (pageResultsData.files || [])
					.filter((f: any) => f.extension === '.mmd' && f.name.startsWith('page_'))
					.map((f: any) => f.path)
					.sort((a: string, b: string) => {
						const numA = parseInt(a.match(/page_(\d+)\.mmd/)?.[1] || '0');
						const numB = parseInt(b.match(/page_(\d+)\.mmd/)?.[1] || '0');
						return numA - numB;
					});
			}

			totalPages = pages.length;

			if (totalPages === 0) {
				error = '未找到 OCR 处理结果页面';
			}

			loading = false;
		} catch (e) {
			console.error('加载页面列表失败:', e);
			error = '加载页面列表失败: ' + (e instanceof Error ? e.message : String(e));
			loading = false;
		}
	};

	// 当前页面的图片 URL（响应式）
	let currentPageImageUrl = '';
	
	// 获取当前页面的图片 URL
	$: if (currentPage >= 1 && currentPage <= totalPages && pages.length > 0) {
		const pagePath = pages[currentPage - 1];
		currentPageImageUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(pagePath)}`;
		// 切换页面时重置缩放和位置
		imageScale = 1;
		imagePosition = { x: 0, y: 0 };
	} else {
		currentPageImageUrl = '';
	}

	// 图片缩放和拖拽相关状态
	let imageScale = 1;
	const minScale = 0.5;
	const maxScale = 5;
	const scaleStep = 0.25;
	
	let imagePosition = { x: 0, y: 0 };
	let isDragging = false;
	let dragStart = { x: 0, y: 0 };
	let imageContainer: HTMLDivElement;
	let imageElement: HTMLImageElement;

	// 放大
	const zoomIn = () => {
		if (imageScale < maxScale) {
			imageScale = Math.min(imageScale + scaleStep, maxScale);
		}
	};

	// 缩小
	const zoomOut = () => {
		if (imageScale > minScale) {
			imageScale = Math.max(imageScale - scaleStep, minScale);
		}
	};

	// 重置缩放和位置
	const resetZoom = () => {
		imageScale = 1;
		imagePosition = { x: 0, y: 0 };
	};

	// 鼠标滚轮缩放（按住 Ctrl 键时缩放，否则正常滚动）
	const handleWheel = (e: WheelEvent) => {
		if (e.ctrlKey || e.metaKey) {
			// 按住 Ctrl/Cmd 键时进行缩放
			e.preventDefault();
			const delta = e.deltaY > 0 ? -scaleStep : scaleStep;
			const newScale = Math.max(minScale, Math.min(maxScale, imageScale + delta));
			imageScale = newScale;
		}
		// 否则允许正常滚动
	};

	// 鼠标按下开始拖拽
	const handleMouseDown = (e: MouseEvent) => {
		// 只在图片放大时启用拖拽，且使用鼠标左键或中键
		if (imageScale > 1 && (e.button === 0 || e.button === 1)) {
			e.preventDefault(); // 阻止默认行为，避免与滚动冲突
			isDragging = true;
			dragStart = { x: e.clientX - imagePosition.x, y: e.clientY - imagePosition.y };
			if (imageContainer) {
				imageContainer.style.cursor = 'grabbing';
			}
		}
	};

	// 鼠标移动拖拽
	const handleMouseMove = (e: MouseEvent) => {
		if (isDragging && imageScale > 1) {
			e.preventDefault(); // 阻止默认行为
			imagePosition = {
				x: e.clientX - dragStart.x,
				y: e.clientY - dragStart.y
			};
		}
	};

	// 鼠标释放结束拖拽
	const handleMouseUp = () => {
		if (isDragging) {
			isDragging = false;
			if (imageContainer) {
				imageContainer.style.cursor = imageScale > 1 ? 'grab' : 'default';
			}
		}
	};

	// 获取当前页面的 Markdown 内容
	let currentPageMarkdown = '';
	let loadingMarkdown = false;

	// 响应式加载 Markdown（当页面改变时）
	$: if (currentPage >= 1 && currentPage <= totalPages && ocrTaskId && knowledgeId) {
		loadCurrentPageMarkdown();
	}

	const loadCurrentPageMarkdown = async () => {
		try {
			loadingMarkdown = true;
			const pageNum = String(currentPage).padStart(3, '0');
			const pageResultPath = `ocr_result_${ocrTaskId}/page_results/page_${pageNum}.mmd`;

			const pageResultUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(pageResultPath)}`;
			const response = await fetch(pageResultUrl, {
				headers: {
					'authorization': `Bearer ${localStorage.token}`
				}
			});

			if (response.ok) {
				let markdownContent = await response.text();
				
				// 处理图片路径：将相对路径转换为完整的 API URL
				// 匹配多种图片路径格式：
				// 1. ![](images/0_0.jpg) - 无 alt 文本
				// 2. ![alt](images/0_0.jpg) - 有 alt 文本
				// 3. ![](./images/0_0.jpg) - 相对路径
				// 4. ![](/images/0_0.jpg) - 绝对路径
				markdownContent = markdownContent.replace(
					/!\[([^\]]*)\]\((\.?\/?)(images\/[^)]+)\)/g,
					(match, alt, prefix, imagePath) => {
						// 图片路径相对于 ocr_result_{taskId} 目录
						const relativeImagePath = `ocr_result_${ocrTaskId}/${imagePath}`;
						const imageUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(relativeImagePath)}`;
						console.log(`🖼️ OCR对比视图 - 转换图片路径: ${imagePath} -> ${relativeImagePath} (URL: ${imageUrl})`);
						return `![${alt}](${imageUrl})`;
					}
				);
				
				currentPageMarkdown = markdownContent;
			} else {
				currentPageMarkdown = '*该页面暂无 OCR 处理结果*';
			}
		} catch (e) {
			console.error('加载 Markdown 失败:', e);
			currentPageMarkdown = '*加载失败*';
		} finally {
			loadingMarkdown = false;
		}
	};

	// 上一页
	const goToPreviousPage = () => {
		if (currentPage > 1) {
			currentPage--;
		}
	};

	// 下一页
	const goToNextPage = () => {
		if (currentPage < totalPages) {
			currentPage++;
		}
	};

	// 跳转到指定页
	const goToPage = (page: number) => {
		if (page >= 1 && page <= totalPages) {
			currentPage = page;
		}
	};

	// 键盘快捷键支持
	const handleKeyDown = (e: KeyboardEvent) => {
		// 如果焦点在编辑器、输入框或表格单元格内，不拦截按键
		const target = e.target as HTMLElement;
		if (target) {
			// 检查是否在编辑器内（ProseMirror编辑器）
			if (target.closest('.ProseMirror') || 
			    target.closest('[contenteditable="true"]') ||
			    target.closest('input') ||
			    target.closest('textarea') ||
			    target.closest('table') ||
			    target.closest('[role="textbox"]')) {
				return; // 不拦截，让编辑器处理
			}
		}
		
		// Ctrl/Cmd + 数字键用于缩放
		if ((e.ctrlKey || e.metaKey) && !e.shiftKey) {
			if (e.key === '0' || e.key === '=') {
				e.preventDefault();
				resetZoom();
				return;
			} else if (e.key === '+' || e.key === '=') {
				e.preventDefault();
				zoomIn();
				return;
			} else if (e.key === '-' || e.key === '_') {
				e.preventDefault();
				zoomOut();
				return;
			}
		}
		
		// 页面导航
		if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
			e.preventDefault();
			goToPreviousPage();
		} else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
			e.preventDefault();
			goToNextPage();
		}
	};

	onMount(() => {
		loadPages();
		// 添加键盘事件监听
		window.addEventListener('keydown', handleKeyDown);
		return () => {
			window.removeEventListener('keydown', handleKeyDown);
		};
	});
</script>

<div class="flex flex-col h-full w-full">
	<!-- 工具栏 -->
	<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
		<div class="flex items-center gap-4">
			<button
				class="px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				disabled={currentPage <= 1}
				on:click={goToPreviousPage}
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path>
				</svg>
			</button>
			
			<div class="flex items-center gap-2">
				<span class="text-sm text-gray-700 dark:text-gray-300">
					第 <input
						type="number"
						min="1"
						max={totalPages}
						bind:value={currentPage}
						on:change={(e) => goToPage(parseInt(e.currentTarget.value) || 1)}
						class="w-16 px-2 py-1 text-center border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
					/> 页 / 共 {totalPages} 页
				</span>
			</div>

			<button
				class="px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				disabled={currentPage >= totalPages}
				on:click={goToNextPage}
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
				</svg>
			</button>
		</div>

		<div class="text-sm text-gray-500 dark:text-gray-400">
			OCR 任务 ID: {ocrTaskId}
		</div>
	</div>

	<!-- 对比内容区域 -->
	<div class="flex-1 flex overflow-hidden">
		{#if loading}
			<div class="flex-1 flex items-center justify-center">
				<div class="text-center">
					<div class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
					<div class="text-gray-600 dark:text-gray-400">加载中...</div>
				</div>
			</div>
		{:else if error}
			<div class="flex-1 flex items-center justify-center">
				<div class="text-center text-red-600 dark:text-red-400">
					<div class="text-lg mb-2">❌</div>
					<div>{error}</div>
				</div>
			</div>
		{:else if totalPages === 0}
			<div class="flex-1 flex items-center justify-center">
				<div class="text-center text-gray-500 dark:text-gray-400">
					<div class="text-lg mb-2">📄</div>
					<div>未找到 OCR 处理结果</div>
				</div>
			</div>
		{:else}
			<!-- 左侧：原始页面图片 -->
			<div class="w-1/2 border-r border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden">
				<div class="p-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex-shrink-0 flex items-center justify-between">
					<h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">原始页面 (pages)</h3>
					<div class="flex items-center gap-2">
						<button
							class="p-1.5 bg-white dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded border border-gray-300 dark:border-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
							on:click={zoomOut}
							disabled={imageScale <= minScale}
							title="缩小 (Ctrl + -)"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7"></path>
							</svg>
						</button>
						<span class="text-xs text-gray-600 dark:text-gray-400 min-w-[3rem] text-center">
							{Math.round(imageScale * 100)}%
						</span>
						<button
							class="p-1.5 bg-white dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded border border-gray-300 dark:border-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
							on:click={zoomIn}
							disabled={imageScale >= maxScale}
							title="放大 (Ctrl + +)"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7"></path>
							</svg>
						</button>
						<button
							class="p-1.5 bg-white dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 rounded border border-gray-300 dark:border-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
							on:click={resetZoom}
							disabled={imageScale === 1 && imagePosition.x === 0 && imagePosition.y === 0}
							title="重置 (Ctrl + 0)"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
							</svg>
						</button>
					</div>
				</div>
				<!-- svelte-ignore a11y-noninteractive-element-interactions -->
				<!-- svelte-ignore a11y-no-noninteractive-tabindex -->
				<div
					bind:this={imageContainer}
					class="flex-1 overflow-y-auto overflow-x-hidden bg-gray-100 dark:bg-gray-900 relative"
					role="region"
					aria-label="PDF 页面图片查看器，支持缩放和拖拽"
					tabindex="-1"
					on:wheel={handleWheel}
					on:mousedown={handleMouseDown}
					on:mousemove={handleMouseMove}
					on:mouseup={handleMouseUp}
					on:mouseleave={handleMouseUp}
					style="cursor: {imageScale > 1 ? 'grab' : 'default'};"
				>
					{#if currentPage >= 1 && currentPage <= totalPages && currentPageImageUrl}
						{#key currentPage}
							<div
								class="w-full min-h-full flex items-start justify-center py-4"
								style="transform: translate({imagePosition.x}px, {imagePosition.y}px); transition: transform 0.1s ease-out;"
							>
								<img
									bind:this={imageElement}
									src={currentPageImageUrl}
									alt={`Page ${currentPage}`}
									class="shadow-lg select-none"
									style="width: 100%; height: auto; object-fit: contain; display: block; transform: scale({imageScale}); transform-origin: top center; transition: transform 0.2s ease-out;"
									on:error={(e) => {
										console.error('图片加载失败:', e);
									}}
									draggable="false"
								/>
							</div>
						{/key}
					{:else if currentPage >= 1 && currentPage <= totalPages}
						<div class="text-center text-gray-500 dark:text-gray-400 h-full flex items-center justify-center">
							<div>
								<div class="w-6 h-6 border-3 border-gray-400 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
								<div class="text-sm">加载图片中...</div>
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- 右侧：OCR 处理结果 Markdown -->
			<div class="w-1/2 flex flex-col overflow-hidden">
				<div class="p-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
					<h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">OCR 处理结果 (page_results)</h3>
				</div>
				<div class="flex-1 overflow-auto p-4 bg-white dark:bg-gray-800">
					{#if loadingMarkdown}
						<div class="flex items-center justify-center h-full">
							<div class="text-center">
								<div class="w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
								<div class="text-sm text-gray-500 dark:text-gray-400">加载中...</div>
							</div>
						</div>
					{:else}
						{#key currentPage}
							<Markdown
								id={`ocr-compare-${ocrTaskId}-page-${currentPage}`}
								content={currentPageMarkdown || '*该页面暂无 OCR 处理结果*'}
								done={true}
								editCodeBlock={false}
								topPadding={true}
							/>
						{/key}
					{/if}
				</div>
			</div>
		{/if}
	</div>
</div>

