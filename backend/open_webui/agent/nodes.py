"""
LangGraph 节点实现

定义各种工作流节点的执行逻辑
"""
from typing import Dict, Any, List, Optional
from .state import WorkflowState, Message
import logging
import json
import inspect

logger = logging.getLogger(__name__)


class BaseNode:
    """节点基类"""
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        self.node_id = node_id
        self.config = config or {}
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        """执行节点逻辑"""
        raise NotImplementedError


class InputNode(BaseNode):
    """输入节点：接收用户输入"""
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        input_text = str(self.config.get("user_input", "")).strip()
        if input_text:
            if not state.messages.get(self.node_id):
                state.messages[self.node_id] = {}
            state.messages[self.node_id]["user"] = Message(
                type="user",
                payload=input_text
            )
        state.execution_path.append(self.node_id)
        return state


class DataSourceNode(BaseNode):
    """数据源节点：提供知识库列表"""
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        dataset_ids = self.config.get("selected_datasets", [])
        
        # 如果有上游节点绑定了 datasets，使用绑定的值
        bindings = self.config.get("input_bindings", {})
        if "datasets" in bindings:
            binding = bindings["datasets"]
            if binding and "." in binding:
                source_node_id, source_port = binding.split(".", 1)
                source_msg = state.messages.get(source_node_id, {}).get(source_port)
                if source_msg:
                    dataset_ids = source_msg.payload if isinstance(source_msg.payload, list) else dataset_ids
        
        if dataset_ids:
            if not state.messages.get(self.node_id):
                state.messages[self.node_id] = {}
            state.messages[self.node_id]["datasets"] = Message(
                type="json",
                payload=dataset_ids
            )
        state.execution_path.append(self.node_id)
        return state


class RetrievalNode(BaseNode):
    """检索节点：执行向量检索"""
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        # 获取 question
        question = self._get_input_value(state, "question", None)
        if not question or not isinstance(question, str):
            # 从上游 input 节点获取
            question = state.question or ""
        else:
            question = str(question).strip()
        
        # 获取 datasets
        dataset_ids = self._get_input_value(state, "datasets", None)
        if not dataset_ids or not isinstance(dataset_ids, list):
            # 从上游 dataSource 节点获取（通过连接）
            dataset_ids = []
        
        if not dataset_ids:
            logger.warning(f"检索节点 {self.node_id} 没有找到数据源")
            state.execution_path.append(self.node_id)
            return state
        
        # 执行检索（调用实际的检索服务）
        from open_webui.services.ragflow.chunk_management import get_client as get_ragflow_chunk_client
        from open_webui.services.ragflow import get_base_url, get_api_key
        
        cfg = self.config
        
        # 创建检索客户端（需要从配置获取 base_url 和 api_key）
        # 这里简化处理，实际应该从请求上下文获取
        base_url = get_base_url(None)  # TODO: 传入 Request 对象
        api_key = get_api_key(None)
        chunk_client = get_ragflow_chunk_client(base_url, api_key)
        
        # 执行检索
        documents, scores = await chunk_client.retrieve(
            question=question,
            dataset_ids=dataset_ids,
            similarity_threshold=cfg.get("similarity_threshold"),
            vector_similarity_weight=cfg.get("vector_similarity_weight"),
            top_k=cfg.get("top_k", 5),
            keyword=cfg.get("keyword", True),
            highlight=cfg.get("highlight", False)
        )
        
        # 组装上下文
        context = self._assemble_context(cfg, {"documents": documents, "scores": scores})
        
        # 存储结果
        if not state.messages.get(self.node_id):
            state.messages[self.node_id] = {}
        state.messages[self.node_id]["context"] = Message(
            type="context",
            payload=context
        )
        state.messages[self.node_id]["retrieval_result"] = Message(
            type="json",
            payload={
                "total": len(documents),
                "documents": documents,
                "scores": scores
            }
        )
        
        state.retrieved_context = context
        state.total = len(documents)
        state.documents = documents
        state.scores = scores
        
        state.execution_path.append(self.node_id)
        return state
    
    def _get_input_value(self, state: WorkflowState, port_key: str, default: Any) -> Any:
        """获取输入值（优先从 input_bindings，否则从上游节点）"""
        bindings = self.config.get("input_bindings", {})
        binding = bindings.get(port_key)
        
        if binding and "." in binding:
            source_node_id, source_port = binding.split(".", 1)
            source_msg = state.messages.get(source_node_id, {}).get(source_port)
            if source_msg:
                return source_msg.payload
        
        return default
    
    def _assemble_context(self, cfg: Dict[str, Any], ret: Dict[str, Any]) -> str:
        """组装检索上下文"""
        documents = ret.get("documents", [])
        scores = ret.get("scores", [])
        
        ctx_top_k = cfg.get("context_top_k", 3)
        ctx_join = cfg.get("context_join", "\n---\n")
        ctx_max = cfg.get("context_max_chars", 2000)
        use_hl = cfg.get("context_use_highlight", False)
        inc_src = cfg.get("context_include_source", True)
        inc_score = cfg.get("context_include_score", False)
        
        picked = documents[:ctx_top_k]
        assembled_parts = []
        
        for i, doc in enumerate(picked):
            meta = doc.get("metadata", {})
            content = meta.get("highlight") if use_hl and meta.get("highlight") else doc.get("content", "")
            
            parts = [content]
            if inc_src and meta.get("document_name"):
                parts.append(f"【来源】{meta.get('document_name')}")
            if inc_score and i < len(scores):
                parts.append(f"【分数】{scores[i]:.3f}")
            
            assembled_parts.append("\n".join(parts))
        
        assembled = ctx_join.join(assembled_parts)
        if len(assembled) > ctx_max:
            assembled = assembled[:ctx_max] + "..."
        
        return assembled


