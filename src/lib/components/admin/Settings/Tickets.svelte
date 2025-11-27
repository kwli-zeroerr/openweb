<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { models } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import Switch from '$lib/components/common/Switch.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getGroups, updateGroupById } from '$lib/apis/groups';

	const i18n = getContext('i18n');

	export let saveHandler: () => void;

	// 工单配置状态
	let ticketConfig = {
		enabled: true,
		model_id: '',
		system_prompt: ''
	};

	let availableModels: any[] = [];
	let loading = false;
	let saving = false;

	// 权限组配置
	let groups: any[] = [];
	let groupsLoading = false;
	let groupsSaving = false;

	// 响应式监听模型变化
	$: if ($models && Array.isArray($models)) {
		console.log('All models:', $models);
		// 先显示所有模型，不管是否启用
		availableModels = ($models as any[]).filter((model: any) => model.id && model.name);
		console.log('Available models (all):', availableModels);
		
		// 如果有启用的模型，优先显示启用的
		const activeModels = ($models as any[]).filter((model: any) => model.is_active);
		if (activeModels.length > 0) {
			availableModels = activeModels;
			console.log('Using active models:', availableModels);
		}
	}

	// 从数据库加载工单配置
	const loadTicketConfig = async () => {
		loading = true;
		try {
			const response = await fetch('/api/v1/tickets/config', {
				headers: {
					'Authorization': `Bearer ${localStorage.token}`
				}
			});
			
			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}
			
			const config = await response.json();
			ticketConfig = {
				enabled: config.enabled,
				model_id: config.model_id,
				system_prompt: config.system_prompt
			};
			
			console.log('Loaded ticket config:', ticketConfig);
		} catch (error) {
			console.error('Failed to load ticket config:', error);
			toast.error('加载工单配置失败');
			
			// 使用默认配置
			ticketConfig = {
				enabled: true,
				model_id: 'gpt-3.5-turbo',
				system_prompt: `你是一个专业的AI工单分析专家，专门处理用户对AI回复的负面反馈。你的任务是深度分析用户反馈，生成高质量的结构化工单。

## 🎯 核心任务
根据用户的负面反馈和完整对话上下文，智能生成专业的工单，帮助技术团队快速定位和解决问题。

## 📋 分析流程

### 第一步：问题识别
- 仔细分析用户的具体问题描述
- 理解用户期望与实际结果的差距
- 识别AI回复中的错误或不足
- 评估问题对用户体验的影响

### 第二步：上下文理解
- 分析完整对话流程
- 理解用户的使用场景和需求
- 识别AI回复的技术问题
- 评估问题的可重现性

### 第三步：影响评估
- 判断问题的严重程度
- 评估对业务的影响范围
- 确定紧急程度和处理优先级
- 识别潜在的系统性问题

## 🏷️ 工单生成标准

### 标题规范（≤30字）
- 使用动词开头，如"修复"、"优化"、"调整"
- 突出核心问题，避免模糊表述
- 包含关键的技术术语
- 示例：修复AI回复中的代码格式错误

### 描述结构
1. **问题概述**：简洁描述用户遇到的问题
2. **技术分析**：分析AI回复中的具体错误
3. **影响评估**：说明问题对用户的影响
4. **解决建议**：提供初步的修复方向
5. **相关技术**：涉及的技术栈和模块

### 优先级判断标准
- **urgent**: 系统崩溃、数据泄露、安全漏洞、核心功能完全失效
- **high**: 主要功能异常、严重影响用户体验、数据错误
- **medium**: 功能部分异常、性能问题、用户体验不佳
- **low**: 优化建议、小bug、非关键功能问题

### 分类选择指南
- **bug**: AI回复错误、功能异常、技术故障、逻辑错误
- **feature_request**: 新功能需求、功能增强、用户体验改进
- **general_inquiry**: 使用咨询、操作指导、配置问题
- **technical_support**: 技术问题、集成问题、性能优化
- **other**: 其他类型问题

### 标签策略
- **技术标签**：涉及的技术栈（如python、javascript、api等）
- **模块标签**：相关功能模块（如chat、auth、database等）
- **严重程度**：critical、major、minor、enhancement
- **问题类型**：accuracy、performance、usability、security

## 📤 输出格式要求

请严格按照以下JSON格式返回，确保字段完整：

{
    "title": "具体的问题标题",
    "description": "详细的问题分析、技术原因、影响评估和解决建议",
    "priority": "urgent|high|medium|low",
    "category": "bug|feature_request|general_inquiry|technical_support|other",
    "tags": ["技术标签", "模块标签", "严重程度", "问题类型"]
}

## ⚠️ 质量要求
- 分析必须客观准确，基于事实
- 提供具体可执行的解决建议
- 避免重复用户已表达的内容
- 保持专业、清晰、友好的语调
- 确保JSON格式正确，字段完整`
			};
		} finally {
			loading = false;
		}
	};

	// 加载可用模型列表
	const loadModels = async () => {
		try {
			console.log('Loading models, current models:', $models);
			// 从stores中获取模型列表
			if ($models && Array.isArray($models)) {
				console.log('All models:', $models);
				// 先显示所有模型，不管是否启用
				availableModels = ($models as any[]).filter((model: any) => model.id && model.name);
				console.log('Available models (all):', availableModels);
				
				// 如果有启用的模型，优先显示启用的
				const activeModels = ($models as any[]).filter((model: any) => model.is_active);
				if (activeModels.length > 0) {
					availableModels = activeModels;
					console.log('Using active models:', availableModels);
				}
			} else {
				console.log('Models not loaded yet, retrying...');
				// 如果模型还没加载，等待一下再试
				setTimeout(() => {
					if ($models && Array.isArray($models)) {
						availableModels = ($models as any[]).filter((model: any) => model.id && model.name);
						console.log('Available models after retry:', availableModels);
					}
				}, 1000);
			}
		} catch (error) {
			console.error('Failed to load models:', error);
		}
	};

	// 保存工单配置
	const saveTicketConfig = async () => {
		saving = true;
		try {
			const response = await fetch('/api/v1/tickets/config', {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					'Authorization': `Bearer ${localStorage.token}`
				},
				body: JSON.stringify(ticketConfig)
			});
			
			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}
			
			const result = await response.json();
			console.log('Save result:', result);
			
			toast.success('工单配置保存成功');
			saveHandler();
		} catch (error) {
			console.error('Failed to save ticket config:', error);
			toast.error('保存工单配置失败');
		} finally {
			saving = false;
		}
	};

	// 加载权限组列表
	const loadGroups = async () => {
		groupsLoading = true;
		try {
			const token = localStorage.token || '';
			console.log('Loading groups with token:', token ? 'present' : 'missing');
			console.log('API URL:', '/api/v1/groups/');
			
			const response = await getGroups(token);
			console.log('Raw API response:', response);
			console.log('Response type:', typeof response);
			console.log('Is array:', Array.isArray(response));
			
			// 后端直接返回数组，不是包装在对象中
			groups = Array.isArray(response) ? response : (response?.groups || []);
			console.log('Processed groups:', groups);
			console.log('Groups count:', groups.length);
		} catch (error) {
			console.error('Failed to load groups:', error);
			console.error('Error details:', error);
			toast.error('加载权限组失败: ' + (error.message || error));
		} finally {
			groupsLoading = false;
		}
	};

	// 更新权限组的工单权限
	const updateGroupTicketPermission = async (groupId: string, permission: boolean) => {
		try {
			const group = groups.find(g => g.id === groupId);
			if (!group) return;

			const token = localStorage.token || '';

			// 更新权限配置
			const updatedPermissions = {
				...group.permissions,
				features: {
					...group.permissions?.features,
					tickets: permission
				}
			};

			await updateGroupById(token, groupId, {
				name: group.name,
				description: group.description,
				permissions: updatedPermissions
			});

			// 更新本地状态
			group.permissions = updatedPermissions;
			groups = [...groups];

			toast.success(`权限组 "${group.name}" 工单权限已${permission ? '开启' : '关闭'}`);
		} catch (error) {
			console.error('Failed to update group permission:', error);
			toast.error('更新权限组失败');
		}
	};

	onMount(() => {
		loadTicketConfig();
		loadModels();
		loadGroups();
	});
