from typing import List, Optional
from pathlib import Path
from datetime import datetime
import json
import logging
import re
import shutil

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status, Body
from pydantic import BaseModel

from open_webui.models.knowledge import (
    Knowledges,
    KnowledgeForm,
    KnowledgeResponse,
    KnowledgeUserResponse,
)
from open_webui.models.files import Files, FileModel, FileMetadataResponse
from open_webui.models.knowledge_logs import KnowledgeLogs, KnowledgeLogForm
from open_webui.retrieval.vector.factory import VECTOR_DB_CLIENT
from open_webui.routers.retrieval import (
    process_file,
    ProcessFileForm,
    process_files_batch,
    BatchProcessFilesForm,
)
from open_webui.storage.provider import Storage

from open_webui.constants import ERROR_MESSAGES
from open_webui.utils.auth import get_verified_user
from open_webui.utils.access_control import has_access, has_permission


from open_webui.env import SRC_LOG_LEVELS
from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL, UPLOAD_DIR
from open_webui.models.models import Models, ModelForm


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
        print(f"🔍 DEBUG: 尝试记录日志 - knowledge_id: {knowledge_id}, action: {action}")
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
        if result:
            print(f"✅ DEBUG: 日志记录成功 - ID: {result.id}")
        else:
            print("❌ DEBUG: 日志记录失败")
    except Exception as e:
        print(f"❌ DEBUG: 日志记录异常: {e}")
        log.exception(f"Error logging knowledge action: {e}")

############################
# Knowledge Logs API
############################

