import logging
import os
import uuid
import json
import time
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional
from urllib.parse import quote
import asyncio
import zipfile
import shutil

from fastapi import (
    BackgroundTasks,
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
    Query,
)

from fastapi.responses import FileResponse, StreamingResponse
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT

from open_webui.models.users import Users
from open_webui.models.files import (
    FileForm,
    FileModel,
    FileModelResponse,
    Files,
)
from open_webui.models.knowledge import Knowledges
from open_webui.models.knowledge_logs import KnowledgeLogs, KnowledgeLogForm
from open_webui.models.knowledge_file_link import KnowledgeFileLinks
from open_webui.models.knowledge_file_link import KnowledgeFileLinks

from open_webui.routers.knowledge import get_knowledge, get_knowledge_list
from open_webui.routers.retrieval import ProcessFileForm, process_file
from open_webui.routers.audio import transcribe
from open_webui.storage.provider import Storage
from open_webui.config import UPLOAD_DIR
from open_webui.utils.auth import get_admin_user, get_verified_user
from pydantic import BaseModel

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


def log_knowledge_action(
    knowledge_id: str,
    user_id: str,
    user_name: str,
    user_email: str,
    action_type: str,
    action: str,
    description: str = None,
    file_id: str = None,
    file_name: str = None,
    file_size: int = None,
    extra_data: dict = None,
    status: str = "success"
):
    """记录知识库操作日志"""
    try:
        log_form = KnowledgeLogForm(
            knowledge_id=knowledge_id,
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            action_type=action_type,
            action=action,
            description=description,
            file_id=file_id,
            file_name=file_name,
            file_size=file_size,
            extra_data=extra_data,
            status=status
        )
        result = KnowledgeLogs.insert_log(log_form)
        return result
    except Exception as e:
        log.exception(f"Error logging knowledge action: {e}")
        return None




############################
# Check if the current user has access to a file through any knowledge bases the user may be in.
############################


def has_access_to_file(
    file_id: Optional[str], access_type: str, user=Depends(get_verified_user)
) -> bool:
    file = Files.get_file_by_id(file_id)
    log.debug(f"Checking if user has {access_type} access to file")

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    has_access = False
    
    # 1. 检查是否是管理员（最高权限）
    if user.role == "admin":
        has_access = True
        log.debug(f"User {user.id} is admin")
    
    # 2. 检查是否是文件负责人（个人）
    if not has_access:
        file_meta = file.meta or {}
        file_data = file_meta.get("data", {})
        
        # 检查两个位置的owner：meta.owner 和 meta.data.owner
        file_owner = file_meta.get("owner", "") or file_data.get("owner", "")
        
        if file_owner and user.name == file_owner:
            has_access = True
            log.debug(f"User {user.name} is the file owner")
    
    # 3. 检查是否是文件负责部门成员
    if not has_access and file_owner:
        from open_webui.models.groups import Groups
        groups = Groups.get_groups_by_member_id(user.id)
        
        for group in groups:
            if group.name == file_owner:
                has_access = True
                log.debug(f"User {user.name} is member of responsible department {file_owner}")
                break
    
    # 4. 检查是否是知识库所有者
    if not has_access:
        knowledge_base_id = file_meta.get("collection_name") if file_meta else None
        
        if knowledge_base_id:
            from open_webui.models.knowledge import Knowledges
            knowledge = Knowledges.get_knowledge_by_id(knowledge_base_id)
            if knowledge and knowledge.user_id == user.id:
                has_access = True
                log.debug(f"User {user.id} is knowledge base owner")
    
    # 5. 检查是否是文件上传者（最低权限）
    if not has_access and file.user_id == user.id:
        has_access = True
        log.debug(f"User {user.id} is the file uploader")
    
    # 检查知识库权限
    if not has_access:
        knowledge_base_id = file_meta.get("collection_name") if file_meta else None
        
        if knowledge_base_id:
            # For read access, check both read and write permissions
            if access_type == "read":
                knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(
                    user.id, "read"
                )
            else:
                knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(
                    user.id, access_type
                )
            for knowledge_base in knowledge_bases:
                if knowledge_base.id == knowledge_base_id:
                    has_access = True
                    log.debug(f"User {user.id} has {access_type} access to knowledge base {knowledge_base_id}")
                    break

    log.debug(f"Final access result: {has_access}")
    return has_access


############################
# Upload File
############################


