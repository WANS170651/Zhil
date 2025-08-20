"""
LLM Schema Builder 模块
将Notion Schema转换为LLM可理解的JSON Schema格式，支持函数调用模式
"""

import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from .notion_schema import DatabaseSchema, FieldSchema, FieldType, SelectOption


class JSONSchemaType(Enum):
    """JSON Schema数据类型"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class JSONSchemaField:
    """JSON Schema字段定义"""
    type: str
    description: Optional[str] = None
    enum: Optional[List[str]] = None
    format: Optional[str] = None
    items: Optional[Dict[str, Any]] = None
    required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {"type": self.type}
        
        if self.description:
            result["description"] = self.description
        if self.enum:
            result["enum"] = self.enum
        if self.format:
            result["format"] = self.format
        if self.items:
            result["items"] = self.items
            
        return result


@dataclass
class FunctionCallSchema:
    """OpenAI函数调用Schema定义"""
    name: str
    description: str
    parameters: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为OpenAI函数调用格式"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class LLMSchemaBuilder:
    """LLM Schema构建器"""
    
    # Notion字段类型到JSON Schema类型的映射
    TYPE_MAPPING = {
        FieldType.TITLE.value: JSONSchemaType.STRING.value,
        FieldType.RICH_TEXT.value: JSONSchemaType.STRING.value,
        FieldType.SELECT.value: JSONSchemaType.STRING.value,
        FieldType.MULTI_SELECT.value: JSONSchemaType.ARRAY.value,
        FieldType.STATUS.value: JSONSchemaType.STRING.value,
        FieldType.URL.value: JSONSchemaType.STRING.value,
        FieldType.EMAIL.value: JSONSchemaType.STRING.value,
        FieldType.PHONE_NUMBER.value: JSONSchemaType.STRING.value,
        FieldType.DATE.value: JSONSchemaType.STRING.value,
        FieldType.NUMBER.value: JSONSchemaType.NUMBER.value,
        FieldType.CHECKBOX.value: JSONSchemaType.BOOLEAN.value,
        FieldType.FILES.value: JSONSchemaType.STRING.value,
        FieldType.PEOPLE.value: JSONSchemaType.STRING.value,
        FieldType.CREATED_BY.value: JSONSchemaType.STRING.value,
        FieldType.CREATED_TIME.value: JSONSchemaType.STRING.value,
        FieldType.LAST_EDITED_BY.value: JSONSchemaType.STRING.value,
        FieldType.LAST_EDITED_TIME.value: JSONSchemaType.STRING.value,
    }
    
    # 格式映射
    FORMAT_MAPPING = {
        FieldType.URL.value: "uri",
        FieldType.EMAIL.value: "email",
        FieldType.DATE.value: "date",
        FieldType.CREATED_TIME.value: "date-time",
        FieldType.LAST_EDITED_TIME.value: "date-time",
    }
    
    def __init__(self):
        pass
    
    def _convert_select_options_to_enum(self, options: List[SelectOption]) -> List[str]:
        """将Select选项转换为枚举列表"""
        return [option.name for option in options if option.name]
    
    def _get_field_description(self, field: FieldSchema) -> str:
        """生成字段描述"""
        base_desc = f"{field.name}字段"
        
        if field.description:
            base_desc += f" - {field.description}"
        
        # 为不同类型添加特定描述
        type_descriptions = {
            FieldType.TITLE.value: "标题字段，必填",
            FieldType.SELECT.value: "单选字段，必须从给定选项中选择",
            FieldType.MULTI_SELECT.value: "多选字段，可选择多个选项",
            FieldType.STATUS.value: "状态字段，必须从给定状态中选择",
            FieldType.URL.value: "URL字段，必须是有效的网址格式",
            FieldType.EMAIL.value: "邮箱字段，必须是有效的邮箱格式",
            FieldType.DATE.value: "日期字段，格式为YYYY-MM-DD",
            FieldType.NUMBER.value: "数字字段",
            FieldType.CHECKBOX.value: "布尔字段，true或false",
            FieldType.RICH_TEXT.value: "富文本字段，支持多行文本",
        }
        
        if field.type in type_descriptions:
            base_desc += f"。{type_descriptions[field.type]}"
        
        # 为Select/Status字段添加选项信息
        if field.options and field.type in [FieldType.SELECT.value, FieldType.STATUS.value, FieldType.MULTI_SELECT.value]:
            options_str = "、".join([opt.name for opt in field.options[:5]])  # 只显示前5个
            if len(field.options) > 5:
                options_str += f"等{len(field.options)}个选项"
            base_desc += f"。可选项包括：{options_str}"
        
        # 特别为Requirements字段添加详细描述
        if field.name.lower() in ["requirements", "requirement", "要求", "任职要求", "招聘要求"]:
            base_desc += "。这是招聘要求/任职要求字段，请提取学历要求、工作经验、技能要求、证书要求等相关信息。如果网页中有'任职要求'、'岗位要求'、'招聘要求'、'技能要求'等章节，请重点关注并整合相关信息。"
        
        return base_desc
    
    def _convert_notion_field_to_json_schema(self, field: FieldSchema) -> JSONSchemaField:
        """将Notion字段转换为JSON Schema字段"""
        # 获取基础类型
        json_type = self.TYPE_MAPPING.get(field.type, JSONSchemaType.STRING.value)
        
        # 创建JSON Schema字段
        json_field = JSONSchemaField(
            type=json_type,
            description=self._get_field_description(field),
            required=field.required
        )
        
        # 处理特殊字段类型
        if field.type in [FieldType.SELECT.value, FieldType.STATUS.value]:
            # Select/Status字段 -> 枚举
            if field.options:
                json_field.enum = self._convert_select_options_to_enum(field.options)
        
        elif field.type == FieldType.MULTI_SELECT.value:
            # Multi-Select字段 -> 字符串数组
            json_field.items = {"type": "string"}
            if field.options:
                enum_options = self._convert_select_options_to_enum(field.options)
                json_field.items["enum"] = enum_options
        
        elif field.type in self.FORMAT_MAPPING:
            # 设置格式约束
            json_field.format = self.FORMAT_MAPPING[field.type]
        
        return json_field
    
    def build_json_schema(self, database_schema: DatabaseSchema, 
                         include_optional: bool = True) -> Dict[str, Any]:
        """
        构建标准JSON Schema
        
        Args:
            database_schema: Notion数据库Schema
            include_optional: 是否包含可选字段
            
        Returns:
            标准JSON Schema格式
        """
        properties = {}
        required_fields = []
        
        for field_name, field in database_schema.fields.items():
            # 跳过系统字段
            if field.type in [FieldType.CREATED_BY.value, FieldType.CREATED_TIME.value, 
                             FieldType.LAST_EDITED_BY.value, FieldType.LAST_EDITED_TIME.value]:
                continue
            
            # 可选择是否包含可选字段
            if not include_optional and not field.required:
                continue
            
            json_field = self._convert_notion_field_to_json_schema(field)
            properties[field_name] = json_field.to_dict()
            
            if field.required:
                required_fields.append(field_name)
        
        schema = {
            "type": "object",
            "properties": properties,
            "required": required_fields,
            "additionalProperties": False,
            "description": f"从网页内容中提取的结构化信息，用于填入Notion数据库 '{database_schema.title}'"
        }
        
        return schema
    
    def build_function_call_schema(self, database_schema: DatabaseSchema,
                                  function_name: str = "extract_job_info",
                                  include_optional: bool = True) -> FunctionCallSchema:
        """
        构建OpenAI函数调用Schema
        
        Args:
            database_schema: Notion数据库Schema
            function_name: 函数名称
            include_optional: 是否包含可选字段
            
        Returns:
            OpenAI函数调用Schema
        """
        json_schema = self.build_json_schema(database_schema, include_optional)
        
        function_description = f"""
