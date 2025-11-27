<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { updateFileMetadataById } from '$lib/apis/files';
	import { toast } from 'svelte-sonner';

	const dispatch = createEventDispatcher();

	export let isOpen = false;
	export let fileIds = [];
	export let files = [];

	let selectedCategory = '';
	let isLoading = false;

	// 预定义的分类选项
	const availableCategories = [
		'技术文档',
		'产品手册',
		'用户指南',
		'API文档',
		'培训材料',
		'设计文件',
		'测试报告',
		'项目文档',
		'会议记录',
		'其他'
	];

	// 重置表单
	const resetForm = () => {
		selectedCategory = '';
	};

	// 关闭模态框
	const closeModal = () => {
		resetForm();
		dispatch('close');
	};

	// 批量设置分类
	const handleBatchAssign = async () => {
		if (!selectedCategory.trim()) {
			toast.error('请选择分类');
			return;
		}

		isLoading = true;
		let successCount = 0;
		let failCount = 0;

		try {
			// 并发处理所有文件
			const promises = fileIds.map(async (fileId) => {
				try {
					await updateFileMetadataById(localStorage.token, fileId, { category: selectedCategory.trim() });
					successCount++;
				} catch (error) {
					console.error(`Failed to update file ${fileId}:`, error);
					failCount++;
				}
			});

			await Promise.all(promises);

			if (successCount > 0) {
				toast.success(`成功设置 ${successCount} 个文件的分类`);
				dispatch('success', { 
					fileIds, 
					category: selectedCategory.trim(),
					successCount,
					failCount 
				});
			}

			if (failCount > 0) {
				toast.warning(`${failCount} 个文件设置失败`);
			}

			closeModal();
		} catch (error) {
			console.error('Batch assignment failed:', error);
			toast.error('批量设置失败');
		} finally {
			isLoading = false;
		}
	};

	// 监听模态框打开，重置表单
	$: if (isOpen) {
		resetForm();
	}
</script>

{#if isOpen}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" on:click={closeModal}>
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4" on:click|stopPropagation>
			<!-- Header -->
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
						批量设置分类
					</h3>
					<button
						class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
						on:click={closeModal}
					>
						<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
						</svg>
					</button>
				</div>
			</div>

			<!-- Content -->
			<div class="px-6 py-4">
				<!-- 文件列表 -->
				<div class="mb-4">
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-2">
						将为以下 {fileIds.length} 个文件设置分类：
					</p>
					<div class="max-h-32 overflow-y-auto bg-gray-50 dark:bg-gray-700 rounded p-2">
						{#each files.filter(f => fileIds.includes(f.id)) as file}
							<div class="text-xs text-gray-700 dark:text-gray-300 py-1 truncate">
								{file.meta?.name || file.name}
							</div>
						{/each}
					</div>
				</div>

				<!-- 分类选择 -->
				<div class="mb-4">
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						选择分类
					</label>
					<select
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
						bind:value={selectedCategory}
					>
						<option value="">选择分类...</option>
						{#each availableCategories as category}
							<option value={category}>{category}</option>
						{/each}
					</select>
					<input
						class="w-full mt-2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
						type="text"
						placeholder="或输入自定义分类"
						bind:value={selectedCategory}
					/>
				</div>
			</div>

			<!-- Footer -->
			<div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
				<button
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
					on:click={closeModal}
					disabled={isLoading}
				>
					取消
				</button>
				<button
					class="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={handleBatchAssign}
					disabled={isLoading || !selectedCategory.trim()}
				>
					{#if isLoading}
						<svg class="w-4 h-4 animate-spin inline mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
						</svg>
					{/if}
					{isLoading ? '设置中...' : '确认设置'}
				</button>
			</div>
		</div>
	</div>
{/if}
