/**
 * LangGraph 执行器
 * 
 * 将工作流图转换为 LangGraph StateGraph，支持：
 * - 多输入/多输出节点
 * - 条件路由（LLM -> 检索 or LLM -> LLM）
 * - 循环执行（检索 -> LLM -> 检索）
 * - 并行执行（多个检索节点）
 * 
 * 架构设计：
 * 1. 工作流图 -> LangGraph StateGraph 转换器
 * 2. 节点类型 -> LangGraph Node 映射
 * 3. 连接 -> LangGraph Edge/Condition 映射
 * 4. 状态管理：全局 State 存储所有节点的消息
 */

import type { Executor, ExecutionInput, ExecutionOutput } from "./Executor";
import type { WorkflowNode, WorkflowConnection, Message } from "../types";
import { retrieval } from "../adapters/ragflow.adapter";
import { renderPrompt, runLLM } from "../services/llmService";
import { assembleRetrievedContext, collectLinkedDatasetIds } from "../services/retrievalService";

/**
 * LangGraph 状态结构
 * 存储所有节点的输入/输出消息
 */
interface LangGraphState {
  // 节点ID -> 端口 -> 消息
  messages: Record<string, Record<string, Message>>;
  // 当前执行路径（用于调试）
  executionPath: string[];
  // 元数据
  metadata: {
    question: string;
    startTime: number;
    timings: Record<string, number>;
  };
}

/**
 * 节点执行上下文
 */
interface NodeExecutionContext {
  node: WorkflowNode;
  state: LangGraphState;
  nodes: WorkflowNode[];
  connections: WorkflowConnection[];
}

/**
 * LangGraph 执行器实现
 * 
 * 注意：这是一个前端实现，实际 LangGraph 需要在后端运行
 * 这里提供一个模拟实现，展示如何将工作流转换为图执行
 */
export class LangGraphExecutor implements Executor {
  async execute(input: ExecutionInput): Promise<ExecutionOutput> {
    const { question, nodes, connections } = input;
    const t0 = typeof performance !== 'undefined' ? performance.now() : Date.now();
    
    // 初始化状态
    const state: LangGraphState = {
      messages: {},
      executionPath: [],
      metadata: {
        question: question.trim(),
        startTime: t0,
        timings: {}
      }
    };

    // 构建执行图：拓扑排序 + BFS
    const executionOrder = this.buildExecutionOrder(nodes, connections);
    
    // 确保所有节点都被执行（包括没有连接的独立节点）
    const allNodeIds = new Set(nodes.map(n => n.id));
    const executedNodeIds = new Set(executionOrder);
    const isolatedNodes = nodes.filter(n => !executedNodeIds.has(n.id));
    
    // 将孤立节点添加到执行顺序的前面（先执行输入节点和数据源节点）
    const isolatedInputNodes = isolatedNodes.filter(n => n.type === "input" || n.type === "dataSource");
    const isolatedOtherNodes = isolatedNodes.filter(n => n.type !== "input" && n.type !== "dataSource");
    const finalExecutionOrder = [...isolatedInputNodes.map(n => n.id), ...executionOrder, ...isolatedOtherNodes.map(n => n.id)];
    
    console.log(`[LangGraphExecutor] 执行顺序:`, finalExecutionOrder);
    console.log(`[LangGraphExecutor] 孤立节点:`, isolatedNodes.map(n => `${n.type}:${n.id}`));
    
    // 按顺序执行节点
    for (const nodeId of finalExecutionOrder) {
      const node = nodes.find(n => n.id === nodeId);
      if (!node) continue;

      const ctx: NodeExecutionContext = { node, state, nodes, connections };
      
      // 执行节点
      const tNode0 = typeof performance !== 'undefined' ? performance.now() : Date.now();
      await this.executeNode(ctx);
      const tNode1 = typeof performance !== 'undefined' ? performance.now() : Date.now();
      
      state.metadata.timings[`node_${nodeId}`] = Math.round(tNode1 - tNode0);
      state.executionPath.push(nodeId);
    }

    // 提取最终结果
    const finalResult = this.extractFinalResult(state, nodes, connections);
    const t1 = typeof performance !== 'undefined' ? performance.now() : Date.now();
    finalResult.timings = {
      ...state.metadata.timings,
      total: Math.round(t1 - t0)
    };

    return finalResult;
  }