def process_uploaded_file(request, file, file_path, file_item, file_metadata, user):
    try:
        if file.content_type:
            stt_supported_content_types = getattr(
                request.app.state.config, "STT_SUPPORTED_CONTENT_TYPES", []
            )

            if any(
                fnmatch(file.content_type, content_type)
                for content_type in (
                    stt_supported_content_types
                    if stt_supported_content_types
                    and any(t.strip() for t in stt_supported_content_types)
                    else ["audio/*", "video/webm"]
                )
            ):
                file_path = Storage.get_file(file_path)
                result = transcribe(request, file_path, file_metadata)

                process_file(
                    request,
                    ProcessFileForm(
                        file_id=file_item.id, content=result.get("text", "")
                    ),
                    user=user,
                )
            elif (not file.content_type.startswith(("image/", "video/"))) or (
                request.app.state.config.CONTENT_EXTRACTION_ENGINE == "external"
            ):
                process_file(request, ProcessFileForm(file_id=file_item.id), user=user)
        else:
            log.info(
                f"File type {file.content_type} is not provided, but trying to process anyway"
            )
            process_file(request, ProcessFileForm(file_id=file_item.id), user=user)
    except Exception as e:
        log.error(f"Error processing file: {file_item.id}")
        Files.update_file_data_by_id(
            file_item.id,
            {
                "status": "failed",
                "error": str(e.detail) if hasattr(e, "detail") else str(e),
            },
        )


@router.post("/", response_model=FileModelResponse)
def upload_file(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: Optional[dict | str] = Form(None),
    process: bool = Query(True),
    process_in_background: bool = Query(True),
    user=Depends(get_verified_user),
):
    """Upload a file"""
    return upload_file_handler(
        request,
        file=file,
        metadata=metadata,
        process=process,
        process_in_background=process_in_background,
        user=user,
        background_tasks=background_tasks,
    )


@router.post("/{file_id}/update", response_model=FileModelResponse)
def update_file(
    file_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: Optional[dict | str] = Form(None),
    process: bool = Query(True),
    process_in_background: bool = Query(True),
    user=Depends(get_verified_user),
):
    """Update an existing file with a new version"""
    return update_file_handler(
        file_id,
        request,
        file=file,
        metadata=metadata,
        process=process,
        process_in_background=process_in_background,
        user=user,
        background_tasks=background_tasks,
    )


