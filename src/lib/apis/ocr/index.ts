import { WEBUI_API_BASE_URL } from '$lib/constants';

// OCR API 基础 URL，优先使用 nginx 代理路径（解决跨域问题）
// 如果设置了 window.__OCR_API_BASE_URL__，则使用自定义 URL
// 否则使用 nginx 代理路径 /ocr-api（通过 nginx 代理到 http://192.168.195.125:8002）
const OCR_API_BASE_URL = typeof window !== 'undefined' 
	? (window as any).__OCR_API_BASE_URL__ || '/ocr-api'
	: 'http://192.168.195.125:8002';

export interface UploadResponse {
	status: 'success' | 'error';
	file_path: string;
	file_type: 'pdf' | 'image';
	message?: string;
}

export interface OCRTaskResponse {
	status: 'success' | 'running' | 'error';
	task_id: string;
	message?: string;
}

export interface OCRProgressState {
	status: 'processing' | 'completed' | 'finished' | 'error'; // 支持 'finished' 状态
	result_dir: string;
	total_pages: number;
	processed_pages: number;
	progress: number;
	message: string;
	latest_result?: {
		page: number;
		message: string;
		preview: string;
		result_file: string;
	};
	use_qwen_vlm?: boolean; // VLM 使用状态
	qwen_vlm_status?: 'completed' | 'pending' | 'disabled'; // VLM 状态
}

export interface OCRProgressResponse {
	status: 'success' | 'error';
	task_id: string;
	state: OCRProgressState;
	progress?: number;
	result_dir?: string;
	total_pages?: number;
	processed_pages?: number;
	latest_result?: {
		page: number;
		message: string;
		preview: string;
		result_file: string;
	};
	use_qwen_vlm?: boolean; // VLM 使用状态
	qwen_vlm_status?: 'completed' | 'pending' | 'disabled'; // VLM 状态
}

export interface OCRResultResponse {
	status: 'success' | 'error';
	task_id: string;
	state: 'finished' | 'completed' | 'error'; // 支持 'completed' 状态
	result_dir: string;
	files: string[];
	message?: string;
	use_qwen_vlm?: boolean; // VLM 使用状态
	qwen_vlm_status?: 'completed' | 'pending' | 'disabled'; // VLM 状态
	processed_pages?: number; // 已处理页数
	total_pages?: number; // 总页数
}

/**
 * 上传文件到 OCR 服务
 */
export const uploadFileToOCR = async (file: File): Promise<UploadResponse> => {
	const formData = new FormData();
	formData.append('file', file);

	const response = await fetch(`${OCR_API_BASE_URL}/api/upload`, {
		method: 'POST',
		body: formData
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ status: 'error', message: response.statusText }));
		throw new Error(error.message || `上传失败: ${response.status}`);
	}

	const result = await response.json();
	if (result.status === 'error') {
		throw new Error(result.message || '上传失败');
	}

	return result;
};

/**
 * 使用 OCR 处理图片
 * @param filePath 文件路径（绝对路径，从上传接口返回的 file_path）
 * @param options 可选参数
 */
export const processImageWithOCR = async (
	filePath: string,
	options?: {
		prompt?: string;
		originalFilename?: string;
		timeout?: number;
		maxRetries?: number;
		outputDir?: string;
	}
): Promise<OCRTaskResponse> => {
	const payload: any = {
		file_path: filePath
	};

	if (options?.prompt) payload.prompt = options.prompt;
	if (options?.originalFilename) payload.original_filename = options.originalFilename;
	if (options?.timeout) payload.timeout = options.timeout;
	if (options?.maxRetries) payload.max_retries = options.maxRetries;
	if (options?.outputDir) payload.output_dir = options.outputDir;

	const response = await fetch(`${OCR_API_BASE_URL}/api/ocr-image`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(payload)
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ status: 'error', message: response.statusText }));
		throw new Error(error.message || `OCR 图片处理失败: ${response.status}`);
	}

	const result = await response.json();
	if (result.status === 'error') {
		throw new Error(result.message || 'OCR 图片处理失败');
	}

	return result;
};

