<script lang="ts">
	import { onMount } from 'svelte';
	import Modal from './common/Modal.svelte';
	import XMark from './icons/XMark.svelte';

	export let show = false;

	const closeModal = () => {
		show = false;
		// 记录用户已查看过此弹窗
		localStorage.setItem('zeroerrInfoViewed', 'true');
	};

	// 检查是否已查看过
	onMount(() => {
		const viewed = localStorage.getItem('zeroerrInfoViewed');
		if (!viewed) {
			show = true;
		}
	});
</script>

<Modal bind:show size="lg">
	<div class="px-6 pt-5 dark:text-white text-black">
		<div class="flex justify-between items-start">
			<div class="text-xl font-medium">
				ZeroErr GPT 售后内测版 v1.2.0
			</div>
			<button
				class="self-center"
				on:click={closeModal}
				aria-label="关闭"
			>
				<XMark className={'size-5'}>
					<p class="sr-only">关闭</p>
				</XMark>
			</button>
		</div>
		<div class="flex items-center mt-1">
			<div class="text-sm dark:text-gray-200">版本信息</div>
		</div>
	</div>

	<div class="w-full p-4 px-5 text-gray-700 dark:text-gray-100">
		<div class="space-y-4">
			<!-- 主要信息 -->
			<div class="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
				<h3 class="font-semibold text-lg mb-2 text-blue-800 dark:text-blue-200">
					ZeroErr GPT 售后内测版 v1.2.0
				</h3>
				<p class="text-blue-700 dark:text-blue-300">
					欢迎使用 ZeroErr GPT 售后内测版本！
				</p>
			</div>

			<!-- 版本更新 -->
			<div class="space-y-3">
				<h4 class="font-semibold text-gray-800 dark:text-gray-200">v1.2.0 版本更新：</h4>
				<div class="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
					<p class="text-green-800 dark:text-green-200 font-medium mb-3">
						相比 v1.1.8 版本，v1.2.0 版本做了以下改进：
					</p>
					<ol class="space-y-2 text-sm text-green-700 dark:text-green-300">
						<li class="flex items-start">
							<span class="font-medium mr-2">1、</span>
							<span>改变了网站的架构，可以支持更多的定制化开发，方便嵌入更多功能</span>
						</li>
						<li class="flex items-start">
							<span class="font-medium mr-2">2、</span>
							<span>增加追问功能</span>
						</li>
						<li class="flex items-start">
							<span class="font-medium mr-2">3、</span>
							<span>增加反馈功能</span>
						</li>
					</ol>
				</div>
			</div>

			<!-- 主要特性 -->
			<div class="space-y-3">
				<h4 class="font-semibold text-gray-800 dark:text-gray-200">主要特性：</h4>
				<ul class="space-y-2 text-sm">
					<li class="flex items-start">
						<span class="text-green-500 mr-2">✓</span>
						<span>基于 Open WebUI 的现代化界面</span>
					</li>
					<li class="flex items-start">
						<span class="text-green-500 mr-2">✓</span>
						<span>支持多种 AI 模型接入</span>
					</li>
					<li class="flex items-start">
						<span class="text-green-500 mr-2">✓</span>
						<span>模型评分和排行榜系统</span>
					</li>
					<li class="flex items-start">
						<span class="text-green-500 mr-2">✓</span>
						<span>美观的表格展示和折叠功能</span>
					</li>
					<li class="flex items-start">
						<span class="text-green-500 mr-2">✓</span>
						<span>完整的 CORS 和代理支持</span>
					</li>
				</ul>
			</div>

			<!-- 技术信息 -->
			<div class="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
				<h4 class="font-semibold text-gray-800 dark:text-gray-200 mb-2">技术信息：</h4>
				<div class="text-sm space-y-1">
					<p><span class="font-medium">版本：</span>v1.2.0</p>
					<p><span class="font-medium">构建：</span>1.2.0</p>
					<p><span class="font-medium">仓库：</span>
						<a 
							href="https://git.zeroerr.cn/Don/openwebui-zeroerr" 
							target="_blank" 
							class="text-blue-600 dark:text-blue-400 hover:underline"
						>
							https://git.zeroerr.cn/Don/openwebui-zeroerr
						</a>
					</p>
				</div>
			</div>

			<!-- 注意事项 -->
			<div class="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
				<h4 class="font-semibold text-yellow-800 dark:text-yellow-200 mb-2">注意事项：</h4>
				<p class="text-yellow-700 dark:text-yellow-300 text-sm">
					这是内测版本，如有问题请及时反馈。感谢您的使用！
				</p>
			</div>
		</div>

		<div class="flex justify-end pt-4">
			<button
				on:click={closeModal}
				class="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition rounded-lg"
			>
				我知道了
			</button>
		</div>
	</div>
</Modal>