def update_file_handler(
    file_id: str,
    request: Request,
    file: UploadFile = File(...),
    metadata: Optional[dict | str] = Form(None),
    process: bool = Query(True),
    process_in_background: bool = Query(True),
    user=Depends(get_verified_user),
    background_tasks: Optional[BackgroundTasks] = None,
):
    """Update an existing file with a new version"""
    log.info(f"Updating file {file_id} with new file: {file.filename}")
    print(f"🔍 DEBUG: 开始更新文件 - file_id: {file_id}, filename: {file.filename}")
    
    # Check if the original file exists and user has access
    original_file = Files.get_file_by_id(file_id)
    if not original_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.DEFAULT("File not found"),
        )
    
    # Check user access
    if not Files.check_access_by_user_id(file_id, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.DEFAULT("Access denied"),
        )
    
    
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Invalid metadata format"),
            )
    
    file_metadata = metadata if metadata else {}
    
    # 自动设置文件分类（如果用户没有提供分类）
    if 'category' not in file_metadata:
        file_extension = os.path.splitext(file.filename)[1]
        file_extension = file_extension[1:] if file_extension else ""
        file_metadata['category'] = get_file_category(file_extension, file.content_type)
    
    # 自动设置负责人（如果用户没有提供）
    if 'owner' not in file_metadata:
        file_metadata['owner'] = user.name
    
    # Preserve original file metadata and add update information
    original_meta = original_file.meta or {}
    print(f"🔍 DEBUG: 原始文件元数据 - original_meta: {original_meta}")
    updated_meta = {
        **original_meta,
        **file_metadata,
        "previous_version": original_meta.get("version", "1.0"),
        "update_type": "file_update",
        "updated_at": int(time.time()),
    }
    print(f"🔍 DEBUG: 更新后的元数据 - updated_meta: {updated_meta}")
    
    try:
        print(f"🔍 DEBUG: 进入try块 - 开始处理文件")
        unsanitized_filename = file.filename
        filename = os.path.basename(unsanitized_filename)
        
        file_extension = os.path.splitext(filename)[1]
        file_extension = file_extension[1:] if file_extension else ""
        
        if process and request.app.state.config.ALLOWED_FILE_EXTENSIONS:
            request.app.state.config.ALLOWED_FILE_EXTENSIONS = [
                ext for ext in request.app.state.config.ALLOWED_FILE_EXTENSIONS if ext
            ]
            
            if file_extension not in request.app.state.config.ALLOWED_FILE_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT(f"File type {file_extension} is not allowed"),
                )
        
        # 保持原始文件名，不添加UUID前缀
        new_file_id = str(uuid.uuid4())
        name = filename
        # filename 保持原始名称，用于文件存储
        # new_file_id 用于数据库记录的唯一标识
        
        # 准备上传标签（用于 MinIO bucket 选择和路径生成）
        upload_tags = {
            "OpenWebUI-User-Email": user.email,
            "OpenWebUI-User-Id": user.id,
            "OpenWebUI-User-Name": user.name,
            "OpenWebUI-File-Id": new_file_id,
            "OpenWebUI-Original-File-Id": file_id,
            "content_type": file.content_type,
        }
        
        # 添加 metadata 中的信息到 tags（使用原始文件的元数据）
        if original_meta.get("collection_name"):
            upload_tags["collection_name"] = original_meta.get("collection_name")
            upload_tags["OpenWebUI-Collection-Name"] = original_meta.get("collection_name")
        
        if updated_meta.get("source"):
            upload_tags["source"] = updated_meta.get("source")
        
        if updated_meta.get("chat_id"):
            upload_tags["chat_id"] = updated_meta.get("chat_id")
            upload_tags["OpenWebUI-Chat-Id"] = updated_meta.get("chat_id")
        
        # 上传文件到存储（MinIO 或本地）
        # MinIOStorageProvider 会根据 tags 自动选择 bucket 和生成路径
        # 对于本地存储，仍需要创建文件夹（向后兼容）
        if hasattr(Storage, '__class__') and Storage.__class__.__name__ == 'LocalStorageProvider':
            folder_path = get_file_folder_path(original_meta, user.id)
            filename_with_folder = f"{folder_path}/{filename}"
            full_folder_path = os.path.join(UPLOAD_DIR, folder_path)
            os.makedirs(full_folder_path, exist_ok=True)
            contents, file_path = Storage.upload_file(
                file.file,
                filename_with_folder,
                upload_tags,
            )
        else:
            # MinIO 存储：直接使用文件名，provider 会生成完整路径
            contents, file_path = Storage.upload_file(
                file.file,
                filename,
                upload_tags,
            )
        
        # 记录文件更新日志
        collection_name = original_meta.get("collection_name")
        print(f"🔍 DEBUG: 文件更新 - original_meta: {original_meta}")
        print(f"🔍 DEBUG: 文件更新 - collection_name: {collection_name}")
        
        # 即使没有collection_name也记录日志
        if collection_name:
            log_knowledge_action(
                knowledge_id=collection_name,
                user_id=user.id,
                user_name=user.name,
                user_email=user.email,
                action_type="file_update",
                action="更新文件",
                description=f"文件 {file.filename} 已更新到版本 {file_metadata.get('version', '未知')}",
                file_id=new_file_id,
                file_name=file.filename,
                file_size=len(contents),
                extra_data={
                    "original_file_id": file_id,
                    "new_version": file_metadata.get('version', '未知'),
                    "update_notes": file_metadata.get('update_notes', ''),
                    "collection_name": collection_name
                }
            )
        else:
            print(f"⚠️ DEBUG: 文件更新但没有collection_name，跳过日志记录")
        
        # Create new file record
        file_item = Files.insert_new_file(
            user.id,
            FileForm(
                **{
                    "id": new_file_id,
                    "filename": name,
                    "path": file_path,
                    "data": {
                        **({"status": "pending"} if process else {}),
                        "original_file_id": file_id,
                        "update_type": "file_update",
                    },
                    "meta": {
                        "name": name,
                        "content_type": file.content_type,
                        "size": len(contents),
                        "data": file_metadata,
                        **updated_meta,
                    },
                }
            ),
        )
        
        # 数据库同步：如果文件更新时指定了知识库，自动创建关联记录
        collection_name = original_meta.get("collection_name")
        if collection_name and file_item:
            try:
                # 验证知识库是否存在
                knowledge = Knowledges.get_knowledge_by_id(id=collection_name)
                if knowledge:
                    # 创建知识库-文件关联记录（新版本文件）
                    link = KnowledgeFileLinks.create_link(
                        knowledge_id=collection_name,
                        file_id=new_file_id,
                        is_indexed=False  # 默认未索引，后续处理完成后更新
                    )
                    if link:
                        log.info(f"✅ 文件更新：创建知识库-文件关联: knowledge_id={collection_name}, file_id={new_file_id}")
                    
                    # 更新知识库的 file_ids（添加新版本，保留旧版本或替换取决于业务逻辑）
                    data = knowledge.data or {}
                    file_ids = data.get("file_ids", [])
                    if new_file_id not in file_ids:
                        file_ids.append(new_file_id)
                        data["file_ids"] = file_ids
                        Knowledges.update_knowledge_data_by_id(id=collection_name, data=data)
                        log.info(f"✅ 文件更新：更新知识库 file_ids: knowledge_id={collection_name}")
            except Exception as e:
                log.warning(f"文件更新：创建知识库-文件关联时出错: {e}")
        
        if process:
            if background_tasks and process_in_background:
                background_tasks.add_task(
                    process_uploaded_file,
                    request,
                    file,
                    file_path,
                    file_item,
                    file_metadata,
                    user,
                )
                return {"status": True, **file_item.model_dump()}
            else:
                process_uploaded_file(
                    request,
                    file,
                    file_path,
                    file_item,
                    file_metadata,
                    user,
                )
                return {"status": True, **file_item.model_dump()}
        else:
            if file_item:
                return file_item
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error updating file"),
                )
    
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error updating file"),
        )


