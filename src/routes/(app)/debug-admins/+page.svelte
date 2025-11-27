<script lang="ts">
	import { onMount } from 'svelte';
	import { getAvailableAdmins, type AvailableAdmin } from '$lib/apis/tickets';
	import { toast } from 'svelte-sonner';

	let availableAdmins: AvailableAdmin[] = [];
	let loading = false;
	let error = '';

	async function loadAdmins() {
		loading = true;
		error = '';
		try {
			console.log('开始加载管理员列表...');
			const response = await getAvailableAdmins();
			console.log('API响应:', response);
			availableAdmins = response.admins;
			console.log('管理员列表:', availableAdmins);
			toast.success(`成功加载 ${availableAdmins.length} 个管理员`);
		} catch (err) {
			console.error('加载管理员失败:', err);
			error = err instanceof Error ? err.message : '未知错误';
			toast.error(`加载失败: ${error}`);
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		loadAdmins();
	});
</script>

<div class="p-6 max-w-4xl mx-auto">
	<h1 class="text-2xl font-bold mb-6">管理员列表调试</h1>
	
	<div class="mb-4">
		<button 
			on:click={loadAdmins}
			disabled={loading}
			class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
		>
			{loading ? '加载中...' : '重新加载'}
		</button>
	</div>

	{#if error}
		<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
			<strong>错误:</strong> {error}
		</div>
	{/if}

	{#if loading}
		<div class="text-center py-8">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
			<p class="mt-2 text-gray-600">加载中...</p>
		</div>
	{:else if availableAdmins.length === 0}
		<div class="text-center py-8 text-gray-500">
			<p>暂无可分配的管理员</p>
		</div>
	{:else}
		<div class="bg-white shadow rounded-lg overflow-hidden">
			<table class="min-w-full divide-y divide-gray-200">
				<thead class="bg-gray-50">
					<tr>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">姓名</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">邮箱</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">角色</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">工作负载</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">组</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
					</tr>
				</thead>
				<tbody class="bg-white divide-y divide-gray-200">
					{#each availableAdmins as admin}
						<tr>
							<td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
								{admin.name}
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
								{admin.email}
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
								<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
									{admin.role}
								</span>
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
								{admin.workload}
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
								{admin.group || '-'}
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono text-xs">
								{admin.id}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
