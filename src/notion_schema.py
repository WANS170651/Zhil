"""
Notion Schema 模块
动态获取和缓存 Notion Database 字段定义
支持同步和异步两种模式
"""

import json
import requests
import httpx
import asyncio
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from cachetools import TTLCache
from enum import Enum

from .config import config


class FieldType(Enum):
    """支持的Notion字段类型枚举"""
    TITLE = "title"
    RICH_TEXT = "rich_text"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    STATUS = "status"
    URL = "url"
    DATE = "date"
    NUMBER = "number"
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    CHECKBOX = "checkbox"
    FILES = "files"
    CREATED_BY = "created_by"
    CREATED_TIME = "created_time"
    LAST_EDITED_BY = "last_edited_by"
    LAST_EDITED_TIME = "last_edited_time"
    PEOPLE = "people"
    FORMULA = "formula"
    RELATION = "relation"
    ROLLUP = "rollup"


@dataclass
class SelectOption:
    """Select/Status选项数据结构"""
    id: str
    name: str
    color: str
    description: Optional[str] = None


@dataclass
class FieldSchema:
    """字段Schema数据结构"""
    name: str
    type: str
    required: bool = False
    description: Optional[str] = None
    
    # Select/Status专用
    options: Optional[List[SelectOption]] = None
    
    # Number专用
    format: Optional[str] = None
    
    # 其他配置
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class DatabaseSchema:
    """数据库Schema数据结构"""
    database_id: str
    title: str
    description: Optional[str]
    fields: Dict[str, FieldSchema]
    title_field: Optional[str]
    url_field: Optional[str]
    created_at: float
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


class NotionSchemaError(Exception):
    """Notion Schema相关异常"""
    pass


class NotionSchemaAPI:
    """Notion Schema API客户端（同步版本）"""
    
    def __init__(self):
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {config.notion_token}",
            "Notion-Version": config.notion_version,
            "Content-Type": "application/json",
        }
        
        # 初始化缓存
        self.cache = TTLCache(
            maxsize=config.schema_cache_maxsize,
            ttl=config.schema_cache_ttl
        )


class AsyncNotionSchemaAPI:
    """异步Notion Schema API客户端"""
    
    def __init__(self):
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {config.notion_token}",
            "Notion-Version": config.notion_version,
            "Content-Type": "application/json",
        }
        
        # 异步HTTP客户端与连接池
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            headers=self.headers
        )
        
        # 初始化缓存
        self.cache = TTLCache(
            maxsize=config.schema_cache_maxsize,
            ttl=config.schema_cache_ttl
        )
    
    async def _make_request_async(self, method: str, url: str, **kwargs) -> httpx.Response:
        """异步HTTP请求"""
        try:
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except httpx.RequestError as e:
            raise NotionSchemaError(f"异步请求失败: {e}")
    
    def _parse_select_options(self, options_data: List[Dict]) -> List[SelectOption]:
        """解析Select/Status选项（与同步版本共享）"""
        options = []
        for opt in options_data:
            options.append(SelectOption(
                id=opt.get("id", ""),
                name=opt.get("name", ""),
                color=opt.get("color", "default"),
                description=opt.get("description")
            ))
        return options
    
    def _parse_field_schema(self, name: str, field_data: Dict[str, Any]) -> FieldSchema:
        """解析单个字段Schema（与同步版本共享）"""
        field_type = field_data.get("type", "")
        
        # 基础字段信息
        field_schema = FieldSchema(
            name=name,
            type=field_type,
            description=field_data.get("description"),
            metadata=field_data
        )
        
        # 处理特殊字段类型
        if field_type in [FieldType.SELECT.value, FieldType.STATUS.value]:
            type_data = field_data.get(field_type, {})
            options_data = type_data.get("options", [])
            field_schema.options = self._parse_select_options(options_data)
        
        elif field_type == FieldType.MULTI_SELECT.value:
            multi_select_data = field_data.get("multi_select", {})
            options_data = multi_select_data.get("options", [])
            field_schema.options = self._parse_select_options(options_data)
        
        elif field_type == FieldType.NUMBER.value:
            number_data = field_data.get("number", {})
            field_schema.format = number_data.get("format")
        
        # Title字段始终必需
        if field_type == FieldType.TITLE.value:
            field_schema.required = True
        
        return field_schema
    
    async def _fetch_database_raw_async(self, database_id: str) -> Dict[str, Any]:
        """异步从API获取原始数据库信息"""
        url = f"{self.base_url}/databases/{database_id}"
        response = await self._make_request_async("GET", url)
        return response.json()
    
    async def get_database_schema_async(self, database_id: Optional[str] = None, 
                                       use_cache: bool = True) -> DatabaseSchema:
        """
        异步获取数据库Schema
        
        Args:
            database_id: 数据库ID，默认使用配置中的ID
            use_cache: 是否使用缓存
            
        Returns:
            DatabaseSchema: 解析后的数据库Schema
        """
        if database_id is None:
            database_id = config.notion_database_id
        
        # 检查缓存
        cache_key = f"schema_{database_id}"
        if use_cache and cache_key in self.cache:
            print(f"🔄 使用缓存的异步Schema: {database_id}")
            return self.cache[cache_key]
        
        print(f"🔍 正在异步获取数据库Schema: {database_id}")
        
        try:
            # 异步获取原始数据
            raw_data = await self._fetch_database_raw_async(database_id)
            
            # 解析基本信息
            title = ""
            title_data = raw_data.get("title", [])
            if title_data and isinstance(title_data, list):
                title = "".join([item.get("plain_text", "") for item in title_data])
            
            description = None
            desc_data = raw_data.get("description", [])
            if desc_data and isinstance(desc_data, list):
                description = "".join([item.get("plain_text", "") for item in desc_data])
            
            # 解析字段
            properties = raw_data.get("properties", {})
            fields = {}
            title_field = None
            url_field = None
            
            for field_name, field_data in properties.items():
                field_schema = self._parse_field_schema(field_name, field_data)
                fields[field_name] = field_schema
                
                # 记录特殊字段
                if field_schema.type == FieldType.TITLE.value:
                    title_field = field_name
                elif field_schema.type == FieldType.URL.value and not url_field:
                    url_field = field_name
            
            # 构建Schema对象
            schema = DatabaseSchema(
                database_id=database_id,
                title=title,
                description=description,
                fields=fields,
                title_field=title_field,
                url_field=url_field,
                created_at=time.time()
            )
            
            # 缓存结果
            if use_cache:
                self.cache[cache_key] = schema
                print(f"💾 异步Schema已缓存，TTL: {config.schema_cache_ttl}秒")
            
            print(f"✅ 异步成功获取Schema，包含 {len(fields)} 个字段")
            return schema
            
        except Exception as e:
            raise NotionSchemaError(f"异步获取Schema失败: {e}")
    
    async def get_field_names_by_type_async(self, field_type: Union[str, FieldType], 
                                          database_id: Optional[str] = None) -> List[str]:
        """异步获取指定类型的字段名列表"""
        schema = await self.get_database_schema_async(database_id)
        
        if isinstance(field_type, FieldType):
            field_type = field_type.value
        
        return [
            name for name, field in schema.fields.items() 
            if field.type == field_type
        ]
    
    async def get_select_options_async(self, field_name: str, 
                                     database_id: Optional[str] = None) -> List[SelectOption]:
        """异步获取Select/Status字段的选项列表"""
        schema = await self.get_database_schema_async(database_id)
        
        if field_name not in schema.fields:
            raise NotionSchemaError(f"字段 '{field_name}' 不存在")
        
        field = schema.fields[field_name]
        if field.type not in [FieldType.SELECT.value, FieldType.STATUS.value, FieldType.MULTI_SELECT.value]:
            raise NotionSchemaError(f"字段 '{field_name}' 不是选择类型字段")
        
        return field.options or []