def get_file_category(file_extension: str, content_type: str) -> str:
    """根据文件扩展名和内容类型自动确定文件分类"""
    file_extension = file_extension.lower() if file_extension else ""
    content_type = content_type.lower() if content_type else ""
    
    # PDF文档
    if file_extension in ['pdf'] or 'pdf' in content_type:
        return "技术文档"
    
    # Word文档
    elif file_extension in ['doc', 'docx'] or 'word' in content_type or 'document' in content_type:
        return "办公文档"
    
    # Markdown文档
    elif file_extension in ['md', 'markdown'] or 'markdown' in content_type:
        return "说明文档"
    
    # 图片文件
    elif file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg'] or 'image' in content_type:
        return "图片资源"
    
    # 代码文件
    elif file_extension in ['py', 'js', 'ts', 'java', 'cpp', 'c', 'h', 'css', 'html', 'xml', 'json', 'yaml', 'yml']:
        return "代码文件"
    
    # Excel文件
    elif file_extension in ['xls', 'xlsx'] or 'spreadsheet' in content_type:
        return "数据表格"
    
    # PowerPoint文件
    elif file_extension in ['ppt', 'pptx'] or 'presentation' in content_type:
        return "演示文稿"
    
    # 文本文件
    elif file_extension in ['txt', 'log', 'csv'] or 'text' in content_type:
        return "文本文件"
    
    # 压缩文件
    elif file_extension in ['zip', 'rar', '7z', 'tar', 'gz']:
        return "压缩包"
    
    # 默认分类
    else:
        return "其他文件"


def get_file_folder_path(metadata: dict, user_id: str) -> str:
    """根据元数据确定文件应该保存的文件夹路径"""
    collection_name = metadata.get("collection_name")
    
    # 如果是知识库文件
    if collection_name:
        return f"knowledge/{collection_name}"
    
    # 如果是聊天文件（通过检查来源或其他标识）
    # 这里可以根据实际需求添加更多判断逻辑
    if metadata.get("source") == "chat" or metadata.get("chat_id"):
        return f"chat/{user_id}"
    
    # 默认上传文件夹
    return "uploads"


