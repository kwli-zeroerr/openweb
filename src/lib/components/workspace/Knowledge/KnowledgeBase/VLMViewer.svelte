<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import OCREditor from './OCREditor.svelte';
	import { processPDFWithManualReview, pollTaskUntilComplete, processPDFWithOCR, processImageWithOCR, getFileContent } from '$lib/apis/ocr';
import type { OCRProgressResponse } from '$lib/apis/ocr';
import { getFileContentById } from '$lib/apis/files';
import { uploadFileToOCR } from '$lib/apis/ocr';

// OCR API 基础 URL
const OCR_API_BASE_URL = typeof window !== 'undefined' 
	? (window as any).__OCR_API_BASE_URL__ || '/ocr-api'
	: 'http://192.168.195.125:8002';
import { settings, config, models } from '$lib/stores';
import type { Model } from '$lib/stores';
	// 已删除未使用的导入：ModelSelector, generateOpenAIChatCompletion

	const encodePath = (path: string) =>
		path
			.split('/')
			.filter((segment) => segment.length > 0)
			.map((segment) => encodeURIComponent(segment))
			.join('/');

	let staticKnowledgeBaseUrl = '';
	if (typeof window !== 'undefined') {
		staticKnowledgeBaseUrl = `${window.location.origin.replace(/\/$/, '')}/knowledge-static`;
	}

	const buildStaticKnowledgeFileUrl = (knowledgeId: string, relativePath: string) => {
		if (!staticKnowledgeBaseUrl) return '';
		return `${staticKnowledgeBaseUrl}/${knowledgeId}/${encodePath(relativePath)}`;
	};

	const getKnowledgeFileDataUrl = async (relativePath: string) => {
		try {
			const fileUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(relativePath)}`;
			const resp = await fetch(fileUrl, {
				headers: {
					authorization: `Bearer ${localStorage.token}`,
				},
			});

			if (!resp.ok) {
				throw new Error(`获取文件失败: ${resp.status}`);
			}

			const blob = await resp.blob();
			return await new Promise<string>((resolve, reject) => {
				const reader = new FileReader();
				reader.onloadend = () => resolve(reader.result as string);
				reader.onerror = reject;
				reader.readAsDataURL(blob);
			});
		} catch (error) {
			console.error('获取图片 DataURL 失败:', error);
			return '';
		}
	};

	// 提取"OCR的优化结果"部分
	const extractOptimizedResult = (content: string): string | null => {
		if (!content || !content.includes('OCR的优化结果')) {
			return null;
		}

		// 尝试多种可能的标记格式
		const markers = [
			'OCR的优化结果：',
			'OCR的优化结果:',
			'OCR的优化结果',
			'## OCR的优化结果',
			'### OCR的优化结果'
		];

		let startIndex = -1;
		let markerLength = 0;

		for (const marker of markers) {
			const index = content.indexOf(marker);
			if (index !== -1) {
				startIndex = index;
				markerLength = marker.length;
				break;
			}
		}

		if (startIndex === -1) {
			return null;
		}

		// 提取标记之后的内容
		let optimizedContent = content.substring(startIndex + markerLength).trim();
		
		// 移除开头的换行符和空白
		optimizedContent = optimizedContent.replace(/^\s*[\n\r]+/, '');
		
		// 如果内容为空，返回 null
		if (!optimizedContent) {
			return null;
		}

		// 如果内容以"<"开头（可能是HTML标签或占位符），尝试找到实际内容
		if (optimizedContent.startsWith('<')) {
			// 查找第一个非HTML标签的内容
			const textMatch = optimizedContent.match(/>\s*([^<]+)/);
			if (textMatch) {
				optimizedContent = optimizedContent.substring(optimizedContent.indexOf(textMatch[0]) + 1).trim();
			}
		}

		// 移除可能的提示文本（如"在该段落结束后严禁再输出任何其他内容"）
		const endMarkers = [
			'但在该段落结束后严禁再输出任何其他内容',
			'严禁再输出任何其他内容',
			'但该段落结束后严禁再输出',
			'严禁再输出'
		];

		for (const endMarker of endMarkers) {
			const endIndex = optimizedContent.indexOf(endMarker);
			if (endIndex !== -1) {
				optimizedContent = optimizedContent.substring(0, endIndex).trim();
				break;
			}
		}

		return optimizedContent;
	};

	const listPageResultFiles = async (taskId: string): Promise<Array<{ pageNum: number; path: string }>> => {
		const pageResultsDir = `ocr_result_${taskId}/page_results`;
		try {
			const response = await fetch(
				`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files-list/${encodeURIComponent(pageResultsDir)}`,
				{
					headers: {
						authorization: `Bearer ${localStorage.token}`
					}
				}
			);
			if (response.ok) {
				const data = await response.json();
				return (data.files || [])
					.filter((file: any) => file.extension === '.mmd' && file.name.startsWith('page_'))
					.map((file: any) => {
						const match = file.name.match(/page_(\d+)\.mmd/);
						return {
							pageNum: match ? parseInt(match[1], 10) : 0,
							path: file.path
						};
					})
					.filter((file: any) => file.pageNum > 0)
					.sort((a: any, b: any) => a.pageNum - b.pageNum);
			}
		} catch (error) {
			console.warn('获取 page_results 列表失败，使用回退方案:', error);
		}

		const fallbackFiles: Array<{ pageNum: number; path: string }> = [];
		const maxPages = 500;
		let consecutiveMisses = 0;

		for (let i = 1; i <= maxPages && consecutiveMisses < 50; i++) {
			const pageNumStr = String(i).padStart(3, '0');
			const pagePath = `${pageResultsDir}/page_${pageNumStr}.mmd`;
			try {
				const headResponse = await fetch(
					`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(pagePath)}`,
					{
						method: 'HEAD',
						headers: { authorization: `Bearer ${localStorage.token}` }
					}
				);
				if (headResponse.ok) {
					fallbackFiles.push({ pageNum: i, path: pagePath });
					consecutiveMisses = 0;
				} else {
					consecutiveMisses++;
				}
			} catch (error) {
				consecutiveMisses++;
			}
		}

		return fallbackFiles;
	};

	const normalizedResultSection = (pageNum: number, body: string) => {
		const trimmedBody = body.trim();
		return `# Page ${pageNum}\n\n${trimmedBody}\n`;
	};

	const regenerateResultFromPages = async () => {
		if (!ocrTaskId || !knowledgeId) return;
		const pageFiles = await listPageResultFiles(ocrTaskId);
		if (!pageFiles.length) {
			console.warn('未找到 page_results 文件，跳过 result.mmd 重建');
			return;
		}

		const pageSplitMarker = `<--- Page Split --->`;
		const sections: string[] = [];

		for (const file of pageFiles) {
			try {
				const response = await fetch(
					`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(file.path)}`,
					{
						headers: {
							authorization: `Bearer ${localStorage.token}`
						}
					}
				);
				if (!response.ok) {
					console.warn(`读取 ${file.path} 失败: ${response.status}`);
					continue;
				}
				const content = await response.text();
				sections.push(normalizedResultSection(file.pageNum, content));
			} catch (error) {
				console.warn(`读取 ${file.path} 时发生错误:`, error);
			}
		}

		if (!sections.length) {
			console.warn('没有任何 page_results 内容，跳过 result.mmd 重建');
			return;
		}

		const resultContent = sections.join(`\n${pageSplitMarker}\n`).trim() + '\n';
		const resultPath = `ocr_result_${ocrTaskId}/result.mmd`;
		await saveKnowledgeFile(resultPath, resultContent);
		console.log(`✅ 已根据 page_results 重建 result.mmd（共 ${sections.length} 页）`);
	};

	// 保存单个页面的 人工处理结果
	const saveVLMOptimizedResult = async (pageNum: number, content: string): Promise<boolean> => {
		if (!content || !content.trim()) {
			return false;
		}

		const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
		const pageNumStr = String(pageNum).padStart(3, '0');
		const filename = `page_${pageNumStr}_vlm_opt_${timestamp}.md`;

		try {
			const response = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/vlm-optimize`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${localStorage.token}`,
				},
				body: JSON.stringify({
					filename,
					content,
				}),
			});

			if (!response.ok) {
				throw new Error(await response.text());
			}

			console.log(`✅ 已保存第 ${pageNum} 页的 人工处理结果: ${filename}`);
			return true;
		} catch (error) {
			console.error(`❌ 保存第 ${pageNum} 页的 人工处理结果失败:`, error);
			return false;
		}
	};

	// 自动保存所有页面的 人工处理结果
	const autoSaveAllVLMOptimizedResults = async (taskId: string, totalPages: number) => {
		console.log(`📦 开始自动保存所有页面的 人工处理结果，共 ${totalPages} 页`);
		vlmMessage = '正在保存优化结果...';
		
		let savedCount = 0;
		let failedCount = 0;

		for (let page = 1; page <= totalPages; page++) {
			try {
				const pageNum = String(page).padStart(3, '0');
				
				// 尝试从多个可能的路径加载 人工处理结果
				const possiblePaths = [
					`ocr_result_${taskId}/page_results/page_${pageNum}_refine.mmd`,
					`ocr_result_${taskId}/page_results/page_${pageNum}.mmd`,
					`ocr_result_${taskId}/refine.mmd`, // 整个文档 refine（如果是单页）
					`ocr_result_${taskId}/result.mmd` // 整个文档结果（如果是单页）
				];

				let markdownContent = '';
				let foundPath = '';
				for (const refinePath of possiblePaths) {
					try {
						const resultUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(refinePath)}`;
						const response = await fetch(resultUrl, {
							headers: {
								'authorization': `Bearer ${localStorage.token}`
							}
						});

						if (response.ok) {
							markdownContent = await response.text();
							foundPath = refinePath;
							console.log(`✅ 找到第 ${page} 页的 人工处理结果: ${refinePath}`);
							break;
						}
						// 404 是正常的，不记录错误（这是正常的回退行为）
					} catch (e) {
						// 网络错误等才记录，404 不记录
						if (!(e instanceof TypeError)) {
							console.warn(`⚠️ 尝试加载 ${refinePath} 时出错:`, e);
						}
						continue;
					}
				}

				if (markdownContent) {
					// 提取优化结果
					const optimizedResult = extractOptimizedResult(markdownContent);
					if (optimizedResult) {
						const success = await saveVLMOptimizedResult(page, optimizedResult);
						if (success) {
							savedCount++;
						} else {
							failedCount++;
						}
					} else {
						console.warn(`⚠️ 第 ${page} 页的 人工处理结果中未找到"OCR的优化结果"部分`);
						failedCount++;
					}
				} else {
					console.warn(`⚠️ 未找到第 ${page} 页的 人工处理结果`);
					failedCount++;
				}

				// 更新进度
				vlmProgress = Math.round((page / totalPages) * 100);
				vlmMessage = `正在保存优化结果... (${page}/${totalPages})`;
			} catch (error) {
				console.error(`❌ 处理第 ${page} 页时出错:`, error);
				failedCount++;
			}
		}

		console.log(`📦 人工处理结果保存完成: 成功 ${savedCount} 页，失败 ${failedCount} 页`);
		if (savedCount > 0) {
			toast.success(`已保存 ${savedCount} 页的 人工处理结果到 vlm_optimized 文件夹`);
		}
		if (failedCount > 0) {
			toast.warning(`${failedCount} 页的优化结果保存失败`);
		}
	};

	// 已删除 maybeSaveVLMOptimizedResult 函数（仅在已删除的聊天功能中使用）

	export let knowledgeId: string;
	export let ocrTaskId: string;
	export let selectedFile: any = null;
	export let i18n: any;

	const t = (i18n as any)?.t || ((key: string) => key);

	// 页面相关状态
	let currentPage = 1;
	let totalPages = 0;
	let pages: string[] = [];
	let pageResults: string[] = [];
	let loading = true;
	let error: string | null = null;

	// 人工处理相关状态
	let isProcessingVLM = false;
	let vlmProgress = 0;
	let vlmMessage = '';
	let vlmTaskId: string | null = null;
	
	// 自动处理相关状态
	let isAutoProcessing = false; // 是否正在自动处理
	let autoProcessProgress = 0; // 自动处理进度 (0-100)
	let autoProcessMessage = ''; // 自动处理消息
	let autoProcessedPages = new Set<number>(); // 已成功处理的页面
	let autoProcessFailedPages = new Map<number, string>(); // 处理失败的页面及原因
	let autoProcessConfig = {
		processAllPages: true, // 是否处理所有页面
		skipExisting: true, // 是否跳过已有 人工处理结果的页面
		processTablesOnly: false, // 是否只处理包含表格的页面
		processLowQualityOnly: false, // 是否只处理低质量 OCR 结果的页面
		maxConcurrent: 1, // 最大并发数（逐页处理时为 1）
		retryFailed: true, // 是否重试失败的页面
		maxRetries: 2, // 最大重试次数
		autoSave: true // 是否自动保存优化结果
	};
	let showAutoProcessConfig = false; // 是否显示配置面板

	// 加载页面列表
	const loadPages = async () => {
		try {
			loading = true;
			error = null;

			const pagesDir = `ocr_result_${ocrTaskId}/pages`;
			const pageResultsDir = `ocr_result_${ocrTaskId}/page_results`;

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
			}

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

	// 当前页面的图片 URL
	let currentPageImageUrl = '';
	$: if (currentPage >= 1 && currentPage <= totalPages && pages.length > 0) {
		const pagePath = pages[currentPage - 1];
		currentPageImageUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(pagePath)}`;
	} else {
		currentPageImageUrl = '';
	}

	// OCR 结果的 Markdown 内容
	let ocrMarkdown = '';
	let loadingOCRMarkdown = false;

	// 人工处理结果的 Markdown 内容
	let vlmMarkdown = '';
	let loadingVLMMarkdown = false;
	
	// 表格修复相关状态
	let tableImages: Array<{ name: string; url: string; index: number }> = []; // 当前页面的表格图片
	let loadingTableImages = false;
	let showTableFixModal = false; // 是否显示表格修复弹窗
	let showTableSelectDropdown = false; // 是否显示表格选择下拉菜单
	let selectedTableIndex = -1; // 当前选中的表格索引
	let originalTableContent = ''; // 原始表格内容
	let optimizedTableContent = ''; // 优化后的表格内容
	let isProcessingTable = false; // 是否正在处理表格
	let tableDiffLines: Array<{ type: 'added' | 'removed' | 'unchanged'; content: string }> = []; // diff 行数据
	let tableOptimizeStatus = ''; // 表格优化状态信息
	let tableOptimizeError = ''; // 表格优化错误信息
	let tableOptimizeProgress = ''; // 表格优化进度信息
	let tableOptimizeStreamingContent = ''; // 流式输出的内容
	let tableOptimizeDetails: {
		model?: string;
		requestTime?: number;
		responseTime?: number;
		tokensUsed?: number;
		imageSize?: string;
	} = {}; // 表格优化详细信息
	let tableProcessMode: 'ocr' | 'fix' = 'fix'; // 表格处理模式：'ocr'=OCR处理（纯文字），'fix'=表格修复（HTML）
	let renderedMarkdownTableImage: string | null = null; // 渲染的 Markdown 表格图片（DataURL）
	let editedMarkdownTableImage: string | null = null; // 编辑后的 Markdown 表格图片（带红色框标记）
	let isEditingTableImage = false; // 是否正在编辑表格图片
	let tableImageCanvas: HTMLCanvasElement | null = null; // Canvas 元素引用
	let tableImageRectangles: Array<{ x: number; y: number; width: number; height: number; description?: string }> = []; // 红色框列表（包含错误描述）
	let isDrawing = false; // 是否正在画框
	let drawingStart: { x: number; y: number } | null = null; // 画框起始点
	let currentRect: { x: number; y: number; width: number; height: number } | null = null; // 当前正在画的框
	let editingRectIndex: number | null = null; // 正在编辑描述的错误框索引
	let errorDescriptions: { [key: number]: string } = {}; // 错误描述字典（索引 -> 描述）
	
	// 页面OCR优化相关状态
	let showPageOptimizeModal = false; // 是否显示页面优化弹窗
	let originalPageContent = ''; // 原始页面内容
	let optimizedPageContent = ''; // 优化后的页面内容
	let isProcessingPage = false; // 是否正在处理页面
	let pageOptimizeStatus = ''; // 页面优化状态信息
	let pageOptimizeError = ''; // 页面优化错误信息
	let pageOptimizeProgress = ''; // 页面优化进度信息
	let pageOptimizeStreamingContent = ''; // 流式输出的内容
	let pageOptimizeDetails: {
		model?: string;
		requestTime?: number;
		responseTime?: number;
		tokensUsed?: number;
		imageSize?: string;
	} = {}; // 页面优化详细信息
	
	// 获取表格中文名称（表一、表二等）
	const getTableName = (index: number): string => {
		const tableNames = ['表一', '表二', '表三', '表四', '表五', '表六', '表七', '表八', '表九', '表十'];
		if (index < tableNames.length) {
			return tableNames[index];
		}
		return `表${index + 1}`;
	};
	
	// 人工处理模型选择（用于表格优化和页面优化）
	let selectedModels: string[] = [''];
	let hasInitializedModel = false;

// 初始化默认模型
$: if (
	!hasInitializedModel &&
	$models &&
	$models.length > 0 &&
	(selectedModels.length === 0 || (selectedModels.length === 1 && selectedModels[0] === ''))
) {
	const filteredModels = $models.filter(
		(model) => !((model?.info?.meta as Record<string, any> | undefined)?.hidden ?? false)
	);
	const availableIds = filteredModels.map((model) => model.id);

	let defaultId = '';

	// 优先使用用户设置中的模型
	const userModelIds = $settings?.models ?? [];
	if (userModelIds.length > 0) {
		const userModel = userModelIds.find((modelId: string) => availableIds.includes(modelId));
		if (userModel) {
			defaultId = userModel;
		}
	}

	// 如果没有，使用配置中的默认模型
	if (!defaultId && $config?.default_models) {
		const defaultIds = ($config.default_models ?? '')
			.split(',')
			.map((id: string) => id.trim())
			.filter(Boolean);
		const matchedId = defaultIds.find((modelId: string) => availableIds.includes(modelId));
		if (matchedId) {
			defaultId = matchedId;
		}
	}

	// 如果都没有，使用第一个可用模型
	if (!defaultId && availableIds.length > 0) {
		defaultId = availableIds[0];
	}

	if (defaultId) {
		selectedModels = [defaultId];
	}
	hasInitializedModel = true;
}

// 限制只选择一个模型
$: if (selectedModels.length > 1) {
	selectedModels = [selectedModels[0]];
}
$: if (selectedModels.length === 0) {
	selectedModels = [''];
}

// 获取当前选中的模型 ID
$: vlmModelId = selectedModels[0] || '';
$: vlmModelName = $models?.find((m) => m.id === vlmModelId)?.name || '未选择模型';

	// 已删除VLM聊天相关状态变量

	// 响应式加载 Markdown
	$: if (currentPage >= 1 && currentPage <= totalPages && ocrTaskId && knowledgeId) {
		loadCurrentPageMarkdown();
		loadTableImages(); // 同时加载表格图片
	}

	const loadCurrentPageMarkdown = async () => {
		// 加载 OCR 结果
		await loadOCRMarkdown();
		// 加载 人工处理结果
		await loadVLMMarkdown();
	};
	
	// 刷新当前页面内容
	const refreshCurrentPage = async () => {
		try {
			toast.info('正在刷新页面内容...');
			await loadCurrentPageMarkdown();
			await loadTableImages(); // 同时刷新表格图片
			toast.success('页面内容已刷新');
		} catch (e) {
			console.error('刷新页面内容失败:', e);
			toast.error(`刷新失败: ${e instanceof Error ? e.message : String(e)}`);
		}
	};
	
	// 加载当前页面的表格图片
	const loadTableImages = async () => {
		if (!ocrTaskId || !knowledgeId || currentPage < 1) {
			tableImages = [];
			return;
		}
		
		try {
			loadingTableImages = true;
			const tablesDir = `ocr_result_${ocrTaskId}/tables`;
			const listUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files-list/${encodeURIComponent(tablesDir)}`;
			
			const response = await fetch(listUrl, {
				headers: { 'authorization': `Bearer ${localStorage.token}` }
			});
			
			if (response.ok) {
				const filesData = await response.json();
				const files = filesData.files || filesData || [];
				
				// 筛选当前页面的表格图片（文件名格式：{pageNum}_{index}.jpg）
				const pageNum = currentPage;
				const pageTableImages = files
					.filter((f: any) => {
						const fileName = typeof f === 'string' ? f : (f.name || f);
						return fileName && fileName.match(new RegExp(`^${pageNum}_\\d+\\.jpg$`));
					})
					.map((f: any, index: number) => {
						const fileName = typeof f === 'string' ? f : (f.name || f);
						const filePath = `${tablesDir}/${fileName}`;
						const fileUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(filePath)}`;
						const match = fileName.match(/^(\d+)_(\d+)\.jpg$/);
						return {
							name: fileName,
							url: fileUrl,
							index: match ? parseInt(match[2]) : index
						};
					})
					.sort((a: { index: number }, b: { index: number }) => a.index - b.index);
				
				tableImages = pageTableImages;
				console.log(`📊 找到第 ${currentPage} 页的 ${pageTableImages.length} 个表格图片`);
			} else {
				tableImages = [];
			}
		} catch (e) {
			console.error('加载表格图片失败:', e);
			tableImages = [];
		} finally {
			loadingTableImages = false;
		}
	};
	
	// 从 OCR Markdown 中提取表格内容（简单方法：查找 HTML table 标签）
	const extractTableFromMarkdown = (markdown: string, tableIndex: number): string => {
		console.log(`🔍 开始提取表格，索引: ${tableIndex}`);
		console.log(`  - Markdown 长度: ${markdown?.length || 0} 字符`);
		
		if (!markdown || markdown.trim().length === 0) {
			console.warn('⚠️ Markdown 内容为空');
			return '';
		}
		
		// 查找所有 HTML table 标签
		const tableRegex = /<table[\s\S]*?<\/table>/gi;
		const tables = markdown.match(tableRegex) || [];
		
		console.log(`  - 找到 ${tables.length} 个 HTML 表格`);
		
		if (tableIndex >= 0 && tableIndex < tables.length) {
			const table = tables[tableIndex];
			console.log(`✅ 提取到第 ${tableIndex} 个 HTML 表格，长度: ${table.length} 字符`);
			console.log(`  - 表格前200字符: ${table.substring(0, 200)}`);
			return table;
		}
		
		// 如果没找到，尝试查找 Markdown 表格（支持多行）
		console.log(`🔄 未找到 HTML 表格，尝试 Markdown 表格...`);
		const markdownTableRegex = /(\|.*\|.*\|(?:\n\|.*\|.*\|)*)/gm;
		const markdownTables = markdown.match(markdownTableRegex) || [];
		
		console.log(`  - 找到 ${markdownTables.length} 个 Markdown 表格`);
		
		if (markdownTables && tableIndex < markdownTables.length) {
			const table = markdownTables[tableIndex];
			console.log(`✅ 提取到第 ${tableIndex} 个 Markdown 表格，长度: ${table.length} 字符`);
			return table;
		}
		
		console.warn(`⚠️ 未找到索引为 ${tableIndex} 的表格`);
		console.log(`  - Markdown 前500字符: ${markdown.substring(0, 500)}`);
		return '';
	};
	
	// 将 HTML 表格渲染成图片
	const renderTableToImage = async (tableHtml: string, updateProgress: boolean = true): Promise<string | null> => {
		try {
			if (updateProgress) {
				tableOptimizeProgress = '正在渲染 Markdown 表格为图片...';
			}
			
			// 动态导入 html2canvas-pro
			const { default: html2canvas } = await import('html2canvas-pro');
			
			// 创建一个临时的隐藏容器
			const container = document.createElement('div');
			container.style.position = 'absolute';
			container.style.left = '-9999px';
			container.style.top = '-9999px';
			container.style.width = '1200px'; // 设置一个合适的宽度
			container.style.padding = '20px';
			container.style.backgroundColor = '#ffffff';
			container.style.fontFamily = 'Arial, sans-serif';
			container.style.fontSize = '14px';
			container.style.lineHeight = '1.5';
			
			// 设置表格样式
			const styledTableHtml = `
				<style>
					table {
						border-collapse: collapse;
						width: 100%;
						margin: 0;
						font-size: 14px;
					}
					th, td {
						border: 1px solid #ddd;
						padding: 8px;
						text-align: left;
					}
					th {
						background-color: #f2f2f2;
						font-weight: bold;
					}
					tr:nth-child(even) {
						background-color: #f9f9f9;
					}
				</style>
				${tableHtml}
			`;
			
			container.innerHTML = styledTableHtml;
			document.body.appendChild(container);
			
			// 等待内容渲染
			await new Promise(resolve => setTimeout(resolve, 100));
			
			// 使用 html2canvas 渲染
			const canvas = await html2canvas(container, {
				useCORS: true,
				scale: 2,
				backgroundColor: '#ffffff',
				width: container.offsetWidth,
				height: container.offsetHeight,
				logging: false
			});
			
			// 获取图片的 DataURL
			const imageDataUrl = canvas.toDataURL('image/png', 0.95);
			
			// 清理临时容器
			document.body.removeChild(container);
			
			if (updateProgress) {
				tableOptimizeProgress = 'Markdown 表格图片渲染完成';
			}
			console.log('✅ Markdown 表格图片渲染成功，大小:', Math.round(imageDataUrl.length / 1024), 'KB');
			
			return imageDataUrl;
		} catch (error) {
			console.error('❌ 渲染 Markdown 表格图片失败:', error);
			if (updateProgress) {
				tableOptimizeProgress = 'Markdown 表格图片渲染失败，将仅使用原 PDF 表格图片';
			}
			return null;
		}
	};
	
	// 计算 diff（简单的行级 diff）
	const calculateDiff = (oldContent: string, newContent: string) => {
		const oldLines = oldContent.split('\n');
		const newLines = newContent.split('\n');
		const diff: Array<{ type: 'added' | 'removed' | 'unchanged'; content: string }> = [];
		
		// 简单的 LCS 算法（最长公共子序列）
		const maxLen = Math.max(oldLines.length, newLines.length);
		let oldIndex = 0;
		let newIndex = 0;
		
		while (oldIndex < oldLines.length || newIndex < newLines.length) {
			if (oldIndex < oldLines.length && newIndex < newLines.length && 
				oldLines[oldIndex].trim() === newLines[newIndex].trim()) {
				// 相同行
				diff.push({ type: 'unchanged', content: oldLines[oldIndex] });
				oldIndex++;
				newIndex++;
			} else if (newIndex < newLines.length && 
				(oldIndex >= oldLines.length || !oldLines.slice(oldIndex).some(line => line.trim() === newLines[newIndex].trim()))) {
				// 新增行
				diff.push({ type: 'added', content: newLines[newIndex] });
				newIndex++;
			} else if (oldIndex < oldLines.length) {
				// 删除行
				diff.push({ type: 'removed', content: oldLines[oldIndex] });
				oldIndex++;
			} else {
				break;
			}
		}
		
		return diff;
	};
	
	// 使用人工处理优化表格（或OCR二次处理）
	const optimizeTableWithVLM = async (tableImageUrl: string, originalContent: string) => {
		// 重置状态
		tableOptimizeStatus = '';
		tableOptimizeError = '';
		tableOptimizeProgress = '';
		tableOptimizeStreamingContent = '';
		tableOptimizeDetails = {};
		optimizedTableContent = '';
		
		try {
			isProcessingTable = true;
			tableOptimizeStatus = '初始化中...';
			tableOptimizeProgress = '正在加载表格图片...';
			
			// 确保 OCR markdown 已加载（用于渲染 markdown 表格图片）
			if (!ocrMarkdown || ocrMarkdown === '*该页面暂无 OCR 处理结果*' || ocrMarkdown === '*加载失败*') {
				tableOptimizeProgress = '正在加载 OCR Markdown 内容...';
				await loadOCRMarkdown();
			}
			
			// 获取表格图片的 DataURL
			const tableImageDataUrl = await getKnowledgeFileDataUrl(`ocr_result_${ocrTaskId}/tables/${tableImages[selectedTableIndex].name}`);
			
			if (!tableImageDataUrl) {
				throw new Error('无法加载表格图片');
			}
			
			// 记录图片大小
			const imageSizeKB = Math.round(tableImageDataUrl.length / 1024);
			tableOptimizeDetails.imageSize = `${imageSizeKB} KB`;
			tableOptimizeProgress = `图片已加载 (${imageSizeKB} KB)，准备发送请求...`;
			
			// 根据处理模式选择不同的API
			if (tableProcessMode === 'ocr') {
				// OCR处理模式：直接使用OCR图片API，不需要模型
				// OCR处理模式：使用OCR API（类似第一次OCR处理）
				try {
					tableOptimizeStatus = '上传中...';
					tableOptimizeProgress = '正在上传图片到 OCR 服务...';
					
					// 将DataURL转换为File对象
					const response = await fetch(tableImageDataUrl);
					const blob = await response.blob();
					const fileName = `table_${tableImages[selectedTableIndex].name}`;
					const file = new File([blob], fileName, { type: 'image/png' });
					
					// 上传到OCR服务
					tableOptimizeProgress = '正在上传图片...';
					const uploadResult = await uploadFileToOCR(file);
					const ocrFilePath = uploadResult.file_path;
					tableOptimizeProgress = `图片已上传，开始OCR处理...`;
					
					// 调用OCR图片API（使用第一次OCR处理的提示词，加强表格中的图片提取）
					tableOptimizeStatus = '处理中...';
					tableOptimizeProgress = '正在调用 OCR 图片 API...';
					const requestStartTime = Date.now();
					
					const taskResponse = await processImageWithOCR(ocrFilePath, {
						prompt: `<image> 
						extract the image from the table image.`,
						originalFilename: fileName,
						timeout: 600,
						maxRetries: 3
					});
					
					const taskId = taskResponse.task_id;
					tableOptimizeProgress = `OCR 任务已启动: ${taskId}，等待完成...`;
					
					// 轮询任务进度
					const result = await pollTaskUntilComplete(
						taskId,
					(progress: OCRProgressResponse) => {
						const progressPercent = progress.progress || 0;
						tableOptimizeProgress = `处理中... ${progressPercent}%`;
						const message = progress.state?.message || progress.latest_result?.message || '';
						if (message) {
							tableOptimizeStreamingContent = message;
						}
					},
						2000, // interval: 2秒
						300000, // timeout: 5分钟超时
						false // useWebSocket: 不使用WebSocket
					);
					
					const responseTime = Date.now() - requestStartTime;
					tableOptimizeDetails.responseTime = responseTime;
					
					if (!result || result.status !== 'success') {
						const errorMsg = result?.message || 'OCR 处理失败';
						tableOptimizeError = errorMsg;
						tableOptimizeStatus = '失败';
						throw new Error(errorMsg);
					}
					
					// 获取OCR结果
					tableOptimizeProgress = '正在获取OCR结果...';
					const resultDir = result.result_dir;
					if (!resultDir) {
						console.error('❌ OCR结果目录为空', result);
						throw new Error('OCR结果目录为空');
					}
					
					console.log(`📁 OCR结果目录: ${resultDir}`);
					
					// 读取OCR结果文件（使用getFileContent API）
					const ocrResultPath = `${resultDir}/result.mmd`;
					console.log(`📄 尝试读取OCR结果文件: ${ocrResultPath}`);
					
					let ocrResultText = '';
					try {
						ocrResultText = await getFileContent(ocrResultPath);
						console.log(`✅ OCR结果文件读取成功，原始长度: ${ocrResultText.length} 字符`);
						console.log(`📝 OCR结果前200字符: ${ocrResultText.substring(0, 200)}`);
					} catch (fileError: any) {
						console.error('❌ 读取OCR结果文件失败:', fileError);
						// 尝试检查是否有其他结果文件
						if (result.files && result.files.length > 0) {
							console.log(`📋 可用文件列表: ${result.files.join(', ')}`);
							// 尝试读取第一个文件
							const firstFile = result.files[0];
							if (firstFile.endsWith('.mmd') || firstFile.endsWith('.md')) {
								const altPath = `${resultDir}/${firstFile}`;
								console.log(`🔄 尝试读取备用文件: ${altPath}`);
								ocrResultText = await getFileContent(altPath);
							}
						}
						if (!ocrResultText) {
							throw new Error(`无法读取OCR结果文件: ${fileError.message}`);
						}
					}
					
					if (!ocrResultText || ocrResultText.trim().length === 0) {
						console.error('❌ OCR结果文件内容为空');
						throw new Error('OCR结果文件内容为空，请检查OCR处理是否成功');
					}
					
					// 提取纯文字内容（移除Markdown格式，但保留换行和基本结构）
					let finalContent = ocrResultText
						.replace(/#{1,6}\s+/g, '')  // 移除标题标记
						.replace(/\*\*([^*]+)\*\*/g, '$1')  // 移除粗体
						.replace(/\*([^*]+)\*/g, '$1')  // 移除斜体
						.replace(/`([^`]+)`/g, '$1')  // 移除代码标记
						.replace(/```[\s\S]*?```/g, '')  // 移除代码块
						.replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')  // 移除链接，保留文本
						.replace(/<table[\s\S]*?<\/table>/gi, '')  // 移除 HTML 表格
						.replace(/\|[\s\S]*?\|/g, '')  // 移除 Markdown 表格
						.replace(/!\[([^\]]*)\]\([^\)]+\)/g, '$1')  // 移除图片标记，保留alt文本
						.trim();
					
					console.log(`📊 清理后内容长度: ${finalContent.length} 字符`);
					console.log(`📝 清理后内容前200字符: ${finalContent.substring(0, 200)}`);
					
					if (!finalContent || finalContent.length < 10) {
						// 如果清理后内容太短，尝试使用原始内容（可能包含图片引用等）
						console.warn('⚠️ 清理后内容过短，尝试使用原始内容');
						finalContent = ocrResultText.trim();
						
						if (!finalContent || finalContent.length < 10) {
							const errorMsg = `OCR结果为空或过短（原始: ${ocrResultText.length} 字符，清理后: ${finalContent.length} 字符）`;
							console.error(`❌ ${errorMsg}`);
							tableOptimizeError = errorMsg;
							tableOptimizeStatus = '失败';
							throw new Error(errorMsg);
						}
					}
					
					tableOptimizeStatus = '成功';
					tableOptimizeProgress = `处理完成！内容长度: ${finalContent.length} 字符`;
					optimizedTableContent = finalContent;
					tableOptimizeStreamingContent = finalContent;
					
					// 计算 diff
					tableDiffLines = calculateDiff(originalTableContent, finalContent);
					
					toast.success('表格OCR处理成功！');
					return finalContent;
				} catch (ocrError: any) {
					const errorMessage = ocrError instanceof Error ? ocrError.message : String(ocrError);
					if (!tableOptimizeError) {
						tableOptimizeError = errorMessage;
						tableOptimizeStatus = '失败';
					}
					throw ocrError;
				}
			} else {
				// 表格修复模式：使用VLM API（需要模型）
				if (!selectedModels[0]) {
					toast.error('请先选择一个模型');
					return null;
				}
				
				// 检查模型是否支持多模态（vision）
				const selectedModel = $models.find((m) => m.id === selectedModels[0]);
				const isVisionCapable = (selectedModel?.info?.meta?.capabilities as any)?.vision ?? true;
				
				if (!isVisionCapable) {
					const modelName = selectedModel?.name || selectedModels[0];
					const errorMsg = `模型 ${modelName} 不支持图片输入（多模态）。表格优化需要识别图片，请选择一个支持 Vision 的模型。`;
					toast.error(errorMsg);
					tableOptimizeError = errorMsg;
					tableOptimizeStatus = '失败';
					return null;
				}
				
				tableOptimizeDetails.model = selectedModels[0];
				
				// 表格修复模式：使用VLM API
				// 先尝试渲染 OCR markdown 表格为图片
				let markdownTableImageDataUrl: string | null = null;
				if (originalContent && originalContent.trim()) {
					// 从 OCR markdown 中提取当前表格
					const extractedTable = extractTableFromMarkdown(ocrMarkdown, selectedTableIndex);
					if (extractedTable && extractedTable.trim()) {
						// 如果已经有渲染的图片，直接使用；否则重新渲染
						if (!renderedMarkdownTableImage) {
							tableOptimizeProgress = '正在渲染 OCR Markdown 表格为图片...';
							renderedMarkdownTableImage = await renderTableToImage(extractedTable);
						}
						markdownTableImageDataUrl = renderedMarkdownTableImage;
					} else {
						renderedMarkdownTableImage = null;
					}
				} else {
					renderedMarkdownTableImage = null;
				}
				
				// 如果有编辑后的图片（带红色框标记），优先使用编辑后的图片
				if (editedMarkdownTableImage && tableImageRectangles.length > 0) {
					markdownTableImageDataUrl = editedMarkdownTableImage;
					console.log(`✅ 使用编辑后的表格图片（包含 ${tableImageRectangles.length} 个错误标记）`);
				}
				
				// 构建系统提示词（精简版）
				let systemPrompt = `你是表格识别助手。参考两张图片生成准确的HTML表格：
1. 原PDF表格图片（主要参考）
2. OCR渲染图片（辅助参考，可能有错误）`;

				// 如果有红色框标记，添加简要说明
				if (editedMarkdownTableImage && tableImageRectangles.length > 0) {
					const errorList = tableImageRectangles
						.map((rect, index) => {
							if (rect.description && rect.description.trim()) {
								return `${index + 1}. ${rect.description}`;
							}
							return null;
						})
						.filter(desc => desc !== null);

					if (errorList.length > 0) {
						systemPrompt += `\n\n红色框标记的错误区域：\n${errorList.join('\n')}`;
					} else {
						systemPrompt += `\n\n红色框标记了需要修正的错误区域。`;
					}
				}

				systemPrompt += `

要求：
- 使用HTML表格格式（<table><thead><tr><th>...</th></tr></thead><tbody><tr><td>...</td></tr></tbody></table>）
- 禁止Markdown表格语法
- 以原PDF图片为准，修正OCR错误
- 保持表格结构、对齐方式与原图一致
- 使用colspan/rowspan处理合并单元格`;
				
				const userContent: any[] = [
					{ type: 'text', text: '请识别并优化以下表格。我将提供两张图片供你参考：' }
				];
				
				// 添加原 PDF 表格图片
				userContent.push({
					type: 'text',
					text: '1. 原 PDF 表格图片（主要参考）：'
				});
				userContent.push({
					type: 'image_url',
					image_url: { 
						url: tableImageDataUrl, 
						detail: 'auto'
					}
				});
				
				// 如果成功渲染了 markdown 表格图片，也添加进去
				if (markdownTableImageDataUrl) {
					let imageDescription = '2. OCR Markdown 表格渲染图片（辅助参考）：';
					if (editedMarkdownTableImage && tableImageRectangles.length > 0) {
						imageDescription = `2. OCR Markdown 表格渲染图片（辅助参考，红色框标记了 ${tableImageRectangles.length} 个错误区域，请特别关注）：`;
					}
					userContent.push({
						type: 'text',
						text: imageDescription
					});
					userContent.push({
						type: 'image_url',
						image_url: { 
							url: markdownTableImageDataUrl, 
							detail: 'auto'
						}
					});
					if (editedMarkdownTableImage && tableImageRectangles.length > 0) {
						tableOptimizeProgress = `已准备两张表格图片（包含 ${tableImageRectangles.length} 个错误标记），正在发送请求...`;
					} else {
						tableOptimizeProgress = '已准备两张表格图片，正在发送请求...';
					}
				} else {
					tableOptimizeProgress = '仅使用原 PDF 表格图片，正在发送请求...';
				}
				
				// 如果原始内容不为空，作为文本参考提供（限制长度）
				if (originalContent && originalContent.trim()) {
					userContent.push({ 
						type: 'text', 
						text: `\n原始 OCR 文本结果（仅供参考）：\n${originalContent.substring(0, 500)}`
					});
				}
				
				userContent.push({
					type: 'text',
					text: '\n请根据以上图片和文本，生成准确、完整的 HTML 表格代码。'
				});

				// 创建带超时的 AbortController
				const controller = new AbortController();
				const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 分钟超时

				try {
					tableOptimizeStatus = '请求中...';
					tableOptimizeProgress = '正在向人工处理 API 发送请求...';
					tableOptimizeStreamingContent = '';
					const requestStartTime = Date.now();
					
					const response = await fetch(`${WEBUI_BASE_URL}/api/chat/completions`, {
						method: 'POST',
						headers: {
							Authorization: `Bearer ${localStorage.token}`,
							'Content-Type': 'application/json'
						},
						body: JSON.stringify({
							model: selectedModels[0],
							messages: [
								{ role: 'system', content: systemPrompt },
								{ role: 'user', content: userContent }
							],
							temperature: 0.3, // 降低温度以提高准确性
							stream: true, // 启用流式输出
							max_tokens: 8000,  // 限制最大 token，避免过长响应
							extra_body: {
								enable_thinking: true,
								thinking_budget: 4096
							}
						}),
						signal: controller.signal
					});

				const requestTime = Date.now() - requestStartTime;
				tableOptimizeDetails.requestTime = requestTime;
				tableOptimizeProgress = `请求已发送，等待流式响应... (${Math.round(requestTime / 1000)}s)`;

				if (!response.ok) {
					const errorText = await response.text().catch(() => response.statusText);
					
					// 特殊处理 504 超时错误
					if (response.status === 504) {
						const errorMsg = '请求超时（504）。人工处理时间过长，请尝试：\n1. 使用更快的模型\n2. 降低图片精度（detail: auto）\n3. 检查网络连接';
						tableOptimizeError = errorMsg;
						tableOptimizeStatus = '失败';
						throw new Error(errorMsg);
					}
					
					const errorMsg = `API 调用失败 (${response.status}): ${errorText.substring(0, 200)}`;
					tableOptimizeError = errorMsg;
					tableOptimizeStatus = '失败';
					throw new Error(errorMsg);
				}

				// 流式处理响应
				tableOptimizeStatus = '流式处理中...';
				tableOptimizeProgress = '正在接收人工处理生成内容...';
				
				if (!response.body) {
					throw new Error('响应体为空');
				}
				
				const reader = response.body.getReader();
				const decoder = new TextDecoder('utf-8');
				let fullContent = '';
				let thinkingContent = '';
				let tokenCount = 0;
				let doneReading = false;
				
				while (!doneReading) {
					const { value, done } = await reader.read();
					if (done) break;
					
					const chunk = decoder.decode(value, { stream: true });
					const lines = chunk.split('\n');
					
					for (const rawLine of lines) {
						const line = rawLine.trim();
						if (!line || !line.startsWith('data:')) continue;
						
						const data = line.slice(5).trim();
						if (!data) continue;
						if (data === '[DONE]') {
							doneReading = true;
							break;
						}
						
						try {
							const parsed = JSON.parse(data);
							const delta = parsed?.choices?.[0]?.delta;
							if (!delta) continue;
							
							// 处理 thinking/reasoning 内容（不添加到 fullContent）
							if (delta.reasoning_content) {
								thinkingContent += delta.reasoning_content;
								tableOptimizeProgress = `思考中... (${thinkingContent.length} 字符)`;
								// 确保思考内容不会混入最终内容
								continue;
							}
							
							// 处理正常内容（只处理 content，不处理 reasoning_content）
							if (delta.content) {
								// 检查 content 中是否包含 thinking 标记（某些 API 可能把 thinking 放在 content 中）
								const contentText = delta.content;
								
								// 如果 content 看起来像 thinking 内容（包含常见的 thinking 标记），跳过
								if (contentText.includes('思考') || 
								    contentText.includes('thinking') || 
								    contentText.includes('分析') ||
								    (contentText.length < 10 && !contentText.includes('<table'))) {
									// 可能是 thinking 内容，但如果没有明确的标记，还是添加到 fullContent
									// 因为有些模型可能会在 content 中包含思考过程
								}
								
								fullContent += contentText;
								tableOptimizeStreamingContent = fullContent;
								tokenCount++;
								
								// 实时更新优化后的内容（如果已包含完整的 table 标签）
								const tableMatch = fullContent.match(/<table[\s\S]*?<\/table>/i);
								if (tableMatch) {
									optimizedTableContent = tableMatch[0];
								}
								
								tableOptimizeProgress = `接收中... (${fullContent.length} 字符)`;
							}
							
							// 处理完成和 token 使用情况
							if (parsed.choices?.[0]?.finish_reason) {
								if (parsed.usage) {
									tableOptimizeDetails.tokensUsed = parsed.usage.total_tokens || tokenCount;
								}
							}
						} catch (err) {
							console.warn('解析流式数据失败:', err, line);
						}
					}
				}
				
				clearTimeout(timeoutId);
				const responseTime = Date.now() - requestStartTime;
				tableOptimizeDetails.responseTime = responseTime;
				
				if (!fullContent || fullContent.trim().length === 0) {
					const errorMsg = '人工处理返回内容为空';
					tableOptimizeError = errorMsg;
					tableOptimizeStatus = '失败';
					throw new Error(errorMsg);
				}
				
				tableOptimizeProgress = '正在提取内容...';
				
				// 表格修复模式：提取 HTML 表格代码
				// 清理内容：移除可能的 thinking 内容标记
				let cleanedContent = fullContent;
				
				// 移除常见的 thinking 标记和内容
				cleanedContent = cleanedContent
					.replace(/<think>[\s\S]*?<\/think>/gi, '')
					.replace(/<think>[\s\S]*?<\/redacted_reasoning>/gi, '')
					.replace(/```thinking[\s\S]*?```/gi, '')
					.replace(/思考过程[：:][\s\S]*?(?=<table|$)/gi, '')
					.replace(/分析[：:][\s\S]*?(?=<table|$)/gi, '');
				
				// 提取 HTML table（优先提取表格，如果返回的内容包含其他文本）
				const tableMatch = cleanedContent.match(/<table[\s\S]*?<\/table>/i);
				let finalContent = tableMatch ? tableMatch[0] : cleanedContent.trim();
				
				// 如果提取的内容仍然包含明显的 thinking 内容，尝试更严格的提取
				if (finalContent && (
					finalContent.includes('思考') || 
					finalContent.includes('分析') ||
					finalContent.includes('我需要') ||
					(finalContent.length > 500 && !finalContent.includes('<table'))
				)) {
					// 再次尝试只提取 table 标签
					const strictTableMatch = finalContent.match(/<table[\s\S]*?<\/table>/i);
					if (strictTableMatch) {
						finalContent = strictTableMatch[0];
						console.log('⚠️ 检测到可能的 thinking 内容，已过滤，只保留表格');
					} else {
						console.warn('⚠️ 提取的内容可能包含 thinking 内容，但未找到表格标签');
					}
				}
				
				if (!finalContent || finalContent.length < 10) {
					const errorMsg = '提取的表格内容为空或过短';
					tableOptimizeError = errorMsg;
					tableOptimizeStatus = '失败';
					throw new Error(errorMsg);
				}
				
				// 验证最终内容确实是表格
				if (!finalContent.includes('<table')) {
					console.warn('⚠️ 最终内容不包含 <table> 标签，可能提取了 thinking 内容');
					// 尝试从原始 fullContent 中重新提取
					const fallbackMatch = fullContent.match(/<table[\s\S]*?<\/table>/i);
					if (fallbackMatch) {
						finalContent = fallbackMatch[0];
						console.log('✅ 从原始内容中重新提取表格成功');
					} else {
						throw new Error('无法提取有效的表格内容，可能返回的是思考过程而非表格代码');
					}
				}
				
				tableOptimizeStatus = '成功';
				tableOptimizeProgress = `处理完成！内容长度: ${finalContent.length} 字符`;
				
				// 更新优化后的内容
				optimizedTableContent = finalContent;
				tableOptimizeStreamingContent = finalContent;
				
				// 计算 diff
				tableDiffLines = calculateDiff(originalTableContent, finalContent);
				
				toast.success('表格优化成功！');
				return finalContent;
				} catch (fetchError: any) {
					clearTimeout(timeoutId);
					
					if (fetchError.name === 'AbortError') {
						const errorMsg = '请求超时（10分钟）。人工处理时间过长，请尝试使用更快的模型或降低图片精度。';
						tableOptimizeError = errorMsg;
						tableOptimizeStatus = '超时';
						throw new Error(errorMsg);
					}
					
					if (!tableOptimizeError) {
						tableOptimizeError = fetchError.message || String(fetchError);
						tableOptimizeStatus = '失败';
					}
					throw fetchError;
				}
			}
		} catch (e: unknown) {
			console.error('表格优化失败:', e);
			const errorMessage = e instanceof Error ? e.message : String(e);
			if (!tableOptimizeError) {
				tableOptimizeError = errorMessage;
				tableOptimizeStatus = '失败';
			}
			toast.error(`表格优化失败: ${errorMessage}`);
			return null;
		} finally {
			isProcessingTable = false;
			if (!tableOptimizeStatus || tableOptimizeStatus === '初始化中...' || tableOptimizeStatus === '请求中...') {
				if (tableOptimizeError) {
					tableOptimizeStatus = '失败';
				} else {
					tableOptimizeStatus = '已取消';
				}
			}
		}
	};
	
	// 使用 人工优化页面 OCR 结果
	const optimizePageWithVLM = async () => {
		if (!selectedModels[0]) {
			toast.error('请先选择一个模型');
			return null;
		}
		
		// 检查模型是否支持多模态（vision）
		const selectedModel = $models.find((m) => m.id === selectedModels[0]);
		const isVisionCapable = (selectedModel?.info?.meta?.capabilities as any)?.vision ?? true;
		
		if (!isVisionCapable) {
			const modelName = selectedModel?.name || selectedModels[0];
			const errorMsg = `模型 ${modelName} 不支持图片输入（多模态）。页面优化需要识别图片，请选择一个支持 Vision 的模型。`;
			toast.error(errorMsg);
			pageOptimizeError = errorMsg;
			pageOptimizeStatus = '失败';
			return null;
		}
		
		// 重置状态
		pageOptimizeStatus = '';
		pageOptimizeError = '';
		pageOptimizeProgress = '';
		pageOptimizeStreamingContent = '';
		pageOptimizeDetails = {};
		optimizedPageContent = '';
		
		try {
			isProcessingPage = true;
			pageOptimizeStatus = '初始化中...';
			pageOptimizeProgress = '正在加载页面图片...';
			
			// 获取页面图片的 DataURL
			const pageNum = String(currentPage).padStart(3, '0');
			const pageImagePath = `ocr_result_${ocrTaskId}/pages/page_${pageNum}.png`;
			const pageImageDataUrl = await getKnowledgeFileDataUrl(pageImagePath);
			
			if (!pageImageDataUrl) {
				throw new Error('无法加载页面图片');
			}
			
			// 记录图片大小
			const imageSizeKB = Math.round(pageImageDataUrl.length / 1024);
			pageOptimizeDetails.imageSize = `${imageSizeKB} KB`;
			pageOptimizeDetails.model = selectedModels[0];
			pageOptimizeProgress = `图片已加载 (${imageSizeKB} KB)，准备发送请求...`;
			
			// System Prompt：页面 OCR 优化（使用第一次OCR处理的提示词）
			const systemPrompt = `<image> 
<|grounding|>Convert the document to markdown format.`;

			const userContent: any[] = [
				{ type: 'text', text: '' },
				{
					type: 'image_url',
					image_url: { 
						url: pageImageDataUrl, 
						detail: 'auto'
					}
				}
			];
			
			// 如果原始内容不为空，作为参考提供（限制长度）
			if (originalPageContent && originalPageContent.trim()) {
				userContent.push({ 
					type: 'text', 
					text: `原始 OCR 结果（仅供参考，可能包含页眉页脚和格式）：\n${originalPageContent.substring(0, 1000)}`
				});
			}

			// 创建带超时的 AbortController
			const controller = new AbortController();
			const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 分钟超时

			try {
				pageOptimizeStatus = '请求中...';
				pageOptimizeProgress = '正在向人工处理 API 发送请求...';
				pageOptimizeStreamingContent = '';
				const requestStartTime = Date.now();
				
				const response = await fetch(`${WEBUI_BASE_URL}/api/chat/completions`, {
					method: 'POST',
					headers: {
						Authorization: `Bearer ${localStorage.token}`,
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({
						model: selectedModels[0],
						messages: [
							{ role: 'system', content: systemPrompt },
							{ role: 'user', content: userContent }
						],
						temperature: 0.3,
						stream: true,
						max_tokens: 16000,
						extra_body: {
							enable_thinking: true,
							thinking_budget: 4096
						}
					}),
					signal: controller.signal
				});

				const requestTime = Date.now() - requestStartTime;
				pageOptimizeDetails.requestTime = requestTime;
				pageOptimizeProgress = `请求已发送，等待流式响应... (${Math.round(requestTime / 1000)}s)`;

				if (!response.ok) {
					const errorText = await response.text().catch(() => response.statusText);
					
					if (response.status === 504) {
						const errorMsg = '请求超时（504）。人工处理时间过长，请尝试：\n1. 使用更快的模型\n2. 降低图片精度（detail: auto）\n3. 检查网络连接';
						pageOptimizeError = errorMsg;
						pageOptimizeStatus = '失败';
						throw new Error(errorMsg);
					}
					
					const errorMsg = `API 调用失败 (${response.status}): ${errorText.substring(0, 200)}`;
					pageOptimizeError = errorMsg;
					pageOptimizeStatus = '失败';
					throw new Error(errorMsg);
				}

				// 流式处理响应
				pageOptimizeStatus = '流式处理中...';
				pageOptimizeProgress = '正在接收人工处理生成内容...';
				
				if (!response.body) {
					throw new Error('响应体为空');
				}
				
				const reader = response.body.getReader();
				const decoder = new TextDecoder('utf-8');
				let fullContent = '';
				let thinkingContent = '';
				let tokenCount = 0;
				let doneReading = false;
				
				while (!doneReading) {
					const { value, done } = await reader.read();
					if (done) break;
					
					const chunk = decoder.decode(value, { stream: true });
					const lines = chunk.split('\n');
					
					for (const rawLine of lines) {
						const line = rawLine.trim();
						if (!line || !line.startsWith('data:')) continue;
						
						const data = line.slice(5).trim();
						if (!data) continue;
						if (data === '[DONE]') {
							doneReading = true;
							break;
						}
						
						try {
							const parsed = JSON.parse(data);
							const delta = parsed?.choices?.[0]?.delta;
							if (!delta) continue;
							
							// 处理 thinking/reasoning 内容（不添加到 fullContent）
							if (delta.reasoning_content) {
								thinkingContent += delta.reasoning_content;
								pageOptimizeProgress = `思考中... (${thinkingContent.length} 字符)`;
								continue;
							}
							
							// 处理正常内容
							if (delta.content) {
								fullContent += delta.content;
								pageOptimizeStreamingContent = fullContent;
								tokenCount++;
								pageOptimizeProgress = `接收中... (${fullContent.length} 字符)`;
							}
							
							// 处理完成和 token 使用情况
							if (parsed.choices?.[0]?.finish_reason) {
								if (parsed.usage) {
									pageOptimizeDetails.tokensUsed = parsed.usage.total_tokens || tokenCount;
								}
							}
						} catch (err) {
							console.warn('解析流式数据失败:', err, line);
						}
					}
				}
				
				clearTimeout(timeoutId);
				const responseTime = Date.now() - requestStartTime;
				pageOptimizeDetails.responseTime = responseTime;
				
				if (!fullContent || fullContent.trim().length === 0) {
					const errorMsg = '人工处理返回内容为空';
					pageOptimizeError = errorMsg;
					pageOptimizeStatus = '失败';
					throw new Error(errorMsg);
				}
				
				pageOptimizeStatus = '成功';
				pageOptimizeProgress = `处理完成！内容长度: ${fullContent.length} 字符`;
				
				// 更新优化后的内容
				optimizedPageContent = fullContent.trim();
				pageOptimizeStreamingContent = optimizedPageContent;
				
				toast.success('页面优化成功！');
				return optimizedPageContent;
			} catch (fetchError: any) {
				clearTimeout(timeoutId);
				
				if (fetchError.name === 'AbortError') {
					const errorMsg = '请求超时（10分钟）。人工处理时间过长，请尝试使用更快的模型或降低图片精度。';
					pageOptimizeError = errorMsg;
					pageOptimizeStatus = '超时';
					throw new Error(errorMsg);
				}
				
				if (!pageOptimizeError) {
					pageOptimizeError = fetchError.message || String(fetchError);
					pageOptimizeStatus = '失败';
				}
				throw fetchError;
			}
		} catch (e) {
			console.error('页面优化失败:', e);
			const errorMessage = e instanceof Error ? e.message : String(e);
			if (!pageOptimizeError) {
				pageOptimizeError = errorMessage;
				pageOptimizeStatus = '失败';
			}
			toast.error(`页面优化失败: ${errorMessage}`);
			return null;
		} finally {
			isProcessingPage = false;
			if (!pageOptimizeStatus || pageOptimizeStatus === '初始化中...' || pageOptimizeStatus === '请求中...') {
				if (pageOptimizeError) {
					pageOptimizeStatus = '失败';
				} else {
					pageOptimizeStatus = '已取消';
				}
			}
		}
	};
	
	// 打开页面优化弹窗
	const openPageOptimizeModal = async () => {
		if (!ocrMarkdown) {
			toast.error('当前页面没有 OCR 内容');
			return;
		}
		
		showPageOptimizeModal = true;
		
		// 重置状态
		originalPageContent = ocrMarkdown;
		optimizedPageContent = '';
		pageOptimizeStatus = '';
		pageOptimizeError = '';
		pageOptimizeProgress = '';
		pageOptimizeStreamingContent = '';
		pageOptimizeDetails = {};
	};
	
	// 应用页面优化
	const applyPageOptimize = async () => {
		if (!originalPageContent || !optimizedPageContent) {
			toast.error('无法应用优化：内容为空');
			return;
		}
		
		try {
			// 保存更新后的内容到页面结果文件
			const pageNum = String(currentPage).padStart(3, '0');
			const pageResultPath = `ocr_result_${ocrTaskId}/page_results/page_${pageNum}.mmd`;
			
			// 保存到文件
			await saveKnowledgeFile(pageResultPath, optimizedPageContent);
			
			// 同时更新 result.mmd 文件
			try {
				const resultPath = `ocr_result_${ocrTaskId}/result.mmd`;
				const resultUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(resultPath)}`;
				
				let resultContent = '';
				try {
					const resultResponse = await fetch(resultUrl, {
						headers: { 'authorization': `Bearer ${localStorage.token}` }
					});
					
					if (resultResponse.ok) {
						resultContent = await resultResponse.text();
					}
				} catch (e) {
					console.warn('读取 result.mmd 失败:', e);
				}
				
				if (resultContent) {
					// 使用页面分隔符来分割页面
					const pageSplitRegex = /<---\s*Page\s+Split\s*--->/gi;
					const pages = resultContent.split(pageSplitRegex);
					
					if (pages.length > 1) {
						const pageIndex = currentPage - 1;
						if (pageIndex >= 0 && pageIndex < pages.length) {
							pages[pageIndex] = optimizedPageContent;
							resultContent = pages.join('\n<--- Page Split --->\n');
						}
					} else {
						// 如果没有分隔符，尝试使用页面标题
						const pageTitleRegex = new RegExp(`#\\s*Page\\s+${currentPage}\\b`, 'i');
						const match = resultContent.match(pageTitleRegex);
						
						if (match) {
							const startIndex = match.index!;
							const nextPageRegex = new RegExp(`<---\\s*Page\\s+Split\\s*--->|#\\s*Page\\s+${currentPage + 1}\\b`, 'i');
							const nextMatch = resultContent.substring(startIndex + match[0].length).search(nextPageRegex);
							
							if (nextMatch !== -1) {
								const endIndex = startIndex + match[0].length + nextMatch;
								const beforePage = resultContent.substring(0, startIndex + match[0].length);
								const afterPage = resultContent.substring(endIndex);
								resultContent = beforePage + '\n\n' + optimizedPageContent + '\n\n' + afterPage;
							} else {
								const beforePage = resultContent.substring(0, startIndex + match[0].length);
								resultContent = beforePage + '\n\n' + optimizedPageContent;
							}
						}
					}
					
					await saveKnowledgeFile(resultPath, resultContent);
				}
			} catch (e) {
				console.warn('更新 result.mmd 失败，但页面文件已保存:', e);
			}
			
			// 更新本地显示
			ocrMarkdown = optimizedPageContent;
			
			toast.success('页面优化已应用并保存');
			showPageOptimizeModal = false;
			
			// 重新加载当前页面内容
			await loadOCRMarkdown();
		} catch (e) {
			console.error('应用页面优化失败:', e);
			toast.error(`应用页面优化失败: ${e instanceof Error ? e.message : String(e)}`);
		}
	};

	// 打开表格修复弹窗
	const openTableFixModal = async (tableIndex: number) => {
		if (tableIndex < 0 || tableIndex >= tableImages.length) {
			return;
		}
		
		selectedTableIndex = tableIndex;
		showTableFixModal = true;
		showTableSelectDropdown = false; // 关闭下拉菜单
		
		// 重置状态
		originalTableContent = '';
		optimizedTableContent = '';
		tableDiffLines = [];
		tableOptimizeStatus = '';
		tableOptimizeError = '';
		tableOptimizeProgress = '';
		tableOptimizeStreamingContent = '';
		tableOptimizeDetails = {};
		tableProcessMode = 'fix'; // 默认使用表格修复模式
		renderedMarkdownTableImage = null; // 重置渲染的表格图片
		
		// 确保 ocrMarkdown 已加载
		console.log(`📋 准备提取表格内容:`);
		console.log(`  - 表格索引: ${tableIndex}`);
		console.log(`  - ocrMarkdown 是否为空: ${!ocrMarkdown || ocrMarkdown.length === 0}`);
		console.log(`  - ocrMarkdown 长度: ${ocrMarkdown?.length || 0} 字符`);
		
		// 如果 ocrMarkdown 为空，先加载当前页面的内容
		if (!ocrMarkdown || ocrMarkdown.length === 0 || ocrMarkdown.includes('暂无') || ocrMarkdown.includes('加载失败')) {
			console.log(`🔄 ocrMarkdown 为空或无效，重新加载当前页面内容...`);
			await loadOCRMarkdown();
			console.log(`  - 重新加载后 ocrMarkdown 长度: ${ocrMarkdown?.length || 0} 字符`);
		}
		
		// 提取原始表格内容
		originalTableContent = extractTableFromMarkdown(ocrMarkdown, tableIndex);
		
		if (!originalTableContent || originalTableContent.length === 0) {
			console.error(`❌ 无法提取表格内容，表格索引可能不正确或 Markdown 中不包含表格`);
			console.log(`  - Markdown 前500字符: ${ocrMarkdown?.substring(0, 500) || '(空)'}`);
			toast.warning(`无法提取表格内容，请检查表格索引是否正确或页面是否包含表格`);
			renderedMarkdownTableImage = null;
		} else {
			console.log(`✅ 成功提取原始表格内容，长度: ${originalTableContent.length} 字符`);
			
			// 立即渲染 Markdown 表格图片（不更新优化进度，因为此时还没开始优化）
			try {
				renderedMarkdownTableImage = null; // 先清空，显示加载状态
				renderedMarkdownTableImage = await renderTableToImage(originalTableContent, false);
				if (renderedMarkdownTableImage) {
					console.log(`✅ Markdown 表格图片渲染成功`);
					// 初始化canvas并绘制图片
					setTimeout(() => {
						initTableImageCanvas();
					}, 100);
				}
			} catch (error) {
				console.error('❌ 渲染 Markdown 表格图片失败:', error);
				renderedMarkdownTableImage = null;
			}
		}
		
		// 重置编辑状态
		isEditingTableImage = false;
		tableImageRectangles = [];
		editedMarkdownTableImage = null;
		
		// 不自动优化，让用户手动点击优化按钮
	};
	
	// 初始化表格图片canvas
	const initTableImageCanvas = () => {
		if (!tableImageCanvas || !renderedMarkdownTableImage) return;
		
		const canvas = tableImageCanvas;
		const img = new Image();
		img.onload = () => {
			// 计算canvas尺寸（保持宽高比，最大高度500px）
			const maxHeight = 500;
			const maxWidth = canvas.parentElement?.clientWidth || 800;
			const aspectRatio = img.width / img.height;
			
			let canvasWidth = img.width;
			let canvasHeight = img.height;
			
			if (canvasHeight > maxHeight) {
				canvasHeight = maxHeight;
				canvasWidth = canvasHeight * aspectRatio;
			}
			if (canvasWidth > maxWidth) {
				canvasWidth = maxWidth;
				canvasHeight = canvasWidth / aspectRatio;
			}
			
			canvas.width = canvasWidth;
			canvas.height = canvasHeight;
			
			const ctx = canvas.getContext('2d');
			if (!ctx) return;
			
			// 绘制图片
			ctx.drawImage(img, 0, 0, canvasWidth, canvasHeight);
			
			// 绘制已有的红色框
			redrawTableImage();
		};
		img.src = renderedMarkdownTableImage;
	};
	
	// 重绘表格图片（包括红色框）
	const redrawTableImage = () => {
		if (!tableImageCanvas || !renderedMarkdownTableImage) return;
		
		const canvas = tableImageCanvas;
		const ctx = canvas.getContext('2d');
		if (!ctx) return;
		
		const img = new Image();
		img.onload = () => {
			// 重新绘制图片
			ctx.clearRect(0, 0, canvas.width, canvas.height);
			ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
			
			// 绘制所有红色框
			ctx.strokeStyle = '#ef4444'; // 红色
			ctx.lineWidth = 3;
			ctx.setLineDash([]);
			
			for (const rect of tableImageRectangles) {
				ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);
			}
			
			// 绘制当前正在画的框
			if (currentRect) {
				ctx.strokeStyle = '#ef4444';
				ctx.lineWidth = 3;
				ctx.setLineDash([5, 5]); // 虚线
				ctx.strokeRect(currentRect.x, currentRect.y, currentRect.width, currentRect.height);
			}
		};
		img.src = renderedMarkdownTableImage;
	};
	
	// 获取canvas上的坐标（考虑图片缩放）
	const getCanvasCoordinates = (e: MouseEvent): { x: number; y: number } | null => {
		if (!tableImageCanvas) return null;
		
		const rect = tableImageCanvas.getBoundingClientRect();
		const x = e.clientX - rect.left;
		const y = e.clientY - rect.top;
		
		return { x, y };
	};
	
	// 鼠标按下事件
	const handleTableImageMouseDown = (e: MouseEvent) => {
		if (!isEditingTableImage || !tableImageCanvas) return;
		
		const coords = getCanvasCoordinates(e);
		if (!coords) return;
		
		isDrawing = true;
		drawingStart = coords;
		currentRect = { x: coords.x, y: coords.y, width: 0, height: 0 };
	};
	
	// 鼠标移动事件
	const handleTableImageMouseMove = (e: MouseEvent) => {
		if (!isEditingTableImage || !isDrawing || !drawingStart || !tableImageCanvas) return;
		
		const coords = getCanvasCoordinates(e);
		if (!coords) return;
		
		// 计算矩形
		const x = Math.min(drawingStart.x, coords.x);
		const y = Math.min(drawingStart.y, coords.y);
		const width = Math.abs(coords.x - drawingStart.x);
		const height = Math.abs(coords.y - drawingStart.y);
		
		currentRect = { x, y, width, height };
		redrawTableImage();
	};
	
	// 鼠标释放事件
	const handleTableImageMouseUp = (e: MouseEvent) => {
		if (!isEditingTableImage || !isDrawing || !drawingStart || !tableImageCanvas) return;
		
		const coords = getCanvasCoordinates(e);
		if (!coords) return;
		
		// 计算矩形
		const x = Math.min(drawingStart.x, coords.x);
		const y = Math.min(drawingStart.y, coords.y);
		const width = Math.abs(coords.x - drawingStart.x);
		const height = Math.abs(coords.y - drawingStart.y);
		
		// 只有当框足够大时才保存（避免误操作）
		if (width > 10 && height > 10) {
			const newIndex = tableImageRectangles.length;
			tableImageRectangles.push({ x, y, width, height });
			// 自动弹出输入框让用户输入错误描述
			editingRectIndex = newIndex;
			errorDescriptions[newIndex] = ''; // 初始化空描述
		}
		
		isDrawing = false;
		drawingStart = null;
		currentRect = null;
		redrawTableImage();
	};
	
	// 鼠标离开事件
	const handleTableImageMouseLeave = () => {
		if (!isEditingTableImage) return;
		
		isDrawing = false;
		drawingStart = null;
		currentRect = null;
		redrawTableImage();
	};
	
	// 保存编辑后的表格图片（带红色框）
	const saveEditedTableImage = () => {
		if (!tableImageCanvas || !renderedMarkdownTableImage) {
			editedMarkdownTableImage = null;
			return;
		}
		
		// 如果没有任何标记，使用原始图片
		if (tableImageRectangles.length === 0) {
			editedMarkdownTableImage = null;
			return;
		}
		
		// 获取canvas的DataURL（已经包含了红色框）
		editedMarkdownTableImage = tableImageCanvas.toDataURL('image/png', 0.95);
		console.log(`✅ 已保存编辑后的表格图片，包含 ${tableImageRectangles.length} 个错误标记`);
	};
	
	// 重新索引错误描述（用于删除框后）
	const reindexErrorDescriptions = () => {
		const newDescriptions: { [key: number]: string } = {};
		tableImageRectangles.forEach((_, idx) => {
			if (errorDescriptions[idx] !== undefined) {
				newDescriptions[idx] = errorDescriptions[idx];
			}
		});
		errorDescriptions = newDescriptions;
	};
	
	// 确认并保存错误描述
	const confirmErrorDescription = (idx: number) => {
		if (idx === null || idx < 0 || idx >= tableImageRectangles.length) return;
		
		// 如果没有描述，删除这个框
		if (!errorDescriptions[idx] || errorDescriptions[idx].trim() === '') {
			tableImageRectangles.splice(idx, 1);
			delete errorDescriptions[idx];
			reindexErrorDescriptions();
		} else {
			// 保存描述到矩形对象
			tableImageRectangles[idx].description = errorDescriptions[idx];
		}
		editingRectIndex = null;
		redrawTableImage();
	};
	
	// 删除错误标记
	const deleteErrorMark = (idx: number) => {
		if (idx === null || idx < 0 || idx >= tableImageRectangles.length) return;
		
		tableImageRectangles.splice(idx, 1);
		delete errorDescriptions[idx];
		reindexErrorDescriptions();
		editingRectIndex = null;
		redrawTableImage();
		if (!isEditingTableImage) {
			saveEditedTableImage();
		}
	};
	
	// 点击外部关闭下拉菜单
	const handleClickOutside = (event: MouseEvent) => {
		const target = event.target as HTMLElement;
		if (!target.closest('.table-select-dropdown')) {
			showTableSelectDropdown = false;
		}
	};
	
	onMount(() => {
		document.addEventListener('click', handleClickOutside);
	});
	
	onDestroy(() => {
		document.removeEventListener('click', handleClickOutside);
	});
	
	// 应用表格修复（替换 OCR Markdown 中的表格）
	// 保存文件内容到知识库目录
	const saveKnowledgeFile = async (filePath: string, content: string): Promise<boolean> => {
		try {
			const response = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files-save`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${localStorage.token}`,
				},
				body: JSON.stringify({
					file_path: filePath,
					content: content,
				}),
			});

			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(errorText || `保存失败: ${response.status}`);
			}

			return true;
		} catch (error) {
			console.error('保存文件失败:', error);
			throw error;
		}
	};

	// 替换 Markdown 中指定索引的表格
	const replaceTableInMarkdown = (markdown: string, tableIndex: number, newTable: string): string => {
		console.log(`🔍 开始替换表格，索引: ${tableIndex}`);
		
		// 查找所有 HTML table 标签
		const tableRegex = /<table[\s\S]*?<\/table>/gi;
		let match;
		let currentIndex = 0;
		let lastIndex = 0;
		const parts: string[] = [];
		const allMatches: string[] = [];
		
		// 先收集所有匹配的表格
		while ((match = tableRegex.exec(markdown)) !== null) {
			allMatches.push(match[0]);
		}
		
		console.log(`📊 找到 ${allMatches.length} 个 HTML 表格`);
		
		// 如果找到了表格
		if (allMatches.length > 0) {
			// 重新执行正则表达式来替换
			tableRegex.lastIndex = 0; // 重置正则表达式
			while ((match = tableRegex.exec(markdown)) !== null) {
				if (currentIndex === tableIndex) {
					// 添加匹配前的文本
					parts.push(markdown.substring(lastIndex, match.index));
					// 添加新的表格内容
					parts.push(newTable);
					lastIndex = match.index + match[0].length;
					console.log(`✅ 找到并替换第 ${tableIndex} 个 HTML 表格`);
				}
				// 如果不是目标表格，继续遍历，lastIndex 会在下一次循环时更新
				currentIndex++;
			}
			
			// 添加剩余文本
			parts.push(markdown.substring(lastIndex));
			
			// 如果找到了表格并替换了，返回新内容
			if (currentIndex > tableIndex) {
				const result = parts.join('');
				console.log(`✅ HTML 表格替换成功，新内容长度: ${result.length} 字符`);
				return result;
			}
		}
		
		// 如果没找到 HTML 表格，尝试 Markdown 表格
		console.log(`🔄 未找到 HTML 表格，尝试 Markdown 表格...`);
		const markdownTableRegex = /(\|.*\|.*\|(?:\n\|.*\|.*\|)*)/gm;
		currentIndex = 0;
		lastIndex = 0;
		parts.length = 0;
		
		while ((match = markdownTableRegex.exec(markdown)) !== null) {
			if (currentIndex === tableIndex) {
				parts.push(markdown.substring(lastIndex, match.index));
				parts.push(newTable);
				lastIndex = match.index + match[0].length;
				console.log(`✅ 找到并替换第 ${tableIndex} 个 Markdown 表格`);
			}
			currentIndex++;
		}
		
		if (currentIndex > tableIndex) {
			parts.push(markdown.substring(lastIndex));
			const result = parts.join('');
			console.log(`✅ Markdown 表格替换成功，新内容长度: ${result.length} 字符`);
			return result;
		}
		
		// 如果都没找到，使用简单的替换（fallback）
		console.warn('⚠️ 无法精确定位表格，使用简单替换（基于原始内容）');
		console.log(`  - 原始表格内容长度: ${originalTableContent.length}`);
		console.log(`  - 原始表格前100字符: ${originalTableContent.substring(0, 100)}`);
		
		// 尝试使用原始内容进行替换
		if (markdown.includes(originalTableContent)) {
			const result = markdown.replace(originalTableContent, optimizedTableContent);
			console.log(`✅ 使用原始内容替换成功`);
			return result;
		} else {
			console.error('❌ 无法找到原始表格内容，替换失败');
			// 如果还是找不到，直接追加新表格
			return markdown + '\n\n' + newTable;
		}
	};

	const applyTableFix = async () => {
		if (!originalTableContent || !optimizedTableContent) {
			toast.error('无法应用修复：内容为空');
			return;
		}
		
		try {
			console.log(`🔧 开始应用表格修复:`);
			console.log(`  - 表格索引: ${selectedTableIndex}`);
			console.log(`  - 原始表格长度: ${originalTableContent.length} 字符`);
			console.log(`  - 优化后表格长度: ${optimizedTableContent.length} 字符`);
			console.log(`  - 原始Markdown长度: ${ocrMarkdown.length} 字符`);
			
			// 在 OCR Markdown 中精确替换指定索引的表格
			const updatedMarkdown = replaceTableInMarkdown(ocrMarkdown, selectedTableIndex, optimizedTableContent);
			
			console.log(`  - 更新后Markdown长度: ${updatedMarkdown.length} 字符`);
			
			// 检查是否真的发生了变化
			if (updatedMarkdown === ocrMarkdown) {
				console.warn('⚠️ 警告：替换后内容未发生变化，可能未找到表格');
				toast.warning('警告：未检测到表格变化，请检查表格索引是否正确');
			} else {
				console.log(`✅ 表格替换成功，内容已更新`);
			}
			
			// 保存更新后的内容到页面结果文件
			const pageNum = String(currentPage).padStart(3, '0');
			const pageResultPath = `ocr_result_${ocrTaskId}/page_results/page_${pageNum}.mmd`;
			
			console.log(`💾 保存到文件: ${pageResultPath}`);
			
			// 保存到文件
			await saveKnowledgeFile(pageResultPath, updatedMarkdown);
			
			console.log(`✅ 页面文件已保存`);
			
			// 同时更新 result.mmd 文件
			// 需要读取现有的 result.mmd，然后替换对应页面的内容
			try {
				const resultPath = `ocr_result_${ocrTaskId}/result.mmd`;
				const resultUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(resultPath)}`;
				
				let resultContent = '';
				try {
					// 添加时间戳参数防止缓存
					const resultUrlWithCache = `${resultUrl}?t=${Date.now()}`;
					const resultResponse = await fetch(resultUrlWithCache, {
						headers: { 
							'authorization': `Bearer ${localStorage.token}`,
							'Cache-Control': 'no-cache',
							'Pragma': 'no-cache'
						},
						cache: 'no-store' // 禁用缓存
					});
					
					if (resultResponse.ok) {
						resultContent = await resultResponse.text();
						console.log(`✅ 读取 result.mmd 成功，长度: ${resultContent.length}`);
					} else {
						console.warn(`⚠️ result.mmd 不存在 (${resultResponse.status})，将创建新文件`);
					}
				} catch (e) {
					console.warn('⚠️ 读取 result.mmd 失败，将创建新文件:', e);
				}
				
				// 如果 result.mmd 存在，替换对应页面的内容
				if (resultContent) {
					// 使用页面分隔符来分割页面（支持多种格式）
					const pageSplitRegex = /<---\s*Page\s+Split\s*--->/gi;
					const pages = resultContent.split(pageSplitRegex);
					
					// 如果找到了页面分隔符
					if (pages.length > 1) {
						// 当前页面索引（从1开始，但数组从0开始）
						const pageIndex = currentPage - 1;
						
						if (pageIndex >= 0 && pageIndex < pages.length) {
							// 替换对应页面的内容
							pages[pageIndex] = updatedMarkdown;
							console.log(`✅ 替换 result.mmd 中第 ${currentPage} 页的内容`);
							
							// 重新合并，使用原始的分隔符格式
							resultContent = pages.join('\n<--- Page Split --->\n');
						} else {
							console.warn(`⚠️ 页面索引 ${pageIndex} 超出范围 (0-${pages.length - 1})`);
							// 如果索引超出范围，追加到末尾
							resultContent += `\n<--- Page Split --->\n${updatedMarkdown}`;
						}
					} else {
						// 如果没有找到页面分隔符，尝试使用页面标题来定位
						const pageTitleRegex = new RegExp(`#\\s*Page\\s+${currentPage}\\b`, 'i');
						const match = resultContent.match(pageTitleRegex);
						
						if (match) {
							// 找到页面标题，替换从标题到下一个分隔符或下一个页面标题之间的内容
							const startIndex = match.index!;
							const nextPageRegex = new RegExp(`<---\\s*Page\\s+Split\\s*--->|#\\s*Page\\s+${currentPage + 1}\\b`, 'i');
							const nextMatch = resultContent.substring(startIndex + match[0].length).search(nextPageRegex);
							
							if (nextMatch !== -1) {
								const endIndex = startIndex + match[0].length + nextMatch;
								const beforePage = resultContent.substring(0, startIndex + match[0].length);
								const afterPage = resultContent.substring(endIndex);
								resultContent = beforePage + '\n\n' + updatedMarkdown + '\n\n' + afterPage;
								console.log(`✅ 使用页面标题替换 result.mmd 中第 ${currentPage} 页的内容`);
							} else {
								// 如果没找到下一个分隔符，替换到文件末尾
								const beforePage = resultContent.substring(0, startIndex + match[0].length);
								resultContent = beforePage + '\n\n' + updatedMarkdown;
								console.log(`✅ 使用页面标题替换 result.mmd 中第 ${currentPage} 页的内容（到文件末尾）`);
							}
						} else {
							// 如果既没有分隔符也没有标题，直接追加
							console.warn('⚠️ 无法定位页面，将追加到 result.mmd 末尾');
							resultContent += `\n<--- Page Split --->\n# Page ${currentPage}\n\n${updatedMarkdown}`;
						}
					}
				} else {
					// 如果 result.mmd 不存在，创建新文件
					resultContent = `# Page ${currentPage}\n\n${updatedMarkdown}`;
					console.log('✅ 创建新的 result.mmd 文件');
				}
				
				// 保存更新后的 result.mmd
				await saveKnowledgeFile(resultPath, resultContent);
				console.log(`✅ result.mmd 已更新，包含表格修复`);
			} catch (e) {
				console.error('更新 result.mmd 失败，但页面文件已保存:', e);
				toast.error(`更新 result.mmd 失败: ${e instanceof Error ? e.message : String(e)}`);
			}
			
			// 更新本地显示（立即更新，确保用户看到最新内容）
			ocrMarkdown = updatedMarkdown;
			console.log(`✅ 本地显示已更新`);
			
			toast.success('表格修复已应用并保存');
			showTableFixModal = false;
			
			// 延迟重新加载，确保文件已保存（增加延迟时间，并强制刷新）
			setTimeout(async () => {
				console.log(`🔄 重新加载页面内容（强制刷新）...`);
				// 先强制更新本地显示，然后再从服务器加载
				ocrMarkdown = updatedMarkdown;
				await loadOCRMarkdown();
				// 如果重新加载的内容与更新的内容不同，使用更新的内容（避免缓存问题）
				if (ocrMarkdown !== updatedMarkdown) {
					console.warn('⚠️ 检测到缓存问题，使用本地更新的内容');
					ocrMarkdown = updatedMarkdown;
				}
				console.log(`✅ 页面内容已重新加载`);
			}, 1000); // 增加延迟到1秒，确保文件已完全保存
		} catch (e) {
			console.error('应用表格修复失败:', e);
			toast.error(`应用表格修复失败: ${e instanceof Error ? e.message : String(e)}`);
		}
	};

	// 检测页面是否需要处理
	const shouldProcessPage = async (pageNum: number): Promise<{ should: boolean; reason: string }> => {
		// 检查是否已有 人工处理结果
		if (autoProcessConfig.skipExisting) {
			const pageNumStr = String(pageNum).padStart(3, '0');
			const vlmOptimizedDir = `ocr_result_${ocrTaskId}/vlm_optimized`;
			try {
				const listUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files-list/${encodeURIComponent(vlmOptimizedDir)}`;
				const listResponse = await fetch(listUrl, {
					headers: { 'authorization': `Bearer ${localStorage.token}` }
				});
				if (listResponse.ok) {
					const filesData = await listResponse.json();
					const files = filesData.files || filesData || [];
					// 支持两种格式：文件对象数组或字符串数组
					const hasResult = files.some((f: any) => {
						const fileName = typeof f === 'string' ? f : (f.name || f);
						return fileName && fileName.includes(`page_${pageNumStr}_vlm_opt`);
					});
					if (hasResult) {
						return { should: false, reason: '已有人工处理结果' };
					}
				}
			} catch (e) {
				console.warn(`检查第 ${pageNum} 页 人工处理结果失败:`, e);
			}
		}
		
		// 检查是否只处理包含表格的页面
		if (autoProcessConfig.processTablesOnly) {
			try {
				const pageNumStr = String(pageNum).padStart(3, '0');
				const pageResultPath = `ocr_result_${ocrTaskId}/page_results/page_${pageNumStr}.mmd`;
				const pageResultUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(pageResultPath)}`;
				const response = await fetch(pageResultUrl, {
					headers: { 'authorization': `Bearer ${localStorage.token}` }
				});
				if (response.ok) {
					const content = await response.text();
					// 检测是否包含表格（HTML table 或 Markdown table）
					const hasTable = /<table|<thead|<tbody|^\|.*\|.*\|/m.test(content);
					if (!hasTable) {
						return { should: false, reason: '不包含表格' };
					}
				}
			} catch (e) {
				console.warn(`检查第 ${pageNum} 页表格失败:`, e);
			}
		}
		
		return { should: true, reason: '需要处理' };
	};
	
	// 检测 OCR 结果质量（简单启发式方法）
	const detectOCRQuality = (content: string): 'high' | 'medium' | 'low' => {
		if (!content || content.length < 50) return 'low';
		
		// 检测常见 OCR 错误指标
		const errorIndicators = [
			/\?\?\?/g, // 无法识别的字符
			/[a-zA-Z]{20,}/g, // 超长无空格单词（可能是 OCR 错误）
			/\s{5,}/g, // 多个连续空格
		];
		
		let errorCount = 0;
		errorIndicators.forEach(pattern => {
			const matches = content.match(pattern);
			if (matches) errorCount += matches.length;
		});
		
		const errorRate = errorCount / (content.length / 100); // 每 100 字符的错误数
		if (errorRate > 5) return 'low';
		if (errorRate > 2) return 'medium';
		return 'high';
	};

	const loadOCRMarkdown = async () => {
		try {
			loadingOCRMarkdown = true;
			const pageNum = String(currentPage).padStart(3, '0');
			const pageResultPath = `ocr_result_${ocrTaskId}/page_results/page_${pageNum}.mmd`;

			// 添加时间戳参数防止缓存
			const timestamp = Date.now();
			const pageResultUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(pageResultPath)}?t=${timestamp}`;
			const response = await fetch(pageResultUrl, {
				headers: {
					'authorization': `Bearer ${localStorage.token}`,
					'Cache-Control': 'no-cache',
					'Pragma': 'no-cache'
				},
				cache: 'no-store' // 禁用缓存
			});

			if (response.ok) {
				let markdownContent = await response.text();
				
				// 处理图片路径
				markdownContent = markdownContent.replace(
					/!\[([^\]]*)\]\((\.?\/?)(images\/[^)]+)\)/g,
					(match, alt, prefix, imagePath) => {
						const relativeImagePath = `ocr_result_${ocrTaskId}/${imagePath}`;
						const imageUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(relativeImagePath)}`;
						return `![${alt}](${imageUrl})`;
					}
				);
				
				ocrMarkdown = markdownContent;
			} else {
				ocrMarkdown = '*该页面暂无 OCR 处理结果*';
			}
		} catch (e) {
			console.error('加载 OCR Markdown 失败:', e);
			ocrMarkdown = '*加载失败*';
		} finally {
			loadingOCRMarkdown = false;
		}
	};

	const loadVLMMarkdown = async () => {
		// 如果没有 人工处理任务 ID，尝试使用 OCR 任务 ID（人工处理结果可能在同一个任务中）
		const taskId = vlmTaskId || ocrTaskId;
		if (!taskId) {
			vlmMarkdown = '';
			return;
		}

		try {
			loadingVLMMarkdown = true;
			const pageNum = String(currentPage).padStart(3, '0');
			
			// 人工处理结果可能的路径（按优先级）：
			// 1. 分页的 refine 结果：ocr_result_{taskId}/page_results/page_{pageNum}_refine.mmd
			// 2. 分页的普通结果（可能包含 人工处理）：ocr_result_{taskId}/page_results/page_{pageNum}.mmd
			// 3. 整个文档的 refine 结果：ocr_result_{taskId}/refine.mmd
			// 4. 整个文档的 result.mmd（如果 人工处理完成，可能包含 人工处理结果）
			
			let markdownContent = '';
			let foundPath = '';
			
			// 首先尝试从 vlm_optimized 文件夹加载最新的优化结果
			try {
				// 获取 vlm_optimized 文件夹中的文件列表
				const vlmOptimizedDir = 'vlm_optimized';
				const filesListUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files-list/${encodeURIComponent(vlmOptimizedDir)}`;
				const filesListResponse = await fetch(filesListUrl, {
					headers: {
						'authorization': `Bearer ${localStorage.token}`
					}
				});

				if (filesListResponse.ok) {
					const filesData = await filesListResponse.json();
					const files = filesData.files || [];
					
					// 查找当前页面的优化结果文件（可能有多个版本，选择最新的）
					const pageFiles = files.filter((f: any) => 
						f.name && f.name.startsWith(`page_${pageNum}_vlm_opt_`) && f.extension === '.md'
					);
					
					if (pageFiles.length > 0) {
						// 按文件名排序（最新的在后面，因为文件名包含时间戳）
						pageFiles.sort((a: any, b: any) => {
							const nameA = a.name || '';
							const nameB = b.name || '';
							return nameA.localeCompare(nameB);
						});
						
						// 使用最新的文件
						const latestFile = pageFiles[pageFiles.length - 1];
						const optimizedPath = `${vlmOptimizedDir}/${latestFile.name}`;
						
						const optimizedUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(optimizedPath)}`;
						const optimizedResponse = await fetch(optimizedUrl, {
							headers: {
								'authorization': `Bearer ${localStorage.token}`
							}
						});

					if (optimizedResponse.ok) {
						markdownContent = await optimizedResponse.text();
						console.log(`✅ 找到 人工处理结果: ${optimizedPath}`);
					}
					}
				}
			} catch (e) {
				console.error('❌ 从 vlm_optimized 加载失败:', e);
			}
			
			// 如果找到了结果，显示内容；否则显示"没结果"
			if (markdownContent) {
				vlmMarkdown = markdownContent;
			} else {
				vlmMarkdown = '*该页面暂无人工处理结果*';
				console.log(`ℹ️ 第 ${currentPage} 页在 vlm_optimized 文件夹中暂无优化结果`);
			}
		} catch (e) {
			console.error('加载人工处理 Markdown 失败:', e);
			vlmMarkdown = '*加载失败*';
		} finally {
			loadingVLMMarkdown = false;
		}
	};

	// 保存OCR结果（用于OCREditor的onSave回调）
	const saveOCRResult = async (content: string) => {
		try {
			// 保存到当前页面的page_result文件
			const pageNum = String(currentPage).padStart(3, '0');
			const pageResultPath = `ocr_result_${ocrTaskId}/page_results/page_${pageNum}.mmd`;
			
			// 保存到文件
			await saveKnowledgeFile(pageResultPath, content);
			
			try {
				await regenerateResultFromPages();
			} catch (e) {
				console.warn('重建 result.mmd 失败:', e);
			}
			
			// 同时更新 result_det.mmd 文件（保留检测信息）
			try {
				const resultDetPath = `ocr_result_${ocrTaskId}/result_det.mmd`;
				const resultDetUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(resultDetPath)}`;
				
				let resultDetContent = '';
				try {
					const resultDetUrlWithCache = `${resultDetUrl}?t=${Date.now()}`;
					const resultDetResponse = await fetch(resultDetUrlWithCache, {
						headers: { 
							'authorization': `Bearer ${localStorage.token}`,
							'Cache-Control': 'no-cache',
							'Pragma': 'no-cache'
						},
						cache: 'no-store'
					});
					
					if (resultDetResponse.ok) {
						resultDetContent = await resultDetResponse.text();
					}
				} catch (e) {
					console.warn('读取 result_det.mmd 失败:', e);
				}
				
				// 如果 result_det.mmd 存在，智能合并：保留检测信息，更新文本内容
				if (resultDetContent) {
					console.log(`📝 开始更新 result_det.mmd，当前页面: ${currentPage}`);
					
					const pageSeparator = `# Page ${currentPage}`;
					const nextPageSeparator = `# Page ${currentPage + 1}`;
					const pageSplitMarker = `<--- Page Split --->`;
					
					// 查找当前页面的开始位置
					const currentPageStart = resultDetContent.indexOf(pageSeparator);
					console.log(`🔍 查找页面分隔符 "${pageSeparator}": ${currentPageStart !== -1 ? '找到' : '未找到'}`);
					
					if (currentPageStart !== -1) {
						// 找到当前页面的结束位置
						const nextPageStart = resultDetContent.indexOf(nextPageSeparator, currentPageStart);
						const pageSplitIndex = resultDetContent.indexOf(pageSplitMarker, currentPageStart);
						
						let pageEndIndex = resultDetContent.length;
						if (nextPageStart !== -1) {
							pageEndIndex = nextPageStart;
						} else if (pageSplitIndex !== -1) {
							pageEndIndex = pageSplitIndex;
						}
						
						// 提取当前页面的原始内容（包含检测信息）
						const originalPageContent = resultDetContent.substring(currentPageStart, pageEndIndex);
						console.log(`📄 原始页面内容长度: ${originalPageContent.length} 字符`);
						
						// 提取页面标题
						const pageTitleEnd = originalPageContent.indexOf('\n');
						const pageTitle = pageTitleEnd !== -1 
							? originalPageContent.substring(0, pageTitleEnd + 1)
							: pageSeparator + '\n';
						
						// 从原始内容中提取所有检测信息块
						const detInfoRegex = new RegExp('<\\|ref\\|>([^<]+)<\\|/ref\\|><\\|det\\|>(\\[\\[[^\\]]+\\]\\])<\\|/det\\|>', 'g');
						const detInfoBlocks: Array<{type: string; coords: string; fullMatch: string}> = [];
						let match;
						while ((match = detInfoRegex.exec(originalPageContent)) !== null) {
							detInfoBlocks.push({
								type: match[1].trim(),
								coords: match[2],
								fullMatch: match[0]
							});
						}
						console.log(`🔍 找到 ${detInfoBlocks.length} 个检测信息块:`, detInfoBlocks.map(b => b.type));
						
						// 从编辑后的内容中提取图片URL
						const imageUrlRegex = /(?:!\[([^\]]*)\]\(([^)]+)\)|<img[^>]+src=["']([^"']+)["'][^>]*>)/g;
						const imageUrls: string[] = [];
						let imgMatch;
						while ((imgMatch = imageUrlRegex.exec(content)) !== null) {
							const url = imgMatch[2] || imgMatch[3];
							if (url) {
								imageUrls.push(url);
							}
						}
						console.log(`🖼️ 编辑内容中包含 ${imageUrls.length} 个图片`);
						
						// 构建更新后的页面内容
						let updatedPageContent = pageTitle + '\n';
						
						// 从编辑后的内容中提取图片和表格，以便匹配检测信息
						const hasTable = content.includes('<table');
						const hasImages = imageUrls.length > 0;
						
						// 按顺序处理检测信息块，保留与编辑内容匹配的检测信息
						let imageIndex = 0;
						let tableIndex = 0;
						let textIndex = 0;
						
						for (const detBlock of detInfoBlocks) {
							if (detBlock.type === 'image' && hasImages && imageIndex < imageUrls.length) {
								// 保留图片的检测信息
								updatedPageContent += `<|ref|>image<|/ref|><|det|>${detBlock.coords}<|/det|>\n\n`;
								imageIndex++;
								console.log(`✅ 保留图片检测信息: ${detBlock.coords}`);
							} else if (detBlock.type === 'table' && hasTable && tableIndex === 0) {
								// 保留第一个表格的检测信息
								updatedPageContent += `<|ref|>table<|/ref|><|det|>${detBlock.coords}<|/det|>\n\n`;
								tableIndex++;
								console.log(`✅ 保留表格检测信息: ${detBlock.coords}`);
							} else if ((detBlock.type === 'text' || detBlock.type === 'sub_title') && textIndex === 0) {
								// 保留第一个文本/标题的检测信息作为示例
								updatedPageContent += `<|ref|>${detBlock.type}<|/ref|><|det|>${detBlock.coords}<|/det|>\n`;
								textIndex++;
								console.log(`✅ 保留文本检测信息: ${detBlock.type} - ${detBlock.coords}`);
							}
						}
						
						// 添加编辑后的内容
						let contentToAdd = content.trim();
						updatedPageContent += contentToAdd;
						
						console.log(`📝 更新后的页面内容长度: ${updatedPageContent.length} 字符`);
						
						// 构建更新后的内容
						const beforePage = resultDetContent.substring(0, currentPageStart);
						const afterPage = pageEndIndex < resultDetContent.length 
							? resultDetContent.substring(pageEndIndex)
							: '';
						
						const updatedResult = beforePage + updatedPageContent + 
							(afterPage ? '\n' + pageSplitMarker + '\n' + afterPage : '');
						
						console.log(`💾 准备保存 result_det.mmd，总长度: ${updatedResult.length} 字符`);
						await saveKnowledgeFile(resultDetPath, updatedResult);
						console.log(`✅ result_det.mmd 已保存`);
					} else {
						// 如果找不到页面，追加到文件末尾
						console.log(`⚠️ 未找到页面 ${currentPage}，追加到文件末尾`);
						const pageTitle = `# Page ${currentPage}\n`;
						const pageSplit = resultDetContent.trim() ? `\n${pageSplitMarker}\n` : '';
						await saveKnowledgeFile(resultDetPath, resultDetContent + pageSplit + pageTitle + '\n' + content.trim());
					}
				} else {
					// 如果 result_det.mmd 不存在，创建新文件（不包含检测信息）
					console.log(`⚠️ result_det.mmd 不存在，创建新文件`);
					const pageTitle = `# Page ${currentPage}\n`;
					await saveKnowledgeFile(resultDetPath, pageTitle + '\n' + content.trim());
				}
			} catch (e) {
				console.error('❌ 更新 result_det.mmd 失败:', e);
				console.error('错误详情:', e instanceof Error ? e.stack : String(e));
			}
			
			// 更新本地状态
			ocrMarkdown = content;
			toast.success('OCR 结果已保存（已更新 page_result、result.mmd 和 result_det.mmd）');
		} catch (error) {
			console.error('保存 OCR 结果失败:', error);
			toast.error(`保存 OCR 结果失败: ${error instanceof Error ? error.message : String(error)}`);
		}
	};

	// 处理 VLM
	const processWithVLM = async () => {
		if (!selectedFile) {
			toast.error('无法获取文件信息');
			return;
		}

		try {
			isProcessingVLM = true;
			vlmProgress = 0;
			vlmMessage = '正在启动人工处理...';
			vlmMarkdown = '';
			toast.info('开始人工处理');

			const fileName = selectedFile.meta?.name || selectedFile.name || 'document.pdf';
			console.log(`📥 获取文件内容: ${selectedFile.id}`);
			const fileBlob = await getFileContentById(selectedFile.id);
			
			if (!fileBlob) {
				throw new Error('无法获取文件内容');
			}

			console.log(`📤 上传文件到 OCR 服务...`);
			const file = new File([fileBlob], fileName, { type: 'application/pdf' });
			const uploadResult = await uploadFileToOCR(file);
			const ocrFilePath = uploadResult.file_path;
			console.log(`✅ 文件已上传到 OCR 服务: ${ocrFilePath}`);

			const vlmResponse = await processPDFWithManualReview(ocrFilePath, {
				vlmPrompt: `请根据 OCR 结果生成高质量 Markdown，保持文档结构和格式，确保内容准确完整。

重要表格处理规则：
1. 所有表格必须使用 HTML 格式：<table><thead><tr><th>...</th></tr></thead><tbody><tr><td>...</td></tr></tbody></table>
2. 禁止使用 Markdown 表格语法（| a | b |）
3. 表格标签内不能有空行
4. 确保每行的单元格数量一致
5. 使用 colspan 和 rowspan 处理合并单元格
6. 准确保留所有表格数据，包括数字、单位和文本
7. 对于复杂的多表头表格，使用正确的 <thead> 和 <tbody> 结构
8. 保持表格结构和对齐方式与原始图像完全一致
9. 如果表格数据不完整或模糊，在相应位置标注 [数据缺失] 或 [模糊不清]
10. 对于跨页表格，保持结构完整性
11. 特别注意表格中的数值、单位、符号等细节的准确性`,
				originalFilename: fileName
			});

			vlmTaskId = vlmResponse.task_id;
			vlmMessage = '人工处理已启动，等待完成...';
			toast.info(`人工处理任务已启动: ${vlmTaskId}`);

			const result = await pollTaskUntilComplete(
				vlmTaskId,
				(progress: OCRProgressResponse) => {
					const state = progress.state || {};
					vlmProgress = state.progress || progress.progress || 0;
					vlmMessage = state.message || progress.latest_result?.message || '处理中...';
					console.log(`📊 人工处理进度: ${vlmProgress}% - ${vlmMessage}`);
				},
				3000,
				600000
			);

			if (result && (result.state === 'completed' || result.state === 'finished')) {
				vlmProgress = 100;
				vlmMessage = '人工处理完成';
				toast.success('人工处理完成');
				
				// 重新加载当前页面的 人工处理结果
				await loadVLMMarkdown();
				
				// 自动保存所有页面的 人工处理结果
				// 优先从 人工处理结果中获取总页数，否则从 OCR 结果中获取，最后使用当前已知的总页数
				const vlmTotalPages = result.total_pages || result.processed_pages;
				const finalTotalPages = vlmTotalPages || totalPages || 1;
				
				if (finalTotalPages > 0 && vlmTaskId) {
					console.log(`📦 人工处理完成，开始自动保存 ${finalTotalPages} 页的优化结果`);
					await autoSaveAllVLMOptimizedResults(vlmTaskId, finalTotalPages);
				} else {
					console.warn(`⚠️ 无法确定总页数，跳过自动保存优化结果`);
				}
			} else {
				throw new Error('人工处理未完成');
			}
		} catch (e) {
			console.error('人工处理失败:', e);
			vlmMessage = `处理失败: ${e instanceof Error ? e.message : String(e)}`;
			toast.error(`人工处理失败: ${e instanceof Error ? e.message : String(e)}`);
		} finally {
			isProcessingVLM = false;
		}
	};

	// 自动处理单页（用于批量处理）
	const autoProcessSinglePage = async (pageNum: number, retryCount = 0): Promise<boolean> => {
		try {
			// 检查是否需要处理
			const shouldProcess = await shouldProcessPage(pageNum);
			if (!shouldProcess.should) {
				console.log(`⏭️ 跳过第 ${pageNum} 页: ${shouldProcess.reason}`);
				return true; // 返回 true 表示成功（跳过也算成功）
			}

			// 检查是否只处理低质量页面
			if (autoProcessConfig.processLowQualityOnly) {
				const pageNumStr = String(pageNum).padStart(3, '0');
				const pageResultPath = `ocr_result_${ocrTaskId}/page_results/page_${pageNumStr}.mmd`;
				const pageResultUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(pageResultPath)}`;
				const response = await fetch(pageResultUrl, {
					headers: { 'authorization': `Bearer ${localStorage.token}` }
				});
				if (response.ok) {
					const content = await response.text();
					const quality = detectOCRQuality(content);
					if (quality === 'high') {
						console.log(`⏭️ 跳过第 ${pageNum} 页: OCR 质量较高`);
						return true;
					}
				}
			}

			autoProcessMessage = `正在处理第 ${pageNum}/${totalPages} 页...`;
			
			// 获取页面 OCR 结果
			const pageNumStr = String(pageNum).padStart(3, '0');
			const pageResultPath = `ocr_result_${ocrTaskId}/page_results/page_${pageNumStr}.mmd`;
			const pageResultUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(pageResultPath)}`;
			const ocrResponse = await fetch(pageResultUrl, {
				headers: { 'authorization': `Bearer ${localStorage.token}` }
			});
			
			if (!ocrResponse.ok) {
				throw new Error(`无法加载第 ${pageNum} 页的 OCR 结果`);
			}
			
			const ocrMarkdown = await ocrResponse.text();
			
			// 获取页面图片
			const pageImageRelativePath = `ocr_result_${ocrTaskId}/pages/page_${pageNumStr}.png`;
			const pageImageDataUrl = await getKnowledgeFileDataUrl(pageImageRelativePath);
			
			if (!pageImageDataUrl) {
				throw new Error(`无法加载第 ${pageNum} 页的图片`);
			}

			// 使用 人工处理页面
			const currentModelId = selectedModels[0];
			if (!currentModelId) {
				throw new Error('未选择模型');
			}

			const systemPrompt = `你是一个专业的文档分析助手。必须结合原始页面图像与 OCR 结果生成高质量 Markdown，严格遵循以下结构：

原始页面分析：
- 描述页面布局与关键信息
- 如有必要可使用列表或小标题
- 特别关注表格结构、列数和行数

OCR的优化结果：
<在这里输出优化后的文本，严格按照PDF的图像来输出内容，但在该段落结束后严禁再输出任何其他内容或提示>

CRITICAL TABLE PROCESSING RULES:
1. 所有表格必须使用 HTML 格式：<table><thead><tr><th>...</th></tr></thead><tbody><tr><td>...</td></tr></tbody></table>
2. 禁止使用 Markdown 表格语法（| a | b |）
3. 表格标签内不能有空行
4. 确保每行的单元格数量一致
5. 使用 colspan 和 rowspan 处理合并单元格
6. 准确保留所有表格数据，包括数字、单位和文本
7. 对于复杂的多表头表格，使用正确的 <thead> 和 <tbody> 结构
8. 保持表格结构和对齐方式与图像完全一致
9. 如果表格数据不完整或模糊，在相应位置标注 [数据缺失] 或 [模糊不清]
10. 对于跨页表格，保持结构完整性`;

			const userContent: any[] = [
				{ type: 'text', text: `原始页面（第 ${pageNum} 页）` },
				{
					type: 'image_url',
					image_url: { url: pageImageDataUrl, detail: 'auto' }
				},
				{ type: 'text', text: `OCR 结果：\n${ocrMarkdown}` },
				{ type: 'text', text: '请优化并完善此页面的 Markdown 内容，确保表格格式正确、内容准确完整。' }
			];

			const response = await fetch(`${WEBUI_BASE_URL}/api/chat/completions`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.token}`,
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					model: currentModelId,
					messages: [
						{ role: 'system', content: systemPrompt },
						{ role: 'user', content: userContent }
					],
					temperature: 0.7,
					stream: false // 自动处理时使用非流式，便于获取完整结果
				})
			});

			if (!response.ok) {
				const errorText = await response.text().catch(() => response.statusText);
				throw new Error(`API 调用失败 (${response.status}): ${errorText.substring(0, 200)}`);
			}

			const result = await response.json();
			const assistantContent = result.choices?.[0]?.message?.content || '';
			
			if (!assistantContent) {
				throw new Error('人工处理返回内容为空');
			}

			// 提取优化结果
			const optimizedResult = extractOptimizedResult(assistantContent);
			if (!optimizedResult) {
				throw new Error('无法从人工处理响应中提取优化结果');
			}

			// 自动保存
			if (autoProcessConfig.autoSave) {
				const saved = await saveVLMOptimizedResult(pageNum, optimizedResult);
				if (!saved) {
					throw new Error('保存优化结果失败');
				}
			}

			autoProcessedPages.add(pageNum);
			console.log(`✅ 第 ${pageNum} 页处理完成`);
			return true;
		} catch (e) {
			const errorMsg = e instanceof Error ? e.message : String(e);
			console.error(`❌ 第 ${pageNum} 页处理失败:`, errorMsg);
			autoProcessFailedPages.set(pageNum, errorMsg);
			
			// 如果允许重试且未达到最大重试次数，则重试
			if (autoProcessConfig.retryFailed && retryCount < autoProcessConfig.maxRetries) {
				console.log(`🔄 第 ${pageNum} 页重试中 (${retryCount + 1}/${autoProcessConfig.maxRetries})...`);
				await new Promise(resolve => setTimeout(resolve, 2000)); // 等待 2 秒后重试
				return await autoProcessSinglePage(pageNum, retryCount + 1);
			}
			
			return false;
		}
	};

	// 自动处理所有页面
	const autoProcessAllPages = async () => {
		if (!totalPages || totalPages === 0) {
			toast.error('无法确定总页数');
			return;
		}

		if (!selectedModels[0]) {
			toast.error('请先选择一个模型');
			return;
		}

		if (isAutoProcessing) {
			toast.warning('自动处理正在进行中');
			return;
		}

		try {
			isAutoProcessing = true;
			autoProcessProgress = 0;
			autoProcessMessage = '正在分析需要处理的页面...';
			autoProcessedPages.clear();
			autoProcessFailedPages.clear();

			// 确定需要处理的页面列表
			const pagesToProcess: number[] = [];
			for (let page = 1; page <= totalPages; page++) {
				const shouldProcess = await shouldProcessPage(page);
				if (shouldProcess.should) {
					pagesToProcess.push(page);
				}
			}

			if (pagesToProcess.length === 0) {
				toast.info('所有页面都已处理或无需处理');
				return;
			}

			autoProcessMessage = `准备处理 ${pagesToProcess.length} 页...`;
			console.log(`📋 需要处理的页面: ${pagesToProcess.join(', ')}`);

			// 逐页处理（保持顺序，避免并发问题）
			for (let i = 0; i < pagesToProcess.length; i++) {
				const pageNum = pagesToProcess[i];
				await autoProcessSinglePage(pageNum);
				
				// 更新进度
				autoProcessProgress = Math.round(((i + 1) / pagesToProcess.length) * 100);
				autoProcessMessage = `已处理 ${i + 1}/${pagesToProcess.length} 页`;
			}

			// 处理完成
			const successCount = autoProcessedPages.size;
			const failedCount = autoProcessFailedPages.size;
			
			if (failedCount === 0) {
				toast.success(`自动处理完成！成功处理 ${successCount} 页`);
			} else {
				toast.warning(`自动处理完成：成功 ${successCount} 页，失败 ${failedCount} 页`);
				console.warn('处理失败的页面:', Array.from(autoProcessFailedPages.entries()));
			}

			// 重新加载当前页面的 人工处理结果
			await loadVLMMarkdown();
		} catch (e) {
			console.error('自动处理失败:', e);
			toast.error(`自动处理失败: ${e instanceof Error ? e.message : String(e)}`);
		} finally {
			isAutoProcessing = false;
			autoProcessMessage = '';
		}
	};

	// 页面导航
	const goToPreviousPage = () => {
		if (currentPage > 1) {
			currentPage--;
		}
	};

	const goToNextPage = () => {
		if (currentPage < totalPages) {
			currentPage++;
		}
	};

	const goToPage = (page: number) => {
		if (page >= 1 && page <= totalPages) {
			currentPage = page;
		}
	};


	// 键盘快捷键
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
		window.addEventListener('keydown', handleKeyDown);
		return () => {
			window.removeEventListener('keydown', handleKeyDown);
		};
	});
</script>

<div class="flex flex-col h-full w-full overflow-hidden" style="max-height: 100%;">
	<!-- 工具栏 -->
	<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 flex-shrink-0">
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

		<div class="flex items-center gap-4">
			{#if isProcessingVLM}
				<div class="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400">
					<div class="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
					<span>人工处理中: {vlmProgress}%</span>
					{#if vlmMessage}
						<span class="text-xs text-gray-500 dark:text-gray-400">({vlmMessage})</span>
					{/if}
				</div>
			{/if}
			
			<!-- 刷新按钮 -->
			<button
				class="px-3 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
				disabled={loadingOCRMarkdown || loadingVLMMarkdown}
				on:click={refreshCurrentPage}
				title="刷新当前页面内容"
			>
				<svg 
					class="w-4 h-4 {(loadingOCRMarkdown || loadingVLMMarkdown) ? 'animate-spin' : ''}" 
					fill="none" 
					stroke="currentColor" 
					viewBox="0 0 24 24"
				>
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
				</svg>
				<span class="text-sm">刷新</span>
			</button>
			
			<div class="text-sm text-gray-500 dark:text-gray-400">
				OCR 任务 ID: {ocrTaskId}
			</div>
		</div>
	</div>

	<!-- 三栏内容区域 -->
	<div class="flex-1 flex overflow-hidden min-h-0" style="flex: 1 1 0; min-height: 0;">
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
			<!-- 左侧：原始 PDF 图片 -->
			<div class="w-1/2 border-r border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden h-full min-h-0">
				<div class="p-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
					<h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">原始页面 (pages)</h3>
				</div>
				<div class="flex-1 overflow-y-auto overflow-x-hidden bg-gray-100 dark:bg-gray-900 min-h-0">
					{#if currentPage >= 1 && currentPage <= totalPages && currentPageImageUrl}
						{#key currentPage}
							<div class="w-full flex items-start justify-center py-4">
								<img
									src={currentPageImageUrl}
									alt={`Page ${currentPage}`}
									class="shadow-lg select-none"
									style="width: 100%; height: auto; object-fit: contain; display: block;"
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

			<!-- 中间：OCR 处理结果 Markdown -->
			<div class="w-1/2 flex flex-col overflow-hidden h-full min-h-0">
				<div class="p-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 flex-shrink-0 flex items-center justify-between">
					<div class="flex items-center gap-2">
						<button
							class="px-2 py-1 text-xs rounded bg-blue-500 hover:bg-blue-600 text-white transition-colors flex items-center gap-1"
							on:click={openPageOptimizeModal}
							title="优化当前页面的 OCR 结果"
							disabled={!ocrMarkdown || ocrMarkdown.trim().length === 0}
						>
							<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
							</svg>
							优化页面
						</button>
						{#if tableImages.length > 0}
							<div class="relative table-select-dropdown">
								<button
									class="px-2 py-1 text-xs rounded bg-green-500 hover:bg-green-600 text-white transition-colors flex items-center gap-1"
									on:click|stopPropagation={() => showTableSelectDropdown = !showTableSelectDropdown}
									title="选择要修复的表格 ({tableImages.length} 个)"
								>
									<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
									</svg>
									修复表格 ({tableImages.length})
									<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
									</svg>
								</button>
								
								{#if showTableSelectDropdown}
									<div 
										class="absolute right-0 mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50 min-w-[140px]"
										on:click|stopPropagation
									>
										<div class="py-1">
											<div class="px-3 py-2 text-xs font-medium text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
												选择表格
											</div>
											{#each tableImages as table, index}
												<button
													class="w-full px-3 py-2 text-xs text-left text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center justify-between"
													on:click={() => {
														showTableSelectDropdown = false;
														openTableFixModal(index);
													}}
												>
													<span>{getTableName(index)}</span>
													{#if index === selectedTableIndex && showTableFixModal}
														<svg class="w-3 h-3 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
															<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
														</svg>
													{/if}
												</button>
											{/each}
										</div>
									</div>
								{/if}
							</div>
						{/if}
						<h3 class="text-sm font-medium text-gray-700 dark:text-gray-300">
							OCR 处理结果
						</h3>
					</div>
				</div>
				<div class="flex-1 overflow-auto p-4 bg-white dark:bg-gray-800 min-h-0">
					{#if loadingOCRMarkdown}
						<div class="flex items-center justify-center h-full">
							<div class="text-center">
								<div class="w-6 h-6 border-3 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
								<div class="text-sm text-gray-500 dark:text-gray-400">加载中...</div>
							</div>
						</div>
					{:else}
						{#key currentPage}
							{#if ocrMarkdown && !ocrMarkdown.includes('暂无') && !ocrMarkdown.includes('加载失败') && !ocrMarkdown.startsWith('*')}
								<OCREditor
									content={ocrMarkdown}
									knowledgeId={knowledgeId}
									ocrTaskId={ocrTaskId || ''}
									currentPage={currentPage}
									onSave={saveOCRResult}
									tableImages={tableImages}
									onOpenTableFixModal={openTableFixModal}
								/>
							{:else}
								<Markdown
									id={`ocr-${ocrTaskId}-page-${currentPage}`}
									content={ocrMarkdown || '*该页面暂无 OCR 处理结果*'}
									done={true}
									editCodeBlock={false}
									topPadding={true}
								/>
							{/if}
						{/key}
					{/if}
				</div>
			</div>

		{/if}
	</div>
</div>
<!-- 表格修复弹窗 -->
{#if showTableFixModal}
	<div 
		class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" 
		role="dialog"
		aria-modal="true"
		on:click|self={() => showTableFixModal = false}
		on:keydown={(e) => e.key === 'Escape' && (showTableFixModal = false)}
	>
		<div 
			class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] flex flex-col" 
			on:click|stopPropagation
		>
			<!-- 弹窗头部 -->
			<div class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between flex-shrink-0">
				<div class="flex items-center gap-3">
					<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">
						表格修复 - {getTableName(selectedTableIndex)}
					</h3>
					{#if tableImages.length > 1}
						<div class="flex items-center gap-2">
							<select
								class="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
								value={selectedTableIndex}
								on:change={(e) => {
									const newIndex = parseInt(e.currentTarget.value);
									if (newIndex >= 0 && newIndex < tableImages.length) {
										openTableFixModal(newIndex);
									}
								}}
							>
								{#each tableImages as table, index}
									<option value={index}>{getTableName(index)}</option>
								{/each}
							</select>
							<span class="text-sm text-gray-500 dark:text-gray-400">
								({selectedTableIndex + 1} / {tableImages.length})
							</span>
						</div>
					{/if}
				</div>
				<button
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
					on:click={() => showTableFixModal = false}
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
					</svg>
				</button>
			</div>
			
			<!-- 弹窗内容 -->
			<div class="flex-1 overflow-hidden flex flex-col min-h-0">
				<!-- 表格图片 -->
				<div class="p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
					<!-- 两张表格图片并排显示，渲染图片更大 -->
					<div class="grid grid-cols-3 gap-4 mb-4">
						<!-- 原 PDF 表格图片 (占1/3) -->
						<div class="flex flex-col">
							<div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								原 PDF 表格图片
							</div>
							<div class="flex-1 border border-gray-200 dark:border-gray-700 rounded bg-gray-50 dark:bg-gray-900/50 flex items-center justify-center min-h-[300px]">
								<img
									src={tableImages[selectedTableIndex]?.url}
									alt="原 PDF 表格图片"
									class="max-w-full max-h-[400px] object-contain"
								/>
							</div>
						</div>
						<!-- OCR Markdown 表格渲染图片 (占2/3，更大) -->
						<div class="flex flex-col col-span-2">
							<div class="flex items-center justify-between mb-2">
								<div class="text-sm font-medium text-gray-700 dark:text-gray-300">
									OCR Markdown 表格渲染图片
								</div>
								{#if renderedMarkdownTableImage}
									<div class="flex items-center gap-2">
										<button
											class="px-2 py-1 text-xs rounded transition-colors {isEditingTableImage
												? 'bg-red-500 text-white'
												: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
											on:click={() => {
												isEditingTableImage = !isEditingTableImage;
												if (!isEditingTableImage) {
													// 退出编辑模式时，保存编辑后的图片
													saveEditedTableImage();
												} else {
													// 进入编辑模式时，重置画框
													tableImageRectangles = [];
													editedMarkdownTableImage = null;
													errorDescriptions = {};
													editingRectIndex = null;
												}
											}}
											title="点击进入/退出编辑模式，在图片上画红色框标记错误"
										>
											{isEditingTableImage ? '完成标记' : '标记错误'}
										</button>
										{#if isEditingTableImage}
											<button
												class="px-2 py-1 text-xs rounded bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
												on:click={() => {
													tableImageRectangles = [];
													editedMarkdownTableImage = null;
													errorDescriptions = {};
													editingRectIndex = null;
													redrawTableImage();
												}}
												title="清除所有标记"
											>
												清除标记
											</button>
										{/if}
									</div>
								{/if}
							</div>
							<div class="flex-1 border border-gray-200 dark:border-gray-700 rounded bg-gray-50 dark:bg-gray-900/50 flex items-center justify-center min-h-[300px] relative">
								{#if renderedMarkdownTableImage}
									<div class="relative w-full h-full flex items-center justify-center">
										<canvas
											bind:this={tableImageCanvas}
											class="max-w-full max-h-[500px] object-contain {isEditingTableImage ? 'cursor-crosshair' : 'cursor-default'}"
											style="touch-action: none;"
											on:mousedown={handleTableImageMouseDown}
											on:mousemove={handleTableImageMouseMove}
											on:mouseup={handleTableImageMouseUp}
											on:mouseleave={handleTableImageMouseLeave}
										></canvas>
										{#if isEditingTableImage}
											<div class="absolute top-2 left-2 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 text-xs px-2 py-1 rounded">
												编辑模式：在图片上拖拽画红色框标记错误区域
											</div>
										{/if}
										<!-- 错误描述输入框 -->
										{#if editingRectIndex !== null && tableImageRectangles[editingRectIndex]}
											{@const rect = tableImageRectangles[editingRectIndex]}
											{@const inputBoxWidth = 280}
											{@const inputBoxHeight = 150}
											{@const padding = 10}
											{@const canvasRect = tableImageCanvas?.getBoundingClientRect()}
											{@const containerRect = tableImageCanvas?.parentElement?.getBoundingClientRect()}
											{@const containerWidth = containerRect?.width || 800}
											{@const containerHeight = containerRect?.height || 600}
											{@const canvasLeft = (canvasRect && containerRect) ? (canvasRect.left - containerRect.left) : 0}
											{@const canvasTop = (canvasRect && containerRect) ? (canvasRect.top - containerRect.top) : 0}
											{@const absoluteX = canvasLeft + rect.x}
											{@const absoluteY = canvasTop + rect.y}
											{@const rightSpace = containerWidth - (absoluteX + rect.width)}
											{@const leftSpace = absoluteX}
											{@const bottomSpace = containerHeight - absoluteY}
											{@const topSpace = absoluteY}
											{@const placeRight = rightSpace >= inputBoxWidth + padding}
											{@const placeLeft = !placeRight && leftSpace >= inputBoxWidth + padding}
											{@const placeBottom = bottomSpace >= inputBoxHeight + padding}
											{@const placeTop = !placeBottom && topSpace >= inputBoxHeight + padding}
											{@const finalLeft = placeRight ? (absoluteX + rect.width + padding) : (placeLeft ? (absoluteX - inputBoxWidth - padding) : Math.max(padding, Math.min(absoluteX, containerWidth - inputBoxWidth - padding)))}
											{@const finalTop = placeBottom ? absoluteY : (placeTop ? (absoluteY - inputBoxHeight - padding) : Math.max(padding, Math.min(absoluteY, containerHeight - inputBoxHeight - padding)))}
											<div 
												class="absolute bg-white dark:bg-gray-800 border-2 border-red-500 rounded-lg shadow-lg p-3 z-50"
												style="left: {finalLeft}px; top: {finalTop}px; width: {inputBoxWidth}px; max-width: calc(100% - {padding * 2}px); max-height: calc(100% - {padding * 2}px); overflow-y: auto;"
											>
												<div class="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
													错误描述（可选）：
												</div>
												<textarea
													bind:value={errorDescriptions[editingRectIndex]}
													placeholder="请描述这个区域的错误，例如：数据识别错误、格式不对、缺少内容等..."
													class="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 resize-none focus:outline-none focus:ring-2 focus:ring-red-500"
													rows="3"
												></textarea>
												<div class="flex justify-end gap-2 mt-2">
													<button
														class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
														on:click={() => {
															if (editingRectIndex !== null) {
																confirmErrorDescription(editingRectIndex);
															}
														}}
													>
														确定
													</button>
													<button
														class="px-2 py-1 text-xs bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 text-red-700 dark:text-red-300 rounded transition-colors"
														on:click={() => {
															if (editingRectIndex !== null) {
																deleteErrorMark(editingRectIndex);
															}
														}}
													>
														删除
													</button>
												</div>
											</div>
										{/if}
									</div>
								{:else if originalTableContent && originalTableContent.length > 0}
									<div class="text-center text-gray-500 dark:text-gray-400">
										<div class="w-8 h-8 border-2 border-gray-400 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
										<div class="text-xs">正在渲染表格图片...</div>
									</div>
								{:else}
									<div class="text-center text-gray-400 dark:text-gray-500 text-sm">
										暂无表格内容
										<div class="text-xs mt-1">无法提取表格</div>
									</div>
								{/if}
							</div>
						</div>
					</div>
					<!-- 错误标记列表 -->
					{#if tableImageRectangles.length > 0 && !isEditingTableImage}
						<div class="p-4 border-b border-gray-200 dark:border-gray-700 bg-red-50 dark:bg-red-900/10">
							<div class="text-sm font-medium text-red-700 dark:text-red-300 mb-2">
								已标记的错误区域 ({tableImageRectangles.length} 个)：
							</div>
							<div class="space-y-2 max-h-40 overflow-y-auto">
								{#each tableImageRectangles as rect, index}
									<div class="flex items-start gap-2 p-2 bg-white dark:bg-gray-800 rounded border border-red-200 dark:border-red-800">
										<div class="flex-shrink-0 w-4 h-4 border-2 border-red-500 rounded mt-0.5"></div>
										<div class="flex-1 min-w-0">
											<div class="text-xs text-gray-600 dark:text-gray-400 mb-1">
												错误 #{index + 1}
											</div>
											{#if rect.description && rect.description.trim()}
												<div class="text-xs text-gray-800 dark:text-gray-200">
													{rect.description}
												</div>
											{:else}
												<div class="text-xs text-gray-400 dark:text-gray-500 italic">
													未添加描述
												</div>
											{/if}
										</div>
										<button
											class="flex-shrink-0 px-2 py-1 text-xs text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
											on:click={() => deleteErrorMark(index)}
											title="删除此标记"
										>
											删除
										</button>
									</div>
								{/each}
							</div>
						</div>
					{/if}
					<!-- 表格工具栏 -->
					<div class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-end gap-4 flex-shrink-0 bg-gray-50 dark:bg-gray-800/50">
						<div class="flex flex-col gap-2">
							<!-- 处理模式选择 -->
							<div class="flex gap-2 mb-2">
								<button
									class="px-3 py-1 text-xs rounded transition-colors {tableProcessMode === 'ocr'
										? 'bg-blue-500 text-white'
										: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
									on:click={async () => {
										tableProcessMode = 'ocr';
										optimizedTableContent = '';
										tableOptimizeStatus = '';
										tableOptimizeError = '';
										// 点击OCR处理按钮时，直接开始OCR二次处理
										await optimizeTableWithVLM(tableImages[selectedTableIndex]?.url, originalTableContent);
									}}
									title="OCR处理：输出纯文字内容，加强表格中的图片提取"
								>
									OCR处理
								</button>
								<button
									class="px-3 py-1 text-xs rounded transition-colors {tableProcessMode === 'fix'
										? 'bg-blue-500 text-white'
										: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
									on:click={() => {
										tableProcessMode = 'fix';
										optimizedTableContent = '';
										tableOptimizeStatus = '';
										tableOptimizeError = '';
									}}
									title="表格修复：输出HTML表格代码"
								>
									表格修复
								</button>
							</div>
							{#if tableImages.length > 1}
								<div class="flex gap-2">
									<button
										class="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors disabled:opacity-50"
										disabled={selectedTableIndex <= 0}
										on:click={() => {
											selectedTableIndex--;
											openTableFixModal(selectedTableIndex);
										}}
									>
										上一个
									</button>
									<button
										class="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors disabled:opacity-50"
										disabled={selectedTableIndex >= tableImages.length - 1}
										on:click={() => {
											selectedTableIndex++;
											openTableFixModal(selectedTableIndex);
										}}
									>
										下一个
									</button>
								</div>
							{/if}
							{#if !optimizedTableContent && !isProcessingTable}
								<button
									class="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors"
									on:click={() => optimizeTableWithVLM(tableImages[selectedTableIndex]?.url, originalTableContent)}
								>
									{tableProcessMode === 'ocr' ? '使用人工处理 OCR 模式处理表格' : '使用人工处理优化表格'}
								</button>
							{/if}
						</div>
					</div>
				</div>
				
				<!-- 处理状态信息 -->
				{#if isProcessingTable || tableOptimizeStatus || tableOptimizeError}
					<div class="p-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex-shrink-0">
						<div class="space-y-2">
							{#if isProcessingTable}
								<div class="flex items-center gap-2">
									<div class="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
									<span class="text-sm font-medium text-blue-600 dark:text-blue-400">{tableOptimizeStatus || '处理中...'}</span>
								</div>
							{:else if tableOptimizeStatus === '成功'}
								<div class="flex items-center gap-2">
									<svg class="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
									</svg>
									<span class="text-sm font-medium text-green-600 dark:text-green-400">{tableOptimizeStatus}</span>
								</div>
							{:else if tableOptimizeError}
								<div class="flex items-center gap-2">
									<svg class="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
									</svg>
									<span class="text-sm font-medium text-red-600 dark:text-red-400">{tableOptimizeStatus || '失败'}</span>
								</div>
							{/if}
							
							{#if tableOptimizeProgress}
								<div class="text-xs text-gray-600 dark:text-gray-400 ml-6">{tableOptimizeProgress}</div>
							{/if}
							
							{#if tableOptimizeError}
								<div class="text-xs text-red-600 dark:text-red-400 ml-6 bg-red-50 dark:bg-red-900/20 p-2 rounded border border-red-200 dark:border-red-800">
									{tableOptimizeError}
								</div>
							{/if}
							
							{#if Object.keys(tableOptimizeDetails).length > 0}
								<div class="text-xs text-gray-500 dark:text-gray-500 ml-6 space-y-1">
									{#if tableOptimizeDetails.model}
										<div>模型: <span class="font-mono">{tableOptimizeDetails.model}</span></div>
									{/if}
									{#if tableOptimizeDetails.imageSize}
										<div>图片大小: <span class="font-mono">{tableOptimizeDetails.imageSize}</span></div>
									{/if}
									{#if tableOptimizeDetails.requestTime !== undefined}
										<div>请求时间: <span class="font-mono">{Math.round(tableOptimizeDetails.requestTime / 1000)}s</span></div>
									{/if}
									{#if tableOptimizeDetails.responseTime !== undefined}
										<div>响应时间: <span class="font-mono">{Math.round(tableOptimizeDetails.responseTime / 1000)}s</span></div>
									{/if}
									{#if tableOptimizeDetails.tokensUsed}
										<div>Token 使用: <span class="font-mono">{tableOptimizeDetails.tokensUsed}</span></div>
									{/if}
								</div>
							{/if}
						</div>
					</div>
				{/if}
				
				<!-- Diff 对比区域 -->
				<div class="flex-1 overflow-hidden flex min-h-0">
					{#if isProcessingTable}
						<!-- 流式输出显示区域 -->
						<div class="flex-1 flex flex-col overflow-hidden">
							<div class="flex-1 overflow-auto p-4 bg-white dark:bg-gray-900">
								{#if tableOptimizeStreamingContent}
									<div class="space-y-2">
										<div class="text-xs text-gray-500 dark:text-gray-400 mb-2">实时生成内容：</div>
										<pre class="text-xs whitespace-pre-wrap font-mono text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700 max-h-96 overflow-auto">{tableOptimizeStreamingContent}</pre>
									</div>
								{:else}
									<div class="flex items-center justify-center h-full">
										<div class="text-center">
											<div class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
											<div class="text-sm text-gray-600 dark:text-gray-400">正在使用人工处理优化表格...</div>
											{#if tableOptimizeProgress}
												<div class="text-xs text-gray-500 dark:text-gray-500 mt-2">{tableOptimizeProgress}</div>
											{/if}
										</div>
									</div>
								{/if}
							</div>
						</div>
					{:else if optimizedTableContent}
						<!-- 左侧：原始内容 -->
						<div class="w-1/2 border-r border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden">
							<div class="p-2 bg-red-50 dark:bg-red-900/20 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
								<h4 class="text-sm font-medium text-red-700 dark:text-red-300">原始内容（将被替换）</h4>
							</div>
							<div class="flex-1 overflow-auto p-4 bg-white dark:bg-gray-900">
								<pre class="text-xs whitespace-pre-wrap font-mono text-gray-800 dark:text-gray-200">{originalTableContent || '(空)'}</pre>
							</div>
						</div>
						
						<!-- 右侧：优化后内容 -->
						<div class="w-1/2 flex flex-col overflow-hidden">
							<div class="p-2 bg-green-50 dark:bg-green-900/20 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
								<h4 class="text-sm font-medium text-green-700 dark:text-green-300">优化后内容（将替换原始内容）</h4>
							</div>
							<div class="flex-1 overflow-auto p-4 bg-white dark:bg-gray-900">
								<pre class="text-xs whitespace-pre-wrap font-mono text-gray-800 dark:text-gray-200">{optimizedTableContent}</pre>
							</div>
						</div>
					{:else}
						<div class="flex-1 flex items-center justify-center">
							<div class="text-center text-gray-500 dark:text-gray-400">
								<div class="text-lg mb-2">📊</div>
								<div class="text-sm">点击"使用人工处理优化表格"开始优化</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
			
			<!-- 弹窗底部操作按钮 -->
			<div class="p-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-end gap-2 flex-shrink-0">
				<button
					class="px-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
					on:click={() => showTableFixModal = false}
				>
					取消
				</button>
				{#if optimizedTableContent}
					<button
						class="px-4 py-2 text-sm bg-green-500 hover:bg-green-600 text-white rounded transition-colors"
						on:click={applyTableFix}
					>
						确认应用修复
					</button>
				{/if}
			</div>
		</div>
	</div>
{/if}

<!-- 页面优化弹窗 -->
{#if showPageOptimizeModal}
	<div 
		class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" 
		role="dialog"
		aria-modal="true"
		on:click|self={() => showPageOptimizeModal = false}
		on:keydown={(e) => e.key === 'Escape' && (showPageOptimizeModal = false)}
	>
		<div 
			class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] flex flex-col" 
			on:click|stopPropagation
		>
			<!-- 弹窗头部 -->
			<div class="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between flex-shrink-0">
				<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">
					页面 OCR 优化 - 第 {currentPage} 页
				</h3>
				<button
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
					on:click={() => showPageOptimizeModal = false}
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
					</svg>
				</button>
			</div>
			
			<!-- 弹窗内容 -->
			<div class="flex-1 overflow-hidden flex flex-col min-h-0">
				<!-- 页面图片和优化按钮 -->
				<div class="p-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
					<div class="flex items-center gap-4">
						<div class="flex-1">
							<img
								src={currentPageImageUrl}
								alt="页面图片"
								class="max-w-full max-h-64 object-contain border border-gray-200 dark:border-gray-700 rounded"
							/>
						</div>
						<div class="flex flex-col gap-2">
							{#if !optimizedPageContent && !isProcessingPage}
								<button
									class="px-4 py-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors"
									on:click={optimizePageWithVLM}
								>
									使用 人工优化页面
								</button>
							{/if}
						</div>
					</div>
				</div>
				
				<!-- 处理状态信息 -->
				{#if isProcessingPage || pageOptimizeStatus || pageOptimizeError}
					<div class="p-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex-shrink-0">
						<div class="space-y-2">
							{#if isProcessingPage}
								<div class="flex items-center gap-2">
									<div class="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
									<span class="text-sm font-medium text-blue-600 dark:text-blue-400">{pageOptimizeStatus || '处理中...'}</span>
								</div>
							{:else if pageOptimizeStatus === '成功'}
								<div class="flex items-center gap-2">
									<svg class="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
									</svg>
									<span class="text-sm font-medium text-green-600 dark:text-green-400">{pageOptimizeStatus}</span>
								</div>
							{:else if pageOptimizeError}
								<div class="flex items-center gap-2">
									<svg class="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
									</svg>
									<span class="text-sm font-medium text-red-600 dark:text-red-400">{pageOptimizeStatus || '失败'}</span>
								</div>
							{/if}
							
							{#if pageOptimizeProgress}
								<div class="text-xs text-gray-600 dark:text-gray-400 ml-6">{pageOptimizeProgress}</div>
							{/if}
							
							{#if pageOptimizeError}
								<div class="text-xs text-red-600 dark:text-red-400 ml-6 bg-red-50 dark:bg-red-900/20 p-2 rounded border border-red-200 dark:border-red-800">
									{pageOptimizeError}
								</div>
							{/if}
							
							{#if Object.keys(pageOptimizeDetails).length > 0}
								<div class="text-xs text-gray-500 dark:text-gray-500 ml-6 space-y-1">
									{#if pageOptimizeDetails.model}
										<div>模型: <span class="font-mono">{pageOptimizeDetails.model}</span></div>
									{/if}
									{#if pageOptimizeDetails.imageSize}
										<div>图片大小: <span class="font-mono">{pageOptimizeDetails.imageSize}</span></div>
									{/if}
									{#if pageOptimizeDetails.requestTime !== undefined}
										<div>请求时间: <span class="font-mono">{Math.round(pageOptimizeDetails.requestTime / 1000)}s</span></div>
									{/if}
									{#if pageOptimizeDetails.responseTime !== undefined}
										<div>响应时间: <span class="font-mono">{Math.round(pageOptimizeDetails.responseTime / 1000)}s</span></div>
									{/if}
									{#if pageOptimizeDetails.tokensUsed}
										<div>Token 使用: <span class="font-mono">{pageOptimizeDetails.tokensUsed}</span></div>
									{/if}
								</div>
							{/if}
						</div>
					</div>
				{/if}
				
				<!-- 对比区域 -->
				<div class="flex-1 overflow-hidden flex min-h-0">
					{#if isProcessingPage}
						<!-- 流式输出显示区域 -->
						<div class="flex-1 flex flex-col overflow-hidden">
							<div class="flex-1 overflow-auto p-4 bg-white dark:bg-gray-900">
								{#if pageOptimizeStreamingContent}
									<div class="space-y-2">
										<div class="text-xs text-gray-500 dark:text-gray-400 mb-2">实时生成内容：</div>
										<pre class="text-xs whitespace-pre-wrap font-mono text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-gray-800 p-3 rounded border border-gray-200 dark:border-gray-700 max-h-96 overflow-auto">{pageOptimizeStreamingContent}</pre>
									</div>
								{:else}
									<div class="flex items-center justify-center h-full">
										<div class="text-center">
											<div class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
											<div class="text-sm text-gray-600 dark:text-gray-400">正在使用人工处理优化页面...</div>
											{#if pageOptimizeProgress}
												<div class="text-xs text-gray-500 dark:text-gray-500 mt-2">{pageOptimizeProgress}</div>
											{/if}
										</div>
									</div>
								{/if}
							</div>
						</div>
					{:else if optimizedPageContent}
						<!-- 左侧：原始内容 -->
						<div class="w-1/2 border-r border-gray-200 dark:border-gray-700 flex flex-col overflow-hidden">
							<div class="p-2 bg-red-50 dark:bg-red-900/20 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
								<h4 class="text-sm font-medium text-red-700 dark:text-red-300">原始内容（将被替换）</h4>
							</div>
							<div class="flex-1 overflow-auto p-4 bg-white dark:bg-gray-900">
								<pre class="text-xs whitespace-pre-wrap font-mono text-gray-800 dark:text-gray-200">{originalPageContent || '(空)'}</pre>
							</div>
						</div>
						
						<!-- 右侧：优化后内容 -->
						<div class="w-1/2 flex flex-col overflow-hidden">
							<div class="p-2 bg-green-50 dark:bg-green-900/20 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
								<h4 class="text-sm font-medium text-green-700 dark:text-green-300">优化后内容（将替换原始内容）</h4>
							</div>
							<div class="flex-1 overflow-auto p-4 bg-white dark:bg-gray-900">
								<pre class="text-xs whitespace-pre-wrap font-mono text-gray-800 dark:text-gray-200">{optimizedPageContent}</pre>
							</div>
						</div>
					{:else}
						<div class="flex-1 flex items-center justify-center">
							<div class="text-center text-gray-500 dark:text-gray-400">
								<div class="text-lg mb-2">📄</div>
								<div class="text-sm">点击"使用人工处理优化页面"开始优化</div>
							</div>
						</div>
					{/if}
				</div>
			</div>
			
			<!-- 弹窗底部操作按钮 -->
			<div class="p-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-end gap-2 flex-shrink-0">
				<button
					class="px-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
					on:click={() => showPageOptimizeModal = false}
				>
					取消
				</button>
				{#if optimizedPageContent}
					<button
						class="px-4 py-2 text-sm bg-green-500 hover:bg-green-600 text-white rounded transition-colors"
						on:click={applyPageOptimize}
					>
						确认应用优化
					</button>
				{/if}
			</div>
		</div>
	</div>
{/if}
