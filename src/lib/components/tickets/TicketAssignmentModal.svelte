<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { assignTicket, transferTicket, getAvailableAdmins, type AvailableAdmin, type AssignTicketForm, type TransferTicketForm } from '$lib/apis/tickets';
	import XMark from '$lib/components/icons/XMark.svelte';
	import UserIcon from '$lib/components/icons/User.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const dispatch = createEventDispatcher();

	export let show = false;
	export let ticket: any = null;
	export let mode: 'assign' | 'transfer' = 'assign'; // assign: 分配, transfer: 转派

	let availableAdmins: AvailableAdmin[] = [];
	let selectedAdminId = '';
	let reason = '';
	let loading = false;
	let submitting = false;
	
	// 任务要求字段
	let taskRequirements = '';
	let completionCriteria = '';
	let taskDeadline = '';
	let taskPriority = 'medium';
	
	// 交付要求字段
	let requiredFiles = '';
	let requiredText = '';
	let requiredImages = '';
	let deliveryInstructions = '';
	
	// 显示高级选项
	let showAdvanced = false;

	// 计算属性
	$: isTransfer = mode === 'transfer';
	$: title = isTransfer ? '转派工单' : '分配工单';
	$: submitText = isTransfer ? '确认转派' : '确认分配';
	$: reasonPlaceholder = isTransfer ? '请输入转派原因...' : '请输入分配原因（可选）...';

	onMount(async () => {
		if (show) {
			await loadAvailableAdmins();
		}
	});

	async function loadAvailableAdmins() {
		loading = true;
		try {
			console.log('Loading available admins for mode:', mode, 'ticket:', ticket);
			const response = await getAvailableAdmins();
			console.log('Available admins response:', response);
			availableAdmins = response.admins;
			
			// 如果是转派模式，排除当前分配的用户
			if (isTransfer && ticket?.assigned_to) {
				console.log('Filtering out current assignee:', ticket.assigned_to);
				availableAdmins = availableAdmins.filter(admin => admin.id !== ticket.assigned_to);
				console.log('Filtered admins:', availableAdmins);
			}
		} catch (error) {
			console.error('Error loading available admins:', error);
			const errorMessage = error instanceof Error ? error.message : String(error);
			toast.error(`加载用户列表失败: ${errorMessage}`);
		} finally {
			loading = false;
		}
	}

	async function handleSubmit() {
		if (!selectedAdminId.trim()) {
			toast.error('请选择要分配的用户');
			return;
		}

		if (isTransfer && !reason.trim()) {
			toast.error('转派时必须填写原因');
			return;
		}

		submitting = true;
		try {
			if (isTransfer) {
				const formData: TransferTicketForm = {
					assigned_to: selectedAdminId,
					reason: reason.trim()
				};
				await transferTicket(ticket.id, formData);
				toast.success('工单转派成功');
			} else {
				const formData: AssignTicketForm = {
					assigned_to: selectedAdminId,
					reason: reason.trim() || undefined,
					// 任务要求
					task_requirements: taskRequirements.trim() || undefined,
					completion_criteria: completionCriteria.trim() || undefined,
					task_deadline: taskDeadline ? new Date(taskDeadline).getTime() / 1000 : undefined,
					task_priority: taskPriority,
					// 交付要求
					required_files: requiredFiles.trim() || undefined,
					required_text: requiredText.trim() || undefined,
					required_images: requiredImages.trim() || undefined,
					delivery_instructions: deliveryInstructions.trim() || undefined
				};
				await assignTicket(ticket.id, formData);
				toast.success('工单分配成功');
			}
			
			resetForm();
			dispatch('success');
			handleClose();
		} catch (error) {
			console.error('Error submitting:', error);
			toast.error(isTransfer ? '转派失败' : '分配失败');
		} finally {
			submitting = false;
		}
	}

	function resetForm() {
		selectedAdminId = '';
		reason = '';
		submitting = false;
		// 重置任务要求字段
		taskRequirements = '';
		completionCriteria = '';
		taskDeadline = '';
		taskPriority = 'medium';
		// 重置交付要求字段
		requiredFiles = '';
		requiredText = '';
		requiredImages = '';
		deliveryInstructions = '';
		// 重置高级选项
		showAdvanced = false;
	}

	function handleClose() {
		resetForm();
		dispatch('close');
	}

	// 监听show变化，重新加载用户列表
	$: if (show) {
		loadAvailableAdmins();
	}
</script>

