<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { updateFileMetadataById } from '$lib/apis/files';
	import { getGroups } from '$lib/apis/groups';
	import { onMount } from 'svelte';

	export let selectedFile: any;
	export let knowledge: any;

	let editingFileCategory = false;
	let editingFileVersion = false;
	let editingFileOwner = false;
	let newFileCategory = '';
	let newFileVersion = '';
	let newFileOwner = '';
	let availableFileCategories: string[] = [];
	let availableFileVersions: string[] = [];
	let availableFileOwners: string[] = [];
	let availableGroups: any[] = []; // 存储部门列表

	// 获取部门列表
	const loadGroups = async () => {
		try {
			const groups = await getGroups(localStorage.token);
			availableGroups = groups || [];
		} catch (error) {
			console.error('Failed to load groups:', error);
			availableGroups = [];
		}
	};

	// 组件挂载时加载部门列表
	onMount(() => {
		loadGroups();
	});

	// File metadata functions
	const addFileCategory = async (category: string) => {
		if (!category?.trim()) return;
		await updateFileMetadata({ category: category.trim() });
	};

	const updateFileVersion = async (version: string) => {
		if (!version?.trim()) return;
		await updateFileMetadata({ version: version.trim() });
	};

	const updateFileOwner = async (owner: string) => {
		if (!owner?.trim()) return;
		await updateFileMetadata({ owner: owner.trim() });
	};

	const updateFileMetadata = async (metadata: any) => {
		if (!selectedFile?.id) return;
		
		try {
			const res = await updateFileMetadataById(localStorage.token, selectedFile.id, metadata);
			
			if (res) {
				// Update local state
				const fileIndex = knowledge.files.findIndex((f: any) => f.id === selectedFile.id);
				if (fileIndex !== -1) {
					knowledge.files[fileIndex].meta = { ...knowledge.files[fileIndex].meta, ...metadata };
					knowledge = { ...knowledge }; // Trigger reactivity
				}
				
				// 同时更新 selectedFile 的状态
				selectedFile.meta = { ...selectedFile.meta, ...metadata };
				selectedFile = { ...selectedFile }; // Trigger reactivity
				
				toast.success('文件信息已保存');
			}
		} catch (error: any) {
			console.error('Failed to update file metadata:', error);
			toast.error('保存失败: ' + (error.message || '未知错误'));
		}
	};

	const loadAvailableFileMetadata = async () => {
		if (!knowledge?.files) return;
		
		const allCategories = new Set();
		const allVersions = new Set();
		const allOwners = new Set();

		knowledge.files.forEach((file: any) => {
			if (file.meta?.category) allCategories.add(file.meta.category);
			if (file.meta?.version) allVersions.add(file.meta.version);
			if (file.meta?.owner) allOwners.add(file.meta.owner);
		});

		availableFileCategories = Array.from(allCategories) as string[];
		availableFileVersions = Array.from(allVersions) as string[];
		availableFileOwners = Array.from(allOwners) as string[];
	};

	// Load metadata when component mounts or selectedFile changes
	$: if (selectedFile && knowledge) {
		loadAvailableFileMetadata();
	}
</script>