/**
 * 使用 OCR 处理 PDF
 * @param filePath 文件路径（绝对路径，从上传接口返回的 file_path）
 * @param options 可选参数
 */
export const processPDFWithOCR = async (
	filePath: string,
	options?: {
		prompt?: string;
		originalFilename?: string;
		workers?: number;
		maxRetries?: number;
		outputDir?: string;
	}
): Promise<OCRTaskResponse> => {
	const payload: any = {
		file_path: filePath
	};

	if (options?.prompt) payload.prompt = options.prompt;
	if (options?.originalFilename) payload.original_filename = options.originalFilename;
	if (options?.workers) payload.workers = options.workers;
	if (options?.maxRetries) payload.max_retries = options.maxRetries;
	if (options?.outputDir) payload.output_dir = options.outputDir;

	const response = await fetch(`${OCR_API_BASE_URL}/api/ocr-pdf`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(payload)
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ status: 'error', message: response.statusText }));
		throw new Error(error.message || `OCR 处理失败: ${response.status}`);
	}

	const result = await response.json();
	if (result.status === 'error') {
		throw new Error(result.message || 'OCR 处理失败');
	}

	return result;
};

/**
 * 使用人工处理模式处理 PDF
 * @param filePath 文件路径（绝对路径）
 * @param options 可选参数
 */
export const processPDFWithManualReview = async (
	filePath: string,
	options?: {
		vlmPrompt?: string;
		originalFilename?: string;
		maxWorkers?: number;
		maxRetries?: number;
		retryDelay?: number;
		outputDir?: string;
	}
): Promise<OCRTaskResponse> => {
	const payload: any = {
		file_path: filePath
	};

	if (options?.vlmPrompt) payload.vlm_prompt = options.vlmPrompt;
	if (options?.originalFilename) payload.original_filename = options.originalFilename;
	if (options?.maxWorkers) payload.max_workers = options.maxWorkers;
	if (options?.maxRetries) payload.max_retries = options.maxRetries;
	if (options?.retryDelay) payload.retry_delay = options.retryDelay;
	if (options?.outputDir) payload.output_dir = options.outputDir;

	const response = await fetch(`${OCR_API_BASE_URL}/api/vlm-pdf`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(payload)
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ status: 'error', message: response.statusText }));
		throw new Error(error.message || `人工处理失败: ${response.status}`);
	}

	const result = await response.json();
	if (result.status === 'error') {
		throw new Error(result.message || '人工处理失败');
	}

	return result;
};

/**
 * 开始 OCR + 人工处理完整流程任务（推荐）
 * @param filePath 文件路径（绝对路径）
 * @param options 可选参数
 */
export const startOCRTask = async (
	filePath: string,
	options?: {
		prompt?: string;
		vlmPrompt?: string;
		useQwenVLM?: boolean;
		originalFilename?: string;
		outputDir?: string;
	}
): Promise<OCRTaskResponse> => {
	const payload: any = {
		file_path: filePath
	};

	if (options?.prompt) payload.prompt = options.prompt;
	if (options?.vlmPrompt) payload.vlm_prompt = options.vlmPrompt;
	if (options?.useQwenVLM !== undefined) payload.use_qwen_vlm = options.useQwenVLM;
	if (options?.originalFilename) payload.original_filename = options.originalFilename;
	if (options?.outputDir) payload.output_dir = options.outputDir;

	const response = await fetch(`${OCR_API_BASE_URL}/api/start`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(payload)
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ status: 'error', message: response.statusText }));
		throw new Error(error.message || `启动任务失败: ${response.status}`);
	}

	const result = await response.json();
	if (result.status === 'error') {
		throw new Error(result.message || '启动任务失败');
	}

	return result;
};

/**
 * 获取任务进度
 */
