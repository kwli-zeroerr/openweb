import { generateChatOrCompletion } from '../adapters/llm.adapter';

export function renderPrompt(template: string, vars: Record<string, string>): string {
  let out = template || '';
  for (const [k, v] of Object.entries(vars)) {
    out = out.replaceAll(`{${k}}`, v ?? '');
  }
  return out;
}

export async function runLLM(
  model: string,
  prompt: string,
  temperature: number,
  max_tokens: number
): Promise<string | null> {
  return await generateChatOrCompletion({ model, prompt, temperature, max_tokens });
}