@router.get("/{id}/logs", response_model=List[dict])
def get_knowledge_logs(
    id: str,
    user=Depends(get_verified_user),
    limit: int = Query(100, ge=1, le=1000)
):
    """获取知识库操作日志"""
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    # 检查访问权限
    if (
        knowledge.user_id != user.id
        and not has_access(user.id, "read", knowledge.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    
    logs = KnowledgeLogs.get_logs_by_knowledge_id(id, limit)
    return [log.model_dump() for log in logs]


@router.delete("/{id}/logs")
def clear_knowledge_logs(
    id: str,
    user=Depends(get_verified_user),
    confirm: str = Query(..., description="确认删除，必须输入'确定删除'")
):
    """清空知识库操作日志"""
    # 检查确认参数
    if confirm != "确定删除":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请确认删除操作，输入'确定删除'"
        )
    
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    
    # 只有知识库所有者或管理员可以清空日志
    if knowledge.user_id != user.id and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    
    # 记录清除日志操作
    print(f"🔍 DEBUG: 清除知识库日志 - knowledge_id: {id}, name: {knowledge.name}")
    log_knowledge_action(
        knowledge_id=id,
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
        action_type="logs_clear",
        action="清除日志",
        description=f"知识库 {knowledge.name} 的操作日志已清空",
        extra_data={
            "knowledge_name": knowledge.name,
            "confirmed_by": user.name
        }
    )
    
    success = KnowledgeLogs.delete_logs_by_knowledge_id(id)
    if success:
        return {"message": "日志已清空"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="清空日志失败"
        )


############################
# getKnowledgeBases
############################


@router.get("/", response_model=list[KnowledgeUserResponse])
async def get_knowledge(user=Depends(get_verified_user)):
    knowledge_bases = []

    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        knowledge_bases = Knowledges.get_knowledge_bases()
    else:
        knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(user.id, "read")

    # Get files for each knowledge base
    knowledge_with_files = []
    for knowledge_base in knowledge_bases:
        files = []
        if knowledge_base.data:
            files = Files.get_file_metadatas_by_ids(
                knowledge_base.data.get("file_ids", [])
            )

            # Check if all files exist
            if len(files) != len(knowledge_base.data.get("file_ids", [])):
                missing_files = list(
                    set(knowledge_base.data.get("file_ids", []))
                    - set([file.id for file in files])
                )
                if missing_files:
                    data = knowledge_base.data or {}
                    file_ids = data.get("file_ids", [])

                    for missing_file in missing_files:
                        file_ids.remove(missing_file)

                    data["file_ids"] = file_ids
                    Knowledges.update_knowledge_data_by_id(
                        id=knowledge_base.id, data=data
                    )

                    files = Files.get_file_metadatas_by_ids(file_ids)

        knowledge_with_files.append(
            KnowledgeUserResponse(
                **knowledge_base.model_dump(),
                files=files,
            )
        )

    return knowledge_with_files


@router.get("/list", response_model=list[KnowledgeUserResponse])
async def get_knowledge_list(user=Depends(get_verified_user)):
    knowledge_bases = []

    if user.role == "admin" and BYPASS_ADMIN_ACCESS_CONTROL:
        knowledge_bases = Knowledges.get_knowledge_bases()
    else:
        knowledge_bases = Knowledges.get_knowledge_bases_by_user_id(user.id, "write")

    # Get files for each knowledge base
    knowledge_with_files = []
    for knowledge_base in knowledge_bases:
        files = []
        if knowledge_base.data:
            files = Files.get_file_metadatas_by_ids(
                knowledge_base.data.get("file_ids", [])
            )

            # Check if all files exist
            if len(files) != len(knowledge_base.data.get("file_ids", [])):
                missing_files = list(
                    set(knowledge_base.data.get("file_ids", []))
                    - set([file.id for file in files])
                )
                if missing_files:
                    data = knowledge_base.data or {}
                    file_ids = data.get("file_ids", [])

                    for missing_file in missing_files:
                        file_ids.remove(missing_file)

                    data["file_ids"] = file_ids
                    Knowledges.update_knowledge_data_by_id(
                        id=knowledge_base.id, data=data
                    )

                    files = Files.get_file_metadatas_by_ids(file_ids)

        knowledge_with_files.append(
            KnowledgeUserResponse(
                **knowledge_base.model_dump(),
                files=files,
            )
        )
    return knowledge_with_files


############################
# CreateNewKnowledge
############################


@router.post("/create", response_model=Optional[KnowledgeResponse])
async def create_new_knowledge(
    request: Request, form_data: KnowledgeForm, user=Depends(get_verified_user)
):
    if user.role != "admin" and not has_permission(
        user.id, "workspace.knowledge", request.app.state.config.USER_PERMISSIONS
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    # Check if user can share publicly
    if (
        user.role != "admin"
        and form_data.access_control == None
        and not has_permission(
            user.id,
            "sharing.public_knowledge",
            request.app.state.config.USER_PERMISSIONS,
        )
    ):
        form_data.access_control = {}

    knowledge = Knowledges.insert_new_knowledge(user.id, form_data)

    if knowledge:
        # 记录知识库创建日志
        print(f"🔍 DEBUG: 创建知识库 - knowledge_id: {knowledge.id}, name: {knowledge.name}")
        log_knowledge_action(
            knowledge_id=knowledge.id,
            user_id=user.id,
            user_name=user.name,
            user_email=user.email,
            action_type="knowledge_create",
            action="创建知识库",
            description=f"知识库 {knowledge.name} 已创建",
            extra_data={
                "knowledge_name": knowledge.name,
                "access_control": knowledge.access_control,
                "description": knowledge.description
            }
        )
        return knowledge
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_EXISTS,
        )


############################
# ReindexKnowledgeFiles
############################


@router.post("/reindex", response_model=bool)
async def reindex_knowledge_files(request: Request, user=Depends(get_verified_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    knowledge_bases = Knowledges.get_knowledge_bases()

    log.info(f"Starting reindexing for {len(knowledge_bases)} knowledge bases")

    deleted_knowledge_bases = []

    for knowledge_base in knowledge_bases:
        # -- Robust error handling for missing or invalid data
        if not knowledge_base.data or not isinstance(knowledge_base.data, dict):
            log.warning(
                f"Knowledge base {knowledge_base.id} has no data or invalid data ({knowledge_base.data!r}). Deleting."
            )
            try:
                Knowledges.delete_knowledge_by_id(id=knowledge_base.id)
                deleted_knowledge_bases.append(knowledge_base.id)
            except Exception as e:
                log.error(
                    f"Failed to delete invalid knowledge base {knowledge_base.id}: {e}"
                )
            continue

        try:
            file_ids = knowledge_base.data.get("file_ids", [])
            files = Files.get_files_by_ids(file_ids)
            try:
                if VECTOR_DB_CLIENT.has_collection(collection_name=knowledge_base.id):
                    VECTOR_DB_CLIENT.delete_collection(
                        collection_name=knowledge_base.id
                    )
            except Exception as e:
                log.error(f"Error deleting collection {knowledge_base.id}: {str(e)}")
                continue  # Skip, don't raise

            failed_files = []
            for file in files:
                try:
                    process_file(
                        request,
                        ProcessFileForm(
                            file_id=file.id, collection_name=knowledge_base.id
                        ),
                        user=user,
                    )
                except Exception as e:
                    log.error(
                        f"Error processing file {file.filename} (ID: {file.id}): {str(e)}"
                    )
                    failed_files.append({"file_id": file.id, "error": str(e)})
                    continue

        except Exception as e:
            log.error(f"Error processing knowledge base {knowledge_base.id}: {str(e)}")
            # Don't raise, just continue
            continue

        if failed_files:
            log.warning(
                f"Failed to process {len(failed_files)} files in knowledge base {knowledge_base.id}"
            )
            for failed in failed_files:
                log.warning(f"File ID: {failed['file_id']}, Error: {failed['error']}")

    log.info(
        f"Reindexing completed. Deleted {len(deleted_knowledge_bases)} invalid knowledge bases: {deleted_knowledge_bases}"
    )
    return True


############################
# GetKnowledgeById
############################


class KnowledgeFilesResponse(KnowledgeResponse):
    files: list[FileMetadataResponse]


@router.get("/{id}", response_model=Optional[KnowledgeFilesResponse])
async def get_knowledge_by_id(id: str, user=Depends(get_verified_user)):
    knowledge = Knowledges.get_knowledge_by_id(id=id)

    if knowledge:

        if (
            user.role == "admin"
            or knowledge.user_id == user.id
            or has_access(user.id, "read", knowledge.access_control)
        ):

            file_ids = knowledge.data.get("file_ids", []) if knowledge.data else []
            files = Files.get_file_metadatas_by_ids(file_ids)

            return KnowledgeFilesResponse(
                **knowledge.model_dump(),
                files=files,
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# UpdateKnowledgeById
############################


@router.post("/{id}/update", response_model=Optional[KnowledgeFilesResponse])
async def update_knowledge_by_id(
    request: Request,
    id: str,
    form_data: KnowledgeForm,
    user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    # Is the user the original creator, in a group with write access, or an admin
    if (
        knowledge.user_id != user.id
        and not has_access(user.id, "write", knowledge.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Check if user can share publicly
    if (
        user.role != "admin"
        and form_data.access_control == None
        and not has_permission(
            user.id,
            "sharing.public_knowledge",
            request.app.state.config.USER_PERMISSIONS,
        )
    ):
        form_data.access_control = {}

    knowledge = Knowledges.update_knowledge_by_id(id=id, form_data=form_data)
    if knowledge:
        # 记录知识库更新日志
        print(f"🔍 DEBUG: 更新知识库 - knowledge_id: {id}, name: {knowledge.name}")
        log_knowledge_action(
            knowledge_id=id,
            user_id=user.id,
            user_name=user.name,
            user_email=user.email,
            action_type="knowledge_update",
            action="更新知识库",
            description=f"知识库 {knowledge.name} 已更新",
            extra_data={
                "knowledge_name": knowledge.name,
                "access_control": knowledge.access_control,
                "description": knowledge.description
            }
        )
        
        file_ids = knowledge.data.get("file_ids", []) if knowledge.data else []
        files = Files.get_file_metadatas_by_ids(file_ids)

        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=files,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ID_TAKEN,
        )


############################
# AddFileToKnowledge
############################


class KnowledgeFileIdForm(BaseModel):
    file_id: str


@router.post("/{id}/file/add", response_model=Optional[KnowledgeFilesResponse])
def add_file_to_knowledge_by_id(
    request: Request,
    id: str,
    form_data: KnowledgeFileIdForm,
    user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)

    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        knowledge.user_id != user.id
        and not has_access(user.id, "write", knowledge.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    if not file.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.FILE_NOT_PROCESSED,
        )

    # Add content to the vector database
    try:
        process_file(
            request,
            ProcessFileForm(file_id=form_data.file_id, collection_name=id),
            user=user,
        )
    except Exception as e:
        log.debug(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if knowledge:
        data = knowledge.data or {}
        file_ids = data.get("file_ids", [])

        if form_data.file_id not in file_ids:
            file_ids.append(form_data.file_id)
            data["file_ids"] = file_ids

            knowledge = Knowledges.update_knowledge_data_by_id(id=id, data=data)

            if knowledge:
                # 确保文件的 collection_name 被正确设置
                Files.update_file_metadata_by_id(
                    form_data.file_id,
                    {
                        "collection_name": id,
                    },
                )
                
                # 记录文件添加日志
                print(f"🔍 DEBUG: 文件添加 - knowledge_id: {id}, file_id: {form_data.file_id}")
                log_knowledge_action(
                    knowledge_id=id,
                    user_id=user.id,
                    user_name=user.name,
                    user_email=user.email,
                    action_type="file_add",
                    action="添加文件到知识库",
                    description=f"文件 {file.filename} 已添加到知识库 {knowledge.name}",
                    file_id=form_data.file_id,
                    file_name=file.filename,
                    file_size=file.meta.get("size") if file.meta else None,
                    extra_data={"collection_name": id}
                )
                
                files = Files.get_file_metadatas_by_ids(file_ids)

                return KnowledgeFilesResponse(
                    **knowledge.model_dump(),
                    files=files,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("knowledge"),
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("file_id"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.post("/{id}/file/update", response_model=Optional[KnowledgeFilesResponse])
def update_file_from_knowledge_by_id(
    request: Request,
    id: str,
    form_data: KnowledgeFileIdForm,
    user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        knowledge.user_id != user.id
        and not has_access(user.id, "write", knowledge.access_control)
        and user.role != "admin"
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Remove content from the vector database
    VECTOR_DB_CLIENT.delete(
        collection_name=knowledge.id, filter={"file_id": form_data.file_id}
    )

    # Add content to the vector database
    try:
        process_file(
            request,
            ProcessFileForm(file_id=form_data.file_id, collection_name=id),
            user=user,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if knowledge:
        data = knowledge.data or {}
        file_ids = data.get("file_ids", [])

        files = Files.get_file_metadatas_by_ids(file_ids)

        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=files,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# RemoveFileFromKnowledge
############################


@router.post("/{id}/file/remove", response_model=Optional[KnowledgeFilesResponse])
def remove_file_from_knowledge_by_id(
    id: str,
    form_data: KnowledgeFileIdForm,
    delete_file: bool = Query(True),
    user=Depends(get_verified_user),
):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # 检查权限
    if (
        knowledge.user_id != user.id
        and not has_access(user.id, "write", knowledge.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    file = Files.get_file_by_id(form_data.file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Remove content from the vector database
    try:
        VECTOR_DB_CLIENT.delete(
            collection_name=knowledge.id, filter={"file_id": form_data.file_id}
        )
    except Exception as e:
        log.debug("This was most likely caused by bypassing embedding processing")
        log.debug(e)
        pass

    if delete_file:
        try:
            # Remove the file's collection from vector database
            file_collection = f"file-{form_data.file_id}"
            if VECTOR_DB_CLIENT.has_collection(collection_name=file_collection):
                VECTOR_DB_CLIENT.delete_collection(collection_name=file_collection)
        except Exception as e:
            log.debug("This was most likely caused by bypassing embedding processing")
            log.debug(e)
            pass

        # 清理 OCR 处理结果目录
        try:
            import os
            import shutil
            from pathlib import Path
            
            # 检查文件数据中是否有 OCR 任务 ID
            file_data = file.data or {}
            ocr_task_id = file_data.get("ocr_task_id")
            
            if ocr_task_id:
                # 构建 OCR 结果目录路径
                knowledge_dir = UPLOAD_DIR / "knowledge" / id
                ocr_result_dir = knowledge_dir / f"ocr_result_{ocr_task_id}"
                
                # 如果目录存在，删除整个目录
                if ocr_result_dir.exists() and ocr_result_dir.is_dir():
                    shutil.rmtree(ocr_result_dir)
                    log.info(f"✅ 已删除 OCR 处理结果目录: {ocr_result_dir}")
                    print(f"🗑️ 已删除 OCR 处理结果目录: {ocr_result_dir}")
                else:
                    log.debug(f"OCR 结果目录不存在或不是目录: {ocr_result_dir}")
            else:
                # 如果没有存储 task_id，尝试从文件内容中查找
                # 或者扫描知识库目录，查找所有 ocr_result_* 目录
                knowledge_dir = UPLOAD_DIR / "knowledge" / id
                if knowledge_dir.exists():
                    # 查找所有 ocr_result_* 目录
                    for ocr_dir in knowledge_dir.glob("ocr_result_*"):
                        if ocr_dir.is_dir():
                            # 检查目录中是否有与当前文件相关的文件
                            # 这里简化处理：如果目录存在且文件被删除，可以选择删除所有 ocr_result 目录
                            # 或者更精确地匹配文件名
                            log.debug(f"发现 OCR 结果目录: {ocr_dir}，但未找到关联的 task_id")
        except Exception as e:
            log.exception(f"清理 OCR 处理结果目录时出错: {e}")
            # 不抛出异常，继续删除文件

        # Delete file from database
        Files.delete_file_by_id(form_data.file_id)

    if knowledge:
        data = knowledge.data or {}
        file_ids = data.get("file_ids", [])

        if form_data.file_id in file_ids:
            file_ids.remove(form_data.file_id)
            data["file_ids"] = file_ids

            knowledge = Knowledges.update_knowledge_data_by_id(id=id, data=data)

            if knowledge:
                # 记录文件从知识库移除日志
                print(f"🔍 DEBUG: 从知识库移除文件 - knowledge_id: {id}, file_id: {form_data.file_id}")
                log_knowledge_action(
                    knowledge_id=id,
                    user_id=user.id,
                    user_name=user.name,
                    user_email=user.email,
                    action_type="file_remove",
                    action="从知识库移除文件",
                    description=f"文件 {file.filename} 已从知识库 {knowledge.name} 移除",
                    file_id=form_data.file_id,
                    file_name=file.filename,
                    file_size=file.meta.get("size") if file.meta else None,
                    extra_data={
                        "collection_name": id,
                        "delete_file": delete_file
                    }
                )
                
                files = Files.get_file_metadatas_by_ids(file_ids)

                return KnowledgeFilesResponse(
                    **knowledge.model_dump(),
                    files=files,
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT("knowledge"),
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("file_id"),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


@router.post("/{id}/vlm-optimize")
async def save_vlm_optimized_result(
    id: str,
    payload: dict = Body(...),
    user=Depends(get_verified_user),
):
    from pathlib import Path

    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        knowledge.user_id != user.id
        and not has_access(user.id, "write", knowledge.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    filename = payload.get("filename")
    content = payload.get("content")
    if not filename or not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="filename and content are required",
        )

    knowledge_dir = Path(UPLOAD_DIR) / "knowledge" / id
    knowledge_dir.mkdir(parents=True, exist_ok=True)
    vlm_dir = knowledge_dir / "vlm_optimized"
    vlm_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = filename.replace("/", "_")
    target_path = vlm_dir / safe_filename

    try:
        target_path.write_text(content, encoding="utf-8")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {e}",
        )

    relative_path = target_path.relative_to(Path(UPLOAD_DIR) / "knowledge")
    return {
        "status": "success",
        "path": str(relative_path),
    }


############################
# DeleteKnowledgeById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_knowledge_by_id(id: str, user=Depends(get_verified_user)):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        knowledge.user_id != user.id
        and not has_access(user.id, "write", knowledge.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    log.info(f"Deleting knowledge base: {id} (name: {knowledge.name})")

    # 记录知识库删除日志
    print(f"🔍 DEBUG: 删除知识库 - knowledge_id: {id}, name: {knowledge.name}")
    log_knowledge_action(
        knowledge_id=id,
        user_id=user.id,
        user_name=user.name,
        user_email=user.email,
        action_type="knowledge_delete",
        action="删除知识库",
        description=f"知识库 {knowledge.name} 已删除",
        extra_data={
            "knowledge_name": knowledge.name,
            "access_control": knowledge.access_control,
            "description": knowledge.description,
            "file_count": len(knowledge.data.get("file_ids", [])) if knowledge.data else 0
        }
    )

    # Get all models
    models = Models.get_all_models()
    log.info(f"Found {len(models)} models to check for knowledge base {id}")

    # Update models that reference this knowledge base
    for model in models:
        if model.meta and hasattr(model.meta, "knowledge"):
            knowledge_list = model.meta.knowledge or []
            # Filter out the deleted knowledge base
            updated_knowledge = [k for k in knowledge_list if k.get("id") != id]

            # If the knowledge list changed, update the model
            if len(updated_knowledge) != len(knowledge_list):
                log.info(f"Updating model {model.id} to remove knowledge base {id}")
                model.meta.knowledge = updated_knowledge
                # Create a ModelForm for the update
                model_form = ModelForm(
                    id=model.id,
                    name=model.name,
                    base_model_id=model.base_model_id,
                    meta=model.meta,
                    params=model.params,
                    access_control=model.access_control,
                    is_active=model.is_active,
                )
                Models.update_model_by_id(model.id, model_form)

    # Clean up vector DB
    try:
        VECTOR_DB_CLIENT.delete_collection(collection_name=id)
    except Exception as e:
        log.debug(e)
        pass
    result = Knowledges.delete_knowledge_by_id(id=id)
    return result


############################
# ResetKnowledgeById
############################


@router.post("/{id}/reset", response_model=Optional[KnowledgeResponse])
async def reset_knowledge_by_id(id: str, user=Depends(get_verified_user)):
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        knowledge.user_id != user.id
        and not has_access(user.id, "write", knowledge.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    try:
        VECTOR_DB_CLIENT.delete_collection(collection_name=id)
    except Exception as e:
        log.debug(e)
        pass

    knowledge = Knowledges.update_knowledge_data_by_id(id=id, data={"file_ids": []})

    return knowledge


############################
# AddFilesToKnowledge
############################


@router.post("/{id}/files/batch/add", response_model=Optional[KnowledgeFilesResponse])
def add_files_to_knowledge_batch(
    request: Request,
    id: str,
    form_data: list[KnowledgeFileIdForm],
    user=Depends(get_verified_user),
):
    """
    Add multiple files to a knowledge base
    """
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        knowledge.user_id != user.id
        and not has_access(user.id, "write", knowledge.access_control)
        and user.role != "admin"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    # Get files content
    log.info(f"files/batch/add - {len(form_data)} files")
    files: List[FileModel] = []
    for form in form_data:
        file = Files.get_file_by_id(form.file_id)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {form.file_id} not found",
            )
        files.append(file)

    # Process files
    try:
        result = process_files_batch(
            request=request,
            form_data=BatchProcessFilesForm(files=files, collection_name=id),
            user=user,
        )
    except Exception as e:
        log.error(
            f"add_files_to_knowledge_batch: Exception occurred: {e}", exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Add successful files to knowledge base
    data = knowledge.data or {}
    existing_file_ids = data.get("file_ids", [])

    # Only add files that were successfully processed
    successful_file_ids = [r.file_id for r in result.results if r.status == "completed"]
    for file_id in successful_file_ids:
        if file_id not in existing_file_ids:
            existing_file_ids.append(file_id)

    data["file_ids"] = existing_file_ids
    knowledge = Knowledges.update_knowledge_data_by_id(id=id, data=data)

    # If there were any errors, include them in the response
    if result.errors:
        error_details = [f"{err.file_id}: {err.error}" for err in result.errors]
        return KnowledgeFilesResponse(
            **knowledge.model_dump(),
            files=Files.get_file_metadatas_by_ids(existing_file_ids),
            warnings={
                "message": "Some files failed to process",
                "errors": error_details,
            },
        )

    return KnowledgeFilesResponse(
        **knowledge.model_dump(),
        files=Files.get_file_metadatas_by_ids(existing_file_ids),
    )


# PDF转图片API端点
@router.post("/{id}/files/{file_id}/pdf-to-image")
async def convert_pdf_to_image(
    id: str,
    file_id: str,
    page: int = 1,
    user=Depends(get_verified_user)
):
    """
    将PDF文件的指定页面转换为图片
    """
    try:
        # 验证知识库权限
        knowledge = Knowledges.get_knowledge_by_id(id=id)
        if not knowledge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Knowledge base not found"
            )
        
        if (
            knowledge.user_id != user.id
            and not has_access(user.id, "read", knowledge.access_control)
            and user.role != "admin"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )
        
        # 获取文件
        file = Files.get_file_by_id(file_id)
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # 检查文件类型
        if not file.meta.get("content_type", "").startswith("application/pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File is not a PDF"
            )
        
        # 调用Python脚本进行PDF转图片
        import subprocess
        import tempfile
        import os
        
        # 获取实际文件路径
        file_path = Storage.get_file(file.path)
        
        # 调用Python脚本
        script_path = os.path.join(os.path.dirname(__file__), "../../../pdf_to_image.py")
        result = subprocess.run(
            ["python3", script_path, file_path, str(page), "200"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"PDF conversion failed: {result.stderr}"
            )
        
        return {
            "success": True,
            "imageDataUrl": result.stdout.strip(),
            "pageNumber": page,
            "message": "PDF转图片完成"
        }
                
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="PDF conversion timeout"
        )
    except Exception as e:
        log.error(f"PDF转图片失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF conversion failed: {str(e)}"
        )


############################
# Move OCR Result Directory
############################

class MoveOCRResultForm(BaseModel):
    source_path: str
    target_path: str


@router.post("/{id}/move-ocr-result")
async def move_ocr_result_directory(
    id: str,
    form_data: MoveOCRResultForm,
    user=Depends(get_verified_user)
):
    """移动 OCR 结果目录到知识库目录"""
    try:
        import shutil
        import os
        from pathlib import Path
        
        # 验证知识库访问权限
        knowledge = Knowledges.get_knowledge_by_id(id=id)
        if not knowledge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND
            )
        
        if (
            user.role != "admin"
            and knowledge.user_id != user.id
            and not has_access(user.id, "write", knowledge.access_control)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED
            )
        
        source_path = Path(form_data.source_path)
        target_path = Path(form_data.target_path)
        
        # 验证源路径存在
        if not source_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Source path does not exist: {source_path}"
            )
        
        # 确保目标目录的父目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果目标路径已存在，先删除
        if target_path.exists():
            if target_path.is_dir():
                shutil.rmtree(target_path)
            else:
                target_path.unlink()
        
        # 移动目录
        shutil.move(str(source_path), str(target_path))
        
        log.info(f"OCR result directory moved: {source_path} -> {target_path}")
        
        return {
            "success": True,
            "message": "OCR result directory moved successfully",
            "source_path": str(source_path),
            "target_path": str(target_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"移动 OCR 结果目录失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to move OCR result directory: {str(e)}"
        )


############################
# Get Knowledge Directory File
############################

@router.get("/{id}/files/{file_path:path}")
async def get_knowledge_directory_file(
    id: str,
    file_path: str,
    user=Depends(get_verified_user)
):
    """获取知识库目录下的文件（用于访问 OCR 结果中的图片等）"""
    try:
        from pathlib import Path
        from fastapi.responses import FileResponse
        
        # 验证知识库访问权限
        knowledge = Knowledges.get_knowledge_by_id(id=id)
        if not knowledge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND
            )
        
        if (
            user.role != "admin"
            and knowledge.user_id != user.id
            and not has_access(user.id, "read", knowledge.access_control)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED
            )
        
        # 构建知识库目录路径
        knowledge_dir = UPLOAD_DIR / "knowledge" / id
        
        # 构建文件完整路径（防止路径遍历攻击）
        file_full_path = (knowledge_dir / file_path).resolve()
        
        # 验证文件在知识库目录内（防止路径遍历）
        if not str(file_full_path).startswith(str(knowledge_dir.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: File path outside knowledge directory"
            )
        
        # 检查文件是否存在
        if not file_full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_path}"
            )
        
        if not file_full_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Path is not a file"
            )
        
        # 返回文件
        return FileResponse(
            str(file_full_path),
            media_type="application/octet-stream"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"获取知识库文件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get knowledge file: {str(e)}"
        )


############################
# List Knowledge Directory Files
############################

@router.get("/{id}/files-list/{dir_path:path}")
async def list_knowledge_directory_files(
    id: str,
    dir_path: str,
    user=Depends(get_verified_user)
):
    """列出知识库目录下的文件（用于获取 OCR 结果中的页面列表等）"""
    try:
        from pathlib import Path
        
        # 验证知识库访问权限
        knowledge = Knowledges.get_knowledge_by_id(id=id)
        if not knowledge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND
            )
        
        if (
            user.role != "admin"
            and knowledge.user_id != user.id
            and not has_access(user.id, "read", knowledge.access_control)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED
            )
        
        # 构建知识库目录路径
        knowledge_dir = UPLOAD_DIR / "knowledge" / id
        
        # 构建目录完整路径（防止路径遍历攻击）
        dir_full_path = (knowledge_dir / dir_path).resolve()
        
        # 验证目录在知识库目录内（防止路径遍历）
        if not str(dir_full_path).startswith(str(knowledge_dir.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Directory path outside knowledge directory"
            )
        
        # 检查目录是否存在
        if not dir_full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Directory not found: {dir_path}"
            )
        
        if not dir_full_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path is not a directory: {dir_path}"
            )
        
        # 列出目录下的文件
        files = []
        try:
            for file_path in dir_full_path.iterdir():
                if file_path.is_file():
                    # 计算相对路径
                    relative_path = file_path.relative_to(knowledge_dir)
                    files.append({
                        "name": file_path.name,
                        "path": str(relative_path),
                        "size": file_path.stat().st_size,
                        "extension": file_path.suffix
                    })
        except Exception as e:
            log.exception(f"Error listing directory files: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list directory files: {str(e)}"
            )
        
        # 按文件名排序
        files.sort(key=lambda x: x["name"])
        
        return {
            "status": "success",
            "directory": dir_path,
            "files": files,
            "count": len(files)
        }
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error listing knowledge directory files: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list directory files: {str(e)}"
        )


############################
# Save Knowledge Directory File
############################

class SaveKnowledgeFileForm(BaseModel):
    file_path: str
    content: str
    is_base64: bool = False  # 是否为基础64编码的二进制文件


@router.post("/{id}/files-save")
async def save_knowledge_directory_file(
    id: str,
    form_data: SaveKnowledgeFileForm,
    user=Depends(get_verified_user)
):
    """保存文件内容到知识库目录（用于更新 OCR 结果等）"""
    try:
        from pathlib import Path
        
        # 验证知识库访问权限
        knowledge = Knowledges.get_knowledge_by_id(id=id)
        if not knowledge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND
            )
        
        if (
            user.role != "admin"
            and knowledge.user_id != user.id
            and not has_access(user.id, "write", knowledge.access_control)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED
            )
        
        # 构建知识库目录路径
        knowledge_dir = UPLOAD_DIR / "knowledge" / id
        
        # 构建文件完整路径（防止路径遍历攻击）
        file_full_path = (knowledge_dir / form_data.file_path).resolve()
        
        # 验证文件在知识库目录内（防止路径遍历）
        if not str(file_full_path).startswith(str(knowledge_dir.resolve())):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: File path outside knowledge directory"
            )
        
        # 确保目录存在
        file_full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存文件内容
        if form_data.is_base64:
            # 如果是 base64 编码的二进制文件，解码后保存
            import base64
            try:
                binary_data = base64.b64decode(form_data.content)
                with open(file_full_path, 'wb') as f:
                    f.write(binary_data)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid base64 content: {str(e)}"
                )
        else:
            # 文本文件，使用 UTF-8 编码保存
            with open(file_full_path, 'w', encoding='utf-8') as f:
                f.write(form_data.content)
        
        log.info(f"文件已保存: {file_full_path}")
        
        return {
            "success": True,
            "message": "File saved successfully",
            "file_path": form_data.file_path
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"保存知识库文件失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save knowledge file: {str(e)}"
        )


############################
# OCR Segments (Auto Split)
############################


class AutoSegmentForm(BaseModel):
    ocr_task_id: str
    source_file: str = "result.mmd"
    max_heading_level: int = 3
    overwrite: bool = True


def _split_markdown_sections(
    text: str, max_heading_level: int = 3
) -> list[dict]:
    """
    根据中文章节编号切分文本，返回分段内容与元信息
    过滤掉包含 #page 标识符的行和标题本身是 Page X 格式的标题
    
    分段规则：
    H1: 按照"一、"、"二、"等中文数字分段，从"一、"开始，到"二、"之前结束
    H2: 在一级分段内，按照"1."、"2."等数字分段，从"1."开始，到下一个"2."之前结束
    H3: 在二级分段内，按照"1.1."、"1.2."等格式分段，从"1.1."开始，到下一个"1.2."之前结束
    """
    sections: list[dict] = []
    lines = text.splitlines()
    current_lines: list[str] = []
    current_heading = None
    current_level = None

    # 匹配 #page 标识符
    page_pattern = re.compile(r"#\s*page\s*\d*", re.IGNORECASE)
    # 匹配标题文本是否为 Page X 格式
    page_title_pattern = re.compile(r"^page\s+\d+$", re.IGNORECASE)
    
    # 匹配中文章节编号：一、二、三、... 十、十一、...（可能后面有标题文本）
    chinese_number_pattern = re.compile(r"^[一二三四五六七八九十百千万]+[、，]\s*(.*)")
    # 匹配一级数字编号：1. 2. 3. ...（可能后面有标题文本，注意：数字后可能是 . 或 、）
    level1_number_pattern = re.compile(r"^(\d+)[\.、]\s*(.*)")
    # 匹配二级数字编号：1.1. 1.2. 2.1. ...（可能后面有标题文本）
    level2_number_pattern = re.compile(r"^(\d+)[\.、]\s*(\d+)[\.、]\s*(.*)")
    # 匹配三级数字编号：1.1.1. 1.1.2. ...（可能后面有标题文本）
    level3_number_pattern = re.compile(r"^(\d+)[\.、]\s*(\d+)[\.、]\s*(\d+)[\.、]\s*(.*)")
    
    # 匹配 Markdown 标题格式
    heading_pattern = re.compile(r"^(#{1,6})\s+(.*)")

    # 辅助函数：判断行是否包含章节编号
    def get_section_level_and_title(line: str) -> tuple[int | None, str | None]:
        """返回 (层级, 标题文本)，如果没有匹配则返回 (None, None)"""
        stripped = line.strip()
        
        # 先检查是否是 Markdown 标题
        match = heading_pattern.match(stripped)
        if match:
            heading_text = match.group(2).strip()
            # 跳过 Page X 格式的标题
            if page_title_pattern.match(heading_text):
                return None, None
            
            # 检查标题文本中的章节编号
            chinese_match = chinese_number_pattern.match(heading_text)
            if chinese_match:
                title = chinese_match.group(1).strip() if chinese_match.group(1) else heading_text
                return 1, heading_text
            
            level3_match = level3_number_pattern.match(heading_text)
            if level3_match:
                return 3, heading_text
            
            level2_match = level2_number_pattern.match(heading_text)
            if level2_match:
                return 2, heading_text
            
            level1_match = level1_number_pattern.match(heading_text)
            if level1_match:
                return 2, heading_text
            
            # 普通 Markdown 标题，不按章节编号分段
            return None, None
        
        # 检查是否是独立的章节编号行（不以 # 开头）
        chinese_match = chinese_number_pattern.match(stripped)
        if chinese_match:
            title = chinese_match.group(1).strip() if chinese_match.group(1) else stripped
            return 1, stripped
        
        level3_match = level3_number_pattern.match(stripped)
        if level3_match:
            return 3, stripped
        
        level2_match = level2_number_pattern.match(stripped)
        if level2_match:
            return 2, stripped
        
        level1_match = level1_number_pattern.match(stripped)
        if level1_match:
            return 2, stripped
        
        return None, None

    # 扫描文档，确定实际使用的分段层级
    actual_levels = set()
    for line in lines:
        if page_pattern.search(line):
            continue
        level, _ = get_section_level_and_title(line)
        if level:
            actual_levels.add(level)
    
    # 确定实际分段层级：优先使用H1（中文数字），其次H2（1. 2.），最后H3（1.1. 1.2.）
    actual_split_level = 1
    if actual_levels:
        # 优先检查是否有H1（中文数字）
        if 1 in actual_levels:
            actual_split_level = 1
        # 如果没有H1，检查是否有H2（1. 2.）
        elif 2 in actual_levels and 2 <= max_heading_level:
            actual_split_level = 2
        # 如果没有H1和H2，检查是否有H3（1.1. 1.2.）
        elif 3 in actual_levels and 3 <= max_heading_level:
            actual_split_level = 3

    # 按照确定的层级进行分段
    for i, line in enumerate(lines):
        # 过滤掉包含 #page 标识符的行
        if page_pattern.search(line):
            continue
        
        level, title = get_section_level_and_title(line)
        
        if level is not None and title:
            # 只有当层级等于实际分段层级时，才创建新分段
            if level == actual_split_level:
                # 检查前一个分段是否是目录项（只有标题行，后面直接是下一个章节编号）
                is_toc_item = False
                if current_lines and current_heading is not None:
                    # 检查当前分段是否只有标题行（可能是目录项）
                    filtered_lines = [l for l in current_lines if not page_pattern.search(l)]
                    content_lines = [l.strip() for l in filtered_lines if l.strip()]
                    # 如果只有标题行，或者只有标题行和空行，可能是目录项
                    if len(content_lines) <= 1:
                        # 检查后面几行是否直接是下一个章节编号
                        lookahead_count = 0
                        for j in range(i + 1, min(i + 5, len(lines))):
                            lookahead_line = lines[j].strip()
                            if not lookahead_line or page_pattern.search(lookahead_line):
                                continue
                            next_level, _ = get_section_level_and_title(lookahead_line)
                            if next_level is not None:
                                # 如果后面直接是相同层级或更高层级的章节编号，说明这是目录项
                                if next_level <= actual_split_level:
                                    is_toc_item = True
                                break
                            lookahead_count += 1
                            if lookahead_count >= 3:  # 如果后面3行内没有章节编号，说明有实际内容
                                break
                
                if current_lines and current_heading is not None and not is_toc_item:
                    # 过滤掉所有包含 #page 的行
                    filtered_lines = [l for l in current_lines if not page_pattern.search(l)]
                    content = "\n".join(filtered_lines).strip()
                    # 只有实际内容才保存分段
                    if content:
                        sections.append(
                            {
                                "heading": current_heading,
                                "level": current_level,
                                "content": content,
                            }
                        )

                # 开始新分段（即使是目录项也更新，但不会保存）
                current_lines = [line]
                current_heading = title or f"Section {len(sections) + 1}"
                current_level = level
            elif level < actual_split_level:
                # 如果遇到更高层级的标题（如一级标题），也创建新分段
                # 检查前一个分段是否是目录项
                is_toc_item = False
                if current_lines and current_heading is not None:
                    filtered_lines = [l for l in current_lines if not page_pattern.search(l)]
                    content_lines = [l.strip() for l in filtered_lines if l.strip()]
                    if len(content_lines) <= 1:
                        # 检查后面几行是否直接是下一个章节编号
                        lookahead_count = 0
                        for j in range(i + 1, min(i + 5, len(lines))):
                            lookahead_line = lines[j].strip()
                            if not lookahead_line or page_pattern.search(lookahead_line):
                                continue
                            next_level, _ = get_section_level_and_title(lookahead_line)
                            if next_level is not None:
                                if next_level <= level:
                                    is_toc_item = True
                                break
                            lookahead_count += 1
                            if lookahead_count >= 3:
                                break
                
                if current_lines and current_heading is not None and not is_toc_item:
                    # 过滤掉所有包含 #page 的行
                    filtered_lines = [l for l in current_lines if not page_pattern.search(l)]
                    content = "\n".join(filtered_lines).strip()
                    if content:
                        sections.append(
                            {
                                "heading": current_heading,
                                "level": current_level,
                                "content": content,
                            }
                        )

                current_lines = [line]
                current_heading = title or f"Section {len(sections) + 1}"
                current_level = level
            else:
                # 其他层级的标题或内容，添加到当前内容中（但也要过滤 #page）
                if current_lines and not page_pattern.search(line):
                    current_lines.append(line)
        else:
            # 非章节编号行，添加到当前内容中（但也要过滤 #page）
            if current_lines and not page_pattern.search(line):
                current_lines.append(line)

    if current_lines and current_heading is not None:
        # 过滤掉所有包含 #page 的行
        filtered_lines = [l for l in current_lines if not page_pattern.search(l)]
        content_lines = [l.strip() for l in filtered_lines if l.strip()]
        content = "\n".join(filtered_lines).strip()
        # 只有实际内容才保存分段（跳过只有标题行的目录项）
        if content and len(content_lines) > 1:
            sections.append(
                {
                    "heading": current_heading,
                    "level": current_level,
                    "content": content,
                }
            )

    return sections


def _write_segments_to_disk(
    knowledge_dir: Path,
    ocr_task_id: str,
    sections: list[dict],
    source_file: str,
    overwrite: bool = True,
) -> dict:
    """
    将分段内容写入磁盘，并生成 manifest
    """
    if not sections:
        raise ValueError("No sections to write")

    ocr_dir = knowledge_dir / f"ocr_result_{ocr_task_id}"
    if not ocr_dir.exists():
        raise FileNotFoundError(
            f"OCR result directory not found: ocr_result_{ocr_task_id}"
        )

    segments_dir = ocr_dir / "segments"
    if segments_dir.exists() and overwrite:
        shutil.rmtree(segments_dir)

    segments_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "knowledge_id": knowledge_dir.name,
        "ocr_task_id": ocr_task_id,
        "source_file": source_file,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "segment_count": len(sections),
        "segments": [],
    }

    for idx, section in enumerate(sections, 1):
        file_name = f"segment_{idx:03d}.mmd"
        file_path = segments_dir / file_name
        file_path.write_text(section["content"] + "\n", encoding="utf-8")

        preview = section["content"].splitlines()[0] if section["content"] else ""
        preview = preview[:160]

        manifest["segments"].append(
            {
                "id": f"segment_{idx:03d}",
                "heading": section["heading"],
                "level": section["level"],
                "file": str(file_path.relative_to(knowledge_dir)),
                "preview": preview,
                "order": idx,
            }
        )

    manifest_path = segments_dir / "index.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return manifest


@router.post("/{id}/segments/auto")
async def auto_segment_ocr_result(
    id: str,
    form_data: AutoSegmentForm,
    user=Depends(get_verified_user),
):
    """
    根据 OCR result.mmd 自动分段，并生成 segments 目录
    """
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        user.role != "admin"
        and knowledge.user_id != user.id
        and not has_access(user.id, "write", knowledge.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    knowledge_dir = UPLOAD_DIR / "knowledge" / id
    ocr_dir = knowledge_dir / f"ocr_result_{form_data.ocr_task_id}"
    if not ocr_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"OCR result directory not found: ocr_result_{form_data.ocr_task_id}",
        )

    source_path = (ocr_dir / form_data.source_file).resolve()
    if not source_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source file not found: {form_data.source_file}",
        )

    try:
        text = source_path.read_text(encoding="utf-8")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read source file: {exc}",
        )

    sections = _split_markdown_sections(text, max_heading_level=form_data.max_heading_level)
    if not sections:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No sections found using provided heading rules",
        )

    try:
        manifest = _write_segments_to_disk(
            knowledge_dir=knowledge_dir,
            ocr_task_id=form_data.ocr_task_id,
            sections=sections,
            source_file=form_data.source_file,
            overwrite=form_data.overwrite,
        )
    except Exception as exc:
        log.exception("Failed to write segments: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write segments: {exc}",
        )

    return {
        "status": "success",
        "segment_count": manifest["segment_count"],
        "manifest": manifest,
    }


@router.get("/{id}/segments")
async def get_ocr_segments(
    id: str,
    ocr_task_id: str = Query(..., description="OCR 任务 ID，例如 7ee32dd9"),
    user=Depends(get_verified_user),
):
    """
    获取指定 OCR 任务的分段 manifest
    """
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        user.role != "admin"
        and knowledge.user_id != user.id
        and not has_access(user.id, "read", knowledge.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    knowledge_dir = UPLOAD_DIR / "knowledge" / id
    manifest_path = knowledge_dir / f"ocr_result_{ocr_task_id}" / "segments" / "index.json"

    if not manifest_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segments manifest not found. Please run auto segmentation first.",
        )

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        log.exception("Failed to read segments manifest: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read manifest: {exc}",
        )

    return {
        "status": "success",
        "segment_count": data.get("segment_count", 0),
        "manifest": data,
    }


@router.delete("/{id}/segments")
async def delete_ocr_segments(
    id: str,
    ocr_task_id: str = Query(..., description="OCR 任务 ID，例如 7ee32dd9"),
    user=Depends(get_verified_user),
):
    """
    删除指定 OCR 任务的分段目录
    """
    knowledge = Knowledges.get_knowledge_by_id(id=id)
    if not knowledge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if (
        user.role != "admin"
        and knowledge.user_id != user.id
        and not has_access(user.id, "write", knowledge.access_control)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    knowledge_dir = UPLOAD_DIR / "knowledge" / id
    segments_dir = knowledge_dir / f"ocr_result_{ocr_task_id}" / "segments"

    if not segments_dir.exists():
        return {
            "status": "success",
            "message": "Segments directory already removed",
        }

    try:
        shutil.rmtree(segments_dir)
    except Exception as exc:
        log.exception("Failed to delete segments directory: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete segments: {exc}",
        )

    return {
        "status": "success",
        "message": "Segments deleted successfully",
    }