export const getTaskProgress = async (taskId: string): Promise<OCRProgressResponse> => {
	const response = await fetch(`${OCR_API_BASE_URL}/api/progress/${taskId}`, {
		method: 'GET'
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ status: 'error', message: response.statusText }));
		throw new Error(error.message || `获取进度失败: ${response.status}`);
	}

	const result = await response.json();
	
	// 检查顶层 status（某些 API 可能直接返回 error）
	if (result.status === 'error') {
		// 如果顶层就是 error，直接抛出
		const errorMessage = result.message || '获取进度失败';
		throw new Error(errorMessage);
	}
	
	// 如果顶层是 success，但 state.status 是 error，不在这里抛出
	// 让 pollTaskUntilComplete 统一处理，以便正确传递 state.message
	// 这样错误信息会更准确（例如 "DeepSeek OCR 执行失败"）
	
	return result;
};

/**
 * 获取任务结果
 */
export const getTaskResult = async (taskId: string): Promise<OCRResultResponse> => {
	console.log(`📥 获取任务结果: ${taskId}`);
	
	const response = await fetch(`${OCR_API_BASE_URL}/api/result/${taskId}`, {
		method: 'GET'
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ status: 'error', message: response.statusText }));
		const errorMessage = error.message || `获取结果失败: ${response.status}`;
		console.error(`❌ 获取任务结果失败 (HTTP ${response.status}): ${errorMessage}`);
		throw new Error(errorMessage);
	}

	const result = await response.json();
	console.log(`📋 任务结果响应:`, result);
	
	// 检查顶层 status
	if (result.status === 'error') {
		const errorMessage = result.message || '获取结果失败';
		console.error(`❌ API 返回错误状态: ${errorMessage}`);
		throw new Error(errorMessage);
	}

	// 检查 state 字段（如果存在）
	// 注意：某些 API 可能返回 state: 'completed'，这是正常的完成状态
	if (result.state) {
		const state = result.state;
		console.log(`📊 任务状态: ${state}`);
		
		// 如果 state 是 'completed' 或 'finished'，这是正常完成状态
		if (state === 'completed' || state === 'finished') {
			console.log(`✅ 任务已完成，状态: ${state}`);
			// 继续处理，不抛出错误
		} else if (state === 'error') {
			// state 是 error，但顶层 status 可能不是 error，需要检查
			const errorMessage = result.message || '任务处理失败';
			console.error(`❌ 任务状态为错误: ${errorMessage}`);
			throw new Error(errorMessage);
		} else {
			// 其他未知状态，记录警告但不抛出错误（可能是 API 返回的新状态）
			console.warn(`⚠️ 未知的任务状态: ${state}，但继续处理`);
		}
	}

	// 验证必要字段
	if (!result.result_dir && !result.files) {
		console.warn(`⚠️ 结果中缺少 result_dir 或 files 字段`);
	}

	console.log(`✅ 成功获取任务结果`);
	return result;
};

/**
 * WebSocket 完成消息接口
 */
export interface OCRWebSocketMessage {
	status: 'finished' | 'completed'; // 完成状态
	task_id: string;
	result_dir: string;
	files: string[];
	use_qwen_vlm?: boolean;
	qwen_vlm_status?: 'completed' | 'pending' | 'disabled';
	processed_pages?: number;
	total_pages?: number;
	message?: string;
}

/**
 * 通过 WebSocket 监听任务进度（可选，更高效）
 * @param taskId 任务ID
 * @param onMessage 消息回调
 * @param onError 错误回调
 * @returns WebSocket 连接（用于关闭）
 */
