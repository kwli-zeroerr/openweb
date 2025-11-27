<script lang="ts">
	import { fade, slide } from 'svelte/transition';
	import { cubicOut } from 'svelte/easing';
	
	export let comments: any[] = [];
	export let onAddComment: (content: string) => Promise<void>;
	
	let newComment = '';
	let isSubmitting = false;
	
	async function handleSubmit() {
		if (!newComment.trim() || isSubmitting) return;
		
		isSubmitting = true;
		try {
			await onAddComment(newComment.trim());
			newComment = '';
		} catch (error) {
			console.error('Failed to add comment:', error);
		} finally {
			isSubmitting = false;
		}
	}
	
	function formatDate(timestamp: number) {
		return new Date(timestamp * 1000).toLocaleDateString('zh-CN', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}
	
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
			handleSubmit();
		}
	}
</script>

<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
	<!-- 标题栏 -->
	<div class="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-600 px-6 py-4 border-b border-gray-200 dark:border-gray-600">
		<div class="flex items-center gap-3">
			<div class="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
				<svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
					<path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd"/>
				</svg>
			</div>
			<h3 class="text-xl font-bold text-gray-900 dark:text-white">评论讨论</h3>
			{#if comments.length > 0}
				<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
					{comments.length} 条评论
				</span>
			{/if}
		</div>
	</div>
	
	<!-- 内容区域 -->
	<div class="p-6">
		<!-- 添加评论 -->
		<div class="mb-8">
			<div class="flex gap-4">
				<div class="flex-1">
					<textarea
						bind:value={newComment}
						on:keydown={handleKeydown}
						placeholder="添加评论... (Ctrl+Enter 提交)"
						class="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-xl bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none shadow-sm transition-all duration-200"
						rows="3"
						disabled={isSubmitting}
					></textarea>
				</div>
				<button
					on:click={handleSubmit}
					disabled={isSubmitting || !newComment.trim()}
					class="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm transition-all duration-200 hover:scale-105 active:scale-95"
				>
					{#if isSubmitting}
						<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
					{:else}
						<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
							<path fill-rule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clip-rule="evenodd"></path>
						</svg>
					{/if}
					添加评论
				</button>
			</div>
		</div>

		<!-- 评论时间线 -->
		<div class="space-y-6">
			{#each comments as comment, index}
				<div class="relative pl-6 before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-px before:bg-gray-200 dark:before:bg-gray-700">
					<!-- 时间线节点 -->
					<div class="absolute left-0 top-2 w-4 h-4 bg-blue-500 rounded-full border-2 border-white dark:border-gray-800 shadow-sm"></div>
					
					<!-- 评论内容 -->
					<div class="bg-gray-50 dark:bg-gray-700 rounded-xl p-4 border-l-4 border-blue-500 shadow-sm hover:shadow-md transition-all duration-200">
						<div class="flex items-center gap-3 mb-3">
							<div class="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
								<span class="text-sm font-semibold text-blue-600 dark:text-blue-400">
									{comment.author_name?.charAt(0) || 'U'}
								</span>
							</div>
							<div class="flex-1">
								<div class="flex items-center gap-2">
									<span class="font-semibold text-gray-900 dark:text-white">{comment.author_name}</span>
									<span class="text-xs text-gray-500 dark:text-gray-400">{formatDate(comment.created_at)}</span>
									{#if comment.is_internal}
										<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400">
											内部
										</span>
									{/if}
								</div>
							</div>
						</div>
						<div class="text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
							{comment.content}
						</div>
					</div>
				</div>
			{/each}
			
			{#if comments.length === 0}
				<div class="text-center py-12 text-gray-500 dark:text-gray-400">
					<div class="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
						<svg class="w-8 h-8 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
						</svg>
					</div>
					<h4 class="text-lg font-medium text-gray-900 dark:text-white mb-2">暂无评论</h4>
					<p class="text-sm">成为第一个评论的人</p>
				</div>
			{/if}
		</div>
	</div>
</div>
