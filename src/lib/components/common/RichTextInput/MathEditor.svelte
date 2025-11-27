<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	
	export let editor: any = null;
	export let isOpen: boolean = false;
	
	const dispatch = createEventDispatcher();
	
	let formulaInput = '';
	let isInline = true; // 行内公式还是块级公式
	let katex: any = null;
	let textareaElement: HTMLTextAreaElement | null = null;
	
	onMount(async () => {
		// 动态导入 katex 用于预览
		const katexModule = await import('katex');
		katex = katexModule.default;
		await import('katex/dist/katex.min.css');
	});
	
	// 常用数学符号
	const mathSymbols = [
		{ label: '±', latex: '\\pm' },
		{ label: '×', latex: '\\times' },
		{ label: '÷', latex: '\\div' },
		{ label: '≠', latex: '\\neq' },
		{ label: '≤', latex: '\\leq' },
		{ label: '≥', latex: '\\geq' },
		{ label: '≈', latex: '\\approx' },
		{ label: '∞', latex: '\\infty' },
		{ label: '∑', latex: '\\sum' },
		{ label: '∏', latex: '\\prod' },
		{ label: '∫', latex: '\\int' },
		{ label: '√', latex: '\\sqrt' },
		{ label: 'α', latex: '\\alpha' },
		{ label: 'β', latex: '\\beta' },
		{ label: 'γ', latex: '\\gamma' },
		{ label: 'δ', latex: '\\delta' },
		{ label: 'ε', latex: '\\epsilon' },
		{ label: 'π', latex: '\\pi' },
		{ label: 'θ', latex: '\\theta' },
		{ label: 'λ', latex: '\\lambda' },
		{ label: 'μ', latex: '\\mu' },
		{ label: 'σ', latex: '\\sigma' },
		{ label: 'Δ', latex: '\\Delta' },
		{ label: 'Ω', latex: '\\Omega' },
	];
	
	// 在输入框中插入文本（在光标位置）
	const insertIntoTextarea = (text: string, cursorOffset: number = 0) => {
		if (!textareaElement) return;
		
		const start = textareaElement.selectionStart;
		const end = textareaElement.selectionEnd;
		const currentValue = formulaInput;
		
		// 在光标位置插入文本
		const newValue = currentValue.substring(0, start) + text + currentValue.substring(end);
		formulaInput = newValue;
		
		// 设置新的光标位置
		setTimeout(() => {
			if (textareaElement) {
				const newCursorPos = start + text.length + cursorOffset;
				textareaElement.setSelectionRange(newCursorPos, newCursorPos);
				textareaElement.focus();
			}
		}, 10);
	};
	
	// 插入符号到输入框
	const insertSymbol = (latex: string) => {
		insertIntoTextarea(latex);
	};
	
	// 插入分数到输入框
	const insertFraction = () => {
		insertIntoTextarea('\\frac{}{}', -2); // 光标移动到第一个大括号内
	};
	
	// 插入上标到输入框
	const insertSuperscript = () => {
		insertIntoTextarea('^{}', -1); // 光标移动到大括号内
	};
	
	// 插入下标到输入框
	const insertSubscript = () => {
		insertIntoTextarea('_{}', -1); // 光标移动到大括号内
	};
	
	// 插入根号到输入框
	const insertSqrt = () => {
		insertIntoTextarea('\\sqrt{}', -1); // 光标移动到大括号内
	};
	
	// 插入括号到输入框
	const insertBrackets = (type: 'left' | 'right' | 'leftright') => {
		if (type === 'leftright') {
			insertIntoTextarea('\\left(\\right)', -8); // 光标移动到括号中间
		} else if (type === 'left') {
			insertIntoTextarea('\\left(');
		} else {
			insertIntoTextarea('\\right)');
		}
	};
	
	// 插入公式
	const insertFormula = () => {
		if (!editor || !formulaInput.trim()) return;
		
		const formula = formulaInput.trim();
		const wrappedFormula = isInline ? `$${formula}$` : `$$${formula}$$`;
		
		editor.chain().focus().insertContent(wrappedFormula).run();
		
		// 重置
		formulaInput = '';
		dispatch('close');
	};
	
	// 关闭编辑器
	const closeEditor = () => {
		formulaInput = '';
		dispatch('close');
	};
</script>

