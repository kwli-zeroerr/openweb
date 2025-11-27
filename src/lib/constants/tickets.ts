// 工单系统统一配置常量
import BugAnt from '$lib/components/icons/BugAnt.svelte';
import LightBulb from '$lib/components/icons/LightBulb.svelte';
import ChatBubbleLeftRight from '$lib/components/icons/ChatBubbleLeftRight.svelte';
import WrenchScrewdriver from '$lib/components/icons/WrenchScrewdriver.svelte';
import Tag from '$lib/components/icons/Tag.svelte';

export const TICKET_STATUS_OPTIONS = [
	{ value: 'open', label: '待处理', color: 'text-orange-700 dark:text-orange-400', bg: 'bg-orange-100 dark:bg-orange-900/20' },
	{ value: 'in_progress', label: '处理中', color: 'text-blue-700 dark:text-blue-400', bg: 'bg-blue-100 dark:bg-blue-900/20' },
	{ value: 'completed', label: '已完成', color: 'text-green-700 dark:text-green-400', bg: 'bg-green-100 dark:bg-green-900/20' },
	{ value: 'resolved', label: '已解决', color: 'text-green-700 dark:text-green-400', bg: 'bg-green-100 dark:bg-green-900/20' },
	{ value: 'closed', label: '已关闭', color: 'text-gray-700 dark:text-gray-400', bg: 'bg-gray-100 dark:bg-gray-900/20' }
] as const;

export const TICKET_PRIORITY_OPTIONS = [
	{ value: 'low', label: '低', color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-100 dark:bg-blue-900/20' },
	{ value: 'medium', label: '中', color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-100 dark:bg-yellow-900/20' },
	{ value: 'high', label: '高', color: 'text-orange-600 dark:text-orange-400', bg: 'bg-orange-100 dark:bg-orange-900/20' },
	{ value: 'urgent', label: '紧急', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-100 dark:bg-red-900/20' }
] as const;

export const TICKET_CATEGORY_OPTIONS = [
	{ value: 'bug', label: 'Bug 报告', icon: BugAnt, color: 'text-gray-600' },
	{ value: 'feature_request', label: '功能请求', icon: LightBulb, color: 'text-gray-600' },
	{ value: 'general_inquiry', label: '一般咨询', icon: ChatBubbleLeftRight, color: 'text-gray-600' },
	{ value: 'technical_support', label: '技术支持', icon: WrenchScrewdriver, color: 'text-gray-600' },
	{ value: 'other', label: '其他', icon: Tag, color: 'text-gray-600' }
] as const;

// 工具函数
export function getStatusInfo(status: string) {
	return TICKET_STATUS_OPTIONS.find(s => s.value === status) || TICKET_STATUS_OPTIONS[0];
}

export function getPriorityInfo(priority: string) {
	return TICKET_PRIORITY_OPTIONS.find(p => p.value === priority) || TICKET_PRIORITY_OPTIONS[1];
}

export function getCategoryInfo(category: string) {
	return TICKET_CATEGORY_OPTIONS.find(c => c.value === category) || TICKET_CATEGORY_OPTIONS[2];
}

// 工单过滤函数
export function filterTicketsByTab(tickets: any[], tab: 'all' | 'todo' | 'unassigned' | 'assigned' | 'archived' | 'pending_verification', currentUserId?: string) {
	if (tab === 'all') return tickets;
	
	if (tab === 'archived') {
		return tickets.filter((t) => {
			const s = String(t.status || '').toLowerCase();
			return s === 'resolved' || s === 'closed';
		});
	}
	
	if (tab === 'pending_verification') {
		return tickets.filter((t) => {
			// 待验收：有交付内容且验收状态为submitted的工单
			const hasDeliveryContent = t.delivery_files?.length > 0 || t.delivery_images?.length > 0 || t.delivery_text;
			const isPendingVerification = t.completion_status === 'submitted';
			return hasDeliveryContent && isPendingVerification;
		});
	}
	
	if (tab === 'unassigned') {
		return tickets.filter((t) => {
			const s = String(t.status || '').toLowerCase();
			return (s !== 'resolved' && s !== 'closed') && !t.assigned_to;
		});
	}
	
	if (tab === 'assigned') {
		return tickets.filter((t) => {
			const s = String(t.status || '').toLowerCase();
			return (s !== 'resolved' && s !== 'closed') && t.assigned_to;
		});
	}
	
	// default: todo - 只显示分配给当前用户的工单
	return tickets.filter((t) => {
		const s = String(t.status || '').toLowerCase();
		return (s !== 'resolved' && s !== 'closed') && t.assigned_to === currentUserId;
	});
}

// 日期格式化
export function formatTicketDate(timestamp: number) {
	return new Date(timestamp * 1000).toLocaleDateString('zh-CN', {
		year: 'numeric',
		month: 'short',
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	});
}
