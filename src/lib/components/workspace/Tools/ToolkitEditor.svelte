<script>
	import { getContext, onMount, tick } from 'svelte';

	const i18n = getContext('i18n');

	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { getGroups } from '$lib/apis/groups';

	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import Switch from '$lib/components/common/Switch.svelte';

	let formElement = null;
	let loading = false;

	let showConfirm = false;
	let showAccessControlModal = false;

	export let edit = false;
	export let clone = false;

	export let onSave = () => {};

	export let id = '';
	export let name = '';
	export let meta = {
		description: ''
	};
	export let content = '';
	export let accessControl = {};
	export let isDefaultForAllUsers = false;
	export let defaultForGroupIds = [];

	let _content = '';
	let allGroups = [];
	let groupsLoading = false;

	$: if (content) {
		updateContent();
	}

	// 互斥逻辑：当 isDefaultForAllUsers 变为 true 时，清空 specific groups
	let previousIsDefaultForAllUsers = isDefaultForAllUsers;
	$: {
		if (isDefaultForAllUsers && !previousIsDefaultForAllUsers && (defaultForGroupIds || []).length > 0) {
			// 从 false 变为 true，清空 specific groups
			defaultForGroupIds = [];
		}
		previousIsDefaultForAllUsers = isDefaultForAllUsers;
	}

	const updateContent = () => {
		_content = content;
	};

	$: if (name && !edit && !clone) {
		id = name.replace(/\s+/g, '_').toLowerCase();
	}

	let codeEditor;
	let boilerplate = `import os
import requests
from datetime import datetime
from pydantic import BaseModel, Field

class Tools:
    def __init__(self):
        pass

    # Add your custom tools using pure Python code here, make sure to add type hints and descriptions
	
    def get_user_name_and_email_and_id(self, __user__: dict = {}) -> str:
        """
        Get the user name, Email and ID from the user object.
        """

        # Do not include a descrption for __user__ as it should not be shown in the tool's specification
        # The session user object will be passed as a parameter when the function is called

        print(__user__)
        result = ""

        if "name" in __user__:
            result += f"User: {__user__['name']}"
        if "id" in __user__:
            result += f" (ID: {__user__['id']})"
        if "email" in __user__:
            result += f" (Email: {__user__['email']})"

        if result == "":
            result = "User: Unknown"

        return result

    def get_current_time(self) -> str:
        """
        Get the current time in a more human-readable format.
        """

        now = datetime.now()
        current_time = now.strftime("%I:%M:%S %p")  # Using 12-hour format with AM/PM
        current_date = now.strftime(
            "%A, %B %d, %Y"
        )  # Full weekday, month name, day, and year

        return f"Current Date and Time = {current_date}, {current_time}"

    def calculator(
        self,
        equation: str = Field(
            ..., description="The mathematical equation to calculate."
        ),
    ) -> str:
        """
        Calculate the result of an equation.
        """

        # Avoid using eval in production code
        # https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html
        try:
            result = eval(equation)
            return f"{equation} = {result}"
        except Exception as e:
            print(e)
            return "Invalid equation"

    def get_current_weather(
        self,
        city: str = Field(
            "New York, NY", description="Get the current weather for a given city."
        ),
    ) -> str:
        """
        Get the current weather for a given city.
        """

        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return (
                "API key is not set in the environment variable 'OPENWEATHER_API_KEY'."
            )

        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",  # Optional: Use 'imperial' for Fahrenheit
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            data = response.json()

            if data.get("cod") != 200:
                return f"Error fetching weather data: {data.get('message')}"

            weather_description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]

            return f"Weather in {city}: {temperature}°C"
        except requests.RequestException as e:
            return f"Error fetching weather data: {str(e)}"
`;

	const saveHandler = async () => {
		loading = true;
		onSave({
			id,
			name,
			meta,
			content,
			access_control: accessControl,
			is_default_for_all_users: isDefaultForAllUsers,
			default_for_group_ids: defaultForGroupIds || []
		});
	};

	// 加载权限组列表
	const loadGroups = async () => {
		if ($user?.role !== 'admin') {
			return; // 只有管理员可以设置按组默认工具
		}
		groupsLoading = true;
		try {
			const token = localStorage.token || '';
			const response = await getGroups(token);
			allGroups = Array.isArray(response) ? response : [];
		} catch (error) {
			console.error('Failed to load groups:', error);
			allGroups = [];
		} finally {
			groupsLoading = false;
		}
	};

	onMount(() => {
		loadGroups();
	});

	const submitHandler = async () => {
		if (codeEditor) {
			content = _content;
			await tick();

			const res = await codeEditor.formatPythonCodeHandler();
			await tick();

			content = _content;
			await tick();

			if (res) {
				saveHandler();
			}
		}
	};