{#if selectedFile}
	<!-- File Metadata (Desktop) -->
	<div class="mb-2 flex flex-wrap items-center gap-3 text-xs border-b border-gray-100 dark:border-gray-800 pb-2 px-3">
		<!-- Category -->
		<div class="flex items-center gap-1">
			<span class="text-gray-500">分类</span>
			{#if editingFileCategory}
				<select
					class="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
					bind:value={selectedFile.meta.category}
					on:change={() => addFileCategory(selectedFile.meta.category)}
				>
					<option value="">选择分类...</option>
					{#each availableFileCategories as cat}
						<option value={cat}>{cat}</option>
					{/each}
				</select>
				<input
					class="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
					type="text"
					placeholder="或输入新分类"
					bind:value={newFileCategory}
					on:keydown={(e) => {
						if (e.key === 'Enter') {
							e.preventDefault();
							if (newFileCategory.trim()) {
								addFileCategory(newFileCategory.trim());
								newFileCategory = '';
								editingFileCategory = false;
							}
						}
					}}
				/>
				<button
					class="px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600"
					on:click={() => {
						if (newFileCategory?.trim()) {
							addFileCategory(newFileCategory.trim());
							newFileCategory = '';
						}
						editingFileCategory = false;
					}}
				>完成</button>
			{:else}
				{#if selectedFile.meta.category}
					<span class="inline-flex items-center px-2 py-0.5 rounded bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">{selectedFile.meta.category}</span>
				{:else}
					<span class="text-gray-400">未设置</span>
				{/if}
				<button class="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" on:click={() => editingFileCategory = true}>编辑</button>
			{/if}
		</div>

		<!-- Version -->
		<div class="flex items-center gap-1">
			<span class="text-gray-500">版本</span>
			{#if editingFileVersion}
				<select
					class="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
					bind:value={selectedFile.meta.version}
					on:change={() => updateFileVersion(selectedFile.meta.version)}
				>
					<option value="">选择版本...</option>
					{#each availableFileVersions as version}
						<option value={version}>{version}</option>
					{/each}
				</select>
				<input
					class="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
					type="text"
					placeholder="或输入新版本"
					bind:value={newFileVersion}
					on:keydown={(e) => {
						if (e.key === 'Enter') {
							e.preventDefault();
							if (newFileVersion.trim()) {
								updateFileVersion(newFileVersion.trim());
								newFileVersion = '';
								editingFileVersion = false;
							}
						}
					}}
				/>
				<button
					class="px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600"
					on:click={() => {
						if (newFileVersion?.trim()) {
							updateFileVersion(newFileVersion.trim());
							newFileVersion = '';
						}
						editingFileVersion = false;
					}}
				>完成</button>
			{:else}
				{#if selectedFile.meta.version}
					<span class="inline-flex items-center px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">v{selectedFile.meta.version}</span>
				{:else}
					<span class="text-gray-400">未设置</span>
				{/if}
				<button class="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" on:click={() => editingFileVersion = true}>编辑</button>
			{/if}
		</div>

		<!-- Owner -->
		<div class="flex items-center gap-1">
			<span class="text-gray-500">负责人</span>
			{#if editingFileOwner}
				<select
					class="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
					bind:value={newFileOwner}
					on:change={() => {
						if (newFileOwner) {
							updateFileOwner(newFileOwner);
							newFileOwner = '';
							editingFileOwner = false;
						}
					}}
				>
					<option value="">选择负责部门...</option>
					{#each availableGroups as group}
						<option value={group.name}>{group.name}</option>
					{/each}
					{#if availableGroups.length === 0}
						<option value="" disabled>暂无部门数据</option>
					{/if}
				</select>
				<span class="text-xs text-gray-400">或</span>
				<input
					class="text-xs px-2 py-1 rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
					type="text"
					placeholder="输入个人负责人"
					bind:value={newFileOwner}
					on:keydown={(e) => {
						if (e.key === 'Enter') {
							e.preventDefault();
							if (newFileOwner.trim()) {
								updateFileOwner(newFileOwner.trim());
								newFileOwner = '';
								editingFileOwner = false;
							}
						}
					}}
				/>
				<button
					class="px-2 py-1 rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600"
					on:click={() => {
						if (newFileOwner?.trim()) {
							updateFileOwner(newFileOwner.trim());
							newFileOwner = '';
						}
						editingFileOwner = false;
					}}
				>完成</button>
			{:else}
				{#if selectedFile.meta.owner}
					<span class="inline-flex items-center px-2 py-0.5 rounded bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">{selectedFile.meta.owner}</span>
				{:else}
					<span class="text-gray-400">未设置</span>
				{/if}
				<button class="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600" on:click={() => editingFileOwner = true}>编辑</button>
			{/if}
		</div>

		<!-- Upload Date (Read-only) -->
		<div class="flex items-center gap-1">
			<span class="text-gray-500">上传日期</span>
			<span class="text-gray-600 dark:text-gray-400">
				{selectedFile.created_at ? (selectedFile.created_at > 1000000000 ? new Date(selectedFile.created_at * 1000).toLocaleDateString('zh-CN') : new Date(selectedFile.created_at).toLocaleDateString('zh-CN')) : '未知'}
			</span>
		</div>
	</div>

{/if}