def upload_file_handler(
    request: Request,
    file: UploadFile = File(...),
    metadata: Optional[dict | str] = Form(None),
    process: bool = Query(True),
    process_in_background: bool = Query(True),
    user=Depends(get_verified_user),
    background_tasks: Optional[BackgroundTasks] = None,
):
    log.info(f"file.content_type: {file.content_type}")
    print(f"🔍 DEBUG: upload_file_handler开始 - filename: {file.filename}, metadata: {metadata}")

    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Invalid metadata format"),
            )
    file_metadata = metadata if metadata else {}

    # 获取文件扩展名用于自动分类
    unsanitized_filename = file.filename
    filename = os.path.basename(unsanitized_filename)
    file_extension = os.path.splitext(filename)[1]
    file_extension = file_extension[1:] if file_extension else ""

    # 自动设置文件分类和元数据
    auto_category = get_file_category(file_extension, file.content_type)
    auto_owner = user.name  # 默认负责人为上传者
    
    # 合并用户提供的元数据和自动生成的元数据
    enhanced_metadata = {
        "category": auto_category,
        "owner": auto_owner,
        "upload_date": int(time.time()),
        **file_metadata  # 用户提供的元数据优先级更高
    }
    
    # 自动识别文件来源（聊天文件或知识库文件）
    # 策略：
    # 1. 如果 metadata 中有 chat_id，标记为聊天文件
    # 2. 如果没有 collection_name（不是知识库文件），默认视为聊天文件
    # 3. 从 request.state 尝试获取 chat_id（如果存在）
    
    # 首先尝试从 request.state 获取 chat_id（如果前端通过其他方式传递）
    chat_id_from_request = None
    if hasattr(request, "state") and hasattr(request.state, "get"):
        chat_id_from_request = request.state.get("chat_id")
    
    # 确定 chat_id（优先级：metadata > request.state）
    chat_id = enhanced_metadata.get("chat_id") or chat_id_from_request
    
    # 判断是否为知识库文件
    is_knowledge_file = bool(enhanced_metadata.get("collection_name"))
    
    # 如果是知识库文件，标记 source 为 knowledge（如果还没有）
    if is_knowledge_file:
        if not enhanced_metadata.get("source"):
            enhanced_metadata["source"] = "knowledge"
    else:
        # 非知识库文件，默认视为聊天文件
        enhanced_metadata["source"] = "chat"
        if chat_id:
            enhanced_metadata["chat_id"] = chat_id
    
    # 如果已经明确标记为聊天文件，确保 source 正确
    if enhanced_metadata.get("source") == "chat":
        if chat_id and not enhanced_metadata.get("chat_id"):
            enhanced_metadata["chat_id"] = chat_id

    try:
        # 文件扩展名已经在上面定义了，这里不需要重复定义

        if process and request.app.state.config.ALLOWED_FILE_EXTENSIONS:
            request.app.state.config.ALLOWED_FILE_EXTENSIONS = [
                ext for ext in request.app.state.config.ALLOWED_FILE_EXTENSIONS if ext
            ]

            if file_extension not in request.app.state.config.ALLOWED_FILE_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT(
                        f"File type {file_extension} is not allowed"
                    ),
                )

        # 保持原始文件名，不添加UUID前缀
        id = str(uuid.uuid4())
        name = filename
        # filename 保持原始名称，用于文件存储
        # id 用于数据库记录的唯一标识
        
        # 准备上传标签（用于 MinIO bucket 选择和路径生成）
        upload_tags = {
            "OpenWebUI-User-Email": user.email,
            "OpenWebUI-User-Id": user.id,
            "OpenWebUI-User-Name": user.name,
            "OpenWebUI-File-Id": id,
            "content_type": file.content_type,
        }
        
        # 添加 metadata 中的信息到 tags（用于 bucket 选择）
        if enhanced_metadata.get("collection_name"):
            upload_tags["collection_name"] = enhanced_metadata.get("collection_name")
            upload_tags["OpenWebUI-Collection-Name"] = enhanced_metadata.get("collection_name")
        
        if enhanced_metadata.get("source"):
            upload_tags["source"] = enhanced_metadata.get("source")
        
        if enhanced_metadata.get("chat_id"):
            upload_tags["chat_id"] = enhanced_metadata.get("chat_id")
            upload_tags["OpenWebUI-Chat-Id"] = enhanced_metadata.get("chat_id")
        
        # 上传文件到存储（MinIO 或本地）
        # MinIOStorageProvider 会根据 tags 自动选择 bucket 和生成路径
        # 对于本地存储，仍需要创建文件夹（向后兼容）
        if hasattr(Storage, '__class__') and Storage.__class__.__name__ == 'LocalStorageProvider':
            folder_path = get_file_folder_path(enhanced_metadata, user.id)
            filename_with_folder = f"{folder_path}/{filename}"
            full_folder_path = os.path.join(UPLOAD_DIR, folder_path)
            os.makedirs(full_folder_path, exist_ok=True)
            contents, file_path = Storage.upload_file(
                file.file,
                filename_with_folder,
                upload_tags,
            )
        else:
            # MinIO 存储：直接使用文件名，provider 会生成完整路径
            contents, file_path = Storage.upload_file(
                file.file,
                filename,
                upload_tags,
            )

        file_item = Files.insert_new_file(
            user.id,
            FileForm(
                **{
                    "id": id,
                    "filename": name,
                    "path": file_path,
                    "data": {
                        **({"status": "pending"} if process else {}),
                    },
                    "meta": {
                        "name": name,
                        "content_type": file.content_type,
                        "size": len(contents),
                        "data": enhanced_metadata,
                        # 如果metadata中包含collection_name，则设置它
                        **({"collection_name": enhanced_metadata.get("collection_name")} if enhanced_metadata.get("collection_name") else {}),
                    },
                }
            ),
        )
        
        # 数据库同步：如果文件上传时指定了知识库，自动创建关联记录
        collection_name = enhanced_metadata.get("collection_name")
        if collection_name and file_item:
            try:
                # 验证知识库是否存在
                knowledge = Knowledges.get_knowledge_by_id(id=collection_name)
                if knowledge:
                    # 创建知识库-文件关联记录
                    link = KnowledgeFileLinks.create_link(
                        knowledge_id=collection_name,
                        file_id=id,
                        is_indexed=False  # 默认未索引，后续处理完成后更新
                    )
                    if link:
                        log.info(f"✅ 自动创建知识库-文件关联: knowledge_id={collection_name}, file_id={id}")
                    
                    # 更新知识库的 file_ids（如果还没有）
                    data = knowledge.data or {}
                    file_ids = data.get("file_ids", [])
                    if id not in file_ids:
                        file_ids.append(id)
                        data["file_ids"] = file_ids
                        Knowledges.update_knowledge_data_by_id(id=collection_name, data=data)
                        log.info(f"✅ 更新知识库 file_ids: knowledge_id={collection_name}")
            except Exception as e:
                log.warning(f"创建知识库-文件关联时出错（可能已存在）: {e}")
        
        # 数据库同步：聊天文件记录
        # 聊天文件的信息直接存储在聊天消息的 files 字段中，这里记录日志以便追踪
        chat_id = enhanced_metadata.get("chat_id")
        if enhanced_metadata.get("source") == "chat" and chat_id:
            log.info(f"✅ 聊天文件上传完成: chat_id={chat_id}, file_id={id}, path={file_path}")
        
        # 注意：聊天文件不需要额外的关联表，因为文件信息直接存储在聊天消息的 files 字段中


        if process:
            if background_tasks and process_in_background:
                background_tasks.add_task(
                    process_uploaded_file,
                    request,
                    file,
                    file_path,
                    file_item,
                    file_metadata,
                    user,
                )
                return {"status": True, **file_item.model_dump()}
            else:
                process_uploaded_file(
                    request,
                    file,
                    file_path,
                    file_item,
                    file_metadata,
                    user,
                )
                return {"status": True, **file_item.model_dump()}
        else:
            if file_item:
                return file_item
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error uploading file"),
                )

    except Exception as e:
        log.exception(e)
        print(f"❌ DEBUG: upload_file_handler异常 - {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error uploading file"),
        )


