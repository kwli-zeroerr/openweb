<script lang="ts">
	import { goto } from '$app/navigation';
	import { createEventDispatcher } from 'svelte';
	import type { Ticket } from '$lib/apis/tickets';
	import { getStatusInfo, getPriorityInfo, getCategoryInfo, formatTicketDate } from '$lib/constants/tickets';
	import { user } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import Eye from '$lib/components/icons/Eye.svelte';
	import Trash from '$lib/components/icons/Trash.svelte';
	import BugAnt from '$lib/components/icons/BugAnt.svelte';
	import LightBulb from '$lib/components/icons/LightBulb.svelte';
	import ChatBubbleLeftRight from '$lib/components/icons/ChatBubbleLeftRight.svelte';
	import WrenchScrewdriver from '$lib/components/icons/WrenchScrewdriver.svelte';
	import Tag from '$lib/components/icons/Tag.svelte';

	const dispatch = createEventDispatcher();

	export let ticket: Ticket;

	// 获取用户问题内容
	function getUserProblemContent() {
		// 如果是AI生成的工单，尝试从ai_analysis中提取用户问题
		if (ticket.is_ai_generated && ticket.ai_analysis) {
			try {
				const analysis = typeof ticket.ai_analysis === 'string' 
					? JSON.parse(ticket.ai_analysis) 
					: ticket.ai_analysis;
				
				// 优先从feedback_data.data.comment中获取用户反馈评论
				if (analysis.feedback_data && analysis.feedback_data.data) {
					const comment = analysis.feedback_data.data.comment;
					if (comment && comment.trim()) {
						return `💬 用户反馈: ${cleanContent(comment)}`;
					}
					
					// 如果没有评论，尝试获取reason
					const reason = analysis.feedback_data.data.reason;
					if (reason && reason.trim()) {
						return `❓ 反馈原因: ${cleanContent(reason)}`;
					}
					
					// 如果都没有评论和原因，显示简洁的提示
					return "👎 用户对AI回复不满意（点踩反馈）";
				}
				
				// 从feedback_data.snapshot.chat.messages中获取用户问题
				if (analysis.feedback_data && analysis.feedback_data.snapshot && analysis.feedback_data.snapshot.chat) {
					const chat = analysis.feedback_data.snapshot.chat;
					if (chat.messages && Array.isArray(chat.messages)) {
						// 找到最后一条用户消息
						for (let i = chat.messages.length - 1; i >= 0; i--) {
							if (chat.messages[i].role === 'user') {
								return `❓ 用户问题: ${cleanContent(chat.messages[i].content)}`;
							}
						}
					}
				}
				
				// 尝试从其他字段获取用户问题
				if (analysis.user_problem) return `❓ 用户问题: ${cleanContent(analysis.user_problem)}`;
				if (analysis.problem_description) return `📝 问题描述: ${cleanContent(analysis.problem_description)}`;
				if (analysis.original_feedback) return `💬 原始反馈: ${cleanContent(analysis.original_feedback)}`;
				if (analysis.feedback_content) return `💬 反馈内容: ${cleanContent(analysis.feedback_content)}`;
				
				// 如果有snapshot，尝试从中获取
				if (analysis.snapshot && analysis.snapshot.chat) {
					const chat = analysis.snapshot.chat;
					if (chat.messages && chat.messages.length > 0) {
						// 获取最后一条用户消息
						const userMessages = chat.messages.filter((m: any) => m.role === 'user');
						if (userMessages.length > 0) {
							return `❓ 用户问题: ${cleanContent(userMessages[userMessages.length - 1].content)}`;
						}
					}
				}
			} catch (e) {
				console.warn('Failed to parse AI analysis:', e);
			}
			
			// 如果AI工单解析失败，显示简洁提示而不是JSON
			return "用户对AI回复不满意（点踩反馈）";
		}
		
		// 回退到描述字段
		return cleanContent(ticket.description || '暂无描述');
	}

	// 清理内容，移除HTML标签并限制长度
	function cleanContent(content: string) {
		if (!content) return '暂无描述';
		
		// 移除HTML标签
		const textContent = content.replace(/<[^>]*>/g, '');
		
		// 限制长度，避免卡片过长
		if (textContent.length > 150) {
			return textContent.substring(0, 150) + '...';
		}
		
		return textContent;
	}

	function handleDelete() {
		// 检查删除权限
		if ($user?.role !== 'admin') {
			toast.error('权限不足，无法删除工单。请联系管理员申请权限，或在工单下留言说明删除原因。');
			return;
		}
		
		dispatch('delete', ticket.id);
	}

	function handleView() {
		goto(`/workspace/tickets/${ticket.id}`);
	}
