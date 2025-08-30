"""
飞书字段Schema构建器
根据飞书表格的实际字段动态构建LLM提示词和规范化Schema
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio


@dataclass
class FeishuFieldInfo:
    """飞书字段信息"""
    field_name: str
    field_id: str
    data_type: str
    type_code: int
    description: str = ""


class FeishuSchemaBuilder:
    """飞书Schema构建器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._cached_schema: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl = 1800  # 30分钟缓存
    
    async def get_feishu_schema(self) -> Optional[Dict[str, Any]]:
        """
        获取飞书字段Schema
        
        Returns:
            Dict: 包含字段信息的Schema，失败返回None
        """
        try:
            # 检查缓存
            import time
            if (self._cached_schema and self._cache_timestamp and 
                time.time() - self._cache_timestamp < self._cache_ttl):
                self.logger.info("🔄 使用缓存的飞书Schema")
                return self._cached_schema
            
            # 动态导入飞书写入器
            from .feishu_writer import async_feishu_writer
            
            if async_feishu_writer is None:
                self.logger.warning("⚠️ 飞书写入器未初始化，无法获取字段Schema")
                return None
            
            # 获取字段信息
            self.logger.info("📋 获取飞书字段Schema...")
            fields_result = await async_feishu_writer.get_table_fields_async(use_user_token=False)
            
            if not fields_result.get("success"):
                self.logger.error(f"❌ 获取飞书字段失败: {fields_result.get('error', '未知错误')}")
                return None
            
            fields = fields_result.get("fields", {})
            if not fields:
                self.logger.error("❌ 获取到的飞书字段为空")
                return None
            
            # 构建Schema
            schema = self._build_schema_from_fields(fields)
            
            # 缓存结果
            self._cached_schema = schema
            self._cache_timestamp = time.time()
            
            self.logger.info(f"✅ 成功构建飞书Schema，包含 {len(fields)} 个字段")
            return schema
            
        except Exception as e:
            self.logger.error(f"❌ 获取飞书Schema异常: {e}")
            return None
    
    def _build_schema_from_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据飞书字段构建Schema
        
        Args:
            fields: 飞书字段信息字典
            
        Returns:
            Dict: 构建的Schema
        """
        # 创建字段列表
        field_list = []
        function_properties = {}
        
        for field_name, field_info in fields.items():
            data_type = field_info.get("data_type", "text")
            field_id = field_info.get("field_id", "")
            
            # 构建字段描述
            description = self._get_field_description(field_name, data_type)
            
            # 创建字段对象
            field_obj = FeishuFieldInfo(
                field_name=field_name,
                field_id=field_id,
                data_type=data_type,
                type_code=field_info.get("type", 1),
                description=description
            )
            field_list.append(field_obj)
            
            # 构建Function Call的属性定义
            property_def = self._build_function_property(field_name, data_type, description)
            function_properties[field_name] = property_def
        
        return {
            "fields": field_list,
            "field_count": len(field_list),
            "function_properties": function_properties,
            "field_mapping": {f.field_name: f.field_id for f in field_list}
        }
    
    def _get_field_description(self, field_name: str, data_type: str) -> str:
        """
        根据字段名称和类型生成描述
        
        Args:
            field_name: 字段名称
            data_type: 数据类型
            
        Returns:
            str: 字段描述
        """
        # 基于字段名称的描述映射
        name_descriptions = {
            "公司名称": "招聘公司的名称",
            "职位": "招聘职位的名称",
            "地点": "工作地点或办公地址",
            "日期": "招聘或投递的相关日期",
            "行业分类": "公司所属的行业类别",
            "相关要求": "职位的技能要求或工作经验要求",
            "投递入口": "投递简历的网址链接",
            "状态": "招聘或投递的当前状态",
            "备注": "其他相关备注信息"
        }
        
        # 基于数据类型的描述
        type_descriptions = {
            "text": "文本内容",
            "url": "网址链接",
            "date": "日期（YYYY-MM-DD格式）",
            "single_select": "单选值",
            "multi_select": "多选值列表",
            "number": "数字",
            "checkbox": "布尔值（真/假）"
        }
        
        # 组合描述
        base_desc = name_descriptions.get(field_name, f"{field_name}字段")
        type_desc = type_descriptions.get(data_type, "")
        
        if type_desc:
            return f"{base_desc}，{type_desc}"
        return base_desc
    
    def _build_function_property(self, field_name: str, data_type: str, description: str) -> Dict[str, Any]:
        """
        构建Function Call的属性定义
        
        Args:
            field_name: 字段名称
            data_type: 数据类型
            description: 字段描述
            
        Returns:
            Dict: 属性定义
        """
        # 基础属性
        property_def = {
            "description": description
        }
        
        # 根据数据类型设置JSON Schema类型
        if data_type in ["text", "url"]:
            property_def["type"] = "string"
        elif data_type == "number":
            property_def["type"] = "number"
        elif data_type == "checkbox":
            property_def["type"] = "boolean"
        elif data_type == "date":
            property_def["type"] = "string"
            property_def["pattern"] = r"^\d{4}-\d{2}-\d{2}$"
        elif data_type in ["single_select", "multi_select"]:
            property_def["type"] = "string"
        else:
            property_def["type"] = "string"
        
        return property_def
    
    def build_llm_function_schema(self, fields: List[FeishuFieldInfo]) -> Dict[str, Any]:
        """
        构建LLM Function Call的完整Schema
        
        Args:
            fields: 飞书字段列表
            
        Returns:
            Dict: Function Call Schema
        """
        properties = {}
        required_fields = []
        
        for field in fields:
            # 构建属性定义
            prop = self._build_function_property(field.field_name, field.data_type, field.description)
            properties[field.field_name] = prop
            
            # 核心字段设为必需
            if field.field_name in ["公司名称", "职位", "投递入口"]:
                required_fields.append(field.field_name)
        
        return {
            "name": "extract_job_info_for_feishu",
            "description": "从招聘页面提取信息并格式化为飞书多维表格格式",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required_fields
            }
        }


# 全局实例
feishu_schema_builder = FeishuSchemaBuilder()


async def get_feishu_schema() -> Optional[Dict[str, Any]]:
    """便捷函数：获取飞书Schema"""
    return await feishu_schema_builder.get_feishu_schema()


def build_feishu_llm_function(fields: List[FeishuFieldInfo]) -> Dict[str, Any]:
    """便捷函数：构建飞书LLM Function Schema"""
    return feishu_schema_builder.build_llm_function_schema(fields)

