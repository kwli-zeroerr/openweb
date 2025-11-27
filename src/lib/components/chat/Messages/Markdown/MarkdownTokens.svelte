<script lang="ts">
	import DOMPurify from 'dompurify';
	import { onMount, getContext } from 'svelte';
	const i18n = getContext('i18n');

	import { marked, type Token } from 'marked';
	import { unescapeHtml } from '$lib/utils';
	import { WEBUI_BASE_URL } from '$lib/constants';
    
	// Simple state management for Markdown tables
	let markdownTableStates: Record<string, boolean> = {};
	let forceUpdate = 0; // Force reactivity trigger
	import MarkdownInlineTokens from '$lib/components/chat/Messages/Markdown/MarkdownInlineTokens.svelte';
	import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';
	import KatexRenderer from './KatexRenderer.svelte';
	import AlertRenderer, { alertComponent } from './AlertRenderer.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	import Source from './Source.svelte';
	import { settings } from '$lib/stores';
	import HtmlToken from './HTMLToken.svelte';

	export let id: string;
	export let tokens: Token[];
	export let top = true;
	export let attributes = {};

	export let done = true;

	export let save = false;
	export let preview = false;

	export let editCodeBlock = true;
	export let topPadding = false;

	export let onSave: Function = () => {};
	export let onUpdate: Function = () => {};
	export let onPreview: Function = () => {};

	export let onTaskClick: Function = () => {};
	export let onSourceClick: Function = () => {};

	const headerComponent = (depth: number) => {
		return 'h' + depth;
	};
</script>

