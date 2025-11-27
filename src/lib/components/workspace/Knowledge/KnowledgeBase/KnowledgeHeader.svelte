<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';

	const dispatch = createEventDispatcher();

	export let knowledge: any;
	export let i18n: any;

	let debounceTimeout: any = null;

	// 获取i18n的t方法
	const t = (i18n as any)?.t || ((key: string) => key);

	// 防抖处理知识库信息更新
	const changeDebounceHandler = () => {
		console.log('debounce');
		if (debounceTimeout) {
			clearTimeout(debounceTimeout);
		}

		debounceTimeout = setTimeout(() => {
			if (knowledge.name.trim() === '' || knowledge.description.trim() === '') {
				dispatch('error', { message: t('Please fill in all fields.') });
				return;
			}

			dispatch('updateKnowledge', {
				name: knowledge.name,
				description: knowledge.description,
				access_control: knowledge.access_control
			});
		}, 1000);
	};

	// 显示访问控制模态框
	const showAccessControl = () => {
		dispatch('showAccessControl');
	};
</script>

<div class="w-full mb-2.5">
	<div class=" flex w-full">
		<div class="flex-1">
			<div class="flex items-center justify-between w-full px-0.5 mb-1">
				<div class="w-full">
					<input
						type="text"
						class="text-left w-full font-semibold text-2xl font-primary bg-transparent outline-hidden"
						bind:value={knowledge.name}
              placeholder={t('Knowledge Name')}
						on:input={() => {
							changeDebounceHandler();
						}}
					/>
				</div>

				<div class="self-center shrink-0 flex items-center gap-2">
					<button
						class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
						type="button"
						on:click={showAccessControl}
					>
						<LockClosed strokeWidth="2.5" className="size-3.5" />

						<div class="text-sm font-medium shrink-0">
							{t('Access')}
						</div>
					</button>
				</div>
			</div>

			<div class="flex w-full px-1">
				<input
					type="text"
					class="text-left text-xs w-full text-gray-500 bg-transparent outline-hidden"
					bind:value={knowledge.description}
              placeholder={t('Knowledge Description')}
					on:input={() => {
						changeDebounceHandler();
					}}
				/>
			</div>
		</div>
	</div>
</div>
