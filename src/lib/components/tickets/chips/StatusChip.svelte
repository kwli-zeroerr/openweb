<script lang="ts">
	import { getStatusInfo } from '$lib/constants/tickets';
	
	export let status: string;
	export let size: 'sm' | 'md' | 'lg' = 'md';
	export let showPulse: boolean = true;
	
	const statusInfo = getStatusInfo(status);
	
	const sizeClasses = {
		sm: 'px-2 py-1 text-xs',
		md: 'px-3 py-1.5 text-sm',
		lg: 'px-4 py-2 text-base'
	};
	
	const pulseClasses = showPulse ? 'animate-pulse' : '';
</script>

<div class="inline-flex items-center gap-2 {sizeClasses[size]} rounded-full font-semibold border-2 border-current/20 shadow-sm {statusInfo.bg} {statusInfo.color} transition-all duration-200 hover:shadow-md hover:scale-105">
	<div class="w-2 h-2 rounded-full bg-current {pulseClasses}"></div>
	<span class="whitespace-nowrap">{statusInfo.label}</span>
</div>
