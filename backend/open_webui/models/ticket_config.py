import time
from typing import Optional
from open_webui.internal.db import Base, JSONField, get_db
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, String, Text, Boolean


####################
# Ticket Config DB Schema
####################

class TicketConfig(Base):
    __tablename__ = "ticket_config"

    id = Column(String, primary_key=True, default="default")
    enabled = Column(Boolean, default=True)
    model_id = Column(String, nullable=False)
    system_prompt = Column(Text, nullable=False)
    created_at = Column(String, default=lambda: str(int(time.time())))
    updated_at = Column(String, default=lambda: str(int(time.time())))


class TicketConfigModel(BaseModel):
    id: str = "default"
    enabled: bool = True
    model_id: str
    system_prompt: str
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


####################
# Database Operations
####################

class TicketConfigTable:
    def get_config(self) -> Optional[TicketConfigModel]:
        """获取工单配置"""
        try:
            with get_db() as db:
                config = db.query(TicketConfig).filter_by(id="default").first()
                if config:
                    return TicketConfigModel.model_validate(config)
                return None
        except Exception as e:
            print(f"Error getting ticket config: {e}")
            return None

    def save_config(self, config_data: dict) -> bool:
        """保存工单配置"""
        try:
            with get_db() as db:
                # 检查是否存在
                existing = db.query(TicketConfig).filter_by(id="default").first()
                
                if existing:
                    # 更新现有配置
                    existing.enabled = config_data.get("enabled", True)
                    existing.model_id = config_data.get("model_id", "")
                    existing.system_prompt = config_data.get("system_prompt", "")
                    existing.updated_at = str(int(time.time()))
                else:
                    # 创建新配置
                    config = TicketConfig(
                        id="default",
                        enabled=config_data.get("enabled", True),
                        model_id=config_data.get("model_id", ""),
                        system_prompt=config_data.get("system_prompt", ""),
                        created_at=str(int(time.time())),
                        updated_at=str(int(time.time()))
                    )
                    db.add(config)
                
                db.commit()
                return True
        except Exception as e:
            print(f"Error saving ticket config: {e}")
            return False

    def get_default_config(self) -> TicketConfigModel:
        """获取默认配置"""
        return TicketConfigModel(
            id="default",
            enabled=True,
            model_id="gpt-3.5-turbo",
            system_prompt="""你是一个专业的AI工单分析专家，专门处理用户对AI回复的负面反馈。你的任务是深度分析用户反馈，生成高质量的结构化工单。

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
- 确保JSON格式正确，字段完整""",
            created_at=str(int(time.time())),
            updated_at=str(int(time.time()))
        )


TicketConfigs = TicketConfigTable()