  /**
   * 构建执行顺序（拓扑排序）
   * 支持条件路由：如果节点有多个下游，根据条件选择
   */
  private buildExecutionOrder(
    nodes: WorkflowNode[],
    connections: WorkflowConnection[]
  ): string[] {
    // 构建邻接表
    const graph: Record<string, string[]> = {};
    const inDegree: Record<string, number> = {};
    
    nodes.forEach(n => {
      graph[n.id] = [];
      inDegree[n.id] = 0;
    });

    connections.forEach(conn => {
      // 只处理单向连接，且确保 from 和 to 都存在
      if (conn.type === "unidirectional" && conn.from && conn.to) {
        graph[conn.from] = graph[conn.from] || [];
        graph[conn.from].push(conn.to);
        inDegree[conn.to] = (inDegree[conn.to] || 0) + 1;
      }
      // 双向连接：从 from 到 to 仍然需要建立边
      else if (conn.type === "bidirectional" && conn.from && conn.to) {
        graph[conn.from] = graph[conn.from] || [];
        graph[conn.from].push(conn.to);
        inDegree[conn.to] = (inDegree[conn.to] || 0) + 1;
      }
    });

    // 拓扑排序
    const queue: string[] = [];
    const result: string[] = [];

    // 找到所有入度为0的节点（起始节点）
    nodes.forEach(n => {
      if (inDegree[n.id] === 0) {
        queue.push(n.id);
      }
    });

    while (queue.length > 0) {
      const current = queue.shift()!;
      result.push(current);

      const neighbors = graph[current] || [];
      neighbors.forEach(neighbor => {
        inDegree[neighbor]--;
        if (inDegree[neighbor] === 0) {
          queue.push(neighbor);
        }
      });
    }

    return result;
  }

  /**
   * 执行单个节点
   */
  private async executeNode(ctx: NodeExecutionContext): Promise<void> {
    const { node, state, nodes, connections } = ctx;

    switch (node.type) {
      case "input":
        await this.executeInputNode(ctx);
        break;
      case "dataSource":
        await this.executeDataSourceNode(ctx);
        break;
      case "retrieval":
        await this.executeRetrievalNode(ctx);
        break;
      case "llm":
        await this.executeLLMNode(ctx);
        break;
      case "output":
        await this.executeOutputNode(ctx);
        break;
    }
  }

  /**
   * 执行输入节点
   */
  private async executeInputNode(ctx: NodeExecutionContext): Promise<void> {
    const { node, state } = ctx;
    const inputText = String(node.config?.user_input ?? "").trim();
    if (inputText) {
      this.setMessage(state, node.id, "user", {
        type: "user",
        payload: inputText
      });
    }
  }

  /**
   * 执行数据源节点
   */
  private async executeDataSourceNode(ctx: NodeExecutionContext): Promise<void> {
    const { node, state, nodes, connections } = ctx;
    
    // 从配置获取数据集
    let datasetIds = node.config?.selected_datasets || [];
    
    // 如果有上游节点绑定了 datasets，使用绑定的值
    const boundDatasets = this.getInputValue(ctx, "datasets", null);
    if (boundDatasets && Array.isArray(boundDatasets)) {
      datasetIds = boundDatasets;
    }

    if (datasetIds.length > 0) {
      this.setMessage(state, node.id, "datasets", {
        type: "json",
        payload: datasetIds
      });
    }
  }

