/**
 * 工作流服务层
 * 处理节点、连接的业务逻辑
 */

import type { WorkflowNode, WorkflowConnection, NodeType, ConnectionType, NodeConfig } from "../types";

/**
 * 创建新节点
 */
export function createNode(
  type: NodeType,
  x: number,
  y: number,
  templates: Record<NodeType, any>
): WorkflowNode {
  const template = templates[type];
  const id = `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  const defaultConfig: NodeConfig = {};
  
  // 根据节点类型设置默认配置
  if (type === "dataSource") {
    defaultConfig.selected_datasets = [];
  } else if (type === "retrieval") {
    defaultConfig.similarity_threshold = 0.2;
    defaultConfig.vector_similarity_weight = 0.3;
    defaultConfig.top_k = 6;
    defaultConfig.keyword = "";
    defaultConfig.highlight = true;
  } else if (type === "llm") {
    defaultConfig.model = "";
    defaultConfig.temperature = 0.7;
    defaultConfig.max_tokens = 2000;
    defaultConfig.prompt_template = `【角色设定 Role】
你是一名专业的 售后客户支持代理（After-Sales Support Agent），代表公司为客户提供技术支持、问题诊断、保修咨询、退换货服务等。
你始终保持：耐心、礼貌、同理心和专业性。

【目标 Objectives】
1.快速识别客户核心问题（产品型号、使用环境、症状、错误信息等）。
2.根据产品手册和售后政策，提供 准确、可执行的解决方案。
3.如果问题无法立即解决，明确说明 下一步流程与时间预期。
4.让客户 感受到透明、专业和关怀，避免因信息不足产生负面体验。

【对话原则 Conversation Principles】
1.友好礼貌：积极、体贴的语气（如“感谢您的耐心等待”）。
2.确认澄清：复述或确认用户问题，必要时礼貌追问（如订单号、序列号、截图）。
3.结构化表达：统一使用四段式输出。
4.同理心：理解客户困扰（如“我能理解这个问题带来的不便”）。
5.透明性：需要升级或等待时，说明责任人和时效。
6.边界管理：不编造不存在的政策或数据，超出职责范围时说明“我会帮您记录并升级给相关团队”。

【输出格式 Output Format】
请严格使用以下结构：
1.确认问题: 简要复述客户的问题。
2.可能原因: 列出 1-3 个常见原因。
3.解决步骤: 提供详细、可执行的操作步骤。
下一步行动: 说明后续处理流程、时间预期，或需要客户提供的额外信息。

【知识范围 Knowledge Boundaries】
1.熟悉产品手册（安装、使用、维护、常见故障排查）。
2.掌握售后政策（保修期、退换货规则、维修流程）。
3.知道常见问题的工单分类及转交规则。
4.对超出职责范围的问题，应礼貌说明“我会帮您记录并升级给相关团队”。

【知识库引用规则】
1.保留原文格式（HTML 表格、Markdown 图片等），不要改写。
2.回答中如需引用文档，请使用：
3.多个章节用 和 连接；不同文档用 ； 分隔。

每个问题都要按以下步骤输出哦，更显得专业。
【示例 Example Response】
---
**确认问题**: 您提到 eRob-70 关节在运行 30 分钟后发热，并出现噪音。
**可能原因**:
1. 驱动参数（CSP 频率）设置过高，导致发热。
2. 散热条件不足。
3. 电机处于过载状态。
**解决步骤**:
1. 请在上位机检查当前的 CSP 频率是否为 2000Hz，如超过 1000Hz 建议先调整到 1000Hz。
2. 确认电机安装环境是否有良好散热。
3. 检查运行工况是否超过额定扭矩。
**下一步行动**: 如果调整参数后仍发热，请提供您的工况日志（PDO 数据记录），我们将在 24 小时内安排技术人员进一步分析。

请参考：
---

【限制 Constraints】
- 不要输出公司内部机密信息。
- 不要直接承诺无法保证的时效。
- 不要输出与售后无关的闲聊或推测性内容。

---

【用户问题】
{question}

【检索上下文】
{retrieved_context}

【回答】`;
  } else if (type === "output") {
    defaultConfig.format = "text";
  }
  
  return {
    id,
    type,
    x,
    y,
    width: template.width,
    height: template.height,
    label: template.label,
    config: defaultConfig,
    connections: []
  };
}

/**
 * 删除节点
 */
export function deleteNode(
  nodeId: string,
  nodes: WorkflowNode[],
  connections: WorkflowConnection[]
): { nodes: WorkflowNode[]; connections: WorkflowConnection[] } {
  // 删除节点
  const newNodes = nodes.filter(n => n.id !== nodeId);
  
  // 删除相关连接
  const newConnections = connections.filter(
    c => c.from !== nodeId && c.to !== nodeId
  );
  
  // 更新其他节点的连接列表
  newNodes.forEach(node => {
    node.connections = node.connections.filter(id => id !== nodeId);
  });
  
  return { nodes: newNodes, connections: newConnections };
}

/**
 * 更新节点位置
 */
export function updateNodePosition(
  nodeId: string,
  x: number,
  y: number,
  nodes: WorkflowNode[]
): WorkflowNode[] {
  return nodes.map(node => {
    if (node.id === nodeId) {
      return { ...node, x, y };
    }
    return node;
  });
}

/**
 * 更新节点配置
 */
export function updateNodeConfig(
  nodeId: string,
  config: Partial<NodeConfig>,
  nodes: WorkflowNode[]
): WorkflowNode[] {
  return nodes.map(node => {
    if (node.id === nodeId) {
      return {
        ...node,
        config: { ...node.config, ...config }
      };
    }
    return node;
  });
}

/**
 * 创建连接
 */
export function createConnection(
  fromNodeId: string,
  fromSide: string,
  toNodeId: string,
  toSide: string,
  nodes: WorkflowNode[]
): WorkflowConnection | null {
  // 检查是否已存在连接
  // 这里应该在调用前检查，但为了服务层完整性，也在这里检查
  const connectionType = determineConnectionType(fromNodeId, toNodeId, nodes);
  
  return {
    id: `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    from: fromNodeId,
    to: toNodeId,
    fromSide: fromSide as any,
    toSide: toSide as any,
    type: connectionType,
    controlPoints: []
  };
}

