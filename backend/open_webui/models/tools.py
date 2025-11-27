import logging
import time
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_db
from open_webui.models.users import Users, UserResponse
from open_webui.models.groups import Groups

from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, Boolean

from open_webui.utils.access_control import has_access


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Tools DB Schema
####################


class Tool(Base):
    __tablename__ = "tool"

    id = Column(String, primary_key=True)
    user_id = Column(String)
    name = Column(Text)
    content = Column(Text)
    specs = Column(JSONField)
    meta = Column(JSONField)
    valves = Column(JSONField)

    access_control = Column(JSON, nullable=True)  # Controls data access levels.
    # Defines access control rules for this entry.
    # - `None`: Public access, available to all users with the "user" role.
    # - `{}`: Private access, restricted exclusively to the owner.
    # - Custom permissions: Specific access control for reading and writing;
    #   Can specify group or user-level restrictions:
    #   {
    #      "read": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      },
    #      "write": {
    #          "group_ids": ["group_id1", "group_id2"],
    #          "user_ids":  ["user_id1", "user_id2"]
    #      }
    #   }

    is_default_for_all_users = Column(Boolean, nullable=True, default=False)  # Whether this tool is default for all users
    # - `False` or `None`: Not a default tool
    # - `True`: This tool will be automatically selected for all users

    default_for_group_ids = Column(JSONField, nullable=True)  # List of group IDs for which this tool is default
    # - `None` or `[]`: Not a default tool for any group
    # - `["group_id1", "group_id2"]`: This tool will be automatically selected for users in these groups

    updated_at = Column(BigInteger)
    created_at = Column(BigInteger)


class ToolMeta(BaseModel):
    description: Optional[str] = None
    manifest: Optional[dict] = {}


class ToolModel(BaseModel):
    id: str
    user_id: str
    name: str
    content: str
    specs: list[dict]
    meta: ToolMeta
    access_control: Optional[dict] = None
    is_default_for_all_users: Optional[bool] = False
    default_for_group_ids: Optional[list[str]] = None

    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch

    model_config = ConfigDict(from_attributes=True)


####################
# Forms
####################


class ToolUserModel(ToolModel):
    user: Optional[UserResponse] = None


class ToolResponse(BaseModel):
    id: str
    user_id: str
    name: str
    meta: ToolMeta
    access_control: Optional[dict] = None
    is_default_for_all_users: Optional[bool] = False
    default_for_group_ids: Optional[list[str]] = None
    updated_at: int  # timestamp in epoch
    created_at: int  # timestamp in epoch


class ToolUserResponse(ToolResponse):
    user: Optional[UserResponse] = None

    model_config = ConfigDict(extra="allow")


class ToolForm(BaseModel):
    id: str
    name: str
    content: str
    meta: ToolMeta
    access_control: Optional[dict] = None
    is_default_for_all_users: Optional[bool] = False
    default_for_group_ids: Optional[list[str]] = None


class ToolValves(BaseModel):
    valves: Optional[dict] = None