export const connectTaskWebSocket = (
	taskId: string,
	onMessage: (message: OCRWebSocketMessage) => void,
	onError?: (error: Error) => void
): WebSocket | null => {
	try {
		// 构建 WebSocket URL（使用 nginx 代理路径）
		const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		const wsHost = window.location.host;
		const wsUrl = `${wsProtocol}//${wsHost}/ocr-api/ws/progress/${taskId}`;
		
		console.log(`🔌 连接 WebSocket: ${wsUrl}`);
		
		const ws = new WebSocket(wsUrl);
		
		ws.onopen = () => {
			console.log(`✅ WebSocket 连接已建立: ${taskId}`);
		};
		
		ws.onmessage = (event) => {
			try {
				const message: OCRWebSocketMessage = JSON.parse(event.data);
				console.log(`📨 收到 WebSocket 消息:`, message);
				
				// 检查是否是完成消息
				if (message.status === 'finished' || message.status === 'completed') {
					console.log(`✅ 任务完成通知 (WebSocket): ${taskId}`);
					onMessage(message);
				}
			} catch (error) {
				console.error('❌ 解析 WebSocket 消息失败:', error);
			}
		};
		
		ws.onerror = (error) => {
			console.error('❌ WebSocket 错误:', error);
			if (onError) {
				onError(new Error('WebSocket 连接错误'));
			}
		};
		
		ws.onclose = () => {
			console.log(`🔌 WebSocket 连接已关闭: ${taskId}`);
		};
		
		return ws;
	} catch (error) {
		console.error('❌ 创建 WebSocket 连接失败:', error);
		if (onError) {
			onError(error instanceof Error ? error : new Error('WebSocket 创建失败'));
		}
		return null;
	}
};

/**
 * 轮询任务直到完成
 * 支持 WebSocket 和轮询两种方式
 */
export const pollTaskUntilComplete = async (
	taskId: string,
	onProgress?: (progress: OCRProgressResponse) => void,
	interval: number = 3000, // 默认3秒，与文档示例一致
	timeout: number = 600000, // 10分钟超时（人工处理流程可能需要较长时间）
	useWebSocket: boolean = false // 是否使用 WebSocket（如果支持）
): Promise<OCRResultResponse> => {
	const startTime = Date.now();
	let ws: WebSocket | null = null;
	let completed = false;
	let result: OCRResultResponse | null = null;

	// 如果启用 WebSocket，尝试建立连接
	if (useWebSocket && typeof window !== 'undefined') {
		ws = connectTaskWebSocket(
			taskId,
			(message) => {
				// WebSocket 收到完成消息
				console.log(`✅ 通过 WebSocket 收到完成通知:`, message);
				completed = true;
				// 构造结果对象
				result = {
					status: 'success',
					task_id: message.task_id,
					state: message.status === 'finished' ? 'finished' : 'completed',
					result_dir: message.result_dir,
					files: message.files,
					use_qwen_vlm: message.use_qwen_vlm,
					qwen_vlm_status: message.qwen_vlm_status,
					processed_pages: message.processed_pages,
					total_pages: message.total_pages,
					message: message.message
				};
			},
			(error) => {
				console.warn('⚠️ WebSocket 连接失败，回退到轮询模式:', error);
				// WebSocket 失败时继续使用轮询
			}
		);
	}

	try {
		while (!completed) {
			const progress = await getTaskProgress(taskId);
			const state = progress.state || {};

			if (onProgress) {
				onProgress(progress);
			}

			// 检查任务状态
			// 注意：API 可能返回 state.status: 'completed' 或 'finished'
			const taskStatus = state.status || progress.status || 'unknown';
			
			if (taskStatus === 'completed' || taskStatus === 'finished') {
				console.log(`✅ 任务已完成，状态: ${taskStatus}`);
				// 如果 WebSocket 已经返回结果，使用 WebSocket 的结果
				if (result) {
					return result;
				}
				// 否则通过 API 获取结果
				return getTaskResult(taskId);
			}

			if (taskStatus === 'error') {
				// 优先使用 state.message，这是最准确的错误信息
				const errorMessage = state.message || '任务处理失败';
				throw new Error(errorMessage);
			}

			// 检查超时
			if (Date.now() - startTime > timeout) {
				throw new Error('任务处理超时');
			}

			// 如果 WebSocket 已返回结果，直接返回
			if (completed && result) {
				return result;
			}

			// 等待下一次轮询
			await new Promise(resolve => setTimeout(resolve, interval));
		}

		// 如果通过 WebSocket 完成，返回结果
		if (result) {
			return result;
		}

		// 否则通过 API 获取最终结果
		return getTaskResult(taskId);
	} finally {
		// 关闭 WebSocket 连接
		if (ws && ws.readyState === WebSocket.OPEN) {
			ws.close();
			console.log(`🔌 已关闭 WebSocket 连接: ${taskId}`);
		}
	}
};