</script>

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessControl
	accessRoles={['read', 'write']}
	allowPublic={$user?.permissions?.sharing?.public_tools || $user?.role === 'admin'}
/>

<div class=" flex flex-col justify-between w-full overflow-y-auto h-full">
	<div class="mx-auto w-full md:px-0 h-full">
		<form
			bind:this={formElement}
			class=" flex flex-col max-h-[100dvh] h-full"
			on:submit|preventDefault={() => {
				if (edit) {
					submitHandler();
				} else {
					showConfirm = true;
				}
			}}
		>
			<div class="flex flex-col flex-1 overflow-auto h-0 rounded-lg">
				<div class="w-full mb-2 flex flex-col gap-0.5">
					<div class="flex w-full items-center">
						<div class=" shrink-0 mr-2">
							<Tooltip content={$i18n.t('Back')}>
								<button
									class="w-full text-left text-sm py-1.5 px-1 rounded-lg dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-gray-850"
									on:click={() => {
										goto('/workspace/tools');
									}}
									type="button"
								>
									<ChevronLeft strokeWidth="2.5" />
								</button>
							</Tooltip>
						</div>

						<div class="flex-1">
							<Tooltip content={$i18n.t('e.g. My Tools')} placement="top-start">
								<input
									class="w-full text-2xl font-medium bg-transparent outline-hidden font-primary"
									type="text"
									placeholder={$i18n.t('Tool Name')}
									bind:value={name}
									required
								/>
							</Tooltip>
						</div>

						<div class="self-center shrink-0">
							<button
								class="bg-gray-50 hover:bg-gray-100 text-black dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-white transition px-2 py-1 rounded-full flex gap-1 items-center"
								type="button"
								on:click={() => {
									showAccessControlModal = true;
								}}
							>
								<LockClosed strokeWidth="2.5" className="size-3.5" />

								<div class="text-sm font-medium shrink-0">
									{$i18n.t('Access')}
								</div>
							</button>
						</div>
					</div>

					<div class=" flex gap-2 px-1 items-center">
						{#if edit}
							<div class="text-sm text-gray-500 shrink-0">
								{id}
							</div>
						{:else}
							<Tooltip className="w-full" content={$i18n.t('e.g. my_tools')} placement="top-start">
								<input
									class="w-full text-sm disabled:text-gray-500 bg-transparent outline-hidden"
									type="text"
									placeholder={$i18n.t('Tool ID')}
									bind:value={id}
									required
									disabled={edit}
								/>
							</Tooltip>
						{/if}

						<Tooltip
							className="w-full self-center items-center flex"
							content={$i18n.t('e.g. Tools for performing various operations')}
							placement="top-start"
						>
							<input
								class="w-full text-sm bg-transparent outline-hidden"
								type="text"
								placeholder={$i18n.t('Tool Description')}
								bind:value={meta.description}
								required
							/>
						</Tooltip>
					</div>

					{#if edit && $user?.role === 'admin'}
						<div class="flex flex-col gap-2 px-1 mb-2">
							<!-- 全局默认工具设置 -->
							<div class="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
								<div class="flex flex-col flex-1 mr-4">
									<div class="flex items-center gap-2 mb-1">
										<div class="text-sm font-semibold text-blue-900 dark:text-blue-100">
											{$i18n.t('Set as default tool for all users')}
										</div>
										<div class="px-2 py-0.5 text-xs font-medium bg-blue-200 dark:bg-blue-800 text-blue-800 dark:text-blue-200 rounded">
											{$i18n.t('Admin Only')}
										</div>
									</div>
									<div class="text-xs text-blue-700 dark:text-blue-300">
										{$i18n.t('When enabled, this tool will be automatically selected for all users in chat. Only administrators can modify this setting.')}
									</div>
								</div>
								<Switch 
									bind:state={isDefaultForAllUsers}
									on:change={() => {
										// 如果启用了 for all users，清空 specific groups
										if (isDefaultForAllUsers) {
											defaultForGroupIds = [];
										}
									}}
								/>
							</div>
							
							<!-- 按权限组设置默认工具 -->
							<div class="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
								<div class="flex items-center gap-2 mb-2">
									<div class="text-sm font-semibold text-green-900 dark:text-green-100">
										{$i18n.t('Set as default tool for specific groups')}
									</div>
									<div class="px-2 py-0.5 text-xs font-medium bg-green-200 dark:bg-green-800 text-green-800 dark:text-green-200 rounded">
										{$i18n.t('Admin Only')}
									</div>
								</div>
								<div class="text-xs text-green-700 dark:text-green-300 mb-3">
									{$i18n.t('Select permission groups for which this tool will be automatically selected. Users in these groups will have this tool enabled by default.')}
								</div>
								{#if groupsLoading}
									<div class="text-xs text-gray-500">{$i18n.t('Loading groups...')}</div>
								{:else if allGroups.length === 0}
									<div class="text-xs text-gray-500">{$i18n.t('No groups available')}</div>
								{:else}
									<div class="flex flex-wrap gap-2">
										{#each allGroups as group}
											{@const isSelected = (defaultForGroupIds || []).includes(group.id)}
											<button
												type="button"
												class="px-3 py-1.5 text-xs rounded-lg border transition
													{isSelected 
														? 'bg-green-500 text-white border-green-600 dark:bg-green-600 dark:border-green-500' 
														: 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:border-green-500 dark:hover:border-green-400'}"
												on:click={() => {
													if (!defaultForGroupIds) {
														defaultForGroupIds = [];
													}
													if (isSelected) {
														defaultForGroupIds = defaultForGroupIds.filter(id => id !== group.id);
													} else {
														// 如果选择了 specific groups，关闭 for all users
														if (isDefaultForAllUsers) {
															isDefaultForAllUsers = false;
														}
														defaultForGroupIds = [...defaultForGroupIds, group.id];
													}
													defaultForGroupIds = [...defaultForGroupIds]; // 触发响应式更新
												}}
											>
												<div class="flex flex-col items-start">
													<span>{group.name || group.id}</span>
													<span class="text-[10px] opacity-60 mt-0.5">{group.id}</span>
												</div>
											</button>
										{/each}
									</div>
									{#if (defaultForGroupIds || []).length > 0}
										<div class="mt-2 text-xs text-green-600 dark:text-green-400">
											{$i18n.t('Selected')}: {(defaultForGroupIds || []).length} {$i18n.t('group(s)')}
										</div>
									{/if}
								{/if}
							</div>
						</div>
					{/if}
				</div>

				<div class="mb-2 flex-1 overflow-auto h-0 rounded-lg">
					<CodeEditor
						bind:this={codeEditor}
						value={content}
						lang="python"
						{boilerplate}
						onChange={(e) => {
							_content = e;
						}}
						onSave={async () => {
							if (formElement) {
								formElement.requestSubmit();
							}
						}}
					/>
				</div>

				<div class="pb-3 flex justify-between">
					<div class="flex-1 pr-3">
						<div class="text-xs text-gray-500 line-clamp-2">
							<span class=" font-semibold dark:text-gray-200">{$i18n.t('Warning:')}</span>
							{$i18n.t('Tools are a function calling system with arbitrary code execution')} <br />—
							<span class=" font-medium dark:text-gray-400"
								>{$i18n.t(`don't install random tools from sources you don't trust.`)}</span
							>
						</div>
					</div>

					<button
						class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full"
						type="submit"
					>
						{$i18n.t('Save')}
					</button>
				</div>
			</div>
		</form>
	</div>
</div>

<ConfirmDialog
	bind:show={showConfirm}
	on:confirm={() => {
		submitHandler();
	}}
>
	<div class="text-sm text-gray-500">
		<div class=" bg-yellow-500/20 text-yellow-700 dark:text-yellow-200 rounded-lg px-4 py-3">
			<div>{$i18n.t('Please carefully review the following warnings:')}</div>

			<ul class=" mt-1 list-disc pl-4 text-xs">
				<li>
					{$i18n.t('Tools have a function calling system that allows arbitrary code execution.')}
				</li>
				<li>{$i18n.t('Do not install tools from sources you do not fully trust.')}</li>
			</ul>
		</div>

		<div class="my-3">
			{$i18n.t(
				'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
			)}
		</div>
	</div>
</ConfirmDialog>
