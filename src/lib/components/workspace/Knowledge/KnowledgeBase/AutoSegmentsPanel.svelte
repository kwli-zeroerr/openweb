<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import {
		autoSegmentOCR,
		fetchOCRSegments,
		deleteOCRSegments,
		type SegmentManifest,
		type SegmentMeta
	} from '$lib/apis/knowledge/segments';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';

	export let knowledgeId: string | null = null;
	export let ocrTaskId: string | null = null;
	export let fileName: string = '';

	let manifest: SegmentManifest | null = null;
	let segments: SegmentMeta[] = [];
	let loading = false;
	let running = false;
	let deleting = false;
	let errorMsg: string | null = null;
	let lastLoadedKey = '';

	let maxHeadingLevel = 3;
	let sourceFile = 'result.mmd';
const sourceInputId = 'segment-source-file';
const headingLevelId = 'segment-heading-level';
const segmentContentCache = new Map<string, string>();
let showPreviewModal = false;
let previewSegment: SegmentMeta | null = null;
let previewMarkdown = '';
let previewLoading = false;
let previewError: string | null = null;

const closePreviewModal = () => {
	showPreviewModal = false;
	previewSegment = null;
	previewMarkdown = '';
	previewError = null;
};

	const getSegmentUrl = (segment: SegmentMeta) => {
		if (!knowledgeId) return '#';
		return `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(segment.file)}`;
	};

	// 转换 Markdown 中的图片路径为完整的 API URL
	const convertMarkdownImages = (markdownContent: string, taskId: string | null): string => {
		if (!taskId || !knowledgeId) return markdownContent;
		
		// 匹配 Markdown 图片语法: ![alt](path)
		// 支持多种路径格式：
		// - images/xxx.jpg (相对路径)
		// - ocr_result_{taskId}/images/xxx.jpg (完整路径)
		// - /api/v1/knowledge/... (已经是完整URL，跳过)
		const imageRegex = /!\[([^\]]*)\]\((\.?\/?)(images\/[^)]+|ocr_result_[^/]+\/images\/[^)]+)\)/gi;
		
		return markdownContent.replace(imageRegex, (match, alt, prefix, imagePath) => {
			// 如果已经是完整 URL，跳过
			if (imagePath.startsWith('http://') || imagePath.startsWith('https://') || imagePath.startsWith('/api/')) {
				return match;
			}
			
			// 处理相对路径
			let relativePath = imagePath;
			if (imagePath.startsWith('images/')) {
				relativePath = `ocr_result_${taskId}/${imagePath}`;
			}
			
			// 构建完整的 API URL
			const imageUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(relativePath)}`;
			return `![${alt}](${imageUrl})`;
		});
	};

	const loadSegments = async (silent = false) => {
		if (!knowledgeId || !ocrTaskId) return;
		loading = true;
		errorMsg = null;
		try {
			const res = await fetchOCRSegments(localStorage.token, knowledgeId, ocrTaskId);
			manifest = res.manifest;
			segments = manifest?.segments ?? [];
			if (!silent) {
				if (segments.length) {
					toast.success(`已加载 ${segments.length} 个分段`);
				} else {
					toast.info('尚未生成分段，请先点击自动分段');
				}
			}
		} catch (error) {
			console.error('加载分段失败:', error);
			const message = error instanceof Error ? error.message : String(error);
			errorMsg = message;
			if (!silent) {
				toast.error(`加载分段失败: ${message}`);
			}
			manifest = null;
			segments = [];
		} finally {
			loading = false;
		}
	};

	const triggerAutoSegment = async () => {
		if (!knowledgeId || !ocrTaskId) {
			toast.error('缺少知识库或 OCR 任务信息，无法自动分段');
			return;
		}

		running = true;
		errorMsg = null;
		try {
			const res = await autoSegmentOCR(localStorage.token, knowledgeId, {
				ocr_task_id: ocrTaskId,
				source_file: sourceFile.trim() || 'result.mmd',
				max_heading_level: maxHeadingLevel,
				overwrite: true
			});

			manifest = res.manifest;
			segments = manifest?.segments ?? [];
			toast.success(`自动分段完成，共生成 ${segments.length} 个段落`);
		} catch (error) {
			console.error('自动分段失败:', error);
			const message = error instanceof Error ? error.message : String(error);
			errorMsg = message;
			toast.error(`自动分段失败: ${message}`);
		} finally {
			running = false;
		}
	};

const copySegmentContent = async (segment: SegmentMeta) => {
		if (!knowledgeId) return;
		const url = getSegmentUrl(segment);
		try {
			const res = await fetch(url, {
				headers: {
					authorization: `Bearer ${localStorage.token}`
				}
			});
			if (!res.ok) throw new Error(await res.text());
			const text = await res.text();
			await navigator.clipboard.writeText(text);
			toast.success('段落内容已复制到剪贴板');
		} catch (error) {
			console.error('复制段落失败:', error);
			const message = error instanceof Error ? error.message : String(error);
			toast.error(`复制失败: ${message}`);
		}
	};

const viewSegment = async (segment: SegmentMeta) => {
	if (!knowledgeId) return;
	showPreviewModal = true;
	previewSegment = segment;
	previewMarkdown = '';
	previewError = null;
	const cacheKey = segment.file;
	if (segmentContentCache.has(cacheKey)) {
		previewMarkdown = segmentContentCache.get(cacheKey) ?? '';
		return;
	}
	previewLoading = true;
	try {
		const url = getSegmentUrl(segment);
		const res = await fetch(url, {
			headers: {
				authorization: `Bearer ${localStorage.token}`
			}
		});
		if (!res.ok) throw new Error(await res.text());
		const text = await res.text();
		// 转换图片路径为完整的 API URL
		const convertedText = convertMarkdownImages(text, ocrTaskId);
		segmentContentCache.set(cacheKey, convertedText);
		previewMarkdown = convertedText;
	} catch (error) {
		console.error('加载段落内容失败:', error);
		const message = error instanceof Error ? error.message : String(error);
		previewError = message;
		toast.error(`加载段落失败: ${message}`);
	} finally {
		previewLoading = false;
	}
};

const deleteAllSegments = async () => {
	if (!knowledgeId || !ocrTaskId) {
		toast.error('缺少知识库或 OCR 任务信息，无法删除');
		return;
	}

	if (!confirm('确认删除所有分段吗？此操作不可恢复。')) {
		return;
	}

	deleting = true;
	try {
		await deleteOCRSegments(localStorage.token, knowledgeId, ocrTaskId);
		segments = [];
		manifest = null;
		segmentContentCache.clear();
		toast.success('已清除所有分段');
	} catch (error) {
		console.error('删除分段失败:', error);
		const message = error instanceof Error ? error.message : String(error);
		toast.error(`删除失败: ${message}`);
	} finally {
		deleting = false;
	}
};

	onMount(() => {
		if (knowledgeId && ocrTaskId) {
			loadSegments(true);
			lastLoadedKey = `${knowledgeId}-${ocrTaskId}`;
		}
	});

	$: currentKey = knowledgeId && ocrTaskId ? `${knowledgeId}-${ocrTaskId}` : '';
	$: if (currentKey && currentKey !== lastLoadedKey) {
		lastLoadedKey = currentKey;
		loadSegments(true);
	}
</script>

<svelte:window
	on:keydown={(event) => {
		if (showPreviewModal && event.key === 'Escape') {
			event.preventDefault();
			closePreviewModal();
		}
	}}
/>

<div class="auto-segment-panel h-full flex flex-col bg-white dark:bg-gray-900">
	<div class="border-b border-gray-200 dark:border-gray-800 p-4">
		<div class="flex flex-wrap items-center gap-3">
			<div class="min-w-[220px]">
				<label class="block text-xs text-gray-500 dark:text-gray-400 mb-1" for={sourceInputId}>源文件</label>
				<input
					id={sourceInputId}
					class="w-full px-3 py-1.5 text-sm border rounded-lg bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
					bind:value={sourceFile}
					placeholder="result.mmd"
					disabled={running}
				/>
			</div>
			<div>
				<label class="block text-xs text-gray-500 dark:text-gray-400 mb-1" for={headingLevelId}>最大标题层级</label>
				<select
					id={headingLevelId}
					class="px-3 py-1.5 text-sm border rounded-lg bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
					bind:value={maxHeadingLevel}
					disabled={running}
				>
					<option value={1}># 一级标题</option>
					<option value={2}>## 二级标题</option>
					<option value={3}>### 三级标题</option>
					<option value={4}>#### 四级标题</option>
				</select>
			</div>
			<div class="flex items-end gap-2 flex-wrap">
				<button
					class="px-4 py-2 text-sm rounded-lg text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-60 disabled:cursor-not-allowed transition"
					on:click={triggerAutoSegment}
					disabled={running || !knowledgeId || !ocrTaskId}
				>
					{running ? '分段中...' : '立即自动分段'}
				</button>
				<button
					class="px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition disabled:opacity-60"
					on:click={() => loadSegments()}
					disabled={loading || running}
				>
					刷新
				</button>
				<button
					class="px-3 py-2 text-sm rounded-lg border border-red-300 text-red-600 dark:border-red-500 dark:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/30 transition disabled:opacity-60 disabled:cursor-not-allowed"
					on:click={deleteAllSegments}
					disabled={deleting || running || loading || segments.length === 0}
				>
					{deleting ? '删除中...' : '清除全部'}
				</button>
				{#if manifest?.segment_count}
					<span class="text-xs text-gray-500 dark:text-gray-400">
						上次生成：
						{new Date(manifest.created_at).toLocaleString()}
					</span>
				{/if}
			</div>
		</div>
		{#if fileName}
			<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
				文件：{fileName} {#if ocrTaskId}(OCR 任务 {ocrTaskId}){/if}
			</div>
		{/if}
	</div>

	<div class="flex-1 overflow-auto p-4">
		{#if !knowledgeId || !ocrTaskId}
			<div class="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
				<div class="text-center space-y-2">
					<div class="text-2xl">ℹ️</div>
					<div>请先选择文件并确保有对应的 OCR 任务</div>
				</div>
			</div>
		{:else if loading}
			<div class="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
				<div class="text-center space-y-2">
					<div class="w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
					<div>正在加载分段...</div>
				</div>
			</div>
		{:else if errorMsg}
			<div class="h-full flex flex-col items-center justify-center text-red-500">
				<div class="text-lg mb-2">加载失败</div>
				<div class="text-sm text-center whitespace-pre-wrap">{errorMsg}</div>
				<button
					class="mt-4 px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
					on:click={() => loadSegments()}
				>
					重试
				</button>
			</div>
		{:else if segments.length === 0}
			<div class="h-full flex flex-col items-center justify-center text-gray-500 dark:text-gray-400 space-y-3">
				<div class="text-3xl">🧩</div>
				<div class="text-sm">尚未生成自动分段，点击上方按钮即可开始</div>
			</div>
		{:else}
			<div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
				{#each segments as segment}
					<button
						type="button"
						class="p-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg flex flex-col gap-3 text-left hover:shadow-lg transition shadow-sm"
						on:click={() => viewSegment(segment)}
					>
						<div class="flex items-start justify-between gap-2">
							<div>
								<div class="text-xs text-gray-500 dark:text-gray-400">段落 #{segment.order}</div>
								<div class="text-base font-semibold text-gray-900 dark:text-gray-100 line-clamp-2">
									{segment.heading || `段落 ${segment.order}`}
								</div>
							</div>
							<span class="text-[11px] px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-200">
								H{segment.level}
							</span>
						</div>
						<p class="text-sm text-gray-600 dark:text-gray-300 line-clamp-4">
							{segment.preview || '（暂无预览）'}
						</p>
						<div class="flex items-center gap-2 flex-wrap text-xs">
							<button
								class="px-2 py-1 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition"
								on:click|stopPropagation={() => copySegmentContent(segment)}
							>
								复制内容
							</button>
						</div>
					</button>
				{/each}
			</div>
		{/if}
	</div>

	{#if showPreviewModal}
		<div
			class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
			aria-label="段落预览背景"
			role="button"
			tabindex="0"
			on:click={closePreviewModal}
			on:keydown={(event) => {
				if (event.key === 'Enter' || event.key === ' ' || event.key === 'Escape') {
					event.preventDefault();
					closePreviewModal();
				}
			}}
		>
			<div
				class="bg-white dark:bg-gray-900 rounded-xl shadow-2xl max-w-4xl w-full max-h-[85vh] flex flex-col"
				role="dialog"
				aria-modal="true"
				aria-label="段落预览"
				on:click|stopPropagation
			>
				<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-800">
					<div>
						<div class="text-xs text-gray-500 dark:text-gray-400">段落 {previewSegment?.order}</div>
						<div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
							{previewSegment?.heading || '段落预览'}
						</div>
					</div>
					<button
						class="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
						on:click={closePreviewModal}
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
				<div class="flex-1 overflow-auto p-4">
					{#if previewLoading}
						<div class="h-full flex items-center justify-center text-gray-500 dark:text-gray-400">
							<div class="text-center space-y-2">
								<div class="w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
								<div>加载段落内容...</div>
							</div>
						</div>
					{:else if previewError}
						<div class="h-full flex flex-col items-center justify-center text-red-500 text-sm text-center whitespace-pre-wrap">
							{previewError}
						</div>
					{:else if previewMarkdown}
						<div class="markdown-prose">
							<Markdown
								id={previewSegment?.id || 'segment-preview'}
								content={previewMarkdown}
								done={true}
								editCodeBlock={false}
								topPadding={true}
							/>
						</div>
					{:else}
						<div class="h-full flex items-center justify-center text-gray-500 dark:text-gray-400 text-sm">
							暂无内容
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	.auto-segment-panel {
		min-height: 0;
	}
</style>

