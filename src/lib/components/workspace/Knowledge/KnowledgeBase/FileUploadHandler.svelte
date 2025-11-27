<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { v4 as uuidv4 } from 'uuid';
	import { uploadFile } from '$lib/apis/files';
	import { addFileToKnowledgeById, resetKnowledgeById } from '$lib/apis/knowledge';
	import { blobToFile } from '$lib/utils';
	import { createEventDispatcher } from 'svelte';
	import { 
		uploadFileToOCR,
		processPDFWithOCR,
		startOCRTask, 
		pollTaskUntilComplete, 
		getFileContent,
		getTaskResult,
		exportOCRResult,
		type OCRProgressResponse 
	} from '$lib/apis/ocr';
	import { updateFileDataContentById, extractZipFile } from '$lib/apis/files';

	const dispatch = createEventDispatcher();

	export let knowledge: any;
	export let id: string;
	export let settings: any;
	export let config: any;
	export let i18n: any;

	// OCR 处理队列：确保按文件顺序处理
	let ocrQueue: Array<{ fileId: string; fileName: string }> = [];
	let isProcessingOCR = false;

	// 获取i18n的t方法
	const t = (i18n as any)?.t || ((key: string) => key);

	// 创建文本文件
	const createFileFromText = (name: string, content: string) => {
		const blob = new Blob([content], { type: 'text/plain' });
		const file = blobToFile(blob, `${name}.txt`);
		return file;
	};

	// 单个文件上传处理
	const uploadFileHandler = async (file: File) => {
		console.log(file);

		const tempItemId = uuidv4();
		const fileItem = {
			type: 'file',
			file: '',
			id: null,
			url: '',
			name: file.name,
			size: file.size,
			status: 'uploading',
			error: '',
			itemId: tempItemId
		};

		if (fileItem.size == 0) {
			toast.error(t('You cannot upload an empty file.'));
			return null;
		}

		if (
			(config?.file?.max_size ?? null) !== null &&
			file.size > (config?.file?.max_size ?? 0) * 1024 * 1024
		) {
			console.log('File exceeds max size limit:', {
				fileSize: file.size,
				maxSize: (config?.file?.max_size ?? 0) * 1024 * 1024
			});
			toast.error(
				t(`File size should not exceed {{maxSize}} MB.`, {
					maxSize: config?.file?.max_size
				})
			);
			return;
		}

		knowledge.files = [...(knowledge.files ?? []), fileItem];

		try {
			// If the file is an audio file, provide the language for STT.
			let metadata = null;
			if (
				(file.type.startsWith('audio/') || file.type.startsWith('video/')) &&
				settings?.audio?.stt?.language
			) {
				metadata = {
					language: settings?.audio?.stt?.language,
					collection_name: id  // 添加知识库ID到元数据
				};
			} else {
				metadata = {
					collection_name: id  // 添加知识库ID到元数据
				};
			}

			const uploadedFile = await uploadFile(localStorage.token, file, metadata).catch((e) => {
				toast.error(`${e}`);
				return null;
			});

			if (uploadedFile) {
				console.log(uploadedFile);

				if (uploadedFile.error) {
					console.warn('File upload warning:', uploadedFile.error);
					toast.warning(uploadedFile.error);
				}

				knowledge.files = knowledge.files.map((item) => {
					if (item.itemId === tempItemId) {
						item.id = uploadedFile.id;
					}

					// Remove temporary item id
					delete item.itemId;
					return item;
				});
				const addResult = await addFileHandler(uploadedFile.id);
				if (!addResult) {
					// 如果添加到知识库失败，从文件列表中移除
					knowledge.files = knowledge.files.filter(item => item.id !== uploadedFile.id);
				} else {
					// 如果是 PDF 文件，添加到 OCR 处理队列
					if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
						// 立即更新文件状态为等待处理
						knowledge.files = knowledge.files.map((item: any) => {
							if (item.id === uploadedFile.id) {
								item.status = 'pending';
								item.ocrStatus = 'pending';
								item.ocrMessage = '等待处理...';
							}
							return item;
						});
						knowledge = { ...knowledge }; // 触发响应式更新
						
						// 添加到队列，按顺序处理
						ocrQueue.push({ fileId: uploadedFile.id, fileName: file.name });
						console.log(`📋 PDF 文件已添加到 OCR 队列: ${file.name} (队列长度: ${ocrQueue.length})`);
						// 如果当前没有在处理，开始处理队列
						if (!isProcessingOCR) {
							processOCRQueue();
						}
					}
				}
			} else {
				toast.error(t('Failed to upload file.'));
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	// 添加文件到知识库（增强版，带重试机制）
	const addFileHandler = async (fileId: string, retryCount = 0) => {
		const maxRetries = 3;
		const retryDelay = 1000 * (retryCount + 1); // 递增延迟：1s, 2s, 3s
		
		console.log(`📚 添加文件到知识库: ${fileId} (尝试 ${retryCount + 1}/${maxRetries + 1})`);
		
		try {
			const updatedKnowledge = await addFileToKnowledgeById(localStorage.token, id, fileId).catch(
				(e) => {
					console.error(`❌ 添加到知识库失败: ${fileId}`, e);
					throw e;
				}
			);

			if (updatedKnowledge) {
				knowledge = updatedKnowledge;
				console.log(`✅ 文件添加成功: ${fileId}`);
				toast.success(t('File added successfully.'));
				dispatch('knowledgeUpdated', updatedKnowledge);
				return true;
			} else {
				throw new Error('添加到知识库返回空结果');
			}
		} catch (e) {
			console.error(`❌ 添加文件到知识库失败: ${fileId}`, e);
			
			if (retryCount < maxRetries) {
				console.log(`🔄 重试添加文件到知识库: ${fileId} (${retryCount + 1}/${maxRetries})`);
				await new Promise(resolve => setTimeout(resolve, retryDelay));
				return addFileHandler(fileId, retryCount + 1);
			} else {
				console.error(`❌ 文件添加最终失败: ${fileId}`);
				toast.error(t('Failed to add file after multiple attempts.'));
				knowledge.files = knowledge.files.filter((file) => file.id !== fileId);
				return false;
			}
		}
	};

	// 目录上传处理
	const uploadDirectoryHandler = async () => {
		// Check if File System Access API is supported
		const isFileSystemAccessSupported = 'showDirectoryPicker' in window;

		try {
			if (isFileSystemAccessSupported) {
				// Modern browsers (Chrome, Edge) implementation
				await handleModernBrowserUpload();
			} else {
				// Firefox fallback
				await handleFirefoxUpload();
			}
		} catch (error) {
			handleUploadError(error);
		}
	};

	// Helper function to check if a path contains hidden folders
	const hasHiddenFolder = (path: string) => {
		return path.split('/').some((part: string) => part.startsWith('.'));
	};

	// Modern browsers implementation using File System Access API
	const handleModernBrowserUpload = async () => {
		const dirHandle = await window.showDirectoryPicker();
		let totalFiles = 0;
		let uploadedFiles = 0;

		// Function to update the UI with the progress
		const updateProgress = () => {
			const percentage = (uploadedFiles / totalFiles) * 100;
			toast.info(
				t('Upload Progress: {{uploadedFiles}}/{{totalFiles}} ({{percentage}}%)', {
					uploadedFiles: uploadedFiles,
					totalFiles: totalFiles,
					percentage: percentage.toFixed(2)
				})
			);
		};

		// Recursive function to count all files excluding hidden ones
		async function countFiles(dirHandle: any) {
			for await (const entry of dirHandle.values()) {
				// Skip hidden files and directories
				if (entry.name.startsWith('.')) continue;

				if (entry.kind === 'file') {
					totalFiles++;
				} else if (entry.kind === 'directory') {
					// Only process non-hidden directories
					if (!entry.name.startsWith('.')) {
						await countFiles(entry);
					}
				}
			}
		}

		// Recursive function to process directories excluding hidden files and folders
		async function processDirectory(dirHandle: any, path = '') {
			for await (const entry of dirHandle.values()) {
				// Skip hidden files and directories
				if (entry.name.startsWith('.')) continue;

				const entryPath = path ? `${path}/${entry.name}` : entry.name;

				// Skip if the path contains any hidden folders
				if (hasHiddenFolder(entryPath)) continue;

				if (entry.kind === 'file') {
					const file = await entry.getFile();
					const fileWithPath = new File([file], entryPath, { type: file.type });

					await uploadFileHandler(fileWithPath);
					uploadedFiles++;
					updateProgress();
				} else if (entry.kind === 'directory') {
					// Only process non-hidden directories
					if (!entry.name.startsWith('.')) {
						await processDirectory(entry, entryPath);
					}
				}
			}
		}

		await countFiles(dirHandle);
		updateProgress();

		if (totalFiles > 0) {
			await processDirectory(dirHandle);
		} else {
			console.log('No files to upload.');
		}
	};

	// Firefox fallback implementation using traditional file input
	const handleFirefoxUpload = async () => {
		return new Promise((resolve, reject) => {
			// Create hidden file input
			const input = document.createElement('input');
			input.type = 'file';
			input.webkitdirectory = true;
			input.directory = true;
			input.multiple = true;
			input.style.display = 'none';

			// Add input to DOM temporarily
			document.body.appendChild(input);

			input.onchange = async () => {
				try {
					const files = Array.from(input.files)
						// Filter out files from hidden folders
						.filter((file) => !hasHiddenFolder(file.webkitRelativePath));

					let totalFiles = files.length;
					let uploadedFiles = 0;

					// Function to update the UI with the progress
					const updateProgress = () => {
						const percentage = (uploadedFiles / totalFiles) * 100;
						toast.info(
							t('Upload Progress: {{uploadedFiles}}/{{totalFiles}} ({{percentage}}%)', {
								uploadedFiles: uploadedFiles,
								totalFiles: totalFiles,
								percentage: percentage.toFixed(2)
							})
						);
					};

					updateProgress();

					// Process all files
					for (const file of files) {
						// Skip hidden files (additional check)
						if (!file.name.startsWith('.')) {
							const relativePath = file.webkitRelativePath || file.name;
							const fileWithPath = new File([file], relativePath, { type: file.type });

							await uploadFileHandler(fileWithPath);
							uploadedFiles++;
							updateProgress();
						}
					}

					// Clean up
					document.body.removeChild(input);
					resolve();
				} catch (error) {
					reject(error);
				}
			};

			input.onerror = (error) => {
				document.body.removeChild(input);
				reject(error);
			};

			// Trigger file picker
			input.click();
		});
	};

	// Error handler
	const handleUploadError = (error: any) => {
		if (error.name === 'AbortError') {
			toast.info(t('Directory selection was cancelled'));
		} else {
			toast.error(t('Error accessing directory'));
			console.error('Directory access error:', error);
		}
	};

	// Helper function to maintain file paths within zip
	const syncDirectoryHandler = async () => {
		if ((knowledge?.files ?? []).length > 0) {
			const res = await resetKnowledgeById(localStorage.token, id).catch((e) => {
				toast.error(`${e}`);
			});

			if (res) {
				knowledge = res;
				toast.success(t('Knowledge reset successfully.'));
				dispatch('knowledgeUpdated', res);

				// Upload directory
				uploadDirectoryHandler();
			}
		} else {
			uploadDirectoryHandler();
		}
	};

	// 处理添加内容事件
	const handleAddContent = (event: any) => {
		const { type } = event.detail;
		console.log('Add content type:', type);
		
		if (type === 'files') {
			// 触发文件上传
			const input = document.createElement('input');
			input.type = 'file';
			input.multiple = true;
			input.accept = '.pdf,.txt,.md,.docx,.doc,.rtf';
			input.onchange = (e) => {
				const files = Array.from(e.target.files);
				uploadMultipleFiles(files);
			};
			input.click();
		} else if (type === 'directory') {
			// 触发目录上传
			const input = document.createElement('input');
			input.type = 'file';
			input.webkitdirectory = true;
			input.onchange = (e) => {
				const files = Array.from(e.target.files);
				uploadMultipleFiles(files);
			};
			input.click();
		} else if (type === 'text') {
			// 显示添加文本内容模态框
			dispatch('showAddTextContent');
		}
	};

	// 拖拽处理
	const onDragOver = (e: DragEvent) => {
		e.preventDefault();
		if (e.dataTransfer?.types?.includes('Files')) {
			dispatch('dragStart');
		}
	};

	const onDragLeave = () => {
		dispatch('dragEnd');
	};

	const onDrop = async (e: DragEvent) => {
		e.preventDefault();
		dispatch('dragEnd');

		if (e.dataTransfer?.types?.includes('Files')) {
			if (e.dataTransfer?.files) {
				const inputFiles = e.dataTransfer?.files;

				if (inputFiles && inputFiles.length > 0) {
					for (const file of inputFiles) {
						await uploadFileHandler(file);
					}
				} else {
					toast.error(t(`File not found.`));
				}
			}
		}
	};

	// 多文件上传处理（带并发控制）
	const uploadMultipleFiles = async (files: File[]) => {
		const maxConcurrent = 5; // 最大并发数
		const results = [];
		
		console.log(`📁 开始批量上传 ${files.length} 个文件，最大并发数: ${maxConcurrent}`);
		
		// 分批处理文件
		for (let i = 0; i < files.length; i += maxConcurrent) {
			const batch = files.slice(i, i + maxConcurrent);
			console.log(`📦 处理批次 ${Math.floor(i / maxConcurrent) + 1}: ${batch.length} 个文件`);
			
			// 并发处理当前批次
			const batchPromises = batch.map(async (file, index) => {
				console.log(`⏳ 队列中等待: ${file.name} (批次内第 ${index + 1} 个)`);
				await new Promise(resolve => setTimeout(resolve, index * 500)); // 批次内错开500ms
				return uploadFileHandler(file);
			});
			
			const batchResults = await Promise.allSettled(batchPromises);
			results.push(...batchResults);
			
			// 批次间等待
			if (i + maxConcurrent < files.length) {
				console.log(`⏸️ 批次间等待 2 秒...`);
				await new Promise(resolve => setTimeout(resolve, 2000));
			}
		}
		
		// 统计结果
		const successful = results.filter(r => r.status === 'fulfilled').length;
		const failed = results.filter(r => r.status === 'rejected').length;
		
		console.log(`📊 批量上传完成: 成功 ${successful} 个，失败 ${failed} 个`);
		
		// 批量上传完成后，重新加载知识库数据以确保所有文件都显示
		if (successful > 0) {
			try {
				const { getKnowledgeById } = await import('$lib/apis/knowledge');
				const refreshedKnowledge = await getKnowledgeById(localStorage.token, id);
				if (refreshedKnowledge) {
					knowledge = refreshedKnowledge;
					dispatch('knowledgeUpdated', refreshedKnowledge);
					console.log(`🔄 批量上传后刷新知识库数据，当前文件数: ${refreshedKnowledge.files?.length || 0}`);
				}
			} catch (e) {
				console.error('批量上传后刷新知识库数据失败:', e);
			}
		}
		
		if (failed > 0) {
			toast.warning(`批量上传完成: ${successful} 个成功，${failed} 个失败`);
		} else {
			toast.success(`批量上传完成: ${successful} 个文件全部成功`);
		}
		
		return results;
	};

	/**
	 * 处理 OCR 队列：按顺序处理每个文件
	 */
	const processOCRQueue = async () => {
		if (isProcessingOCR || ocrQueue.length === 0) {
			return;
		}

		isProcessingOCR = true;
		console.log(`🚀 开始处理 OCR 队列，共 ${ocrQueue.length} 个文件`);

		while (ocrQueue.length > 0) {
			const { fileId, fileName } = ocrQueue.shift()!;
			console.log(`📄 处理队列中的文件: ${fileName} (剩余 ${ocrQueue.length} 个)`);
			
			try {
				await processPDFWithOCRAsync(fileId, fileName);
				console.log(`✅ 文件处理完成: ${fileName}`);
			} catch (err) {
				console.error(`❌ 文件处理失败: ${fileName}`, err);
				// 继续处理下一个文件，不中断队列
			}
		}

		isProcessingOCR = false;
		console.log(`✅ OCR 队列处理完成`);
	};

	/**
	 * 异步处理 PDF 文件的 OCR 转换（不阻塞主流程）
	 * 流程：1. 获取文件内容 2. 上传到 OCR 服务 3. 调用 OCR 处理 4. 轮询进度 5. 获取结果并更新
	 */
	const processPDFWithOCRAsync = async (fileId: string, fileName: string) => {
		try {
			console.log(`🔄 开始处理 PDF 文件 OCR: ${fileName}`);
			toast.info(`正在处理 PDF: ${fileName}...`);

			// 更新文件状态为处理中
			knowledge.files = knowledge.files.map((item: any) => {
				if (item.id === fileId) {
					item.status = 'processing';
					item.ocrStatus = 'processing';
				}
				return item;
			});
			knowledge = { ...knowledge }; // 触发响应式更新

			// 1. 获取文件内容（从知识库文件 API）
			console.log(`📥 获取文件内容: ${fileId}`);
			const { getFileContentById } = await import('$lib/apis/files');
			const fileBlob = await getFileContentById(fileId);
			
			if (!fileBlob) {
				throw new Error('无法获取文件内容');
			}

			// 2. 上传文件到 OCR 服务
			console.log(`📤 上传文件到 OCR 服务...`);
			const file = new File([fileBlob], fileName, { type: 'application/pdf' });
			const uploadResult = await uploadFileToOCR(file);
			const ocrFilePath = uploadResult.file_path;
			console.log(`✅ 文件已上传到 OCR 服务: ${ocrFilePath}`);

			// 3. 启动 OCR 任务（仅 OCR 模式，不使用 VLM）
			console.log(`🚀 启动 OCR 任务（仅 OCR 模式）...`);
			const taskResponse = await processPDFWithOCR(ocrFilePath, {
				prompt: `<image> 
				<|grounding|>Convert the document to markdown format.`,
				originalFilename: fileName,
				workers: 64,
				maxRetries: 3
			});
			const taskId = taskResponse.task_id;
			console.log(`✅ OCR 任务已启动: ${taskId}`);

			// 4. 轮询任务进度（支持 WebSocket，如果可用）
			let result: any = null;
			try {
				// 尝试使用 WebSocket（如果支持），否则使用轮询
				// WebSocket 更高效，可以实时接收完成通知
				const useWebSocket = true; // 可以改为配置项
				
				result = await pollTaskUntilComplete(
					taskId,
					(progress: OCRProgressResponse) => {
						const state = progress.state || {};
						const progressPercent = state.progress || progress.progress || 0;
						const message = state.message || progress.latest_result?.message || '';
						
						// 记录 人工处理状态（如果有）
						const vlmStatus = progress.qwen_vlm_status || state.qwen_vlm_status;
						const useVLM = progress.use_qwen_vlm || state.use_qwen_vlm;
						
						console.log(`📊 OCR 进度: ${progressPercent}% - ${message}`);
						if (useVLM && vlmStatus) {
							console.log(`🤖 人工处理状态: ${vlmStatus}`);
						}
						
						// 更新文件状态显示进度
						knowledge.files = knowledge.files.map((item: any) => {
							if (item.id === fileId) {
								item.ocrProgress = progressPercent;
								item.ocrMessage = message;
								item.ocrProcessedPages = state.processed_pages || progress.processed_pages || 0;
								item.ocrTotalPages = state.total_pages || progress.total_pages || 0;
								// 记录 人工处理状态
								if (useVLM) {
									item.useQwenVLM = true;
									item.qwenVLMStatus = vlmStatus;
								}
							}
							return item;
						});
						knowledge = { ...knowledge }; // 触发响应式更新
					},
					10000, // 每10秒轮询一次（减少请求频率）
					300000, // 5分钟超时（仅 OCR 模式处理较快）
					useWebSocket // 使用 WebSocket（如果支持）
				);
			} catch (pollError) {
				// 处理轮询错误
				const errorMessage = pollError instanceof Error ? pollError.message : String(pollError);
				console.warn('⚠️ pollTaskUntilComplete 遇到错误:', errorMessage);
				
				// 如果是"未知状态"错误，或者包含"completed"的错误，尝试直接获取结果
				// 这可能是因为 API 返回了 completed 状态，但轮询逻辑没有正确处理
				if (errorMessage.includes('未知状态') || 
				    (errorMessage.includes('completed') && errorMessage.includes('未知'))) {
					console.warn('⚠️ 检测到状态相关错误，尝试直接获取任务结果', pollError);
					try {
						result = await getTaskResult(taskId);
						console.log('✅ 通过 getTaskResult 成功获取结果');
					} catch (fallbackError) {
						const fallbackMessage = fallbackError instanceof Error ? fallbackError.message : String(fallbackError);
						console.error('❌ getTaskResult 备用方案失败:', fallbackMessage);
						
						// 如果备用方案也失败，但错误消息包含"completed"，可能是任务实际上已经完成
						// 尝试从进度接口获取最后的状态
						if (fallbackMessage.includes('completed') || fallbackMessage.includes('未知状态')) {
							console.warn('⚠️ 检测到可能是状态解析问题，尝试从进度接口获取最终状态');
							try {
								const { getTaskProgress } = await import('$lib/apis/ocr');
								const finalProgress = await getTaskProgress(taskId);
								if (finalProgress.state && (finalProgress.state.status === 'completed' || finalProgress.state.result_dir)) {
									console.log('✅ 从进度接口获取到完成状态，使用 result_dir');
									// 构造一个结果对象
									result = {
										status: 'success',
										task_id: taskId,
										state: 'completed',
										result_dir: finalProgress.state.result_dir || '',
										files: [] // 文件列表可能需要从其他地方获取
									};
									console.log('✅ 使用构造的结果对象继续处理');
								} else {
									throw fallbackError;
								}
							} catch (progressError) {
								console.error('❌ 从进度接口获取状态也失败:', progressError);
								throw fallbackError;
							}
						} else {
							throw fallbackError;
						}
					}
				} else {
					// 其他类型的错误，直接抛出
					throw pollError;
				}
			}

			console.log(`✅ OCR 处理完成:`, result);
			
			// 记录完成信息
			if (result.use_qwen_vlm && result.qwen_vlm_status) {
				console.log(`🤖 人工处理状态: ${result.qwen_vlm_status}`);
				// 如果 VLM 处理完成，保存 VLM 任务 ID（使用 OCR 任务 ID，因为 人工处理结果在同一个任务中）
				if (result.qwen_vlm_status === 'completed') {
					console.log(`✅ 人工处理已完成，任务 ID: ${taskId}`);
					// 更新文件状态，标记 VLM 处理完成
					knowledge.files = knowledge.files.map((item: any) => {
						if (item.id === fileId) {
							item.useQwenVLM = true;
							item.qwenVLMStatus = 'completed';
							item.vlmTaskId = taskId; // 人工处理结果在同一个 OCR 任务中
						}
						return item;
					});
					knowledge = { ...knowledge };
				}
			}
			if (result.processed_pages && result.total_pages) {
				console.log(`📄 处理页数: ${result.processed_pages}/${result.total_pages}`);
			}

			// 5. 使用新的 export-result API 将结果导出到知识库目录
			const knowledgeDir = `/home/zeroerr-ai72/openwebui-zeroerr/backend/data/uploads/knowledge/${id}`;
			const targetResultDir = `${knowledgeDir}/ocr_result_${taskId}`;
			
			console.log(`📦 准备导出 OCR 结果到知识库目录: ${targetResultDir}`);
			
			// 更新文件状态显示导出进度
			knowledge.files = knowledge.files.map((item: any) => {
				if (item.id === fileId) {
					item.ocrStatus = 'exporting';
					item.ocrMessage = '正在导出结果...';
				}
				return item;
			});
			knowledge = { ...knowledge };
			
			let exportedDir = targetResultDir;
			let exportSuccess = false;
			let zipPath: string | null = null;
			try {
				// 调用 OCR API 导出结果
				const exportResult = await exportOCRResult(taskId, targetResultDir);
				console.log(`✅ OCR 结果已导出:`, exportResult);
				
				// 如果 API 返回了实际的目标目录，使用它
				if (exportResult.target_dir) {
					exportedDir = exportResult.target_dir;
					console.log(`📁 导出目标目录: ${exportedDir}`);
				}
				
				// 记录压缩文件信息（如果导出为 zip）
				if (exportResult.zip_path) {
					zipPath = exportResult.zip_path;
					console.log(`📦 压缩文件路径: ${zipPath}`);
					console.log(`📦 压缩文件名: ${exportResult.zip_filename || 'N/A'}`);
					console.log(`📦 压缩文件大小: ${exportResult.zip_size_mb || (exportResult.zip_size ? `${(exportResult.zip_size / 1024 / 1024).toFixed(2)} MB` : 'N/A')}`);
					
					// 自动解压 zip 文件到目标目录
					try {
						console.log(`📂 开始解压 zip 文件到: ${exportedDir}`);
						
						// 更新文件状态显示解压进度
						knowledge.files = knowledge.files.map((item: any) => {
							if (item.id === fileId) {
								item.ocrStatus = 'extracting';
								item.ocrMessage = '正在解压结果文件...';
							}
							return item;
						});
						knowledge = { ...knowledge };
						
						const extractResult = await extractZipFile(localStorage.token, zipPath, exportedDir);
						console.log(`✅ Zip 文件解压成功:`, extractResult);
						console.log(`📊 解压文件数量: ${extractResult.file_count || 'unknown'}`);
						
						// 解压成功后，更新导出目录为解压后的目录
						if (extractResult.extract_to) {
							exportedDir = extractResult.extract_to;
							console.log(`📁 解压目录: ${exportedDir}`);
						}
						
						// 如果解压结果包含文件列表，更新 resultFiles
						if (extractResult.extracted_files && extractResult.extracted_files.length > 0) {
							console.log(`📋 解压后的文件列表 (前10个):`, extractResult.extracted_files.slice(0, 10));
							// 注意：这里不直接替换 resultFiles，因为后续逻辑会从 resultDir 读取
						}
						
						exportSuccess = true; // 标记解压成功
					} catch (extractError) {
						console.error(`❌ 解压 zip 文件失败:`, extractError);
						const errorMessage = extractError instanceof Error ? extractError.message : String(extractError);
						console.warn(`⚠️ 解压失败: ${errorMessage}`);
						// 解压失败不影响后续流程，继续使用 zip 文件路径
						// 但标记导出成功，因为 zip 文件已经导出
						exportSuccess = true;
					}
				}
				
				// 记录导出的文件数量（如果有）
				if (exportResult.file_count) {
					console.log(`📊 导出文件数量: ${exportResult.file_count}`);
				}
				if (exportResult.exported_files && exportResult.exported_files.length > 0) {
					console.log(`📋 导出的文件列表:`, exportResult.exported_files);
				}
				
				exportSuccess = true;
				
			} catch (exportError) {
				console.error(`❌ 导出 OCR 结果失败:`, exportError);
				const errorMessage = exportError instanceof Error ? exportError.message : String(exportError);
				
				// 如果导出失败，尝试使用原来的 resultDir
				if (result.result_dir) {
					exportedDir = result.result_dir;
					console.warn(`⚠️ 导出失败，使用原始结果目录: ${exportedDir}`);
					console.warn(`⚠️ 导出错误: ${errorMessage}`);
					// 不抛出错误，继续使用原始目录处理
				} else {
					// 如果既没有导出成功，也没有原始目录，抛出错误
					throw new Error(`导出失败且未找到结果目录: ${errorMessage}`);
				}
			}

			// 6. 获取 Markdown 内容
			const resultDir = exportedDir;
			console.log(`📁 使用结果目录: ${resultDir}`);
			
			// 如果导出并解压成功，文件已经在知识库目录中
			// 优先使用解压后的文件列表，否则使用原始结果的文件列表
			let resultFiles = result.files || [];
			
			// 如果导出并解压到知识库目录，文件应该已经解压到该目录
			if (exportSuccess && exportedDir === targetResultDir) {
				console.log(`📋 结果文件已在知识库目录中（已解压）`);
				console.log(`📋 原始文件列表:`, resultFiles);
				// 解压后，文件应该直接在 resultDir 目录下
				// 例如：result.mmd, result_det.mmd 等
			}

			// 优先读取顺序：result.mmd（清理后的结果） > refine.mmd > result_det.mmd
			// 注意：如果导出到知识库目录，文件路径需要调整
			let markdownContent = '';
			let markdownFile = '';
			
			// 尝试直接读取知识库目录中的文件（如果导出成功）
			const possibleMarkdownFiles = [
				`${resultDir}/result.mmd`,
				`${resultDir}/refine.mmd`,
				`${resultDir}/result_det.mmd`
			];
			
			// 1. 优先查找 result.mmd（清理后的结果）
			// 如果导出并解压成功，文件应该直接在 resultDir 目录下
			if (exportSuccess && exportedDir === targetResultDir) {
				// 解压后，文件直接在知识库目录中，尝试直接读取
				markdownFile = `${resultDir}/result.mmd`;
				console.log(`📄 尝试读取解压后的 result.mmd (知识库目录)`);
			} else {
				// 否则从原始结果中查找
				const resultFile = resultFiles.find((f: string) => 
					f.includes('result.mmd') || f.endsWith('result.mmd')
				);
				if (resultFile) {
					markdownFile = resultFile.startsWith('/') ? resultFile : `${resultDir}/${resultFile}`;
					console.log(`📄 使用清理结果: result.mmd`);
				} else {
					// 2. 查找 refine.mmd（人工处理精炼结果）
					const refineFile = resultFiles.find((f: string) => 
						f.includes('refine.mmd') || f.endsWith('refine.mmd')
					);
					if (refineFile) {
						markdownFile = refineFile.startsWith('/') ? refineFile : `${resultDir}/${refineFile}`;
						console.log(`📄 使用 人工处理精炼结果: refine.mmd`);
					} else {
						// 3. 查找 result_det.mmd（原始检测结果，作为备选）
						const resultDetFile = resultFiles.find((f: string) => 
							f.includes('result_det.mmd') || f.endsWith('result_det.mmd')
						);
						if (resultDetFile) {
							markdownFile = resultDetFile.startsWith('/') ? resultDetFile : `${resultDir}/${resultDetFile}`;
							console.log(`📄 使用原始检测结果: result_det.mmd`);
						} else {
							// 4. 查找任何 .mmd 文件
							const mmdFiles = resultFiles.filter((f: string) => f.endsWith('.mmd'));
							if (mmdFiles.length > 0) {
								const firstMmd = mmdFiles[0];
								markdownFile = firstMmd.startsWith('/') ? firstMmd : `${resultDir}/${firstMmd}`;
								console.log(`📄 使用找到的第一个 .mmd 文件: ${firstMmd}`);
							}
						}
					}
				}
			}
			
			// 如果解压成功但还没找到文件，尝试直接读取知识库目录中的文件
			if (!markdownFile && exportSuccess && exportedDir === targetResultDir) {
				// 按优先级尝试读取
				const fallbackFiles = [
					`${resultDir}/result.mmd`,
					`${resultDir}/refine.mmd`,
					`${resultDir}/result_det.mmd`
				];
				for (const file of fallbackFiles) {
					markdownFile = file;
					console.log(`📄 尝试读取: ${file}`);
					break; // 先尝试第一个
				}
			}

			if (markdownFile) {
				console.log(`📄 读取 Markdown 文件: ${markdownFile}`);
				
				// 如果文件在知识库目录中，通过后端文件服务读取
				// 否则通过 OCR API 读取
				if (exportedDir === targetResultDir && markdownFile.startsWith(knowledgeDir)) {
					// 文件在知识库目录，通过后端 API 读取
					try {
						const { WEBUI_API_BASE_URL } = await import('$lib/constants');
						// 计算相对路径
						const relativePath = markdownFile.replace(knowledgeDir + '/', '');
						// 注意：WEBUI_API_BASE_URL 已经包含 /api/v1，所以直接使用
						const fileUrl = `${WEBUI_API_BASE_URL}/knowledge/${id}/files/${encodeURIComponent(relativePath)}`;
						
						console.log(`📄 通过后端 API 读取文件: ${fileUrl}`);
						const response = await fetch(fileUrl, {
							headers: {
								'authorization': `Bearer ${localStorage.token}`
							}
						});
						
				if (response.ok) {
					markdownContent = await response.text();
					// 验证内容是否为 Markdown（不是 HTML）
					if (markdownContent.trim().startsWith('<!doctype') || markdownContent.trim().startsWith('<html')) {
						console.error(`❌ 读取到的内容不是 Markdown，而是 HTML！`);
						throw new Error('读取到的内容格式错误（HTML 而非 Markdown）');
					}
				} else {
					throw new Error(`读取文件失败: ${response.status}`);
				}
			} catch (e) {
				console.warn(`⚠️ 通过后端 API 读取失败，尝试通过 OCR API:`, e);
				// 回退到 OCR API
				markdownContent = await getFileContent(markdownFile);
				// 验证内容是否为 Markdown（不是 HTML）
				if (markdownContent.trim().startsWith('<!doctype') || markdownContent.trim().startsWith('<html')) {
					console.error(`❌ OCR API 读取到的内容也不是 Markdown，而是 HTML！`);
					throw new Error('OCR API 返回的内容格式错误（HTML 而非 Markdown）');
				}
			}
		} else {
			// 通过 OCR API 读取
			markdownContent = await getFileContent(markdownFile);
			// 验证内容是否为 Markdown（不是 HTML）
			if (markdownContent.trim().startsWith('<!doctype') || markdownContent.trim().startsWith('<html')) {
				console.error(`❌ OCR API 读取到的内容不是 Markdown，而是 HTML！`);
				throw new Error('OCR API 返回的内容格式错误（HTML 而非 Markdown）');
			}
		}
		
		console.log(`📄 Markdown 内容长度: ${markdownContent.length} 字符`);
		console.log(`📄 Markdown 内容前100字符: ${markdownContent.substring(0, 100)}`);

			// 处理图片路径
			// 如果导出成功，图片在知识库目录中，使用相对路径
			// 否则使用 OCR API URL
			if (exportedDir === targetResultDir) {
				// 图片在知识库目录中，使用相对路径
				// 格式：ocr_result_{taskId}/images/0_0.jpg
				// 需要通过 WebUI 的文件服务访问
				const { WEBUI_API_BASE_URL } = await import('$lib/constants');
				
				// 匹配多种图片路径格式：
				// 1. ![](images/0_0.jpg) - 无 alt 文本
				// 2. ![alt](images/0_0.jpg) - 有 alt 文本
				// 3. ![](./images/0_0.jpg) - 相对路径
				// 4. ![](/images/0_0.jpg) - 绝对路径
					markdownContent = markdownContent.replace(
						/!\[([^\]]*)\]\((\.?\/?)(images\/[^)]+)\)/g,
						(match, alt, prefix, imagePath) => {
							// 构建图片在知识库目录中的相对路径
							// imagePath 已经是 images/0_0.jpg 格式
							const relativeImagePath = `ocr_result_${taskId}/${imagePath}`;
							// 通过后端文件服务访问
							// 注意：WEBUI_API_BASE_URL 已经包含 /api/v1，所以直接使用
							const imageUrl = `${WEBUI_API_BASE_URL}/knowledge/${id}/files/${encodeURIComponent(relativeImagePath)}`;
							console.log(`🖼️ 转换图片路径: ${imagePath} -> ${relativeImagePath} (URL: ${imageUrl})`);
							// 保留原始的 alt 文本（如果有）
							return `![${alt}](${imageUrl})`;
						}
					);
				console.log(`🖼️ 已处理图片路径（使用知识库目录相对路径）`);
			} else {
				// 使用 OCR API URL（回退方案）
				console.warn(`⚠️ 使用 OCR API URL 作为回退方案`);
				const imagesDir = `${resultDir}/images`;
				// 使用 nginx 代理路径（解决跨域问题）
				const ocrApiBaseUrl = typeof window !== 'undefined' 
					? (window as any).__OCR_API_BASE_URL__ || '/ocr-api'
					: 'http://192.168.195.125:8002';
				
				// 匹配多种图片路径格式
				markdownContent = markdownContent.replace(
					/!\[([^\]]*)\]\((\.?\/?)(images\/[^)]+)\)/g,
					(match, alt, prefix, imagePath) => {
						// 提取图片文件名（去掉 images/ 前缀）
						const imageFileName = imagePath.replace(/^images\//, '');
						const fullImagePath = `${imagesDir}/${imageFileName}`;
						const imageUrl = `${ocrApiBaseUrl}/api/file/content?path=${encodeURIComponent(fullImagePath)}`;
						// 保留原始的 alt 文本（如果有）
						return `![${alt}](${imageUrl})`;
					}
				);
				console.log(`🖼️ 已处理图片路径（使用 OCR API URL）`);
			}

			// 更新文件内容为 Markdown
			try {
				// 再次验证内容格式
				if (!markdownContent || markdownContent.trim().startsWith('<!doctype') || markdownContent.trim().startsWith('<html')) {
					throw new Error('Markdown 内容格式错误，无法更新文件');
				}
				
				console.log(`📤 准备更新文件内容，长度: ${markdownContent.length} 字符`);
				// 保存 OCR 任务 ID，以便删除文件时清理 OCR 结果目录
				const updateResult = await updateFileDataContentById(localStorage.token, fileId, markdownContent, taskId);
				console.log(`✅ Markdown 内容已更新到文件: ${fileId}，OCR 任务 ID: ${taskId}`, updateResult);
				
				// 验证更新是否成功（可选：重新获取文件内容验证）
				// 注意：这里不立即验证，因为后端可能需要时间处理

					// 更新文件状态
					knowledge.files = knowledge.files.map((item: any) => {
						if (item.id === fileId) {
							item.status = 'completed';
							item.ocrStatus = 'completed';
							item.hasMarkdown = true;
							item.ocrProgress = 100;
							// 如果之前检测到 VLM 处理完成，确保 VLM 信息被保留
							if (result.use_qwen_vlm && result.qwen_vlm_status === 'completed') {
								item.useQwenVLM = true;
								item.qwenVLMStatus = 'completed';
								item.vlmTaskId = taskId; // 人工处理结果在同一个 OCR 任务中
							}
						}
						return item;
					});
					knowledge = { ...knowledge }; // 触发响应式更新

					toast.success(`PDF 处理完成: ${fileName} 已转换为 Markdown`);
					dispatch('knowledgeUpdated', knowledge);
				} catch (error) {
					console.error('更新文件内容失败:', error);
					toast.error(`Markdown 内容更新失败: ${error instanceof Error ? error.message : String(error)}`);
					
					// 更新文件状态为失败
					knowledge.files = knowledge.files.map((item: any) => {
						if (item.id === fileId) {
							item.status = 'failed';
							item.ocrStatus = 'failed';
							item.ocrError = error instanceof Error ? error.message : String(error);
						}
						return item;
					});
					knowledge = { ...knowledge };
				}
			} else {
				console.warn('⚠️ OCR 结果中未找到 Markdown 文件');
				toast.warning(`PDF 处理完成，但未找到 Markdown 文件`);
				
				// 更新文件状态
				knowledge.files = knowledge.files.map((item: any) => {
					if (item.id === fileId) {
						item.status = 'completed';
						item.ocrStatus = 'completed';
						item.ocrWarning = '未找到 Markdown 文件';
					}
					return item;
				});
				knowledge = { ...knowledge };
			}
		} catch (error) {
			console.error('❌ OCR 处理失败:', error);
			toast.error(`OCR 处理失败: ${error instanceof Error ? error.message : String(error)}`);

			// 更新文件状态为失败
			knowledge.files = knowledge.files.map((item: any) => {
				if (item.id === fileId) {
					item.status = 'failed';
					item.ocrStatus = 'failed';
					item.ocrError = error instanceof Error ? error.message : String(error);
				}
				return item;
			});
			knowledge = { ...knowledge }; // 触发响应式更新
		}
	};

	// 导出方法供父组件使用
	export { uploadFileHandler, uploadDirectoryHandler, syncDirectoryHandler, createFileFromText, handleAddContent, onDragOver, onDragLeave, onDrop, uploadMultipleFiles };
</script>

<!-- 这个组件不渲染任何UI，只提供文件上传功能 -->
<div style="display: none;"></div>