############################
# List Files
############################


@router.get("/", response_model=list[FileModelResponse])
async def list_files(user=Depends(get_verified_user), content: bool = Query(True)):
    if user.role == "admin":
        files = Files.get_files()
    else:
        files = Files.get_files_by_user_id(user.id)

    if not content:
        for file in files:
            if "content" in file.data:
                del file.data["content"]

    return files


############################
# Search Files
############################


@router.get("/search", response_model=list[FileModelResponse])
async def search_files(
    filename: str = Query(
        ...,
        description="Filename pattern to search for. Supports wildcards such as '*.txt'",
    ),
    content: bool = Query(True),
    user=Depends(get_verified_user),
):
    """
    Search for files by filename with support for wildcard patterns.
    """
    # Get files according to user role
    if user.role == "admin":
        files = Files.get_files()
    else:
        files = Files.get_files_by_user_id(user.id)

    # Get matching files
    matching_files = [
        file for file in files if fnmatch(file.filename.lower(), filename.lower())
    ]

    if not matching_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No files found matching the pattern.",
        )

    if not content:
        for file in matching_files:
            if "content" in file.data:
                del file.data["content"]

    return matching_files


############################
# Delete All Files
############################


@router.delete("/all")
async def delete_all_files(user=Depends(get_admin_user)):
    result = Files.delete_all_files()
    if result:
        try:
            Storage.delete_all_files()
            VECTOR_DB_CLIENT.reset()
        except Exception as e:
            log.exception(e)
            log.error("Error deleting files")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting files"),
            )
        return {"message": "All files deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error deleting files"),
        )


############################
# Get File By Id
############################


@router.get("/{id}", response_model=Optional[FileModel])
async def get_file_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        return file
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get("/{id}/process/status")
async def get_file_process_status(
    id: str, stream: bool = Query(False), user=Depends(get_verified_user)
):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        if stream:
            MAX_FILE_PROCESSING_DURATION = 3600 * 2

            async def event_stream(file_item):
                if file_item:
                    for _ in range(MAX_FILE_PROCESSING_DURATION):
                        file_item = Files.get_file_by_id(file_item.id)
                        if file_item:
                            data = file_item.model_dump().get("data", {})
                            status = data.get("status")

                            if status:
                                event = {"status": status}
                                if status == "failed":
                                    event["error"] = data.get("error")

                                yield f"data: {json.dumps(event)}\n\n"
                                if status in ("completed", "failed"):
                                    break
                            else:
                                # Legacy
                                break

                        await asyncio.sleep(0.5)
                else:
                    yield f"data: {json.dumps({'status': 'not_found'})}\n\n"

            return StreamingResponse(
                event_stream(file),
                media_type="text/event-stream",
            )
        else:
            return {"status": file.data.get("status", "pending")}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Get File Data Content By Id
############################


@router.get("/{id}/data/content")
async def get_file_data_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        return {"content": file.data.get("content", "") or ""}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Update File Data Content By Id
############################


class ContentForm(BaseModel):
    content: str
    ocr_task_id: Optional[str] = None  # OCR 任务 ID，用于删除文件时清理 OCR 结果目录


