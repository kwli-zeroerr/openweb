import { WEBUI_API_BASE_URL } from '$lib/constants';

// 请求缓存
const requestCache = new Map<string, { data: any; timestamp: number; ttl: number }>();

// 缓存配置
const CACHE_TTL = {
	tickets: 30000, // 30秒
	ticket: 10000,  // 10秒
	config: 300000, // 5分钟
};

function getCachedRequest<T>(key: string, ttl: number): T | null {
	const cached = requestCache.get(key);
	if (cached && Date.now() - cached.timestamp < ttl) {
		return cached.data;
	}
	return null;
}

function setCachedRequest<T>(key: string, data: T, ttl: number): void {
	requestCache.set(key, {
		data,
		timestamp: Date.now(),
		ttl
	});
}

// 清理过期缓存
function clearExpiredCache(): void {
	const now = Date.now();
	for (const [key, cached] of requestCache.entries()) {
		if (now - cached.timestamp > cached.ttl) {
			requestCache.delete(key);
		}
	}
}

// 清理特定工单的缓存
export const clearTicketCache = (ticketId?: string): void => {
	if (ticketId) {
		requestCache.delete(`ticket:${ticketId}`);
		// 清理工单列表缓存（因为可能包含这个工单）
		for (const key of requestCache.keys()) {
			if (key.startsWith('tickets:')) {
				requestCache.delete(key);
			}
		}
	} else {
		// 清理所有缓存
		requestCache.clear();
	}
};

// 定期清理过期缓存
setInterval(clearExpiredCache, 60000); // 每分钟清理一次

export interface Ticket {
	id: string;
	title: string;
	description: string;
	status: 'open' | 'in_progress' | 'resolved' | 'closed';
	priority: 'low' | 'medium' | 'high' | 'urgent';
	category: 'bug' | 'feature_request' | 'general_inquiry' | 'technical_support' | 'other';
	user_id: string;
	user_name: string;
	user_email: string;
	assigned_to?: string;
	assigned_to_name?: string;
	attachments?: string[];
	tags?: string[];
	comments?: TicketComment[];
	created_at: number;
	updated_at: number;
	resolved_at?: number;
    // AI工单相关字段
    is_ai_generated?: boolean;
    source_feedback_id?: string;
    ai_analysis?: any;
    
    // 交付验收相关字段
    completion_status?: 'pending' | 'submitted' | 'verified' | 'rejected';
    verification_score?: number;
    verification_checklist?: Array<{
        id: string;
        label: string;
        checked: boolean;
    }>;
	// 任务分配相关字段
	task_requirements?: string;
	completion_criteria?: string;
	task_deadline?: number;
	task_priority?: string;
	// 交付要求
	required_files?: string;
	required_text?: string;
	required_images?: string;
	delivery_instructions?: string;
	// 任务完成
	delivery_files?: any[];
	delivery_text?: string;
	delivery_images?: any[];
	completion_status?: string;
	completion_notes?: string;
}

export interface TicketComment {
	id: string;
	content: string;
	author_id: string;
	author_name: string;
	is_internal: boolean;
	created_at: number;
}

export interface CreateTicketForm {
	title: string;
	description: string;
	priority: 'low' | 'medium' | 'high' | 'urgent';
	category: 'bug' | 'feature_request' | 'general_inquiry' | 'technical_support' | 'other';
	attachments?: string[];
	tags?: string[];
}

export interface UpdateTicketForm {
	title?: string;
	description?: string;
	status?: 'open' | 'in_progress' | 'resolved' | 'closed';
	priority?: 'low' | 'medium' | 'high' | 'urgent';
	category?: 'bug' | 'feature_request' | 'general_inquiry' | 'technical_support' | 'other';
	assigned_to?: string;
	tags?: string[];
}

export interface AddCommentForm {
	content: string;
	is_internal?: boolean;
}

export interface AssignTicketForm {
	assigned_to: string;
	reason?: string;
	// 任务要求
	task_requirements?: string;
	completion_criteria?: string;
	task_deadline?: number;
	task_priority?: string;
	// 交付要求
	required_files?: string;
	required_text?: string;
	required_images?: string;
	delivery_instructions?: string;
}

export interface TransferTicketForm {
	assigned_to: string;
	reason: string;
}

export interface TaskDeliveryForm {
	delivery_files?: any[];
	delivery_text?: string;
	delivery_images?: any[];
	completion_notes?: string;
}

export interface TaskVerificationForm {
	verified: boolean;
	verification_notes?: string;
	verification_score?: number;
	verification_checklist?: Array<{
		id: string;
		label: string;
		checked: boolean;
	}>;
}

