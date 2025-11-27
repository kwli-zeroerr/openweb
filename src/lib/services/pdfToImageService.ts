// PDF处理服务 - 将PDF页面转换为图片
// 使用后端API处理PDF转图片，避免前端PDF.js的复杂性

export class PDFToImageService {
	// 调用后端API将PDF页面转换为图片
	async convertPageToImage(file: any, pageNumber: number, knowledgeId: string): Promise<string> {
		try {
			// 使用知识库API端点
			const response = await fetch(`/api/v1/knowledge/${knowledgeId}/files/${file.id}/pdf-to-image?page=${pageNumber}`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				}
			});
			
			if (!response.ok) {
				throw new Error(`API调用失败: ${response.status}`);
			}
			
			// 获取base64图片数据
			const result = await response.json();
			return result.imageDataUrl;
			
		} catch (error) {
			console.error('PDF转图片API调用失败:', error);
			throw error;
		}
	}
}

// 创建单例实例
export const pdfToImageService = new PDFToImageService();
