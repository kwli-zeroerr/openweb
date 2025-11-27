import type { WorkflowNode, WorkflowConnection } from '../types';
import type { RagFlowRetrievalResponse } from '$lib/apis/agent';

/**
 * 收集与指定检索节点直连的数据源节点中的 dataset_ids
 */
export function collectLinkedDatasetIds(
  retrievalNodeId: string,
  nodes: WorkflowNode[],
  connections: WorkflowConnection[]
): string[] {
  const linked = new Set<string>();
  for (const c of connections) {
    if (c.from === retrievalNodeId || c.to === retrievalNodeId) {
      const otherId = c.from === retrievalNodeId ? c.to : c.from;
      const other = nodes.find((n) => n.id === otherId);
      if (other && other.type === 'dataSource') {
        const ds: string[] = (other as any).config?.selected_datasets || [];
        for (const id of ds) linked.add(id);
      }
    }
  }
  return Array.from(linked);
}

/**
 * 根据检索配置拼接 retrieved_context
 */
export function assembleRetrievedContext(
  retrievalConfig: any,
  result: RagFlowRetrievalResponse
): string {
  const ctxTopK = retrievalConfig.context_top_k || 3;
  const ctxJoin = typeof retrievalConfig.context_join === 'string' ? retrievalConfig.context_join : '\n---\n';
  const ctxMax = retrievalConfig.context_max_chars || 2000;
  const useHl = retrievalConfig.context_use_highlight === true;
  const incSrc = retrievalConfig.context_include_source !== false;
  const incScore = retrievalConfig.context_include_score === true;

  const picked = (result.documents || []).slice(0, ctxTopK);
  let assembled = picked
    .map((d) => {
      const meta: any = (d as any).metadata || {};
      const content = useHl && meta.highlight ? meta.highlight : (d as any).content || '';
      const parts: string[] = [];
      parts.push(content);
      if (incSrc && meta.document_name) parts.push(`【来源】${meta.document_name}`);
      if (incScore && meta.similarity != null) parts.push(`【分数】${Number(meta.similarity).toFixed(3)}`);
      return parts.join('\n');
    })
    .join(ctxJoin);
  if (assembled.length > ctxMax) assembled = assembled.slice(0, ctxMax) + '...';
  return assembled;
}


