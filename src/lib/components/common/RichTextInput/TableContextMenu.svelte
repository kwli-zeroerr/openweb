<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	
	export let editor: any = null;
	export let x: number = 0;
	export let y: number = 0;
	export let visible: boolean = false;
	
	const dispatch = createEventDispatcher();
	
	let menuElement: HTMLElement | null = null;
	
	const handleAction = (action: () => void) => {
		if (editor) {
			action();
			dispatch('close');
		}
	};
	
	// 确保菜单在视口内
	$: if (visible && menuElement) {
		// 使用setTimeout确保DOM已更新
		setTimeout(() => {
			if (menuElement) {
				const rect = menuElement.getBoundingClientRect();
				const viewportWidth = window.innerWidth;
				const viewportHeight = window.innerHeight;
				
				let adjustedX = x;
				let adjustedY = y;
				
				// 如果菜单会超出右边界，调整到左侧
				if (rect.right > viewportWidth) {
					adjustedX = viewportWidth - rect.width - 10;
				}
				
				// 如果菜单会超出下边界，调整到上方
				if (rect.bottom > viewportHeight) {
					adjustedY = viewportHeight - rect.height - 10;
				}
				
				// 确保不会超出左边界和上边界
				if (adjustedX < 10) adjustedX = 10;
				if (adjustedY < 10) adjustedY = 10;
				
				menuElement.style.left = adjustedX + 'px';
				menuElement.style.top = adjustedY + 'px';
			}
		}, 0);
	}
</script>

{#if visible && editor}
	<div
		bind:this={menuElement}
		class="fixed z-[9999] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl py-1 min-w-[200px]"
		style="left: {x}px; top: {y}px;"
		on:click|stopPropagation
		on:contextmenu|preventDefault
		role="menu"
	>
		<!-- 行操作 -->
		<div class="px-3 py-1.5 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase border-b border-gray-200 dark:border-gray-700">
			行操作
		</div>
		<button
			class="w-full px-3 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 transition-colors"
			on:click={() => handleAction(() => editor?.chain().focus().addRowBefore().run())}
			role="menuitem"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m0 0l-4-4m4 4l4-4M4 12h16"></path>
			</svg>
			<span>在上方添加行</span>
		</button>
		<button
			class="w-full px-3 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 transition-colors"
			on:click={() => handleAction(() => editor?.chain().focus().addRowAfter().run())}
			role="menuitem"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m0 0l-4-4m4 4l4-4M20 12H4"></path>
			</svg>
			<span>在下方添加行</span>
		</button>
		<button
			class="w-full px-3 py-2 text-sm text-left hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400 flex items-center gap-2 transition-colors"
			on:click={() => handleAction(() => editor?.chain().focus().deleteRow().run())}
			role="menuitem"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
			</svg>
			<span>删除当前行</span>
		</button>
		
		<!-- 列操作 -->
		<div class="px-3 py-1.5 mt-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase border-b border-gray-200 dark:border-gray-700">
			列操作
		</div>
		<button
			class="w-full px-3 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 transition-colors"
			on:click={() => handleAction(() => editor?.chain().focus().addColumnBefore().run())}
			role="menuitem"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 12h16m0 0l-4-4m4 4l-4 4M4 12l4-4m-4 4l4 4"></path>
			</svg>
			<span>在左侧添加列</span>
		</button>
		<button
			class="w-full px-3 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 transition-colors"
			on:click={() => handleAction(() => editor?.chain().focus().addColumnAfter().run())}
			role="menuitem"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4m0 0l4-4m-4 4l4 4"></path>
			</svg>
			<span>在右侧添加列</span>
		</button>
		<button
			class="w-full px-3 py-2 text-sm text-left hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400 flex items-center gap-2 transition-colors"
			on:click={() => handleAction(() => editor?.chain().focus().deleteColumn().run())}
			role="menuitem"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
			</svg>
			<span>删除当前列</span>
		</button>
		
		<!-- 单元格操作 -->
		<div class="px-3 py-1.5 mt-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase border-b border-gray-200 dark:border-gray-700">
			单元格操作
		</div>
		<button
			class="w-full px-3 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
			disabled={!editor?.can().mergeCells()}
			on:click={() => {
				if (editor?.can().mergeCells()) {
					// 使用 requestAnimationFrame 优化性能
					requestAnimationFrame(() => {
						handleAction(() => editor?.chain().focus().mergeCells().run());
					});
				}
			}}
			role="menuitem"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zM14 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"></path>
			</svg>
			<span>合并单元格</span>
		</button>
		<button
			class="w-full px-3 py-2 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2 transition-colors {!editor?.can().splitCell() ? 'opacity-50 cursor-not-allowed' : ''}"
			on:click={() => {
				if (editor?.can().splitCell()) {
					// 使用 requestAnimationFrame 优化性能
					requestAnimationFrame(() => {
						handleAction(() => editor?.chain().focus().splitCell().run());
					});
				}
			}}
			role="menuitem"
			title={editor?.can().splitCell() ? "拆分单元格" : "请先选中已合并的单元格"}
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM14 5a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1V5zM4 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1H5a1 1 0 01-1-1v-4zM14 15a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"></path>
			</svg>
			<span>拆分单元格</span>
		</button>
		
		<!-- 删除表格 -->
		<div class="px-3 py-1.5 mt-1 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase border-b border-gray-200 dark:border-gray-700">
			表格操作
		</div>
		<button
			class="w-full px-3 py-2 text-sm text-left hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400 flex items-center gap-2 transition-colors"
			on:click={() => handleAction(() => editor?.chain().focus().deleteTable().run())}
			role="menuitem"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
			</svg>
			<span>删除表格</span>
		</button>
	</div>
{/if}
