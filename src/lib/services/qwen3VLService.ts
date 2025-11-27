// Qwen3 VL API 服务
export class Qwen3VLService {
	private apiKey: string;
	private baseUrl: string;

	constructor(apiKey: string = 'sk-6f1ba80e09af4103b686fbe523d8f93c') {
		this.apiKey = apiKey;
		this.baseUrl = 'https://dashscope.aliyuncs.com/compatible-mode/v1';
	}

	// 调用 Qwen3 VL API 进行格式转换（支持图片输入）
	async convertPageContent(pageContent: string, pageNumber: number): Promise<string> {
		try {
			// 检查输入是否为图片（base64 data URL）
			const isImage = pageContent.startsWith('data:image/');
			
			const response = await fetch(`${this.baseUrl}/chat/completions`, {
				method: 'POST',
				headers: {
					'Authorization': `Bearer ${this.apiKey}`,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					model: 'qwen3-vl-plus',
					messages: [
						{
							role: 'user',
							content: isImage ? [
								{
									type: 'image_url',
									image_url: {
										url: pageContent
									}
								},
								{
									type: 'text',
									text: `请对以下第${pageNumber}页的PDF内容进行格式转换和优化，使其结构更清晰，内容更易读。

请按照以下要求进行转换：
1. 保持原文的核心信息不变
2. 优化段落结构，使其更易阅读
3. 提取关键信息并格式化
4. 去除冗余内容
5. 使用清晰的标题和子标题
6. 保持逻辑顺序

请直接返回转换后的内容，不要包含任何解释性文字。`
								}
							] : [
								{
									type: 'text',
									text: `请对以下第${pageNumber}页的内容进行格式转换和优化，使其结构更清晰，内容更易读：

${pageContent}

请按照以下要求进行转换：
1. 保持原文的核心信息不变
2. 优化段落结构，使其更易阅读
3. 提取关键信息并格式化
4. 去除冗余内容
5. 使用清晰的标题和子标题
6. 保持逻辑顺序`
								}
							]
						}
					],
					stream: false,
					extra_body: {
						enable_thinking: true,
						thinking_budget: 81920
					}
				})
			});

			if (!response.ok) {
				throw new Error(`API 调用失败: ${response.status} ${response.statusText}`);
			}

			const data = await response.json();
			
			if (data.choices && data.choices[0] && data.choices[0].message) {
				return data.choices[0].message.content;
			} else {
				throw new Error('API 响应格式错误');
			}
		} catch (error) {
			console.error('Qwen3 VL API 调用错误:', error);
			throw error;
		}
	}

	// 流式调用 Qwen3 VL API
	async convertPageContentStream(
		pageContent: string, 
		pageNumber: number, 
		onChunk: (chunk: string) => void,
		onComplete: (fullContent: string) => void,
		onError: (error: Error) => void
	): Promise<void> {
		try {
			const response = await fetch(`${this.baseUrl}/chat/completions`, {
				method: 'POST',
				headers: {
					'Authorization': `Bearer ${this.apiKey}`,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					model: 'qwen3-vl-plus',
					messages: [
						{
							role: 'user',
							content: [
								{
									type: 'text',
									text: `请对以下第${pageNumber}页的内容进行格式转换和优化，使其结构更清晰，内容更易读：

${pageContent}

请按照以下要求进行转换：
1. 保持原文的核心信息不变
2. 优化段落结构，使其更易阅读
3. 提取关键信息并格式化
4. 去除冗余内容
5. 使用清晰的标题和子标题
6. 保持逻辑顺序`

								}
							]
						}
					],
					stream: true,
					extra_body: {
						enable_thinking: true,
						thinking_budget: 81920
					}
				})
			});

			if (!response.ok) {
				throw new Error(`API 调用失败: ${response.status} ${response.statusText}`);
			}

			const reader = response.body?.getReader();
			if (!reader) {
				throw new Error('无法读取响应流');
			}

			const decoder = new TextDecoder();
			let fullContent = '';
			let reasoningContent = '';
			let isAnswering = false;

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				const chunk = decoder.decode(value);
				const lines = chunk.split('\n');

				for (const line of lines) {
					if (line.startsWith('data: ')) {
						const data = line.slice(6);
						if (data === '[DONE]') {
							onComplete(fullContent);
							return;
						}

						try {
							const parsed = JSON.parse(data);
							if (parsed.choices && parsed.choices[0]) {
								const delta = parsed.choices[0].delta;
								
								// 处理思考过程
								if (delta.reasoning_content) {
									reasoningContent += delta.reasoning_content;
								} else if (delta.content) {
									// 开始回复
									if (!isAnswering) {
										isAnswering = true;
									}
									
									// 处理回复内容
									fullContent += delta.content;
									onChunk(delta.content);
								}
							}
						} catch (e) {
							// 忽略解析错误
						}
					}
				}
			}

			onComplete(fullContent);
		} catch (error) {
			console.error('Qwen3 VL 流式 API 调用错误:', error);
			onError(error as Error);
		}
	}

	// 测试 API 连接
	async testConnection(): Promise<boolean> {
		try {
			const response = await fetch(`${this.baseUrl}/chat/completions`, {
				method: 'POST',
				headers: {
					'Authorization': `Bearer ${this.apiKey}`,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					model: 'qwen3-vl-plus',
					messages: [
						{
							role: 'user',
							content: [
								{
									type: 'text',
									text: 'Hello, this is a test message.'
								}
							]
						}
					],
					max_tokens: 10
				})
			});

			return response.ok;
		} catch (error) {
			console.error('API 连接测试失败:', error);
			return false;
		}
	}
}

// 创建单例实例
export const qwen3VLService = new Qwen3VLService();
