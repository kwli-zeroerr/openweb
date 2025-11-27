import { WEBUI_API_BASE_URL } from '$lib/constants';
import { splitStream } from '$lib/utils';

export const uploadFile = async (token: string, file: File, metadata?: object | null) => {
	const data = new FormData();
	data.append('file', file);
	if (metadata) {
		data.append('metadata', JSON.stringify(metadata));
	}

	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		},
		body: data
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	if (res) {
		const status = await getFileProcessStatus(token, res.id);

		if (status && status.ok) {
			const reader = status.body
				.pipeThrough(new TextDecoderStream())
				.pipeThrough(splitStream('\n'))
				.getReader();

			while (true) {
				const { value, done } = await reader.read();
				if (done) {
					break;
				}

				try {
					let lines = value.split('\n');

					for (const line of lines) {
						if (line !== '') {
							console.log(line);
							if (line === 'data: [DONE]') {
								console.log(line);
							} else {
								let data = JSON.parse(line.replace(/^data: /, ''));
								console.log(data);

								if (data?.error) {
									console.error(data.error);
									res.error = data.error;
								}
							}
						}
					}
				} catch (error) {
					console.log(error);
				}
			}
		}
	}

	if (error) {
		throw error;
	}

	return res;
};

export const getFileProcessStatus = async (token: string, id: string) => {
	const queryParams = new URLSearchParams();
	queryParams.append('stream', 'true');

	let error = null;
	const res = await fetch(`${WEBUI_API_BASE_URL}/files/${id}/process/status?${queryParams}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		}
	}).catch((err) => {
		error = err.detail;
		console.error(err);
		return null;
	});

	if (error) {
		throw error;
	}

	return res;
};

export const uploadDir = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/upload/dir`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFiles = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFileById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFileMetadataById = async (token: string, id: string, metadata: object) => {
	let error = null;

	console.log('API call - updateFileMetadataById:', { id, metadata });

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/${id}/metadata/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(metadata)
	})
		.then(async (res) => {
			console.log('API response status:', res.status);
			if (!res.ok) {
				const errorData = await res.json();
				console.error('API error response:', errorData);
				throw errorData;
			}
			return res.json();
		})
		.then((json) => {
			console.log('API success response:', json);
			return json;
		})
		.catch((err) => {
			console.error('API call error:', err);
			error = err.detail || err.message || 'Unknown error';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFileById = async (token: string, fileId: string, file: File, metadata?: object) => {
	let error = null;

	console.log('API call - updateFileById:', { fileId, fileName: file.name, metadata });

	const formData = new FormData();
	formData.append('file', file);
	if (metadata) {
		formData.append('metadata', JSON.stringify(metadata));
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/${fileId}/update`, {
		method: 'POST',
		headers: {
			authorization: `Bearer ${token}`
		},
		body: formData
	})
		.then(async (res) => {
			console.log('API response status:', res.status);
			if (!res.ok) {
				const errorData = await res.json();
				console.error('API error response:', errorData);
				throw errorData;
			}
			return res.json();
		})
		.then((json) => {
			console.log('API success response:', json);
			return json;
		})
		.catch((err) => {
			console.error('API call error:', err);
			error = err.detail || err.message || 'Unknown error';
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFileDataContentById = async (token: string, id: string, content: string, ocrTaskId?: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/${id}/data/content/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			content: content,
			ocr_task_id: ocrTaskId || undefined
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFileContentById = async (id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/${id}/content`, {
		method: 'GET',
		headers: {
			Accept: 'application/json'
		},
		credentials: 'include'
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return await res.blob();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);

			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteFileById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/${id}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteAllFiles = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/all`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const extractZipFile = async (token: string, zipPath: string, extractTo?: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/files/extract-zip`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			zip_path: zipPath,
			extract_to: extractTo
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail || err.message || 'Unknown error';
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