class LLMNode(BaseNode):
    """LLM 节点：执行大语言模型生成"""
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        # 获取 Request 和 user（从 state 中传递）
        request = getattr(state, "_request", None)
        user = getattr(state, "_user", None)
        # 规范化 user：保证可通过属性访问 id/name/email/role
        try:
            from types import SimpleNamespace
            if isinstance(user, dict):
                user = SimpleNamespace(
                    id=user.get("id"),
                    name=user.get("name"),
                    email=user.get("email"),
                    role=user.get("role"),
                )
        except Exception:
            pass
        
        # 保存到实例中供 _call_llm 使用
        self._request = request
        self._user = user
        
        # 获取输入
        question = self._get_input_value(state, "question", state.question) or state.question
        context = self._get_input_value(state, "context", "") or ""
        
        # 收集所有工具节点的结果
        tool_results = []
        for node_id, node_messages in state.messages.items():
            if node_id.startswith("tool_") and "result" in node_messages:
                tool_result = node_messages["result"].payload
                tool_results.append(f"工具 {node_id} 的结果:\n{tool_result}")
        
        # 构建工具结果文本
        tool_results_text = "\n\n".join(tool_results) if tool_results else "无工具结果"
        
        # 渲染提示词模板
        template = str(
            self.config.get("prompt_template") or
            "请基于上下文和工具结果回答问题\n问题: {question}\n上下文:\n{retrieved_context}\n\n工具结果:\n{tool_results}"
        )
        
        prompt = template.format(
            question=str(question),
            retrieved_context=str(context) if context else "无上下文",
            tool_results=tool_results_text
        )
        
        # 调用 LLM
        model_id = str(self.config.get("model", ""))
        temperature = float(self.config.get("temperature", 0.7))
        max_tokens = int(self.config.get("max_tokens", 2000))
        
        output = await self._call_llm(model_id, prompt, temperature, max_tokens)
        
        if output:
            if not state.messages.get(self.node_id):
                state.messages[self.node_id] = {}
            state.messages[self.node_id]["answer"] = Message(
                type="text",
                payload=output
            )
            state.llm_output = output
        
        state.execution_path.append(self.node_id)
        return state
    
    def _get_input_value(self, state: WorkflowState, port_key: str, default: Any) -> Any:
        """获取输入值"""
        bindings = self.config.get("input_bindings", {})
        binding = bindings.get(port_key)
        
        if binding and "." in binding:
            source_node_id, source_port = binding.split(".", 1)
            source_msg = state.messages.get(source_node_id, {}).get(source_port)
            if source_msg:
                return source_msg.payload
        
        return default
    
    async def _call_llm(self, model_id: str, prompt: str, temperature: float, max_tokens: int) -> str:
        """调用 LLM 生成"""
        try:
            # 获取 Request 和 user（从 state 中传递）
            request = getattr(self, "_request", None)
            user = getattr(self, "_user", None)
            
            if not request:
                logger.warning("缺少 Request 对象，无法调用 LLM")
                return ""
            
            # 使用 OpenAI 客户端直接调用
            try:
                import aiohttp
                from open_webui.models.models import Models
                
                # 获取模型信息
                model_info = Models.get_model_by_id(model_id)
                if not model_info:
                    logger.warning(f"模型 {model_id} 未找到")
                    return ""
                
                # 从 request.app.state 获取 API 配置
                models_dict = request.app.state.MODELS
                model_config = models_dict.get(model_id, {})
                
                if not model_config:
                    logger.warning(f"模型配置 {model_id} 未找到")
                    return ""
                
                # 获取 API URL 和 Key
                url_idx = model_config.get("urlIdx", 0)
                api_base_urls = request.app.state.config.OPENAI_API_BASE_URLS
                api_keys = request.app.state.config.OPENAI_API_KEYS
                
                if url_idx >= len(api_base_urls):
                    logger.warning(f"API URL 索引 {url_idx} 超出范围")
                    return ""
                
                url = api_base_urls[url_idx]
                key = api_keys[url_idx] if url_idx < len(api_keys) else None
                
                # 构建请求
                api_url = f"{url}/chat/completions"
                headers = {
                    "Content-Type": "application/json"
                }
                if key:
                    headers["Authorization"] = f"Bearer {key}"
                
                payload = {
                    "model": model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                # 发送请求
                timeout = aiohttp.ClientTimeout(total=300)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(api_url, json=payload, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                            return content
                        else:
                            error_text = await response.text()
                            logger.error(f"LLM API 调用失败: {response.status} - {error_text}")
                            return ""
                
            except Exception as e:
                logger.error(f"LLM 调用失败: {e}", exc_info=True)
                return ""
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}", exc_info=True)
            return ""


class ToolNode(BaseNode):
    """工具节点：调用 OpenWebUI Tools 系统"""
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        # 获取工具配置
        tool_id = self.config.get("tool_id", "")
        tool_name = self.config.get("tool_name", "")
        tool_params = self.config.get("tool_params", {})
        
        # 从输入端口获取参数（优先使用 input_bindings）
        input_params = self._get_input_value(state, "params", {})
        if isinstance(input_params, dict):
            tool_params = {**tool_params, **input_params}
        elif isinstance(input_params, str):
            try:
                input_params = json.loads(input_params)
                tool_params = {**tool_params, **input_params}
            except:
                pass
        
        # 如果没有 question 参数，尝试从 state.question 获取
        if "question" not in tool_params and state.question:
            tool_params["question"] = state.question
        
        # 如果输入是字符串，尝试解析为 question
        question_input = self._get_input_value(state, "question", None)
        if question_input and isinstance(question_input, str):
            if "question" not in tool_params:
                tool_params["question"] = question_input
        
        # 获取 Request 和 user（从 state 中传递）
        request = getattr(state, "_request", None)
        user = getattr(state, "_user", None)
        
        try:
            # 调用工具系统
            from open_webui.utils.tools import get_tools
            
            # 构建 extra_params
            # 构建 extra_params（保留字典形式给工具侧）
            extra_params = {
                "__id__": tool_id,
                "__user__": {
                    "id": getattr(user, "id", None) if user else None,
                    "name": getattr(user, "name", None) if user else None,
                    "email": getattr(user, "email", None) if user else None,
                    "role": getattr(user, "role", None) if user else None,
                },
                "__metadata__": {},
                "__event_call__": None,  # TODO: 实现事件调用（用于 direct 工具）
            }
            
            # 获取工具
            tool_ids = [tool_id] if tool_id else []
            tools_dict = await get_tools(request, tool_ids, user, extra_params)
            
            # 查找工具函数
            tool_function = None
            tool_info = None
            
            if tool_name and tool_name in tools_dict:
                tool_info = tools_dict[tool_name]
                tool_function = tool_info.get("callable")
            elif tool_id:
                # 尝试通过 tool_id 查找
                for name, tool_dict in tools_dict.items():
                    if tool_dict.get("tool_id") == tool_id:
                        tool_info = tool_dict
                        tool_function = tool_dict.get("callable")
                        tool_name = name
                        break
            
            if not tool_function:
                logger.warning(f"工具节点 {self.node_id} 未找到工具: tool_id={tool_id}, tool_name={tool_name}")
                error_msg = f"工具未找到: tool_id={tool_id}, tool_name={tool_name}"
                if not state.messages.get(self.node_id):
                    state.messages[self.node_id] = {}
                state.messages[self.node_id]["error"] = Message(
                    type="text",
                    payload=error_msg
                )
                state.execution_path.append(self.node_id)
                return state
            
            # 根据函数签名过滤/映射参数，避免意外参数报错
            try:
                sig = inspect.signature(tool_function)
                param_names = set(sig.parameters.keys())
                accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())

                filtered_params = dict(tool_params)

                # question 字段智能映射到常见入参名
                if "question" in filtered_params and "question" not in param_names:
                    q = filtered_params.pop("question")
                    for alt in ["prompt", "query", "text", "input", "message"]:
                        if alt in param_names:
                            filtered_params[alt] = q
                            break
                        
                # 注入 __request__/__user__ 如果函数接受
                if "__request__" in param_names:
                    filtered_params["__request__"] = request
                if "__user__" in param_names:
                    filtered_params["__user__"] = user

                # 如果不接受 **kwargs，则严格过滤只保留签名里的参数
                if not accepts_kwargs:
                    filtered_params = {k: v for k, v in filtered_params.items() if k in param_names}

                # 类型转换：根据函数签名中的类型注解转换参数类型
                for param_name, param_value in list(filtered_params.items()):
                    if param_name in sig.parameters:
                        param = sig.parameters[param_name]
                        param_type = param.annotation
                        
                        # 跳过没有类型注解或类型为 inspect.Parameter.empty 的参数
                        if param_type == inspect.Parameter.empty:
                            continue
                        
                        # 如果参数已经是正确类型，跳过
                        if isinstance(param_value, param_type):
                            continue
                        
                        try:
                            # 尝试类型转换
                            if param_type == int:
                                filtered_params[param_name] = int(param_value)
                            elif param_type == float:
                                filtered_params[param_name] = float(param_value)
                            elif param_type == bool:
                                if isinstance(param_value, str):
                                    filtered_params[param_name] = param_value.lower() in ('true', '1', 'yes', 'on')
                                else:
                                    filtered_params[param_name] = bool(param_value)
                            elif param_type == str:
                                filtered_params[param_name] = str(param_value)
                            # 处理 Optional 类型（Union[SomeType, None]）
                            elif hasattr(param_type, '__origin__'):
                                origin = param_type.__origin__
                                # 检查是否是 Union 类型（Optional 就是 Union[T, None]）
                                try:
                                    from typing import Union
                                    if origin is Union or (hasattr(origin, '__name__') and origin.__name__ == 'Union'):
                                        # 提取非 None 的类型
                                        args = getattr(param_type, '__args__', [])
                                        actual_types = [t for t in args if t is not type(None)]
                                        if actual_types:
                                            actual_type = actual_types[0]
                                            if not isinstance(param_value, actual_type):
                                                if actual_type == int:
                                                    filtered_params[param_name] = int(param_value)
                                                elif actual_type == float:
                                                    filtered_params[param_name] = float(param_value)
                                except:
                                    pass
                        except (ValueError, TypeError) as e:
                            logger.warning(f"参数 {param_name} 类型转换失败: {e}，使用原始值")
                            # 转换失败时保持原值

                # 执行工具
                if inspect.iscoroutinefunction(tool_function):
                    tool_result = await tool_function(**filtered_params)
                else:
                    tool_result = tool_function(**filtered_params)
            except Exception as e:
                raise e
            
            # 格式化结果
            if isinstance(tool_result, (dict, list)):
                tool_result = json.dumps(tool_result, indent=2, ensure_ascii=False)
            elif not isinstance(tool_result, str):
                tool_result = str(tool_result)
            
            # 存储结果
            if not state.messages.get(self.node_id):
                state.messages[self.node_id] = {}
            state.messages[self.node_id]["result"] = Message(
                type="text",
                payload=tool_result
            )
            
            logger.info(f"工具节点 {self.node_id} 执行成功: {tool_name}")
            
        except Exception as e:
            logger.error(f"工具节点 {self.node_id} 执行失败: {e}", exc_info=True)
            error_msg = f"工具调用失败: {str(e)}"
            if not state.messages.get(self.node_id):
                state.messages[self.node_id] = {}
            state.messages[self.node_id]["error"] = Message(
                type="text",
                payload=error_msg
            )
        
        state.execution_path.append(self.node_id)
        return state
    
    def _get_input_value(self, state: WorkflowState, port_key: str, default: Any) -> Any:
        """获取输入值"""
        bindings = self.config.get("input_bindings", {})
        binding = bindings.get(port_key)
        
        if binding and "." in binding:
            source_node_id, source_port = binding.split(".", 1)
            source_msg = state.messages.get(source_node_id, {}).get(source_port)
            if source_msg:
                return source_msg.payload
        
        return default


class OutputNode(BaseNode):
    """输出节点：收集最终结果"""
    
    async def execute(self, state: WorkflowState) -> WorkflowState:
        # 输出节点通常只是收集结果，不做实际操作
        answer = self._get_input_value(state, "answer", None)
        if answer:
            if not state.messages.get(self.node_id):
                state.messages[self.node_id] = {}
            state.messages[self.node_id]["output"] = Message(
                type="text",
                payload=answer
            )
        state.execution_path.append(self.node_id)
        return state
    
    def _get_input_value(self, state: WorkflowState, port_key: str, default: Any) -> Any:
        """获取输入值"""
        bindings = self.config.get("input_bindings", {})
        binding = bindings.get(port_key)
        
        if binding and "." in binding:
            source_node_id, source_port = binding.split(".", 1)
            source_msg = state.messages.get(source_node_id, {}).get(source_port)
            if source_msg:
                return source_msg.payload
        
        return default

