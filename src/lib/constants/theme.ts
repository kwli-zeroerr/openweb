// 前端样式主题配置
export const THEME_CONFIG = {
	colors: {
		primary: {
			light: 'from-blue-50 to-indigo-50',
			dark: 'from-blue-900/20 to-indigo-900/20',
			border: 'border-blue-200 dark:border-blue-700',
			text: 'text-blue-800 dark:text-blue-200'
		},
		secondary: {
			light: 'from-purple-50 to-pink-50',
			dark: 'from-purple-900/20 to-pink-900/20',
			border: 'border-purple-200 dark:border-purple-700',
			text: 'text-purple-800 dark:text-purple-200'
		},
		chart: {
			submitted: '#3b82f6',
			completed: '#10b981',
			maintenance: '#8b5cf6'
		}
	},
	layout: {
		gridCols: 2,
		gridRows: 4,
		cardHeight: 'h-[800px]'
	}
} as const;

// SVG 图表配置
export const CHART_CONFIG = {
	dimensions: {
		width: 200,
		height: 120,
		margin: 20,
		padding: 20
	},
	colors: {
		grid: 'currentColor',
		gridOpacity: 0.1,
		strokeWidth: 2.5,
		pointRadius: 4,
		pointStrokeWidth: 2
	},
	gradients: {
		submitted: {
			id: 'submittedGradient',
			color: '#3b82f6',
			opacity: 0.3
		},
		completed: {
			id: 'completedGradient', 
			color: '#10b981',
			opacity: 0.3
		},
		maintenance: {
			id: 'maintenanceGradient',
			color: '#8b5cf6', 
			opacity: 0.3
		}
	}
} as const;