@router.post("/{id}/data/content/update")
async def update_file_data_content_by_id(
    request: Request, id: str, form_data: ContentForm, user=Depends(get_verified_user)
):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "write", user)
    ):
        try:
            process_file(
                request,
                ProcessFileForm(file_id=id, content=form_data.content),
                user=user,
            )
            file = Files.get_file_by_id(id=id)
            
            # 如果请求中包含 OCR 任务 ID，保存到文件数据中
            # 这样删除文件时可以清理对应的 OCR 结果目录
            if form_data.ocr_task_id:
                Files.update_file_data_by_id(id, {"ocr_task_id": form_data.ocr_task_id})
                file = Files.get_file_by_id(id=id)
        except Exception as e:
            log.exception(e)
            log.error(f"Error processing file: {file.id}")

        return {"content": file.data.get("content", "") or ""}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Get File Content By Id
############################


@router.get("/{id}/content")
async def get_file_content_by_id(
    id: str, user=Depends(get_verified_user), attachment: bool = Query(False)
):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        try:
            # 检查 file.path 是否存在
            if not file.path:
                log.error(f"File {id} has no path")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
            
            file_path = Storage.get_file(file.path)
            if not file_path:
                log.error(f"Storage.get_file returned None for path: {file.path}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
            
            file_path = Path(file_path)

            # Storage.get_file() 已经返回绝对路径，不需要再次处理
            # 但为了兼容性，检查一下
            if not file_path.is_absolute():
                from open_webui.config import UPLOAD_DIR
                file_path = Path(UPLOAD_DIR) / file_path
                log.debug(f"Resolved relative path to absolute: {file_path}")

            # Check if the file already exists in the cache
            if file_path.is_file():
                # Handle Unicode filenames
                filename = file.meta.get("name", file.filename)
                encoded_filename = quote(filename)  # RFC5987 encoding

                content_type = file.meta.get("content_type")
                filename = file.meta.get("name", file.filename)
                encoded_filename = quote(filename)
                headers = {}

                if attachment:
                    headers["Content-Disposition"] = (
                        f"attachment; filename*=UTF-8''{encoded_filename}"
                    )
                else:
                    if content_type == "application/pdf" or filename.lower().endswith(
                        ".pdf"
                    ):
                        headers["Content-Disposition"] = (
                            f"inline; filename*=UTF-8''{encoded_filename}"
                        )
                        content_type = "application/pdf"
                    elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or filename.lower().endswith(".docx"):
                        headers["Content-Disposition"] = (
                            f"inline; filename*=UTF-8''{encoded_filename}"
                        )
                        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    elif content_type != "text/plain":
                        headers["Content-Disposition"] = (
                            f"attachment; filename*=UTF-8''{encoded_filename}"
                        )

                return FileResponse(file_path, headers=headers, media_type=content_type)

            else:
                # 增强错误日志
                log.error(
                    f"File not found: file_id={id}, "
                    f"file.path={file.path}, "
                    f"resolved_path={file_path}, "
                    f"path_exists={file_path.exists()}, "
                    f"is_file={file_path.is_file()}, "
                    f"is_dir={file_path.is_dir() if file_path.exists() else False}"
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        except HTTPException:
            # 重新抛出 HTTP 异常（如 404），不包装为 400
            raise
        except Exception as e:
            log.exception(e)
            log.error(
                f"Error getting file content: file_id={id}, "
                f"file.path={file.path if file else 'N/A'}, "
                f"error={str(e)}, "
                f"error_type={type(e).__name__}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error getting file content"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.get("/{id}/content/html")
async def get_html_file_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    file_user = Users.get_user_by_id(file.user_id)
    if not file_user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        try:
            file_path = Storage.get_file(file.path)
            file_path = Path(file_path)

            # Check if the file already exists in the cache
            if file_path.is_file():
                log.info(f"file_path: {file_path}")
                return FileResponse(file_path)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        except Exception as e:
            log.exception(e)
            log.error("Error getting file content")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error getting file content"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.post("/{id}/metadata/update")
async def update_file_metadata_by_id(
    id: str,
    request: Request,
    user=Depends(get_verified_user)
):
    """Update file metadata including tags and categories"""
    try:
        metadata = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON data"
        )
    
    file = Files.get_file_by_id(id)
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    # Check if user has access to update this file
    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "write", user)
    ):
        # Update file metadata
        updated_file = Files.update_file_metadata_by_id(id, metadata)
        
        if updated_file:
            # 记录文件元数据更新日志
            file_meta = updated_file.meta or {}
            collection_name = file_meta.get("collection_name")
            
            if collection_name:
                # 生成详细的更新描述
                updated_fields = []
                if 'category' in metadata:
                    updated_fields.append(f"分类: {metadata['category']}")
                if 'version' in metadata:
                    updated_fields.append(f"版本: {metadata['version']}")
                if 'owner' in metadata:
                    updated_fields.append(f"负责人: {metadata['owner']}")
                if 'tags' in metadata:
                    updated_fields.append(f"标签: {', '.join(metadata['tags']) if isinstance(metadata['tags'], list) else metadata['tags']}")
                
                if updated_fields:
                    description = f"文件 {updated_file.filename} 的元数据已更新: {', '.join(updated_fields)}"
                else:
                    description = f"文件 {updated_file.filename} 的元数据已更新"
                
                log_knowledge_action(
                    knowledge_id=collection_name,
                    user_id=user.id,
                    user_name=user.name,
                    user_email=user.email,
                    action_type="file_metadata_update",
                    action="更新文件元数据",
                    description=description,
                    file_id=id,
                    file_name=updated_file.filename,
                    file_size=file_meta.get("size"),
                    extra_data={
                        "collection_name": collection_name,
                        "updated_metadata": metadata,
                        "updated_fields": list(metadata.keys())
                    }
                )
            
            return updated_file
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("file"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


@router.get("/{id}/content/{file_name}")
async def get_file_content_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "read", user)
    ):
        file_path = file.path

        # Handle Unicode filenames
        filename = file.meta.get("name", file.filename)
        encoded_filename = quote(filename)  # RFC5987 encoding
        headers = {
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }

        if file_path:
            file_path = Storage.get_file(file_path)
            file_path = Path(file_path)

            # Check if the file already exists in the cache
            if file_path.is_file():
                return FileResponse(file_path, headers=headers)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )
        else:
            # File path doesn’t exist, return the content as .txt if possible
            file_content = file.content.get("content", "")
            file_name = file.filename

            # Create a generator that encodes the file content
            def generator():
                yield file_content.encode("utf-8")

            return StreamingResponse(
                generator(),
                media_type="text/plain",
                headers=headers,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Delete File By Id
############################


@router.delete("/{id}")
async def delete_file_by_id(id: str, user=Depends(get_verified_user)):
    file = Files.get_file_by_id(id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        file.user_id == user.id
        or user.role == "admin"
        or has_access_to_file(id, "write", user)
    ):

        result = Files.delete_file_by_id(id)
        if result:
            # 记录文件删除日志
            file_meta = file.meta or {}
            collection_name = file_meta.get("collection_name")
            print(f"🔍 DEBUG: 删除文件 - file_id: {id}, filename: {file.filename}")
            print(f"🔍 DEBUG: 删除文件 - collection_name: {collection_name}")
            
            if collection_name:
                log_knowledge_action(
                    knowledge_id=collection_name,
                    user_id=user.id,
                    user_name=user.name,
                    user_email=user.email,
                    action_type="file_delete",
                    action="删除文件",
                    description=f"文件 {file.filename} 已从知识库删除",
                    file_id=id,
                    file_name=file.filename,
                    file_size=file_meta.get("size"),
                    extra_data={
                        "collection_name": collection_name,
                        "file_path": file.path
                    }
                )
            else:
                print(f"⚠️ DEBUG: 删除文件但没有collection_name，跳过日志记录")
            
            try:
                Storage.delete_file(file.path)
                VECTOR_DB_CLIENT.delete(collection_name=f"file-{id}")
            except Exception as e:
                log.exception(e)
                log.error("Error deleting files")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("Error deleting files"),
                )
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error deleting file"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Extract Zip File
############################