  /**
   * 执行检索节点
   */
  private async executeRetrievalNode(ctx: NodeExecutionContext): Promise<void> {
    const { node, state, nodes, connections } = ctx;

    // 获取 question
    let question = this.getInputValue(ctx, "question", null);
    if (!question || typeof question !== 'string') {
      // 从上游 input 节点获取
      const inputNode = this.getUpstreamNodes(ctx, "input")[0];
      question = String(inputNode?.config?.user_input ?? "").trim() || state.metadata.question;
    } else {
      question = String(question).trim();
    }

    // 获取 datasets：优先从 input_bindings，否则使用 collectLinkedDatasetIds（与 NativeExecutor 一致）
    let datasetIds = this.getInputValue(ctx, "datasets", null);
    if (!datasetIds || !Array.isArray(datasetIds)) {
      // 使用与 NativeExecutor 相同的逻辑：收集所有连接到检索节点的数据源
      datasetIds = collectLinkedDatasetIds(node.id, nodes, connections);
      console.log(`[LangGraphExecutor] 检索节点 ${node.id} 收集到的数据集:`, datasetIds);
    }

    if (!Array.isArray(datasetIds) || datasetIds.length === 0) {
      console.warn(`[LangGraphExecutor] 检索节点 ${node.id} 没有找到数据源，跳过检索`);
      console.warn(`[LangGraphExecutor] 连接信息:`, connections.filter(c => c.from === node.id || c.to === node.id));
      console.warn(`[LangGraphExecutor] 数据源节点:`, nodes.filter(n => n.type === "dataSource").map(n => ({ id: n.id, datasets: n.config?.selected_datasets })));
      // 设置空结果，而不是直接返回
      this.setMessage(state, node.id, "context", {
        type: "context",
        payload: ""
      });
      this.setMessage(state, node.id, "retrieval_result", {
        type: "json",
        payload: {
          total: 0,
          documents: [],
          scores: []
        }
      });
      return;
    }

    const cfg = node.config || {};
    // 转换 keyword：string | boolean | undefined -> boolean | null
    const keywordValue = cfg.keyword === undefined || cfg.keyword === null 
      ? null 
      : typeof cfg.keyword === 'string' 
        ? cfg.keyword.trim().length > 0 
        : Boolean(cfg.keyword);
    
    const ret = await retrieval({
      question,
      dataset_ids: datasetIds,
      similarity_threshold: cfg.similarity_threshold,
      vector_similarity_weight: cfg.vector_similarity_weight,
      top_k: cfg.top_k,
      keyword: keywordValue,
      highlight: cfg.highlight ?? null
    });

    const assembled = assembleRetrievedContext(cfg, ret);
    this.setMessage(state, node.id, "context", {
      type: "context",
      payload: assembled
    });
    // 存储完整的检索结果（用于最终输出）
    this.setMessage(state, node.id, "retrieval_result", {
      type: "json",
      payload: {
        total: ret.total,
        documents: ret.documents,
        scores: ret.scores
      }
    });
  }

  /**
   * 执行 LLM 节点
   * 支持条件路由：根据输出决定是否触发检索
   */
  private async executeLLMNode(ctx: NodeExecutionContext): Promise<void> {
    const { node, state } = ctx;

    // 获取输入
    const question = this.getInputValue(ctx, "question", state.metadata.question) || state.metadata.question;
    const context = this.getInputValue(ctx, "context", "") || "";

    const tpl = String(
      node.config?.prompt_template ||
      "请基于上下文回答问题\n问题: {question}\n上下文:\n{retrieved_context}"
    );

    const rendered = renderPrompt(tpl, {
      question: String(question),
      retrieved_context: String(context)
    });

    const modelId = String(node.config?.model || "");
    const temp = Number(node.config?.temperature ?? 0.7);
    const maxTok = Number(node.config?.max_tokens ?? 2000);

    const output = await runLLM(modelId, rendered, temp, maxTok);
    if (output) {
      this.setMessage(state, node.id, "answer", {
        type: "text",
        payload: output
      });
    }

    // TODO: 条件路由判断
    // 如果 LLM 输出需要触发检索（例如：查询重写），可以在这里判断
    // const shouldRetrieve = this.shouldTriggerRetrieval(output);
  }

  /**
   * 执行输出节点
   */
  private async executeOutputNode(ctx: NodeExecutionContext): Promise<void> {
    const { node, state } = ctx;
    // 输出节点通常只是收集结果，不做实际操作
    const answer = this.getInputValue(ctx, "answer", null);
    if (answer) {
      this.setMessage(state, node.id, "output", {
        type: "text",
        payload: answer
      });
    }
  }

