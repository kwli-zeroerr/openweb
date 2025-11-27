import type { Ticket } from '$lib/apis/tickets';

// 统计数据类型定义
export interface DailyStats {
	date: string;
	submitted: number;
	completed: number;
}

export interface MaintainerStats {
	name: string;
	count: number;
}

export interface SubmitterStats {
	name: string;
	count: number;
}

export interface ResolverDepartmentStats {
	department: string;
	count: number;
}

export interface WeeklyStats {
	week: string;
	count: number;
}

export interface DeliveryFileStats {
	totalFiles: number;
	totalImages: number;
	totalTextLength: number;
	ticketsWithDelivery: number;
	totalTickets: number;
	deliveryRate: number;
	ticketsWithDeliveryDetails: TicketDeliveryDetail[];
}

export interface TicketDeliveryDetail {
	id: string;
	title: string;
	status: string;
	filesCount: number;
	imagesCount: number;
	textLength: number;
	deliveryText?: string;
}

export interface TicketStats {
	last7Days: DailyStats[];
	avgCompletionHours: number;
	completedByMaintainer: MaintainerStats[];
	submittedByUser: SubmitterStats[];
	resolvedByDepartment: ResolverDepartmentStats[];
	last30Days: DailyStats[];
	maintenanceCompletedTotal: number;
	maintenanceCompletedByWeek: WeeklyStats[];
	deliveryStats: DeliveryFileStats;
}

// 根据用户ID获取权限组名称
function getUserGroupName(userId: string, groups: any[]): string {
	for (const group of groups) {
		if (group.user_ids && group.user_ids.includes(userId)) {
			return group.name;
		}
	}
	return '未分组';
}

