<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import FileItem from '$lib/components/common/FileItem.svelte';

	export let selectedFileId = null;
	export let files = [];

	export let small = false;
</script>

<div class=" max-h-full flex flex-col w-full">
	{#each files as file}
		<div class="mt-1 px-2">
			<div class="flex flex-col">
				<FileItem
					className="w-full"
					colorClassName="{selectedFileId === file.id
						? ' bg-gray-50 dark:bg-gray-850'
						: 'bg-transparent'} hover:bg-gray-50 dark:hover:bg-gray-850 transition"
					{small}
					item={file}
					name={file?.name ?? file?.meta?.name}
					type="file"
					size={file?.size ?? file?.meta?.size ?? ''}
					loading={file.status === 'uploading'}
					dismissible
					on:click={() => {
						if (file.status === 'uploading') {
							return;
						}

						dispatch('click', file.id);
					}}
					on:dismiss={() => {
						if (file.status === 'uploading') {
							return;
						}

						dispatch('delete', file.id);
					}}
				/>
				
				<!-- File Metadata Display -->
				{#if file.meta && (file.meta.category || file.meta.version || file.meta.owner)}
					<div class="flex flex-col gap-1 mt-1 px-2 pb-1">
						<div class="flex flex-wrap gap-1">
							{#if file.meta.category}
								<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
									{file.meta.category}
								</span>
							{/if}
							{#if file.meta.version}
								<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
									v{file.meta.version}
								</span>
							{/if}
							{#if file.meta.owner}
								<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
									{file.meta.owner}
								</span>
							{/if}
						</div>
						{#if file.created_at}
							<div class="text-xs text-gray-500 dark:text-gray-400">
								上传: {new Date(file.created_at * 1000).toLocaleDateString('zh-CN')}
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{/each}
</div>
