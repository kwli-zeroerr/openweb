<script lang="ts">
	import DOMPurify from 'dompurify';
	import type { Token } from 'marked';
	import { onMount } from 'svelte';

	import { WEBUI_BASE_URL } from '$lib/constants';
	import { settings } from '$lib/stores';
	import Source from './Source.svelte';

	export let id: string;
	export let token: Token;

	export let onSourceClick: Function = () => {};

	// Simple state management for HTML tables
	let htmlTableStates: Record<string, boolean> = {};
	let forceUpdate = 0; // Force reactivity trigger

	let html: string | null = null;
	let katex: any = null;

	onMount(async () => {
		// 动态导入 katex
		const katexModule = await import('katex');
		katex = katexModule.default;
		await import('katex/dist/katex.min.css');
	});

	// 处理 HTML 中的 LaTeX 公式
	const processMathInHTML = (htmlContent: string): string => {
		if (!htmlContent) return htmlContent;
		
		// 先进行全局更正：\textcircled{*} -> \textcircled{/}
		// 这需要在所有处理之前进行，确保所有位置的 textcircled 都被更正
		// 匹配 \textcircled{任何内容}，包括可能的空格
		htmlContent = htmlContent.replace(/\\textcircled\s*\{[^}]+\}/g, '\\textcircled{/}');
		
		if (!katex) return htmlContent; // 如果 katex 未加载，只进行更正，不渲染公式
		
		// 处理行内公式 \(...\) 和 $...$
		htmlContent = htmlContent.replace(/\$([^$]+?)\$/g, (match, formula) => {
			try {
				// 修复常见的错误：}${ 为 }{
				formula = formula.replace(/\}\$\{/g, '}{');
				// 再次更正 textcircled（确保公式内的也被更正）
				formula = formula.replace(/\\textcircled\s*\{[^}]+\}/g, '\\textcircled{/}');
				return katex.renderToString(formula, { 
					displayMode: false,
					throwOnError: false,
					strict: false,
					trust: true
				});
			} catch (e) {
				return match; // 如果渲染失败，返回原始内容
			}
		});
		
		// 处理块级公式 \[...\] 和 $$...$$
		htmlContent = htmlContent.replace(/\$\$([\s\S]*?)\$\$/g, (match, formula) => {
			try {
				// 修复常见的错误：}${ 为 }{
				formula = formula.replace(/\}\$\{/g, '}{');
				// 再次更正 textcircled（确保公式内的也被更正）
				formula = formula.replace(/\\textcircled\s*\{[^}]+\}/g, '\\textcircled{/}');
				return katex.renderToString(formula.trim(), { 
					displayMode: true,
					throwOnError: false,
					strict: false,
					trust: true
				});
			} catch (e) {
				return match; // 如果渲染失败，返回原始内容
			}
		});
		
		// 处理 \(...\) 格式
		htmlContent = htmlContent.replace(/\\\(([\s\S]*?)\\\)/g, (match, formula) => {
			try {
				formula = formula.replace(/\}\$\{/g, '}{');
				// 再次更正 textcircled（确保公式内的也被更正）
				formula = formula.replace(/\\textcircled\{[^}]+\}/g, '\\textcircled{/}');
				return katex.renderToString(formula, { 
					displayMode: false,
					throwOnError: false,
					strict: false,
					trust: true
				});
			} catch (e) {
				return match;
			}
		});
		
		// 处理 \[...\] 格式
		htmlContent = htmlContent.replace(/\\\[([\s\S]*?)\\\]/g, (match, formula) => {
			try {
				formula = formula.replace(/\}\$\{/g, '}{');
				// 再次更正 textcircled（确保公式内的也被更正）
				formula = formula.replace(/\\textcircled\{[^}]+\}/g, '\\textcircled{/}');
				return katex.renderToString(formula.trim(), { 
					displayMode: true,
					throwOnError: false,
					strict: false,
					trust: true
				});
			} catch (e) {
				return match;
			}
		});
		
		return htmlContent;
	};

	$: if (token.type === 'html' && token?.text) {
		let sanitized = DOMPurify.sanitize(token.text);
		// 如果是表格，处理其中的 LaTeX 公式和更正 textcircled
		if (sanitized.includes('<table')) {
			html = processMathInHTML(sanitized);
		} else {
			// 即使不是表格，也要进行 textcircled 更正
			html = sanitized.replace(/\\textcircled\s*\{[^}]+\}/g, '\\textcircled{/}');
		}
	} else {
		html = null;
	}
	
	// 当 katex 加载后，重新处理 HTML（如果是表格）
	$: if (katex && html && token?.text && token.text.includes('<table')) {
		let sanitized = DOMPurify.sanitize(token.text);
		html = processMathInHTML(sanitized);
	}
