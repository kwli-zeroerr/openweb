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
	import KatexRenderer from '$lib/components/chat/Messages/Markdown/KatexRenderer.svelte';
	import AlertRenderer, { alertComponent } from '$lib/components/chat/Messages/Markdown/AlertRenderer.svelte';
	import Collapsible from '$lib/components/common/Collapsible.svelte';

	import Source from '$lib/components/chat/Messages/Markdown/Source.svelte';
	import { settings } from '$lib/stores';
	import HtmlToken from '$lib/components/chat/Messages/Markdown/HTMLToken.svelte';

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
		<svelte:element this={headerComponent(token.depth)} dir="auto" data-sourcepos="heading-{tokenIdx}">
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
        
        <div class="relative group mb-4" data-table-id={tableId} data-sourcepos="table-{tokenIdx}">
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
                    <div class="table-container scrollbar-hidden relative overflow-x-auto inline-block">
                <table
					id={tableId}
					class="text-sm text-center text-gray-600 dark:text-gray-300"
					style="border-collapse: collapse; border-spacing: 0; width: auto; min-width: fit-content; border: 1px solid #d1d5db;"
					data-sourcepos="table-{tokenIdx}"
				>
					<thead>
						<tr class="bg-gray-50 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
							{#each token.header as header, headerIdx}
								<th
									scope="col"
									class="px-3 py-2 font-medium text-sm border-r border-gray-300 dark:border-gray-600 last:border-r-0 text-center border-b border-gray-300 dark:border-gray-600"
									style={token.align[headerIdx] ? `text-align: ${token.align[headerIdx]}` : ''}
								>
									<div class="flex items-center justify-center gap-2">
										<div class="shrink-0 break-normal">
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
                    <tbody class="bg-white dark:bg-gray-800">
						{#each token.rows as row, rowIdx}
							<tr class="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors duration-150">
								{#each row ?? [] as cell, cellIdx}
									<td
										class="px-3 py-2 text-gray-900 dark:text-gray-100 border-r border-gray-300 dark:border-gray-600 last:border-r-0 text-center {token.rows.length - 1 === rowIdx ? 'border-b-0' : 'border-b border-gray-300 dark:border-gray-600'}"
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
		<p dir="auto" data-sourcepos="paragraph-{tokenIdx}">
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
