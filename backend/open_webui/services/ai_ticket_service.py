import logging
import json
import time
import asyncio
from typing import Optional, Dict, Any
from open_webui.models.tickets import Tickets, TicketModel, TicketPriority, TicketCategory
from open_webui.models.users import Users
from open_webui.models.chats import Chats
from open_webui.models.messages import Messages
from open_webui.utils.chat import generate_chat_completion
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class AITicketService:
    """AI工单生成服务"""
    
    def __init__(self):
        # 默认系统提示词，实际使用时从数据库配置中读取
        self.default_system_prompt = """你是一个专业的AI工单分析专家，专门处理用户对AI回复的负面反馈。你的任务是深度分析用户反馈，生成高质量的结构化工单。

## 🎯 核心任务
根据用户的负面反馈和完整对话上下文，智能生成专业的工单，帮助技术团队快速定位和解决问题。

## 📋 分析流程

### 第一步：问题识别
- 仔细分析用户的具体问题描述
- 理解用户期望与实际结果的差距
- 识别AI回复中的错误或不足
- 评估问题对用户体验的影响

### 第二步：上下文理解
- 分析完整对话流程
- 理解用户的使用场景和需求
- 识别AI回复的技术问题
- 评估问题的可重现性

### 第三步：影响评估
- 判断问题的严重程度
- 评估对业务的影响范围
- 确定紧急程度和处理优先级
- 识别潜在的系统性问题

## 🏷️ 工单生成标准

### 标题规范（≤30字）
- 使用动词开头，如"修复"、"优化"、"调整"
- 突出核心问题，避免模糊表述
- 包含关键的技术术语
- 示例：修复AI回复中的代码格式错误

### 问题描述结构（用户视角）
1. **用户反馈**：直接引用或总结用户的反馈内容
2. **问题现象**：描述用户遇到的具体问题
3. **期望结果**：用户期望得到的结果
4. **实际结果**：用户实际得到的结果
5. **影响范围**：问题对用户的影响程度

### 问题分析结构（技术视角）
1. **技术分析**：分析AI回复中的具体错误
2. **根本原因**：识别问题的根本原因
3. **影响评估**：说明问题对系统的影响
4. **解决建议**：提供初步的修复方向
5. **相关技术**：涉及的技术栈和模块

### 优先级判断标准
- **urgent**: 系统崩溃、数据泄露、安全漏洞、核心功能完全失效
- **high**: 主要功能异常、严重影响用户体验、数据错误
- **medium**: 功能部分异常、性能问题、用户体验不佳
- **low**: 优化建议、小bug、非关键功能问题

### 分类选择指南
- **bug**: AI回复错误、功能异常、技术故障、逻辑错误
- **feature_request**: 新功能需求、功能增强、用户体验改进
- **general_inquiry**: 使用咨询、操作指导、配置问题
- **technical_support**: 技术问题、集成问题、性能优化
- **other**: 其他类型问题

### 标签策略
- **技术标签**：涉及的技术栈（如python、javascript、api等）
- **模块标签**：相关功能模块（如chat、auth、database等）
- **严重程度**：critical、major、minor、enhancement
- **问题类型**：accuracy、performance、usability、security

## 📤 输出格式要求

请严格按照以下JSON格式返回，确保字段完整：

{
    "title": "具体的问题标题",
    "description": "问题描述部分：用户反馈、问题现象、期望结果、实际结果、影响范围",
    "analysis": "问题分析部分：技术分析、根本原因、影响评估、解决建议、相关技术",
    "priority": "urgent|high|medium|low",
    "category": "bug|feature_request|general_inquiry|technical_support|other",
    "tags": ["技术标签", "模块标签", "严重程度", "问题类型"]
}

## ⚠️ 质量要求
- 分析必须客观准确，基于事实
- 问题描述要站在用户角度，问题分析要站在技术角度
- 提供具体可执行的解决建议
- 避免重复用户已表达的内容
- 保持专业、清晰、友好的语调
- 确保JSON格式正确，字段完整"""

    async def generate_ticket_from_feedback(
        self, 
        feedback_data: Dict[str, Any], 
        user_id: str,
        request=None
    ) -> Optional[TicketModel]:
        """
        根据用户反馈生成工单
        
        Args:
            feedback_data: 反馈数据
            user_id: 用户ID
            request: FastAPI请求对象
            
        Returns:
            生成的工单对象
        """
        try:
            # 检查是否已经为这个反馈生成过工单
            existing_ticket = Tickets.get_ticket_by_source_feedback_id(feedback_data.get("id"))
            if existing_ticket:
                log.info(f"Ticket already exists for feedback {feedback_data.get('id')}, updating instead of creating new")
                # 更新现有工单
                return await self._update_existing_ticket(existing_ticket, feedback_data, user_id, request)

            # 获取用户信息
            user_info = Users.get_user_by_id(user_id)
            if not user_info:
                log.error(f"User not found: {user_id}")
                return None

            # 获取对话上下文
            chat_context = self._get_chat_context(feedback_data)
            
            # 获取完整的对话数据
            full_chat_data = await self._get_full_chat_data(feedback_data)
            
            # 使用AI分析反馈并生成工单
            ticket_data = await self._analyze_feedback_with_ai(
                feedback_data, chat_context, request
            )
            
            if not ticket_data:
                log.error("Failed to generate ticket data from AI")
                return None

            # 合并AI分析结果和完整对话数据
            # 确保feedback_data包含完整的反馈信息
            complete_feedback_data = {
                "id": feedback_data.get("id"),
                "user_id": feedback_data.get("user_id"),
                "version": feedback_data.get("version"),
                "type": feedback_data.get("type"),
                "data": feedback_data.get("data", {}),  # 确保data字段存在
                "meta": feedback_data.get("meta", {}),
                "snapshot": feedback_data.get("snapshot", {}),
                "created_at": feedback_data.get("created_at"),
                "updated_at": feedback_data.get("updated_at")
            }
            
            ai_analysis_data = {
                **ticket_data,
                "feedback_data": complete_feedback_data,
                "chat_context": chat_context,
                "full_chat_data": full_chat_data
            }

            # 创建工单
            ticket = Tickets.create_ticket(
                id=f"ai-{int(time.time())}-{user_id[:8]}",
                title=ticket_data.get("title", "AI回复质量问题"),
                description=ticket_data.get("description", "用户对AI回复不满意，需要人工处理"),
                user_id=user_id,
                user_name=user_info.name,
                user_email=user_info.email,
                priority=self._map_priority(ticket_data.get("priority", "medium")),
                category=self._map_category(ticket_data.get("category", "general_inquiry")),
                tags=ticket_data.get("tags", ["ai-feedback", "auto-generated"]),
                is_ai_generated=True,
                source_feedback_id=feedback_data.get("id"),
                ai_analysis=ai_analysis_data
            )

            if ticket:
                log.info(f"AI generated ticket {ticket.id} for user {user_id}")
                
                # 自动派发工单 - 已禁用，改为人工分配
                # try:
                #     from open_webui.services.ticket_assignment_service import ticket_assignment_service
                #     assigned_admin = await ticket_assignment_service.auto_assign_ticket(ticket)
                #     if assigned_admin:
                #         log.info(f"Auto-assigned AI ticket {ticket.id} to admin {assigned_admin}")
                #     else:
                #         log.warning(f"Failed to auto-assign AI ticket {ticket.id}")
                # except Exception as e:
                #     log.error(f"Error in auto-assignment for AI ticket {ticket.id}: {e}")
                
                log.info(f"AI ticket {ticket.id} created and waiting for manual assignment")
                
                # 发送钉钉通知
                try:
                    from open_webui.services.notification_service import notification_service
                    await notification_service.notify_new_ticket(ticket)
                    log.info(f"Sent DingTalk notification for AI ticket {ticket.id}")
                except Exception as e:
                    log.error(f"Failed to send DingTalk notification for AI ticket {ticket.id}: {e}")
                
                return ticket
            else:
                log.error("Failed to create ticket in database")
                return None

        except Exception as e:
            log.error(f"Error generating AI ticket: {e}")
            return None

    def _get_chat_context(self, feedback_data: Dict[str, Any]) -> str:
        """获取对话上下文"""
        try:
            meta = feedback_data.get("meta", {})
            chat_id = meta.get("chat_id")
            message_id = meta.get("message_id")
            
            if not chat_id or not message_id:
                return "无法获取对话上下文"

            # 获取聊天记录
            chat = Chats.get_chat_by_id(chat_id)
            if not chat:
                return "聊天记录不存在"

            # 获取相关消息
            messages_map = Chats.get_messages_map_by_chat_id(chat_id)
            if not messages_map:
                return "聊天记录不存在"
            
            # 将消息映射转换为列表
            messages = []
            for msg_id, msg_data in messages_map.items():
                messages.append(msg_data)
            
            context_parts = []
            context_parts.append(f"聊天标题: {chat.title}")
            context_parts.append(f"问题消息ID: {message_id}")
            
            # 添加最近的消息上下文
            for msg in messages[-5:]:  # 最近5条消息
                role = "用户" if msg.get("role") == "user" else "AI助手"
                content = msg.get("content", "")
                if len(content) > 200:
                    content = content[:200] + "..."
                context_parts.append(f"{role}: {content}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            log.error(f"Error getting chat context: {e}")
            return "获取对话上下文时出错"

    async def _get_full_chat_data(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取完整的对话数据"""
        try:
            meta = feedback_data.get("meta", {})
            chat_id = meta.get("chat_id")
            
            if not chat_id:
                return {"error": "无法获取聊天ID"}

            # 获取聊天记录
            chat = Chats.get_chat_by_id(chat_id)
            if not chat:
                return {"error": "聊天记录不存在"}

            # 获取所有消息
            messages_map = Chats.get_messages_map_by_chat_id(chat_id)
            if not messages_map:
                return {"error": "聊天记录不存在"}
            
            # 构建完整的对话数据
            chat_data = {
                "chat_id": chat_id,
                "title": chat.title,
                "created_at": chat.created_at,
                "updated_at": chat.updated_at,
                "messages": []
            }
            
            # 添加消息数据
            for msg_id, msg in messages_map.items():
                message_data = {
                    "id": msg_id,
                    "role": msg.get("role"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("timestamp"),
                    "model": msg.get("model"),
                    "parent_id": msg.get("parentId"),
                    "children_ids": msg.get("childrenIds", []),
                    "follow_ups": msg.get("followUps", []),
                    "done": msg.get("done", True)
                }
                chat_data["messages"].append(message_data)
            
            return chat_data
            
        except Exception as e:
            log.error(f"Error getting full chat data: {e}")
            return {"error": f"获取完整对话数据时出错: {str(e)}"}

    async def _analyze_manual_ticket_with_ai(
        self, 
        ticket_data: Dict[str, Any], 
        request=None,
        user=None
    ) -> Optional[Dict[str, Any]]:
        """为人工创建的工单生成AI分析"""
        try:
            # 从数据库获取工单配置
            from open_webui.models.ticket_config import TicketConfigs
            config = TicketConfigs.get_config()
            
            # 检查是否启用了AI工单生成
            if not config or not config.enabled:
                log.error("AI ticket generation is disabled, cannot generate analysis")
                raise Exception("AI ticket generation is disabled")
            
            # 使用配置中的模型和提示词
            model_name = config.model_id if config.model_id else "gpt-3.5-turbo"
            system_prompt = config.system_prompt if config.system_prompt else self.default_system_prompt
            
            # 构建分析提示
            analysis_prompt = f"""
请分析以下人工创建的工单并生成AI分析：

工单信息：
- 标题: {ticket_data['title']}
- 描述: {ticket_data['description']}
- 优先级: {ticket_data['priority']}
- 分类: {ticket_data['category']}
- 标签: {', '.join(ticket_data['tags']) if ticket_data['tags'] else '无'}
- 创建者: {ticket_data['user_name']}
- 创建时间: {ticket_data['created_at']}

请根据以上信息生成AI分析，包括：
1. 问题描述（用户视角）
2. 问题分析（技术视角）
3. 优先级评估
4. 分类建议
5. 相关标签

请严格只返回一个JSON对象，格式如下：
{{
    "description": "问题描述部分：用户反馈、问题现象、期望结果、实际结果、影响范围",
    "analysis": "问题分析部分：技术分析、根本原因、影响评估、解决建议、相关技术",
    "priority": "urgent|high|medium|low",
    "category": "bug|feature_request|general_inquiry|technical_support|other",
    "tags": ["技术标签", "模块标签", "严重程度", "问题类型"]
}}
"""

            # 准备AI请求数据
            ai_request_data = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                "stream": False,
                "temperature": 0.3,
                "max_tokens": 8000,
                "response_format": {"type": "json_object"}
            }

            # 调用AI生成分析
            if request and user:
                response = await generate_chat_completion(request, ai_request_data, user)
            else:
                # 如果没有request对象，使用默认方式
                import requests
                import os
                from open_webui.env import OPENAI_API_BASE, OPENAI_API_KEY
                
                headers = {
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    f"{OPENAI_API_BASE}/chat/completions",
                    headers=headers,
                    json=ai_request_data,
                    timeout=30
                )
                
                if response.status_code != 200:
                    log.error(f"AI API request failed: {response.status_code} - {response.text}")
                    return None
                
                response = response.json()

            # 解析AI响应
            if response and "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
                log.info(f"AI analysis response: {content}")
                
                try:
                    ai_analysis = json.loads(content)
                    log.info(f"Successfully parsed AI analysis: {ai_analysis}")
                    return ai_analysis
                except json.JSONDecodeError as e:
                    log.error(f"Failed to parse AI response as JSON: {e}")
                    log.error(f"AI response content: {content}")
                    # 尝试从内容中提取有用信息作为fallback
                    log.warning("Using fallback analysis data due to JSON parsing error")
                    return self._get_fallback_manual_analysis(ticket_data)
            else:
                log.error("No valid response from AI service")
                log.warning("Using fallback analysis data due to no valid response")
                return self._get_fallback_manual_analysis(ticket_data)

        except Exception as e:
            log.error(f"Error analyzing manual ticket with AI: {e}")
            log.error(f"Exception type: {type(e).__name__}")
            log.error(f"Exception details: {str(e)}")
            return self._get_fallback_manual_analysis(ticket_data)

    def _get_fallback_manual_analysis(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """为人工工单生成fallback分析数据"""
        description = f"用户反馈: {ticket_data['description']}\n\n问题现象: 用户报告了具体问题\n期望结果: 希望问题得到解决\n实际结果: 问题尚未解决\n影响范围: 影响用户正常使用"
        
        analysis = f"技术分析: 需要进一步分析用户报告的问题\n根本原因: 待技术人员深入调查\n影响评估: 根据问题严重程度评估\n解决建议: 建议优先处理此工单\n相关技术: 需要根据具体问题确定"
        
        return {
            "description": description,
            "analysis": analysis,
            "priority": ticket_data.get('priority', 'medium'),
            "category": ticket_data.get('category', 'general_inquiry'),
            "tags": ticket_data.get('tags', []) + ["manual-ticket", "ai-analysis", "fallback"],
            "is_fallback": True,
            "fallback_reason": "AI service unavailable or failed"
        }

    async def _analyze_feedback_with_ai(
        self, 
        feedback_data: Dict[str, Any], 
        chat_context: str,
        request=None
    ) -> Optional[Dict[str, Any]]:
        """使用AI分析反馈并生成工单数据"""
        try:
            # 从数据库获取工单配置
            from open_webui.models.ticket_config import TicketConfigs
            config = TicketConfigs.get_config()
            
            # 检查是否启用了AI工单生成
            if not config or not config.enabled:
                log.error("AI ticket generation is disabled, cannot generate ticket")
                raise Exception("AI ticket generation is disabled")
            
            # 使用配置中的模型和提示词
            model_name = config.model_id if config.model_id else "gpt-3.5-turbo"
            system_prompt = config.system_prompt if config.system_prompt else self.default_system_prompt
            
            # 构建分析提示
            analysis_prompt = f"""
请分析以下用户反馈并生成工单：

用户反馈数据：
{json.dumps(feedback_data, ensure_ascii=False, indent=2)}

对话上下文：
{chat_context}

请根据以上信息生成工单，并严格只返回一个JSON对象，不要包含多余文本、注释或代码块标记。
"""

            # 准备AI请求数据
            ai_request_data = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": analysis_prompt}
                ],
                "stream": False,
                "temperature": 0.3,
                "max_tokens": 8000,
                "response_format": {"type": "json_object"}
            }

            # 调用AI生成工单
            if request:
                try:
                    log.info(f"Calling AI service with model: {ai_request_data['model']}")
                    log.info(f"System prompt length: {len(system_prompt)}")
                    log.info(f"Analysis prompt length: {len(analysis_prompt)}")
                    log.info(f"AI request data: {json.dumps(ai_request_data, ensure_ascii=False, indent=2)}")
                    
                    from open_webui.utils.chat import generate_chat_completion
                    # 获取用户对象用于AI调用
                    user = Users.get_user_by_id(feedback_data.get("user_id"))
                    if not user:
                        log.error("User not found for AI call")
                        return self._get_fallback_ticket_data(feedback_data)
                    
                    log.info(f"User found: {user.name} ({user.email})")
                    # 添加超时处理，30秒超时
                    try:
                        response = await asyncio.wait_for(
                            generate_chat_completion(request, ai_request_data, user, bypass_filter=True),
                            timeout=30.0
                        )
                    except asyncio.TimeoutError:
                        log.error("AI service timeout after 30 seconds")
                        return self._get_fallback_ticket_data(feedback_data)
                    
                    log.info(f"AI service response type: {type(response)}")
                    log.info(f"AI service response: {response}")
                    
                    # 检查响应是否为异常对象
                    if isinstance(response, Exception):
                        log.error(f"AI service returned error: {response}")
                        raise Exception(f"AI service error: {response}")
                    elif response and isinstance(response, dict) and 'choices' in response:
                        # 处理OpenAI格式的响应
                        content = response['choices'][0]['message']['content']
                        log.info(f"AI response content length: {len(content)}")
                        log.info(f"AI response content preview: {content[:200]}...")
                        
                        # 尝试解析JSON响应
                        try:
                            # 提取JSON部分
                            json_start = content.find('{')
                            json_end = content.rfind('}') + 1
                            if json_start >= 0 and json_end > json_start:
                                json_str = content[json_start:json_end]
                                log.info(f"Extracted JSON: {json_str}")
                                ticket_data = json.loads(json_str)
                                log.info(f"Successfully parsed AI response: {ticket_data}")
                                return ticket_data
                            else:
                                log.error("No JSON found in AI response")
                                log.warning("Using fallback ticket data due to no JSON found")
                                return self._get_fallback_ticket_data(feedback_data)
                        except json.JSONDecodeError as e:
                            log.error(f"Failed to parse AI response as JSON: {e}")
                            log.error(f"AI response content: {content}")
                            # 尝试从内容中提取有用信息作为fallback
                            log.warning("Using fallback ticket data due to JSON parsing error")
                            return self._get_fallback_ticket_data(feedback_data)
                    elif response and hasattr(response, 'choices'):
                        # 处理对象格式的响应
                        content = response.choices[0].message.content
                        log.info(f"AI response content length: {len(content)}")
                        log.info(f"AI response content preview: {content[:200]}...")
                        
                        # 尝试解析JSON响应
                        try:
                            # 提取JSON部分
                            json_start = content.find('{')
                            json_end = content.rfind('}') + 1
                            if json_start >= 0 and json_end > json_start:
                                json_str = content[json_start:json_end]
                                log.info(f"Extracted JSON: {json_str}")
                                ticket_data = json.loads(json_str)
                                log.info(f"Successfully parsed AI response: {ticket_data}")
                                return ticket_data
                            else:
                                log.error("No JSON found in AI response")
                                log.warning("Using fallback ticket data due to no JSON found")
                                return self._get_fallback_ticket_data(feedback_data)
                        except json.JSONDecodeError as e:
                            log.error(f"Failed to parse AI response as JSON: {e}")
                            log.error(f"AI response content: {content}")
                            # 尝试从内容中提取有用信息作为fallback
                            log.warning("Using fallback ticket data due to JSON parsing error")
                            return self._get_fallback_ticket_data(feedback_data)
                    else:
                        log.error("AI service returned unexpected response format")
                        log.error(f"Response: {response}")
                        raise Exception(f"AI service returned unexpected response format: {response}")
                except Exception as e:
                    log.error(f"Error calling AI service: {e}")
                    import traceback
                    log.error(f"Traceback: {traceback.format_exc()}")
                    raise Exception(f"AI service call failed: {e}")
            else:
                log.error("No request object provided, cannot generate AI ticket")
                raise Exception("No request object provided")

        except Exception as e:
            log.error(f"Error analyzing feedback with AI: {e}")
            raise Exception(f"AI analysis failed: {e}")

    def _get_fallback_ticket_data(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取fallback工单数据"""
        # 生成简洁的描述，不包含JSON数据
        description = "用户对AI回复不满意，需要人工处理。"
        
        # 尝试从反馈数据中提取用户评论
        if feedback_data.get('data'):
            comment = feedback_data['data'].get('comment')
            reason = feedback_data['data'].get('reason')
            
            if comment and comment.strip():
                description = f"用户反馈：{comment.strip()}"
            elif reason and reason.strip():
                description = f"反馈原因：{reason.strip()}"
        
        return {
            "title": "AI回复质量问题反馈",
            "description": description,
            "analysis": "AI服务暂时不可用，需要人工分析用户反馈。建议检查AI服务状态和模型配置。",
            "priority": "medium",
            "category": "general_inquiry",
            "tags": ["ai-feedback", "auto-generated", "fallback"]
        }

    def _map_priority(self, priority_str: str) -> TicketPriority:
        """映射优先级字符串到枚举"""
        priority_map = {
            "low": TicketPriority.LOW,
            "medium": TicketPriority.MEDIUM,
            "high": TicketPriority.HIGH,
            "urgent": TicketPriority.URGENT
        }
        return priority_map.get(priority_str.lower(), TicketPriority.MEDIUM)

    def _map_category(self, category_str: str) -> TicketCategory:
        """映射分类字符串到枚举"""
        category_map = {
            "bug": TicketCategory.BUG,
            "feature_request": TicketCategory.FEATURE_REQUEST,
            "general_inquiry": TicketCategory.GENERAL_INQUIRY,
            "technical_support": TicketCategory.TECHNICAL_SUPPORT,
            "other": TicketCategory.OTHER
        }
        return category_map.get(category_str.lower(), TicketCategory.GENERAL_INQUIRY)

    async def _update_existing_ticket(
        self, 
        existing_ticket: TicketModel, 
        feedback_data: Dict[str, Any], 
        user_id: str,
        request=None
    ) -> Optional[TicketModel]:
        """
        更新现有工单
        
        Args:
            existing_ticket: 现有工单
            feedback_data: 新的反馈数据
            user_id: 用户ID
            request: FastAPI请求对象
            
        Returns:
            更新后的工单对象
        """
        try:
            # 获取对话上下文
            chat_context = self._get_chat_context(feedback_data)
            
            # 获取完整的对话数据
            full_chat_data = await self._get_full_chat_data(feedback_data)
            
            # 使用AI分析反馈并生成工单数据
            ticket_data = await self._analyze_feedback_with_ai(
                feedback_data, chat_context, request
            )
            
            if not ticket_data:
                log.error("Failed to generate ticket data from AI for update")
                return existing_ticket

            # 合并AI分析结果和完整对话数据
            complete_feedback_data = {
                "id": feedback_data.get("id"),
                "user_id": feedback_data.get("user_id"),
                "version": feedback_data.get("version"),
                "type": feedback_data.get("type"),
                "data": feedback_data.get("data", {}),
                "meta": feedback_data.get("meta", {}),
                "snapshot": feedback_data.get("snapshot", {}),
                "created_at": feedback_data.get("created_at"),
                "updated_at": feedback_data.get("updated_at")
            }
            
            ai_analysis_data = {
                **ticket_data,
                "feedback_data": complete_feedback_data,
                "chat_context": chat_context,
                "full_chat_data": full_chat_data
            }

            # 更新工单
            updates = {
                "title": ticket_data.get("title", existing_ticket.title),
                "description": ticket_data.get("description", existing_ticket.description),
                "priority": self._map_priority(ticket_data.get("priority", existing_ticket.priority)),
                "category": self._map_category(ticket_data.get("category", existing_ticket.category)),
                "tags": ticket_data.get("tags", existing_ticket.tags),
                "ai_analysis": ai_analysis_data,
                "updated_at": int(time.time())
            }
            
            updated_ticket = Tickets.update_ticket(existing_ticket.id, updates)
            
            if updated_ticket:
                log.info(f"Updated existing ticket {updated_ticket.id} for feedback {feedback_data.get('id')}")
                
                # 发送钉钉通知（更新通知）
                try:
                    from open_webui.services.notification_service import notification_service
                    await notification_service.notify_ticket_updated(updated_ticket)
                    log.info(f"Sent DingTalk update notification for ticket {updated_ticket.id}")
                except Exception as e:
                    log.error(f"Failed to send DingTalk update notification for ticket {updated_ticket.id}: {e}")
                
                return updated_ticket
            else:
                log.error("Failed to update ticket in database")
                return existing_ticket

        except Exception as e:
            log.error(f"Error updating existing ticket: {e}")
            return existing_ticket


# 创建全局实例
ai_ticket_service = AITicketService()
