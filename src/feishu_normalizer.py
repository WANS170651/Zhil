"""
飞书数据规范化模块
将提取的数据转换为飞书多维表格可接受的格式
处理不同字段类型的数据转换和验证
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import re
from fuzzywuzzy import fuzz

from .config import config


@dataclass
class FeishuNormalizationResult:
    """飞书数据规范化结果"""
    success: bool
    feishu_payload: Dict[str, Any]
    error_count: int = 0
    warning_count: int = 0
    errors: List[str] = None
    warnings: List[str] = None
    processed_fields: int = 0
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "feishu_payload": self.feishu_payload,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "processed_fields": self.processed_fields
        }


class FeishuFieldMapper:
    """飞书字段映射器，将通用字段映射到飞书字段名称"""
    
    def __init__(self):
        # 预定义的字段映射关系
        # 左侧是通用字段名，右侧是飞书多维表格中的字段名
        self.field_mapping = {
            # 基础信息字段
            "company": "公司名称",
            "position": "职位名称", 
            "title": "标题",
            "url": "链接",
            "description": "描述",
            "content": "内容",
            
            # 职位相关字段
            "job_title": "职位名称",
            "company_name": "公司名称",
            "location": "工作地点",
            "salary": "薪资",
            "experience": "工作经验",
            "education": "学历要求",
            "department": "部门",
            "job_type": "工作性质",
            "industry": "行业",
            
            # 时间字段
            "publish_date": "发布时间",
            "deadline": "截止时间",
            "created_at": "创建时间",
            "updated_at": "更新时间",
            
            # 联系信息
            "contact": "联系方式",
            "email": "邮箱",
            "phone": "电话",
            "address": "地址",
            
            # 其他通用字段
            "status": "状态",
            "priority": "优先级",
            "category": "分类",
            "tags": "标签",
            "notes": "备注",
            "source": "来源"
        }
    
    def map_field_name(self, field_name: str, fuzzy_threshold: int = 80) -> Optional[str]:
        """
        映射字段名称
        
        Args:
            field_name: 原字段名
            fuzzy_threshold: 模糊匹配阈值
            
        Returns:
            映射后的飞书字段名，如果没有找到则返回None
        """
        # 直接匹配
        field_lower = field_name.lower()
        if field_lower in self.field_mapping:
            return self.field_mapping[field_lower]
        
        # 模糊匹配
        best_match = None
        best_score = 0
        
        for key, value in self.field_mapping.items():
            score = fuzz.ratio(field_lower, key.lower())
            if score > best_score and score >= fuzzy_threshold:
                best_score = score
                best_match = value
        
        return best_match
    
    def get_unmapped_field_name(self, field_name: str) -> str:
        """
        获取未映射字段的标准化名称
        
        Args:
            field_name: 原字段名
            
        Returns:
            标准化后的字段名
        """
        # 移除特殊字符，保留中英文、数字和下划线
        cleaned_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', field_name)
        
        # 移除多余的下划线
        cleaned_name = re.sub(r'_+', '_', cleaned_name).strip('_')
        
        # 如果为空，使用默认名称
        if not cleaned_name:
            return "未知字段"
        
        return cleaned_name


class FeishuDataNormalizer:
    """飞书数据规范化器"""
    
    def __init__(self):
        """初始化飞书数据规范化器"""
        self.field_mapper = FeishuFieldMapper()
        
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
    
    def _convert_to_text_field(self, value: Any) -> str:
        """转换为文本字段"""
        if value is None:
            return ""
        
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False, indent=2)
        
        return str(value).strip()
    
    def _convert_to_number_field(self, value: Any) -> Optional[float]:
        """转换为数字字段"""
        if value is None:
            return None
        
        # 如果已经是数字
        if isinstance(value, (int, float)):
            return float(value)
        
        # 尝试从字符串解析数字
        if isinstance(value, str):
            # 移除常见的非数字字符
            cleaned_value = re.sub(r'[^\d.-]', '', value.strip())
            
            if cleaned_value:
                try:
                    return float(cleaned_value)
                except ValueError:
                    pass
        
        return None
    
    def _convert_to_date_field(self, value: Any) -> Optional[int]:
        """
        转换为日期字段（飞书使用时间戳）
        
        Args:
            value: 输入值
            
        Returns:
            时间戳（毫秒），如果转换失败返回None
        """
        if value is None:
            return None
        
        # 如果已经是时间戳
        if isinstance(value, (int, float)):
            # 判断是秒还是毫秒
            if value > 1e10:  # 毫秒时间戳
                return int(value)
            else:  # 秒时间戳
                return int(value * 1000)
        
        # 尝试解析字符串日期
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            
            # 常见日期格式
            date_patterns = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%Y年%m月%d日",
                "%m月%d日",
            ]
            
            for pattern in date_patterns:
                try:
                    dt = datetime.strptime(value, pattern)
                    return int(dt.timestamp() * 1000)
                except ValueError:
                    continue
        
        return None
    
    def _convert_to_checkbox_field(self, value: Any) -> bool:
        """转换为复选框字段"""
        if value is None:
            return False
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            return value_lower in ['true', 'yes', '是', '1', 'on', 'checked', '✓']
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        return False
    
    def _convert_to_url_field(self, value: Any) -> Optional[Dict[str, str]]:
        """
        转换为URL字段（飞书超链接格式）
        
        Args:
            value: 输入值
            
        Returns:
            飞书超链接格式 {"text": "显示文本", "link": "URL"}
        """
        if value is None:
            return None
        
        if isinstance(value, dict) and "link" in value:
            # 已经是飞书格式
            return value
        
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            
            # 检查是否是有效URL
            url_pattern = r'https?://[^\s]+'
            if re.match(url_pattern, value):
                return {
                    "text": value,
                    "link": value
                }
        
        return None
    
    def _convert_to_select_field(self, value: Any) -> Optional[str]:
        """转换为单选字段"""
        if value is None:
            return None
        
        if isinstance(value, str):
            return value.strip()
        
        # 如果是列表，取第一个
        if isinstance(value, list) and value:
            return str(value[0]).strip()
        
        return str(value).strip()
    
    def _convert_to_multi_select_field(self, value: Any) -> List[str]:
        """转换为多选字段"""
        if value is None:
            return []
        
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            
            # 尝试分割字符串
            separators = [',', ';', '|', '\n', '、']
            for sep in separators:
                if sep in value:
                    return [item.strip() for item in value.split(sep) if item.strip()]
            
            # 如果没有分隔符，返回单个值
            return [value]
        
        return [str(value).strip()]
    
    def _infer_field_type(self, field_name: str, value: Any) -> str:
        """
        推断字段类型
        
        Args:
            field_name: 字段名
            value: 字段值
            
        Returns:
            推断的字段类型
        """
        if value is None:
            return "text"
        
        field_lower = field_name.lower()
        
        # 基于字段名推断
        if any(keyword in field_lower for keyword in ['url', 'link', '链接']):
            return "url"
        
        if any(keyword in field_lower for keyword in ['date', 'time', '时间', '日期']):
            return "date"
        
        if any(keyword in field_lower for keyword in ['salary', 'price', 'amount', '薪资', '价格', '金额']):
            return "number"
        
        if any(keyword in field_lower for keyword in ['status', 'type', '状态', '类型']):
            return "select"
        
        if any(keyword in field_lower for keyword in ['tags', 'skills', '标签', '技能']):
            return "multi_select"
        
        if any(keyword in field_lower for keyword in ['checkbox', 'bool', 'flag', '复选', '标志']):
            return "checkbox"
        
        # 基于值类型推断
        if isinstance(value, bool):
            return "checkbox"
        
        if isinstance(value, (int, float)):
            return "number"
        
        if isinstance(value, list):
            return "multi_select"
        
        if isinstance(value, str):
            # 检查是否是URL
            if re.match(r'https?://', value):
                return "url"
            
            # 检查是否是日期
            if re.match(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}', value):
                return "date"
        
        # 默认为文本
        return "text"
    
    def _convert_field_value(self, field_name: str, value: Any, field_type: str = None) -> Any:
        """
        转换字段值
        
        Args:
            field_name: 字段名
            value: 字段值
            field_type: 指定的字段类型，如果为None则自动推断
            
        Returns:
            转换后的字段值
        """
        if field_type is None:
            field_type = self._infer_field_type(field_name, value)
        
        try:
            if field_type == "text":
                return self._convert_to_text_field(value)
            elif field_type == "number":
                return self._convert_to_number_field(value)
            elif field_type == "date":
                return self._convert_to_date_field(value)
            elif field_type == "checkbox":
                return self._convert_to_checkbox_field(value)
            elif field_type == "url":
                return self._convert_to_url_field(value)
            elif field_type == "select":
                return self._convert_to_select_field(value)
            elif field_type == "multi_select":
                return self._convert_to_multi_select_field(value)
            else:
                # 默认转为文本
                return self._convert_to_text_field(value)
                
        except Exception as e:
            self.logger.warning(f"⚠️ 字段 {field_name} 值转换失败: {e}，使用文本格式")
            return self._convert_to_text_field(value)
    
    def normalize(self, raw_data: Dict[str, Any], 
                 field_type_mapping: Optional[Dict[str, str]] = None) -> FeishuNormalizationResult:
        """
        规范化数据为飞书多维表格格式
        
        Args:
            raw_data: 原始数据字典
            field_type_mapping: 字段类型映射，格式为 {field_name: field_type}
            
        Returns:
            FeishuNormalizationResult: 规范化结果
        """
        if field_type_mapping is None:
            field_type_mapping = {}
        
        result = FeishuNormalizationResult(
            success=False,
            feishu_payload={}
        )
        
        if not raw_data:
            result.errors.append("输入数据为空")
            return result
        
        self.logger.info(f"🔧 开始规范化数据为飞书格式，包含 {len(raw_data)} 个字段")
        
        converted_fields = {}
        
        for field_name, field_value in raw_data.items():
            try:
                # 跳过空字段名
                if not field_name or not isinstance(field_name, str):
                    result.warnings.append(f"跳过无效字段名: {field_name}")
                    result.warning_count += 1
                    continue
                
                # 映射字段名
                mapped_field_name = self.field_mapper.map_field_name(field_name)
                if mapped_field_name is None:
                    # 使用清理后的原字段名
                    mapped_field_name = self.field_mapper.get_unmapped_field_name(field_name)
                    result.warnings.append(f"字段 '{field_name}' 未找到映射，使用名称: {mapped_field_name}")
                    result.warning_count += 1
                
                # 获取字段类型
                field_type = field_type_mapping.get(field_name) or field_type_mapping.get(mapped_field_name)
                
                # 转换字段值
                converted_value = self._convert_field_value(mapped_field_name, field_value, field_type)
                
                # 跳过None值（除了复选框）
                if converted_value is None and field_type != "checkbox":
                    result.warnings.append(f"字段 '{mapped_field_name}' 转换结果为空，跳过")
                    result.warning_count += 1
                    continue
                
                converted_fields[mapped_field_name] = converted_value
                result.processed_fields += 1
                
                self.logger.debug(f"  ✓ {field_name} -> {mapped_field_name}: {type(converted_value).__name__}")
                
            except Exception as e:
                error_msg = f"处理字段 '{field_name}' 时出错: {e}"
                result.errors.append(error_msg)
                result.error_count += 1
                self.logger.error(f"❌ {error_msg}")
        
        # 构建飞书payload
        result.feishu_payload = {
            "fields": converted_fields
        }
        
        # 判断成功条件
        result.success = result.processed_fields > 0 and result.error_count == 0
        
        # 记录统计信息
        if result.success:
            self.logger.info(f"✅ 数据规范化成功，处理了 {result.processed_fields} 个字段")
        else:
            self.logger.warning(f"⚠️ 数据规范化完成但有问题，处理了 {result.processed_fields} 个字段，{result.error_count} 个错误")
        
        if result.warning_count > 0:
            self.logger.info(f"💡 规范化过程中有 {result.warning_count} 个警告")
        
        return result


# 全局规范化器实例
feishu_normalizer = FeishuDataNormalizer()


def normalize_for_feishu(raw_data: Dict[str, Any], 
                        field_type_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    便捷函数：规范化数据为飞书格式
    
    Args:
        raw_data: 原始数据
        field_type_mapping: 字段类型映射
        
    Returns:
        规范化结果字典
    """
    result = feishu_normalizer.normalize(raw_data, field_type_mapping)
    return result.to_dict()

