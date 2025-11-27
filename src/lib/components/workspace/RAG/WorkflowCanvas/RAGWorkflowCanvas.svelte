<!--
  RAG工作流画布
  支持拖拽式配置RAG检索和LLM工作流
-->
<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { ragAPI, type RagFlowDataset, type LLMModel } from "$lib/apis/rag";
  import { WEBUI_API_BASE_URL } from "$lib/constants";
  import { fetchModelsOnce, getCachedModels } from "./services/llmTools";
  import { datasetsStore } from './stores/datasets.store';
  import { modelsStore } from './stores/models.store';
  import { executionStore } from './stores/execution.store';
  import { listDatasets, retrieval } from './adapters/ragflow.adapter';
  import { collectLinkedDatasetIds, assembleRetrievedContext } from './services/retrievalService';
  import { renderPrompt, runLLM } from './services/llmService';
  import { shouldIgnoreDeleteForTarget } from './services/keyboardService';
  import { snap as snapToGridPosition, alignNodes as alignNodesSvc } from './services/layoutService';
  import { toast } from "svelte-sonner";
  import NodeToolbox from "./components/NodeToolbox.svelte";
  // @ts-ignore Svelte component default export
  import WorkflowNodeComp from "./components/WorkflowNode.svelte";
  import WorkflowConnectionComp from "./components/WorkflowConnection.svelte";
  import NodeConfigPanel from "./components/NodeConfigPanel.svelte";
  import OutputPanel from "./components/OutputPanel.svelte";
  import type { Executor } from "./executors/Executor";
  import { createExecutor, type ExecutorName } from "./executors/registry";

  export const knowledgeId: string = '';

