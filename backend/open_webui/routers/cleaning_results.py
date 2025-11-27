from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from open_webui.internal.db import get_db
from open_webui.models.cleaning_result import CleaningResult
from open_webui.models.users import User
from open_webui.models.knowledge import Knowledge
from open_webui.utils.auth import get_current_user
import uuid
import time
import os
import urllib.parse
from open_webui.config import UPLOAD_DIR

router = APIRouter()

@router.get("/cleaning-results")
async def get_cleaning_results(
    knowledgeId: str = Query(..., description="知识库ID"),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取指定知识库的清洗结果列表"""
    try:
        # 验证知识库是否存在且用户有权限
        knowledge = db.query(Knowledge).filter(
            Knowledge.id == knowledgeId,
            Knowledge.user_id == user_id.id
        ).first()
        
        if not knowledge:
            raise HTTPException(status_code=404, detail="知识库不存在或无权限访问")
        
        # 获取清洗结果列表
        results = db.query(CleaningResult).filter(
            CleaningResult.knowledgeId == knowledgeId
        ).order_by(CleaningResult.created_at.desc()).all()
        
        return {
            "success": True,
            "data": [result.to_dict() for result in results]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取清洗结果失败: {str(e)}")

@router.post("/cleaning-results")
async def create_cleaning_result(
    knowledgeId: str,
    source_fileName: str,
    source_file_path: str,
    source_file_size: Optional[int] = None,
    result_folder_path: str = "mineru/",
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新的清洗结果记录"""
    try:
        # 验证知识库是否存在且用户有权限
        knowledge = db.query(Knowledge).filter(
            Knowledge.id == knowledgeId,
            Knowledge.user_id == user_id.id
        ).first()
        
        if not knowledge:
            raise HTTPException(status_code=404, detail="知识库不存在或无权限访问")
        
        # 检查是否已存在相同的清洗结果
        existing = db.query(CleaningResult).filter(
            CleaningResult.knowledgeId == knowledgeId,
            CleaningResult.source_fileName == source_fileName
        ).first()
        
        if existing:
            return {
                "success": True,
                "data": existing.to_dict(),
                "message": "清洗结果已存在"
            }
        
        # 创建新的清洗结果记录
        cleaning_result = CleaningResult.create_from_processing(
            knowledgeId=knowledgeId,
            user_id=user_id.id,
            source_fileName=source_fileName,
            source_file_path=source_file_path,
            source_file_size=source_file_size,
            result_folder_path=result_folder_path
        )
        
        db.add(cleaning_result)
        db.commit()
        db.refresh(cleaning_result)
        
        return {
            "success": True,
            "data": cleaning_result.to_dict(),
            "message": "清洗结果记录创建成功"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建清洗结果失败: {str(e)}")

@router.put("/cleaning-results/{result_id}")
async def update_cleaning_result(
    result_id: str,
    processing_status: Optional[str] = None,
    markdown_file_path: Optional[str] = None,
    error_message: Optional[str] = None,
    processing_log: Optional[str] = None,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新清洗结果记录"""
    try:
        # 查找清洗结果记录
        cleaning_result = db.query(CleaningResult).filter(
            CleaningResult.id == result_id,
            CleaningResult.user_id == user_id.id
        ).first()
        
        if not cleaning_result:
            raise HTTPException(status_code=404, detail="清洗结果不存在或无权限访问")
        
        # 更新字段
        if processing_status:
            cleaning_result.processing_status = processing_status
            
            if processing_status == "processing":
                cleaning_result.mark_processing_started()
            elif processing_status == "completed":
                cleaning_result.mark_completed(markdown_file_path, processing_log)
            elif processing_status == "failed":
                cleaning_result.mark_failed(error_message or "", processing_log)
        
        if markdown_file_path:
            cleaning_result.markdown_file_path = markdown_file_path
        if error_message:
            cleaning_result.error_message = error_message
        if processing_log:
            cleaning_result.processing_log = processing_log
            
        cleaning_result.updated_at = int(time.time())
        
        db.commit()
        db.refresh(cleaning_result)
        
        return {
            "success": True,
            "data": cleaning_result.to_dict(),
            "message": "清洗结果更新成功"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"更新清洗结果失败: {str(e)}")

@router.delete("/cleaning-results/{result_id}")
async def delete_cleaning_result(
    result_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除清洗结果记录"""
    try:
        # 查找清洗结果记录
        cleaning_result = db.query(CleaningResult).filter(
            CleaningResult.id == result_id,
            CleaningResult.user_id == user_id.id
        ).first()
        
        if not cleaning_result:
            raise HTTPException(status_code=404, detail="清洗结果不存在或无权限访问")
        
        db.delete(cleaning_result)
        db.commit()
        
        return {
            "success": True,
            "message": "清洗结果删除成功"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除清洗结果失败: {str(e)}")

@router.get("/cleaning-results/{result_id}")
async def get_cleaning_result(
    result_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个清洗结果详情"""
    try:
        # 查找清洗结果记录
        cleaning_result = db.query(CleaningResult).filter(
            CleaningResult.id == result_id,
            CleaningResult.user_id == user_id.id
        ).first()
        
        if not cleaning_result:
            raise HTTPException(status_code=404, detail="清洗结果不存在或无权限访问")
        
        return {
            "success": True,
            "data": cleaning_result.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取清洗结果失败: {str(e)}")

@router.get("/existing-segments")
async def get_existing_segments(
    knowledgeId: str = Query(..., description="知识库ID"),
    fileName: str = Query(..., description="文件名")
):
    """获取已存在的分段文件"""
    try:
        
        # 构建segment目录路径
        knowledge_base_dir = os.path.join(UPLOAD_DIR, "knowledge", knowledgeId)
        segment_dir = os.path.join(knowledge_base_dir, "segment")
        
        if not os.path.exists(segment_dir):
            return {"segments": []}
        
        # 从文件名中提取清理后的名称
        original_name = fileName.replace('.md', '').replace('_manual', '')
        clean_name = original_name.split('/')[-1]  # 只取文件名部分
        file_segments_dir = os.path.join(segment_dir, f"{clean_name}_segments")
        
        if not os.path.exists(file_segments_dir):
            return {"segments": []}
        
        # 读取分段文件
        segments = []
        for item in os.listdir(file_segments_dir):
            if item.endswith('.md'):
                item_path = os.path.join(file_segments_dir, item)
                try:
                    with open(item_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 提取标题（去掉序号前缀）
                    import re
                    title = re.sub(r'^\d+_', '', item.replace('.md', ''))
                    
                    segments.append({
                        "title": title,
                        "fileName": f"segment/{clean_name}_segments/{item}",
                        "content": content[:100] + "..." if len(content) > 100 else content
                    })
                except Exception as e:
                    continue
        
        return {"segments": segments}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分段文件失败: {str(e)}")

@router.post("/save-segment")
async def save_segment(
    request: Request
):
    """保存分段文件"""
    try:
        data = await request.json()
        knowledgeId = data.get("knowledgeId")
        fileName = data.get("fileName")
        content = data.get("content")
        
        if not all([knowledgeId, fileName, content]):
            raise HTTPException(status_code=400, detail="缺少必要参数")
        
        # 构建文件路径
        knowledge_base_dir = os.path.join(UPLOAD_DIR, "knowledge", knowledgeId)
        file_path = os.path.join(knowledge_base_dir, fileName)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 保存文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {"success": True, "message": "分段保存成功"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存分段失败: {str(e)}")

@router.get("/test-segment")
async def test_segment(
    knowledgeId: str = Query(..., description="知识库ID"),
    user_id: str = Depends(get_current_user)
):
    """测试segment目录"""
    try:
        knowledge_base_dir = os.path.join(UPLOAD_DIR, "knowledge", knowledgeId)
        segment_dir = os.path.join(knowledge_base_dir, "segment")

        result = {
            "knowledge_base_dir": knowledge_base_dir,
            "segment_dir": segment_dir,
            "segment_exists": os.path.exists(segment_dir)
        }

        if os.path.exists(segment_dir):
            files = []
            for item in os.listdir(segment_dir):
                item_path = os.path.join(segment_dir, item)
                if os.path.isdir(item_path):
                    files.append(item)
            result["segment_folders"] = files

        return result
    except Exception as e:
        return {"error": str(e)}

async def segment_markdown_file(
    request: Request,
    db: Session = Depends(get_db)
):
    """对Markdown文件进行分段处理"""
    try:
        data = await request.json()
        knowledgeId = data.get("knowledgeId")
        fileName = data.get("fileName")
        content = data.get("content")
        rules = data.get("rules", {"h1": True, "h2": True, "h3": True})
        
        if not all([knowledgeId, fileName, content]):
            raise HTTPException(status_code=400, detail="缺少必要参数")
        
        # 验证知识库是否存在（简化权限验证）
        knowledge_base_dir = os.path.join(UPLOAD_DIR, "knowledge", knowledgeId)
        if not os.path.exists(knowledge_base_dir):
            raise HTTPException(status_code=404, detail="知识库不存在")
        
        # 构建文件路径 - 保存到知识库根目录的segment文件夹
        knowledge_base_dir = os.path.join(UPLOAD_DIR, "knowledge", knowledgeId)
        segments_dir = os.path.join(knowledge_base_dir, "segment")
        os.makedirs(segments_dir, exist_ok=True)
        
        # 解析Markdown内容并分段
        segments = parse_markdown_segments(content, rules)
        
        # 创建具体文件的分段文件夹
        original_name = fileName.replace('.md', '').replace('_manual', '')
        # 清理文件名，移除路径分隔符
        clean_name = original_name.split('/')[-1]  # 只取文件名部分
        file_segments_dir = os.path.join(segments_dir, f"{clean_name}_segments")
        os.makedirs(file_segments_dir, exist_ok=True)
        
        # 保存每个分段
        saved_segments = []
        skipped_count = 0
        for i, segment in enumerate(segments):
            # 过滤掉标题为空或内容为空的分段
            segment_content = segment.get('content', '').strip()
            segment_title = segment.get('title', '').strip()
            
            if not segment_title or not segment_content:
                skipped_count += 1
                print(f"[跳过] 第 {i+1} 个分段，标题: {segment_title[:30]}, 内容长度: {len(segment_content)}")
                continue
            
            segment_fileName = f"{i+1:02d}_{segment_title}.md"
            
            # 清理文件名中的特殊字符
            segment_fileName = clean_filename(segment_fileName)
            segment_file_path = os.path.join(file_segments_dir, segment_fileName)
            
            with open(segment_file_path, 'w', encoding='utf-8') as f:
                f.write(segment_content)
            
            saved_segments.append({
                "title": segment_title,
                "fileName": f"segment/{clean_name}_segments/{segment_fileName}",
                "content": segment_content[:100] + "..." if len(segment_content) > 100 else segment_content
            })
        
        print(f"[统计] 总分段数: {len(segments)}, 跳过: {skipped_count}, 有效: {len(saved_segments)}")
        
        return {
            "success": True,
            "segments": saved_segments,
            "message": f"成功分段为 {len(saved_segments)} 个文件"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分段处理失败: {str(e)}")


def parse_markdown_segments(content: str, rules: dict) -> list:
    """解析Markdown内容并分段 - 面包屑策略"""
    # 调试：输出rules
    print(f"[分段规则] rules = {rules}")
    
    lines = content.split('\n')
    segments = []
    current_segment = []
    current_title = ""
    
    # 维护标题层级栈，用于生成面包屑路径
    title_stack = []  # [(level, title), ...]
    
    for line in lines:
        # 检查是否是标题行 - 从最深层级到最浅层级检测
        is_header = False
        header_level = 0
        
        # 调试：输出原始行和检测结果
        if line.strip().startswith('#'):
            print(f"[检测] 行内容: {repr(line[:50])}")
        
        # 必须从最深层级（6个#）到最浅层级（1个#）检测，否则会被错误匹配
        if rules.get('h6', False) and line.startswith('###### '):
            is_header = True
            header_level = 6
        elif rules.get('h5', False) and line.startswith('##### '):
            is_header = True
            header_level = 5
        elif rules.get('h4', False) and line.startswith('#### '):
            is_header = True
            header_level = 4
        elif rules.get('h3', True) and line.startswith('### '):
            is_header = True
            header_level = 3
        elif rules.get('h2', True) and line.startswith('## '):
            is_header = True
            header_level = 2
        elif rules.get('h1', True) and line.startswith('# '):
            is_header = True
            header_level = 1
        
        if is_header:
            # 保存当前分段
            if current_segment and current_title:
                segments.append({
                    "title": current_title,
                    "content": '\n'.join(current_segment)
                })
            
            # 提取标题文本：去掉所有开头的 # 号和空格
            title_text = line.lstrip('#').strip()
            
            # 更新标题栈：移除同级及更深层级的标题，添加新标题
            while title_stack and title_stack[-1][0] >= header_level:
                title_stack.pop()
            title_stack.append((header_level, title_text))
            
            # 生成面包屑路径标题
            breadcrumb = " > ".join([title for _, title in title_stack])
            current_title = breadcrumb
            current_segment = [line]
            
            print(f"[面包屑] Level {header_level}, 标题: {title_text}")
            print(f"[面包屑] 标题栈: {[(l, t) for l, t in title_stack]}")
            print(f"[面包屑] 生成路径: {breadcrumb}")
        else:
            # 添加到当前分段
            current_segment.append(line)
    
    # 保存最后一个分段
    if current_segment and current_title:
        segments.append({
            "title": current_title,
            "content": '\n'.join(current_segment)
        })
    
    return segments

def clean_filename(filename: str) -> str:
    """清理文件名中的特殊字符"""
    import re
    # 移除或替换特殊字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'[^\w\s\-_\.]', '', filename)
    filename = filename.strip()
    return filename

