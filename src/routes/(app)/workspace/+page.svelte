<script lang="ts">
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { onMount } from 'svelte';

	onMount(() => {
		if ($user?.role !== 'admin') {
			if ($user?.permissions?.workspace?.analytics) {
				goto('/workspace/analytics');
			} else if ($user?.permissions?.workspace?.models) {
				goto('/workspace/models');
			} else if ($user?.permissions?.workspace?.knowledge) {
				goto('/workspace/knowledge');
			} else if ($user?.permissions?.workspace?.tools) {
				goto('/workspace/tools');
			} else if ($user?.permissions?.workspace?.tickets || $user?.permissions?.workspace?.tickets_view_all) {
				goto('/workspace/tickets');
			} else {
				goto('/');
			}
		} else {
			goto('/workspace/analytics');
		}
	});
</script>