// 固定提示词（不可修改）
const FIXED_PROMPT = `【角色设定 Role】
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
3.“请参考《{文档名}》中的‘{章节名}’。”
4.多个章节用 和 连接；不同文档用 ； 分隔。

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

根据同义词映射做思考和回复，不排除提示词已有的同义词映射。
**同义词映射**：
纵向力/垂直拉力
横向力/水平拉力
波特率/通信速率/传输速率
通讯/通信/传输协议
寄存器/对象字典
例程/报文/案例/教程/指引
映射对象/地址
刹车/制动器/抱闸
报错/异常/出错/警告
eRob/关节/电机/关节模组
负载/承重/负荷
角度/转角/旋转角度
正转/反转/方向
开环/闭环/反馈
输入/输出/信号
编码器/传感器/反馈
速度/转速/角速度
加速度/角加速度
扭矩/转矩/力矩
位置/位移/坐标
---
根据以上设置和用户问题和检索上下文信息，回答用户问题。
【用户问题】
{question}
【检索上下文】
{retrieved_context}
`;

  // 节点类型定义
  interface WorkflowNode {
    id: string;
    type: "input" | "dataSource" | "retrieval" | "llm" | "output";
    x: number;
    y: number;
    width: number;
    height: number;
    label: string;
    config: any;
    connections: string[]; // 连接的节点ID列表
  }

  // 连接类型
  type ConnectionType = "unidirectional" | "bidirectional";

  // 连接线定义
  interface WorkflowConnection {
    id: string;
    from: string;
    to: string;
    fromSide: "top" | "bottom" | "left" | "right"; // 起始连接点位置
    toSide: "top" | "bottom" | "left" | "right"; // 目标连接点位置
    type: ConnectionType; // 连接类型：单向或双向
    controlPoints?: Array<{ x: number; y: number }>; // 可编辑的控制点（用于折线编辑）
  }

  // 画布状态
  let canvas: HTMLElement;
  let nodes: WorkflowNode[] = [];
  let connections: WorkflowConnection[] = [];
  let selectedNode: WorkflowNode | null = null;
  let draggingNode: WorkflowNode | null = null;
  let dragOffset = { x: 0, y: 0 };
  let connectingFrom: string | null = null;
  let connectingFromSide: "top" | "bottom" | "left" | "right" | null = null;
  let previewConnection: { from: { x: number; y: number }, to: { x: number; y: number } } | null = null;

  // 数据集列表
  let datasets: RagFlowDataset[] = [];
  let loadingDatasets = false;
  let models: LLMModel[] = [];
  let loadingModels = false;

  // 节点配置
  let showNodeConfig = false;
  let configNode: WorkflowNode | null = null;

  // 工作流执行
  let executing = false;
  let executionResult: any = null;
  let executorName: ExecutorName = "native";
  let executor: Executor = createExecutor(executorName);
  $: executor = createExecutor(executorName);

  // 本地持久化（不下载文件）
  const LOCAL_SETTINGS_KEY = "rag-workflow-canvas:v1";

  function saveLocalSettings() {
    try {
      const data = {
        nodes,
        connections,
        executorName,
        queryQuestion,
        snapToGrid,
        gridSize
      };
      localStorage.setItem(LOCAL_SETTINGS_KEY, JSON.stringify(data));
      toast.success("设置已保存");
    } catch (e: any) {
      console.error("保存本地设置失败:", e);
      toast.error("保存本地设置失败");
    }
  }

  function loadLocalSettings() {
    try {
      const text = localStorage.getItem(LOCAL_SETTINGS_KEY);
      if (!text) return;
      const data = JSON.parse(text);
      if (Array.isArray(data.nodes)) {
        nodes = data.nodes.map((n: any) => {
          const tpl = nodeTemplates[(n?.type || "output") as keyof typeof nodeTemplates] as any;
          // 标准化卡片尺寸，确保各类型节点统一尺寸（修复历史不一致问题）
          if (tpl && (n.width !== tpl.width || n.height !== tpl.height)) {
            return { ...n, width: tpl.width, height: tpl.height };
          }
          return n;
        });
      }
      if (Array.isArray(data.connections)) connections = data.connections;
      if (typeof data.executorName === 'string') executorName = data.executorName;
      if (typeof data.queryQuestion === 'string') queryQuestion = data.queryQuestion;
      if (typeof data.snapToGrid === 'boolean') snapToGrid = data.snapToGrid;
      if (typeof data.gridSize === 'number') gridSize = data.gridSize;
      toast.success("已加载上次设置");
    } catch (e: any) {
      console.warn("读取本地设置失败，忽略:", e);
    }
  }
  
  // UI 优化：对齐和吸附功能
  let snapToGrid = true;
  let gridSize = 20;

  // 为连接渲染提供 O(1) 的节点查找，并且让 Svelte 正确追踪依赖
  $: nodeById = new Map(nodes.map((n) => [n.id, n]));
  const dummyNode: WorkflowNode = { id: "__dummy__", type: "output", x: 0, y: 0, width: 0, height: 0, label: "", config: {}, connections: [] };
  
  // 画布平移/缩放
  let panX = 0;
  let panY = 0;
  let scale = 1;
  let isPanning = false;
  let panStart = { x: 0, y: 0 };

  // 将屏幕坐标转换为画布“世界坐标”（受 pan/scale 影响）
  function toWorldCoordinates(clientX: number, clientY: number) {
    const rect = canvas.getBoundingClientRect();
    const x = (clientX - rect.left - panX) / scale;
    const y = (clientY - rect.top - panY) / scale;
    return { x, y };
  }
  
  // 安全查找节点（用于模板，规避类型告警）
  function findNodeByIdStrict(id: string): any {
    return nodes.find(n => n.id === id) as any;
  }
  
  // 对齐到网格：已委托到 layoutService.snap

  // 初始化节点类型模板
  const nodeTemplates = {
    input: {
      type: "input" as const,
      label: "用户输入",
      icon: "fas fa-keyboard",
      color: "bg-teal-500",
      width: 160,
      height: 80
    },
    dataSource: {
      type: "dataSource" as const,
      label: "数据源",
      icon: "fas fa-database",
      color: "bg-blue-500",
      width: 160,
      height: 80
    },
    retrieval: {
      type: "retrieval" as const,
      label: "检索",
      icon: "fas fa-search",
      color: "bg-green-500",
      width: 160,
      height: 80
    },
    llm: {
      type: "llm" as const,
      label: "LLM",
      icon: "fas fa-brain",
      color: "bg-purple-500",
      width: 160,
      height: 80
    },
    output: {
      type: "output" as const,
      label: "输出",
      icon: "fas fa-terminal",
      color: "bg-orange-500",
      width: 160,
      height: 80
    }
  };

  // 加载数据集列表
  async function loadDatasets() {
    try {
      loadingDatasets = true;
      const response = await listDatasets();
      datasets = response.datasets || [];
      datasetsStore.set(datasets);
    } catch (e: any) {
      console.error("加载datasets失败:", e);
      toast.error("加载知识库列表失败: " + (e.message || "未知错误"));
    } finally {
      loadingDatasets = false;
    }
  }

  // 创建新节点
  function createNode(type: "input" | "dataSource" | "retrieval" | "llm" | "output", x: number, y: number): WorkflowNode {
    const template = nodeTemplates[type];
    const id = `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    let config = {};
    if (type === "input") {
      config = { user_input: "" };
    } else if (type === "dataSource") {
      config = { dataset_ids: [], selected_datasets: [] };
    } else if (type === "retrieval") {
      config = {
        similarity_threshold: 0.2,
        vector_similarity_weight: 0.3,
        top_k: 1024,
        keyword: true,
        highlight: true
      };
    } else if (type === "llm") {
      config = {
        model: "",
        temperature: 0.7,
        max_tokens: 20000,
        // 默认提示词固定
        prompt_template: FIXED_PROMPT
      };
    }

    return {
      id,
      type,
      x,
      y,
      width: template.width,
      height: template.height,
      label: template.label,
      config,
      connections: []
    };
  }

  // 添加节点到画布
  function addNode(type: string, event: DragEvent) {
    const validTypes: Array<"input" | "dataSource" | "retrieval" | "llm" | "output"> = ["input", "dataSource", "retrieval", "llm", "output"];
    if (!validTypes.includes(type as any)) return;
    const nodeType = type as "input" | "dataSource" | "retrieval" | "llm" | "output";
    const tmpl = nodeTemplates[nodeType];
    if (!canvas) return;
    
    const world = toWorldCoordinates(event.clientX, event.clientY);
    const x = world.x - tmpl.width / 2;
    const y = world.y - tmpl.height / 2;
    
    const newNode = createNode(nodeType, x, y);
    nodes = [...nodes, newNode];
    selectedNode = newNode;
    
    // 自动打开配置：输入/数据源/LLM
    if (nodeType === "input" || nodeType === "dataSource" || nodeType === "llm") {
      configNode = newNode;
      showNodeConfig = true;
      if (nodeType === "llm") {
        // 懒加载模型
        (async () => {
          try {
            loadingModels = true;
            const cached = getCachedModels();
            if (cached) { models = cached; } else { models = await fetchModelsOnce(); }
            modelsStore.set(models);
          } catch (e) {
            console.error("加载LLM模型失败", e);
          } finally {
            loadingModels = false;
          }
        })();
      }
    }
  }

  // 节点拖拽开始
  function onNodeDragStart(node: WorkflowNode, event: MouseEvent) {
    draggingNode = node;
    const world = toWorldCoordinates(event.clientX, event.clientY);
    dragOffset = { x: world.x - node.x, y: world.y - node.y };
    
    event.preventDefault();
  }

  // 节点拖拽中（拖拽过程中不吸附，避免抖动；在结束时再吸附）
  function onNodeDrag(node: WorkflowNode, event: MouseEvent) {
    if (!draggingNode || draggingNode.id !== node.id || !canvas) return;
    const world = toWorldCoordinates(event.clientX, event.clientY);
    const newX = world.x - dragOffset.x;
    const newY = world.y - dragOffset.y;
    
    nodes = nodes.map(n => 
      n.id === node.id 
        ? { ...n, x: Math.max(0, newX), y: Math.max(0, newY) }
        : n
    );
  }

  // 节点拖拽结束（此时再做网格吸附，避免拖拽抖动）
  function onNodeDragEnd() {
    if (draggingNode) {
      const opts = { snapToGrid, gridSize };
      nodes = nodes.map(n =>
        n.id === draggingNode!.id
          ? {
              ...n,
              x: snapToGrid ? snapToGridPosition(n.x, opts) : n.x,
              y: snapToGrid ? snapToGridPosition(n.y, opts) : n.y
            }
          : n
      );
    }
    draggingNode = null;
  }

  // 节点点击
  function selectNode(node: WorkflowNode) {
    selectedNode = node;
    configNode = node;
    showNodeConfig = true;
  }

  // 删除节点
  function deleteNode(nodeId: string) {
    nodes = nodes.filter(n => n.id !== nodeId);
    connections = connections.filter(c => c.from !== nodeId && c.to !== nodeId);
    if (selectedNode?.id === nodeId) {
      selectedNode = null;
      showNodeConfig = false;
    }
  }

  // 更新节点的辅助函数
  function updateNodeConfig(updater: (node: WorkflowNode) => void) {
    if (!configNode) return;
    const currentNode = configNode;
    updater(currentNode);
    nodes = nodes.map(n => {
      if (n.id === currentNode.id) {
        return {
          id: currentNode.id,
          type: currentNode.type,
          x: currentNode.x,
          y: currentNode.y,
          width: currentNode.width,
          height: currentNode.height,
          label: currentNode.label,
          config: {...currentNode.config},
          connections: [...currentNode.connections]
        };
      }
      return n;
    });
    const updated = nodes.find(n => n.id === currentNode.id);
    if (updated) {
      configNode = updated;
    }
  }

  // 获取连接点的坐标
  function getConnectionPoint(node: WorkflowNode, side: "top" | "bottom" | "left" | "right"): { x: number; y: number } {
    switch (side) {
      case "top":
        return { x: node.x + node.width / 2, y: node.y };
      case "bottom":
        return { x: node.x + node.width / 2, y: node.y + node.height };
      case "left":
        return { x: node.x, y: node.y + node.height / 2 };
      case "right":
        return { x: node.x + node.width, y: node.y + node.height / 2 };
    }
  }

  // 开始连接
  function startConnection(nodeId: string, side: "top" | "bottom" | "left" | "right", event?: MouseEvent | KeyboardEvent) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }
    connectingFrom = nodeId;
    connectingFromSide = side;
    const node = nodes.find(n => n.id === nodeId);
    if (node && canvas) {
      const rect = canvas.getBoundingClientRect();
      const fromPoint = getConnectionPoint(node, side);
      if (event && 'clientX' in event) {
        const w = toWorldCoordinates((event as MouseEvent).clientX, (event as MouseEvent).clientY);
        previewConnection = {
          from: fromPoint,
          to: { x: w.x, y: w.y }
        };
      } else {
        // 根据边方向计算预览终点
        let offsetX = 0, offsetY = 0;
        switch (side) {
          case "top": offsetY = -50; break;
          case "bottom": offsetY = 50; break;
          case "left": offsetX = -50; break;
          case "right": offsetX = 50; break;
        }
        previewConnection = {
          from: fromPoint,
          to: { x: fromPoint.x + offsetX, y: fromPoint.y + offsetY }
        };
      }
    }
  }

  // 完成连接
  function completeConnection(toNodeId: string, toSide: "top" | "bottom" | "left" | "right", event?: MouseEvent | KeyboardEvent) {
    if (event) {
      event.stopPropagation();
      event.preventDefault();
    }
    if (!connectingFrom || connectingFrom === toNodeId || !connectingFromSide) {
      connectingFrom = null;
      connectingFromSide = null;
      previewConnection = null;
      return;
    }
    
    // 检查是否已存在连接（单向或双向）
    const existsForward = connections.some(c => c.from === connectingFrom && c.to === toNodeId);
    const existsBackward = connections.some(c => c.from === toNodeId && c.to === connectingFrom);
    
    if (!existsForward && !existsBackward && connectingFromSide) {
      // 默认创建双向连接（可以根据节点类型自动判断）
      const connectionType: ConnectionType = determineConnectionType(connectingFrom, toNodeId);
      
      const newConnection: WorkflowConnection = {
        id: `conn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        from: connectingFrom,
        to: toNodeId,
        fromSide: connectingFromSide,
        toSide: toSide,
        type: connectionType,
        controlPoints: [] // 初始为空，中点控制点会自动显示并可拖动
      };
      connections = [...connections, newConnection];
      
      // 更新节点的连接列表
      nodes = nodes.map(n => {
        if (n.id === connectingFrom) {
          return { ...n, connections: [...n.connections, toNodeId] };
        }
        return n;
      });
    }
    
    connectingFrom = null;
    connectingFromSide = null;
    previewConnection = null;
  }

  // 根据节点类型自动判断连接类型
  function determineConnectionType(fromNodeId: string, toNodeId: string): ConnectionType {
    const fromNode = nodes.find(n => n.id === fromNodeId);
    const toNode = nodes.find(n => n.id === toNodeId);
    
    if (!fromNode || !toNode) return "unidirectional";
    
    // 检索节点到数据源：双向（检索请求 + 返回数据）
    if (fromNode.type === "retrieval" && toNode.type === "dataSource") {
      return "bidirectional";
    }
    
    // 数据源到检索：单向（数据源只输出）
    if (fromNode.type === "dataSource" && toNode.type === "retrieval") {
      return "unidirectional";
    }
    
    // LLM到检索：双向（可能需要二次检索）
    if (fromNode.type === "llm" && toNode.type === "retrieval") {
      return "bidirectional";
    }
    
    // 检索到LLM：单向（检索结果传给LLM）
    if (fromNode.type === "retrieval" && toNode.type === "llm") {
      return "unidirectional";
    }
    
    // LLM到输出：单向
    if (fromNode.type === "llm" && toNode.type === "output") {
      return "unidirectional";
    }
    
    // 默认单向
    return "unidirectional";
  }

  // 切换连接类型
  function toggleConnectionType(connectionId: string) {
    connections = connections.map(conn => {
      if (conn.id === connectionId) {
        return {
          ...conn,
          type: conn.type === "unidirectional" ? "bidirectional" : "unidirectional"
        };
      }
      return conn;
    });
  }

  // 对齐节点功能（委托服务）
  function alignNodes(alignment: "left" | "right" | "top" | "bottom" | "center" | "middle") {
    if (!selectedNode) { toast.error("请先选择一个节点"); return; }
    nodes = alignNodesSvc(nodes, selectedNode, alignment, { snapToGrid, gridSize });
    toast.success(`节点已对齐：${alignment}`);
  }
  
  // 分布节点功能（暂不实现，需要多选支持）
  function distributeNodes(direction: "horizontal" | "vertical") {
    toast.info("分布功能需要多选支持，将在后续版本中实现");
  }

  // 在连接线上添加编辑点
  let editingConnection: string | null = null;
  let draggingControlPoint: { connId: string; pointIndex: number } | null = null;

  function startEditingConnection(connId: string) {
    editingConnection = connId;
  }

  function stopEditingConnection() {
    editingConnection = null;
    draggingControlPoint = null;
  }

  function addControlPoint(connId: string, x: number, y: number) {
    connections = connections.map(conn => {
      if (conn.id === connId) {
        const points = conn.controlPoints || [];
    return {
          ...conn,
          controlPoints: [...points, { x, y }]
        };
      }
      return conn;
    });
  }

  function deleteControlPoint(connId: string, pointIndex: number) {
    connections = connections.map(conn => {
      if (conn.id === connId && conn.controlPoints) {
        const points = [...conn.controlPoints];
        points.splice(pointIndex, 1);
        return {
          ...conn,
          controlPoints: points
        };
      }
      return conn;
    });
  }

  function startDragControlPoint(connId: string, pointIndex: number, event: MouseEvent) {
    event.stopPropagation();
    const conn = connections.find(c => c.id === connId);
    // 如果没有控制点，先创建中点控制点
    if (conn && (!conn.controlPoints || conn.controlPoints.length === 0)) {
      const fromNode = nodes.find(n => n.id === conn.from);
      const toNode = nodes.find(n => n.id === conn.to);
      if (fromNode && toNode) {
        const fromPoint = getConnectionPoint(fromNode, conn.fromSide);
        const toPoint = getConnectionPoint(toNode, conn.toSide);
        const midX = (fromPoint.x + toPoint.x) / 2;
        const midY = (fromPoint.y + toPoint.y) / 2;
        addControlPoint(connId, midX, midY);
        // 现在开始拖动刚创建的控制点（索引为0）
        draggingControlPoint = { connId, pointIndex: 0 };
      }
    } else {
      draggingControlPoint = { connId, pointIndex };
    }
  }

  function updateControlPoint(connId: string, pointIndex: number, x: number, y: number) {
    connections = connections.map(conn => {
      if (conn.id === connId && conn.controlPoints) {
        const points = [...conn.controlPoints];
        const originalPoint = points[pointIndex];
        
        // 直角约束：根据拖动方向，只移动一个维度（水平或垂直）
        const deltaX = Math.abs(x - originalPoint.x);
        const deltaY = Math.abs(y - originalPoint.y);
        
        let constrainedPoint: { x: number; y: number };
        if (deltaX > deltaY) {
          // 水平拖动：只改变 x，保持 y 不变（直角折线）
          constrainedPoint = { x, y: originalPoint.y };
        } else {
          // 垂直拖动：只改变 y，保持 x 不变（直角折线）
          constrainedPoint = { x: originalPoint.x, y };
        }
        
        points[pointIndex] = constrainedPoint;
        return {
          ...conn,
          controlPoints: points
        };
      }
      return conn;
    });
  }


  // 执行工作流
  async function executeWorkflow(question: string) {
    // 若存在“用户输入”节点，优先使用其内容作为问题
    const inputNode = nodes.find(n => n.type === "input");
    const inputText = (inputNode && (inputNode as any).config?.user_input) ? String((inputNode as any).config.user_input) : "";
    const finalQuestion = (inputText && inputText.trim()) ? inputText.trim() : (question || "").trim();
    if (!finalQuestion) { toast.error("请输入查询问题"); return; }
    if (!nodes.some(n => n.type === "retrieval")) { toast.error("请至少添加一个检索节点"); return; }
    executing = true;
    executionResult = null;
    try {
      const out = await executor.execute({ question: finalQuestion, nodes: nodes as any, connections: connections as any });
      executionResult = out;
      executionStore.set(out as any);
      const outputNodes = nodes.filter(n => n.type === "output");
      if (outputNodes.length > 0) {
        const outNode = outputNodes[0];
        const connected = connections.some(c => c.from === outNode.id || c.to === outNode.id);
        if (!connected) toast.info("提示：请将检索或LLM节点连接到输出节点，以形成完整链路");
      }
      toast.success(`检索完成，找到 ${out.total || 0} 个结果`);
    } catch (e: any) {
      console.error("执行工作流失败:", e);
      toast.error("执行工作流失败: " + (e.message || "未知错误"));
    } finally {
      executing = false;
    }
  }

  // 事件处理（为模板移除隐式 any）
  function handleNodeMouseDown(n: any, e: Event) {
    selectNode(n);
    if (e instanceof MouseEvent) {
      onNodeDragStart(n, e);
    }
  }
  function handleNodeContextMenu(n: any, e: MouseEvent) {
    if (confirm("确定要删除这个节点吗？")) { deleteNode(n.id); }
  }
  function handleConnDown(id: string, side: "top"|"bottom"|"left"|"right", e: Event) {
    startConnection(id, side, e as unknown as MouseEvent);
  }
  function handleConnUp(id: string, side: "top"|"bottom"|"left"|"right", e: Event) {
    completeConnection(id, side, e as unknown as MouseEvent);
  }

  // 画布平移/缩放事件
  function onCanvasMouseDown(e: MouseEvent) {
    const target = e.target as HTMLElement;
    // 仅当点击空白区域（不在节点、连接点、SVG连线等上）时开始平移
    if (target === canvas || (
      !target.closest('.workflow-node') &&
      !target.closest('.connection-point') &&
      !(target.closest('svg'))
    )) {
      isPanning = true;
      panStart = { x: e.clientX - panX, y: e.clientY - panY };
      (canvas as HTMLElement).style.cursor = 'grabbing';
    }
  }
  function onCanvasMouseMove(e: MouseEvent) {
    if (isPanning) {
      panX = e.clientX - panStart.x;
      panY = e.clientY - panStart.y;
    }
  }
  function onCanvasMouseUp() {
    isPanning = false;
    (canvas as HTMLElement).style.cursor = '';
  }
  function onCanvasMouseLeave() {
    isPanning = false;
    (canvas as HTMLElement).style.cursor = '';
  }
  function onCanvasWheel(e: WheelEvent) {
    if (e.ctrlKey) return;
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    scale = Math.min(2, Math.max(0.5, scale + delta));
  }

  // 保存工作流
  function saveWorkflow() {
    const workflow = {
      nodes,
      connections,
      version: "1.0"
    };
    const json = JSON.stringify(workflow, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rag_workflow_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("工作流已保存");
  }

  // LLM 生成已适配到 adapters/llm.adapter.ts

  // 加载工作流
  function loadWorkflow(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const workflow = JSON.parse(e.target?.result as string);
        nodes = workflow.nodes || [];
        connections = workflow.connections || [];
        toast.success("工作流已加载");
      } catch (error) {
        toast.error("加载工作流失败: 文件格式错误");
      }
    };
    reader.readAsText(file);
  }

  // 清空画布
  function clearCanvas() {
    if (confirm("确定要清空画布吗？")) {
      nodes = [];
      connections = [];
      selectedNode = null;
      showNodeConfig = false;
    }
  }

  onMount(() => {
    loadDatasets();
    loadLocalSettings();
    
    // 监听鼠标移动以更新连接预览
           let dragScheduled = false;
           let lastMouseEvent: MouseEvent | null = null;

    const handleMouseMove = (e: MouseEvent) => {
      if (connectingFrom && connectingFromSide && canvas) {
        const node = nodes.find(n => n.id === connectingFrom);
        if (node) {
          const fromPoint = getConnectionPoint(node, connectingFromSide);
          const w = toWorldCoordinates(e.clientX, e.clientY);
          previewConnection = {
            from: fromPoint,
            to: { x: w.x, y: w.y }
          };
        }
      } else if (draggingNode && canvas) {
               // 使用 rAF 合批更新，降低抖动
               lastMouseEvent = e;
               if (!dragScheduled) {
                 dragScheduled = true;
                 requestAnimationFrame(() => {
                   if (draggingNode && lastMouseEvent) {
                     onNodeDrag(draggingNode, lastMouseEvent);
                   }
                   dragScheduled = false;
                 });
               }
      } else if (draggingControlPoint && canvas) {
        const w = toWorldCoordinates(e.clientX, e.clientY);
        updateControlPoint(draggingControlPoint.connId, draggingControlPoint.pointIndex, w.x, w.y);
      }
    };
    

    const handleMouseUp = (e: MouseEvent) => {
      if (draggingControlPoint) {
        draggingControlPoint = null;
      }
      // 如果正在连接，但在画布上释放鼠标，检查是否释放在连接点上
      if (connectingFrom && connectingFromSide && canvas) {
        const w = toWorldCoordinates(e.clientX, e.clientY);
        const x = w.x; const y = w.y;
        
        // 检查是否释放在任何节点的连接点上
        let connected = false;
        const sides: Array<"top" | "bottom" | "left" | "right"> = ["top", "bottom", "left", "right"];
        
        for (const node of nodes) {
          if (node.id !== connectingFrom) {
            for (const side of sides) {
              const point = getConnectionPoint(node, side);
              const distance = Math.sqrt(Math.pow(x - point.x, 2) + Math.pow(y - point.y, 2));
              // 如果在连接点附近（25px范围内）
              if (distance < 25) {
                completeConnection(node.id, side, e);
                connected = true;
                break;
              }
            }
            if (connected) break;
          }
        }
        
        if (!connected) {
          connectingFrom = null;
          connectingFromSide = null;
          previewConnection = null;
        }
      }
      if (draggingNode) {
        onNodeDragEnd();
      }
    };

    // 键盘事件处理（Esc 退出编辑，Delete 删除节点）
    const handleKeyDown = (e: KeyboardEvent) => {
      // 在输入类控件中不处理删除键，避免误删节点/面板
      if (shouldIgnoreDeleteForTarget(e.target)) return;
      if (e.key === "Escape") {
        if (editingConnection) {
          stopEditingConnection();
        } else if (connectingFrom) {
          connectingFrom = null;
          connectingFromSide = null;
          previewConnection = null;
        } else if (showNodeConfig) {
          showNodeConfig = false;
          configNode = null;
        }
      } else if (e.key === "Delete" || e.key === "Backspace") {
        if (selectedNode && !editingConnection) {
          deleteNode(selectedNode.id);
        }
      }
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
      document.removeEventListener("keydown", handleKeyDown);
    };
  });

  let queryQuestion = "";

  function handleCanvasKeydown(e: KeyboardEvent){
    if(e.key === 'Escape'){
      stopEditingConnection();
    }
  }