</script>

{#if token.type === 'html'}
	{#if html && html.includes('<video')}
		{@const video = html.match(/<video[^>]*>([\s\S]*?)<\/video>/)}
		{@const videoSrc = video && video[1]}
		{#if videoSrc}
			<!-- svelte-ignore a11y-media-has-caption -->
			<video
				class="w-full my-2"
				src={videoSrc.replaceAll('&amp;', '&')}
				title="Video player"
				frameborder="0"
				referrerpolicy="strict-origin-when-cross-origin"
				controls
				allowfullscreen
			></video>
		{:else}
			{token.text}
		{/if}
	{:else if html && html.includes('<audio')}
		{@const audio = html.match(/<audio[^>]*>([\s\S]*?)<\/audio>/)}
		{@const audioSrc = audio && audio[1]}
		{#if audioSrc}
			<!-- svelte-ignore a11y-media-has-caption -->
			<audio
				class="w-full my-2"
				src={audioSrc.replaceAll('&amp;', '&')}
				title="Audio player"
				controls
			></audio>
		{:else}
			{token.text}
		{/if}
	{:else if token.text && token.text.match(/<iframe\s+[^>]*src="https:\/\/www\.youtube\.com\/embed\/([a-zA-Z0-9_-]{11})(?:\?[^"]*)?"[^>]*><\/iframe>/)}
		{@const match = token.text.match(
			/<iframe\s+[^>]*src="https:\/\/www\.youtube\.com\/embed\/([a-zA-Z0-9_-]{11})(?:\?[^"]*)?"[^>]*><\/iframe>/
		)}
		{@const ytId = match && match[1]}
		{#if ytId}
			<iframe
				class="w-full aspect-video my-2"
				src={`https://www.youtube.com/embed/${ytId}`}
				title="YouTube video player"
				frameborder="0"
				allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
				referrerpolicy="strict-origin-when-cross-origin"
				allowfullscreen
			>
			</iframe>
		{/if}
	{:else if token.text && token.text.includes('<iframe')}
		{@const match = token.text.match(/<iframe\s+[^>]*src="([^"]+)"[^>]*><\/iframe>/)}
		{@const iframeSrc = match && match[1]}
		{#if iframeSrc}
			<iframe
				class="w-full my-2"
				src={iframeSrc}
				title="Embedded content"
				frameborder="0"
				sandbox
				onload="this.style.height=(this.contentWindow.document.body.scrollHeight+20)+'px';"
			></iframe>
		{:else}
			{token.text}
		{/if}
	{:else if token.text && token.text.includes('<status')}
		{@const match = token.text.match(/<status title="([^"]+)" done="(true|false)" ?\/?>/)}
		{@const statusTitle = match && match[1]}
		{@const statusDone = match && match[2] === 'true'}
		{#if statusTitle}
			<div class="flex flex-col justify-center -space-y-0.5">
				<div
					class="{statusDone === false
						? 'shimmer'
						: ''} text-gray-500 dark:text-gray-500 line-clamp-1 text-wrap"
				>
					{statusTitle}
				</div>
			</div>
		{:else}
			{token.text}
		{/if}
	{:else if token.text.includes(`<file type="html"`)}
		{@const match = token.text.match(/<file type="html" id="([^"]+)"/)}
		{@const fileId = match && match[1]}
		{#if fileId}
			<iframe
				class="w-full my-2"
				src={`${WEBUI_BASE_URL}/api/v1/files/${fileId}/content/html`}
				title="Content"
				frameborder="0"
				sandbox={`allow-scripts allow-downloads${($settings?.iframeSandboxAllowForms ?? false)
					? ' allow-forms'
					: ''}${($settings?.iframeSandboxAllowSameOrigin ?? false) ? ' allow-same-origin' : ''}`}
				referrerpolicy="strict-origin-when-cross-origin"
				allowfullscreen
				width="100%"
				onload="this.style.height=(this.contentWindow.document.body.scrollHeight+20)+'px';"
			></iframe>
		{/if}
	{:else if token.text.includes(`<source_id`)}
		<Source {id} {token} onClick={onSourceClick} />
	{:else if token.text.includes('<table')}
		{@const htmlTableId = `html-table-${id}-${token.text.slice(0, 20).replace(/[^a-zA-Z0-9]/g, '')}`}
		{@const getKey = () => `${id}:${htmlTableId}`}
		
		<!-- HTML 表格折叠功能 -->
		{@const getCollapsed = () => {
			forceUpdate; // Trigger reactivity
			return htmlTableStates[htmlTableId] || false;
		}}
		{@const toggleCollapsed = () => {
			console.log('HTML table toggleCollapsed called for:', htmlTableId);
			const currentState = htmlTableStates[htmlTableId] || false;
			const next = !currentState;
			htmlTableStates[htmlTableId] = next;
			htmlTableStates = { ...htmlTableStates }; // Trigger reactivity
			forceUpdate++; // Force reactivity update
			console.log('HTML table collapsed state toggled:', htmlTableId, next);
		}}
		
		<!-- HTML 表格支持 -->
		<div class="relative group mb-4" data-html-table-id={htmlTableId}>
			<!-- HTML 表格折叠按钮 -->
			<div class="absolute top-0 right-0 z-10 opacity-80 hover:opacity-100 transition-opacity duration-200">
				<button
					class="p-1.5 rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm shadow-sm hover:bg-white dark:hover:bg-gray-700 transition-all duration-200 border border-gray-200 dark:border-gray-600"
					on:click|stopPropagation={toggleCollapsed}
					title={getCollapsed() ? "展开表格" : "折叠表格"}
				>
					{#if getCollapsed()}
						<svg class="w-3.5 h-3.5 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
						</svg>
					{:else}
						<svg class="w-3.5 h-3.5 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
						</svg>
					{/if}
				</button>
			</div>

			<!-- 折叠后的摘要显示 -->
			{#if getCollapsed()}
				<div class="html-table-summary bg-gray-50 dark:bg-gray-700 p-4 rounded-lg mb-2 transition-all duration-300 ease-in-out">
					<div class="text-sm text-gray-600 dark:text-gray-300 mb-2">
						<span class="font-semibold">HTML 表格摘要:</span>
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400">
						<span class="italic">点击展开按钮查看完整表格内容</span>
					</div>
				</div>
			{/if}

			<!-- HTML 表格内容（折叠时隐藏） -->
			{#if !getCollapsed()}
			<div class="transition-all duration-300 ease-in-out">
				<div class="html-table-container relative w-full overflow-hidden">
				<style>
					.html-table-container {
						width: 100%;
					}
					.html-table-container table {
						width: 100%;
						max-width: 100%;
						border-collapse: collapse;
						border-spacing: 0;
						border: 2px solid #e5e7eb;
						border-radius: 8px;
						margin: 1rem 0;
						overflow: hidden;
						background-color: #ffffff;
						table-layout: fixed;
						word-break: break-word;
						white-space: normal;
					}
					.html-table-container table tr {
						background-color: #ffffff;
					}
					.html-table-container table tr:nth-child(1) {
						background-color: #f9fafb;
						color: #1f2937;
					}
					.html-table-container table th,
					.html-table-container table td {
						padding: 0.75rem 1rem;
						font-size: 14px;
						border: 1px solid #e5e7eb;
						text-align: left;
						vertical-align: top;
						line-height: 1.5;
						min-width: 70px;
						/* 确保文本大小写正常显示 */
						text-transform: none !important;
						word-break: break-word;
						white-space: normal;
					}
					.html-table-container table th {
						font-weight: 600;
						color: #1f2937;
					}
					.html-table-container table td {
						font-weight: 400;
						color: #111827;
					}
					.html-table-container table tbody tr:nth-child(even) {
						background-color: #fdfdfd;
					}
					.html-table-container table tr:hover {
						background-color: #f3f4f6;
						transition: background-color 0.15s;
					}
					.dark .html-table-container table {
						border: 2px solid #4b5563;
						background-color: #1f2937;
					}
					.dark .html-table-container table tr:nth-child(1) {
						background-color: #374151;
						color: #e5e7eb;
					}
					.dark .html-table-container table th,
					.dark .html-table-container table td {
						border: 1px solid #4b5563;
					}
					.dark .html-table-container table td {
						color: #f3f4f6;
					}
					.dark .html-table-container table tbody tr:nth-child(even) {
						background-color: #273042;
					}
					.dark .html-table-container table tr:hover {
						background-color: #374151;
					}
				</style>
				{@html html}
					</div>
				</div>
			{/if}
		</div>
	{:else if token.text.includes('<div') && token.text.includes('style=')}
		<!-- HTML div 支持 -->
		{@html html}
	{:else}
		{@const br = token.text.match(/<br\s*\/?>/)}
		{#if br}
			<br />
		{:else}
			{@html html}
		{/if}
	{/if}
{/if}
