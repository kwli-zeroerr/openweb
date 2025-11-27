from fastapi import APIRouter, HTTPException, Request, Depends, Query, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging
import uuid
import time

from open_webui.services.langchain_rag_service import (
    get_langchain_rag_service,
)
from open_webui.services.ragflow.chunk_management import get_client as get_ragflow_chunk_client
from open_webui.services.ragflow.dataset_management import get_client as get_ragflow_dataset_client
from open_webui.services.ragflow.file_management import get_client as get_ragflow_file_client
from open_webui.models.knowledge import Knowledges
from open_webui.models.files import Files, FileForm
from open_webui.utils.auth import get_verified_user
from open_webui.routers.retrieval import save_docs_to_vector_db
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

router = APIRouter()

class ExcelExtractRequest(BaseModel):
    dir_path: Optional[str] = None
    limit_per_file: Optional[int] = 1000

class ExcelSegment(BaseModel):
    file: str
    sheet: str
    row: int
    title: str
    content: str
    questions: str

class ExcelExtractResponse(BaseModel):
    total_files: int
    total_segments: int
    segments: List[ExcelSegment]
    groups: Optional[List[Dict[str, Any]]] = None

class SaveExcelSegmentsRequest(BaseModel):
    knowledge_id: str
    dir_path: Optional[str] = None
    limit_per_file: Optional[int] = 2000

class SaveExcelSegmentsResponse(BaseModel):
    knowledge_id: str
    total_segments: int
    total_files_created: int
    file_ids: List[str]

class SavedExcelFile(BaseModel):
    file_id: str
    filename: str
    original_file: str
    sheet: str
    segment_count: int
    created_at: Optional[str] = None

class GetSavedExcelFilesResponse(BaseModel):
    knowledge_id: str
    knowledge_name: str
    total_files: int
    files: List[SavedExcelFile]

class SavedFileSegmentsResponse(BaseModel):
    file_id: str
    original_file: str
    sheets: List[Dict[str, Any]]  # [{ name, segments: [{title, content, questions}] }]

class ListExcelFilesRequest(BaseModel):
    """列出目录下Excel文件的请求"""
    dir_path: str  # 目录路径
    knowledge_id: Optional[str] = None  # 可选，用于构建知识库目录路径

class ListExcelFilesResponse(BaseModel):
    """列出目录下Excel文件的响应"""
    files: List[Dict[str, Any]]  # [{filename: str, size: int, mtime: float}]
    dir_path: str  # 实际使用的目录路径（相对或绝对）
    total: int  # 文件总数

class MigrateExcelDirectToRagFlowRequest(BaseModel):
    """直接从Excel文件或目录迁移到RAGFlow的请求"""
    dir_path: str  # 目录路径
    selected_files: List[str]  # 用户选择的文件名列表
    dataset_id: Optional[str] = None  # 如果提供，使用现有dataset；否则创建新dataset
    dataset_name: Optional[str] = None  # 创建新dataset时的名称
    document_name: Optional[str] = None  # 文档名称，默认为Excel文件名
    mode: Optional[str] = "skip"  # skip | overwrite
    limit_segments: Optional[int] = None  # 限制每个sheet处理的分段数量
    auto_delete_duplicates: Optional[bool] = True  # 自动删除重名的数据集或文档

class MigrateExcelDirectToRagFlowResponse(BaseModel):
    """直接从Excel文件迁移到RAGFlow的响应"""
    dataset_id: str
    document_id: str  # 保留第一个document_id作为参考
    documents: List[Dict[str, str]]  # 所有创建的documents: [{sheet_name, document_id}]
    files_processed: int
    sheets_processed: int
    segments_processed: int
    chunks_created: int
    message: str

# 已移除：测试工具相关的检索API（/list-collections, /query, /search/vector, /search/fulltext）