class ToolsTable:
    def insert_new_tool(
        self, user_id: str, form_data: ToolForm, specs: list[dict]
    ) -> Optional[ToolModel]:
        with get_db() as db:
            tool = ToolModel(
                **{
                    **form_data.model_dump(),
                    "specs": specs,
                    "user_id": user_id,
                    "updated_at": int(time.time()),
                    "created_at": int(time.time()),
                }
            )

            try:
                result = Tool(**tool.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                if result:
                    return ToolModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                log.exception(f"Error creating a new tool: {e}")
                return None

    def get_tool_by_id(self, id: str) -> Optional[ToolModel]:
        try:
            with get_db() as db:
                tool = db.get(Tool, id)
                if tool:
                    # Parse JSON fields that might be stored as strings
                    import json
                    tool_data = {
                        'id': tool.id,
                        'user_id': tool.user_id,
                        'name': tool.name,
                        'content': tool.content,
                        'updated_at': tool.updated_at,
                        'created_at': tool.created_at,
                    }
                    
                    # Parse specs
                    specs = getattr(tool, 'specs', None)
                    if specs is None:
                        tool_data['specs'] = []
                    elif isinstance(specs, str):
                        try:
                            tool_data['specs'] = json.loads(specs)
                        except:
                            tool_data['specs'] = []
                    else:
                        tool_data['specs'] = specs
                    
                    # Parse meta
                    meta = getattr(tool, 'meta', None)
                    if meta is None:
                        tool_data['meta'] = {}
                    elif isinstance(meta, str):
                        try:
                            tool_data['meta'] = json.loads(meta)
                        except:
                            tool_data['meta'] = {}
                    else:
                        tool_data['meta'] = meta
                    
                    # Parse access_control
                    access_control = getattr(tool, 'access_control', None)
                    if access_control is None:
                        tool_data['access_control'] = None
                    elif isinstance(access_control, str):
                        try:
                            tool_data['access_control'] = json.loads(access_control) if access_control else None
                        except:
                            tool_data['access_control'] = None
                    else:
                        tool_data['access_control'] = access_control
                    
                    tool_dict = ToolModel.model_validate(tool_data).model_dump()
                    # Ensure is_default_for_all_users is included
                    is_default = getattr(tool, 'is_default_for_all_users', False)
                    if is_default is None:
                        is_default = False
                    tool_dict['is_default_for_all_users'] = bool(is_default)
                    
                    # Ensure default_for_group_ids is included
                    default_group_ids = getattr(tool, 'default_for_group_ids', None)
                    if default_group_ids is None:
                        default_group_ids = []
                    elif isinstance(default_group_ids, str):
                        try:
                            default_group_ids = json.loads(default_group_ids)
                        except:
                            default_group_ids = []
                    if not isinstance(default_group_ids, list):
                        default_group_ids = []
                    tool_dict['default_for_group_ids'] = default_group_ids
                    
                    return ToolModel(**tool_dict)
                return None
        except Exception as e:
            log.exception(f"Error getting tool by id {id}: {e}")
            return None

    def get_tools(self) -> list[ToolUserModel]:
        with get_db() as db:
            try:
                all_tools = db.query(Tool).order_by(Tool.updated_at.desc()).all()
            except Exception as e:
                # If column doesn't exist yet, try to add it
                log.warning(f"Error querying tools, attempting to add missing column: {e}")
                try:
                    from sqlalchemy import inspect, text
                    inspector = inspect(db.bind)
                    cols = [c["name"] for c in inspector.get_columns("tool")]
                    
                    # Add is_default_for_all_users if missing
                    if "is_default_for_all_users" not in cols:
                        if db.bind.dialect.name == "sqlite":
                            db.execute(text("ALTER TABLE tool ADD COLUMN is_default_for_all_users INTEGER DEFAULT 0"))
                        else:
                            db.execute(text("ALTER TABLE tool ADD COLUMN is_default_for_all_users BOOLEAN DEFAULT FALSE"))
                        db.commit()
                        log.info("Added is_default_for_all_users column to tool table")
                        cols.append("is_default_for_all_users")
                    
                    # Add default_for_group_ids if missing
                    if "default_for_group_ids" not in cols:
                        if db.bind.dialect.name == "sqlite":
                            db.execute(text("ALTER TABLE tool ADD COLUMN default_for_group_ids TEXT DEFAULT '[]'"))
                        else:
                            db.execute(text("ALTER TABLE tool ADD COLUMN default_for_group_ids JSON DEFAULT '[]'"))
                        db.commit()
                        log.info("Added default_for_group_ids column to tool table")
                    
                    # Retry the query
                    all_tools = db.query(Tool).order_by(Tool.updated_at.desc()).all()
                except Exception as e2:
                    log.error(f"Failed to add column: {e2}")
                    # Fallback: query without the new columns
                    from sqlalchemy import text
                    # Try to include new columns if they exist
                    try:
                        result = db.execute(text("SELECT id, user_id, name, content, specs, meta, valves, access_control, is_default_for_all_users, default_for_group_ids, updated_at, created_at FROM tool ORDER BY updated_at DESC"))
                        all_tools = []
                        for row in result:
                            tool_dict = {
                                "id": row[0],
                                "user_id": row[1],
                                "name": row[2],
                                "content": row[3],
                                "specs": row[4] if row[4] else {},
                                "meta": row[5] if row[5] else {},
                                "valves": row[6] if row[6] else {},
                                "access_control": row[7],
                                "is_default_for_all_users": bool(row[8]) if len(row) > 8 else False,
                                "default_for_group_ids": row[9] if len(row) > 9 else [],
                                "updated_at": row[10] if len(row) > 10 else row[8],
                                "created_at": row[11] if len(row) > 11 else row[9],
                            }
                            all_tools.append(Tool(**tool_dict))
                    except:
                        # Ultimate fallback: query without new columns
                        result = db.execute(text("SELECT id, user_id, name, content, specs, meta, valves, access_control, updated_at, created_at FROM tool ORDER BY updated_at DESC"))
                        all_tools = []
                        for row in result:
                            tool_dict = {
                                "id": row[0],
                                "user_id": row[1],
                                "name": row[2],
                                "content": row[3],
                                "specs": row[4] if row[4] else {},
                                "meta": row[5] if row[5] else {},
                                "valves": row[6] if row[6] else {},
                                "access_control": row[7],
                                "updated_at": row[8],
                                "created_at": row[9],
                                "is_default_for_all_users": False,  # Default value
                                "default_for_group_ids": [],  # Default value
                            }
                            all_tools.append(Tool(**tool_dict))

            user_ids = list(set(tool.user_id for tool in all_tools))

            users = Users.get_users_by_user_ids(user_ids) if user_ids else []
            users_dict = {user.id: user for user in users}

            tools = []
            import json
            for tool in all_tools:
                user = users_dict.get(tool.user_id)
                # Handle missing is_default_for_all_users attribute
                is_default = getattr(tool, 'is_default_for_all_users', False)
                # Convert to boolean (SQLite stores as INTEGER 0/1)
                if is_default is None:
                    is_default = False
                is_default = bool(is_default)
                
                # Handle default_for_group_ids
                default_group_ids = getattr(tool, 'default_for_group_ids', None)
                if default_group_ids is None:
                    default_group_ids = []
                elif isinstance(default_group_ids, str):
                    # Handle JSON string from SQLite
                    try:
                        default_group_ids = json.loads(default_group_ids)
                    except:
                        default_group_ids = []
                if not isinstance(default_group_ids, list):
                    default_group_ids = []
                
                # Parse JSON fields that might be stored as strings in SQLite
                tool_data = {
                    'id': tool.id,
                    'user_id': tool.user_id,
                    'name': tool.name,
                    'content': tool.content,
                    'updated_at': tool.updated_at,
                    'created_at': tool.created_at,
                }
                
                # Parse specs (JSONField)
                specs = getattr(tool, 'specs', None)
                if specs is None:
                    tool_data['specs'] = []
                elif isinstance(specs, str):
                    try:
                        tool_data['specs'] = json.loads(specs)
                    except:
                        tool_data['specs'] = []
                else:
                    tool_data['specs'] = specs
                
                # Parse meta (JSONField)
                meta = getattr(tool, 'meta', None)
                if meta is None:
                    tool_data['meta'] = {}
                elif isinstance(meta, str):
                    try:
                        tool_data['meta'] = json.loads(meta)
                    except:
                        tool_data['meta'] = {}
                else:
                    tool_data['meta'] = meta
                
                # Parse access_control (JSON)
                access_control = getattr(tool, 'access_control', None)
                if access_control is None:
                    tool_data['access_control'] = None
                elif isinstance(access_control, str):
                    try:
                        tool_data['access_control'] = json.loads(access_control) if access_control else None
                    except:
                        tool_data['access_control'] = None
                else:
                    tool_data['access_control'] = access_control
                
                # Now validate with properly parsed data
                tool_dict = ToolModel.model_validate(tool_data).model_dump()
                tool_dict['is_default_for_all_users'] = is_default
                tool_dict['default_for_group_ids'] = default_group_ids
                tools.append(
                    ToolUserModel.model_validate(
                        {
                            **tool_dict,
                            "user": user.model_dump() if user else None,
                        }
                    )
                )
            return tools

    def get_tools_by_user_id(
        self, user_id: str, permission: str = "read"
    ) -> list[ToolUserModel]:
        tools = self.get_tools()
        user_group_ids = {group.id for group in Groups.get_groups_by_member_id(user_id)}

        log.info(f"get_tools_by_user_id: Total tools in DB: {len(tools)}")
        
        result = [
            tool
            for tool in tools
            if tool.user_id == user_id
            or has_access(user_id, permission, tool.access_control, user_group_ids)
        ]
        
        log.info(f"get_tools_by_user_id: Tools with access: {len(result)}")
        log.info(f"get_tools_by_user_id: Tool IDs with access: {[t.id for t in result]}")
        
        # 添加所有默认工具（即使没有直接访问权限，默认工具也应该可见）
        # 使用工具ID集合来避免重复
        result_ids = {tool.id for tool in result}
        
        # 互斥逻辑：优先检查 for all users，如果设置了则忽略 groups
        # 如果 for all users 未设置，则检查 groups
        
        # 检查全局默认工具（for all users）
        default_tools = [
            tool
            for tool in tools
            if tool.is_default_for_all_users and tool.id not in result_ids
        ]
        
        # 检查按组设置的默认工具（只在 for all users 未设置时检查）
        # 如果工具设置了 for all users，则不再检查 groups
        group_default_tools = [
            tool
            for tool in tools
            if not tool.is_default_for_all_users  # 互斥：如果设置了 for all users，则忽略 groups
            and tool.default_for_group_ids 
            and any(group_id in tool.default_for_group_ids for group_id in user_group_ids)
            and tool.id not in result_ids
        ]
        
        log.info(f"get_tools_by_user_id: Default tools (all users): {len(default_tools)}")
        log.info(f"get_tools_by_user_id: Default tools (groups): {len(group_default_tools)}")
        log.info(f"get_tools_by_user_id: Default tool IDs: {[t.id for t in default_tools + group_default_tools]}")
        log.info(f"get_tools_by_user_id: Total returned: {len(result + default_tools + group_default_tools)}")
        
        return result + default_tools + group_default_tools

    def get_tool_valves_by_id(self, id: str) -> Optional[dict]:
        try:
            with get_db() as db:
                tool = db.get(Tool, id)
                return tool.valves if tool.valves else {}
        except Exception as e:
            log.exception(f"Error getting tool valves by id {id}")
            return None

    def update_tool_valves_by_id(self, id: str, valves: dict) -> Optional[ToolValves]:
        try:
            with get_db() as db:
                db.query(Tool).filter_by(id=id).update(
                    {"valves": valves, "updated_at": int(time.time())}
                )
                db.commit()
                return self.get_tool_by_id(id)
        except Exception:
            return None

    def get_user_valves_by_id_and_user_id(
        self, id: str, user_id: str
    ) -> Optional[dict]:
        try:
            user = Users.get_user_by_id(user_id)
            if user is None:
                return {}
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "tools" and "valves" settings
            if "tools" not in user_settings:
                user_settings["tools"] = {}
            if "valves" not in user_settings["tools"]:
                user_settings["tools"]["valves"] = {}

            return user_settings["tools"]["valves"].get(id, {})
        except Exception as e:
            log.exception(
                f"Error getting user values by id {id} and user_id {user_id}: {e}"
            )
            return None

    def update_user_valves_by_id_and_user_id(
        self, id: str, user_id: str, valves: dict
    ) -> Optional[dict]:
        try:
            user = Users.get_user_by_id(user_id)
            user_settings = user.settings.model_dump() if user.settings else {}

            # Check if user has "tools" and "valves" settings
            if "tools" not in user_settings:
                user_settings["tools"] = {}
            if "valves" not in user_settings["tools"]:
                user_settings["tools"]["valves"] = {}

            user_settings["tools"]["valves"][id] = valves

            # Update the user settings in the database
            Users.update_user_by_id(user_id, {"settings": user_settings})

            return user_settings["tools"]["valves"][id]
        except Exception as e:
            log.exception(
                f"Error updating user valves by id {id} and user_id {user_id}: {e}"
            )
            return None

    def update_tool_by_id(self, id: str, updated: dict) -> Optional[ToolModel]:
        try:
            with get_db() as db:
                # Ensure default_for_group_ids is serialized as JSON string for SQLite
                if "default_for_group_ids" in updated:
                    import json
                    if isinstance(updated["default_for_group_ids"], (list, dict)):
                        updated["default_for_group_ids"] = json.dumps(updated["default_for_group_ids"])
                
                db.query(Tool).filter_by(id=id).update(
                    {**updated, "updated_at": int(time.time())}
                )
                db.commit()

                # Use get_tool_by_id to properly parse JSON fields
                return self.get_tool_by_id(id)
        except Exception as e:
            log.exception(f"Error updating tool by id {id}: {e}")
            return None

    def delete_tool_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Tool).filter_by(id=id).delete()
                db.commit()

                return True
        except Exception:
            return False


Tools = ToolsTable()
