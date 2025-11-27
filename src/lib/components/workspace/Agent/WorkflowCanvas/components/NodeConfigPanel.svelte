<!--
  节点配置面板组件
  表现层：负责节点配置的UI展示和交互
-->
<script lang="ts">
  import type { WorkflowNode, RagFlowDataset } from "../types";
  import type { LLMModel } from "$lib/apis/rag";
  
  import type { WorkflowConnection } from "../types";
  
  export let node: WorkflowNode | null;
  export let datasets: RagFlowDataset[];
  export let loadingDatasets: boolean;
  export let models: LLMModel[] = [];
  export let loadingModels: boolean = false;
  export let nodes: WorkflowNode[] = [];
  export let connections: WorkflowConnection[] = [];
  export let onClose: () => void;
  export let onUpdateConfig: (config: Partial<any>) => void;
  
  // 节点类型 -> 输入端口定义
  const inputPortsByType: Record<string, Array<{ key: string; label: string; desc?: string }>> = {
    retrieval: [
      { key: "question", label: "问题 (question)", desc: "检索查询问题" },
      { key: "datasets", label: "数据源 (datasets)", desc: "知识库列表" }
    ],
    llm: [
      { key: "question", label: "问题 (question)", desc: "用户问题" },
      { key: "context", label: "上下文 (context)", desc: "检索得到的上下文" }
    ],
    output: [
      { key: "answer", label: "答案 (answer)", desc: "LLM生成的答案" }
    ]
  };
  
  // 节点类型 -> 输出端口定义
  const outputPortsByType: Record<string, Array<{ key: string; label: string; desc?: string }>> = {
    input: [{ key: "user", label: "用户输入 (user)", desc: "用户输入的问题文本" }],
    dataSource: [{ key: "datasets", label: "知识库列表 (datasets)", desc: "选中的知识库ID列表" }],
    retrieval: [{ key: "context", label: "检索上下文 (context)", desc: "拼接后的检索上下文" }],
    llm: [{ key: "answer", label: "回答 (answer)", desc: "LLM生成的回答文本" }]
  };
  
  // 获取上游节点的可用输出端口
  function getUpstreamOutputs(nodeId: string): Array<{ nodeId: string; nodeLabel: string; port: string; portLabel: string }> {
    const res: Array<{ nodeId: string; nodeLabel: string; port: string; portLabel: string }> = [];
    for (const conn of connections) {
      if (conn.to === nodeId) {
        const fromNode = nodes.find(n => n.id === conn.from);
        if (fromNode) {
          const ports = outputPortsByType[fromNode.type] || [];
          for (const p of ports) {
            res.push({ nodeId: fromNode.id, nodeLabel: fromNode.label, port: p.key, portLabel: p.label });
          }
        }
      }
    }
    return res;
  }
</script>

