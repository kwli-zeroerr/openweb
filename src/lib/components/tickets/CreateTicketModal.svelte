<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { createTicket, type CreateTicketForm } from '$lib/apis/tickets';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ExclamationTriangle from '$lib/components/icons/ExclamationTriangle.svelte';
	import InformationCircle from '$lib/components/icons/InformationCircle.svelte';
	import CheckCircle from '$lib/components/icons/CheckCircle.svelte';
	import BugAnt from '$lib/components/icons/BugAnt.svelte';
	import LightBulb from '$lib/components/icons/LightBulb.svelte';
	import ChatBubbleLeftRight from '$lib/components/icons/ChatBubbleLeftRight.svelte';
	import WrenchScrewdriver from '$lib/components/icons/WrenchScrewdriver.svelte';
	import Tag from '$lib/components/icons/Tag.svelte';

	const dispatch = createEventDispatcher();

	export let show = false;

	let title = '';
	let description = '';
	let priority: 'low' | 'medium' | 'high' | 'urgent' = 'medium';
	let category: 'bug' | 'feature_request' | 'general_inquiry' | 'technical_support' | 'other' = 'general_inquiry';
	let isSubmitting = false;

	const priorityOptions = [
		{ value: 'low', label: '低', icon: InformationCircle, color: 'text-blue-500' },
		{ value: 'medium', label: '中', icon: InformationCircle, color: 'text-yellow-500' },
		{ value: 'high', label: '高', icon: ExclamationTriangle, color: 'text-orange-500' },
		{ value: 'urgent', label: '紧急', icon: ExclamationTriangle, color: 'text-red-500' }
	];

	const categoryOptions = [
		{ value: 'bug', label: 'Bug 报告', icon: BugAnt, color: 'text-red-500' },
		{ value: 'feature_request', label: '功能请求', icon: LightBulb, color: 'text-blue-500' },
		{ value: 'general_inquiry', label: '一般咨询', icon: ChatBubbleLeftRight, color: 'text-green-500' },
		{ value: 'technical_support', label: '技术支持', icon: WrenchScrewdriver, color: 'text-purple-500' },
		{ value: 'other', label: '其他', icon: Tag, color: 'text-gray-500' }
	];

	function resetForm() {
		title = '';
		description = '';
		priority = 'medium';
		category = 'general_inquiry';
		isSubmitting = false;
	}

	async function handleSubmit() {
		if (!title.trim() || !description.trim()) {
			toast.error('请填写标题和描述');
			return;
		}

		isSubmitting = true;

		try {
			const formData: CreateTicketForm = {
				title: title.trim(),
				description: description.trim(),
				priority,
				category
			};

			await createTicket(formData);
			toast.success('工单提交成功！我们会尽快处理您的请求。');
			resetForm();
			dispatch('close');
		} catch (error) {
			console.error('Error creating ticket:', error);
			toast.error('提交失败，请稍后重试');
		} finally {
			isSubmitting = false;
		}
	}

	function handleClose() {
		resetForm();
		dispatch('close');
	}
</script>

{#if show}
	<div class="fixed inset-0 z-50 flex items-center justify-center">
		<!-- Backdrop -->
		<div class="absolute inset-0 bg-black/50" on:click={handleClose} on:keydown={(e) => e.key === 'Escape' && handleClose()} role="button" tabindex="0"></div>

		<!-- Modal -->
		<div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
			<!-- Header -->
			<div class="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white">提交问题工单</h2>
				<button
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					on:click={handleClose}
				>
					<XMark className="w-6 h-6" />
				</button>
			</div>

			<!-- Form -->
			<form on:submit|preventDefault={handleSubmit} class="p-6 space-y-6">
				<!-- Title -->
				<div>
					<label for="title" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						标题 *
					</label>
					<input
						id="title"
						type="text"
						bind:value={title}
						placeholder="简要描述您的问题"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
						required
					/>
				</div>

				<!-- Category -->
				<div>
					<fieldset>
						<legend class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							问题类型 *
						</legend>
						<div class="grid grid-cols-2 gap-3">
							{#each categoryOptions as option}
								<label class="relative">
									<input
										type="radio"
										bind:group={category}
										value={option.value}
										class="sr-only"
									/>
									<div class="flex items-center p-3 border rounded-lg cursor-pointer transition-colors {category === option.value ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'}">
										<svelte:component this={option.icon} className="w-5 h-5 {option.color} mr-2" />
										<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{option.label}</span>
									</div>
								</label>
							{/each}
						</div>
					</fieldset>
				</div>

				<!-- Priority -->
				<div>
					<fieldset>
						<legend class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							优先级 *
						</legend>
						<div class="grid grid-cols-4 gap-3">
							{#each priorityOptions as option}
								<label class="relative">
									<input
										type="radio"
										bind:group={priority}
										value={option.value}
										class="sr-only"
									/>
									<div class="flex flex-col items-center p-3 border rounded-lg cursor-pointer transition-colors {priority === option.value ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'}">
										<svelte:component this={option.icon} className="w-5 h-5 {option.color} mb-1" />
										<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{option.label}</span>
									</div>
								</label>
							{/each}
						</div>
					</fieldset>
				</div>

				<!-- Description -->
				<div>
					<label for="description" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						详细描述 *
					</label>
					<textarea
						id="description"
						bind:value={description}
						placeholder="请详细描述您遇到的问题，包括：&#10;1. 问题的具体表现&#10;2. 重现步骤&#10;3. 期望的结果&#10;4. 任何相关的错误信息"
						rows="6"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
						required
					></textarea>
				</div>

				<!-- Actions -->
				<div class="flex justify-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
					<button
						type="button"
						on:click={handleClose}
						class="px-6 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-600"
					>
						取消
					</button>
					<button
						type="submit"
						disabled={isSubmitting || !title.trim() || !description.trim()}
						class="px-6 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-blue-500 dark:hover:bg-blue-600"
					>
						{#if isSubmitting}
							<div class="flex items-center">
								<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
								提交中...
							</div>
						{:else}
							提交工单
						{/if}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}