{#if show}
	<div class="fixed inset-0 z-50 flex items-center justify-center">
		<!-- Backdrop -->
		<div class="absolute inset-0 bg-black/50" on:click={handleClose} on:keydown={(e) => e.key === 'Escape' && handleClose()} role="button" tabindex="0"></div>

		<!-- Modal -->
		<div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4 max-h-[90vh] overflow-hidden flex flex-col">
			<!-- Header -->
			<div class="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white">{title}</h2>
				<button
					class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					on:click={handleClose}
				>
					<XMark className="w-6 h-6" />
				</button>
			</div>

			<!-- Form -->
			<form on:submit|preventDefault={handleSubmit} class="flex-1 overflow-y-auto p-6 space-y-6">
				<!-- Ticket Info -->
				{#if ticket}
					<div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
						<h3 class="text-sm font-medium text-gray-900 dark:text-white mb-2">工单信息</h3>
						<p class="text-sm text-gray-600 dark:text-gray-300 mb-1">
							<strong>标题:</strong> {ticket.title}
						</p>
						<p class="text-sm text-gray-600 dark:text-gray-300">
							<strong>当前分配:</strong> {ticket.assigned_to_name || '未分配'}
						</p>
					</div>
				{/if}

				<!-- Admin Selection -->
				<div>
					<label for="admin" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						{isTransfer ? '转派给' : '分配给'} *
					</label>
					{#if loading}
						<div class="flex items-center justify-center py-8">
							<Spinner />
							<span class="ml-2 text-sm text-gray-500">加载用户列表...</span>
						</div>
					{:else if availableAdmins.length === 0}
						<div class="text-center py-8 text-gray-500 dark:text-gray-400">
							<UserIcon className="w-8 h-8 mx-auto mb-2 text-gray-400" />
							<p>暂无可分配的用户</p>
						</div>
					{:else}
						<select
							id="admin"
							bind:value={selectedAdminId}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
							required
						>
							<option value="">请选择用户</option>
							{#each availableAdmins as admin}
								<option value={admin.id}>
									{admin.name} ({admin.email})
								</option>
							{/each}
						</select>
					{/if}
				</div>

				<!-- Reason -->
				<div>
					<label for="reason" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						原因 {isTransfer ? '*' : '(可选)'}
					</label>
					<textarea
						id="reason"
						bind:value={reason}
						placeholder={reasonPlaceholder}
						rows="3"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
						required={isTransfer}
					></textarea>
				</div>

				<!-- Advanced Options (only for assignment) -->
				{#if !isTransfer}
					<div class="border-t border-gray-200 dark:border-gray-700 pt-4">
						<button
							type="button"
							on:click={() => showAdvanced = !showAdvanced}
							class="flex items-center text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
						>
							<svg class="w-4 h-4 mr-1 transform transition-transform {showAdvanced ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
							</svg>
							高级选项
						</button>
						
						{#if showAdvanced}
							<div class="mt-4 max-h-96 overflow-y-auto pr-2 space-y-4">
								<!-- Task Requirements -->
								<div>
									<label for="taskRequirements" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										任务要求
									</label>
									<textarea
										id="taskRequirements"
										bind:value={taskRequirements}
										placeholder="请描述具体的任务要求..."
										rows="3"
										class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
									></textarea>
								</div>

								<!-- Completion Criteria -->
								<div>
									<label for="completionCriteria" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
										完成标准
									</label>
									<textarea
										id="completionCriteria"
										bind:value={completionCriteria}
										placeholder="请描述如何判断任务完成..."
										rows="3"
										class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
									></textarea>
								</div>

								<!-- Task Deadline and Priority -->
								<div class="grid grid-cols-2 gap-4">
									<div>
										<label for="taskDeadline" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
											截止时间
										</label>
										<input
											type="datetime-local"
											id="taskDeadline"
											bind:value={taskDeadline}
											class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
										/>
									</div>
									<div>
										<label for="taskPriority" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
											任务优先级
										</label>
										<select
											id="taskPriority"
											bind:value={taskPriority}
											class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
										>
											<option value="low">低</option>
											<option value="medium">中</option>
											<option value="high">高</option>
											<option value="urgent">紧急</option>
										</select>
									</div>
								</div>

								<!-- Delivery Requirements -->
								<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
									<h4 class="text-sm font-medium text-blue-900 dark:text-blue-300 mb-3">交付要求</h4>
									
									<div class="space-y-3">
										<div>
											<label for="requiredFiles" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
												需要提交的文件类型
											</label>
											<input
												type="text"
												id="requiredFiles"
												bind:value={requiredFiles}
												placeholder="如：PDF报告、Excel表格、Word文档..."
												class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
											/>
										</div>
										
										<div>
											<label for="requiredText" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
												需要提交的文字说明
											</label>
											<input
												type="text"
												id="requiredText"
												bind:value={requiredText}
												placeholder="如：详细分析报告、操作步骤说明..."
												class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
											/>
										</div>
										
										<div>
											<label for="requiredImages" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
												需要提交的图片要求
											</label>
											<input
												type="text"
												id="requiredImages"
												bind:value={requiredImages}
												placeholder="如：截图、流程图、照片..."
												class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
											/>
										</div>
										
										<div>
											<label for="deliveryInstructions" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
												交付说明
											</label>
											<textarea
												id="deliveryInstructions"
												bind:value={deliveryInstructions}
												placeholder="请提供具体的交付指导..."
												rows="2"
												class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
											></textarea>
										</div>
									</div>
								</div>
							</div>
						{/if}
					</div>
				{/if}

			</form>

			<!-- Actions -->
			<div class="flex justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
				<button
					type="button"
					on:click={handleClose}
					class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:bg-gray-600 dark:text-gray-300 dark:border-gray-500 dark:hover:bg-gray-500"
				>
					取消
				</button>
				<button
					type="button"
					on:click={handleSubmit}
					disabled={submitting || !selectedAdminId.trim() || (isTransfer && !reason.trim())}
					class="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{#if submitting}
						<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2 inline-block"></div>
						{submitText}中...
					{:else}
						{submitText}
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
