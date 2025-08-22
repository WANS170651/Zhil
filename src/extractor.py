"""
Extractor模块
基于动态Schema调用LLM进行内容抽取，返回结构化JSON
支持同步和异步两种模式
"""

import json
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from openai import OpenAI, AsyncOpenAI
from openai.types.chat import ChatCompletion
import httpx

from .config import config
from .notion_schema import DatabaseSchema, get_database_schema, get_database_schema_async
from .llm_schema_builder import build_function_call_schema, build_system_prompt


class ExtractionMode(Enum):
    """抽取模式枚举"""
    FUNCTION_CALL = "function_call"    # 函数调用模式（推荐）
    JSON_RESPONSE = "json_response"    # JSON响应模式
    TEXT_RESPONSE = "text_response"    # 文本响应模式


@dataclass
class ExtractionResult:
    """抽取结果数据结构"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    raw_response: Optional[str] = None
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None
    mode: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "data": self.data,
            "raw_response": self.raw_response,
            "error": self.error,
            "tokens_used": self.tokens_used,
            "processing_time": self.processing_time,
            "mode": self.mode
        }


class ExtractorError(Exception):
    """Extractor相关异常"""
    pass


class LLMExtractor:
    """LLM内容抽取器（同步版本）"""
    
    def __init__(self):
        """初始化LLM客户端"""
        self.client = OpenAI(
            api_key=config.dashscope_api_key,
            base_url=config.llm_base_url
        )
        self.model = config.llm_model
        
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


class AsyncLLMExtractor:
    """异步LLM内容抽取器"""
    
    def __init__(self):
        """初始化异步LLM客户端"""
        self.client = AsyncOpenAI(
            api_key=config.dashscope_api_key,
            base_url=config.llm_base_url,
            http_client=httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=5)
            )
        )
        self.model = config.llm_model
        
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
    
    def _build_messages(self, content: str, url: str, 
                       database_schema: DatabaseSchema) -> List[Dict[str, str]]:
        """构建消息列表"""
        system_prompt = build_system_prompt(database_schema)
        
        user_content = f"""
请从以下网页内容中提取招聘信息：

原始URL: {url}

网页内容:
{content}

