/**
 * 工作流画布类型定义
 */
import type { RagFlowDataset } from '$lib/apis/agent';

export type NodeType = "dataSource" | "retrieval" | "llm" | "output" | "input";
export type ConnectionType = "unidirectional" | "bidirectional";
export type ConnectionSide = "top" | "bottom" | "left" | "right";

// 重新导出以便组件使用
export type { RagFlowDataset };

// 简单消息模型，用于节点间传值
export interface Message {
  type: "user" | "context" | "text" | "json";
  payload: any;
}

/**
 * 工作流节点
 */
export interface WorkflowNode {
  id: string;
  type: NodeType;
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
  config: NodeConfig;
  connections: string[]; // 连接的节点ID列表
}

/**
 * 节点配置
 */
export interface NodeConfig {
  // 输入节点
  user_input?: string;
  // 数据源配置
  selected_datasets?: string[];
  
  // 检索配置
  similarity_threshold?: number;
  vector_similarity_weight?: number;
  top_k?: number;
  keyword?: string | boolean;
  highlight?: boolean;
  // 上下文拼接配置（检索节点）
  context_top_k?: number;
  context_max_chars?: number;
  context_include_source?: boolean;
  context_include_score?: boolean;
  context_use_highlight?: boolean;
  context_join?: string;
  
  // LLM配置
  model?: string;
  temperature?: number;
  max_tokens?: number;
  prompt_template?: string;
  
  // 输出配置
  format?: "text" | "json" | "markdown";
  
  // 输入/输出端口绑定
  input_bindings?: Record<string, string>; // "question" -> "node_123.user" 或 "" 表示使用节点默认值
  output_ports?: string[]; // 显式声明的输出端口列表（可选，默认按类型推断）
}

/**
 * 工作流连接
 */
export interface WorkflowConnection {
  id: string;
  from: string;
  to: string;
  fromSide: ConnectionSide;
  toSide: ConnectionSide;
  type: ConnectionType;
  controlPoints?: Array<{ x: number; y: number }>;
}

/**
 * 节点模板
 */
export interface NodeTemplate {
  type: NodeType;
  label: string;
  icon: string;
  color: string;
  width: number;
  height: number;
}

/**
 * 连接预览
 */
export interface ConnectionPreview {
  from: { x: number; y: number };
  to: { x: number; y: number };
}

/**
 * 工作流配置
 */
export interface WorkflowConfig {
  nodes: WorkflowNode[];
  connections: WorkflowConnection[];
  version: string;
}