  /**
   * 获取节点的输入值（优先从 input_bindings，否则从上游节点）
   */
  private getInputValue(
    ctx: NodeExecutionContext,
    portKey: string,
    defaultValue: any
  ): any {
    const { node, state } = ctx;
    const bindings = node.config?.input_bindings || {};
    const binding = bindings[portKey];
    
    if (binding && binding.includes('.')) {
      const [sourceNodeId, sourcePort] = binding.split('.');
      const sourceMsg = state.messages[sourceNodeId]?.[sourcePort];
      if (sourceMsg) return sourceMsg.payload;
    }

    // 从上游连接获取
    const upstreamNodes = this.getUpstreamNodes(ctx);
    for (const upstream of upstreamNodes) {
      // 根据上游节点类型推断输出端口
      const outputPort = this.inferOutputPort(upstream);
      const msg = state.messages[upstream.id]?.[outputPort];
      if (msg) return msg.payload;
    }

    return defaultValue;
  }

  /**
   * 获取上游节点
   */
  private getUpstreamNodes(
    ctx: NodeExecutionContext,
    filterType?: WorkflowNode["type"]
  ): WorkflowNode[] {
    const { node, nodes, connections } = ctx;
    const result: WorkflowNode[] = [];

    for (const conn of connections) {
      if (conn.to === node.id) {
        const upstreamId = conn.from;
        const upstream = nodes.find(n => n.id === upstreamId);
        if (upstream && (!filterType || upstream.type === filterType)) {
          result.push(upstream);
        }
      }
    }

    return result;
  }

  /**
   * 推断节点的默认输出端口
   */
  private inferOutputPort(node: WorkflowNode): string {
    switch (node.type) {
      case "input":
        return "user";
      case "dataSource":
        return "datasets";
      case "retrieval":
        return "context";
      case "llm":
        return "answer";
      case "output":
        return "output";
      default:
        return "output";
    }
  }

  /**
   * 设置消息
   */
  private setMessage(
    state: LangGraphState,
    nodeId: string,
    portKey: string,
    msg: Message
  ): void {
    if (!state.messages[nodeId]) {
      state.messages[nodeId] = {};
    }
    state.messages[nodeId][portKey] = msg;
  }

  /**
   * 提取最终结果
   * 支持多个 LLM 和检索节点：优先使用最后一个执行的节点
   */
  private extractFinalResult(
    state: LangGraphState,
    nodes: WorkflowNode[],
    connections: WorkflowConnection[]
  ): ExecutionOutput {
    // 查找输出节点
    const outputNode = nodes.find(n => n.type === "output");
    
    // 按执行顺序查找最后一个 LLM 节点
    const llmNodes = nodes.filter(n => n.type === "llm");
    const lastLLMNode = llmNodes.length > 0 
      ? llmNodes.find(n => state.executionPath.includes(n.id)) || llmNodes[llmNodes.length - 1]
      : null;

    // 按执行顺序查找最后一个检索节点
    const retrievalNodes = nodes.filter(n => n.type === "retrieval");
    const lastRetrievalNode = retrievalNodes.length > 0
      ? retrievalNodes.find(n => state.executionPath.includes(n.id)) || retrievalNodes[retrievalNodes.length - 1]
      : null;

    let llmOutput: string | null = null;
    if (lastLLMNode) {
      const answerMsg = state.messages[lastLLMNode.id]?.["answer"];
      llmOutput = answerMsg?.payload || null;
    }

    let retrievedContext: string | null = null;
    let total = 0;
    let documents: any[] = [];
    let scores: number[] = [];

    if (lastRetrievalNode) {
      const contextMsg = state.messages[lastRetrievalNode.id]?.["context"];
      retrievedContext = contextMsg?.payload || null;
      
      // 提取完整的检索结果
      const resultMsg = state.messages[lastRetrievalNode.id]?.["retrieval_result"];
      if (resultMsg && resultMsg.payload) {
        total = resultMsg.payload.total || 0;
        documents = resultMsg.payload.documents || [];
        scores = resultMsg.payload.scores || [];
      }
    }

    return {
      question: state.metadata.question,
      retrieved_context: retrievedContext,
      llm_output: llmOutput,
      total,
      documents,
      scores,
      messages: state.messages
    };
  }
}