请严格按照字段定义提取信息，如果某些信息无法确定，请留空。
""".strip()
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    
    async def _extract_with_function_call_async(self, content: str, url: str,
                                              database_schema: DatabaseSchema) -> ExtractionResult:
        """使用异步函数调用模式进行抽取"""
        start_time = time.time()
        
        try:
            # 构建函数Schema
            function_schema = build_function_call_schema(database_schema)
            messages = self._build_messages(content, url, database_schema)
            
            self.logger.info(f"🚀 开始异步函数调用模式抽取，URL: {url[:50]}...")
            
            # 异步调用LLM
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=[function_schema],
                function_call={"name": "extract_job_info"},
                temperature=0.1,
                max_tokens=2000
            )
            
            processing_time = time.time() - start_time
            
            # 解析响应
            choice = response.choices[0]
            if choice.message.function_call:
                function_call = choice.message.function_call
                if function_call.name == "extract_job_info":
                    try:
                        extracted_data = json.loads(function_call.arguments)
                        
                        # 确保URL字段正确设置
                        if database_schema.url_field and database_schema.url_field in extracted_data:
                            extracted_data[database_schema.url_field] = url
                        
                        self.logger.info(f"✅ 异步函数调用抽取成功，耗时: {processing_time:.2f}s")
                        
                        return ExtractionResult(
                            success=True,
                            data=extracted_data,
                            raw_response=function_call.arguments,
                            tokens_used=response.usage.total_tokens if response.usage else None,
                            processing_time=processing_time,
                            mode=ExtractionMode.FUNCTION_CALL.value
                        )
                    except json.JSONDecodeError as e:
                        self.logger.error(f"❌ 异步函数调用结果JSON解析失败: {e}")
                        return ExtractionResult(
                            success=False,
                            error=f"JSON解析失败: {e}",
                            raw_response=function_call.arguments,
                            processing_time=processing_time,
                            mode=ExtractionMode.FUNCTION_CALL.value
                        )
            
            # 如果没有函数调用结果
            self.logger.error("❌ 没有收到异步函数调用结果")
            return ExtractionResult(
                success=False,
                error="没有收到函数调用结果",
                raw_response=choice.message.content,
                processing_time=processing_time,
                mode=ExtractionMode.FUNCTION_CALL.value
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"❌ 异步函数调用模式抽取失败: {e}")
            return ExtractionResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                mode=ExtractionMode.FUNCTION_CALL.value
            )
    
    async def _extract_with_json_response_async(self, content: str, url: str,
                                              database_schema: DatabaseSchema) -> ExtractionResult:
        """使用异步JSON响应模式进行抽取"""
        start_time = time.time()
        
        try:
            messages = self._build_messages(content, url, database_schema)
            
            # 添加JSON格式要求到系统提示
            messages[0]["content"] += "\n\n请以JSON格式返回抽取结果，不要包含任何其他内容。"
            
            self.logger.info(f"🔄 开始异步JSON响应模式抽取，URL: {url[:50]}...")
            
            # 异步调用LLM
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2000
            )
            
            processing_time = time.time() - start_time
            
            # 解析响应
            content_text = response.choices[0].message.content
            if content_text:
                try:
                    extracted_data = json.loads(content_text)
                    
                    # 确保URL字段正确设置
                    if database_schema.url_field and database_schema.url_field in extracted_data:
                        extracted_data[database_schema.url_field] = url
                    
                    self.logger.info(f"✅ 异步JSON响应抽取成功，耗时: {processing_time:.2f}s")
                    
                    return ExtractionResult(
                        success=True,
                        data=extracted_data,
                        raw_response=content_text,
                        tokens_used=response.usage.total_tokens if response.usage else None,
                        processing_time=processing_time,
                        mode=ExtractionMode.JSON_RESPONSE.value
                    )
                except json.JSONDecodeError as e:
                    self.logger.error(f"❌ 异步JSON响应解析失败: {e}")
                    return ExtractionResult(
                        success=False,
                        error=f"JSON解析失败: {e}",
                        raw_response=content_text,
                        processing_time=processing_time,
                        mode=ExtractionMode.JSON_RESPONSE.value
                    )
            
            self.logger.error("❌ 没有收到异步响应内容")
            return ExtractionResult(
                success=False,
                error="没有收到响应内容",
                processing_time=processing_time,
                mode=ExtractionMode.JSON_RESPONSE.value
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"❌ 异步JSON响应模式抽取失败: {e}")
            return ExtractionResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                mode=ExtractionMode.JSON_RESPONSE.value
            )
    
    async def extract_async(self, content: str, url: str, 
                           database_id: Optional[str] = None,
                           mode: ExtractionMode = ExtractionMode.FUNCTION_CALL,
                           max_retries: Optional[int] = None) -> ExtractionResult:
        """
        异步从内容中抽取结构化信息
        
        Args:
            content: 网页内容（Markdown或纯文本）
            url: 原始URL
            database_id: 数据库ID，默认使用配置中的ID
            mode: 抽取模式
            max_retries: 最大重试次数，默认使用配置值
            
        Returns:
            ExtractionResult: 抽取结果
        """
        if max_retries is None:
            max_retries = config.max_retries
        
        # 获取数据库Schema（异步版本）
        try:
            database_schema = await get_database_schema_async(database_id)
        except Exception as e:
            return ExtractionResult(
                success=False,
                error=f"获取数据库Schema失败: {e}",
                mode=mode.value
            )
        
        # 执行异步抽取（带重试）
        last_error = None
        for attempt in range(max_retries + 1):
            if attempt > 0:
                self.logger.info(f"🔄 第 {attempt} 次异步重试...")
                await asyncio.sleep(config.retry_delay * attempt)
            
            try:
                if mode == ExtractionMode.FUNCTION_CALL:
                    result = await self._extract_with_function_call_async(content, url, database_schema)
                elif mode == ExtractionMode.JSON_RESPONSE:
                    result = await self._extract_with_json_response_async(content, url, database_schema)
                else:
                    return ExtractionResult(
                        success=False,
                        error=f"不支持的抽取模式: {mode}",
                        mode=mode.value
                    )
                
                if result.success:
                    return result
                else:
                    last_error = result.error
                    
            except Exception as e:
                last_error = str(e)
                self.logger.error(f"❌ 第 {attempt + 1} 次异步抽取失败: {e}")
        
        # 所有重试都失败
        self.logger.error(f"❌ 异步抽取失败，已重试 {max_retries} 次")
        return ExtractionResult(
            success=False,
            error=f"异步抽取失败（重试{max_retries}次）: {last_error}",
            mode=mode.value
        )
    
    async def test_connection_async(self) -> bool:
        """测试异步LLM连接"""
        try:
            self.logger.info("🔗 测试异步LLM连接...")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Hello, are you working?"}
                ],
                max_tokens=50
            )
            
            if response.choices and response.choices[0].message.content:
                self.logger.info("✅ 异步LLM连接正常")
                return True
            else:
                self.logger.error("❌ 异步LLM连接异常：没有响应内容")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 异步LLM连接失败: {e}")
            return False


# 继续原有的_build_messages方法，但现在在同步类中
    def _build_messages(self, content: str, url: str, 
                       database_schema: DatabaseSchema) -> List[Dict[str, str]]:
        """构建消息列表"""
        system_prompt = build_system_prompt(database_schema)
        
        user_content = f"""