<!-- {JSON.stringify(tokens)} -->
{#each tokens as token, tokenIdx (tokenIdx)}
	{#if token.type === 'hr'}
		<hr class=" border-gray-100 dark:border-gray-850" />
	{:else if token.type === 'heading'}
		<svelte:element this={headerComponent(token.depth)} dir="auto">
			<MarkdownInlineTokens
				id={`${id}-${tokenIdx}-h`}
				tokens={token.tokens}
				{done}
				{onSourceClick}
			/>
		</svelte:element>
	{:else if token.type === 'code'}
		{#if token.raw.includes('```')}
			<CodeBlock
				id={`${id}-${tokenIdx}`}
				collapsed={$settings?.collapseCodeBlocks ?? false}
				{token}
				lang={token?.lang ?? ''}
				code={token?.text ?? ''}
				{attributes}
				{save}
				{preview}
				edit={editCodeBlock}
				stickyButtonsClassName={topPadding ? 'top-7' : 'top-0'}
				onSave={(value) => {
					onSave({
						raw: token.raw,
						oldContent: token.text,
						newContent: value
					});
				}}
				{onUpdate}
				{onPreview}
			/>
		{:else}
			{token.text}
		{/if}
	{:else if token.type === 'table'}
        {@const tableId = `table-${id}-${tokenIdx}`}
        {@const getKey = () => `${id}:${tableId}`}
        
        <!-- Markdown 表格折叠功能 -->
        {@const getCollapsed = () => {
            forceUpdate; // Trigger reactivity
            return markdownTableStates[tableId] || false;
        }}
        {@const toggleCollapsed = () => {
            console.log('Markdown table toggleCollapsed called for:', tableId);
            const currentState = markdownTableStates[tableId] || false;
            const next = !currentState;
            markdownTableStates[tableId] = next;
            markdownTableStates = { ...markdownTableStates }; // Trigger reactivity
            forceUpdate++; // Force reactivity update
            console.log('Markdown table collapsed state toggled:', tableId, next);
        }}
        
        <div class="relative group mb-4" data-table-id={tableId}>
			<!-- 表格折叠按钮 -->
            <div class="absolute top-0 right-0 z-10 opacity-80 hover:opacity-100 transition-opacity duration-200">
                <button
                    class="p-1.5 rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm shadow-sm hover:bg-white dark:hover:bg-gray-700 transition-all duration-200 border border-gray-200 dark:border-gray-600"
                    on:click|stopPropagation={toggleCollapsed}
                    title={getCollapsed() ? "展开表格" : "折叠表格"}
                >
                    {#if getCollapsed()}
                        <svg class="w-3.5 h-3.5 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                        </svg>
                    {:else}
                        <svg class="w-3.5 h-3.5 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                        </svg>
					{/if}
				</button>
			</div>

            <!-- 折叠后的摘要显示 -->
            {#if getCollapsed()}
                <div class="table-summary bg-gray-50 dark:bg-gray-700 p-4 rounded-lg mb-2 transition-all duration-300 ease-in-out">
					<div class="text-sm text-gray-600 dark:text-gray-300 mb-2">
						<span class="font-semibold">表格摘要:</span>
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400">
						{#each token.header as header, headerIdx}
							<span class="inline-block mr-3">
								<MarkdownInlineTokens
									id={`${id}-${tokenIdx}-summary-header-${headerIdx}`}
									tokens={header.tokens}
									{done}
									{onSourceClick}
								/>
							</span>
						{/each}
					</div>
					{#if token.rows.length > 0}
						<div class="text-xs text-gray-500 dark:text-gray-400 mt-2">
							<span class="font-medium">第一行数据:</span>
							{#each token.rows[0] ?? [] as cell, cellIdx}
								<span class="inline-block mr-3">
									<MarkdownInlineTokens
										id={`${id}-${tokenIdx}-summary-row-0-${cellIdx}`}
										tokens={cell.tokens}
										{done}
										{onSourceClick}
									/>
								</span>
							{/each}
						</div>
					{/if}
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-2">
						<span class="italic">点击展开按钮查看完整表格内容</span>
					</div>
				</div>
            {/if}

            <!-- 表格内容（折叠时隐藏） -->
            {#if !getCollapsed()}
                <div class="transition-all duration-300 ease-in-out">
                    <div class="table-container relative w-full overflow-hidden">
                <table
					id={tableId}
					class="rendered-table text-sm text-gray-700 dark:text-gray-200"
				>
					<thead>
						<tr>
							{#each token.header as header, headerIdx}
								<th
									scope="col"
									class="font-medium text-sm"
									style={token.align[headerIdx] ? `text-align: ${token.align[headerIdx]}` : ''}
								>
									<div class="flex items-center gap-2">
										<div class="shrink-0 break-normal w-full">
											<MarkdownInlineTokens
												id={`${id}-${tokenIdx}-header-${headerIdx}`}
												tokens={header.tokens}
												{done}
												{onSourceClick}
											/>
										</div>
									</div>
								</th>
							{/each}
						</tr>
					</thead>
                    <tbody>
						{#each token.rows as row, rowIdx}
							<tr>
								{#each row ?? [] as cell, cellIdx}
									<td
										class="text-gray-900 dark:text-gray-100"
										style={token.align[cellIdx] ? `text-align: ${token.align[cellIdx]}` : ''}
									>
										<div class="break-normal">
											<MarkdownInlineTokens
												id={`${id}-${tokenIdx}-row-${rowIdx}-${cellIdx}`}
												tokens={cell.tokens}
												{done}
												{onSourceClick}
											/>
										</div>
									</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
                    </div>
                </div>
            {/if}
        </div>
	{:else if token.type === 'blockquote'}
		{@const alert = alertComponent(token)}
		{#if alert}
			<AlertRenderer {token} {alert} />
		{:else}
			<blockquote dir="auto">
				<svelte:self
					id={`${id}-${tokenIdx}`}
					tokens={token.tokens}
					{done}
					{editCodeBlock}
					{onTaskClick}
					{onSourceClick}
				/>
			</blockquote>
		{/if}
	{:else if token.type === 'list'}
		{#if token.ordered}
			<ol start={token.start || 1} dir="auto">
				{#each token.items as item, itemIdx}
					<li class="text-start">
						{#if item?.task}
							<input
								class=" translate-y-[1px] -translate-x-1"
								type="checkbox"
								checked={item.checked}
								on:change={(e) => {
									onTaskClick({
										id: id,
										token: token,
										tokenIdx: tokenIdx,
										item: item,
										itemIdx: itemIdx,
										checked: e.target.checked
									});
								}}
							/>
						{/if}

						<svelte:self
							id={`${id}-${tokenIdx}-${itemIdx}`}
							tokens={item.tokens}
							top={token.loose}
							{done}
							{editCodeBlock}
							{onTaskClick}
							{onSourceClick}
						/>
					</li>
				{/each}
			</ol>
		{:else}
			<ul dir="auto" class="">
				{#each token.items as item, itemIdx}
					<li class="text-start {item?.task ? 'flex -translate-x-6.5 gap-3 ' : ''}">
						{#if item?.task}
							<input
								class=""
								type="checkbox"
								checked={item.checked}
								on:change={(e) => {
									onTaskClick({
										id: id,
										token: token,
										tokenIdx: tokenIdx,
										item: item,
										itemIdx: itemIdx,
										checked: e.target.checked
									});
								}}
							/>

							<div>
								<svelte:self
									id={`${id}-${tokenIdx}-${itemIdx}`}
									tokens={item.tokens}
									top={token.loose}
									{done}
									{editCodeBlock}
									{onTaskClick}
									{onSourceClick}
								/>
							</div>
						{:else}
							<svelte:self
								id={`${id}-${tokenIdx}-${itemIdx}`}
								tokens={item.tokens}
								top={token.loose}
								{done}
								{editCodeBlock}
								{onTaskClick}
								{onSourceClick}
							/>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
	{:else if token.type === 'details'}
		<Collapsible
			title={token.summary}
			open={$settings?.expandDetails ?? false}
			attributes={token?.attributes}
			className="w-full space-y-1"
			dir="auto"
		>
			<div class=" mb-1.5" slot="content">
				<svelte:self
					id={`${id}-${tokenIdx}-d`}
					tokens={marked.lexer(token.text)}
					attributes={token?.attributes}
					{done}
					{editCodeBlock}
					{onTaskClick}
					{onSourceClick}
				/>
			</div>
		</Collapsible>
	{:else if token.type === 'html'}
		<HtmlToken {id} {token} {onSourceClick} />
	{:else if token.type === 'iframe'}
		<iframe
			src="{WEBUI_BASE_URL}/api/v1/files/{token.fileId}/content"
			title={token.fileId}
			width="100%"
			frameborder="0"
			onload="this.style.height=(this.contentWindow.document.body.scrollHeight+20)+'px';"
		></iframe>
	{:else if token.type === 'paragraph'}
		<p dir="auto">
			<MarkdownInlineTokens
				id={`${id}-${tokenIdx}-p`}
				tokens={token.tokens ?? []}
				{done}
				{onSourceClick}
			/>
		</p>
	{:else if token.type === 'text'}
		{#if top}
			<p>
				{#if token.tokens}
					<MarkdownInlineTokens
						id={`${id}-${tokenIdx}-t`}
						tokens={token.tokens}
						{done}
						{onSourceClick}
					/>
				{:else}
					{unescapeHtml(token.text)}
				{/if}
			</p>
		{:else if token.tokens}
			<MarkdownInlineTokens
				id={`${id}-${tokenIdx}-p`}
				tokens={token.tokens ?? []}
				{done}
				{onSourceClick}
			/>
		{:else}
			{unescapeHtml(token.text)}
		{/if}
	{:else if token.type === 'inlineKatex'}
		{#if token.text}
			<KatexRenderer content={token.text} displayMode={token?.displayMode ?? false} />
		{/if}
	{:else if token.type === 'blockKatex'}
		{#if token.text}
			<KatexRenderer content={token.text} displayMode={token?.displayMode ?? false} />
		{/if}
	{:else if token.type === 'space'}
		<div class="my-2" />
	{:else}
		{console.log('Unknown token', token)}
	{/if}
{/each}

<style>
	.table-container {
		width: 100%;
	}

	.table-container :global(table.rendered-table) {
		width: 100%;
		max-width: 100%;
		border-collapse: collapse;
		border: 2px solid #e5e7eb;
		border-radius: 8px;
		margin: 1rem 0;
		overflow: hidden;
		background-color: #ffffff;
		table-layout: fixed;
		word-break: break-word;
		white-space: normal;
	}

	.table-container :global(table.rendered-table thead tr) {
		background-color: #f9fafb;
		color: #1f2937;
	}

	.table-container :global(table.rendered-table th) {
		font-weight: 600;
	}

	.table-container :global(table.rendered-table td) {
		font-weight: 400;
		color: #111827;
	}

	.table-container :global(table.rendered-table th),
	.table-container :global(table.rendered-table td) {
		padding: 0.75rem 1rem;
		border: 1px solid #e5e7eb;
		text-align: left;
		vertical-align: top;
		line-height: 1.5;
		min-width: 70px;
		text-transform: none !important;
		word-break: break-word;
		white-space: normal;
	}

	.table-container :global(table.rendered-table tbody tr:nth-child(even)) {
		background-color: #fdfdfd;
	}

	.table-container :global(table.rendered-table tbody tr:hover) {
		background-color: #f3f4f6;
		transition: background-color 0.15s ease;
	}

	:global(.dark) .table-container :global(table.rendered-table) {
		border-color: #4b5563;
		background-color: #1f2937;
	}

	:global(.dark) .table-container :global(table.rendered-table thead tr) {
		background-color: #374151;
		color: #e5e7eb;
	}

	:global(.dark) .table-container :global(table.rendered-table th),
	:global(.dark) .table-container :global(table.rendered-table td) {
		border-color: #4b5563;
	}

	:global(.dark) .table-container :global(table.rendered-table td) {
		color: #f3f4f6;
	}

	:global(.dark) .table-container :global(table.rendered-table tbody tr:nth-child(even)) {
		background-color: #273042;
	}

	:global(.dark) .table-container :global(table.rendered-table tbody tr:hover) {
		background-color: #374151;
	}
</style>
