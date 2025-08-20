"""
Normalizer模块
校验和归一化LLM输出，确保数据符合Notion API要求
"""

import re
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum

from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from .notion_schema import DatabaseSchema, FieldSchema, FieldType, SelectOption


class ValidationResult(Enum):
    """验证结果枚举"""
    VALID = "valid"
    FIXED = "fixed"
    INVALID = "invalid"
    EMPTY = "empty"


@dataclass
class FieldValidationResult:
    """字段验证结果"""
    field_name: str
    original_value: Any
    normalized_value: Any
    result: ValidationResult
    error_message: Optional[str] = None
    warning_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "field_name": self.field_name,
            "original_value": self.original_value,
            "normalized_value": self.normalized_value,
            "result": self.result.value,
            "error_message": self.error_message,
            "warning_message": self.warning_message
        }


@dataclass
class NormalizationResult:
    """归一化结果"""
    success: bool
    notion_payload: Optional[Dict[str, Any]] = None
    field_results: Optional[List[FieldValidationResult]] = None
    error_count: int = 0
    warning_count: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "notion_payload": self.notion_payload,
            "field_results": [fr.to_dict() for fr in self.field_results] if self.field_results else [],
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "error_message": self.error_message
        }


class NormalizerError(Exception):
    """Normalizer相关异常"""
    pass


