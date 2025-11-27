<script>
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import Settings from '$lib/components/admin/Settings.svelte';

	onMount(() => {
		goto('/admin/settings/tickets');
	});
</script>

<Settings />