</script>

<div class="h-full flex flex-col bg-gray-50 dark:bg-gray-900">
  <!-- 工具栏 -->
  <div class="flex-shrink-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-3">
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">RAG 工作流画布</h3>
      </div>
      <div class="flex items-center space-x-2">
        <!-- UI 优化：对齐和吸附工具 -->
        <div class="flex items-center space-x-1 border-r border-gray-300 dark:border-gray-600 pr-2 mr-2">
          <button
            on:click={() => { snapToGrid = !snapToGrid; toast.info(snapToGrid ? "已启用网格吸附" : "已禁用网格吸附"); }}
            class="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded {snapToGrid ? 'ring-2 ring-indigo-500' : ''}"
            title="网格吸附 (Ctrl+G)"
          >
            <i class="fas fa-th"></i>
          </button>
        </div>
        <!-- 执行器选择 -->
        <div class="flex items-center space-x-2">
          <label for="executor-select" class="text-xs text-gray-600 dark:text-gray-300">执行器</label>
          <select id="executor-select" bind:value={executorName}
            class="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
            <option value="native">NativeExecutor</option>
            <option value="langgraph">LangGraphExecutor</option>
          </select>
        </div>
        <!-- 查询输入 -->
        <input
          type="text"
          bind:value={queryQuestion}
          placeholder="输入查询问题..."
          class="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 dark:focus:ring-indigo-800 w-64"
        />
        <button
          on:click={() => executeWorkflow(queryQuestion)}
          disabled={executing || nodes.length === 0}
          class="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
        >
          <i class="fas {executing ? 'fa-spinner fa-spin' : 'fa-play'}"></i>
          <span>{executing ? '执行中...' : '执行工作流'}</span>
        </button>
        <button
          on:click={saveLocalSettings}
          class="px-3 py-1.5 bg-emerald-100 hover:bg-emerald-200 dark:bg-emerald-900 dark:hover:bg-emerald-800 text-emerald-700 dark:text-emerald-300 text-sm rounded-lg font-medium transition-colors"
        >
          <i class="fas fa-save mr-1"></i>
          保存设置
        </button>
        <button
          on:click={saveWorkflow}
          class="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 text-sm rounded-lg font-medium transition-colors"
        >
          <i class="fas fa-save mr-1"></i>
          保存
        </button>
        <label class="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 text-sm rounded-lg font-medium transition-colors cursor-pointer">
          <i class="fas fa-folder-open mr-1"></i>
          加载
          <input type="file" accept=".json" on:change={loadWorkflow} class="hidden" />
        </label>
        <button
          on:click={clearCanvas}
          class="px-3 py-1.5 bg-red-100 hover:bg-red-200 dark:bg-red-900 dark:hover:bg-red-800 text-red-700 dark:text-red-300 text-sm rounded-lg font-medium transition-colors"
        >
          <i class="fas fa-trash mr-1"></i>
          清空
        </button>
      </div>
    </div>
  </div>

  <div class="flex-1 flex overflow-hidden">
    <!-- 节点工具箱（左侧） -->
    <NodeToolbox {nodeTemplates} />

    <!-- 画布区域 -->
    <div class="flex-1 relative overflow-hidden">
      <div
        bind:this={canvas}
        class="w-full h-full bg-gray-50 dark:bg-gray-900 relative"
        role="application"
        aria-label="工作流画布"
        style="background-image: {snapToGrid ? `radial-gradient(circle, #e5e7eb 1px, transparent 1px)` : 'none'}; background-size: {gridSize}px {gridSize}px;"
        on:drop={(e) => {
          e.preventDefault();
          if (e.dataTransfer) {
            const nodeType = e.dataTransfer.getData("text/plain");
            if (nodeType && canvas) {
              addNode(nodeType, e);
            }
          }
        }}
        on:dragover={(e) => {
          e.preventDefault();
          if (e.dataTransfer) {
            e.dataTransfer.dropEffect = "copy";
          }
        }}
        on:click={(e) => {
          // 点击画布空白区域，退出编辑模式
          const target = e.target;
          if (target instanceof HTMLElement && target === canvas) {
            stopEditingConnection();
          }
        }}
        on:keydown={handleCanvasKeydown}
        on:mousedown={onCanvasMouseDown}
        on:mousemove={onCanvasMouseMove}
        on:mouseup={onCanvasMouseUp}
        on:mouseleave={onCanvasMouseLeave}
        on:wheel={onCanvasWheel}
      >
        <div class="absolute inset-0" style="transform: translate({panX}px, {panY}px) scale({scale}); transform-origin: 0 0;">
        <!-- 绘制连接线 -->
        <svg class="absolute inset-0 pointer-events-none" style="z-index: 1; width: 100%; height: 100%;">
          {#each connections as conn}
                   {#if nodeById.get(conn.from) && nodeById.get(conn.to)}
                     <g>
                      <WorkflowConnectionComp
                         connection={conn}
                         fromNode={nodeById.get(conn.from) || dummyNode}
                         toNode={nodeById.get(conn.to) || dummyNode}
                  isEditing={editingConnection === conn.id}
                  {canvas}
                  onConnectionClick={() => startEditingConnection(conn.id)}
                  onToggleType={(id) => toggleConnectionType(id)}
                  onAddControlPoint={(id, x, y) => addControlPoint(id, x, y)}
                  onDeleteControlPoint={(id, idx) => deleteControlPoint(id, idx)}
                  onConnectionRightClick={(id) => {
                    if (confirm("确定要删除这条连接吗？")) {
                      connections = connections.filter(c => c.id !== id);
                      const c = conn;
                      nodes = nodes.map(n => {
                        if (n.id === c.from) {
                          const updatedConnections = n.connections.filter(x => x !== c.to);
                          return { ...n, connections: updatedConnections };
                        }
                        return n;
                      });
                    }
                  }}
                  onControlPointMouseDown={(id, idx, e) => startDragControlPoint(id, idx, e)}
                />
              </g>
            {/if}
          {/each}
          
          <!-- 预览连接线 -->
          {#if previewConnection}
            <line
              x1={previewConnection.from.x}
              y1={previewConnection.from.y}
              x2={previewConnection.to.x}
              y2={previewConnection.to.y}
              stroke="#6366f1"
              stroke-width="3"
              stroke-dasharray="8,4"
              fill="none"
              marker-end="url(#arrowhead-preview)"
              opacity="0.6"
            />
          {/if}

          <!-- 箭头标记定义 -->
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <polygon points="0 0, 10 3, 0 6" fill="#6366f1" />
            </marker>
            <marker id="arrowhead-bidirectional" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <polygon points="0 0, 10 3, 0 6" fill="#10b981" />
            </marker>
            <marker id="arrowhead-bidirectional-reverse" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <polygon points="0 0, 10 3, 0 6" fill="#10b981" opacity="0.6" />
            </marker>
            <marker id="arrowhead-preview" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <polygon points="0 0, 10 3, 0 6" fill="#6366f1" opacity="0.6" />
            </marker>
          </defs>
        </svg>

        <!-- 渲染节点（组件化） -->
        {#each nodes as node}
          <WorkflowNodeComp
            node={node}
            template={nodeTemplates[node.type]}
            isSelected={selectedNode?.id === node.id}
            {connectingFrom}
            onNodeMouseDown={handleNodeMouseDown}
            onNodeContextMenu={handleNodeContextMenu}
            onConnectionPointMouseDown={handleConnDown}
            onConnectionPointMouseUp={handleConnUp}
          />
        {/each}
      </div>
    </div>
        </div>

    <!-- 节点配置面板（右侧，组件化） -->
    {#if showNodeConfig && configNode}
      <NodeConfigPanel
        node={configNode}
        {datasets}
        {loadingDatasets}
        {models}
        {loadingModels}
        {nodes}
        {connections}
        onClose={() => { showNodeConfig = false; configNode = null; }}
        onUpdateConfig={(partial) => {
                          if (!configNode) return;
                  updateNodeConfig((node) => {
            Object.assign(node.config, partial);
                  });
                }}
      />
    {/if}
  </div>

  <!-- 执行结果区域 -->
  {#if executionResult}
    <OutputPanel {executionResult} onClose={() => executionResult = null} />
  {/if}
</div>

<!-- 样式已迁移到 OutputPanel.svelte -->