class DataNormalizer:
    """数据归一化器"""
    
    # 正则表达式模式
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    URL_PATTERN = re.compile(r'^https?://[^\s/$.?#].[^\s]*$')
    PHONE_PATTERN = re.compile(r'^[\d\-\+\(\)\s]+$')
    DATE_PATTERNS = [
        re.compile(r'^\d{4}-\d{2}-\d{2}$'),          # YYYY-MM-DD
        re.compile(r'^\d{4}/\d{2}/\d{2}$'),          # YYYY/MM/DD
        re.compile(r'^\d{4}\.\d{2}\.\d{2}$'),        # YYYY.MM.DD
        re.compile(r'^\d{2}-\d{2}-\d{4}$'),          # DD-MM-YYYY
        re.compile(r'^\d{2}/\d{2}/\d{4}$'),          # DD/MM/YYYY
    ]
    
    def __init__(self, strict_mode: bool = False, fuzzy_threshold: int = 70):
        """
        初始化归一化器
        
        Args:
            strict_mode: 严格模式，不允许模糊匹配
            fuzzy_threshold: 模糊匹配相似度阈值(0-100)
        """
        self.strict_mode = strict_mode
        self.fuzzy_threshold = fuzzy_threshold
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _normalize_date(self, value: Any) -> Tuple[Optional[str], ValidationResult, Optional[str]]:
        """
        归一化日期字段
        
        Returns:
            (normalized_value, result, error_message)
        """
        if not value:
            return None, ValidationResult.EMPTY, None
        
        value_str = str(value).strip()
        if not value_str:
            return None, ValidationResult.EMPTY, None
        
        # 检查是否已经是标准格式
        if self.DATE_PATTERNS[0].match(value_str):
            try:
                # 验证日期有效性
                datetime.strptime(value_str, '%Y-%m-%d')
                return value_str, ValidationResult.VALID, None
            except ValueError:
                return None, ValidationResult.INVALID, f"无效日期: {value_str}"
        
        # 尝试解析其他格式
        formats_to_try = [
            ('%Y/%m/%d', self.DATE_PATTERNS[1]),
            ('%Y.%m.%d', self.DATE_PATTERNS[2]),
            ('%d-%m-%Y', self.DATE_PATTERNS[3]),
            ('%d/%m/%Y', self.DATE_PATTERNS[4]),
        ]
        
        for date_format, pattern in formats_to_try:
            if pattern.match(value_str):
                try:
                    parsed_date = datetime.strptime(value_str, date_format)
                    normalized = parsed_date.strftime('%Y-%m-%d')
                    return normalized, ValidationResult.FIXED, f"日期格式已转换: {value_str} → {normalized}"
                except ValueError:
                    continue
        
        # 尝试解析今天、明天等相对日期
        if value_str.lower() in ['today', '今天']:
            today = date.today().strftime('%Y-%m-%d')
            return today, ValidationResult.FIXED, f"相对日期已转换: {value_str} → {today}"
        
        return None, ValidationResult.INVALID, f"无法解析日期格式: {value_str}"
    
    def _normalize_number(self, value: Any) -> Tuple[Optional[Union[int, float]], ValidationResult, Optional[str]]:
        """归一化数字字段"""
        if value is None or value == "":
            return None, ValidationResult.EMPTY, None
        
        if isinstance(value, (int, float)):
            return value, ValidationResult.VALID, None
        
        value_str = str(value).strip()
        if not value_str:
            return None, ValidationResult.EMPTY, None
        
        # 移除千分位分隔符和货币符号
        cleaned = re.sub(r'[,¥$€£]', '', value_str)
        
        try:
            # 尝试解析为整数
            if '.' not in cleaned:
                return int(cleaned), ValidationResult.VALID if cleaned == value_str else ValidationResult.FIXED, None
            else:
                return float(cleaned), ValidationResult.VALID if cleaned == value_str else ValidationResult.FIXED, None
        except ValueError:
            return None, ValidationResult.INVALID, f"无法解析为数字: {value_str}"
    
    def _normalize_boolean(self, value: Any) -> Tuple[Optional[bool], ValidationResult, Optional[str]]:
        """归一化布尔字段"""
        if value is None or value == "":
            return None, ValidationResult.EMPTY, None
        
        if isinstance(value, bool):
            return value, ValidationResult.VALID, None
        
        value_str = str(value).strip().lower()
        
        true_values = ['true', 'yes', '是', '1', 'on', 'enabled', '启用']
        false_values = ['false', 'no', '否', '0', 'off', 'disabled', '禁用']
        
        if value_str in true_values:
            return True, ValidationResult.VALID if value_str == 'true' else ValidationResult.FIXED, None
        elif value_str in false_values:
            return False, ValidationResult.VALID if value_str == 'false' else ValidationResult.FIXED, None
        else:
            return None, ValidationResult.INVALID, f"无法解析为布尔值: {value}"
    
    def _normalize_url(self, value: Any) -> Tuple[Optional[str], ValidationResult, Optional[str]]:
        """归一化URL字段"""
        if not value:
            return None, ValidationResult.EMPTY, None
        
        value_str = str(value).strip()
        if not value_str:
            return None, ValidationResult.EMPTY, None
        
        # 如果没有协议，尝试添加https://
        if not value_str.startswith(('http://', 'https://')):
            if value_str.startswith('www.') or '.' in value_str:
                fixed_url = f"https://{value_str}"
                if self.URL_PATTERN.match(fixed_url):
                    return fixed_url, ValidationResult.FIXED, f"已添加协议: {value_str} → {fixed_url}"
        
        if self.URL_PATTERN.match(value_str):
            return value_str, ValidationResult.VALID, None
        else:
            return None, ValidationResult.INVALID, f"无效URL格式: {value_str}"
    
    def _normalize_email(self, value: Any) -> Tuple[Optional[str], ValidationResult, Optional[str]]:
        """归一化邮箱字段"""
        if not value:
            return None, ValidationResult.EMPTY, None
        
        value_str = str(value).strip().lower()
        if not value_str:
            return None, ValidationResult.EMPTY, None
        
        if self.EMAIL_PATTERN.match(value_str):
            return value_str, ValidationResult.VALID, None
        else:
            return None, ValidationResult.INVALID, f"无效邮箱格式: {value}"
    
    def _normalize_phone(self, value: Any) -> Tuple[Optional[str], ValidationResult, Optional[str]]:
        """归一化电话号码字段"""
        if not value:
            return None, ValidationResult.EMPTY, None
        
        value_str = str(value).strip()
        if not value_str:
            return None, ValidationResult.EMPTY, None
        
        # 简单的电话号码验证
        if self.PHONE_PATTERN.match(value_str) and len(value_str) >= 7:
            return value_str, ValidationResult.VALID, None
        else:
            return None, ValidationResult.INVALID, f"无效电话号码格式: {value_str}"
    
    def _normalize_text(self, value: Any, max_length: Optional[int] = None) -> Tuple[Optional[str], ValidationResult, Optional[str]]:
        """归一化文本字段"""
        if value is None:
            return None, ValidationResult.EMPTY, None
        
        value_str = str(value).strip()
        if not value_str:
            return None, ValidationResult.EMPTY, None
        
        # 截断过长文本
        if max_length and len(value_str) > max_length:
            truncated = value_str[:max_length] + "..."
            return truncated, ValidationResult.FIXED, f"文本已截断到{max_length}字符"
        
        return value_str, ValidationResult.VALID, None
    
    def _fuzzy_match_option(self, value: str, options: List[SelectOption]) -> Tuple[Optional[str], int]:
        """
        模糊匹配选项
        
        Returns:
            (matched_option, similarity_score)
        """
        if not value or not options:
            return None, 0
        
        option_names = [opt.name for opt in options]
        
        # 精确匹配
        if value in option_names:
            return value, 100
        
        # 模糊匹配
        if not self.strict_mode:
            result = process.extractOne(value, option_names, scorer=fuzz.ratio)
            if result and result[1] >= self.fuzzy_threshold:
                return result[0], result[1]
        
        return None, 0
    
    def _normalize_select(self, value: Any, options: List[SelectOption]) -> Tuple[Optional[str], ValidationResult, Optional[str]]:
        """归一化Select字段"""
        if not value:
            return None, ValidationResult.EMPTY, None
        
        value_str = str(value).strip()
        if not value_str:
            return None, ValidationResult.EMPTY, None
        
        matched_option, similarity = self._fuzzy_match_option(value_str, options)
        
        if matched_option:
            if similarity == 100:
                return matched_option, ValidationResult.VALID, None
            else:
                return matched_option, ValidationResult.FIXED, f"模糊匹配(相似度{similarity}%): {value_str} → {matched_option}"
        else:
            available_options = [opt.name for opt in options[:5]]  # 只显示前5个
            return None, ValidationResult.INVALID, f"选项不匹配: {value_str}，可选: {available_options}"
    
    def _normalize_multi_select(self, value: Any, options: List[SelectOption]) -> Tuple[Optional[List[str]], ValidationResult, Optional[str]]:
        """归一化Multi-Select字段"""
        if not value:
            return None, ValidationResult.EMPTY, None
        
        # 处理不同的输入格式
        if isinstance(value, str):
            # 字符串格式，尝试分割
            items = [item.strip() for item in re.split(r'[,;|]', value) if item.strip()]
        elif isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
        else:
            items = [str(value).strip()]
        
        if not items:
            return None, ValidationResult.EMPTY, None
        
        valid_items = []
        fixed_items = []
        invalid_items = []
        
        for item in items:
            matched_option, similarity = self._fuzzy_match_option(item, options)
            if matched_option:
                if similarity == 100:
                    valid_items.append(matched_option)
                else:
                    valid_items.append(matched_option)
                    fixed_items.append(f"{item}→{matched_option}")
            else:
                invalid_items.append(item)
        
        if valid_items:
            result = ValidationResult.VALID if not fixed_items and not invalid_items else ValidationResult.FIXED
            message = None
            if fixed_items:
                message = f"部分选项已修正: {', '.join(fixed_items)}"
            if invalid_items:
                message = (message + "; " if message else "") + f"无效选项: {', '.join(invalid_items)}"
            
            return valid_items, result, message
        else:
            available_options = [opt.name for opt in options[:5]]
            return None, ValidationResult.INVALID, f"所有选项都无效: {items}，可选: {available_options}"
    
    def _build_notion_property(self, field: FieldSchema, normalized_value: Any) -> Optional[Dict[str, Any]]:
        """构建Notion属性格式"""
        if normalized_value is None:
            return None
        
        field_type = field.type
        
        if field_type == FieldType.TITLE.value:
            return {"title": [{"text": {"content": str(normalized_value)}}]}
        
        elif field_type == FieldType.RICH_TEXT.value:
            return {"rich_text": [{"text": {"content": str(normalized_value)}}]}
        
        elif field_type == FieldType.SELECT.value:
            return {"select": {"name": str(normalized_value)}}
        
        elif field_type == FieldType.MULTI_SELECT.value:
            if isinstance(normalized_value, list):
                return {"multi_select": [{"name": str(item)} for item in normalized_value]}
            else:
                return {"multi_select": [{"name": str(normalized_value)}]}
        
        elif field_type == FieldType.STATUS.value:
            return {"status": {"name": str(normalized_value)}}
        
        elif field_type == FieldType.URL.value:
            return {"url": str(normalized_value)}
        
        elif field_type == FieldType.EMAIL.value:
            return {"email": str(normalized_value)}
        
        elif field_type == FieldType.PHONE_NUMBER.value:
            return {"phone_number": str(normalized_value)}
        
        elif field_type == FieldType.DATE.value:
            return {"date": {"start": str(normalized_value)}}
        
        elif field_type == FieldType.NUMBER.value:
            return {"number": normalized_value}
        
        elif field_type == FieldType.CHECKBOX.value:
            return {"checkbox": bool(normalized_value)}
        
        elif field_type == FieldType.FILES.value:
            # 文件类型较复杂，暂时返回空
            return None
        
        else:
            # 其他类型作为富文本处理
            return {"rich_text": [{"text": {"content": str(normalized_value)}}]}
    
    def normalize(self, raw_data: Dict[str, Any], database_schema: DatabaseSchema) -> NormalizationResult:
        """
        归一化数据
        
        Args:
            raw_data: LLM原始输出数据
            database_schema: 数据库Schema
            
        Returns:
            NormalizationResult: 归一化结果
        """
        try:
            self.logger.info(f"🔧 开始数据归一化，输入字段: {len(raw_data)}")
            
            field_results = []
            notion_properties = {}
            error_count = 0
            warning_count = 0
            
            # 处理每个字段
            for field_name, field_schema in database_schema.fields.items():
                # 跳过系统字段
                if field_schema.type in [FieldType.CREATED_BY.value, FieldType.CREATED_TIME.value,
                                       FieldType.LAST_EDITED_BY.value, FieldType.LAST_EDITED_TIME.value]:
                    continue
                
                raw_value = raw_data.get(field_name)
                
                # 根据字段类型进行归一化
                if field_schema.type == FieldType.DATE.value:
                    normalized_value, result, message = self._normalize_date(raw_value)
                
                elif field_schema.type == FieldType.NUMBER.value:
                    normalized_value, result, message = self._normalize_number(raw_value)
                
                elif field_schema.type == FieldType.CHECKBOX.value:
                    normalized_value, result, message = self._normalize_boolean(raw_value)
                
                elif field_schema.type == FieldType.URL.value:
                    normalized_value, result, message = self._normalize_url(raw_value)
                
                elif field_schema.type == FieldType.EMAIL.value:
                    normalized_value, result, message = self._normalize_email(raw_value)
                
                elif field_schema.type == FieldType.PHONE_NUMBER.value:
                    normalized_value, result, message = self._normalize_phone(raw_value)
                
                elif field_schema.type == FieldType.SELECT.value or field_schema.type == FieldType.STATUS.value:
                    normalized_value, result, message = self._normalize_select(raw_value, field_schema.options or [])
                
                elif field_schema.type == FieldType.MULTI_SELECT.value:
                    normalized_value, result, message = self._normalize_multi_select(raw_value, field_schema.options or [])
                
                else:  # 文本字段
                    max_length = 2000 if field_schema.type == FieldType.RICH_TEXT.value else None
                    normalized_value, result, message = self._normalize_text(raw_value, max_length)
                
                # 记录验证结果
                field_result = FieldValidationResult(
                    field_name=field_name,
                    original_value=raw_value,
                    normalized_value=normalized_value,
                    result=result,
                    error_message=message if result == ValidationResult.INVALID else None,
                    warning_message=message if result == ValidationResult.FIXED else None
                )
                field_results.append(field_result)
                
                # 统计错误和警告
                if result == ValidationResult.INVALID:
                    error_count += 1
                elif result == ValidationResult.FIXED:
                    warning_count += 1
                
                # 构建Notion属性
                if normalized_value is not None:
                    notion_property = self._build_notion_property(field_schema, normalized_value)
                    if notion_property:
                        notion_properties[field_name] = notion_property
            
            # 检查必填字段
            if database_schema.title_field:
                title_field = database_schema.title_field
                if title_field not in notion_properties:
                    error_count += 1
                    field_results.append(FieldValidationResult(
                        field_name=title_field,
                        original_value=raw_data.get(title_field),
                        normalized_value=None,
                        result=ValidationResult.INVALID,
                        error_message=f"必填字段 {title_field} 缺失或无效"
                    ))
            
            # 判断整体结果
            success = error_count == 0 and len(notion_properties) > 0
            
            self.logger.info(f"✅ 归一化完成，成功: {success}, 错误: {error_count}, 警告: {warning_count}")
            
            return NormalizationResult(
                success=success,
                notion_payload=notion_properties if success else None,
                field_results=field_results,
                error_count=error_count,
                warning_count=warning_count,
                error_message=f"归一化失败，{error_count}个错误" if not success else None
            )
            
        except Exception as e:
            self.logger.error(f"❌ 归一化异常: {e}")
            return NormalizationResult(
                success=False,
                error_message=f"归一化异常: {e}"
            )


# 全局Normalizer实例
normalizer = DataNormalizer()


def normalize_data(raw_data: Dict[str, Any], database_schema: DatabaseSchema,
                  strict_mode: bool = False) -> Dict[str, Any]:
    """便捷函数：归一化数据"""
    # 如果需要不同的模式，创建临时实例
    if strict_mode != normalizer.strict_mode:
        temp_normalizer = DataNormalizer(strict_mode=strict_mode)
        result = temp_normalizer.normalize(raw_data, database_schema)
    else:
        result = normalizer.normalize(raw_data, database_schema)
    
    return result.to_dict()