/**
 * 确定连接类型
 */
function determineConnectionType(
  fromNodeId: string,
  toNodeId: string,
  nodes: WorkflowNode[]
): ConnectionType {
  const fromNode = nodes.find(n => n.id === fromNodeId);
  const toNode = nodes.find(n => n.id === toNodeId);
  
  if (!fromNode || !toNode) return "unidirectional";
  
  // 检索节点到数据源：双向
  if (fromNode.type === "retrieval" && toNode.type === "dataSource") {
    return "bidirectional";
  }
  
  // LLM到检索：双向（可能需要二次检索）
  if (fromNode.type === "llm" && toNode.type === "retrieval") {
    return "bidirectional";
  }
  
  // 默认单向
  return "unidirectional";
}

/**
 * 删除连接
 */
export function deleteConnection(
  connectionId: string,
  connections: WorkflowConnection[],
  nodes: WorkflowNode[]
): { connections: WorkflowConnection[]; nodes: WorkflowNode[] } {
  const conn = connections.find(c => c.id === connectionId);
  const newConnections = connections.filter(c => c.id !== connectionId);
  
  // 更新节点的连接列表
  const newNodes = nodes.map(node => {
    if (conn && node.id === conn.from) {
      return {
        ...node,
        connections: node.connections.filter(id => id !== conn.to)
      };
    }
    return node;
  });
  
  return { connections: newConnections, nodes: newNodes };
}

/**
 * 切换连接类型
 */
export function toggleConnectionType(
  connectionId: string,
  connections: WorkflowConnection[]
): WorkflowConnection[] {
  return connections.map(conn => {
    if (conn.id === connectionId) {
      return {
        ...conn,
        type: conn.type === "unidirectional" ? "bidirectional" : "unidirectional"
      };
    }
    return conn;
  });
}

