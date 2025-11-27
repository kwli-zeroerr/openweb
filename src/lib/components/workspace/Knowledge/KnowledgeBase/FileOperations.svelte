<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher } from 'svelte';
	import { removeFileFromKnowledgeById } from '$lib/apis/knowledge';

	const dispatch = createEventDispatcher();

	export let knowledge: any;
	export let id: string;
	export let i18n: any;

	// 获取i18n的t方法
	const t = (i18n as any)?.t || ((key: string) => key);

	// 删除文件处理
	const deleteFileHandler = async (fileId: string) => {
		try {
			console.log('Starting file deletion process for:', fileId);

			// Remove from knowledge base only
			const updatedKnowledge = await removeFileFromKnowledgeById(localStorage.token, id, fileId);

			console.log('Knowledge base updated:', updatedKnowledge);

			if (updatedKnowledge) {
				knowledge = updatedKnowledge;
				toast.success(t('File removed successfully.'));
				dispatch('knowledgeUpdated', updatedKnowledge);
			}
		} catch (e) {
			console.error('Error in deleteFileHandler:', e);
			toast.error(`${e}`);
		}
	};

	// 处理文件删除确认
	const handleFileDelete = (fileId: string) => {
		dispatch('confirmDelete', { fileId });
	};

	// 处理文件更新
	const handleFileUpdate = (fileId: string) => {
		dispatch('updateFile', { fileId });
	};

	// 导出方法供父组件使用
	export { deleteFileHandler, handleFileDelete, handleFileUpdate };
</script>

<!-- 这个组件不渲染任何UI，只提供文件操作功能 -->
<div style="display: none;"></div>
