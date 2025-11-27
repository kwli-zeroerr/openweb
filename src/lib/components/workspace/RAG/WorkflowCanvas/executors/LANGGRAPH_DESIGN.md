# LangGraph 执行器设计文档

## 为什么选择 LangGraph？

### 当前 NativeExecutor 的局限性

1. **线性执行**：只能处理简单的线性流程（input → retrieval → llm → output）
2. **单节点限制**：只能处理第一个检索节点和第一个 LLM 节点
3. **无条件路由**：无法根据 LLM 输出决定是否触发检索
4. **无循环支持**：不支持检索 → LLM → 检索的循环流程
5. **无并行执行**：无法同时执行多个检索节点

### LangGraph 的优势

1. **图执行引擎**：原生支持复杂的有向无环图（DAG）和循环图
2. **条件路由**：可以根据节点输出动态决定下一步
3. **状态管理**：统一的 State 管理所有节点间的数据传递
4. **可视化调试**：可以追踪执行路径和状态变化
5. **生态集成**：与 LangChain 无缝集成，支持工具调用、记忆等

## 架构设计

### 1. 状态结构（State）

```typescript
interface LangGraphState {
  // 节点消息存储
  messages: Record<string, Record<string, Message>>;
  // 执行路径（用于调试）
  executionPath: string[];
  // 元数据
  metadata: {
    question: string;
    startTime: number;
    timings: Record<string, number>;
  };
}
```

### 2. 节点类型映射

| 工作流节点类型 | LangGraph 节点 | 功能 |
|--------------|---------------|------|
| `input` | Start Node | 接收用户输入 |
| `dataSource` | Data Node | 提供知识库列表 |
| `retrieval` | Tool Node | 执行检索 |
| `llm` | LLM Node | 生成文本 |
| `output` | End Node | 输出结果 |

### 3. 连接类型转换

| 工作流连接类型 | LangGraph 边类型 | 说明 |
|--------------|-----------------|------|
| `unidirectional` | `Edge` | 单向边，直接传递数据 |
| `bidirectional` | `Conditional Edge` | 双向边，根据条件路由 |

### 4. 执行流程

```
1. 构建执行图（拓扑排序）
   ↓
2. 初始化状态（State）
   ↓
3. 按顺序执行节点
   - 获取上游输入（input_bindings 或自动推断）
   - 执行节点逻辑
   - 更新状态（messages）
   ↓
4. 条件路由判断（可选）
   - LLM 输出是否需要检索？
   - 检索结果是否需要再次 LLM？
   ↓
5. 提取最终结果
```

## 多输入场景处理

### 场景 1：用户输入 → LLM → 检索 → LLM

```
用户输入 → LLM (查询重写) → 检索 → LLM (生成回答) → 输出
```

**实现方式**：
- LLM1 输出作为检索节点的 `question` 输入
- 检索节点输出作为 LLM2 的 `context` 输入

### 场景 2：LLM 直接到 LLM（绕过检索）

```
用户输入 → LLM1 → LLM2 → 输出
```

**实现方式**：
- 通过 `input_bindings` 配置 LLM2 的 `question` 绑定到 LLM1 的 `answer`
- 如果 LLM2 没有 `context` 输入，则跳过检索

### 场景 3：多个数据源并行检索

```
数据源1 ──┐
          ├─→ 检索 → LLM → 输出
数据源2 ──┘
```

**实现方式**：
- 检索节点收集所有上游 `dataSource` 节点的数据集
- 合并后统一检索

### 场景 4：条件路由（LLM 决定是否检索）

```
用户输入 → LLM → [条件判断] ─┬─→ 检索 → LLM → 输出
                              └─→ LLM → 输出
```

**实现方式**（需要扩展）：
- LLM 节点输出后，根据配置的条件函数判断
- 如果需要检索：路由到检索节点
- 如果不需要：直接路由到下一个 LLM 或输出节点

## 实现计划

### Phase 1: 基础图执行（当前实现）
- ✅ 拓扑排序构建执行顺序
- ✅ 节点间消息传递
- ✅ 支持多输入/多输出
- ✅ 时间统计

### Phase 2: 条件路由（待实现）
- [ ] LLM 输出分析（是否需要检索）
- [ ] 条件边实现
- [ ] 动态路由决策

### Phase 3: 循环支持（待实现）
- [ ] 最大迭代次数限制
- [ ] 循环终止条件
- [ ] 状态检查点

### Phase 4: 后端集成（待实现）
- [ ] 将 LangGraph 执行移到后端
- [ ] 使用真实的 LangGraph 库
- [ ] 支持 LangChain 工具和记忆

## 使用示例

### 简单流程（当前 NativeExecutor 已支持）

```typescript
// 工作流：input → retrieval → llm → output
executor = new LangGraphExecutor();
result = await executor.execute({
  question: "用户问题",
  nodes: [inputNode, retrievalNode, llmNode, outputNode],
  connections: [...]
});
```

### 多 LLM 流程（LangGraph 支持）

```typescript
// 工作流：input → llm1 → retrieval → llm2 → output
// 配置 llm1 的 prompt_template 用于查询重写
// 配置 retrieval 的 question 绑定到 llm1.answer
// 配置 llm2 的 context 绑定到 retrieval.context
```

### 条件路由流程（待实现）

```typescript
// 工作流：input → llm → [条件] → retrieval/llm → output
// 配置 llm 节点的条件函数：shouldRetrieve(output)
```

## 性能考虑

1. **并行执行**：多个独立检索节点可以并行执行
2. **缓存**：相同输入的检索结果可以缓存
3. **流式输出**：LLM 输出可以流式返回
4. **增量更新**：状态可以增量更新，避免全量复制

## 与 NativeExecutor 的对比

| 特性 | NativeExecutor | LangGraphExecutor |
|------|----------------|-------------------|
| 线性流程 | ✅ | ✅ |
| 多节点支持 | ❌ | ✅ |
| 条件路由 | ❌ | ✅ (Phase 2) |
| 循环支持 | ❌ | ✅ (Phase 3) |
| 并行执行 | ❌ | ✅ |
| 状态追踪 | 基础 | 完整 |
| 调试能力 | 弱 | 强 |

## 总结

LangGraph 是处理复杂工作流的理想选择，特别是：
- 多 LLM 节点（查询重写 + 生成）
- 条件路由（动态决定执行路径）
- 循环流程（迭代优化检索结果）
- 并行执行（提高效率）

当前的 `LangGraphExecutor` 实现是一个前端模拟版本，展示了图执行的基本思路。未来可以：
1. 将执行移到后端，使用真实的 LangGraph 库
2. 支持更复杂的条件路由和循环
3. 集成 LangChain 工具和记忆功能

