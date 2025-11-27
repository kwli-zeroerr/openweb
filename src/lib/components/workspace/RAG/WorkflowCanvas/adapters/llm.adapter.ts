import { WEBUI_API_BASE_URL } from '$lib/constants';
import type { ModelsResponse } from '$lib/apis/rag';

export async function fetchModelsNormalized(): Promise<ModelsResponse> {
  // 复用 ragAPI 的多端点逻辑：前端统一从 /api/v1/models 获取
  // 这里做一次兜底（避免依赖具体客户端）
  const candidates = [
    `${WEBUI_API_BASE_URL}/api/v1/models`,
    `${WEBUI_API_BASE_URL}/models`,
  ];
  for (const url of candidates) {
    try {
      const resp = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if (!resp.ok) continue;
      const ct = resp.headers.get('content-type') || '';
      if (!ct.includes('application/json')) continue;
      const data = await resp.json();
      const arr = Array.isArray(data?.models) ? data.models : Array.isArray(data?.data) ? data.data : Array.isArray(data) ? data : [];
      const models = arr.map((m: any) => ({ id: m.id ?? m.name ?? 'model', name: m.name ?? m.id ?? 'model', provider: m.provider ?? 'unknown', description: m.description ?? '', capabilities: m.capabilities ?? {} }));
      return { models, total: models.length };
    } catch (_) {}
  }
  return { models: [], total: 0 };
}

export async function generateChatOrCompletion(params: { model: string; prompt: string; temperature: number; max_tokens: number }): Promise<string | null> {
  const auth = localStorage.token || '';
  const headers: Record<string,string> = { 'Accept': 'application/json', 'Content-Type': 'application/json' };
  if (auth) headers['Authorization'] = `Bearer ${auth}`;

  const base = String(WEBUI_API_BASE_URL).replace(/\/api\/v1\/api\/v1\/?$/, '/api/v1').replace(/\/$/, '');
  try {
    const r = await fetch(`${base}/chat/completions`, { method: 'POST', headers, body: JSON.stringify({ model: params.model, messages: [{ role: 'user', content: params.prompt }], temperature: params.temperature, max_tokens: params.max_tokens }) });
    if (r.ok) { const d = await r.json(); const t = d?.choices?.[0]?.message?.content; if (t) return t; }
  } catch(_) {}
  try {
    const r = await fetch(`${base}/completions`, { method: 'POST', headers, body: JSON.stringify({ model: params.model, prompt: params.prompt, temperature: params.temperature, max_tokens: params.max_tokens }) });
    if (r.ok) { const d = await r.json(); const t = d?.choices?.[0]?.text; if (t) return t; }
  } catch(_) {}
  return null;
}