@router.post("/extract-excel", response_model=ExcelExtractResponse)
async def extract_excel(req: ExcelExtractRequest):
    """扫描目录内的 Excel 文件，按 sheet/列规则提取分段内容与问题（选填，单元格内一行一个）。"""
    try:
        import os
        import pandas as pd
        from pathlib import Path

        base_dir = req.dir_path or \
            "/home/zeroerr-ai72/openwebui-zeroerr/backend/data/uploads/knowledge/748b54f6-73b0-4efb-87c3-15c166556d6f/manual"
        p = Path(base_dir)
        if not p.exists() or not p.is_dir():
            raise HTTPException(status_code=400, detail=f"目录不存在: {base_dir}")

        xlsx_files = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in [".xlsx", ".xls"]]
        segments: List[Dict[str, Any]] = []
        grouped: List[Dict[str, Any]] = []

        for f in xlsx_files:
            try:
                excel_file = pd.ExcelFile(f)
            except Exception as e:
                logger.warning(f"跳过无法读取的文件 {f.name}: {e}")
                continue
        
            file_group = {"file": f.stem, "sheets": []}
            sheets_result: List[Dict[str, Any]] = []
            
            for sheet_idx, sheet_name in enumerate(excel_file.sheet_names):
                try:
                    df = pd.read_excel(f, sheet_name=sheet_name)
                except Exception as e:
                    logger.warning(f"跳过无法读取的Sheet {f.name}:{sheet_name}: {e}")
                    continue

                # 识别常见列名（优先级：精确匹配 > 包含关键词）
                cols = [str(c).strip() for c in df.columns]
                
                # 分段标题列：优先匹配"分段标题"，然后是包含"标题"的列
                title_cols = []
                for c in cols:
                    if "分段标题" in c or "segment" in c.lower() and "title" in c.lower():
                        title_cols.insert(0, c)  # 精确匹配优先
                    elif "标题" in c or "title" in c.lower():
                        title_cols.append(c)
                
                # 分段内容列：优先匹配"分段内容"，然后是包含"内容"的列
                content_cols = []
                for c in cols:
                    if "分段内容" in c or "segment" in c.lower() and "content" in c.lower():
                        content_cols.insert(0, c)  # 精确匹配优先
                    elif "内容" in c or "content" in c.lower():
                        content_cols.append(c)
                
                # 问题（选填，单元格内一行一个）列：优先匹配"问题（选填，单元格内一行一个）"，然后是包含"问题"的列
                question_cols = []
                for c in cols:
                    if "问题（选填，单元格内一行一个）" in c or "associated" in c.lower() and "question" in c.lower():
                        question_cols.insert(0, c)  # 精确匹配优先
                    elif "问题" in c or "question" in c.lower():
                        question_cols.append(c)
                
                # 日志：记录识别到的列
                if not title_cols or not content_cols:
                    logger.warning(f"Sheet {f.name}:{sheet_name} 列识别不完整 - 所有列: {cols}, 标题列: {title_cols}, 内容列: {content_cols}, 问题列: {question_cols}")

                sheet_segments: List[Dict[str, Any]] = []
                for idx, row in df.iterrows():
                    title = ""
                    content = ""
                    questions = ""

                    for c in title_cols[:1]:
                        val = row.get(c)
                        if pd.notna(val):
                            title = str(val).strip()
                            break

                    for c in content_cols[:1]:
                        val = row.get(c)
                        if pd.notna(val):
                            content = str(val)
                            break

                    for c in question_cols[:1]:
                        val = row.get(c)
                        if pd.notna(val):
                            questions = str(val)
                            break

                    if content and content.strip():
                        seg = {
                            "file": f.stem,
                            "sheet": sheet_name,
                            "row": int(idx) if isinstance(idx, (int, float)) else 0,
                            "title": title,
                            "content": content,
                            "questions": questions,
                        }
                        segments.append(seg)
                        sheet_segments.append(seg)

                # 按行号排序该sheet分段
                sheet_segments.sort(key=lambda s: s.get("row", 0))
                
                sheet_info = {
                    "name": sheet_name,
                    "count": len(sheet_segments),
                    "segments": sheet_segments,
                }
                
                sheets_result.append(sheet_info)
            
            # 直接按Sheet作为章节，不做分组
            file_group["sheets"] = sheets_result
            grouped.append(file_group)

        return ExcelExtractResponse(
            total_files=len(xlsx_files),
            total_segments=len(segments),
            segments=[ExcelSegment(**s) for s in segments],
            groups=grouped
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"extract_excel failed: {e}")
        raise HTTPException(status_code=500, detail=f"extract_excel失败: {e}")


