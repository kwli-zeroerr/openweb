<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { updateFileById } from '$lib/apis/files';

	const dispatch = createEventDispatcher();

	export let show = false;
	export let file: any = null;

	let selectedFile: File | null = null;
	let newVersion = '';
	let updateNotes = '';
	let isUploading = false;

	// 重置表单
	const resetForm = () => {
		selectedFile = null;
		newVersion = '';
		updateNotes = '';
		isUploading = false;
	};

	// 关闭模态框
	const closeModal = () => {
		resetForm();
		dispatch('close');
	};

	// 处理文件选择
	const handleFileSelect = (event: Event) => {
		const target = event.target as HTMLInputElement;
		if (target.files && target.files[0]) {
			selectedFile = target.files[0];
		}
	};

	// 处理文件更新
	const handleUpdate = async () => {
		if (!selectedFile || !newVersion.trim()) {
			toast.error('请选择文件并填写版本号');
			return;
		}

		if (!file?.id) {
			toast.error('文件信息错误');
			return;
		}

		isUploading = true;

		try {
			// 准备元数据
			const metadata = {
				collection_name: file.meta?.collection_name,
				category: file.meta?.category,
				owner: file.meta?.owner,
				version: newVersion.trim(),
				update_notes: updateNotes.trim(),
				previous_version: file.meta?.version || '1.0',
				update_type: 'file_update'
			};

			console.log('Updating file:', {
				fileId: file.id,
				fileName: selectedFile.name,
				version: newVersion,
				metadata
			});

			// 更新文件
			const uploadedFile = await updateFileById(localStorage.token, file.id, selectedFile, metadata);

			if (uploadedFile) {
				toast.success(`文件已更新到版本 ${newVersion}`);
				dispatch('updated', {
					oldFile: file,
					newFile: uploadedFile,
					version: newVersion,
					notes: updateNotes
				});
				closeModal();
			} else {
				toast.error('文件更新失败');
			}
		} catch (error) {
			console.error('File update error:', error);
			toast.error(`文件更新失败: ${error}`);
		} finally {
			isUploading = false;
		}
	};

	// 监听文件变化，自动关闭模态框
	$: if (!show) {
		resetForm();
	}
</script>

{#if show}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto">
			<!-- Header -->
			<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
					更新文件
				</h3>
				<button
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					on:click={closeModal}
					disabled={isUploading}
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
					</svg>
				</button>
			</div>

			<!-- Content -->
			<div class="p-4 space-y-4">
				<!-- Current File Info -->
				{#if file}
					<div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
						<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">当前文件</div>
						<div class="text-sm font-medium text-gray-900 dark:text-gray-100">
							{file.meta?.name || file.filename}
						</div>
						{#if file.meta?.version}
							<div class="text-xs text-gray-500 dark:text-gray-400 mt-1">
								当前版本: v{file.meta.version}
							</div>
						{/if}
					</div>
				{/if}

				<!-- File Selection -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						选择新文件 *
					</label>
					<input
						type="file"
						class="block w-full text-sm text-gray-500 dark:text-gray-400
							file:mr-4 file:py-2 file:px-4
							file:rounded-lg file:border-0
							file:text-sm file:font-medium
							file:bg-blue-50 file:text-blue-700
							hover:file:bg-blue-100
							dark:file:bg-blue-900/20 dark:file:text-blue-300
							dark:hover:file:bg-blue-900/30
							border border-gray-300 dark:border-gray-600 rounded-lg
							bg-white dark:bg-gray-700"
						on:change={handleFileSelect}
						disabled={isUploading}
					/>
					{#if selectedFile}
						<div class="mt-2 text-sm text-gray-600 dark:text-gray-400">
							已选择: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
						</div>
					{/if}
				</div>

				<!-- Version Input -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						新版本号 *
					</label>
					<input
						type="text"
						bind:value={newVersion}
						placeholder="例如: 1.1, 2.0, 1.2.3"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
							bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
							focus:ring-2 focus:ring-blue-500 focus:border-transparent
							disabled:opacity-50 disabled:cursor-not-allowed"
						disabled={isUploading}
					/>
					<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">
						建议使用语义化版本号 (如: 1.0, 1.1, 2.0)
					</div>
				</div>

				<!-- Update Notes -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						更新说明 (可选)
					</label>
					<textarea
						bind:value={updateNotes}
						placeholder="描述本次更新的内容..."
						rows="3"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
							bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
							focus:ring-2 focus:ring-blue-500 focus:border-transparent
							resize-none disabled:opacity-50 disabled:cursor-not-allowed"
						disabled={isUploading}
					></textarea>
				</div>
			</div>

			<!-- Footer -->
			<div class="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
				<button
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300
						bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600
						rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={closeModal}
					disabled={isUploading}
				>
					取消
				</button>
				<button
					class="px-4 py-2 text-sm font-medium text-white
						bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400
						rounded-lg transition-colors disabled:cursor-not-allowed
						flex items-center gap-2"
					on:click={handleUpdate}
					disabled={!selectedFile || !newVersion.trim() || isUploading}
				>
					{#if isUploading}
						<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						更新中...
					{:else}
						更新文件
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
