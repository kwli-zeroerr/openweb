import { browser, dev } from '$app/environment';
// Globals provided via Vite define
declare const APP_VERSION: string;
declare const APP_BUILD_HASH: string;
// import { version } from '../../package.json';

export const APP_NAME = 'Open WebUI';

export const WEBUI_HOSTNAME = browser ? (dev ? `${location.hostname}:5173` : location.hostname) : '';

// DEV 下走 Vite 代理，PROD 用相对路径让 nginx 代理
const getApiBaseUrl = () => {
  if (browser && dev) return '';
  return ''; // 生产环境使用相对路径，让 nginx 代理到后端
};

export const WEBUI_BASE_URL = getApiBaseUrl();
export const WEBUI_API_BASE_URL = WEBUI_BASE_URL ? `${WEBUI_BASE_URL}/api/v1` : '/api/v1';
export const API_BASE_URL = WEBUI_BASE_URL; // 兼容性别名

export const OLLAMA_API_BASE_URL = WEBUI_BASE_URL ? `${WEBUI_BASE_URL}/ollama` : '/ollama';
export const OPENAI_API_BASE_URL = WEBUI_BASE_URL ? `${WEBUI_BASE_URL}/openai` : '/openai';
export const AUDIO_API_BASE_URL = WEBUI_BASE_URL ? `${WEBUI_BASE_URL}/api/v1/audio` : '/api/v1/audio';
export const IMAGES_API_BASE_URL = WEBUI_BASE_URL ? `${WEBUI_BASE_URL}/api/v1/images` : '/api/v1/images';
export const RETRIEVAL_API_BASE_URL = WEBUI_BASE_URL ? `${WEBUI_BASE_URL}/api/v1/retrieval` : '/api/v1/retrieval';

export const WEBUI_VERSION = APP_VERSION;
export const WEBUI_BUILD_HASH = APP_BUILD_HASH;
export const REQUIRED_OLLAMA_VERSION = '0.1.16';

export const SUPPORTED_FILE_TYPE = [
	'application/epub+zip',
	'application/pdf',
	'text/plain',
	'text/csv',
	'text/xml',
	'text/html',
	'text/x-python',
	'text/css',
	'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
	'application/octet-stream',
	'application/x-javascript',
	'text/markdown',
	'audio/mpeg',
	'audio/wav',
	'audio/ogg',
	'audio/x-m4a'
];

export const SUPPORTED_FILE_EXTENSIONS = [
	'md',
	'rst',
	'go',
	'py',
	'java',
	'sh',
	'bat',
	'ps1',
	'cmd',
	'js',
	'ts',
	'css',
	'cpp',
	'hpp',
	'h',
	'c',
	'cs',
	'htm',
	'html',
	'sql',
	'log',
	'ini',
	'pl',
	'pm',
	'r',
	'dart',
	'dockerfile',
	'env',
	'php',
	'hs',
	'hsc',
	'lua',
	'nginxconf',
	'conf',
	'm',
	'mm',
	'plsql',
	'perl',
	'rb',
	'rs',
	'db2',
	'scala',
	'bash',
	'swift',
	'vue',
	'svelte',
	'doc',
	'docx',
	'pdf',
	'csv',
	'txt',
	'xls',
	'xlsx',
	'pptx',
	'ppt',
	'msg'
];

export const PASTED_TEXT_CHARACTER_LIMIT = 1000;

// Source: https://kit.svelte.dev/docs/modules#$env-static-public
// This feature, akin to $env/static/private, exclusively incorporates environment variables
// that are prefixed with config.kit.env.publicPrefix (usually set to PUBLIC_).
// Consequently, these variables can be securely exposed to client-side code.