@router.post("/save-excel-segments", response_model=SaveExcelSegmentsResponse)
async def save_excel_segments(req: SaveExcelSegmentsRequest, user=Depends(get_verified_user)):
    """提取目录内Excel分段，并将每个Excel聚合为一个file写入知识库。

    要求：以原始 Excel 文件名作为“合集名”（一个文件），其中文本内容按 sheet（章节）顺序聚合，
    sheet 内再按行号（小章节/分段）顺序拼接。
    """
    try:
        # 校验知识库
        knowledge = Knowledges.get_knowledge_by_id(id=req.knowledge_id)
        if not knowledge:
            raise HTTPException(status_code=404, detail=f"知识库不存在: {req.knowledge_id}")
        if knowledge.user_id != user.id:
            raise HTTPException(status_code=403, detail="无权写入该知识库")

        import pandas as pd
        from pathlib import Path
        base_dir = req.dir_path or \
            "/home/zeroerr-ai72/openwebui-zeroerr/backend/data/uploads/knowledge/748b54f6-73b0-4efb-87c3-15c166556d6f/manual"
        p = Path(base_dir)
        if not p.exists() or not p.is_dir():
            raise HTTPException(status_code=400, detail=f"目录不存在: {base_dir}")

        xlsx_files = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in [".xlsx", ".xls"]]
        file_ids: List[str] = []
        total_segments = 0

        # 构建已存在的“按Excel聚合”的文件索引，便于覆盖更新
        data = knowledge.data or {}
        existing_ids = list(data.get("file_ids", []))
        existing_metas = Files.get_file_metadatas_by_ids(existing_ids) if existing_ids else []
        original_to_file_id: Dict[str, str] = {}
        for fm in existing_metas:
            meta = (fm.meta or {})
            if meta.get("source") == "excel_extraction":
                # 旧的sheet级或新的聚合级都有 original_file
                original = meta.get("original_file")
                if original and original not in original_to_file_id:
                    original_to_file_id[original] = fm.id

        for f in xlsx_files:
            try:
                excel_file = pd.ExcelFile(f)
            except Exception as e:
                logger.warning(f"跳过无法读取的文件 {f.name}: {e}")
                continue

            workbook_total_segments = 0
            sheet_summaries: List[Dict[str, Any]] = []
            sheets_data: List[Dict[str, Any]] = []  # 保存完整的结构化数据
            parts: List[str] = []

            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(f, sheet_name=sheet_name)
                except Exception as e:
                    logger.warning(f"跳过无法读取的Sheet {f.name}:{sheet_name}: {e}")
                    continue

                # 识别常见列名（优先级：精确匹配 > 包含关键词）
                cols = [str(c).strip() for c in df.columns]
                
                # 分段标题列：优先匹配"分段标题"，然后是包含"标题"的列
                title_cols = []
                for c in cols:
                    if "分段标题" in c or "segment" in c.lower() and "title" in c.lower():
                        title_cols.insert(0, c)  # 精确匹配优先
                    elif "标题" in c or "title" in c.lower():
                        title_cols.append(c)
                
                # 分段内容列：优先匹配"分段内容"，然后是包含"内容"的列
                content_cols = []
                for c in cols:
                    if "分段内容" in c or "segment" in c.lower() and "content" in c.lower():
                        content_cols.insert(0, c)  # 精确匹配优先
                    elif "内容" in c or "content" in c.lower():
                        content_cols.append(c)
                
                # 问题（选填，单元格内一行一个）列：优先匹配"问题（选填，单元格内一行一个）"，然后是包含"问题"的列
                question_cols = []
                for c in cols:
                    if "问题（选填，单元格内一行一个）" in c or "associated" in c.lower() and "question" in c.lower():
                        question_cols.insert(0, c)  # 精确匹配优先
                    elif "问题" in c or "question" in c.lower():
                        question_cols.append(c)
                
                # 日志：记录识别到的列
                if not title_cols or not content_cols:
                    logger.warning(f"Sheet {f.name}:{sheet_name} 列识别不完整 - 所有列: {cols}, 标题列: {title_cols}, 内容列: {content_cols}, 问题列: {question_cols}")

                segments_content: List[Dict[str, Any]] = []
                for idx, row in df.iterrows():
                    title = ""; content = ""; questions = ""
                    for c in title_cols[:1]:
                        val = row.get(c)
                        if pd.notna(val):
                            title = str(val).strip(); break
                    for c in content_cols[:1]:
                        val = row.get(c)
                        if pd.notna(val):
                            content = str(val); break
                    for c in question_cols[:1]:
                        val = row.get(c)
                        if pd.notna(val):
                            questions = str(val); break
                    if content and content.strip():
                        segments_content.append({
                            "row": int(idx) if isinstance(idx, (int, float)) else 0,
                            "title": title,
                            "content": content,
                            "questions": questions,
                        })

                if not segments_content:
                            continue
        
                segments_content.sort(key=lambda s: s.get("row", 0))
                workbook_total_segments += len(segments_content)
                
                # 保存完整的结构化数据
                sheet_data = {
                    "name": sheet_name,
                    "segment_count": len(segments_content),
                    "segments": segments_content  # 保存完整的分段数据
                }
                sheets_data.append(sheet_data)
                
                # 同时生成Markdown格式用于展示（兼容性）
                # 注意：为避免把“问题（选填，单元格内一行一个）”混入分段内容，此处仅输出标题与内容，不再拼接问题到内容文本
                sheet_block = [f"# {sheet_name}"]
                for s in segments_content:
                    seg_title = s['title'] or ("分段 " + str(s['row']))
                    content_block = f"## {seg_title}\n{s['content']}"
                    sheet_block.append(content_block)
                parts.append("\n\n".join(sheet_block))
                
                # 保留summary用于兼容
                sheet_summaries.append({
                    "name": sheet_name,
                    "segment_count": len(segments_content)
                })

            if workbook_total_segments == 0:
                continue

            total_segments += workbook_total_segments
            file_content = "\n\n".join(parts)

            # 覆盖已有：如该原始文件已存在，则删除旧记录后再写入
            old_id = original_to_file_id.get(f.stem)
            if old_id:
                try:
                    Files.delete_file_by_id(old_id)
                except Exception:
                    pass
            file_id = str(uuid.uuid4())
            filename = f"{f.stem}.txt"
            file_form = FileForm(
                id=file_id,
                filename=filename,
                path="",
                data={
                    "type": "excel_segment_aggregated",
                    "source_file": f.stem,
                    "sheets": sheet_summaries,  # 保留用于兼容
                    "sheets_data": sheets_data,  # 新增：完整的结构化数据
                    "segment_count": workbook_total_segments,
                    "content": file_content  # Markdown格式，用于兼容
                },
                meta={
                    "name": filename,
                    "content_type": "text/plain",
                    "size": len(file_content.encode('utf-8')),
                    "source": "excel_extraction",
                    "original_file": f.stem
                },
                access_control=None
            )
            rec = Files.insert_new_file(user.id, file_form)
            if rec:
                file_ids.append(file_id)

        # 更新knowledge.data.file_ids（去重）
        existing = set((knowledge.data or {}).get("file_ids", []))
        # 移除被覆盖删除的旧ID
        for orig, old_id in original_to_file_id.items():
            if old_id in existing:
                existing.remove(old_id)
        for fid in file_ids:
            existing.add(fid)
        data["file_ids"] = list(existing)
        Knowledges.update_knowledge_data_by_id(id=req.knowledge_id, data=data)

        return SaveExcelSegmentsResponse(
            knowledge_id=req.knowledge_id,
            total_segments=total_segments,
            total_files_created=len(file_ids),
            file_ids=file_ids,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"save_excel_segments failed: {e}")
        raise HTTPException(status_code=500, detail=f"保存Excel分段失败: {e}")


