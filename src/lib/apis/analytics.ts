import { WEBUI_API_BASE_URL } from '$lib/constants';

// 前端缓存机制
const analyticsCache = new Map<string, { data: any; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000; // 5分钟缓存

function getCachedData(key: string): any | null {
	const cached = analyticsCache.get(key);
	if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
		return cached.data;
	}
	return null;
}

function setCachedData(key: string, data: any): void {
	analyticsCache.set(key, { data, timestamp: Date.now() });
}

function clearAnalyticsCache(): void {
	analyticsCache.clear();
}

export interface UserActivityStats {
	user_id: string;
	user_name: string;
	user_email: string;
	total_messages: number;
	total_thumbs_up: number;
	total_thumbs_down: number;
	thumbs_up_ratio: number;
	last_active?: string;
	login_count: number;
	session_count: number;
	model_usage_count: number;
	knowledge_access_count: number;
	tool_usage_count: number;
	ticket_count: number;
}

export interface DailyStats {
	date: string;
	daily_active_users: number;
	total_messages: number;
	total_thumbs_up: number;
	total_thumbs_down: number;
	thumbs_up_ratio: number;
	new_users: number;
	total_sessions: number;
	model_usage_count: number;
	knowledge_access_count: number;
	tool_usage_count: number;
	ticket_count: number;
}

export interface AnalyticsSummary {
	total_users: number;
	active_users_today: number;
	active_users_this_week: number;
	active_users_this_month: number;
	total_messages: number;
	total_thumbs_up: number;
	total_thumbs_down: number;
	overall_thumbs_up_ratio: number;
	daily_stats: DailyStats[];
	top_users: UserActivityStats[];
}

export const getAnalyticsSummary = async (days: number = 30): Promise<AnalyticsSummary> => {
	const cacheKey = `analytics_summary_${days}`;
	const cachedData = getCachedData(cacheKey);
	if (cachedData) {
		return cachedData;
	}

	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/analytics/summary?days=${days}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to get analytics summary');
	}

	const data = await response.json();
	setCachedData(cacheKey, data);
	return data;
};

export const getUserActivityStats = async (
	userId?: string,
	days: number = 30,
	limit: number = 50
): Promise<UserActivityStats[]> => {
	const cacheKey = `user_activity_stats_${userId}_${days}_${limit}`;
	const cachedData = getCachedData(cacheKey);
	if (cachedData) {
		return cachedData;
	}

	const token = localStorage.token;
	let url = `${WEBUI_API_BASE_URL}/analytics/users?days=${days}&limit=${limit}`;
	if (userId) {
		url += `&user_id=${userId}`;
	}

	const response = await fetch(url, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to get user activity stats');
	}

	const data = await response.json();
	setCachedData(cacheKey, data);
	return data;
};

export const getDailyStats = async (days: number = 30): Promise<DailyStats[]> => {
	const cacheKey = `daily_stats_${days}`;
	const cachedData = getCachedData(cacheKey);
	if (cachedData) {
		return cachedData;
	}

	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/analytics/daily?days=${days}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to get daily stats');
	}

	const data = await response.json();
	setCachedData(cacheKey, data);
	return data;
};

export const getMyActivityStats = async (days: number = 30): Promise<UserActivityStats> => {
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/analytics/my-stats?days=${days}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to get my activity stats');
	}

	return response.json();
};

export const logAnalyticsEvent = async (
	eventType: string,
	eventData?: Record<string, any>,
	sessionId?: string
): Promise<void> => {
	const token = localStorage.token;
	const response = await fetch(`${WEBUI_API_BASE_URL}/analytics/log-event`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			event_type: eventType,
			event_data: eventData,
			session_id: sessionId
		})
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Failed to log analytics event');
	}

	// 记录事件后清除缓存，确保数据实时性
	clearAnalyticsCache();
};

// 导出清除缓存函数，供外部使用
export { clearAnalyticsCache };
