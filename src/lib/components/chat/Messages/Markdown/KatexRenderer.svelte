<script lang="ts">
	import type { renderToString as katexRenderToString } from 'katex';
	import { onMount } from 'svelte';

	export let content: string;
	export let displayMode: boolean = false;

	let renderToString: typeof katexRenderToString | null = null;

	onMount(async () => {
		const [katex] = await Promise.all([
			import('katex'),
			import('katex/contrib/mhchem'),
			import('katex/dist/katex.min.css')
		]);
		renderToString = katex.renderToString;
	});
</script>

{#if renderToString}
	{@html renderToString(content, { 
		displayMode, 
		throwOnError: false,
		strict: false,  // 禁用严格模式，减少 Unicode 字符警告
		trust: true     // 允许更多内容类型
	})}
{/if}
