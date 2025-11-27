<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { marked } from 'marked';
	import RichTextInput from '$lib/components/common/RichTextInput.svelte';
	import FormattingButtons from '$lib/components/common/RichTextInput/FormattingButtons.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	export let content: string = ''; // OCR markdown 内容
	export let knowledgeId: string = '';
	export let ocrTaskId: string = '';
	export let currentPage: number = 1;
	export let onSave: (content: string) => Promise<void>; // 保存回调函数
	export let tableImages: Array<{ name: string; url: string; index: number }> = []; // 表格图片列表
	export let onOpenTableFixModal: ((index: number) => void) | null = null; // 打开表格修复弹窗的回调

	let isEditing = false; // 是否处于编辑模式
	let editor: any = null; // RichTextInput 编辑器实例
	let editedContent = ''; // 编辑后的内容
	let isSaving = false; // 是否正在保存
	let isInTable = false; // 是否在表格中

	// 预处理内容，自动检测并包装LaTeX公式
	const preprocessMathFormulas = (text: string): string => {
		if (!text) return text;
		
		let processedText = text;
		
		// 1. 首先进行全局更正：\textcircled{*} -> \textcircled{/}
		// 这需要在所有处理之前进行，确保所有位置的 textcircled 都被更正
		// 匹配 \textcircled{任何内容}，包括可能的空格
		processedText = processedText.replace(/\\textcircled\s*\{[^}]+\}/g, '\\textcircled{/}');
		
		// 2. 全局修复最常见的错误：}${ 应该替换为 }{
		// 这在 LaTeX 命令参数中是错误的语法
		processedText = processedText.replace(/\}\$\{/g, '}{');
		
		// 3. 修复所有公式块（$$...$$）内的其他错误 $ 使用
		// 匹配 $$...$$ 块（非贪婪匹配）
		const blockMathPattern = /\$\$([\s\S]*?)\$\$/g;
		processedText = processedText.replace(blockMathPattern, (match, content) => {
			// 在块级公式内部，确保没有残留的错误 $ 符号
			// 修复 \frac{...}${...} 模式（如果还有残留）
			let fixedContent = content.replace(/(\\frac\s*\{[^}]*)\}\$\{([^}]*)\}/g, '$1}{$2}');
			// 修复其他命令中的类似错误
			fixedContent = fixedContent.replace(/(\\[a-zA-Z]+\s*\{[^}]*)\}\$\{([^}]*)\}/g, '$1}{$2}');
			return `$$${fixedContent}$$`;
		});
		
		// 4. 修复行内公式 $...$ 中的错误 $ 使用
		// 使用临时标记避免匹配 $$ 块
		processedText = processedText.replace(/\$\$/g, '__DOUBLE_DOLLAR__');
		// 处理行内公式
		processedText = processedText.replace(/\$([^$]+?)\$/g, (match, content) => {
			let fixedContent = content.replace(/\}\$\{/g, '}{');
			fixedContent = fixedContent.replace(/(\\frac\s*\{[^}]*)\}\$\{([^}]*)\}/g, '$1}{$2}');
			fixedContent = fixedContent.replace(/(\\[a-zA-Z]+\s*\{[^}]*)\}\$\{([^}]*)\}/g, '$1}{$2}');
			return `$${fixedContent}$`;
		});
		// 恢复 $$ 标记
		processedText = processedText.replace(/__DOUBLE_DOLLAR__/g, '$$');
		
		// 5. 处理包含 \tag 的公式，确保使用块级公式
		if (processedText.includes('\\tag')) {
			// 查找包含 \tag 的公式（可能在 $$...$$ 块中，也可能不在）
			const tagPattern = /(\$\$)?([^\n]*?\\tag\{[^}]+\})(\$\$)?/g;
			processedText = processedText.replace(tagPattern, (match, startDollar, content, endDollar) => {
				// 修复内容中的错误 $ 符号
				let fixedContent = content.replace(/\}\$\{/g, '}{');
				fixedContent = fixedContent.replace(/(\\frac\s*\{[^}]*)\}\$\{([^}]*)\}/g, '$1}{$2}');
				fixedContent = fixedContent.replace(/(\\[a-zA-Z]+\s*\{[^}]*)\}\$\{([^}]*)\}/g, '$1}{$2}');
				
				// 如果已经有 $$，保持原样
				if (startDollar && endDollar) {
					return `$$${fixedContent}$$`;
				}
				// 如果没有 $$，添加它们（\tag 需要块级公式）
				return `$$${fixedContent}$$`;
			});
		}
		
		// 6. 如果没有公式分隔符，自动检测并包装LaTeX公式
		if (!processedText.includes('$') && !processedText.includes('\\(') && !processedText.includes('\\[')) {
			// 检测LaTeX命令模式：\command{...} 如 \mathrm{Dh}, \frac{1}{2} 等
			const latexCommandPattern = /\\([a-zA-Z]+|alpha|beta|gamma|delta|epsilon|pi|sigma|mu|lambda|theta|phi|omega|Delta|Gamma|Theta|Phi|Omega|Sigma|Lambda|infty|partial|nabla|cdot|times|div|pm|mp|leq|geq|neq|approx|equiv|propto|in|notin|subset|supset|cup|cap|emptyset|exists|forall|rightarrow|leftarrow|Rightarrow|Leftarrow|leftrightarrow|Leftrightarrow|mapsto|to|gets|land|lor|lnot|wedge|vee|oplus|otimes|ominus|odot|circ|bullet|star|ast|dagger|ddagger|ldots|cdots|vdots|ddots|hat|check|breve|acute|grave|tilde|bar|vec|dot|ddot|overline|underline|overbrace|underbrace|sqrt|root|frac|binom|choose|stackrel|overset|underset|limits|nolimits|left|right|middle|big|Big|bigg|Bigg)\s*\{[^}]*\}/g;
			
			// 检测并包装LaTeX公式
			const matches = [...processedText.matchAll(latexCommandPattern)];
			
			// 从后往前处理，避免位置偏移
			for (let i = matches.length - 1; i >= 0; i--) {
				const match = matches[i];
				const start = match.index!;
				const end = start + match[0].length;
				
				// 检查前后是否已经有分隔符
				const before = start > 0 ? processedText[start - 1] : '';
				const after = end < processedText.length ? processedText[end] : '';
				
				if (before !== '$' && after !== '$' && before !== '(' && after !== ')') {
					// 包装公式
					processedText = processedText.slice(0, start) + '$' + match[0] + '$' + processedText.slice(end);
				}
			}
		}
		
		return processedText;
	};

	// 保存图片到知识库的 images 文件夹
	const saveImageToKnowledgeBase = async (file: File): Promise<string> => {
		try {
			// 生成文件名：manual_时间戳_原文件名
			const timestamp = Date.now();
			const originalName = file.name || 'pasted_image';
			
			// 从文件名获取扩展名，如果没有则从 MIME 类型推断
			let extension = originalName.split('.').pop()?.toLowerCase();
			if (!extension || extension === originalName) {
				// 从 MIME 类型推断扩展名
				const mimeToExt: Record<string, string> = {
					'image/png': 'png',
					'image/jpeg': 'jpg',
					'image/jpg': 'jpg',
					'image/gif': 'gif',
					'image/webp': 'webp',
					'image/bmp': 'bmp',
					'image/svg+xml': 'svg'
				};
				extension = mimeToExt[file.type] || 'png'; // 默认使用 png
			}
			
			const fileName = `manual_${timestamp}_${originalName.replace(/[^a-zA-Z0-9._-]/g, '_')}`;
			
			// 如果文件名太长，截断
			const maxLength = 100;
			const finalFileName = fileName.length > maxLength 
				? `manual_${timestamp}.${extension}`
				: fileName;
			
			// 图片保存路径
			const imagePath = `ocr_result_${ocrTaskId}/images/${finalFileName}`;
			
			// 将文件转换为 base64
			const base64 = await new Promise<string>((resolve, reject) => {
				const reader = new FileReader();
				reader.onload = () => {
					const result = reader.result as string;
					// 移除 data:image/...;base64, 前缀
					const base64Data = result.split(',')[1];
					resolve(base64Data);
				};
				reader.onerror = reject;
				reader.readAsDataURL(file);
			});
			
			// 保存文件（使用 base64 编码）
			const response = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files-save`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${localStorage.token}`,
				},
				body: JSON.stringify({
					file_path: imagePath,
					content: base64,
					is_base64: true, // 标记为 base64 编码的二进制文件
				}),
			});
			
			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(errorText || `保存图片失败: ${response.status}`);
			}
			
			// 返回图片的 URL（用于在编辑器中显示）
			const imageUrl = `${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/files/${encodeURIComponent(imagePath)}`;
			console.log(`✅ 图片已保存: ${imagePath} -> ${imageUrl}`);
			return imageUrl;
		} catch (error) {
			console.error('保存图片失败:', error);
			throw error;
		}
	};

	// 处理文件粘贴
	const handleFilePaste = async (currentEditor: any, files: File[], htmlContent: string) => {
		// 只处理图片文件
		const imageFiles = files.filter(file => file.type.startsWith('image/'));
		
		if (imageFiles.length === 0) {
			return false; // 让默认处理继续
		}
		
		// 如果有 HTML 内容，让其他扩展处理
		if (htmlContent) {
			return false;
		}
		
		// 处理每个图片文件
		for (const file of imageFiles) {
			try {
				// 显示上传提示
				const fileName = file.name || '剪贴板图片';
				toast.info(`正在保存图片: ${fileName}...`);
				
				// 保存图片到知识库
				const imageUrl = await saveImageToKnowledgeBase(file);
				
				// 插入图片到编辑器
				currentEditor
					.chain()
					.focus()
					.insertContent({
						type: 'image',
						attrs: {
							src: imageUrl,
							alt: fileName,
						}
					})
					.run();
				
				toast.success(`图片已保存: ${fileName}`);
			} catch (error) {
				console.error('粘贴图片失败:', error);
				toast.error(`保存图片失败: ${error instanceof Error ? error.message : String(error)}`);
			}
		}
		
		return true; // 已处理，阻止默认行为
	};

	// 进入编辑模式
	const enterEditMode = () => {
		// 如果内容包含Markdown图片语法，需要先转换为HTML
		let contentToEdit = content;
		
		// 检查是否包含Markdown图片语法 ![](url) 或 ![alt](url)
		// 但不包含HTML的<img>标签
		if (contentToEdit && !contentToEdit.includes('<img') && contentToEdit.includes('![')) {
			// 使用marked将Markdown转换为HTML（包括图片）
			// marked会自动将 ![alt](url) 转换为 <img src="url" alt="alt" />
			contentToEdit = marked.parse(contentToEdit);
		}
		
		editedContent = contentToEdit;
		isEditing = true;
	};

	// 取消编辑
	const cancelEdit = () => {
		editedContent = content;
		isEditing = false;
	};

	// 将Markdown图片语法转换为HTML格式
	const convertMarkdownImagesToHTML = (text: string): string => {
		// 匹配Markdown图片语法: ![alt](url) 或 ![alt](url "title")
		// 支持多种格式：
		// - ![alt](url)
		// - ![](url)
		// - ![alt](url "title")
		const markdownImageRegex = /!\[([^\]]*)\]\(([^)]+)(?:\s+"([^"]+)")?\)/g;
		
		return text.replace(markdownImageRegex, (match, alt, url, title) => {
			// 清理URL（去除可能的引号）
			const cleanUrl = url.trim().replace(/^["']|["']$/g, '');
			// 构建HTML img标签
			let imgTag = `<img src="${cleanUrl}"`;
			
			// 添加alt属性（如果有）
			if (alt && alt.trim()) {
				imgTag += ` alt="${alt.trim()}"`;
			} else {
				imgTag += ` alt=""`;
			}
			
			// 添加title属性（如果有）
			if (title && title.trim()) {
				imgTag += ` title="${title.trim()}"`;
			}
			
			imgTag += ` />`;
			console.log(`🖼️ 转换Markdown图片: ${match} -> ${imgTag}`);
			return imgTag;
		});
	};

	// 保存编辑
	const saveEdit = async () => {
		if (!editor) {
			toast.error('编辑器未初始化');
			return;
		}

		try {
			isSaving = true;
			
			// 从编辑器获取HTML内容（保持HTML表格格式）
			const htmlContent = editor.getHTML();
			let contentToSave = '';
			
			// 检查原始内容是否包含HTML表格
			const hasOriginalTable = content && content.includes('<table');
			
			// 检查编辑后的内容是否包含HTML表格
			const hasEditedTable = htmlContent.includes('<table');
			
			if (hasOriginalTable || hasEditedTable) {
				// 如果原始内容或编辑后内容包含HTML表格，使用HTML格式保存
				contentToSave = htmlContent;
				console.log('📊 检测到HTML表格，使用HTML格式保存');
			} else {
				// 如果没有表格，使用editedContent（可能是markdown）
				contentToSave = editedContent || htmlContent || content || '';
			}
			
			// 检查并转换Markdown图片语法为HTML格式
			// 即使是在HTML内容中，也可能包含Markdown图片语法（用户手动输入的）
			if (contentToSave.includes('![') && contentToSave.includes('](')) {
				contentToSave = convertMarkdownImagesToHTML(contentToSave);
				console.log('🖼️ 已转换Markdown图片为HTML格式');
			}
			
			if (!contentToSave || contentToSave.trim() === '') {
				toast.error('内容为空，无法保存');
				return;
			}
			
			// 调用保存回调
			await onSave(contentToSave);
			
			// 更新内容
			content = contentToSave;
			isEditing = false;
			
			toast.success('OCR 结果已保存');
		} catch (error) {
			console.error('保存失败:', error);
			toast.error(`保存失败: ${error instanceof Error ? error.message : String(error)}`);
		} finally {
			isSaving = false;
		}
	};

	// 处理内容变化
	const handleContentChange = (data: { html: string; md: string; json: any }) => {
		// 对于包含HTML表格的内容，优先使用HTML格式以保持表格结构
		// 检查是否包含HTML表格标签
		if (data.html && data.html.includes('<table')) {
			editedContent = data.html; // 使用HTML格式保持表格结构
		} else {
			editedContent = data.md || data.html; // 其他内容使用markdown
		}
	};

	// 监听 content 变化，同步到编辑器
	$: if (content && !isEditing) {
		editedContent = content;
	}
	
	// 当进入编辑模式时，确保 editedContent 有值
	$: if (isEditing && !editedContent && content) {
		editedContent = content;
	}
	
	// 处理内容变化 - 优先保持HTML格式
	const handleContentChangeRaw = (data: { html: string; md: string; json: any }) => {
		// 使用raw模式时，直接使用HTML
		editedContent = data.html;
	};

	// 监听编辑器状态，检测是否在表格中
	let tableCheckInterval: ReturnType<typeof setInterval> | null = null;
	
	// 检查表格状态的函数
	const checkTableState = () => {
		if (editor && isEditing) {
			isInTable = editor.isActive('table') || editor.isActive('tableRow') || editor.isActive('tableCell');
		} else {
			isInTable = false;
		}
	};
	
	// 当编辑器或编辑状态变化时，更新表格状态
	$: if (editor && isEditing) {
		// 清除之前的定时器
		if (tableCheckInterval) {
			clearInterval(tableCheckInterval);
			tableCheckInterval = null;
		}
		
		// 初始检查
		checkTableState();
		
		// 监听选择变化
		if (editor.on) {
			editor.on('selectionUpdate', checkTableState);
			editor.on('update', checkTableState);
		}
		
		// 定期检查（作为备用，确保状态同步）
		tableCheckInterval = setInterval(checkTableState, 200);
	} else {
		// 不在编辑模式时，清除定时器
		if (tableCheckInterval) {
			clearInterval(tableCheckInterval);
			tableCheckInterval = null;
		}
		isInTable = false;
	}
	
	// 组件销毁时清理定时器
	onDestroy(() => {
		if (tableCheckInterval) {
			clearInterval(tableCheckInterval);
			tableCheckInterval = null;
		}
	});
</script>

<div class="flex flex-col h-full w-full">
	<!-- 工具栏 -->
	<div class="flex items-center justify-between p-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex-shrink-0">
		<div class="text-sm font-medium text-gray-700 dark:text-gray-300">
			OCR 结果编辑
		</div>
		<div class="flex items-center gap-2">
			{#if isEditing}
				<button
					class="px-3 py-1.5 text-xs bg-green-500 hover:bg-green-600 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
					disabled={isSaving}
					on:click={saveEdit}
				>
					{#if isSaving}
						<div class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
					{:else}
						<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
						</svg>
					{/if}
					<span>保存</span>
				</button>
				<button
					class="px-3 py-1.5 text-xs bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded transition-colors"
					disabled={isSaving}
					on:click={cancelEdit}
				>
					取消
				</button>
			{:else}
				<button
					class="px-3 py-1.5 text-xs bg-blue-500 hover:bg-blue-600 text-white rounded transition-colors flex items-center gap-1"
					on:click={enterEditMode}
				>
					<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
					</svg>
					<span>编辑</span>
				</button>
			{/if}
		</div>
	</div>

	<!-- 内容区域 -->
	<div class="flex-1 overflow-hidden min-h-0 flex flex-col">
		{#if isEditing}
			<!-- 编辑模式：使用 RichTextInput -->
			<div class="flex-1 min-h-0 overflow-hidden flex flex-col">
				<!-- 固定的格式化工具栏 -->
				<div class="sticky top-0 z-50 flex-shrink-0 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-2">
					<FormattingButtons {editor} />
				</div>
				<!-- 可滚动的内容区域 -->
				<div class="flex-1 min-h-0 overflow-y-auto p-4" style="scroll-behavior: smooth;">
					<RichTextInput
						bind:editor
						bind:value={editedContent}
						onChange={handleContentChange}
						richText={true}
						editable={true}
						showFormattingToolbar={false}
						fixedToolbar={false}
						raw={!!(content && content.includes('<table'))}
						className="prose prose-sm max-w-none dark:prose-invert"
						placeholder="开始编辑 OCR 结果..."
						image={true}
						fileHandler={true}
						onFilePaste={handleFilePaste}
					/>
				</div>
			</div>
		{:else}
			<!-- 查看模式：使用 Markdown 组件 -->
			<div class="h-full w-full p-4 overflow-y-auto">
				{#if content && content.trim() && !content.includes('暂无') && !content.includes('加载失败')}
					{@const processedContent = preprocessMathFormulas(content)}
					<Markdown
						content={processedContent}
						done={true}
						editCodeBlock={false}
						topPadding={true}
					/>
				{:else}
					<div class="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
						<div class="text-center">
							<div class="text-lg mb-2">📄</div>
							<div class="text-sm">暂无 OCR 结果</div>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