</script>

<div class="flex flex-col space-y-6">
	<div class="flex items-center justify-between">
		<div>
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white">问题工单设置</h2>
			<p class="text-sm text-gray-600 dark:text-gray-400">
				配置AI自动生成工单的模型和提示词
			</p>
		</div>
	</div>

	{#if loading}
		<div class="flex items-center justify-center py-8">
			<Spinner />
		</div>
	{:else}
		<div class="space-y-6">
			<!-- 启用/禁用工单生成 -->
			<div class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
				<div>
					<h3 class="text-sm font-medium text-gray-900 dark:text-white">启用AI工单生成</h3>
					<p class="text-sm text-gray-600 dark:text-gray-400">
						当用户对AI回复点踩并评论时，自动生成工单
					</p>
				</div>
				<Switch bind:state={ticketConfig.enabled} />
			</div>

			<!-- 选择模型 -->
			<div class="space-y-2">
				<label for="model-select" class="text-sm font-medium text-gray-900 dark:text-white">
					使用的AI模型
				</label>
				<select
					id="model-select"
					bind:value={ticketConfig.model_id}
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
					disabled={!ticketConfig.enabled}
				>
					{#each availableModels as model}
						<option value={model.id}>{model.name}</option>
					{/each}
				</select>
				<p class="text-xs text-gray-500 dark:text-gray-400">
					选择用于分析用户反馈并生成工单的AI模型
				</p>
			</div>

			<!-- 系统提示词 -->
			<div class="space-y-2">
				<label for="system-prompt" class="text-sm font-medium text-gray-900 dark:text-white">
					系统提示词
				</label>
				<textarea
					id="system-prompt"
					bind:value={ticketConfig.system_prompt}
					rows="8"
					class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
					placeholder="输入系统提示词，指导AI如何分析用户反馈并生成工单..."
					disabled={!ticketConfig.enabled}
				></textarea>
				<p class="text-xs text-gray-500 dark:text-gray-400">
					定义AI分析用户反馈时的行为准则和输出格式
				</p>
			</div>

			<!-- 保存按钮 -->
			<div class="flex justify-end">
				<button
					on:click={saveTicketConfig}
					disabled={saving}
					class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
				>
					{#if saving}
						<Spinner />
					{/if}
					<span>{saving ? '保存中...' : '保存配置'}</span>
				</button>
			</div>
		</div>
	{/if}

	<!-- 权限组工单权限配置 -->
	<div class="border-t border-gray-200 dark:border-gray-700 pt-6">
		<div class="flex items-center justify-between mb-4">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white">权限组工单权限</h3>
				<p class="text-sm text-gray-600 dark:text-gray-400">
					配置哪些权限组可以提交工单、处理工单或被分配工单
				</p>
			</div>
		</div>

		{#if groupsLoading}
			<div class="flex items-center justify-center py-8">
				<Spinner />
			</div>
		{:else}
			<div class="space-y-4">
				{#each groups as group}
					<div class="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
						<div class="flex-1">
							<div class="flex items-center space-x-3">
								<h4 class="text-sm font-medium text-gray-900 dark:text-white">
									{group.name}
								</h4>
								<span class="text-xs text-gray-500 dark:text-gray-400">
									{group.user_ids?.length || 0} 名成员
								</span>
							</div>
							{#if group.description}
								<p class="text-xs text-gray-600 dark:text-gray-400 mt-1">
									{group.description}
								</p>
							{/if}
						</div>
						<div class="flex items-center space-x-4">
							<div class="text-right">
								<div class="text-xs text-gray-500 dark:text-gray-400">工单权限</div>
								<div class="text-xs text-gray-600 dark:text-gray-300">
									{group.permissions?.features?.tickets ? '✅ 已开启' : '❌ 未开启'}
								</div>
							</div>
							<Switch 
								state={group.permissions?.features?.tickets || false}
								on:change={(e) => updateGroupTicketPermission(group.id, e.detail)}
							/>
						</div>
					</div>
				{/each}

				{#if groups.length === 0}
					<div class="text-center py-8 text-gray-500 dark:text-gray-400">
						<div class="text-sm">暂无权限组</div>
						<div class="text-xs mt-1">请先在用户管理中添加权限组</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>