export interface AvailableAdmin {
	id: string;
	name: string;
	email: string;
	workload: number;
	role: string;
	group?: string;
}

export interface TicketListResponse {
	tickets: Ticket[];
	total: number;
}

export interface TicketStats {
	total: number;
	open: number;
	in_progress: number;
	resolved: number;
	closed: number;
}

export const createTicket = async (formData: CreateTicketForm): Promise<Ticket> => {
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/tickets/`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(formData)
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to create ticket');
	}

	return response.json();
};

export const getTickets = async (params?: {
	user_id?: string;
	assigned_to?: string;
	status?: string;
	priority?: string;
	category?: string;
	skip?: number;
	limit?: number;
}): Promise<TicketListResponse> => {
	// 生成缓存键
	const cacheKey = `tickets:${JSON.stringify(params || {})}`;
	
	// 检查缓存
	const cached = getCachedRequest<TicketListResponse>(cacheKey, CACHE_TTL.tickets);
	if (cached) {
		return cached;
	}
	
	const searchParams = new URLSearchParams();
	if (params) {
		Object.entries(params).forEach(([key, value]) => {
			if (value !== undefined && value !== null) {
				searchParams.append(key, value.toString());
			}
		});
	}

	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/tickets/?${searchParams}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to get tickets');
	}

	const data = await response.json();
	
	// 缓存结果
	setCachedRequest(cacheKey, data, CACHE_TTL.tickets);
	
	return data;
};

export const getTicket = async (ticketId: string): Promise<Ticket> => {
	// 生成缓存键
	const cacheKey = `ticket:${ticketId}`;
	
	// 检查缓存
	const cached = getCachedRequest<Ticket>(cacheKey, CACHE_TTL.ticket);
	if (cached) {
		return cached;
	}
	
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/tickets/${ticketId}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	if (!response.ok) {
		let errorMessage = 'Failed to get ticket';
		try {
			const error = await response.json();
			errorMessage = error.detail || error.message || errorMessage;
		} catch (e) {
			// If response is not JSON, use status text
			errorMessage = response.statusText || errorMessage;
		}
		
		// Add more context to the error
		if (response.status === 404) {
			errorMessage = `Ticket not found (ID: ${ticketId})`;
		} else if (response.status === 403) {
			errorMessage = 'Access denied to this ticket';
		} else if (response.status === 401) {
			errorMessage = 'Authentication required';
		}
		
		throw new Error(errorMessage);
	}

	const data = await response.json();
	
	// 缓存结果
	setCachedRequest(cacheKey, data, CACHE_TTL.ticket);
	
	return data;
};

export const updateTicket = async (ticketId: string, formData: UpdateTicketForm): Promise<Ticket> => {
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/tickets/${ticketId}`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(formData)
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to update ticket');
	}

	const data = await response.json();
	
	// 清理相关缓存
	clearTicketCache(ticketId);
	
	return data;
};

export const addComment = async (ticketId: string, formData: AddCommentForm): Promise<void> => {
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/tickets/${ticketId}/comments`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(formData)
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to add comment');
	}
};

export const deleteTicket = async (ticketId: string): Promise<void> => {
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/tickets/${ticketId}`, {
		method: 'DELETE',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to delete ticket');
	}
};

export const getTicketStats = async (): Promise<TicketStats> => {
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/tickets/stats/summary`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to get ticket stats');
	}

	return response.json();
};

export const generateAIAnalysis = async (ticketId: string): Promise<{ success: boolean; message: string; ai_analysis?: any }> => {
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/tickets/${ticketId}/generate-ai-analysis`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to generate AI analysis');
	}

	return response.json();
};

export const assignTicket = async (ticketId: string, formData: AssignTicketForm): Promise<void> => {
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/tickets/${ticketId}/assign`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(formData)
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to assign ticket');
	}
};

export const transferTicket = async (ticketId: string, formData: TransferTicketForm): Promise<void> => {
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/tickets/${ticketId}/transfer`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(formData)
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to transfer ticket');
	}
};

export const getAvailableAdmins = async (): Promise<{ admins: AvailableAdmin[] }> => {
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/tickets/available-admins`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to get available admins');
	}

	return response.json();
};

export const deliverTask = async (ticketId: string, formData: FormData): Promise<void> => {
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/tickets/${ticketId}/deliver`, {
		method: 'POST',
		headers: {
			...(token && { authorization: `Bearer ${token}` })
			// 不设置Content-Type，让浏览器自动设置multipart/form-data
		},
		body: formData
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to deliver task');
	}
};

export const verifyTaskCompletion = async (ticketId: string, formData: TaskVerificationForm): Promise<void> => {
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/tickets/${ticketId}/verify`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(formData)
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to verify task completion');
	}
};
