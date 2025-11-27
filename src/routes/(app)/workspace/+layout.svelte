<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { get } from 'svelte/store';
	import {
		WEBUI_NAME,
		showSidebar,
		functions,
		user,
		mobile,
		models,
		knowledge,
		tools
	} from '$lib/stores';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let previousSidebarState = false;

	onMount(() => {
		previousSidebarState = get(showSidebar);
		// 工作空间默认收起对话侧边栏，避免历史对话导航干扰
		showSidebar.set(false);

		const initialize = async () => {
			if ($user?.role !== 'admin') {
				if ($page.url.pathname.includes('/models') && !$user?.permissions?.workspace?.models) {
					goto('/');
				} else if (
					$page.url.pathname.includes('/knowledge') &&
					!$user?.permissions?.workspace?.knowledge
				) {
					goto('/');
				} else if ($page.url.pathname.includes('/tools') && !$user?.permissions?.workspace?.tools) {
					goto('/');
				} else if ($page.url.pathname.includes('/agent') && $user?.role !== 'admin') {
					goto('/');
				} else if (
					$page.url.pathname.includes('/tickets') &&
					!$user?.permissions?.workspace?.tickets &&
					!$user?.permissions?.workspace?.tickets_view_all
				) {
					goto('/');
				} else if (
					$page.url.pathname.includes('/analytics') &&
					!$user?.permissions?.workspace?.analytics &&
					$user?.role !== 'admin'
				) {
					goto('/');
				}
			}

			loaded = true;
		};

		initialize();

		return () => {
			// 离开工作空间后恢复之前的侧边栏状态
			showSidebar.set(previousSidebarState);
		};
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Workspace')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		class=" relative flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-260px)]'
			: ''} max-w-full"
	>
		<nav class="   px-2.5 pt-1.5 backdrop-blur-xl drag-region">
			<div class=" flex items-center gap-1">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} self-center flex flex-none items-center">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class=" cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition cursor-"
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
							>
								<div class=" self-center p-1.5">
									<Sidebar />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}

				<div class="">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent py-1 touch-auto pointer-events-auto"
					>
						{#if $user?.role === 'admin' || $user?.permissions?.workspace?.models}
							<a
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/models')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href="/workspace/models">{$i18n.t('Models')}</a
							>
						{/if}

						{#if $user?.role === 'admin' || $user?.permissions?.workspace?.knowledge}
							<a
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/knowledge')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href="/workspace/knowledge"
							>
								{$i18n.t('Knowledge')}
							</a>
						{/if}

					{#if $user?.role === 'admin' || $user?.permissions?.workspace?.tools}
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/tools')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/workspace/tools"
						>
							{$i18n.t('Tools')}
						</a>
					{/if}

					{#if $user?.role === 'admin'}
						<a
							class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/agent')
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							href="/workspace/agent"
						>
							Agent
						</a>
					{/if}

					{#if $user?.role === 'admin' || $user?.permissions?.workspace?.tickets}
							<a
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/tickets')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href="/workspace/tickets"
							>
								{$i18n.t('Tickets')}
							</a>
						{/if}

						{#if $user?.permissions?.workspace?.analytics || $user?.role === 'admin'}
							<a
								class="min-w-fit p-1.5 {$page.url.pathname.includes('/workspace/analytics')
									? ''
									: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
								href="/workspace/analytics"
							>
								运营分析
							</a>
						{/if}
					</div>
				</div>

				<!-- <div class="flex items-center text-xl font-semibold">{$i18n.t('Workspace')}</div> -->
			</div>
		</nav>

		<div class="  pb-1 px-[18px] flex-1 max-h-full overflow-y-auto" id="workspace-container">
			<slot />
		</div>
	</div>
{/if}