从网页内容中提取结构化的招聘信息，用于填入Notion数据库。

数据库: {database_schema.title}
字段数量: {len([f for f in database_schema.fields.values() if f.type not in ['created_by', 'created_time', 'last_edited_by', 'last_edited_time']])}

请严格按照字段定义提取信息：
- 必填字段必须有值
- Select/Status字段必须从给定选项中选择
- 日期字段使用YYYY-MM-DD格式
- 如果信息不完整或不确定，相应字段请留空（空字符串）
""".strip()
        
        return FunctionCallSchema(
            name=function_name,
            description=function_description,
            parameters=json_schema
        )
    
    def build_system_prompt(self, database_schema: DatabaseSchema) -> str:
        """
        构建系统提示词
        
        Args:
            database_schema: Notion数据库Schema
            
        Returns:
            系统提示词
        """
        # 分析字段结构
        required_fields = []
        select_fields = []
        optional_fields = []
        rich_text_fields = []
        
        for field_name, field in database_schema.fields.items():
            # 跳过系统字段
            if field.type in [FieldType.CREATED_BY.value, FieldType.CREATED_TIME.value, 
                             FieldType.LAST_EDITED_BY.value, FieldType.LAST_EDITED_TIME.value]:
                continue
            
            if field.required:
                required_fields.append(field_name)
            else:
                optional_fields.append(field_name)
            
            if field.type in [FieldType.SELECT.value, FieldType.STATUS.value]:
                options = [opt.name for opt in field.options] if field.options else []
                select_fields.append(f"{field_name}: {options}")
            
            if field.type == FieldType.RICH_TEXT.value:
                rich_text_fields.append(field_name)
        
        prompt = f"""你是一个专业的招聘信息提取助手。你的任务是从网页内容中提取结构化的招聘信息，用于填入Notion数据库。

