<script lang="ts">
	import { getContext } from 'svelte';
	import { onMount, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	export let editor: any = null;
	
	let formatPainterActive = false;
	
	const handleFormatPainterToggle = (event: CustomEvent) => {
		formatPainterActive = event.detail.active;
	};
	
	const handleFormatPainterApplied = () => {
		formatPainterActive = false;
	};
	
	onMount(() => {
		window.addEventListener('toggleFormatPainter', handleFormatPainterToggle as EventListener);
		window.addEventListener('formatPainterApplied', handleFormatPainterApplied);
	});
	
	onDestroy(() => {
		window.removeEventListener('toggleFormatPainter', handleFormatPainterToggle as EventListener);
		window.removeEventListener('formatPainterApplied', handleFormatPainterApplied);
	});

	import Bold from '$lib/components/icons/Bold.svelte';
	import CodeBracket from '$lib/components/icons/CodeBracket.svelte';
	import H1 from '$lib/components/icons/H1.svelte';
	import H2 from '$lib/components/icons/H2.svelte';
	import H3 from '$lib/components/icons/H3.svelte';
	import Italic from '$lib/components/icons/Italic.svelte';
	import ListBullet from '$lib/components/icons/ListBullet.svelte';
	import NumberedList from '$lib/components/icons/NumberedList.svelte';
	import Strikethrough from '$lib/components/icons/Strikethrough.svelte';
	import Underline from '$lib/components/icons/Underline.svelte';

	import Tooltip from '../Tooltip.svelte';
	import ArrowLeftTag from '$lib/components/icons/ArrowLeftTag.svelte';
	import ArrowRightTag from '$lib/components/icons/ArrowRightTag.svelte';
	import MathEditor from './MathEditor.svelte';
	
	let mathEditorOpen = false;
	
	const openMathEditor = () => {
		mathEditorOpen = true;
	};
	
	const closeMathEditor = () => {
		mathEditorOpen = false;
	};
</script>

<div
	class="flex flex-col gap-1 p-1 rounded-xl shadow-lg bg-white text-gray-800 dark:text-white dark:bg-gray-850 min-w-fit border border-gray-100 dark:border-gray-800"
	style="max-width: min(calc(100vw - 3rem), 100%); box-sizing: border-box;"
>
	<!-- 第一行：文本编辑 -->
	<div class="flex gap-0.5 flex-wrap items-center">
		<div class="px-2 py-0.5 text-xs font-semibold text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-700 shadow-sm">
			<div class="flex items-center gap-1">
				<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
				</svg>
				<span>文本编辑</span>
			</div>
		</div>
	<Tooltip placement="top" content={$i18n.t('H1')}>
		<button
			on:click={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()}
			class="{editor?.isActive('heading', { level: 1 })
				? 'bg-gray-50 dark:bg-gray-700'
				: ''} hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<H1 />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('H2')}>
		<button
			on:click={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()}
			class="{editor?.isActive('heading', { level: 2 })
				? 'bg-gray-50 dark:bg-gray-700'
				: ''} hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<H2 />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('H3')}>
		<button
			on:click={() => editor?.chain().focus().toggleHeading({ level: 3 }).run()}
			class="{editor?.isActive('heading', { level: 3 })
				? 'bg-gray-50 dark:bg-gray-700'
				: ''} hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<H3 />
		</button>
	</Tooltip>

	{#if editor?.isActive('bulletList') || editor?.isActive('orderedList')}
		<Tooltip placement="top" content={$i18n.t('Lift List')}>
			<button
				on:click={() => {
					editor?.commands.liftListItem('listItem');
				}}
				class="hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
				type="button"
			>
				<ArrowLeftTag />
			</button>
		</Tooltip>
		<Tooltip placement="top" content={$i18n.t('Sink List')}>
			<button
				on:click={() =>
					editor?.commands.sinkListItem('listItem')}
				class="hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
				type="button"
			>
				<ArrowRightTag />
			</button>
		</Tooltip>
	{/if}

	<Tooltip placement="top" content={$i18n.t('Bullet List')}>
		<button
			on:click={() => editor?.chain().focus().toggleBulletList().run()}
			class="{editor?.isActive('bulletList')
				? 'bg-gray-50 dark:bg-gray-700'
				: ''} hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<ListBullet />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('Ordered List')}>
		<button
			on:click={() => editor?.chain().focus().toggleOrderedList().run()}
			class="{editor?.isActive('orderedList')
				? 'bg-gray-50 dark:bg-gray-700'
				: ''} hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<NumberedList />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('Bold')}>
		<button
			on:click={() => editor?.chain().focus().toggleBold().run()}
			class="{editor?.isActive('bold')
				? 'bg-gray-50 dark:bg-gray-700'
				: ''} hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<Bold />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('Italic')}>
		<button
			on:click={() => editor?.chain().focus().toggleItalic().run()}
			class="{editor?.isActive('italic')
				? 'bg-gray-50 dark:bg-gray-700'
				: ''} hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<Italic />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('Underline')}>
		<button
			on:click={() => editor?.chain().focus().toggleUnderline().run()}
			class="{editor?.isActive('underline')
				? 'bg-gray-50 dark:bg-gray-700'
				: ''} hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<Underline />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('Strikethrough')}>
		<button
			on:click={() => editor?.chain().focus().toggleStrike().run()}
			class="{editor?.isActive('strike')
				? 'bg-gray-50 dark:bg-gray-700'
				: ''} hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<Strikethrough />
		</button>
	</Tooltip>

	<Tooltip placement="top" content={$i18n.t('Code Block')}>
		<button
			on:click={() => editor?.chain().focus().toggleCodeBlock().run()}
			class="{editor?.isActive('codeBlock')
				? 'bg-gray-50 dark:bg-gray-700'
				: ''} hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
			type="button"
		>
			<CodeBracket />
		</button>
	</Tooltip>
	</div>

	<!-- 第二行：表格编辑 -->
	{#if editor?.isActive('table') || editor?.isActive('tableRow') || editor?.isActive('tableCell')}
	<div class="flex gap-0.5 flex-wrap items-center">
		<!-- 表格工具栏标识 -->
		<div class="px-2 py-0.5 text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 rounded border border-blue-300 dark:border-blue-700 shadow-sm">
			<div class="flex items-center gap-1">
				<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
				</svg>
				<span>表格编辑</span>
			</div>
		</div>
		
		<!-- 添加行 -->
		<Tooltip placement="top" content="在上方添加行">
			<button
				on:click={() => editor?.chain().focus().addRowBefore().run()}
				class="hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
				type="button"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m0 0l-4-4m4 4l4-4M4 12h16"></path>
				</svg>
			</button>
		</Tooltip>
		
		<Tooltip placement="top" content="在下方添加行">
			<button
				on:click={() => {
					editor?.chain().focus().addRowAfter().run();
				}}
				class="hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg p-1.5 transition-all hover:scale-110 active:scale-95"
				type="button"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m0 0l-4-4m4 4l4-4M20 12H4"></path>
				</svg>
			</button>
		</Tooltip>
		
		<!-- 删除行 -->
		<Tooltip placement="top" content="删除当前行">
			<button
				on:click={() => {
					editor?.chain().focus().deleteRow().run();
				}}
				class="hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg p-1.5 transition-all hover:scale-110 active:scale-95 text-red-600 dark:text-red-400"
				type="button"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
				</svg>
			</button>
		</Tooltip>
		
		<!-- 添加列 -->
		<Tooltip placement="top" content="在左侧添加列">
			<button
				on:click={() => {
					editor?.chain().focus().addColumnBefore().run();
				}}
				class="hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg p-1.5 transition-all hover:scale-110 active:scale-95"
				type="button"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 12h16m0 0l-4-4m4 4l-4 4M4 12l4-4m-4 4l4 4"></path>
				</svg>
			</button>
		</Tooltip>
		
		<Tooltip placement="top" content="在右侧添加列">
			<button
				on:click={() => {
					editor?.chain().focus().addColumnAfter().run();
				}}
				class="hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg p-1.5 transition-all hover:scale-110 active:scale-95"
				type="button"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4m0 0l4-4m-4 4l4 4"></path>
				</svg>
			</button>
		</Tooltip>
		
		<!-- 删除列 -->
		<Tooltip placement="top" content="删除当前列">
			<button
				on:click={() => {
					editor?.chain().focus().deleteColumn().run();
				}}
				class="hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg p-1.5 transition-all hover:scale-110 active:scale-95 text-red-600 dark:text-red-400"
				type="button"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
				</svg>
			</button>
		</Tooltip>
		
		<!-- 合并单元格 -->
		<Tooltip placement="top" content="合并单元格">
			<button
				on:click={() => {
					if (editor?.can().mergeCells()) {
						// 使用 requestAnimationFrame 优化性能
						requestAnimationFrame(() => {
							editor?.chain().focus().mergeCells().run();
						});
					}
				}}
				class="hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-lg p-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
				type="button"
				disabled={!editor?.can().mergeCells()}
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zM14 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"></path>
				</svg>
			</button>
		</Tooltip>
		
		<Tooltip placement="top" content="拆分单元格">
			<button
				on:click={() => {
					if (editor?.can().splitCell()) {
						// 使用 requestAnimationFrame 优化性能
						requestAnimationFrame(() => {
							editor?.chain().focus().splitCell().run();
						});
					}
				}}
				class="hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-lg p-1.5 transition-colors {!editor?.can().splitCell() ? 'opacity-40 cursor-not-allowed' : ''}"
				type="button"
				title={editor?.can().splitCell() ? "拆分单元格" : "请先选中已合并的单元格"}
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zM14 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"></path>
				</svg>
			</button>
		</Tooltip>
		
		<!-- 格式刷 -->
		<Tooltip placement="top" content={formatPainterActive ? "点击目标单元格/行/列应用格式" : "格式刷：复制格式到其他单元格/行/列"}>
			<button
				on:click={() => {
					// 触发格式刷模式切换事件
					const event = new CustomEvent('toggleFormatPainter', { detail: { active: !formatPainterActive } });
					window.dispatchEvent(event);
				}}
				class="hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg p-1.5 transition-all hover:scale-110 active:scale-95 {formatPainterActive ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400' : 'text-green-600 dark:text-green-400'}"
				type="button"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"></path>
				</svg>
			</button>
		</Tooltip>
		
		<!-- 删除表格 -->
		<Tooltip placement="top" content="删除表格">
			<button
				on:click={() => {
					editor?.chain().focus().deleteTable().run();
				}}
				class="hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg p-1.5 transition-all hover:scale-110 active:scale-95 text-red-600 dark:text-red-400"
				type="button"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
				</svg>
			</button>
		</Tooltip>
	</div>
	{/if}

	<!-- 第三行：公式编辑 -->
	<div class="flex gap-0.5 flex-wrap items-center">
		<div class="px-2 py-0.5 text-xs font-semibold text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/30 rounded border border-purple-300 dark:border-purple-700 shadow-sm">
			<div class="flex items-center gap-1">
				<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"></path>
				</svg>
				<span>公式编辑</span>
			</div>
		</div>
		<Tooltip placement="top" content="数学公式">
			<button
				on:click={openMathEditor}
				class="hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg p-1.5 transition-all"
				type="button"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"></path>
				</svg>
			</button>
		</Tooltip>
	</div>
</div>

<MathEditor {editor} isOpen={mathEditorOpen} on:close={closeMathEditor} />