/**
 * 导出结果响应接口
 */
export interface ExportResultResponse {
	status: 'success' | 'error';
	task_id?: string;
	message?: string;
	target_dir?: string;
	zip_path?: string; // 压缩文件的完整路径
	zip_filename?: string; // 压缩文件名
	zip_size?: number; // 压缩文件大小（字节）
	zip_size_mb?: string; // 压缩文件大小（MB，格式化字符串）
	original_filename?: string; // 原始文件名
	exported_files?: string[]; // 导出的文件列表（如果 API 提供）
	file_count?: number; // 文件数量（如果 API 提供）
}

/**
 * 导出 OCR 结果到指定目录
 * @param taskId 任务ID
 * @param targetDir 目标目录路径（绝对路径）
 * @returns 导出结果，包含状态、消息和目标目录
 */
export const exportOCRResult = async (taskId: string, targetDir: string): Promise<ExportResultResponse> => {
	console.log(`📦 导出 OCR 结果 - taskId: ${taskId}, targetDir: ${targetDir}`);
	
	const response = await fetch(`${OCR_API_BASE_URL}/api/export-result`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			task_id: taskId,
			target_dir: targetDir
		})
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ status: 'error', message: response.statusText }));
		const errorMessage = error.message || `导出结果失败: ${response.status}`;
		console.error(`❌ 导出 OCR 结果失败: ${errorMessage}`);
		throw new Error(errorMessage);
	}

	const result: ExportResultResponse = await response.json();
	
	if (result.status === 'error') {
		const errorMessage = result.message || '导出结果失败';
		console.error(`❌ 导出 OCR 结果失败: ${errorMessage}`);
		throw new Error(errorMessage);
	}

	// 记录详细的导出信息
	if (result.status === 'success') {
		console.log(`✅ OCR 结果导出成功:`);
		console.log(`   - 任务ID: ${result.task_id || taskId}`);
		console.log(`   - 目标目录: ${result.target_dir || targetDir}`);
		if (result.zip_path) {
			console.log(`   - 压缩文件: ${result.zip_filename || 'N/A'}`);
			console.log(`   - 文件大小: ${result.zip_size_mb || (result.zip_size ? `${(result.zip_size / 1024 / 1024).toFixed(2)} MB` : 'N/A')}`);
			console.log(`   - 完整路径: ${result.zip_path}`);
		}
		if (result.original_filename) {
			console.log(`   - 原始文件: ${result.original_filename}`);
		}
		if (result.file_count) {
			console.log(`   - 文件数量: ${result.file_count}`);
		}
	}
	
	return result;
};

/**
 * 获取文件内容（用于读取 Markdown 结果）
 * @param filePath 文件路径（绝对路径）
 */
export const getFileContent = async (filePath: string): Promise<string> => {
	const response = await fetch(
		`${OCR_API_BASE_URL}/api/file/content?path=${encodeURIComponent(filePath)}`,
		{
			method: 'GET'
		}
	);

	if (!response.ok) {
		const error = await response.json().catch(() => ({ status: 'error', message: response.statusText }));
		throw new Error(error.message || `获取文件内容失败: ${response.status}`);
	}

	// 检查 Content-Type 判断是文本还是图片
	const contentType = response.headers.get('Content-Type');
	if (contentType?.startsWith('application/json')) {
		const data = await response.json();
		return data.content || '';
	} else {
		// 文本文件直接返回
		return response.text();
	}
};