</script>

<div 
	class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 hover:shadow-md transition-shadow h-full flex flex-col cursor-pointer"
	on:click={handleView}
	role="button"
	tabindex="0"
	on:keydown={(e) => e.key === 'Enter' && handleView()}
>
	<!-- Header with title and actions -->
	<div class="flex items-start justify-between mb-2">
		<div class="flex-1 min-w-0">
			<div class="flex items-center gap-2 mb-2">
				<h3 class="text-base font-semibold text-gray-900 dark:text-white truncate flex-1 min-w-0">
					{ticket.title}
				</h3>
				{#if ticket.is_ai_generated}
					<span class="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200 whitespace-nowrap flex-shrink-0">
						AI生成
					</span>
				{/if}
			</div>
		</div>
		
		<div class="flex items-center gap-1 ml-2 flex-shrink-0">
			<button
				on:click|stopPropagation={handleView}
				class="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
			>
				<Eye className="w-4 h-4" />
			</button>
			<button
				on:click|stopPropagation={handleDelete}
				class="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
			>
				<Trash className="w-4 h-4" />
			</button>
		</div>
	</div>
	
	<!-- Status tags -->
	<div class="flex items-center gap-1.5 mb-2 flex-wrap">
		<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {getStatusInfo(ticket.status).bg} {getStatusInfo(ticket.status).color} whitespace-nowrap">
			{getStatusInfo(ticket.status).label}
		</span>
		<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {getPriorityInfo(ticket.priority).bg} {getPriorityInfo(ticket.priority).color} whitespace-nowrap">
			{getPriorityInfo(ticket.priority).label}
		</span>
		
		<!-- 交付验收状态 -->
		{#if ticket.completion_status}
			{#if ticket.completion_status === 'pending'}
				<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300 whitespace-nowrap">
					待交付
				</span>
			{:else if ticket.completion_status === 'submitted'}
				<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300 whitespace-nowrap">
					待验收
				</span>
			{:else if ticket.completion_status === 'verified'}
				<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300 whitespace-nowrap">
					验收通过
				</span>
			{:else if ticket.completion_status === 'rejected'}
				<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300 whitespace-nowrap">
					验收未通过
				</span>
			{/if}
		{/if}
	</div>
	
	<!-- Content -->
	<p class="text-gray-600 dark:text-gray-300 text-sm line-clamp-2 mb-2">
		{getUserProblemContent()}
	</p>
	
	<!-- Meta info -->
	<div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
		<div class="flex items-center">
			<svelte:component this={getCategoryInfo(ticket.category).icon} className="w-3 h-3 mr-1 {getCategoryInfo(ticket.category).color}" />
			{getCategoryInfo(ticket.category).label}
		</div>
		<span>·</span>
		<span>创建人: {ticket.user_name ?? '未知'}</span>
		<span>·</span>
		<span>待办人: {ticket.assigned_to_name ?? '待分配'}</span>
		<span>·</span>
		<span>{formatTicketDate(ticket.created_at)}</span>
	</div>

</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		line-clamp: 2;
	}
	.line-clamp-3 {
		display: -webkit-box;
		-webkit-line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
		line-clamp: 3;
	}
</style>
