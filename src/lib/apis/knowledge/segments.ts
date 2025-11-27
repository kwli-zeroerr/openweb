import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface SegmentMeta {
	id: string;
	heading: string;
	level: number;
	file: string;
	preview: string;
	order: number;
}

export interface SegmentManifest {
	knowledge_id: string;
	ocr_task_id: string;
	source_file: string;
	created_at: string;
	segment_count: number;
	segments: SegmentMeta[];
}

type AutoSegmentPayload = {
	ocr_task_id: string;
	source_file?: string;
	max_heading_level?: number;
	overwrite?: boolean;
};

const handleResponse = async (res: Response) => {
	if (!res.ok) {
		let detail = res.statusText;
		try {
			const body = await res.json();
			detail = body?.detail || JSON.stringify(body);
		} catch {
			// ignore json parse errors
		}
		throw new Error(detail);
	}
	return res.json();
};

export const autoSegmentOCR = async (
	token: string,
	knowledgeId: string,
	payload: AutoSegmentPayload
): Promise<{ status: string; segment_count: number; manifest: SegmentManifest }> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/segments/auto`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(payload)
	});

	return handleResponse(res);
};

export const fetchOCRSegments = async (
	token: string,
	knowledgeId: string,
	ocrTaskId: string
): Promise<{ status: string; segment_count: number; manifest: SegmentManifest }> => {
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/segments?ocr_task_id=${encodeURIComponent(ocrTaskId)}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	);

	return handleResponse(res);
};

export const deleteOCRSegments = async (
	token: string,
	knowledgeId: string,
	ocrTaskId: string
): Promise<{ status: string; message: string }> => {
	const res = await fetch(
		`${WEBUI_API_BASE_URL}/knowledge/${knowledgeId}/segments?ocr_task_id=${encodeURIComponent(ocrTaskId)}`,
		{
			method: 'DELETE',
			headers: {
				Accept: 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	);

	return handleResponse(res);
};

