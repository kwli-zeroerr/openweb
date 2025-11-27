<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getTicket, updateTicket, addComment, deliverTask, verifyTaskCompletion, type Ticket, type TicketComment, type UpdateTicketForm, type AddCommentForm, type TaskDeliveryForm, type TaskVerificationForm } from '$lib/apis/tickets';
import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { getStatusInfo, getPriorityInfo, getCategoryInfo } from '$lib/constants/tickets';
	import { user } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import { getFeedbackById } from '$lib/apis/evaluations';
	import ArrowLeft from '$lib/components/icons/ArrowLeft.svelte';
	import ExclamationTriangle from '$lib/components/icons/ExclamationTriangle.svelte';
	import InformationCircle from '$lib/components/icons/InformationCircle.svelte';
	import CheckCircle from '$lib/components/icons/CheckCircle.svelte';
	import BugAnt from '$lib/components/icons/BugAnt.svelte';
	import LightBulb from '$lib/components/icons/LightBulb.svelte';
	import ChatBubbleLeftRight from '$lib/components/icons/ChatBubbleLeftRight.svelte';
	import WrenchScrewdriver from '$lib/components/icons/WrenchScrewdriver.svelte';
	import Tag from '$lib/components/icons/Tag.svelte';
	import PaperAirplane from '$lib/components/icons/PaperAirplane.svelte';
	import AITicketDetails from '$lib/components/tickets/AITicketDetails.svelte';
	import TicketAssignmentModal from '$lib/components/tickets/TicketAssignmentModal.svelte';
	import UserPlus from '$lib/components/icons/UserPlus.svelte';
	import ArrowRightLeft from '$lib/components/icons/ArrowRightLeft.svelte';
	import StatusChip from '$lib/components/tickets/chips/StatusChip.svelte';
	import PriorityChip from '$lib/components/tickets/chips/PriorityChip.svelte';
	import CategoryChip from '$lib/components/tickets/chips/CategoryChip.svelte';
	import StickyActionBar from '$lib/components/tickets/StickyActionBar.svelte';
	import ChatCollapse from '$lib/components/tickets/ChatCollapse.svelte';
	import CommentsTimeline from '$lib/components/tickets/CommentsTimeline.svelte';

	let ticket: Ticket | null = null;
	let loading = true;
	let updating = false;
	let newComment = '';
	let addingComment = false;
	let feedbackData: any = null;
	let chatData: any = null;
	let aiAnalysis: any = null;
	let showAssignmentModal = false;
	let assignmentMode: 'assign' | 'transfer' = 'assign';
	let showDeliveryModal = false;
	let showVerificationModal = false;
	
	// UI state variables
	let showChatContext = false;
	let showStickyBar = false;
	
	// Task delivery form variables
	let deliveryText = '';
	let completionNotes = '';
	let deliverySubmitting = false;
	
	// File upload variables
	let deliveryFiles: File[] = [];
	let deliveryImages: File[] = [];
	let fileInputRef: HTMLInputElement;
	let imageInputRef: HTMLInputElement;
	let uploadingFiles = false;
	
	// Task verification form variables
	let verificationResult = '';
	let verificationNotes = '';
	let verificationSubmitting = false;
	
	// Verification checklist
	let verificationChecklist = [
		{ id: 'quality', label: '交付质量符合要求', checked: false },
		{ id: 'completeness', label: '任务完成度达标', checked: false },
		{ id: 'timeliness', label: '按时完成交付', checked: false },
		{ id: 'documentation', label: '文档说明完整', checked: false },
		{ id: 'testing', label: '功能测试通过', checked: false }
	];
	
	// Verification score
	let verificationScore = 0;

	// 使用统一的状态选项
	const statusOptions = [
		{ value: 'open', label: '待处理' },
		{ value: 'in_progress', label: '处理中' },
		{ value: 'completed', label: '已完成' },
		{ value: 'resolved', label: '已解决' },
		{ value: 'closed', label: '已关闭' }
	];

	const priorityOptions = [
		{ value: 'low', label: '低', color: 'text-blue-500' },
		{ value: 'medium', label: '中', color: 'text-yellow-500' },
		{ value: 'high', label: '高', color: 'text-orange-500' },
		{ value: 'urgent', label: '紧急', color: 'text-red-500' }
	];

	const categoryOptions = [
		{ value: 'bug', label: 'Bug 报告', icon: BugAnt, color: 'text-red-500' },
		{ value: 'feature_request', label: '功能请求', icon: LightBulb, color: 'text-blue-500' },
		{ value: 'general_inquiry', label: '一般咨询', icon: ChatBubbleLeftRight, color: 'text-green-500' },
		{ value: 'technical_support', label: '技术支持', icon: WrenchScrewdriver, color: 'text-purple-500' },
		{ value: 'other', label: '其他', icon: Tag, color: 'text-gray-500' }
	];

	// Validate ticket ID format
	function isValidTicketId(ticketId: string): boolean {
		// Check if ticket ID is not empty and follows expected format
		// Support both UUID format and custom AI ticket format (ai-timestamp-uuid)
		const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
		const aiTicketRegex = /^ai-\d+-[0-9a-f]{8}$/i;
		
		if (!ticketId || ticketId.trim().length === 0) {
			return false;
		}
		
		// Accept both UUID format and AI ticket format
		return uuidRegex.test(ticketId) || aiTicketRegex.test(ticketId);
	}

	async function loadTicket() {
		loading = true;
		try {
			const ticketId = $page.params.id;
			console.log('Loading ticket with ID:', ticketId);
			console.log('Current page params:', $page.params);
			console.log('API base URL:', WEBUI_API_BASE_URL);
			console.log('Ticket ID validation result:', isValidTicketId(ticketId));
			
			// Validate ticket ID before making API call
			if (!isValidTicketId(ticketId)) {
				throw new Error(`Invalid ticket ID format: ${ticketId}`);
			}
			
			ticket = await getTicket(ticketId);
			
			// 加载AI分析数据（AI工单和人工工单都需要）
			await loadFeedbackData();
			
			// 如果是人工工单且没有AI分析，等待一下再重新加载
			if (ticket && !ticket.is_ai_generated && !ticket.ai_analysis) {
				console.log('Manual ticket without AI analysis, waiting and retrying...');
				setTimeout(async () => {
					try {
						ticket = await getTicket(ticketId);
						await loadFeedbackData();
					} catch (error) {
						console.error('Error retrying ticket load:', error);
					}
				}, 2000); // 等待2秒后重试
			}
		} catch (error) {
			console.error('Error loading ticket:', error);
			const errorMessage = error instanceof Error ? error.message : String(error);
			const errorStack = error instanceof Error ? error.stack : undefined;
			
			console.error('Error details:', {
				message: errorMessage,
				stack: errorStack,
				ticketId: $page.params.id
			});
			
			// Show more specific error message
			if (errorMessage.includes('404') || errorMessage.includes('not found')) {
				toast.error(`工单不存在 (ID: ${$page.params.id})`);
				// Don't redirect immediately, let user see the error
				setTimeout(() => {
					goto('/workspace/tickets');
				}, 3000);
			} else if (errorMessage.includes('403') || errorMessage.includes('Access denied')) {
				toast.error('您没有权限访问此工单。请联系管理员申请权限，或在工单下留言说明访问需求。');
				setTimeout(() => {
					goto('/workspace/tickets');
				}, 3000);
			} else if (errorMessage.includes('Invalid ticket ID format')) {
				toast.error(`工单ID格式无效: ${$page.params.id}。支持的格式: UUID 或 ai-时间戳-标识符`);
				setTimeout(() => {
					goto('/workspace/tickets');
				}, 3000);
			} else {
				toast.error(`加载工单失败: ${errorMessage}`);
				setTimeout(() => {
					goto('/workspace/tickets');
				}, 3000);
			}
		} finally {
			loading = false;
		}
	}

	async function loadFeedbackData() {
		if (!ticket) return;
		
		try {
			// 尝试从ai_analysis获取数据
			if (ticket.ai_analysis) {
				aiAnalysis = typeof ticket.ai_analysis === 'string' 
					? JSON.parse(ticket.ai_analysis) 
					: ticket.ai_analysis;
				
				console.log('AI Analysis structure:', aiAnalysis);
				console.log('AI Analysis keys:', Object.keys(aiAnalysis));
				console.log('Has analysis field:', !!aiAnalysis.analysis);
				console.log('Has description field:', !!aiAnalysis.description);
				
				// 对于人工工单，直接使用AI分析数据
				if (!ticket.is_ai_generated) {
					console.log('Manual ticket - using AI analysis directly');
					console.log('Manual ticket AI analysis:', aiAnalysis);
					// 人工工单不需要复杂的反馈数据解析，aiAnalysis已经设置好了
					return;
				}
				
				// 检查description字段是否包含反馈数据JSON字符串（仅对AI工单）
				if (aiAnalysis.description && typeof aiAnalysis.description === 'string') {
					try {
						// 从description字符串中提取反馈数据
						const descriptionMatch = aiAnalysis.description.match(/反馈数据：(.+)$/m);
						if (descriptionMatch && descriptionMatch[1]) {
							const feedbackJsonStr = descriptionMatch[1].trim();
							console.log('Extracted feedback JSON string:', feedbackJsonStr);
							
							// 解析反馈数据JSON
							const parsedFeedback = JSON.parse(feedbackJsonStr);
							feedbackData = parsedFeedback;
							console.log('Parsed feedback data:', feedbackData);
						}
					} catch (e) {
						console.error('Error parsing feedback from description:', e);
					}
				}
				
				// 如果还没有获取到反馈数据，尝试其他方式
				if (!feedbackData) {
					if (aiAnalysis.feedback_data) {
						feedbackData = aiAnalysis.feedback_data;
					} else {
						feedbackData = aiAnalysis;
					}
				}
			}
			
			// 如果没有从ai_analysis获取到数据，尝试从source_feedback_id获取完整反馈数据
			if (!feedbackData && ticket.source_feedback_id) {
				const token = localStorage.getItem('token') || '';
				const fullFeedback = await getFeedbackById(token, ticket.source_feedback_id);
				feedbackData = fullFeedback;
			}
			
			console.log('Final feedbackData:', feedbackData);
			
			// 提取对话内容
			if (feedbackData) {
				// 方式1: 从snapshot.chat.messages数组获取
				if (feedbackData.snapshot && feedbackData.snapshot.chat && feedbackData.snapshot.chat.messages) {
					chatData = {
						title: feedbackData.snapshot.chat.title,
						messages: feedbackData.snapshot.chat.messages
					};
					console.log('Extracted chatData from snapshot.messages array:', chatData);
				}
				// 方式2: 从snapshot.chat.chat.history.messages对象获取
				else if (feedbackData.snapshot && feedbackData.snapshot.chat && feedbackData.snapshot.chat.chat && feedbackData.snapshot.chat.chat.history && feedbackData.snapshot.chat.chat.history.messages) {
					const messagesObj = feedbackData.snapshot.chat.chat.history.messages;
					// 将对象转换为数组
					const messagesArray = Object.values(messagesObj);
					chatData = {
						title: feedbackData.snapshot.chat.title,
						messages: messagesArray
					};
					console.log('Extracted chatData from snapshot.chat.history.messages object:', chatData);
				}
				// 方式3: 从ai_analysis的full_chat_data获取
				else if (ticket.ai_analysis) {
					const aiAnalysis = typeof ticket.ai_analysis === 'string' 
						? JSON.parse(ticket.ai_analysis) 
						: ticket.ai_analysis;
					
					if (aiAnalysis.full_chat_data && aiAnalysis.full_chat_data.messages) {
						chatData = {
							title: aiAnalysis.full_chat_data.title,
							messages: aiAnalysis.full_chat_data.messages
						};
						console.log('Extracted chatData from full_chat_data:', chatData);
					}
				}
			}
		} catch (error) {
			console.error('Error loading feedback data:', error);
		}
	}

	function formatDate(timestamp: number) {
		return new Date(timestamp * 1000).toLocaleDateString('zh-CN', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}


	async function handleStatusChange(newStatus: string) {
		if (!ticket) return;

		updating = true;
		try {
			const updates: UpdateTicketForm = { status: newStatus as any };
			ticket = await updateTicket(ticket.id, updates);
			toast.success('状态已更新');
		} catch (error) {
			console.error('Error updating ticket:', error);
			toast.error('更新失败');
		} finally {
			updating = false;
		}
	}

	async function handleAddComment(content: string) {
		if (!content.trim() || !ticket) return;

		addingComment = true;
		try {
			const formData: AddCommentForm = {
				content: content.trim(),
				is_internal: false
			};
			await addComment(ticket.id, formData);
			toast.success('评论已添加');
			await loadTicket(); // Reload to get updated comments
		} catch (error) {
			console.error('Error adding comment:', error);
			toast.error('添加评论失败');
		} finally {
			addingComment = false;
		}
	}

	// Separate handler to avoid TS assertions inside template expressions
	function onStatusChange(event: Event) {
		const select = event.target as HTMLSelectElement;
		handleStatusChange(select?.value ?? '');
	}

	function handleAssignTicket() {
		assignmentMode = 'assign';
		showAssignmentModal = true;
	}

	function handleTransferTicket() {
		console.log('Transfer ticket clicked', { ticket, user: $user });
		assignmentMode = 'transfer';
		showAssignmentModal = true;
	}

	function handleAssignmentSuccess() {
		// 重新加载工单数据
		loadTicket();
	}

	function handleAssignmentClose() {
		showAssignmentModal = false;
	}

	// Task Delivery Functions
	function handleDeliverySuccess() {
		// 重新加载工单数据
		loadTicket();
		showDeliveryModal = false;
	}

	function handleDeliveryClose() {
		showDeliveryModal = false;
	}

	// Task Verification Functions
	function handleVerificationSuccess() {
		// 重新加载工单数据
		loadTicket();
		showVerificationModal = false;
	}

	function handleVerificationClose() {
		showVerificationModal = false;
	}

	// File upload functions
	function handleFileSelect(event: Event) {
		const target = event.target as HTMLInputElement;
		if (target.files) {
			const newFiles = Array.from(target.files);
			deliveryFiles = [...deliveryFiles, ...newFiles];
		}
	}

	function handleImageSelect(event: Event) {
		const target = event.target as HTMLInputElement;
		if (target.files) {
			const newImages = Array.from(target.files);
			deliveryImages = [...deliveryImages, ...newImages];
		}
	}

	function removeFile(index: number) {
		deliveryFiles = deliveryFiles.filter((_, i) => i !== index);
	}

	function removeImage(index: number) {
		deliveryImages = deliveryImages.filter((_, i) => i !== index);
	}

	function formatFileSize(bytes: number): string {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
	}

	// 预览/下载交付文件：优先使用后端文件API通过授权请求打开
	async function previewOrDownloadFile(file: any) {
		try {
			const token = localStorage.getItem('token');
			if (file?.url) {
				window.open(file.url, '_blank');
				return;
			}
			if (!file?.id) return;
			const endpoint = `${WEBUI_API_BASE_URL}/files/${file.id}/content`;
			const response = await fetch(endpoint, {
				method: 'GET',
				headers: {
					...(token && { authorization: `Bearer ${token}` })
				}
			});
			if (!response.ok) throw new Error('下载失败');
			const blob = await response.blob();
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.target = '_blank';
			a.download = file.name || 'download';
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		} catch (e) {
			toast.error('无法预览/下载该文件');
		}
	}

	function resetDeliveryForm() {
		deliveryText = '';
		completionNotes = '';
		deliveryFiles = [];
		deliveryImages = [];
	}

	// Verification functions
	function updateChecklist(index: number) {
		verificationChecklist = verificationChecklist.map((item, i) => 
			i === index ? { ...item, checked: !item.checked } : item
		);
		updateVerificationScore();
	}

	function updateVerificationScore() {
		const checkedCount = verificationChecklist.filter(item => item.checked).length;
		verificationScore = Math.round((checkedCount / verificationChecklist.length) * 100);
	}

	function resetVerificationForm() {
		verificationResult = '';
		verificationNotes = '';
		verificationChecklist = verificationChecklist.map(item => ({ ...item, checked: false }));
		verificationScore = 0;
	}

	// Task Delivery Submit Handler
	async function handleDeliverySubmit() {
		if (!ticket) return;
		
		deliverySubmitting = true;
		uploadingFiles = true;
		
		try {
			// 使用FormData提交文件
			const formData = new FormData();
			
			// 添加文本字段
			if (deliveryText.trim()) {
				formData.append('delivery_text', deliveryText.trim());
			}
			if (completionNotes.trim()) {
				formData.append('completion_notes', completionNotes.trim());
			}
			
			// 添加文件
			deliveryFiles.forEach(file => {
				formData.append('files', file);
			});
			
			// 添加图片
			deliveryImages.forEach(image => {
				formData.append('images', image);
			});
			
			await deliverTask(ticket.id, formData);
			toast.success('任务交付提交成功');
			
			// 重置表单
			resetDeliveryForm();
			
			handleDeliverySuccess();
		} catch (error) {
			console.error('Error delivering task:', error);
			toast.error('任务交付提交失败');
		} finally {
			deliverySubmitting = false;
			uploadingFiles = false;
		}
	}

	// Task Verification Submit Handler
	async function handleVerificationSubmit() {
		if (!ticket) return;
		
		verificationSubmitting = true;
		try {
			// 准备检查清单数据
			const checklistData = verificationChecklist.map(item => ({
				id: item.id,
				label: item.label,
				checked: item.checked
			}));
			
			const formData: TaskVerificationForm = {
				verified: verificationResult === 'pass',
				verification_notes: verificationNotes.trim() || undefined,
				verification_score: verificationScore,
				verification_checklist: checklistData
			};
			
			await verifyTaskCompletion(ticket.id, formData);
			toast.success(`任务验证${verificationResult === 'pass' ? '通过' : '拒绝'}成功`);
			
			// 重置表单
			resetVerificationForm();
			
			handleVerificationSuccess();
		} catch (error) {
			console.error('Error verifying task:', error);
			toast.error('任务验证失败');
		} finally {
			verificationSubmitting = false;
		}
	}

	// 滚动监听
	function handleScroll() {
		showStickyBar = window.scrollY > 200;
	}

	onMount(() => {
		// 添加滚动监听
		window.addEventListener('scroll', handleScroll);
		
		// 异步加载工单
		loadTicketData();
		
		return () => {
			window.removeEventListener('scroll', handleScroll);
		};
	});

	async function loadTicketData() {
		// Check if user has tickets permission or is assigned to this ticket
		const hasTicketsPermission = $user?.role === 'admin' || 
			($user?.permissions?.workspace?.tickets ?? false) ||
			($user?.permissions?.workspace?.tickets_view_all ?? false);
		
		if (!hasTicketsPermission) {
			// 先加载工单，检查用户是否被分配到这个工单
			await loadTicket();
			
			// 如果用户不是工单创建者且不是被分配者，则拒绝访问
			if (ticket && ticket.user_id !== $user?.id && ticket.assigned_to !== $user?.id) {
				toast.error('您没有权限访问此工单');
				goto('/');
				return;
			}
		} else {
			await loadTicket();
		}
		
		// 调试：检查交付数据
		if (ticket) {
			console.log('Ticket delivery data:', {
				delivery_files: ticket.delivery_files,
				delivery_images: ticket.delivery_images,
				delivery_text: ticket.delivery_text,
				completion_notes: ticket.completion_notes,
				delivery_files_type: typeof ticket.delivery_files,
				delivery_files_isArray: Array.isArray(ticket.delivery_files),
				delivery_files_length: ticket.delivery_files?.length
			});
			
			// 如果delivery_files是字符串，尝试解析为JSON
			if (typeof ticket.delivery_files === 'string') {
				try {
					ticket.delivery_files = JSON.parse(ticket.delivery_files);
					console.log('Parsed delivery_files:', ticket.delivery_files);
				} catch (e) {
					console.error('Failed to parse delivery_files:', e);
				}
			}
			
			// 如果delivery_images是字符串，尝试解析为JSON
			if (typeof ticket.delivery_images === 'string') {
				try {
					ticket.delivery_images = JSON.parse(ticket.delivery_images);
					console.log('Parsed delivery_images:', ticket.delivery_images);
				} catch (e) {
					console.error('Failed to parse delivery_images:', e);
				}
			}
			
			// 调试显示条件
			const showDelivery = ticket.delivery_text || 
				(ticket.delivery_files && Array.isArray(ticket.delivery_files) && ticket.delivery_files.length > 0) || 
				(ticket.delivery_images && Array.isArray(ticket.delivery_images) && ticket.delivery_images.length > 0) || 
				ticket.completion_notes;
			
			console.log('Show delivery condition:', {
				delivery_text: !!ticket.delivery_text,
				delivery_files_condition: !!(ticket.delivery_files && Array.isArray(ticket.delivery_files) && ticket.delivery_files.length > 0),
				delivery_images_condition: !!(ticket.delivery_images && Array.isArray(ticket.delivery_images) && ticket.delivery_images.length > 0),
				completion_notes: !!ticket.completion_notes,
				final_result: showDelivery
			});
		}
	}
</script>

<svelte:head>
	<title>工单详情 • Open WebUI</title>
</svelte:head>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
		<div class="flex items-center gap-4">
			<button
				on:click={() => goto('/workspace/tickets')}
				class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
			>
				<ArrowLeft className="w-5 h-5" />
			</button>
			<div>
				<h1 class="text-2xl font-bold text-gray-900 dark:text-white">工单详情</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					查看和管理工单信息
				</p>
			</div>
		</div>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-y-auto">
		{#if loading}
			<div class="flex items-center justify-center h-64">
				<Spinner />
			</div>
		{:else if ticket}
		<div class="max-w-7xl mx-auto p-6">
			<!-- 吸附式动作条 -->
			<StickyActionBar isVisible={showStickyBar} />
			
			<!-- 工单头部信息卡片 - 简化设计 -->
			<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 mb-8 overflow-hidden">
				<!-- 标题和操作区域 -->
				<div class="px-8 py-6 border-b border-gray-200 dark:border-gray-600">
					<div class="flex items-start justify-between">
						<!-- 左侧：标题和标签 -->
						<div class="flex-1">
							<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-4 leading-tight">
								{ticket.title}
							</h1>
							<div class="flex items-center gap-3 flex-wrap">
								<StatusChip status={ticket.status} size="md" />
								<PriorityChip priority={ticket.priority} size="md" />
								<CategoryChip category={ticket.category} size="md" />
								{#if ticket.is_ai_generated}
									<span class="inline-flex items-center px-3 py-1 rounded-lg text-sm font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-700">
										<svg class="w-4 h-4 mr-1.5" fill="currentColor" viewBox="0 0 20 20">
											<path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
										</svg>
										AI生成
									</span>
								{/if}
							</div>
						</div>
						
						<!-- 右侧：用户反馈 -->
						{#if feedbackData}
							<div class="ml-8">
								<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 max-w-sm">
									<div class="flex items-center gap-3 mb-2">
										<div class="w-6 h-6 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
											<svg class="w-3 h-3 text-red-600 dark:text-red-400" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
											</svg>
										</div>
										<h4 class="text-sm font-semibold text-red-800 dark:text-red-200">用户反馈</h4>
									</div>
									<div class="text-gray-800 dark:text-gray-200 text-sm">
										{#if feedbackData.comment && feedbackData.comment.trim()}
											"{feedbackData.comment}"
										{:else if feedbackData.reason && feedbackData.reason.trim()}
											"{feedbackData.reason}"
										{:else if feedbackData.data && feedbackData.data.comment && feedbackData.data.comment.trim()}
											"{feedbackData.data.comment}"
										{:else if feedbackData.data && feedbackData.data.reason && feedbackData.data.reason.trim()}
											"{feedbackData.data.reason}"
										{:else}
											<span class="text-gray-600 dark:text-gray-400">默认点踩反馈</span>
										{/if}
									</div>
								</div>
							</div>
						{/if}
					</div>
				</div>
				
				<!-- 操作和信息区域 -->
				<div class="px-8 py-6">
					<div class="flex items-center justify-between">
						<!-- 左侧：状态和创建信息 -->
						<div class="flex items-center gap-6">
							<!-- 状态管理 -->
							<div class="flex items-center gap-2">
								<span class="text-sm font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">状态:</span>
								{#if $user?.role === 'admin'}
									<select 
										bind:value={ticket.status} 
										on:change={onStatusChange}
										class="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent min-w-[100px]"
									>
										{#each statusOptions as option}
											<option value={option.value}>{option.label}</option>
										{/each}
									</select>
								{:else}
									<StatusChip status={ticket.status} size="sm" />
								{/if}
							</div>
							
							<!-- 创建信息 -->
							<div class="flex items-center gap-2">
								<span class="text-sm font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">创建者:</span>
								<span class="text-sm text-gray-900 dark:text-white">{ticket.user_name}</span>
								<span class="text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
									{new Date(ticket.created_at).toLocaleString('zh-CN', {
										year: 'numeric',
										month: '2-digit',
										day: '2-digit',
										hour: '2-digit',
										minute: '2-digit',
										second: '2-digit'
									})}
								</span>
							</div>
						</div>
						
						<!-- 右侧：分配信息和操作按钮 -->
						<div class="flex items-center gap-6">
							<!-- 分配信息 -->
							<div class="flex items-center gap-2">
								<span class="text-sm font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">分配给:</span>
								<span class="text-sm text-gray-900 dark:text-white">
									{ticket.assigned_to_name || '未分配'}
								</span>
								{#if $user?.role === 'admin'}
									<button 
										on:click={handleAssignTicket}
										class="inline-flex items-center px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors duration-200 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 whitespace-nowrap"
									>
										<UserPlus className="w-4 h-4 mr-1.5" />
										{ticket.assigned_to ? '重新分配' : '分配工单'}
									</button>
								{/if}
							</div>
							
							<!-- 主要操作按钮 -->
							<div class="flex items-center gap-3">
								{#if $user?.role === 'admin'}
									<!-- 验收按钮 -->
									{#if ticket.completion_status === 'submitted'}
										<button 
											on:click={() => showVerificationModal = true}
											class="inline-flex items-center px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors duration-200 focus:ring-2 focus:ring-green-500 focus:ring-offset-2"
										>
											<svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
											</svg>
											验收任务
										</button>
									{/if}
								{:else if ticket.assigned_to === $user?.id}
									<!-- 处理者操作 -->
									{#if ticket.completion_status !== 'verified'}
										<button 
											on:click={() => showDeliveryModal = true}
											class="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors duration-200 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
										>
											<ArrowRightLeft className="w-4 h-4 mr-2" />
											{ticket.completion_status === 'submitted' ? '重新提交交付' : '提交交付'}
										</button>
									{/if}
								{/if}
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- 主要内容区域 -->
			<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<!-- 左侧：问题描述和任务要求 -->
				<div class="lg:col-span-2 space-y-6">
					<!-- 问题描述 - 重新设计 -->
					<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden h-[600px] flex flex-col">
						<!-- 标题栏 -->
						<div class="bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-600 px-6 py-4 border-b border-gray-200 dark:border-gray-600 flex-shrink-0">
							<div class="flex items-center gap-3">
								<div class="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
									<svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
										<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
									</svg>
								</div>
								<h3 class="text-xl font-bold text-gray-900 dark:text-white">问题描述</h3>
							</div>
						</div>
						
						<!-- 内容区域 - 可滚动 -->
						<div class="flex-1 overflow-y-auto">
							<div class="p-6">
								<div class="prose prose-gray dark:prose-invert max-w-none">
									{#if ticket.is_ai_generated && aiAnalysis && aiAnalysis.description}
										<!-- AI工单：显示AI分析的用户视角描述 -->
										<div class="text-gray-700 dark:text-gray-300 leading-relaxed text-base whitespace-pre-wrap">
											{aiAnalysis.description}
										</div>
									{:else}
										<!-- 人工工单：显示工单原始描述 -->
										<div class="text-gray-700 dark:text-gray-300 leading-relaxed text-base whitespace-pre-wrap">
											{ticket.description}
										</div>
									{/if}
								</div>
							</div>
							
							<!-- 对话上下文 -->
							{#if chatData && chatData.messages}
								<div class="px-6 pb-6">
									<div class="border-t border-gray-200 dark:border-gray-600 pt-6">
										<div class="bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
											<!-- 标题栏 -->
											<div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
												<div class="flex items-center gap-2">
													<div class="w-2 h-2 bg-blue-500 rounded-full"></div>
													<h3 class="text-sm font-medium text-gray-900 dark:text-gray-100">对话上下文</h3>
												</div>
											</div>
											
											<!-- 消息列表 -->
											<div class="max-h-60 overflow-y-auto">
												{#each chatData.messages as message, index}
													<div class="px-4 py-3 border-b border-gray-100 dark:border-gray-700 last:border-b-0">
														<div class="flex items-start gap-3">
															<!-- 头像 -->
															<div class="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white text-xs font-medium flex-shrink-0">
																{message.role === 'user' ? 'U' : 'A'}
															</div>
															
															<!-- 消息内容 -->
															<div class="flex-1 min-w-0">
																<div class="flex items-center gap-2 mb-1">
																	<span class="text-xs font-medium text-gray-600 dark:text-gray-400">
																		{message.role === 'user' ? '用户' : 'AI助手'}
																	</span>
																	<span class="text-xs text-gray-400 dark:text-gray-500">
																		{new Date(message.timestamp || Date.now()).toLocaleString('zh-CN')}
																	</span>
																</div>
																<div class="prose prose-sm max-w-none text-gray-700 dark:text-gray-300">
																	{@html message.content}
																</div>
															</div>
														</div>
													</div>
												{/each}
											</div>
										</div>
									</div>
								</div>
							{/if}
						</div>
					</div>

					<!-- 任务要求 -->
					{#if ticket.task_requirements}
						<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">任务要求</h3>
							<div class="text-gray-700 dark:text-gray-300 leading-relaxed">
								{ticket.task_requirements}
							</div>
						</div>
					{/if}

					<!-- 交付内容 -->
					{#if ticket.delivery_text || (ticket.delivery_files && Array.isArray(ticket.delivery_files) && ticket.delivery_files.length > 0) || (ticket.delivery_images && Array.isArray(ticket.delivery_images) && ticket.delivery_images.length > 0)}
						<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-4">
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">交付内容</h3>
							<div class="space-y-4">
								{#if ticket.delivery_text}
									<div>
										<h4 class="text-sm font-medium text-gray-700 dark:text-gray-400 mb-2">文字说明</h4>
										<div class="bg-gray-50 dark:bg-gray-700 rounded-lg p-3 text-sm text-gray-900 dark:text-white">
											{ticket.delivery_text}
										</div>
									</div>
								{/if}
								
								{#if ticket.delivery_files && Array.isArray(ticket.delivery_files) && ticket.delivery_files.length > 0}
									<div>
										<h4 class="text-sm font-medium text-gray-700 dark:text-gray-400 mb-2">提交文件</h4>
										<div class="space-y-2">
											{#each ticket.delivery_files as file}
												<div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
													<div class="flex items-center space-x-3">
														<svg class="w-5 h-5 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
															<path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"></path>
														</svg>
														<div>
															<p class="font-medium text-gray-900 dark:text-white text-sm">{file.name || 'Unknown file'}</p>
															{#if file.size}
																<p class="text-xs text-gray-500">{formatFileSize(file.size)}</p>
															{/if}
														</div>
													</div>
													{#if file.id}
														<button type="button" class="text-blue-600 hover:text-blue-800 dark:text-blue-400 text-sm font-medium" on:click={() => previewOrDownloadFile(file)}>
															下载
														</button>
													{:else}
														<span class="text-xs text-gray-400">文件ID缺失</span>
													{/if}
												</div>
											{/each}
										</div>
									</div>
								{/if}
										</div>
									</div>
								{/if}
										</div>

				<!-- 右侧：问题分析和用户反馈 -->
				<div class="space-y-6">
					<!-- AI分析 -->
					{#if ticket.ai_analysis}
						<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden h-[600px] flex flex-col">
							<!-- 标题栏 -->
							<div class="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 px-6 py-4 border-b border-blue-200 dark:border-blue-800 flex-shrink-0">
								<div class="flex items-center gap-3">
									<div class="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
										<svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
											<path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd"/>
										</svg>
									</div>
									<h3 class="text-xl font-bold text-gray-900 dark:text-white">AI分析</h3>
								</div>
							</div>
							
							<!-- 内容区域 - 可滚动 -->
							<div class="flex-1 overflow-y-auto">
								<div class="p-6">
									<div class="prose prose-gray dark:prose-invert max-w-none">
										{#if aiAnalysis && aiAnalysis.analysis}
											<!-- 新格式：显示analysis字段（技术分析） -->
											<div class="text-gray-700 dark:text-gray-300 leading-relaxed text-base whitespace-pre-wrap">
												{aiAnalysis.analysis}
											</div>
										{:else if aiAnalysis && aiAnalysis.description}
											<!-- 人工工单格式：显示description字段 -->
											<div class="text-gray-700 dark:text-gray-300 leading-relaxed text-base whitespace-pre-wrap">
												{aiAnalysis.description}
											</div>
										{:else}
											<!-- 降级：显示工单描述 -->
											<div class="text-gray-700 dark:text-gray-300 leading-relaxed text-base whitespace-pre-wrap">
												{ticket.description}
											</div>
										{/if}
									</div>
								</div>
							</div>
						</div>
					{/if}

				</div>
				</div>

			<!-- 评论区域 - 使用时间线组件 -->
			<div class="mt-12">
				<CommentsTimeline 
					comments={ticket.comments || []} 
					onAddComment={handleAddComment}
				/>
			</div>
		</div>
		{:else}
			<div class="flex items-center justify-center h-64">
				<div class="text-center">
					<h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">工单不存在</h3>
					<p class="text-gray-500 dark:text-gray-400">请检查工单ID是否正确</p>
				</div>
			</div>
		{/if}
	</div>
</div>

<!-- 交付模态框 -->
{#if showDeliveryModal}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
			<div class="p-6">
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white">提交任务交付</h3>
					<button
						on:click={handleDeliveryClose}
						class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
					</svg>
				</button>
			</div>
			
				<form on:submit|preventDefault={handleDeliverySubmit}>
					<div class="space-y-4">
						<!-- 文字描述 -->
					<div>
							<label for="delivery-text" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								交付说明 <span class="text-red-500">*</span>
								</label>
							<textarea
								id="delivery-text"
								bind:value={deliveryText}
								rows="4"
								placeholder="请详细描述任务完成情况..."
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
								required
							></textarea>
							</div>
							
						<!-- 文件上传 -->
												<div>
							<label for="delivery-files" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								交付文件 (可选)
							</label>
							<input
								id="delivery-files"
								bind:this={fileInputRef}
								type="file"
								multiple
								on:change={handleFileSelect}
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
							/>
							{#if deliveryFiles.length > 0}
								<div class="mt-2 space-y-1">
									{#each deliveryFiles as file}
										<div class="text-sm text-gray-600 dark:text-gray-400">
											📄 {file.name} ({formatFileSize(file.size)})
										</div>
									{/each}
								</div>
							{/if}
						</div>
					</div>
					
					<!-- 操作按钮 -->
					<div class="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
						<button
							type="button"
							on:click={handleDeliveryClose}
							class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500"
						>
							取消
						</button>
						<button
							type="submit"
							disabled={deliverySubmitting || uploadingFiles || !deliveryText.trim()}
							class="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
						>
							{#if deliverySubmitting || uploadingFiles}
								<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
								{uploadingFiles ? '上传中...' : '提交中...'}
							{:else}
								<CheckCircle className="w-4 h-4" />
								提交交付
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
{/if}

<!-- 分配模态框 -->
{#if showAssignmentModal}
	<TicketAssignmentModal
		show={showAssignmentModal}
		{ticket}
		mode={assignmentMode}
		on:close={handleAssignmentClose}
		on:success={handleAssignmentSuccess}
	/>
{/if}

<!-- 验证模态框 -->
{#if showVerificationModal}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
			<div class="p-6">
				<div class="flex items-center justify-between mb-4">
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white">任务验证</h3>
					<button
						on:click={handleVerificationClose}
						class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
					</svg>
				</button>
			</div>
			
				<form on:submit|preventDefault={handleVerificationSubmit}>
					<div class="space-y-4">
						<!-- 验证结果 -->
						<div>
							<fieldset>
								<legend class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									验证结果 <span class="text-red-500">*</span>
								</legend>
								<div class="flex gap-4">
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={verificationResult}
											value="pass"
											class="mr-2"
										/>
										<span class="text-sm text-gray-700 dark:text-gray-300">通过</span>
									</label>
									<label class="flex items-center">
										<input
											type="radio"
											bind:group={verificationResult}
											value="reject"
											class="mr-2"
										/>
										<span class="text-sm text-gray-700 dark:text-gray-300">拒绝</span>
									</label>
								</div>
							</fieldset>
						</div>
					
						<!-- 验证说明 -->
					<div>
							<label for="verification-notes" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							验证说明
						</label>
						<textarea
								id="verification-notes"
							bind:value={verificationNotes}
							rows="3"
								placeholder="请说明验证结果的原因..."
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
						></textarea>
					</div>
					
						<!-- 验证清单 -->
						<div>
							<fieldset>
								<legend class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									验证清单
								</legend>
								<div class="space-y-2">
									{#each verificationChecklist as item, index}
										<label class="flex items-center">
											<input
												type="checkbox"
												bind:checked={item.checked}
												on:change={updateVerificationScore}
												class="mr-2"
											/>
											<span class="text-sm text-gray-700 dark:text-gray-300">{item.label}</span>
										</label>
									{/each}
								</div>
								<div class="mt-2 text-sm text-gray-600 dark:text-gray-400">
									完成度: {verificationScore}%
								</div>
							</fieldset>
						</div>
					</div>

					<!-- 操作按钮 -->
					<div class="flex justify-end gap-3 mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
						<button
							type="button"
							on:click={handleVerificationClose}
							class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500"
						>
							取消
						</button>
						<button
							type="submit"
							disabled={verificationSubmitting || !verificationResult}
							class="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
						>
							{#if verificationSubmitting}
								<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
								提交中...
							{:else}
								<CheckCircle className="w-4 h-4" />
								提交验证
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
{/if}
