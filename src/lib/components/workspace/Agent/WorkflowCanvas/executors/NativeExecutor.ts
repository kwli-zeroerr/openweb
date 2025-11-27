import type { Executor, ExecutionInput, ExecutionOutput } from "./Executor";
import { collectLinkedDatasetIds, assembleRetrievedContext } from "../services/retrievalService";
import type { Message, WorkflowNode } from "../types";
import { retrieval } from "../adapters/ragflow.adapter";
import { renderPrompt, runLLM } from "../services/llmService";

export class NativeExecutor implements Executor {
  async execute(input: ExecutionInput): Promise<ExecutionOutput> {
    const { question, nodes, connections } = input;
    const t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    const timings: Record<string, number> = {};
    const messages: Record<string, Record<string, Message>> = {};
    const setMsg = (nodeId: string, key: string, msg: Message) => {
      if (!messages[nodeId]) messages[nodeId] = {};
      messages[nodeId][key] = msg;
    };
    const getUpstreamByType = (nodeId: string, type: WorkflowNode["type"]) => {
      const res: WorkflowNode[] = [];
      for (const c of connections) {
        if (c.from === nodeId || c.to === nodeId) {
          const otherId = c.from === nodeId ? c.to : c.from;
          const other = nodes.find(n => n.id === otherId);
          if (other && other.type === type) res.push(other as any);
        }
      }
      return res;
    };
    
    // 根据 input_bindings 获取输入值（优先使用绑定，否则回退到默认逻辑）
    const getInputValue = (node: WorkflowNode, portKey: string, defaultValue: any): any => {
      const bindings = node.config?.input_bindings || {};
      const binding = bindings[portKey];
      if (binding && binding.includes('.')) {
        const [sourceNodeId, sourcePort] = binding.split('.');
        const sourceMsg = messages[sourceNodeId]?.[sourcePort];
        if (sourceMsg) return sourceMsg.payload;
      }
      return defaultValue;
    };

    // 先处理输入节点和数据源节点，产出初始消息
    for (const n of nodes) {
      if (n.type === "input") {
        const inputText = String(n.config?.user_input ?? "").trim();
        if (inputText) {
          setMsg(n.id, "user", { type: "user", payload: inputText });
        }
      } else if (n.type === "dataSource") {
        const dsIds = n.config?.selected_datasets || [];
        if (dsIds.length > 0) {
          setMsg(n.id, "datasets", { type: "json", payload: dsIds });
        }
      }
    }
    
    // 选择第一个检索节点
    const retrievalNode = nodes.find(n => n.type === "retrieval");
    if (!retrievalNode) {
      return { question, retrieved_context: null, llm_output: null, total: 0, documents: [], scores: [], messages };
    }

    // 收集与检索节点相连的数据源所选的 dataset ids
    let datasetIds = collectLinkedDatasetIds(retrievalNode.id, nodes as any, connections as any);
    // 优先从 input_bindings 获取 datasets
    const boundDatasets = getInputValue(retrievalNode, "datasets", null);
    if (boundDatasets && Array.isArray(boundDatasets)) {
      datasetIds = boundDatasets;
    }
    if (datasetIds.length === 0) {
      return { question, retrieved_context: null, llm_output: null, total: 0, documents: [], scores: [], messages };
    }
    const dsNode = getUpstreamByType(retrievalNode.id, "dataSource")[0];
    if (dsNode) setMsg(dsNode.id, "datasets", { type: "json", payload: datasetIds });

    // question 来源：优先从 input_bindings，否则从 input 节点，最后从顶部输入框
    let effectiveQuestion = getInputValue(retrievalNode, "question", null);
    if (!effectiveQuestion || typeof effectiveQuestion !== 'string') {
      const inputNode = getUpstreamByType(retrievalNode.id, "input")[0];
      const questionFromInput = String(inputNode?.config?.user_input ?? "").trim();
      effectiveQuestion = questionFromInput || question.trim();
      if (inputNode && questionFromInput) setMsg(inputNode.id, "user", { type: "user", payload: questionFromInput });
    } else {
      effectiveQuestion = String(effectiveQuestion).trim();
    }

    const cfg: any = retrievalNode.config || {};
    const tR0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    const ret = await retrieval({
      question: effectiveQuestion,
      dataset_ids: datasetIds,
      similarity_threshold: cfg.similarity_threshold,
      vector_similarity_weight: cfg.vector_similarity_weight,
      top_k: cfg.top_k,
      keyword: cfg.keyword,
      highlight: cfg.highlight
    });
    const tR1 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    timings.retrieval = Math.round(tR1 - tR0);

    // 组装 retrieved_context
    const tC0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    const assembled = assembleRetrievedContext(cfg, ret);
    const tC1 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    timings.context_assemble = Math.round(tC1 - tC0);
    setMsg(retrievalNode.id, "context", { type: "context", payload: assembled });

    // 若存在 LLM 节点，执行生成
    const llmNode = nodes.find(n => n.type === "llm");
    let llmOutput: string | null = null;
    if (llmNode) {
      const tL0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
      // 获取 question 和 context：优先从 input_bindings，否则使用默认值
      const llmQuestion = getInputValue(llmNode, "question", effectiveQuestion) || effectiveQuestion;
      const llmContext = getInputValue(llmNode, "context", assembled) || assembled;
      
      const tpl = String(
        llmNode.config?.prompt_template ||
        "请基于上下文回答问题\n问题: {question}\n上下文:\n{retrieved_context}"
      );
      const rendered = renderPrompt(tpl, { question: String(llmQuestion), retrieved_context: String(llmContext) });
      const modelId = String(llmNode.config?.model || "");
      const temp = Number(llmNode.config?.temperature ?? 0.7);
      const maxTok = Number(llmNode.config?.max_tokens ?? 2000);
      llmOutput = await runLLM(modelId, rendered, temp, maxTok);
      if (!llmOutput) llmOutput = rendered; // 兜底可视反馈
      const tL1 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
      timings.llm = Math.round(tL1 - tL0);
      setMsg(llmNode.id, "answer", { type: "text", payload: llmOutput });
    }

    const t1 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
    timings.total = Math.round(t1 - t0);

    return {
      question: effectiveQuestion,
      retrieved_context: assembled,
      llm_output: llmOutput,
      total: ret.total,
      documents: ret.documents,
      scores: ret.scores,
      timings,
      messages
    };
  }
}


