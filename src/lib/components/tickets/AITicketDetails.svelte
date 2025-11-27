<script lang="ts">
	import { onMount } from 'svelte';
	import { getFeedbackById } from '$lib/apis/evaluations';
	import UserIcon from '$lib/components/icons/User.svelte';
	import ChatBubbleLeftRightIcon from '$lib/components/icons/ChatBubbleLeftRight.svelte';
	import ClockIcon from '$lib/components/icons/ClockRotateRight.svelte';
	import TagIcon from '$lib/components/icons/Tag.svelte';
	import CpuChipIcon from '$lib/components/icons/Computer.svelte';
	import ExclamationTriangleIcon from '$lib/components/icons/ExclamationTriangle.svelte';
	import CheckCircleIcon from '$lib/components/icons/CheckCircle.svelte';
	import ChevronDownIcon from '$lib/components/icons/ChevronDown.svelte';
	import ChevronRightIcon from '$lib/components/icons/ChevronRight.svelte';
	import { marked } from 'marked';

	export let ticket: any;

	let feedbackData: any = null;
	let chatData: any = null;
	
	// 折叠状态控制
	let isUserFeedbackCollapsed = true;  // 用户反馈默认折叠
	let isChatContentCollapsed = true;   // 对话内容默认折叠
	let isAIAnalysisCollapsed = true;    // AI分析报告默认折叠
	let isUserRatingCollapsed = true;   // 用户评分默认折叠

	// 渲染Markdown内容为HTML
	function renderMarkdown(content: string): string {
		if (!content) return '';
		
		try {
			// 配置marked选项
			marked.setOptions({
				breaks: true,
				gfm: true
			});
			
			return marked.parse(content);
		} catch (e) {
			console.error('Error rendering markdown:', e);
			return content; // 如果解析失败，返回原始内容
		}
	}

	onMount(async () => {
		// 尝试从不同来源获取反馈数据
		if (ticket.ai_analysis) {
			try {
				const aiAnalysis = typeof ticket.ai_analysis === 'string' 
					? JSON.parse(ticket.ai_analysis) 
					: ticket.ai_analysis;
				
				// 优先从feedback_data获取用户反馈信息
				if (aiAnalysis.feedback_data) {
					feedbackData = aiAnalysis.feedback_data;
					console.log('Using feedback_data from AI analysis:', feedbackData);
				} else {
					feedbackData = aiAnalysis;
					console.log('Using AI analysis as feedback data:', feedbackData);
				}
			} catch (e) {
				console.error('Error parsing AI analysis:', e);
			}
		}
		
		// 如果没有从ai_analysis获取到数据，尝试从source_feedback_id获取完整反馈数据
		if (!feedbackData && ticket.source_feedback_id) {
			try {
				const token = localStorage.getItem('token') || '';
				const fullFeedback = await getFeedbackById(token, ticket.source_feedback_id);
				feedbackData = fullFeedback;
				console.log('Fetched feedback data:', feedbackData);
			} catch (e) {
				console.error('Error fetching feedback data:', e);
			}
		}
		
		// 调试信息
		console.log('Ticket data:', ticket);
		console.log('Feedback data:', feedbackData);
		
		// 如果反馈数据存在，提取对话内容
		if (feedbackData) {
			// 方式1: 从snapshot.chat.messages数组获取
			if (feedbackData.snapshot && feedbackData.snapshot.chat && feedbackData.snapshot.chat.messages) {
				chatData = {
					title: feedbackData.snapshot.chat.title,
					messages: feedbackData.snapshot.chat.messages
				};
				console.log('Extracted chat data from snapshot.messages array:', chatData);
			}
			// 方式2: 从snapshot.chat.chat.history.messages对象获取
			else if (feedbackData.snapshot && feedbackData.snapshot.chat && feedbackData.snapshot.chat.chat && feedbackData.snapshot.chat.chat.history && feedbackData.snapshot.chat.chat.history.messages) {
				const messagesObj = feedbackData.snapshot.chat.chat.history.messages;
				// 将对象转换为数组
				const messagesArray = Object.values(messagesObj);
				chatData = {
					title: feedbackData.snapshot.chat.title,
					messages: messagesArray
				};
				console.log('Extracted chat data from snapshot.chat.history.messages object:', chatData);
			}
			// 方式3: 从ai_analysis的full_chat_data获取
			else if (ticket.ai_analysis) {
				const aiAnalysis = typeof ticket.ai_analysis === 'string' 
					? JSON.parse(ticket.ai_analysis) 
					: ticket.ai_analysis;
				
				if (aiAnalysis.full_chat_data && aiAnalysis.full_chat_data.messages) {
					chatData = {
						title: aiAnalysis.full_chat_data.title,
						messages: aiAnalysis.full_chat_data.messages
					};
					console.log('Extracted chat data from full_chat_data:', chatData);
				}
			}
		}
	});

	function formatDate(timestamp: number) {
		return new Date(timestamp * 1000).toLocaleDateString('zh-CN', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatTimestamp(timestamp: number) {
		return new Date(timestamp * 1000).toLocaleString('zh-CN');
	}

	function getRatingIcon(rating: number) {
		if (rating > 0) return '👍';
		if (rating < 0) return '👎';
		return '😐';
	}

	function getRatingText(rating: number) {
		if (rating > 0) return '正面反馈';
		if (rating < 0) return '负面反馈';
		return '中性反馈';
	}

	function getRatingColor(rating: number) {
		if (rating > 0) return 'text-green-600';
		if (rating < 0) return 'text-red-600';
		return 'text-gray-600';
	}

	function truncateText(text: string, maxLength: number = 100) {
		if (!text) return '';
		return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
	}
</script>

{#if ticket.is_ai_generated}
	<div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-4">
		<!-- AI工单标识 -->
		<div class="flex items-center gap-2 mb-3">
			<span class="text-sm font-medium text-gray-600 dark:text-gray-400">AI自动生成工单</span>
			<span class="text-xs text-gray-500">#{ticket.id.substring(0, 8)}</span>
		</div>

		<!-- 反馈数据概览 -->
		{#if feedbackData}
			<div class="space-y-3">
				<!-- 评分信息 -->
				<div class="bg-gray-50 dark:bg-gray-700 rounded border">
					<!-- 折叠按钮 -->
					<button 
						class="w-full flex items-center justify-between p-3 text-left hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
						on:click={() => isUserRatingCollapsed = !isUserRatingCollapsed}
					>
						<div class="flex items-center gap-3">
							<div class="text-xl">{getRatingIcon(feedbackData.rating)}</div>
							<div class="flex-1">
								<div class="flex items-center gap-2">
									<span class="font-medium text-gray-900 dark:text-white">用户评分</span>
									<span class="text-sm {getRatingColor(feedbackData.rating)}">
										{getRatingText(feedbackData.rating)} ({feedbackData.rating})
									</span>
								</div>
								<div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
									模型: {feedbackData.model_id || '未知'}
								</div>
							</div>
						</div>
						{#if isUserRatingCollapsed}
							<ChevronRightIcon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
						{:else}
							<ChevronDownIcon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
						{/if}
					</button>
					
					<!-- 折叠内容 -->
					{#if !isUserRatingCollapsed}
						<div class="px-3 pb-3">
							<div class="text-sm text-gray-600 dark:text-gray-400">
								<div class="mb-2">
									<span class="font-medium">评分详情:</span>
									<div class="mt-1 p-2 bg-white dark:bg-gray-800 rounded border">
										<div class="flex items-center justify-between">
											<span>评分值:</span>
											<span class="font-medium {getRatingColor(feedbackData.rating)}">
												{feedbackData.rating}
											</span>
										</div>
										<div class="flex items-center justify-between mt-1">
											<span>评分类型:</span>
											<span class="font-medium">
												{getRatingText(feedbackData.rating)}
											</span>
										</div>
										{#if feedbackData.model_id}
											<div class="flex items-center justify-between mt-1">
												<span>使用模型:</span>
												<span class="font-medium text-blue-600 dark:text-blue-400">
													{feedbackData.model_id}
												</span>
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>
					{/if}
				</div>

				<!-- 用户评论反馈 -->
				{#if feedbackData.data && feedbackData.data.comment}
					<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
						<!-- 折叠按钮 -->
						<button 
							class="w-full flex items-center justify-between p-4 text-left hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
							on:click={() => isUserFeedbackCollapsed = !isUserFeedbackCollapsed}
						>
							<div class="flex items-center gap-3">
								<div class="w-8 h-8 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
									<span class="text-red-600 dark:text-red-400 text-sm font-bold">!</span>
								</div>
								<div class="text-sm font-semibold text-red-800 dark:text-red-200">用户反馈评论</div>
							</div>
							{#if isUserFeedbackCollapsed}
								<ChevronRightIcon className="w-4 h-4 text-red-600 dark:text-red-400" />
							{:else}
								<ChevronDownIcon className="w-4 h-4 text-red-600 dark:text-red-400" />
							{/if}
						</button>
						
						<!-- 折叠内容 -->
						{#if !isUserFeedbackCollapsed}
							<div class="px-4 pb-4">
								<div class="text-sm text-red-700 dark:text-red-300 bg-white dark:bg-gray-800 rounded p-3 border-l-4 border-red-500">
									"{feedbackData.data.comment}"
								</div>
							</div>
						{/if}
					</div>
				{:else if feedbackData.data && feedbackData.data.reason}
					<!-- 如果没有评论但有原因，显示原因 -->
					<div class="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4">
						<div class="flex items-start gap-3">
							<div class="flex-shrink-0">
								<div class="w-8 h-8 bg-orange-100 dark:bg-orange-900 rounded-full flex items-center justify-center">
									<span class="text-orange-600 dark:text-orange-400 text-sm font-bold">?</span>
								</div>
							</div>
							<div class="flex-1">
								<div class="text-sm font-semibold text-orange-800 dark:text-orange-200 mb-2">用户反馈原因</div>
								<div class="text-sm text-orange-700 dark:text-orange-300 bg-white dark:bg-gray-800 rounded p-3 border-l-4 border-orange-500">
									"{feedbackData.data.reason}"
								</div>
							</div>
						</div>
					</div>
				{:else if feedbackData.comment}
					<!-- 兼容旧格式 -->
					<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
						<div class="flex items-start gap-3">
							<div class="flex-shrink-0">
								<div class="w-8 h-8 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
									<span class="text-red-600 dark:text-red-400 text-sm font-bold">!</span>
								</div>
							</div>
							<div class="flex-1">
								<div class="text-sm font-semibold text-red-800 dark:text-red-200 mb-2">用户反馈评论</div>
								<div class="text-sm text-red-700 dark:text-red-300 bg-white dark:bg-gray-800 rounded p-3 border-l-4 border-red-500">
									"{feedbackData.comment}"
								</div>
							</div>
						</div>
					</div>
				{:else if feedbackData.reason}
					<!-- 兼容旧格式 -->
					<div class="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg p-4">
						<div class="flex items-start gap-3">
							<div class="flex-shrink-0">
								<div class="w-8 h-8 bg-orange-100 dark:bg-orange-900 rounded-full flex items-center justify-center">
									<span class="text-orange-600 dark:text-orange-400 text-sm font-bold">?</span>
								</div>
							</div>
							<div class="flex-1">
								<div class="text-sm font-semibold text-orange-800 dark:text-orange-200 mb-2">用户反馈原因</div>
								<div class="text-sm text-orange-700 dark:text-orange-300 bg-white dark:bg-gray-800 rounded p-3 border-l-4 border-orange-500">
									"{feedbackData.reason}"
								</div>
							</div>
						</div>
					</div>
				{/if}

				<!-- AI分析结果 -->
				{#if ticket.ai_analysis && typeof ticket.ai_analysis === 'object'}
					<div class="bg-gray-50 dark:bg-gray-700 rounded border">
						<!-- 折叠按钮 -->
						<button 
							class="w-full flex items-center justify-between p-4 text-left hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
							on:click={() => isAIAnalysisCollapsed = !isAIAnalysisCollapsed}
						>
							<div class="flex items-center gap-3">
								<CpuChipIcon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
								<div class="text-sm font-semibold text-gray-900 dark:text-white">AI分析报告</div>
								{#if ticket.ai_analysis.tags && ticket.ai_analysis.tags.length > 0}
									<span class="text-xs text-gray-500">({ticket.ai_analysis.tags.length} 个标签)</span>
								{/if}
							</div>
							{#if isAIAnalysisCollapsed}
								<ChevronRightIcon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
							{:else}
								<ChevronDownIcon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
							{/if}
						</button>
						
						<!-- 折叠内容 -->
						{#if !isAIAnalysisCollapsed}
							<div class="px-4 pb-4">
								<!-- AI完整分析 -->
								<div class="mb-4">
									<div class="text-sm font-medium text-gray-900 dark:text-white mb-2">分析内容</div>
									<div class="text-sm text-gray-700 dark:text-gray-300">
										{@html renderMarkdown(ticket.ai_analysis.description || '无分析内容')}
									</div>
								</div>

								<!-- 处理建议 -->
								<div class="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded">
									<div class="flex items-start gap-2">
										<ExclamationTriangleIcon className="w-4 h-4 text-yellow-600 mt-0.5" />
										<div class="text-sm text-yellow-800 dark:text-yellow-200">
											<strong>处理建议:</strong> 
											{#if ticket.ai_analysis && ticket.ai_analysis.priority}
												<span class="ml-1">
													{#if ticket.ai_analysis.priority === 'urgent'}
														紧急处理 - 系统崩溃或安全漏洞
													{:else if ticket.ai_analysis.priority === 'high'}
														高优先级 - 严重影响用户体验
													{:else if ticket.ai_analysis.priority === 'medium'}
														中等优先级 - 功能异常或性能问题
													{:else}
														低优先级 - 优化建议或小问题
													{/if}
												</span>
											{:else}
												这是基于用户负面反馈自动生成的工单，建议优先处理用户的具体问题。
											{/if}
										</div>
									</div>
								</div>

								<!-- AI分析的技术标签 -->
								{#if ticket.ai_analysis.tags && ticket.ai_analysis.tags.length > 0}
									<div class="mb-2">
										<div class="text-sm font-medium text-gray-900 dark:text-white mb-2">技术标签</div>
										<div class="flex flex-wrap gap-1">
											{#each ticket.ai_analysis.tags as tag}
												<span class="px-2 py-1 bg-gray-200 dark:bg-gray-600 text-gray-800 dark:text-gray-200 text-xs rounded">
													{tag}
												</span>
											{/each}
										</div>
									</div>
								{/if}
							</div>
						{/if}
					</div>
				{/if}

				<!-- 对话内容显示 -->
				{#if chatData && chatData.messages}
					<div class="bg-gray-50 dark:bg-gray-700 rounded border">
						<!-- 折叠按钮 -->
						<button 
							class="w-full flex items-center justify-between p-4 text-left hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
							on:click={() => isChatContentCollapsed = !isChatContentCollapsed}
						>
							<div class="flex items-center gap-3">
								<ChatBubbleLeftRightIcon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
								<div class="text-sm font-semibold text-gray-900 dark:text-white">对话内容</div>
								<span class="text-xs text-gray-500">({chatData.messages.length} 条消息)</span>
							</div>
							{#if isChatContentCollapsed}
								<ChevronRightIcon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
							{:else}
								<ChevronDownIcon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
							{/if}
						</button>
						
						<!-- 折叠内容 -->
						{#if !isChatContentCollapsed}
							<div class="px-4 pb-4 space-y-3">
								{#each chatData.messages as message, index}
									{#if message.role === 'user'}
										<!-- 用户问题 -->
										<div class="bg-white dark:bg-gray-800 rounded p-3 border-l-2 border-blue-500">
											<div class="text-sm font-medium text-gray-900 dark:text-white mb-1">用户问题</div>
											<div class="text-sm text-gray-700 dark:text-gray-300">
												{@html renderMarkdown(message.content)}
											</div>
										</div>
									{:else}
										<!-- AI回复 -->
										<div class="bg-white dark:bg-gray-800 rounded p-3 border-l-2 border-green-500">
											<div class="text-sm font-medium text-gray-900 dark:text-white mb-1">AI回复</div>
											<div class="text-sm text-gray-700 dark:text-gray-300">
												{@html renderMarkdown(message.content)}
											</div>
										</div>
									{/if}
								{/each}
							</div>
						{/if}
					</div>
				{:else}
					<!-- 如果没有对话数据，显示提示 -->
					<div class="p-3 bg-gray-50 dark:bg-gray-700 rounded border">
						<div class="text-sm text-gray-600 dark:text-gray-400">
							⚠️ 无法获取对话数据
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>

{/if}
