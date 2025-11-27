<script lang="ts">
	import { fade, slide } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	import { marked } from 'marked';
	
	export const isOpen: boolean = false;
	export const title: string = '';
	export let messages: any[] = [];
	
	let isExpanded = false;
	
	function toggleExpanded() {
		isExpanded = !isExpanded;
	}
	
	function formatMessageContent(content: string, maxLength: number = 200) {
		if (!content) return '';
		if (content.length <= maxLength) return content;
		return content.substring(0, maxLength) + '...';
	}
	
	function renderHtmlContent(content: string) {
		if (!content) return '';
		
		// 检查是否包含HTML标签或Markdown语法
		const hasHtmlTags = /<[^>]*>/g.test(content);
		const hasMarkdown = /[#*`_~\[\]()]/g.test(content);
		
		if (hasHtmlTags || hasMarkdown) {
			// 如果有HTML标签或Markdown语法，使用marked渲染
			try {
				// 配置marked选项
				marked.setOptions({
					breaks: true,
					gfm: true
				});
				
				return marked(content);
			} catch (error) {
				console.error('Error rendering markdown:', error);
				// 如果渲染失败，返回转义后的内容
				return content.replace(/</g, '&lt;').replace(/>/g, '&gt;');
			}
		} else {
			// 如果没有特殊格式，保持原样但处理换行
			return content.replace(/\n/g, '<br>');
		}
	}
</script>

<style>
	/* 对话气泡中的HTML内容样式 */
	:global(.chat-message-content) {
		line-height: 1.6;
	}
	
	:global(.chat-message-content h1),
	:global(.chat-message-content h2),
	:global(.chat-message-content h3),
	:global(.chat-message-content h4),
	:global(.chat-message-content h5),
	:global(.chat-message-content h6) {
		margin-top: 0.5rem;
		margin-bottom: 0.5rem;
		font-weight: 600;
	}
	
	:global(.chat-message-content p) {
		margin-bottom: 0.5rem;
	}
	
	:global(.chat-message-content ul),
	:global(.chat-message-content ol) {
		margin: 0.5rem 0;
		padding-left: 1.5rem;
	}
	
	:global(.chat-message-content li) {
		margin-bottom: 0.25rem;
	}
	
	:global(.chat-message-content code) {
		background-color: rgba(0, 0, 0, 0.1);
		padding: 0.125rem 0.25rem;
		border-radius: 0.25rem;
		font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
		font-size: 0.875em;
	}
	
	:global(.chat-message-content pre) {
		background-color: rgba(0, 0, 0, 0.1);
		padding: 0.75rem;
		border-radius: 0.5rem;
		overflow-x: auto;
		margin: 0.5rem 0;
	}
	
	:global(.chat-message-content pre code) {
		background-color: transparent;
		padding: 0;
	}
	
	:global(.chat-message-content blockquote) {
		border-left: 4px solid rgba(0, 0, 0, 0.2);
		padding-left: 1rem;
		margin: 0.5rem 0;
		font-style: italic;
	}
	
	:global(.chat-message-content table) {
		border-collapse: collapse;
		width: 100%;
		margin: 0.5rem 0;
	}
	
	:global(.chat-message-content th),
	:global(.chat-message-content td) {
		border: 1px solid rgba(0, 0, 0, 0.2);
		padding: 0.5rem;
		text-align: left;
	}
	
	:global(.chat-message-content th) {
		background-color: rgba(0, 0, 0, 0.1);
		font-weight: 600;
	}
	
	/* 用户消息的特殊样式 */
	:global(.user-message .chat-message-content) {
		color: white;
	}
	
	:global(.user-message .chat-message-content code) {
		background-color: rgba(255, 255, 255, 0.2);
		color: white;
	}
	
	:global(.user-message .chat-message-content pre) {
		background-color: rgba(255, 255, 255, 0.2);
		color: white;
	}
	
	:global(.user-message .chat-message-content blockquote) {
		border-left-color: rgba(255, 255, 255, 0.3);
	}
	
	:global(.user-message .chat-message-content th),
	:global(.user-message .chat-message-content td) {
		border-color: rgba(255, 255, 255, 0.3);
	}
	
	:global(.user-message .chat-message-content th) {
		background-color: rgba(255, 255, 255, 0.2);
	}
</style>

<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
	<!-- 标题栏 -->
	<div class="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 px-6 py-4 border-b border-blue-200 dark:border-blue-800">
		<button 
			on:click={toggleExpanded}
			class="w-full flex items-center justify-between text-left hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors duration-200 rounded-lg p-2 -m-2"
		>
			<div class="flex items-center gap-3">
				<div class="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
					<svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
						<path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd"/>
					</svg>
				</div>
				<div>
					<h3 class="text-lg font-bold text-gray-900 dark:text-white">对话上下文</h3>
					<p class="text-sm text-gray-600 dark:text-gray-400">{messages.length} 条消息</p>
				</div>
			</div>
			<svg class="w-5 h-5 text-gray-600 dark:text-gray-400 transition-transform duration-200 {isExpanded ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
			</svg>
		</button>
	</div>
	
	<!-- 对话内容 -->
	{#if isExpanded}
		<div class="p-6" transition:slide={{ duration: 300, easing: cubicOut }}>
			<div class="space-y-4 max-h-96 overflow-y-auto">
				{#each messages as message, index}
					<div class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'}">
						<div class="max-w-[80%] {message.role === 'user' ? 'bg-blue-500 text-white user-message' : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'} rounded-2xl px-4 py-3 shadow-sm">
							<div class="flex items-center gap-2 mb-2">
								<div class="w-6 h-6 rounded-full {message.role === 'user' ? 'bg-blue-600' : 'bg-green-500'} flex items-center justify-center">
									<span class="text-xs font-semibold text-white">
										{message.role === 'user' ? 'U' : 'AI'}
									</span>
								</div>
								<span class="text-xs font-medium opacity-75">
									{message.role === 'user' ? '用户' : 'AI助手'}
								</span>
							</div>
							<div class="text-sm leading-relaxed chat-message-content">
								{#if message.content}
									{@html renderHtmlContent(message.content)}
								{:else}
									<span class="text-gray-500 dark:text-gray-400 italic">无内容</span>
								{/if}
							</div>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>