class ExtractZipForm(BaseModel):
    zip_path: str
    extract_to: Optional[str] = None  # 如果为空，则解压到 zip 文件所在目录


@router.post("/extract-zip")
async def extract_zip_file(
    request: Request,
    form_data: ExtractZipForm,
    user=Depends(get_verified_user),
):
    """解压 zip 文件到指定目录"""
    zip_path = form_data.zip_path
    extract_to = form_data.extract_to
    
    # 验证 zip 文件是否存在
    if not os.path.exists(zip_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zip file not found: {zip_path}",
        )
    
    # 验证是否为 zip 文件
    if not zip_path.lower().endswith('.zip'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a zip file",
        )
    
    # 如果没有指定解压目录，则解压到 zip 文件所在目录
    if not extract_to:
        extract_to = os.path.dirname(zip_path)
    
    # 确保解压目录存在
    os.makedirs(extract_to, exist_ok=True)
    
    try:
        # 解压 zip 文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        # 获取解压后的文件列表
        extracted_files = []
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            extracted_files = zip_ref.namelist()
        
        log.info(f"Successfully extracted {len(extracted_files)} files from {zip_path} to {extract_to}")
        
        return {
            "status": "success",
            "message": f"Successfully extracted {len(extracted_files)} files",
            "zip_path": zip_path,
            "extract_to": extract_to,
            "extracted_files": extracted_files,
            "file_count": len(extracted_files)
        }
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid zip file",
        )
    except Exception as e:
        log.exception(f"Error extracting zip file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting zip file: {str(e)}",
        )
