<script lang="ts">
	import { getVersionUpdates } from '$lib/apis';
	import { getOllamaVersion } from '$lib/apis/ollama';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { WEBUI_NAME, config, showChangelog } from '$lib/stores';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	let ollamaVersion = '';

	let updateAvailable = null;
	let version = {
		current: '',
		latest: ''
	};

	const checkForVersionUpdates = async () => {
		updateAvailable = null;
		// 直接使用本地版本，不检查远程更新
		version = {
			current: WEBUI_VERSION,
			latest: WEBUI_VERSION
		};

		console.log(version);

		updateAvailable = compareVersion(version.latest, version.current);
		console.log(updateAvailable);
	};

	onMount(async () => {
		ollamaVersion = await getOllamaVersion(localStorage.token).catch((error) => {
			return '';
		});

		if ($config?.features?.enable_version_update_check) {
			checkForVersionUpdates();
		}
	});
</script>

<div id="tab-about" class="flex flex-col h-full justify-between space-y-3 text-sm mb-6">
	<div class=" space-y-3 overflow-y-scroll max-h-[28rem] md:max-h-full">
		<div>
			<div class=" mb-2.5 text-sm font-medium flex space-x-2 items-center">
				<div>
					{$WEBUI_NAME}
					{$i18n.t('Version')}
				</div>
			</div>
			<div class="flex w-full justify-between items-center">
				<div class="flex flex-col text-xs text-gray-700 dark:text-gray-200">
					<div class="flex gap-1">
						<Tooltip content={WEBUI_BUILD_HASH}>
							v{WEBUI_VERSION}
						</Tooltip>

						{#if $config?.features?.enable_version_update_check}
							<a
								href="https://git.zeroerr.cn/Don/openwebui-zeroerr/src/tag/v{version.latest}"
								target="_blank"
							>
								{updateAvailable === null
									? $i18n.t('Checking for updates...')
									: updateAvailable
										? `(v${version.latest} ${$i18n.t('available!')})`
										: $i18n.t('(latest)')}
							</a>
						{/if}
					</div>

					<button
						class=" underline flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-500"
						on:click={() => {
							// 显示ZeroErr GPT信息
							alert(`各位同事好，ZeroErr GPT 售后内测版 v1.2.0已上线，可无内网限制访问：
👉 固定地址：https://gpt.zeroerr.com
相比v1.1.8版本GPT，v1.2.0版本做了以下改进：
1、改变了网站的架构，可以支持更多的定制化开发，方便嵌入更多功能
2、增加追问功能
3、增加反馈功能
（欢迎大家使用并反馈。）`);
						}}
					>
						<div>查阅最新更新内容</div>
					</button>
				</div>

				{#if $config?.features?.enable_version_update_check}
					<button
						class=" text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-850 dark:hover:bg-gray-800 transition rounded-lg font-medium"
						on:click={() => {
							checkForVersionUpdates();
						}}
					>
						{$i18n.t('Check for updates')}
					</button>
				{/if}
			</div>
		</div>

		<hr class=" border-gray-100 dark:border-gray-850" />

		<div class="text-sm text-gray-700 dark:text-gray-200 space-y-3">
			<div>
				<p class="mb-2">各位同事好，ZeroErr GPT 售后内测版 v1.2.0已上线，可无内网限制访问：</p>
				<p class="mb-2">👉 固定地址：<a href="https://gpt.zeroerr.com" target="_blank" class="text-blue-600 dark:text-blue-400 underline">https://gpt.zeroerr.com</a></p>
			</div>

			<div>
				<p class="mb-2">相比v1.1.8版本GPT，v1.2.0版本做了以下改进：</p>
				<ol class="list-decimal list-inside space-y-1 ml-4">
					<li>改变了网站的架构，可以支持更多的定制化开发，方便嵌入更多功能</li>
					<li>增加追问功能</li>
					<li>增加反馈功能</li>
				</ol>
			</div>

			<div>
				<p class="text-xs text-gray-500 dark:text-gray-400">（欢迎大家使用并反馈。）</p>
			</div>
		</div>

		<hr class=" border-gray-100 dark:border-gray-850" />
	</div>
</div>