// 计算工单统计
export function calculateTicketStats(tickets: Ticket[], groups: any[] = []): TicketStats {
	// 准备最近7天的日期键
	const today = new Date();
	const dayKeys7: string[] = [];
	for (let i = 6; i >= 0; i--) {
		const d = new Date(today);
		d.setDate(today.getDate() - i);
		const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
		dayKeys7.push(key);
	}

	// 准备最近30天的日期键
	const dayKeys30: string[] = [];
	for (let i = 29; i >= 0; i--) {
		const d = new Date(today);
		d.setDate(today.getDate() - i);
		const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
		dayKeys30.push(key);
	}

	// 初始化统计数据
	const submittedCounts: Record<string, number> = {};
	const completedCounts: Record<string, number> = {};
	const maintenanceCompletedCounts: Record<string, number> = {};
	const maintainerMap: Record<string, number> = {};
	const submitterMap: Record<string, number> = {};
	const resolverDepartmentMap: Record<string, number> = {};
	const weekMap: Record<string, number> = {};

	// 初始化计数
	dayKeys7.forEach(k => {
		submittedCounts[k] = 0;
		completedCounts[k] = 0;
	});
	dayKeys30.forEach(k => {
		maintenanceCompletedCounts[k] = 0;
	});

	let totalCompletionTime = 0;
	let completedTicketsCount = 0;
	let maintenanceCompletedTotal = 0;

	// 交付文件统计
	let totalFiles = 0;
	let totalImages = 0;
	let totalTextLength = 0;
	let ticketsWithDelivery = 0;
	const ticketsWithDeliveryDetails: TicketDeliveryDetail[] = [];

	// 处理每个工单
	for (const ticket of tickets) {
		const createdDate = new Date(ticket.created_at * 1000);
		const createdKey = `${createdDate.getFullYear()}-${String(createdDate.getMonth() + 1).padStart(2, '0')}-${String(createdDate.getDate()).padStart(2, '0')}`;
		
		// 统计提交者排行
		if (ticket.user_name) {
			submitterMap[ticket.user_name] = (submitterMap[ticket.user_name] || 0) + 1;
		}

		// 统计交付文件
		let hasDelivery = false;
		let filesCount = 0;
		let imagesCount = 0;
		let textLength = 0;
		
		if (ticket.delivery_files && Array.isArray(ticket.delivery_files)) {
			filesCount = ticket.delivery_files.length;
			totalFiles += filesCount;
			hasDelivery = true;
		}
		if (ticket.delivery_images && Array.isArray(ticket.delivery_images)) {
			imagesCount = ticket.delivery_images.length;
			totalImages += imagesCount;
			hasDelivery = true;
		}
		if (ticket.delivery_text) {
			textLength += ticket.delivery_text.length;
			totalTextLength += ticket.delivery_text.length;
			hasDelivery = true;
		}
		if (ticket.completion_notes) {
			textLength += ticket.completion_notes.length;
			totalTextLength += ticket.completion_notes.length;
			hasDelivery = true;
		}
		
		if (hasDelivery) {
			ticketsWithDelivery++;
			ticketsWithDeliveryDetails.push({
				id: ticket.id,
				title: ticket.title || `工单 #${ticket.id.slice(-6)}`,
				status: ticket.completion_status || 'pending',
				filesCount,
				imagesCount,
				textLength,
				deliveryText: ticket.delivery_text
			});
		}
		
		// 统计提交数量
		if (dayKeys7.includes(createdKey)) {
			submittedCounts[createdKey]++;
		}

		// 统计完成数量
		const statusStr = String(ticket.status || '').toLowerCase();
		if ((statusStr === 'resolved' || statusStr === 'closed') && ticket.resolved_at) {
			const resolvedDate = new Date(ticket.resolved_at * 1000);
			const resolvedKey = `${resolvedDate.getFullYear()}-${String(resolvedDate.getMonth() + 1).padStart(2, '0')}-${String(resolvedDate.getDate()).padStart(2, '0')}`;
			
			if (dayKeys7.includes(resolvedKey)) {
				completedCounts[resolvedKey]++;
			}

			// 计算平均完成时长
			const completionTime = (ticket.resolved_at - ticket.created_at) / 3600; // 转换为小时
			totalCompletionTime += completionTime;
			completedTicketsCount++;

			// 统计维护者完成量
			if (ticket.assigned_to_name) {
				maintainerMap[ticket.assigned_to_name] = (maintainerMap[ticket.assigned_to_name] || 0) + 1;
			}

			// 统计解决部门排行 - 基于实际权限组
			let department = '未分组';
			
			if (ticket.assigned_to) {
				department = getUserGroupName(ticket.assigned_to, groups);
			} else if (ticket.created_by) {
				// 如果没有分配人，使用创建人的权限组
				department = getUserGroupName(ticket.created_by, groups);
			}
			
			resolverDepartmentMap[department] = (resolverDepartmentMap[department] || 0) + 1;

			// 维护部门统计
			if (dayKeys30.includes(resolvedKey)) {
				const category = String(ticket.category || '').toLowerCase();
				const isMaintenance = category === 'technical_support' || 
									category === 'bug' || 
									ticket.title?.includes('维护') || 
									ticket.title?.includes('技术') ||
									ticket.description?.includes('维护') ||
									ticket.description?.includes('技术');
				
				if (isMaintenance) {
					maintenanceCompletedCounts[resolvedKey]++;
					maintenanceCompletedTotal++;
					
					// 按周分组
					const weekStart = new Date(resolvedDate);
					weekStart.setDate(weekStart.getDate() - weekStart.getDay());
					const weekKey = `${weekStart.getFullYear()}-${String(weekStart.getMonth() + 1).padStart(2, '0')}-${String(weekStart.getDate()).padStart(2, '0')}`;
					weekMap[weekKey] = (weekMap[weekKey] || 0) + 1;
				}
			}
		}
	}

	// 构建结果
	const last7Days = dayKeys7.map(k => ({
		date: k,
		submitted: submittedCounts[k] || 0,
		completed: completedCounts[k] || 0
	}));

	const last30Days = dayKeys30.map(k => ({
		date: k,
		completed: maintenanceCompletedCounts[k] || 0
	}));

	const avgCompletionHours = completedTicketsCount > 0 ? Math.round(totalCompletionTime / completedTicketsCount) : 0;

	const completedByMaintainer = Object.entries(maintainerMap)
		.map(([name, count]) => ({ name, count }))
		.sort((a, b) => b.count - a.count)
		.slice(0, 10);

	const submittedByUser = Object.entries(submitterMap)
		.map(([name, count]) => ({ name, count }))
		.sort((a, b) => b.count - a.count)
		.slice(0, 10);

	const resolvedByDepartment = Object.entries(resolverDepartmentMap)
		.map(([department, count]) => ({ department, count }))
		.sort((a, b) => b.count - a.count)
		.slice(0, 10);

	const maintenanceCompletedByWeek = Object.entries(weekMap)
		.map(([week, count]) => ({ week, count }))
		.sort((a, b) => a.week.localeCompare(b.week))
		.slice(-4); // 最近4周

	// 计算交付文件统计
	const deliveryStats: DeliveryFileStats = {
		totalFiles,
		totalImages,
		totalTextLength,
		ticketsWithDelivery,
		totalTickets: tickets.length,
		deliveryRate: tickets.length > 0 ? Math.round((ticketsWithDelivery / tickets.length) * 100) : 0,
		ticketsWithDeliveryDetails
	};

	return {
		last7Days,
		avgCompletionHours,
		completedByMaintainer,
		submittedByUser,
		resolvedByDepartment,
		last30Days,
		maintenanceCompletedTotal,
		maintenanceCompletedByWeek,
		deliveryStats
	};
}