# 继续同步版本的_make_request方法
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """发起HTTP请求"""
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise NotionSchemaError(f"请求失败: {e}")
    
    def _parse_select_options(self, options_data: List[Dict]) -> List[SelectOption]:
        """解析Select/Status选项"""
        options = []
        for opt in options_data:
            options.append(SelectOption(
                id=opt.get("id", ""),
                name=opt.get("name", ""),
                color=opt.get("color", "default"),
                description=opt.get("description")
            ))
        return options
    
    def _parse_field_schema(self, name: str, field_data: Dict[str, Any]) -> FieldSchema:
        """解析单个字段Schema"""
        field_type = field_data.get("type", "")
        
        # 基础字段信息
        field_schema = FieldSchema(
            name=name,
            type=field_type,
            description=field_data.get("description"),
            metadata=field_data
        )
        
        # 处理特殊字段类型
        if field_type in [FieldType.SELECT.value, FieldType.STATUS.value]:
            type_data = field_data.get(field_type, {})
            options_data = type_data.get("options", [])
            field_schema.options = self._parse_select_options(options_data)
        
        elif field_type == FieldType.MULTI_SELECT.value:
            multi_select_data = field_data.get("multi_select", {})
            options_data = multi_select_data.get("options", [])
            field_schema.options = self._parse_select_options(options_data)
        
        elif field_type == FieldType.NUMBER.value:
            number_data = field_data.get("number", {})
            field_schema.format = number_data.get("format")
        
        # Title字段始终必需
        if field_type == FieldType.TITLE.value:
            field_schema.required = True
        
        return field_schema
    
    def _fetch_database_raw(self, database_id: str) -> Dict[str, Any]:
        """从API获取原始数据库信息"""
        url = f"{self.base_url}/databases/{database_id}"
        response = self._make_request("GET", url)
        return response.json()
    
    def get_database_schema(self, database_id: Optional[str] = None, 
                          use_cache: bool = True) -> DatabaseSchema:
        """
        获取数据库Schema
        
        Args:
            database_id: 数据库ID，默认使用配置中的ID
            use_cache: 是否使用缓存
            
        Returns:
            DatabaseSchema: 解析后的数据库Schema
        """
        if database_id is None:
            database_id = config.notion_database_id
        
        # 检查缓存
        cache_key = f"schema_{database_id}"
        if use_cache and cache_key in self.cache:
            print(f"🔄 使用缓存的Schema: {database_id}")
            return self.cache[cache_key]
        
        print(f"🔍 正在获取数据库Schema: {database_id}")
        
        try:
            # 获取原始数据
            raw_data = self._fetch_database_raw(database_id)
            
            # 解析基本信息
            title = ""
            title_data = raw_data.get("title", [])
            if title_data and isinstance(title_data, list):
                title = "".join([item.get("plain_text", "") for item in title_data])
            
            description = None
            desc_data = raw_data.get("description", [])
            if desc_data and isinstance(desc_data, list):
                description = "".join([item.get("plain_text", "") for item in desc_data])
            
            # 解析字段
            properties = raw_data.get("properties", {})
            fields = {}
            title_field = None
            url_field = None
            
            for field_name, field_data in properties.items():
                field_schema = self._parse_field_schema(field_name, field_data)
                fields[field_name] = field_schema
                
                # 记录特殊字段
                if field_schema.type == FieldType.TITLE.value:
                    title_field = field_name
                elif field_schema.type == FieldType.URL.value and not url_field:
                    url_field = field_name
            
            # 构建Schema对象
            schema = DatabaseSchema(
                database_id=database_id,
                title=title,
                description=description,
                fields=fields,
                title_field=title_field,
                url_field=url_field,
                created_at=time.time()
            )
            
            # 缓存结果
            if use_cache:
                self.cache[cache_key] = schema
                print(f"💾 Schema已缓存，TTL: {config.schema_cache_ttl}秒")
            
            print(f"✅ 成功获取Schema，包含 {len(fields)} 个字段")
            return schema
            
        except Exception as e:
            raise NotionSchemaError(f"获取Schema失败: {e}")
    
    def get_field_names_by_type(self, field_type: Union[str, FieldType], 
                               database_id: Optional[str] = None) -> List[str]:
        """获取指定类型的字段名列表"""
        schema = self.get_database_schema(database_id)
        
        if isinstance(field_type, FieldType):
            field_type = field_type.value
        
        return [
            name for name, field in schema.fields.items() 
            if field.type == field_type
        ]
    
    def get_select_options(self, field_name: str, 
                          database_id: Optional[str] = None) -> List[SelectOption]:
        """获取Select/Status字段的选项列表"""
        schema = self.get_database_schema(database_id)
        
        if field_name not in schema.fields:
            raise NotionSchemaError(f"字段 '{field_name}' 不存在")
        
        field = schema.fields[field_name]
        if field.type not in [FieldType.SELECT.value, FieldType.STATUS.value, FieldType.MULTI_SELECT.value]:
            raise NotionSchemaError(f"字段 '{field_name}' 不是选择类型字段")
        
        return field.options or []
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        print("🗑️ 缓存已清空")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return {
            "size": len(self.cache),
            "maxsize": self.cache.maxsize,
            "ttl": self.cache.ttl,
            "keys": list(self.cache.keys())
        }
    
    def print_schema_summary(self, database_id: Optional[str] = None):
        """打印Schema摘要信息（用于调试）"""
        schema = self.get_database_schema(database_id)
        
        print("\n" + "="*60)
        print(f"📊 数据库Schema摘要")
        print("="*60)
        print(f"数据库ID: {schema.database_id}")
        print(f"标题: {schema.title}")
        if schema.description:
            print(f"描述: {schema.description}")
        print(f"Title字段: {schema.title_field}")
        print(f"URL字段: {schema.url_field}")
        print(f"字段数量: {len(schema.fields)}")
        
        print(f"\n📋 字段列表:")
        for name, field in schema.fields.items():
            required_mark = " (必需)" if field.required else ""
            print(f"  • {name} → {field.type}{required_mark}")
            
            # 显示选项
            if field.options:
                print(f"    选项: {[opt.name for opt in field.options]}")
        
        print("\n" + "="*60)


# 全局Schema API实例
schema_api = NotionSchemaAPI()
async_schema_api = AsyncNotionSchemaAPI()


def get_database_schema(database_id: Optional[str] = None, 
                       use_cache: bool = True) -> DatabaseSchema:
    """便捷函数：获取数据库Schema（同步版本）"""
    return schema_api.get_database_schema(database_id, use_cache)


async def get_database_schema_async(database_id: Optional[str] = None, 
                                   use_cache: bool = True) -> DatabaseSchema:
    """便捷函数：异步获取数据库Schema"""
    return await async_schema_api.get_database_schema_async(database_id, use_cache)


def get_field_by_type(field_type: Union[str, FieldType], 
                     database_id: Optional[str] = None) -> List[str]:
    """便捷函数：获取指定类型的字段列表（同步版本）"""
    return schema_api.get_field_names_by_type(field_type, database_id)


async def get_field_by_type_async(field_type: Union[str, FieldType], 
                                 database_id: Optional[str] = None) -> List[str]:
    """便捷函数：异步获取指定类型的字段列表"""
    return await async_schema_api.get_field_names_by_type_async(field_type, database_id)