@router.get("/saved-excel-files/{knowledge_id}", response_model=GetSavedExcelFilesResponse)
async def get_saved_excel_files(knowledge_id: str, user=Depends(get_verified_user)):
    """获取指定知识库下所有已保存的Excel提取文件。"""
    try:
        knowledge = Knowledges.get_knowledge_by_id(id=knowledge_id)
        if not knowledge:
            raise HTTPException(status_code=404, detail="知识库不存在")
        if knowledge.user_id != user.id:
            raise HTTPException(status_code=403, detail="无权访问该知识库")

        # 获取知识库关联的所有文件
        file_ids = []
        if knowledge.data and knowledge.data.get("file_ids"):
            file_ids = knowledge.data.get("file_ids", [])

        # 筛选出Excel提取的文件（需要 data.segment_count，改为取完整FileModel）
        excel_files = []
        file_models = Files.get_files_by_ids(file_ids)
        for f in file_models:
            try:
                meta = f.meta or {}
                if meta.get("source") == "excel_extraction":
                    data = f.data or {}
                    excel_files.append(SavedExcelFile(
                        file_id=f.id,
                        filename=(meta.get("name") or f.filename or (meta.get("original_file", "") + ".txt") or f.id),
                        original_file=meta.get("original_file", ""),
                        sheet=meta.get("sheet", ""),
                        segment_count=(data.get("segment_count") or meta.get("segment_count") or 0),
                        created_at=str(getattr(f, 'created_at', "")) if getattr(f, 'created_at', None) else None
                    ))
            except Exception as e:
                logger.warning(f"处理文件 {getattr(f,'id','?')} 失败: {e}")
                continue

        # 按original_file和sheet排序
        excel_files.sort(key=lambda x: (x.original_file, x.sheet))

        return GetSavedExcelFilesResponse(
            knowledge_id=knowledge_id,
            knowledge_name=knowledge.name,
            total_files=len(excel_files),
            files=excel_files
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_saved_excel_files failed: {e}")
        raise HTTPException(status_code=500, detail=f"获取已保存文件失败: {e}")


# ========== RAGFlow 检索功能已迁移到 retrieval_api.py ==========

@router.post("/ragflow/list-excel-files", response_model=ListExcelFilesResponse)
async def list_excel_files(req: ListExcelFilesRequest, user=Depends(get_verified_user)):
    """列出指定目录下的所有Excel文件（仅返回文件名，不暴露完整路径）"""
    try:
        from pathlib import Path
        import os
        
        # 构建目录路径
        if req.knowledge_id:
            # 如果提供了knowledge_id，构建知识库目录路径
            base_dir = Path("/home/zeroerr-ai72/openwebui-zeroerr/backend/data/uploads/knowledge") / req.knowledge_id / "manual"
            if base_dir.exists():
                dir_path = base_dir
            else:
                # 如果不存在，尝试使用提供的dir_path
                dir_path = Path(req.dir_path)
        else:
            dir_path = Path(req.dir_path)
        
        if not dir_path.exists():
            raise HTTPException(status_code=400, detail=f"目录不存在: {req.dir_path}")
        
        if not dir_path.is_dir():
            raise HTTPException(status_code=400, detail=f"不是目录: {req.dir_path}")
        
        # 扫描Excel文件
        excel_files = []
        for item in dir_path.iterdir():
            if item.is_file() and item.suffix.lower() in [".xlsx", ".xls"]:
                stat = item.stat()
                excel_files.append({
                    "filename": item.name,  # 只返回文件名
                    "size": stat.st_size,
                    "mtime": stat.st_mtime
                })
        
        # 按文件名排序
        excel_files.sort(key=lambda x: x["filename"])
        
        return ListExcelFilesResponse(
            files=excel_files,
            dir_path=str(dir_path),  # 返回实际使用的目录路径
            total=len(excel_files)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出Excel文件失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"列出Excel文件失败: {e}")


@router.post("/ragflow/migrate-excel-direct", response_model=MigrateExcelDirectToRagFlowResponse)
async def migrate_excel_direct_to_ragflow(req: MigrateExcelDirectToRagFlowRequest, request: Request, user=Depends(get_verified_user)):
    """直接从Excel文件或目录迁移到RAGFlow，按照Sheet（章节）、分段标题、分段内容、问题的结构组织数据。
    
    规则：
    - 支持单个Excel文件或包含多个Excel文件的目录
    - 所有文件迁移到同一个dataset中
    - 每个Sheet（章节）作为独立的document，结构更清晰
    - 每个分段标题作为Sheet下的小标题
    - 分段内容作为小标题下的内容
    - 问题作为questions列表关联到内容chunk
    - 使用breadcrumb格式：文件名 > Sheet名称 > 分段标题
    """
    try:
        import pandas as pd
        from pathlib import Path
        import hashlib
        
        # 1. 获取RAGFlow客户端
        dataset_client = get_ragflow_dataset_client(request)
        file_client = get_ragflow_file_client(request)
        chunk_client = get_ragflow_chunk_client(request)
        
        # 2. 验证目录路径并构建文件列表
        dir_path = Path(req.dir_path)
        if not dir_path.exists():
            raise HTTPException(status_code=400, detail=f"目录不存在: {req.dir_path}")
        
        if not dir_path.is_dir():
            raise HTTPException(status_code=400, detail=f"不是目录: {req.dir_path}")
        
        if not req.selected_files:
            raise HTTPException(status_code=400, detail="请至少选择一个文件进行迁移")
        
        # 构建选中的Excel文件完整路径
        excel_files: List[Path] = []
        for filename in req.selected_files:
            file_path = dir_path / filename
            if not file_path.exists():
                logger.warning(f"文件不存在: {file_path}")
                continue
            if file_path.suffix.lower() not in [".xlsx", ".xls"]:
                logger.warning(f"不是有效的Excel文件: {filename}")
                continue
            excel_files.append(file_path)
        
        if not excel_files:
            raise HTTPException(status_code=400, detail="没有有效的Excel文件可迁移")
        
        excel_files.sort()  # 按文件名排序
        logger.info(f"将处理 {len(excel_files)} 个Excel文件: {[f.name for f in excel_files]}")
        
        # 3. 辅助函数：删除重名的dataset
        async def delete_duplicate_dataset(dataset_name: str):
            """删除指定名称的所有dataset"""
            if not req.auto_delete_duplicates:
                return
            try:
                import asyncio
                # 列出所有dataset，查找重名的
                all_datasets = await dataset_client.list()
                duplicate_ids = []
                for ds in all_datasets:
                    ds_name = ds.get("name")
                    ds_id = ds.get("id") or ds.get("dataset_id") or ds.get("_id")
                    if ds_name == dataset_name and ds_id:
                        duplicate_ids.append(ds_id)
                
                if duplicate_ids:
                    logger.info(f"发现重名dataset '{dataset_name}' ({len(duplicate_ids)}个)，正在批量删除...")
                    try:
                        # 使用批量删除API
                        result = await dataset_client.delete_many(ids=duplicate_ids)
                        if isinstance(result, dict) and result.get("code", 0) == 0:
                            logger.info(f"✓ 批量删除成功: {len(duplicate_ids)} 个dataset")
                        else:
                            logger.warning(f"删除dataset返回非零code: {result}")
                        await asyncio.sleep(1.5)
                        
                        # 验证删除
                        verify_datasets = await dataset_client.list()
                        remaining = [ds for ds in verify_datasets 
                                   if (ds.get("name") == dataset_name and 
                                       (ds.get("id") or ds.get("dataset_id") or ds.get("_id")) in duplicate_ids)]
                        if remaining:
                            remaining_ids = [ds.get("id") or ds.get("dataset_id") or ds.get("_id") 
                                            for ds in remaining]
                            logger.warning(f"删除后仍存在 {len(remaining)} 个重名dataset，尝试逐个删除")
                            for dup_id in remaining_ids:
                                try:
                                    await dataset_client.delete(dup_id)
                                except Exception:
                                    pass
                            await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.warning(f"批量删除失败，尝试逐个删除: {e}")
                        for dup_id in duplicate_ids:
                            try:
                                await dataset_client.delete(dup_id)
                            except Exception:
                                pass
                        await asyncio.sleep(1.0)
            except Exception as e:
                logger.warning(f"删除重名dataset时出错: {e}")
        
        # 4. 批量处理所有Excel文件
        # 注意：如果用户指定了dataset_id，所有文件都放入同一个dataset；否则为每个文件创建独立的dataset
        files_processed = 0
        sheets_processed = 0
        segments_processed = 0
        chunks_created = 0
        created_documents: List[Dict[str, str]] = []  # 存储所有创建的documents: [{file_name, sheet_name, document_id}]
        first_document_id = None
        created_dataset_ids: List[str] = []  # 存储所有创建的dataset_id
        
        # 去重控制：用于跨document的去重（可选，如果需要在dataset级别去重）
        existing_hashes = set()
        
        # 遍历所有Excel文件
        for excel_file_path in excel_files:
            original_file = excel_file_path.stem
            logger.info(f"开始处理Excel文件: {excel_file_path.name}")
            
            # 重要：为每个文件初始化dataset_id变量，确保每个文件都有独立的dataset_id
            current_file_dataset_id: Optional[str] = None
            
            # 为每个文件创建独立的dataset（如果用户没有指定dataset_id）
            if not req.dataset_id:
                # 确定该文件的dataset名称：优先使用用户指定的名称，否则使用文件名
                if req.dataset_name:
                    # 如果指定了dataset_name，但多个文件时应该为每个文件创建独立的数据集
                    # 除非用户明确希望所有文件放到一个数据集
                    # 这里我们假设：如果指定了dataset_name，只适用于第一个文件，其他文件使用文件名
                    if files_processed == 0:
                        file_dataset_name = req.dataset_name
                    else:
                        file_dataset_name = original_file
                else:
                    # 使用文件名（不含扩展名）作为dataset名称
                    file_dataset_name = original_file
                
                logger.info(f"准备为文件 '{excel_file_path.name}' 创建独立dataset: {file_dataset_name}")
                
                # 删除该文件对应的旧dataset（重要：每个文件都删除其对应的旧dataset）
                await delete_duplicate_dataset(file_dataset_name)
                
                # 创建新dataset
                max_retries = 3
                dataset_payload = None
                for attempt in range(max_retries):
                    try:
                        logger.info(f"为文件 '{excel_file_path.name}' 创建dataset: {file_dataset_name} (尝试 {attempt + 1}/{max_retries})")
                        dataset_payload = await dataset_client.create(name=file_dataset_name)
                        break
                    except RuntimeError as e:
                        error_msg = str(e)
                        # 如果是因为重名错误，尝试再次删除
                        if "already exists" in error_msg.lower() or "name" in error_msg.lower() and "exists" in error_msg.lower():
                            if req.auto_delete_duplicates and attempt < max_retries - 1:
                                logger.warning(f"创建dataset失败（可能是重名），尝试重新删除: {error_msg}")
                                await delete_duplicate_dataset(file_dataset_name)
                                import asyncio
                                await asyncio.sleep(0.5)  # 等待删除完成
                                continue
                            else:
                                raise
                        else:
                            raise
                
                if not dataset_payload:
                    logger.error(f"为文件 '{excel_file_path.name}' 创建dataset失败，跳过该文件")
                    continue
                
                # 从响应中提取dataset_id，确保正确处理不同的响应格式
                if isinstance(dataset_payload, dict):
                    current_file_dataset_id = str(dataset_payload.get("id") or dataset_payload.get("dataset_id") or dataset_payload.get("_id"))
                
                if not current_file_dataset_id:
                    logger.error(f"为文件 '{excel_file_path.name}' 创建dataset失败，无法获取dataset_id: {dataset_payload}")
                    continue
                
                created_dataset_ids.append(current_file_dataset_id)
                logger.info(f"✓ 成功为文件 '{excel_file_path.name}' 创建dataset: {current_file_dataset_id} (名称: {file_dataset_name})")
                # 确保后续处理使用当前文件的dataset_id
                dataset_id = current_file_dataset_id
            else:
                # 使用用户指定的dataset_id（所有文件都放入同一个dataset）
                dataset_id = req.dataset_id
                if dataset_id not in created_dataset_ids:
                    created_dataset_ids.append(dataset_id)
            
            # 验证dataset_id已正确设置
            if not dataset_id:
                logger.error(f"文件 '{excel_file_path.name}' 的dataset_id未设置，跳过该文件")
                continue
            
            # 确保使用当前文件的dataset_id（防止变量作用域问题）
            logger.debug(f"当前文件 '{excel_file_path.name}' 使用dataset_id: {dataset_id}")
            
            # 读取Excel文件
            try:
                excel_file = pd.ExcelFile(excel_file_path)
            except Exception as e:
                logger.warning(f"跳过无法读取的文件 {excel_file_path.name}: {e}")
                continue
            
            # 处理该文件的每个Sheet
            for sheet_idx, sheet_name in enumerate(excel_file.sheet_names):
                try:
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                except Exception as e:
                    logger.warning(f"跳过无法读取的Sheet {excel_file_path.name}:{sheet_name}: {e}")
                    continue
                
                # 识别列名
                cols = [str(c).strip() for c in df.columns]
                
                # 分段标题列
                title_cols = []
                for c in cols:
                    if "分段标题" in c or ("segment" in c.lower() and "title" in c.lower()):
                        title_cols.insert(0, c)
                    elif "标题" in c or "title" in c.lower():
                        title_cols.append(c)
                
                # 分段内容列
                content_cols = []
                for c in cols:
                    if "分段内容" in c or ("segment" in c.lower() and "content" in c.lower()):
                        content_cols.insert(0, c)
                    elif "内容" in c or "content" in c.lower():
                        content_cols.append(c)
                
                # 问题列
                question_cols = []
                for c in cols:
                    if "问题（选填，单元格内一行一个）" in c or ("associated" in c.lower() and "question" in c.lower()):
                        question_cols.insert(0, c)
                    elif "问题" in c or "question" in c.lower():
                        question_cols.append(c)
            
                if not content_cols:
                    logger.warning(f"Sheet {excel_file_path.name}:{sheet_name} 未找到内容列，跳过")
                    continue
                
                # 处理每个分段（行）
                sheet_segments = []
                for idx, row in df.iterrows():
                    title = ""
                    content = ""
                    questions = ""
                    
                    # 提取分段标题
                    for c in title_cols[:1]:
                        val = row.get(c)
                        if pd.notna(val):
                            title = str(val).strip()
                            break
                    
                    # 提取分段内容
                    for c in content_cols[:1]:
                        val = row.get(c)
                        if pd.notna(val):
                            content = str(val)
                            break
                    
                    # 提取问题
                    for c in question_cols[:1]:
                        val = row.get(c)
                        if pd.notna(val):
                            questions = str(val)
                            break
                    
                    if not content or not content.strip():
                        continue
                    
                    sheet_segments.append({
                        "row": int(idx) if isinstance(idx, (int, float)) else 0,
                        "title": title,
                        "content": content,
                        "questions": questions,
                    })
                
                # 限制分段数量
                if req.limit_segments is not None and req.limit_segments >= 0:
                    sheet_segments = sheet_segments[:req.limit_segments]
                
                # 如果没有分段，跳过该Sheet
                if not sheet_segments:
                    logger.warning(f"Sheet '{excel_file_path.name}:{sheet_name}' 没有有效分段，跳过")
                    continue
                
                # 按行号排序
                sheet_segments.sort(key=lambda s: s.get("row", 0))
                
                # 为该Sheet创建独立的document
                document_name = req.document_name or original_file
                # 确保文件名中的中文正确编码，使用UTF-8字符串
                # document名称格式：文件名_Sheet名称，便于识别来源
                sheet_doc_name = f"{original_file}_{sheet_name}"[:100]  # 限制长度，避免文件名过长
                
                # 检查是否有重名的document并删除
                if req.auto_delete_duplicates:
                    try:
                        existing_docs = await file_client.list(dataset_id=dataset_id, name=sheet_doc_name)
                        if existing_docs:
                            duplicate_ids = [doc.get("id") or doc.get("document_id") for doc in existing_docs 
                                           if doc.get("name") == sheet_doc_name]
                            if duplicate_ids:
                                logger.info(f"发现重名document '{sheet_doc_name}' ({len(duplicate_ids)}个)，正在删除...")
                                await file_client.delete(dataset_id=dataset_id, ids=duplicate_ids)
                                logger.info(f"已删除重名document: {duplicate_ids}")
                    except Exception as e:
                        logger.warning(f"检查/删除重名document失败: {e}，继续创建新document")
                
                # 重要：在创建document前再次确认dataset_id是当前文件的
                logger.info(f"为文件 '{excel_file_path.name}' 的Sheet '{sheet_name}' 创建document: {sheet_doc_name} (使用dataset_id: {dataset_id})")
                # 上传时文件名必须包含扩展名，使用sheet_doc_name作为基础（不包含扩展名）
                # 但为了保持一致性，我们在上传和更新时都保持相同的名称结构
                filename = f"{sheet_doc_name}.txt"
                # 确保文件名是UTF-8字符串（Python 3默认就是UTF-8，但显式确保）
                if isinstance(filename, bytes):
                    filename = filename.decode('utf-8')
                placeholder_content = f"Excel迁移文档 - 文件: {original_file} - Sheet: {sheet_name}"
                content_bytes = placeholder_content.encode("utf-8")
                doc_data = await file_client.upload(dataset_id=dataset_id, files=[(filename, content_bytes, "text/plain")])
                
                sheet_document_id = None
                if isinstance(doc_data, dict):
                    if doc_data.get("id"):
                        sheet_document_id = doc_data.get("id")
                    elif doc_data.get("document_id"):
                        sheet_document_id = doc_data.get("document_id")
                    elif doc_data.get("data") and isinstance(doc_data["data"], dict):
                        docs = doc_data["data"].get("documents") or doc_data["data"].get("docs") or []
                        if isinstance(docs, list) and docs:
                            sheet_document_id = docs[0].get("id")
                if not sheet_document_id and isinstance(doc_data, list) and doc_data:
                    sheet_document_id = doc_data[0].get("id")
                if not sheet_document_id:
                    logger.error(f"为Sheet '{excel_file_path.name}:{sheet_name}' 创建document失败: {doc_data}")
                    continue
                
                sheet_document_id = str(sheet_document_id)
                
                # RAGFlow不允许修改文件的扩展名
                # 上传时文件名是 "{sheet_doc_name}.txt"
                # 更新name字段时，必须保持相同的扩展名，否则会报错 "The extension of file can't be changed"
                # 解决方案：在更新name时也带上.txt扩展名，与上传时的文件名保持一致
                try:
                    # 使用带扩展名的名称更新（与上传时的filename保持一致）
                    await file_client.update(
                        dataset_id=dataset_id,
                        document_id=sheet_document_id,
                        name=filename  # 使用完整的文件名（包含.txt扩展名）
                    )
                    logger.debug(f"已更新Sheet '{sheet_name}' 的document名称为: {filename}")
                except Exception as e:
                    # 如果更新失败，也不影响功能，因为上传时已经使用了正确的中文文件名
                    logger.debug(f"更新document名称失败（不影响功能）: {e}")
                
                created_documents.append({"file_name": original_file, "sheet_name": sheet_name, "document_id": sheet_document_id})
                if not first_document_id:
                    first_document_id = sheet_document_id
                logger.info(f"Sheet '{excel_file_path.name}:{sheet_name}' 的document创建成功: {sheet_document_id} (名称: {sheet_doc_name})")
                
                # 如果overwrite模式，清空该document的现有chunks
                if (req.mode or "skip").lower() == "overwrite":
                    try:
                        await chunk_client.delete_chunks(dataset_id=dataset_id, document_id=sheet_document_id)
                        logger.debug(f"已清空Sheet '{sheet_name}' 的现有chunks（overwrite模式）")
                    except Exception as e:
                        logger.warning(f"清空Sheet '{sheet_name}' 的旧chunks失败（忽略继续）: {e}")
                
                # 处理该Sheet的所有分段
                for seg in sheet_segments:
                    title = (seg.get("title") or "").strip()
                    content = (seg.get("content") or "").strip()
                    questions_raw = (seg.get("questions") or "").strip()
                    row = seg.get("row", 0)
                    
                    if not content:
                        continue
                    
                    # 构建breadcrumb: 文件名 > Sheet名称 > 分段标题
                    breadcrumb = f"{original_file} > {sheet_name} > {title or ('行' + str(row))}"
                    
                    # 构建关键词
                    important_keywords = list(filter(None, [original_file, sheet_name, title]))
                    
                    # 处理问题：拆分为列表
                    questions_list = None
                    if questions_raw:
                        questions_list = [q.strip() for q in questions_raw.splitlines() if q and q.strip()]
                        if not questions_list:
                            questions_list = None
                    
                    # 只添加内容chunk（标题信息已在breadcrumb和keywords中，避免冗余）
                    try:
                        # breadcrumb已包含完整路径信息，直接使用内容即可
                        # 注意：content中的图片路径（如 /api/image/xxx）会被保留，确保前端可访问
                        content_text = f"{breadcrumb}: {content}"
                        h = hashlib.sha1(("C|" + content_text).encode("utf-8")).hexdigest()
                        
                        if (req.mode or "skip").lower() == "skip" and h in existing_hashes:
                            logger.debug(f"跳过重复chunk: {breadcrumb}")
                        else:
                            # 重要：在创建chunk前再次确认dataset_id是当前文件的
                            logger.debug(f"添加chunk到dataset_id={dataset_id}, document_id={sheet_document_id}, 文件={original_file}")
                            await chunk_client.add_chunk(
                                dataset_id=dataset_id,  # 确保使用当前文件的dataset_id
                                document_id=sheet_document_id,  # 使用当前Sheet的document_id
                                content=content_text,
                                important_keywords=important_keywords or None,
                                questions=questions_list,
                            )
                            chunks_created += 1
                            existing_hashes.add(h)
                            logger.debug(f"添加内容chunk成功: {breadcrumb}")
                    except Exception as e:
                        logger.warning(f"添加内容chunk失败 ({breadcrumb}, dataset_id={dataset_id}): {e}")
                    
                    segments_processed += 1
                
                sheets_processed += 1
                logger.info(f"文件 '{excel_file_path.name}' 的Sheet '{sheet_name}' 处理完成: {len(sheet_segments)} 个分段")
            
            files_processed += 1
            logger.info(f"Excel文件 '{excel_file_path.name}' 处理完成，共处理 {len(list(excel_file.sheet_names))} 个Sheet")
        
        # 构建结果消息
        files_desc = f"目录中的 {files_processed} 个Excel文件（已选择 {len(req.selected_files)} 个）"
        
        # 确定返回的dataset_id（如果有多个，返回第一个；如果用户指定了dataset_id，返回指定的）
        return_dataset_id = created_dataset_ids[0] if created_dataset_ids else (req.dataset_id if req.dataset_id else "")
        if len(created_dataset_ids) > 1:
            logger.info(f"共创建了 {len(created_dataset_ids)} 个dataset: {created_dataset_ids}")
        
        return MigrateExcelDirectToRagFlowResponse(
            dataset_id=return_dataset_id,
            document_id=first_document_id or "",  # 返回第一个document_id作为参考
            documents=created_documents,  # 返回所有创建的documents列表
            files_processed=files_processed,
            sheets_processed=sheets_processed,
            segments_processed=segments_processed,
            chunks_created=chunks_created,
            message=f"成功迁移 {files_desc}。共创建 {len(created_dataset_ids)} 个dataset，处理了 {sheets_processed} 个章节, {segments_processed} 个分段, 创建了 {len(created_documents)} 个documents, {chunks_created} 个chunks"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"migrate_excel_direct_to_ragflow failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"直接迁移Excel到RAGFlow失败: {e}")

@router.get("/saved-excel-file/{file_id}/segments", response_model=SavedFileSegmentsResponse)
async def get_saved_excel_file_segments(file_id: str, user=Depends(get_verified_user)):
    """根据聚合后的文件ID，解析并返回 Sheet 与分段层级结构。"""
    try:
        file_record = Files.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        if file_record.user_id != user.id:
            raise HTTPException(status_code=403, detail="无权访问该文件")

        # 优先使用保存的结构化数据，如果没有则从Markdown解析
        data = file_record.data or {}
        original_file = data.get("source_file") or (file_record.meta or {}).get("original_file", "")
        
        # 优先使用结构化数据（sheets_data）
        if "sheets_data" in data and data["sheets_data"]:
            sheets_result = []
            for sheet in data["sheets_data"]:
                # 转换格式以匹配前端期望（与提取时的格式完全一致）
                segments = []
                for seg in sheet.get("segments", []):
                    segments.append({
                        "title": seg.get("title", ""),
                        "content": seg.get("content", ""),
                        "questions": seg.get("questions", ""),
                        "row": seg.get("row", 0)  # 保留行号信息
                    })
                sheets_result.append({
                    "name": sheet.get("name", ""),
                    "segments": segments
                })
            return SavedFileSegmentsResponse(file_id=file_id, original_file=original_file, sheets=sheets_result)
        
        # Fallback: 从Markdown解析（兼容旧数据）
        content = data.get("content", "")
        if not content:
            return SavedFileSegmentsResponse(file_id=file_id, original_file=original_file, sheets=[])

        lines = content.splitlines()
        sheets_flat = []
        current_sheet = None
        current_seg = None

        def push_seg():
            nonlocal current_seg, current_sheet
            if current_sheet is not None and current_seg is not None:
                # 结束一段
                current_sheet["segments"].append(current_seg)
                current_seg = None

        def push_sheet():
            nonlocal current_sheet
            if current_sheet is not None:
                sheets_flat.append(current_sheet)
                current_sheet = None

        for line in lines:
            if line.startswith("# ") and not line.startswith("## "):
                # 新 sheet
                push_seg()
                push_sheet()
                name = line[2:].strip()
                current_sheet = {"name": name, "segments": []}
                continue
            if line.startswith("## "):
                # 新分段
                push_seg()
                title = line[3:].strip()
                current_seg = {"title": title, "content": "", "questions": ""}
                continue
            if current_seg is None:
                # 忽略 sheet 标题下的空行等
                continue
            # 累积内容或问题
            # 注意：只有当整行严格以"问题（选填，单元格内一行一个）:"开头时才识别为问题标记
            # 如果内容中包含"问题（选填，单元格内一行一个）:"应该作为内容的一部分
            stripped_line = line.strip()
            if stripped_line.startswith("问题（选填，单元格内一行一个）:") and len(stripped_line.split(":", 1)) == 2:
                # 这是问题行，提取问题内容
                question_text = stripped_line.split(":", 1)[1].strip()
                if question_text:
                    current_seg["questions"] = question_text
                # 问题行不添加到content中
            else:
                # 这是内容行
                current_seg["content"] += ("\n" if current_seg["content"] else "") + line

        # 收尾
        push_seg()
        push_sheet()

        # 直接按Sheet返回，不做分组
        return SavedFileSegmentsResponse(file_id=file_id, original_file=original_file, sheets=sheets_flat)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_saved_excel_file_segments failed: {e}")
        raise HTTPException(status_code=500, detail=f"获取分段失败: {e}")


@router.delete("/saved-excel-file/{file_id}", response_model=Dict[str, Any])
async def delete_saved_excel_file(file_id: str, user=Depends(get_verified_user)):
    """删除指定的Excel提取文件。"""
    try:
        file_record = Files.get_file_by_id(file_id)
        if not file_record:
            raise HTTPException(status_code=404, detail="文件不存在")
        if file_record.user_id != user.id:
            raise HTTPException(status_code=403, detail="无权删除该文件")
        
        meta = file_record.meta or {}
        if meta.get("source") != "excel_extraction":
            raise HTTPException(status_code=400, detail="只能删除Excel提取的文件")
        
        # 删除文件
        Files.delete_file_by_id(file_id)
        
        # 从所有知识库的file_ids中移除该文件ID
        from open_webui.models.knowledge import Knowledges
        all_knowledges = Knowledges.get_knowledges_by_user_id(user.id)
        for kb in all_knowledges:
            data = kb.data or {}
            file_ids = list(data.get("file_ids", []))
            if file_id in file_ids:
                file_ids.remove(file_id)
                data["file_ids"] = file_ids
                Knowledges.update_knowledge_data_by_id(id=kb.id, data=data)
        
        return {"success": True, "message": "文件已删除", "file_id": file_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"delete_saved_excel_file failed: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {e}")