数据库信息：
- 名称: {database_schema.title}
- Title字段: {database_schema.title_field}
- URL字段: {database_schema.url_field}

字段要求：
"""
        
        if required_fields:
            prompt += f"\n必填字段: {', '.join(required_fields)}"
        
        if select_fields:
            prompt += f"\n\n选择字段及选项:"
            for field_info in select_fields:
                prompt += f"\n- {field_info}"
        
        # 特别强调requirement字段
        if "Requirements" in rich_text_fields or "requirement" in [f.lower() for f in rich_text_fields]:
            prompt += f"""

重要字段提取指导：
- Requirements字段：这是招聘要求/任职要求字段，请仔细查找以下内容：
  * 学历要求（本科、硕士、博士等）
  * 工作经验要求（X年以上经验）
  * 技能要求（编程语言、框架、工具等）
  * 证书要求（相关认证）
  * 其他特殊要求
  * 如果网页中有"任职要求"、"岗位要求"、"招聘要求"、"技能要求"等章节，请重点关注
  * 如果信息分散在多个地方，请整合成完整的描述
  * 如果找不到明确的要求信息，可以留空"""
        
        prompt += f"""

提取规则：
1. 严格按照字段定义提取信息
2. 必填字段必须有值，不能为空
3. Select/Status字段必须从给定选项中选择，不能自创
4. 如果找不到确切信息，使用最接近的选项或留空
5. 日期格式统一使用 YYYY-MM-DD
6. URL字段填入原始网页链接
7. 富文本字段可以包含详细描述，支持多行文本
8. 对于Requirements字段，请尽可能完整地提取所有相关要求信息

请仔细分析网页内容，准确提取所需信息。特别注意查找招聘要求、任职要求等相关信息。"""
        
        return prompt
    
    def generate_example_output(self, database_schema: DatabaseSchema) -> Dict[str, Any]:
        """
        生成示例输出（用于测试和文档）
        
        Args:
            database_schema: Notion数据库Schema
            
        Returns:
            示例JSON输出
        """
        example = {}
        
        for field_name, field in database_schema.fields.items():
            # 跳过系统字段
            if field.type in [FieldType.CREATED_BY.value, FieldType.CREATED_TIME.value, 
                             FieldType.LAST_EDITED_BY.value, FieldType.LAST_EDITED_TIME.value]:
                continue
            
            # 根据字段类型生成示例值
            if field.type == FieldType.TITLE.value:
                example[field_name] = "2025-08-19"
            elif field.type == FieldType.RICH_TEXT.value:
                if "company" in field_name.lower():
                    example[field_name] = "示例公司名称"
                elif "position" in field_name.lower():
                    example[field_name] = "高级开发工程师"
                elif "location" in field_name.lower():
                    example[field_name] = "北京·朝阳区"
                elif field_name.lower() in ["requirements", "requirement", "要求", "任职要求", "招聘要求"]:
                    example[field_name] = "本科及以上学历，3年以上相关工作经验，精通Python/Java等编程语言，熟悉Spring/Django等框架，有良好的团队协作能力"
                else:
                    example[field_name] = f"示例{field_name}内容"
            elif field.type in [FieldType.SELECT.value, FieldType.STATUS.value]:
                if field.options:
                    example[field_name] = field.options[0].name
                else:
                    example[field_name] = f"示例{field_name}选项"
            elif field.type == FieldType.MULTI_SELECT.value:
                if field.options:
                    example[field_name] = [field.options[0].name]
                else:
                    example[field_name] = [f"示例{field_name}选项"]
            elif field.type == FieldType.URL.value:
                example[field_name] = "https://example.com/job/123"
            elif field.type == FieldType.EMAIL.value:
                example[field_name] = "hr@example.com"
            elif field.type == FieldType.DATE.value:
                example[field_name] = "2025-08-19"
            elif field.type == FieldType.NUMBER.value:
                example[field_name] = 10000
            elif field.type == FieldType.CHECKBOX.value:
                example[field_name] = True
            else:
                example[field_name] = f"示例{field_name}"
        
        return example


# 全局Schema构建器实例
schema_builder = LLMSchemaBuilder()


def build_function_call_schema(database_schema: DatabaseSchema, 
                              function_name: str = "extract_job_info") -> Dict[str, Any]:
    """便捷函数：构建函数调用Schema"""
    return schema_builder.build_function_call_schema(database_schema, function_name).to_dict()


def build_system_prompt(database_schema: DatabaseSchema) -> str:
    """便捷函数：构建系统提示词"""
    return schema_builder.build_system_prompt(database_schema)