{#if isOpen}
	<div 
		class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50" 
		on:click={closeEditor}
		role="dialog"
		aria-modal="true"
		aria-labelledby="math-editor-title"
	>
		<div 
			class="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-4 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto" 
			on:click|stopPropagation
			role="document"
		>
			<!-- 标题栏 -->
			<div class="flex items-center justify-between mb-4">
				<h3 id="math-editor-title" class="text-lg font-semibold text-gray-900 dark:text-gray-100">公式编辑器</h3>
				<button
					class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
					on:click={closeEditor}
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
					</svg>
				</button>
			</div>
			
			<!-- 公式类型选择 -->
			<div class="flex gap-2 mb-4">
				<button
					class="px-3 py-1.5 rounded text-sm {isInline ? 'bg-blue-500 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'}"
					on:click={() => isInline = true}
				>
					行内公式 ($...$)
				</button>
				<button
					class="px-3 py-1.5 rounded text-sm {!isInline ? 'bg-blue-500 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300'}"
					on:click={() => isInline = false}
				>
					块级公式 ($$...$$)
				</button>
			</div>
			
			<!-- 常用结构按钮 -->
			<div class="mb-4">
				<div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">常用结构</div>
				<div class="flex flex-wrap gap-2">
					<button
						class="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-sm text-gray-700 dark:text-gray-300"
						on:click={insertFraction}
					>
						分数 (frac)
					</button>
					<button
						class="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-sm text-gray-700 dark:text-gray-300"
						on:click={insertSuperscript}
					>
						上标 (^)
					</button>
					<button
						class="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-sm text-gray-700 dark:text-gray-300"
						on:click={insertSubscript}
					>
						下标 (_)
					</button>
					<button
						class="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-sm text-gray-700 dark:text-gray-300"
						on:click={insertSqrt}
					>
						根号 (√)
					</button>
					<button
						class="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-sm text-gray-700 dark:text-gray-300"
						on:click={() => insertBrackets('leftright')}
					>
						括号 (left/right)
					</button>
				</div>
			</div>
			
			<!-- 数学符号 -->
			<div class="mb-4">
				<div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">数学符号</div>
				<div class="flex flex-wrap gap-2">
					{#each mathSymbols as symbol}
						<button
							class="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded text-sm text-gray-700 dark:text-gray-300"
							on:click={() => insertSymbol(symbol.latex)}
							title={symbol.latex}
						>
							{symbol.label}
						</button>
					{/each}
				</div>
			</div>
			
			<!-- 公式输入框 -->
			<div class="mb-4">
				<label for="formula-input" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					LaTeX 公式
				</label>
				<textarea
					id="formula-input"
					bind:this={textareaElement}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 font-mono text-sm"
					rows="4"
					bind:value={formulaInput}
					placeholder="输入 LaTeX 公式，例如: x^2 + y^2 = r^2"
				></textarea>
			</div>
			
			<!-- 预览 -->
			{#if formulaInput.trim() && katex}
				<div class="mb-4 p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700">
					<div class="text-xs text-gray-500 dark:text-gray-400 mb-2">预览:</div>
					<div class="text-base overflow-x-auto">
						{@html (() => {
							try {
								const formula = formulaInput.trim();
								// 修复常见的错误：}${ 为 }{
								const fixedFormula = formula.replace(/\}\$\{/g, '}{');
								return katex.renderToString(fixedFormula, { 
									displayMode: !isInline,
									throwOnError: false,
									strict: false,
									trust: true
								});
							} catch (e) {
								const errorMsg = e instanceof Error ? e.message : String(e);
								return `<span class="text-red-500">公式错误: ${errorMsg}</span>`;
							}
						})()}
					</div>
				</div>
			{:else if formulaInput.trim()}
				<div class="mb-4 p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700">
					<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">预览 (加载中...):</div>
					<div class="text-base font-mono">
						{isInline ? `$${formulaInput.trim()}$` : `$$${formulaInput.trim()}$$`}
					</div>
				</div>
			{/if}
			
			<!-- 操作按钮 -->
			<div class="flex justify-end gap-2">
				<button
					class="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded text-gray-700 dark:text-gray-300"
					on:click={closeEditor}
				>
					取消
				</button>
				<button
					class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={insertFormula}
					disabled={!formulaInput.trim()}
				>
					插入公式
				</button>
			</div>
		</div>
	</div>
{/if}