请从以下网页内容中提取招聘信息：

原始URL: {url}

网页内容:
{content}

请严格按照字段定义提取信息，如果某些信息无法确定，请留空。
""".strip()
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
    
    def _extract_with_function_call(self, content: str, url: str,
                                   database_schema: DatabaseSchema) -> ExtractionResult:
        """使用函数调用模式进行抽取"""
        start_time = time.time()
        
        try:
            # 构建函数Schema
            function_schema = build_function_call_schema(database_schema)
            messages = self._build_messages(content, url, database_schema)
            
            self.logger.info(f"🚀 开始函数调用模式抽取，URL: {url[:50]}...")
            
            # 调用LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                functions=[function_schema],
                function_call={"name": "extract_job_info"},
                temperature=0.1,  # 降低随机性
                max_tokens=2000
            )
            
            processing_time = time.time() - start_time
            
            # 解析响应
            choice = response.choices[0]
            if choice.message.function_call:
                function_call = choice.message.function_call
                if function_call.name == "extract_job_info":
                    try:
                        extracted_data = json.loads(function_call.arguments)
                        
                        # 确保URL字段正确设置
                        if database_schema.url_field and database_schema.url_field in extracted_data:
                            extracted_data[database_schema.url_field] = url
                        
                        self.logger.info(f"✅ 函数调用抽取成功，耗时: {processing_time:.2f}s")
                        
                        return ExtractionResult(
                            success=True,
                            data=extracted_data,
                            raw_response=function_call.arguments,
                            tokens_used=response.usage.total_tokens if response.usage else None,
                            processing_time=processing_time,
                            mode=ExtractionMode.FUNCTION_CALL.value
                        )
                    except json.JSONDecodeError as e:
                        self.logger.error(f"❌ 函数调用结果JSON解析失败: {e}")
                        return ExtractionResult(
                            success=False,
                            error=f"JSON解析失败: {e}",
                            raw_response=function_call.arguments,
                            processing_time=processing_time,
                            mode=ExtractionMode.FUNCTION_CALL.value
                        )
            
            # 如果没有函数调用结果
            self.logger.error("❌ 没有收到函数调用结果")
            return ExtractionResult(
                success=False,
                error="没有收到函数调用结果",
                raw_response=choice.message.content,
                processing_time=processing_time,
                mode=ExtractionMode.FUNCTION_CALL.value
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"❌ 函数调用模式抽取失败: {e}")
            return ExtractionResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                mode=ExtractionMode.FUNCTION_CALL.value
            )
    
    def _extract_with_json_response(self, content: str, url: str,
                                   database_schema: DatabaseSchema) -> ExtractionResult:
        """使用JSON响应模式进行抽取"""
        start_time = time.time()
        
        try:
            messages = self._build_messages(content, url, database_schema)
            
            # 添加JSON格式要求到系统提示
            messages[0]["content"] += "\n\n请以JSON格式返回抽取结果，不要包含任何其他内容。"
            
            self.logger.info(f"🔄 开始JSON响应模式抽取，URL: {url[:50]}...")
            
            # 调用LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=2000
            )
            
            processing_time = time.time() - start_time
            
            # 解析响应
            content_text = response.choices[0].message.content
            if content_text:
                try:
                    extracted_data = json.loads(content_text)
                    
                    # 确保URL字段正确设置
                    if database_schema.url_field and database_schema.url_field in extracted_data:
                        extracted_data[database_schema.url_field] = url
                    
                    self.logger.info(f"✅ JSON响应抽取成功，耗时: {processing_time:.2f}s")
                    
                    return ExtractionResult(
                        success=True,
                        data=extracted_data,
                        raw_response=content_text,
                        tokens_used=response.usage.total_tokens if response.usage else None,
                        processing_time=processing_time,
                        mode=ExtractionMode.JSON_RESPONSE.value
                    )
                except json.JSONDecodeError as e:
                    self.logger.error(f"❌ JSON响应解析失败: {e}")
                    return ExtractionResult(
                        success=False,
                        error=f"JSON解析失败: {e}",
                        raw_response=content_text,
                        processing_time=processing_time,
                        mode=ExtractionMode.JSON_RESPONSE.value
                    )
            
            self.logger.error("❌ 没有收到响应内容")
            return ExtractionResult(
                success=False,
                error="没有收到响应内容",
                processing_time=processing_time,
                mode=ExtractionMode.JSON_RESPONSE.value
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"❌ JSON响应模式抽取失败: {e}")
            return ExtractionResult(
                success=False,
                error=str(e),
                processing_time=processing_time,
                mode=ExtractionMode.JSON_RESPONSE.value
            )
    
    def extract(self, content: str, url: str, 
                database_id: Optional[str] = None,
                mode: ExtractionMode = ExtractionMode.FUNCTION_CALL,
                max_retries: Optional[int] = None) -> ExtractionResult:
        """
        从内容中抽取结构化信息
        
        Args:
            content: 网页内容（Markdown或纯文本）
            url: 原始URL
            database_id: 数据库ID，默认使用配置中的ID
            mode: 抽取模式
            max_retries: 最大重试次数，默认使用配置值
            
        Returns:
            ExtractionResult: 抽取结果
        """
        if max_retries is None:
            max_retries = config.max_retries
        
        # 获取数据库Schema
        try:
            database_schema = get_database_schema(database_id)
        except Exception as e:
            return ExtractionResult(
                success=False,
                error=f"获取数据库Schema失败: {e}",
                mode=mode.value
            )
        
        # 执行抽取（带重试）
        last_error = None
        for attempt in range(max_retries + 1):
            if attempt > 0:
                self.logger.info(f"🔄 第 {attempt} 次重试...")
                time.sleep(config.retry_delay * attempt)  # 指数退避
            
            try:
                if mode == ExtractionMode.FUNCTION_CALL:
                    result = self._extract_with_function_call(content, url, database_schema)
                elif mode == ExtractionMode.JSON_RESPONSE:
                    result = self._extract_with_json_response(content, url, database_schema)
                else:
                    return ExtractionResult(
                        success=False,
                        error=f"不支持的抽取模式: {mode}",
                        mode=mode.value
                    )
                
                if result.success:
                    return result
                else:
                    last_error = result.error
                    
            except Exception as e:
                last_error = str(e)
                self.logger.error(f"❌ 第 {attempt + 1} 次抽取失败: {e}")
        
        # 所有重试都失败
        self.logger.error(f"❌ 抽取失败，已重试 {max_retries} 次")
        return ExtractionResult(
            success=False,
            error=f"抽取失败（重试{max_retries}次）: {last_error}",
            mode=mode.value
        )
    
    def batch_extract(self, items: List[Dict[str, str]], 
                     database_id: Optional[str] = None,
                     mode: ExtractionMode = ExtractionMode.FUNCTION_CALL) -> List[ExtractionResult]:
        """
        批量抽取
        
        Args:
            items: 待抽取的内容列表，每个item包含content和url
            database_id: 数据库ID
            mode: 抽取模式
            
        Returns:
            List[ExtractionResult]: 抽取结果列表
        """
        results = []
        
        self.logger.info(f"🚀 开始批量抽取，共 {len(items)} 个项目")
        
        for i, item in enumerate(items):
            self.logger.info(f"📋 处理第 {i + 1}/{len(items)} 个项目...")
            
            result = self.extract(
                content=item.get("content", ""),
                url=item.get("url", ""),
                database_id=database_id,
                mode=mode
            )
            
            results.append(result)
            
            # 批量处理间隔
            if i < len(items) - 1:
                time.sleep(1)
        
        success_count = sum(1 for r in results if r.success)
        self.logger.info(f"✅ 批量抽取完成，成功: {success_count}/{len(items)}")
        
        return results
    
    def test_connection(self) -> bool:
        """测试LLM连接"""
        try:
            self.logger.info("🔗 测试LLM连接...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Hello, are you working?"}
                ],
                max_tokens=50
            )
            
            if response.choices and response.choices[0].message.content:
                self.logger.info("✅ LLM连接正常")
                return True
            else:
                self.logger.error("❌ LLM连接异常：没有响应内容")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ LLM连接失败: {e}")
            return False


# 全局Extractor实例
extractor = LLMExtractor()
async_extractor = AsyncLLMExtractor()


def extract_from_content(content: str, url: str, 
                        database_id: Optional[str] = None,
                        mode: str = "function_call") -> Dict[str, Any]:
    """便捷函数：从内容中抽取信息（同步版本）"""
    extraction_mode = ExtractionMode(mode)
    result = extractor.extract(content, url, database_id, extraction_mode)
    return result.to_dict()


async def extract_from_content_async(content: str, url: str, 
                                    database_id: Optional[str] = None,
                                    mode: str = "function_call") -> Dict[str, Any]:
    """便捷函数：异步从内容中抽取信息"""
    extraction_mode = ExtractionMode(mode)
    result = await async_extractor.extract_async(content, url, database_id, extraction_mode)
    return result.to_dict()


def test_extractor() -> bool:
    """便捷函数：测试Extractor功能（同步版本）"""
    return extractor.test_connection()


async def test_extractor_async() -> bool:
    """便捷函数：测试异步Extractor功能"""
    return await async_extractor.test_connection_async()