{#if node}
  <div class="flex-shrink-0 w-80 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 p-4 overflow-y-auto">
    <div class="flex items-center justify-between mb-4">
      <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300">节点配置</h4>
      <button
        on:click={onClose}
        class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
      >
        <i class="fas fa-times"></i>
      </button>
    </div>

    {#if node.type === "input"}
      <!-- 用户输入节点配置 -->
      <div class="space-y-3">
        <div>
          <label for="user-input-text" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
            用户输入
          </label>
          <textarea id="user-input-text"
            rows="4"
            placeholder="在此输入要询问的问题；执行时将优先使用这里的内容作为 question"
            value={node.config.user_input || ""}
            on:input={(e) => onUpdateConfig({ user_input: e.currentTarget.value })}
            class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          ></textarea>
        </div>
        <!-- 输出端口信息 -->
        <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
          <div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">输出端口</div>
          {#each (outputPortsByType["input"] || []) as port}
            <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">
              <span class="font-mono">{port.key}</span>: {port.label}
            </div>
          {/each}
        </div>
      </div>
    {:else if node.type === "dataSource"}
      <!-- 数据源配置 -->
      <div class="space-y-4">
        <div>
          <div class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
            选择知识库
          </div>
          {#if loadingDatasets}
            <div class="text-sm text-gray-500">加载中...</div>
          {:else if datasets.length === 0}
            <div class="text-sm text-gray-500">暂无可用知识库</div>
          {:else}
            <div class="space-y-2 max-h-64 overflow-y-auto">
              {#each datasets as dataset}
                {@const isSelected = node.config.selected_datasets?.includes(dataset.id)}
                <label class="flex items-center space-x-2 p-2 border border-gray-200 dark:border-gray-700 rounded hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    on:change={(e) => {
                      const selected = node.config.selected_datasets || [];
                      if (e.currentTarget.checked) {
                        onUpdateConfig({ selected_datasets: [...selected, dataset.id] });
                      } else {
                        onUpdateConfig({ selected_datasets: selected.filter(id => id !== dataset.id) });
                      }
                    }}
                    class="w-4 h-4 text-indigo-600"
                  />
                  <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                      {dataset.name}
                    </div>
                    <div class="text-xs text-gray-500 dark:text-gray-400">
                      文档: {dataset.document_count || 0} | 分段: {dataset.chunk_count || 0}
                    </div>
                  </div>
                </label>
              {/each}
            </div>
          {/if}
        </div>
        <!-- 输出端口信息 -->
        <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
          <div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">输出端口</div>
          {#each (outputPortsByType["dataSource"] || []) as port}
            <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">
              <span class="font-mono">{port.key}</span>: {port.label}
            </div>
          {/each}
        </div>
      </div>
    {:else if node.type === "retrieval"}
      <!-- 检索节点配置 -->
      <div class="space-y-4">
        <!-- 输入端口配置 -->
        <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
          <div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">输入来源配置</div>
          {#each (inputPortsByType["retrieval"] || []) as port}
            {@const bindings = node.config.input_bindings || {}}
            {@const currentBinding = bindings[port.key] || ""}
            {@const upstreams = getUpstreamOutputs(node.id)}
            <div class="mb-3">
              <label for="input-{port.key}" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                {port.label}
              </label>
              {#if port.desc}
                <div class="text-[10px] text-gray-500 dark:text-gray-400 mb-1">{port.desc}</div>
              {/if}
              <select id="input-{port.key}"
                value={currentBinding}
                on:change={(e) => {
                  const bindings = { ...(node.config.input_bindings || {}), [port.key]: e.currentTarget.value };
                  onUpdateConfig({ input_bindings: bindings });
                }}
                class="w-full px-2 py-1.5 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                <option value="">使用默认值</option>
                {#each upstreams as up}
                  <option value="{up.nodeId}.{up.port}">{up.nodeLabel} - {up.portLabel}</option>
                {/each}
              </select>
            </div>
          {/each}
        </div>
        <!-- 输出端口信息 -->
        <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
          <div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">输出端口</div>
          {#each (outputPortsByType["retrieval"] || []) as port}
            <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">
              <span class="font-mono">{port.key}</span>: {port.label}
            </div>
          {/each}
        </div>
        <div>
          <label for="sim-thres" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
            相似度阈值: {(node.config.similarity_threshold || 0.2).toFixed(2)}
          </label>
          <input id="sim-thres"
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={node.config.similarity_threshold || 0.2}
            on:input={(e) => {
              onUpdateConfig({ similarity_threshold: parseFloat(e.currentTarget.value) });
            }}
            class="w-full"
          />
        </div>
        <div>
          <label for="vec-weight" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
            向量相似度权重: {(node.config.vector_similarity_weight || 0.3).toFixed(2)}
          </label>
          <input id="vec-weight"
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={node.config.vector_similarity_weight || 0.3}
            on:input={(e) => {
              onUpdateConfig({ vector_similarity_weight: parseFloat(e.currentTarget.value) });
            }}
            class="w-full"
          />
        </div>
        <div>
          <label for="retr-topk" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
            Top K: {node.config.top_k || 6}
          </label>
          <input id="retr-topk"
            type="number"
            min="1"
            max="20"
            value={node.config.top_k || 6}
            on:input={(e) => {
              onUpdateConfig({ top_k: parseInt(e.currentTarget.value) || 6 });
            }}
            class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          />
        </div>
        <div>
          <label for="keywordText" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
            关键词
          </label>
          <input id="keywordText"
            type="text"
            value={node.config.keyword || ""}
            on:input={(e) => {
              onUpdateConfig({ keyword: e.currentTarget.value });
            }}
            placeholder="可选关键词过滤"
            class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          />
        </div>
        <div>
          <label class="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={node.config.highlight !== false}
              on:change={(e) => {
                onUpdateConfig({ highlight: e.currentTarget.checked });
              }}
              class="w-4 h-4 text-indigo-600"
            />
            <span class="text-sm text-gray-700 dark:text-gray-300">高亮显示</span>
          </label>
        </div>
        <!-- 上下文拼接设置（用于传给LLM的retrieved_context） -->
        <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
          <div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">上下文拼接设置</div>
          <div class="grid grid-cols-2 gap-3 mb-2">
            <div>
              <label for="ctx-topk" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">上下文片段数</label>
              <input id="ctx-topk" type="number" min="1" max="20" value={node.config.context_top_k || 3}
                on:input={(e)=> onUpdateConfig({ context_top_k: parseInt(e.currentTarget.value)||3 })}
                class="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700" />
            </div>
            <div>
              <label for="ctx-max" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">最大字符数</label>
              <input id="ctx-max" type="number" min="100" max="20000" value={node.config.context_max_chars || 2000}
                on:input={(e)=> onUpdateConfig({ context_max_chars: parseInt(e.currentTarget.value)||2000 })}
                class="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700" />
            </div>
          </div>
          <div class="space-y-2 mb-2">
            <label class="flex items-center space-x-2">
              <input type="checkbox" checked={node.config.context_include_source !== false}
                on:change={(e)=> onUpdateConfig({ context_include_source: e.currentTarget.checked })}
                class="w-4 h-4 text-indigo-600" />
              <span class="text-xs text-gray-700 dark:text-gray-300">包含来源文档名</span>
            </label>
            <label class="flex items-center space-x-2">
              <input type="checkbox" checked={node.config.context_include_score === true}
                on:change={(e)=> onUpdateConfig({ context_include_score: e.currentTarget.checked })}
                class="w-4 h-4 text-indigo-600" />
              <span class="text-xs text-gray-700 dark:text-gray-300">包含相似度分数</span>
            </label>
            <label class="flex items-center space-x-2">
              <input type="checkbox" checked={node.config.context_use_highlight === true}
                on:change={(e)=> onUpdateConfig({ context_use_highlight: e.currentTarget.checked })}
                class="w-4 h-4 text-indigo-600" />
              <span class="text-xs text-gray-700 dark:text-gray-300">优先使用高亮片段</span>
            </label>
          </div>
          <div>
            <label for="ctx-join" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">片段分隔符</label>
            <input id="ctx-join" type="text" value={node.config.context_join || "\n---\n"}
              on:input={(e)=> onUpdateConfig({ context_join: e.currentTarget.value })}
              class="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700" />
          </div>
        </div>
      </div>
    {:else if node.type === "llm"}
      <!-- LLM节点配置 -->
      <div class="space-y-4">
        <!-- 输入端口配置 -->
        <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
          <div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">输入来源配置</div>
          {#each (inputPortsByType["llm"] || []) as port}
            {@const bindings = node.config.input_bindings || {}}
            {@const currentBinding = bindings[port.key] || ""}
            {@const upstreams = getUpstreamOutputs(node.id)}
            <div class="mb-3">
              <label for="input-{port.key}" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                {port.label}
              </label>
              {#if port.desc}
                <div class="text-[10px] text-gray-500 dark:text-gray-400 mb-1">{port.desc}</div>
              {/if}
              <select id="input-{port.key}"
                value={currentBinding}
                on:change={(e) => {
                  const bindings = { ...(node.config.input_bindings || {}), [port.key]: e.currentTarget.value };
                  onUpdateConfig({ input_bindings: bindings });
                }}
                class="w-full px-2 py-1.5 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                <option value="">使用默认值</option>
                {#each upstreams as up}
                  <option value="{up.nodeId}.{up.port}">{up.nodeLabel} - {up.portLabel}</option>
                {/each}
              </select>
            </div>
          {/each}
        </div>
        <!-- 输出端口信息 -->
        <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
          <div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">输出端口</div>
          {#each (outputPortsByType["llm"] || []) as port}
            <div class="text-xs text-gray-600 dark:text-gray-400 mb-1">
              <span class="font-mono">{port.key}</span>: {port.label}
            </div>
          {/each}
        </div>
        <div>
          <label for="llm-model" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
            模型
          </label>
          {#if loadingModels}
            <div class="text-sm text-gray-500">模型加载中...</div>
          {:else if models.length === 0}
            <div class="text-sm text-gray-500">暂无可用模型</div>
          {:else}
            <select id="llm-model"
              value={node.config.model || ""}
              on:change={(e) => {
                onUpdateConfig({ model: e.currentTarget.value });
              }}
              class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            >
              <option value="" disabled>请选择模型</option>
              {#each models as m}
                <option value={m.id}>{m.name || m.id}</option>
              {/each}
            </select>
          {/if}
        </div>
        <div>
          <label for="llm-prompt" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">提示词</label>
          <textarea id="llm-prompt"
            rows="4"
            placeholder="在此输入提示词；可用变量: question, retrieved_context"
            value={node.config.prompt_template || ""}
            on:input={(e) => onUpdateConfig({ prompt_template: e.currentTarget.value })}
            class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          ></textarea>
        </div>
        <div>
          <label for="llm-temp" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
            温度: {(node.config.temperature || 0.7).toFixed(2)}
          </label>
          <input id="llm-temp"
            type="range"
            min="0"
            max="2"
            step="0.1"
            value={node.config.temperature || 0.7}
            on:input={(e) => {
              onUpdateConfig({ temperature: parseFloat(e.currentTarget.value) });
            }}
            class="w-full"
          />
        </div>
        <div>
          <label for="llm-max" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
            最大Token数
          </label>
          <input id="llm-max"
            type="number"
            min="1"
            max="8000"
            value={node.config.max_tokens || 2000}
            on:input={(e) => {
              onUpdateConfig({ max_tokens: parseInt(e.currentTarget.value) || 2000 });
            }}
            class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          />
        </div>
      </div>
    {:else if node.type === "output"}
      <!-- 输出节点配置 -->
      <div class="space-y-4">
        <!-- 输入端口配置 -->
        <div class="pt-2 border-t border-gray-200 dark:border-gray-700">
          <div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">输入来源配置</div>
          {#each (inputPortsByType["output"] || []) as port}
            {@const bindings = node.config.input_bindings || {}}
            {@const currentBinding = bindings[port.key] || ""}
            {@const upstreams = getUpstreamOutputs(node.id)}
            <div class="mb-3">
              <label for="input-{port.key}" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                {port.label}
              </label>
              {#if port.desc}
                <div class="text-[10px] text-gray-500 dark:text-gray-400 mb-1">{port.desc}</div>
              {/if}
              <select id="input-{port.key}"
                value={currentBinding}
                on:change={(e) => {
                  const bindings = { ...(node.config.input_bindings || {}), [port.key]: e.currentTarget.value };
                  onUpdateConfig({ input_bindings: bindings });
                }}
                class="w-full px-2 py-1.5 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                <option value="">使用默认值</option>
                {#each upstreams as up}
                  <option value="{up.nodeId}.{up.port}">{up.nodeLabel} - {up.portLabel}</option>
                {/each}
              </select>
            </div>
          {/each}
        </div>
        <div>
          <label for="output-format" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
            输出格式
          </label>
          <select id="output-format"
            value={node.config.format || "text"}
            on:change={(e) => {
              onUpdateConfig({ format: e.currentTarget.value });
            }}
            class="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          >
            <option value="text">文本</option>
            <option value="json">JSON</option>
            <option value="markdown">Markdown</option>
          </select>
        </div>
      </div>
    {/if}
  </div>
{/if}

