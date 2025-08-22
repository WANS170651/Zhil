"""
主处理流程模块
整合WebScraper、Extractor、Normalizer、NotionWriter等组件
实现完整的URL→Notion的数据处理管道
支持同步和异步两种模式，异步模式支持真正的并发处理
"""

import asyncio
import time
import logging
import sys
import os
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# 导入所有必要的模块
from .web_scraper import WebScraper
from .notion_schema import get_database_schema, get_database_schema_async, DatabaseSchema
from .extractor import extractor, async_extractor, ExtractionMode
from .normalizer import normalizer
from .notion_writer import notion_writer, async_notion_writer, WriteOperation, WriteResult
from .config import config


class ProcessingStage(Enum):
    """处理阶段枚举"""
    VALIDATION = "validation"
    SCRAPING = "scraping"
    EXTRACTION = "extraction"
    NORMALIZATION = "normalization"
    WRITING = "writing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStatus(Enum):
    """处理状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProcessingResult:
    """单个URL的处理结果"""
    url: str
    stage: ProcessingStage = ProcessingStage.VALIDATION
    status: ProcessingStatus = ProcessingStatus.PENDING
    
    # 各阶段的详细结果
    scraping_result: Optional[str] = None
    extraction_result: Optional[Dict[str, Any]] = None
    normalization_result: Optional[Dict[str, Any]] = None
    writing_result: Optional[WriteResult] = None
    
    # 时间统计
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    stage_times: Dict[str, float] = field(default_factory=dict)
    
    # 错误信息
    error_message: Optional[str] = None
    error_stage: Optional[ProcessingStage] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = time.time()
    
    @property
    def total_time(self) -> float:
        """总处理时间"""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def success(self) -> bool:
        """是否处理成功"""
        return self.status == ProcessingStatus.SUCCESS and self.stage == ProcessingStage.COMPLETED
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "url": self.url,
            "stage": self.stage.value,
            "status": self.status.value,
            "success": self.success,
            "total_time": self.total_time,
            "stage_times": self.stage_times
        }
        
        if self.writing_result:
            result["writing_result"] = self.writing_result.to_dict()
        
        if self.error_message:
            result["error_message"] = self.error_message
            result["error_stage"] = self.error_stage.value if self.error_stage else None
        
        return result


class MainPipelineError(Exception):
    """主流程异常"""
    pass


class MainPipeline:
    """主处理流程（同步版本）"""
    
    def __init__(self, 
                 headless_browser: bool = True,
                 wait_time: int = 2,
                 max_retries: int = 3,
                 batch_delay: float = 1.0):
        """
        初始化主流程
        
        Args:
            headless_browser: 是否使用无头浏览器
            wait_time: 页面加载等待时间
            max_retries: 最大重试次数
            batch_delay: 批量处理间隔时间
        """
        self.headless_browser = headless_browser
        self.wait_time = wait_time
        self.max_retries = max_retries
        self.batch_delay = batch_delay
        
        # 初始化组件
        self.web_scraper = WebScraper(headless=headless_browser)
        self.database_schema: Optional[DatabaseSchema] = None
        
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


class AsyncMainPipeline:
    """异步主处理流程（支持真正并发）"""
    
    def __init__(self, 
                 headless_browser: bool = True,
                 wait_time: int = 2,
                 max_retries: int = 3,
                 batch_delay: float = 1.0,
                 max_concurrent: int = 5):
        """
        初始化异步主流程
        
        Args:
            headless_browser: 是否使用无头浏览器
            wait_time: 页面加载等待时间
            max_retries: 最大重试次数
            batch_delay: 批量处理间隔时间（异步模式下主要用于速率限制）
            max_concurrent: 最大并发数，防止过度并发导致API限流
        """
        self.headless_browser = headless_browser
        self.wait_time = wait_time
        self.max_retries = max_retries
        self.batch_delay = batch_delay
        self.max_concurrent = max_concurrent
        
        # 并发控制信号量
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # 初始化异步组件
        self.web_scraper = WebScraper(headless=headless_browser)
        self.database_schema: Optional[DatabaseSchema] = None
        
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
    
    async def _load_database_schema_async(self) -> bool:
        """异步加载数据库Schema"""
        try:
            if not self.database_schema:
                self.logger.info("📋 异步加载Notion数据库Schema...")
                self.database_schema = await get_database_schema_async()
                
                if self.database_schema:
                    self.logger.info(f"✅ Schema异步加载成功，包含 {len(self.database_schema.fields)} 个字段")
                    return True
                else:
                    self.logger.error("❌ Schema异步加载失败")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"❌ Schema异步加载异常: {e}")
            return False
    
    def _validate_url(self, url: str) -> bool:
        """验证URL格式（与同步版本共享）"""
        try:
            if not url or not isinstance(url, str):
                return False
            
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                return False
            
            return True
        except Exception:
            return False
    
    async def _extract_information_async(self, scraped_content: str, url: str, result: ProcessingResult) -> bool:
        """异步LLM信息提取"""
        stage_start = time.time()
        
        try:
            result.stage = ProcessingStage.EXTRACTION
            result.status = ProcessingStatus.IN_PROGRESS
            
            self.logger.info(f"🧠 开始异步LLM信息提取...")
            
            # 异步LLM调用
            extraction_result = await async_extractor.extract_async(
                content=scraped_content,
                url=url,
                mode=ExtractionMode.FUNCTION_CALL,
                max_retries=self.max_retries
            )
            
            if extraction_result.success:
                result.extraction_result = extraction_result.to_dict()
                result.status = ProcessingStatus.SUCCESS
                result.stage_times["extraction"] = time.time() - stage_start
                
                extracted_data = extraction_result.data or {}
                self.logger.info(f"✅ 异步信息提取成功，提取 {len(extracted_data)} 个字段")
                
                # 记录提取的关键信息
                if "Company" in extracted_data:
                    self.logger.info(f"   📝 公司: {extracted_data.get('Company', '未知')}")
                if "Position" in extracted_data:
                    self.logger.info(f"   💼 职位: {extracted_data.get('Position', '未知')}")
                
                return True
            else:
                result.status = ProcessingStatus.FAILED
                result.error_message = f"异步LLM提取失败: {extraction_result.error or '未知错误'}"
                result.error_stage = ProcessingStage.EXTRACTION
                
                self.logger.error(f"❌ 异步LLM信息提取失败: {result.error_message}")
                return False
                
        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.error_message = f"异步LLM提取异常: {e}"
            result.error_stage = ProcessingStage.EXTRACTION
            result.stage_times["extraction"] = time.time() - stage_start
            
            self.logger.error(f"❌ 异步LLM提取异常: {e}")
            return False
    
    def _normalize_data(self, extracted_data: Dict[str, Any], result: ProcessingResult) -> bool:
        """数据归一化和验证（与同步版本共享，CPU密集型保持同步）"""
        stage_start = time.time()
        
        try:
            result.stage = ProcessingStage.NORMALIZATION
            result.status = ProcessingStatus.IN_PROGRESS
            
            self.logger.info(f"🔧 开始数据归一化...")
            
            normalization_result = normalizer.normalize(
                raw_data=extracted_data,
                database_schema=self.database_schema
            )
            
            if normalization_result.success:
                result.normalization_result = normalization_result.to_dict()
                result.status = ProcessingStatus.SUCCESS
                result.stage_times["normalization"] = time.time() - stage_start
                
                self.logger.info(f"✅ 数据归一化成功")
                
                # 记录归一化统计
                if normalization_result.error_count > 0:
                    self.logger.warning(f"   ⚠️ 发现 {normalization_result.error_count} 个错误")
                if normalization_result.warning_count > 0:
                    self.logger.info(f"   💡 发现 {normalization_result.warning_count} 个警告")
                
                return True
            else:
                result.status = ProcessingStatus.FAILED
                result.error_message = "数据归一化失败"
                result.error_stage = ProcessingStage.NORMALIZATION
                
                self.logger.error(f"❌ 数据归一化失败")
                return False
                
        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.error_message = f"数据归一化异常: {e}"
            result.error_stage = ProcessingStage.NORMALIZATION
            result.stage_times["normalization"] = time.time() - stage_start
            
            self.logger.error(f"❌ 数据归一化异常: {e}")
            return False
    
    async def _write_to_notion_async(self, normalized_data: Dict[str, Any], result: ProcessingResult) -> bool:
        """异步写入Notion数据库"""
        stage_start = time.time()
        
        try:
            result.stage = ProcessingStage.WRITING
            result.status = ProcessingStatus.IN_PROGRESS
            
            self.logger.info(f"💾 开始异步写入Notion数据库...")
            
            # 获取归一化后的Notion属性
            notion_properties = normalized_data.get("notion_payload", {})
            
            # 异步写入
            write_result = await async_notion_writer.upsert_async(
                properties=notion_properties,
                force_create=False  # 默认启用智能去重
            )
            
            if write_result.success:
                result.writing_result = write_result
                result.status = ProcessingStatus.SUCCESS
                result.stage = ProcessingStage.COMPLETED
                result.stage_times["writing"] = time.time() - stage_start
                result.end_time = time.time()
                
                operation_desc = "创建" if write_result.operation == WriteOperation.CREATE else "更新"
                self.logger.info(f"✅ 异步Notion写入成功，{operation_desc}页面: {write_result.page_id}")
                
                return True
            else:
                result.status = ProcessingStatus.FAILED
                result.error_message = f"异步Notion写入失败: {write_result.error_message}"
                result.error_stage = ProcessingStage.WRITING
                
                self.logger.error(f"❌ 异步Notion写入失败: {write_result.error_message}")
                return False
                
        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.error_message = f"异步Notion写入异常: {e}"
            result.error_stage = ProcessingStage.WRITING
            result.stage_times["writing"] = time.time() - stage_start
            
            self.logger.error(f"❌ 异步Notion写入异常: {e}")
            return False
    
    async def process_single_url_with_semaphore(self, url: str) -> ProcessingResult:
        """带并发控制的单URL处理"""
        async with self.semaphore:  # 并发控制
            return await self.process_single_url_async(url)
    
    async def process_single_url_async(self, url: str) -> ProcessingResult:
        """异步处理单个URL"""
        result = ProcessingResult(url=url)
        
        try:
            self.logger.info(f"🚀 开始异步处理URL: {url}")
            
            # 1. 验证URL
            result.stage = ProcessingStage.VALIDATION
            result.status = ProcessingStatus.IN_PROGRESS
            
            if not self._validate_url(url):
                result.status = ProcessingStatus.FAILED
                result.error_message = "URL格式无效"
                result.error_stage = ProcessingStage.VALIDATION
                return result
            
            # 2. 异步加载数据库Schema
            if not await self._load_database_schema_async():
                result.status = ProcessingStatus.FAILED
                result.error_message = "数据库Schema异步加载失败"
                result.error_stage = ProcessingStage.VALIDATION
                return result
            
            # 3. 爬取页面（已经是异步）
            if not await self._scrape_page_async(url, result):
                return result
            
            # 4. 异步LLM信息提取
            if not await self._extract_information_async(result.scraping_result, url, result):
                return result
            
            # 5. 数据归一化（CPU密集型，保持同步）
            extracted_data = result.extraction_result.get("data", {}) if result.extraction_result else {}
            if not self._normalize_data(extracted_data, result):
                return result
            
            # 6. 异步写入Notion
            if not await self._write_to_notion_async(result.normalization_result, result):
                return result
            
            self.logger.info(f"🎉 异步URL处理完成: {url} (耗时: {result.total_time:.2f}s)")
            
            return result
            
        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.error_message = f"异步处理异常: {e}"
            result.end_time = time.time()
            
            self.logger.error(f"❌ 异步URL处理异常: {url} - {e}")
            return result
    
    async def _scrape_page_async(self, url: str, result: ProcessingResult) -> bool:
        """异步爬取页面内容"""
        stage_start = time.time()
        
        try:
            result.stage = ProcessingStage.SCRAPING
            result.status = ProcessingStatus.IN_PROGRESS
            
            self.logger.info(f"🕷️ 开始异步爬取页面: {url}")
            
            scraped_content = await self.web_scraper.scrape_to_markdown(url, wait_time=self.wait_time)
            
            if scraped_content:
                result.scraping_result = scraped_content
                result.status = ProcessingStatus.SUCCESS
                result.stage_times["scraping"] = time.time() - stage_start
                
                self.logger.info(f"✅ 异步页面爬取成功，内容长度: {len(scraped_content)} 字符")
                return True
            else:
                result.status = ProcessingStatus.FAILED
                result.error_message = "异步页面爬取返回空内容"
                result.error_stage = ProcessingStage.SCRAPING
                
                self.logger.error(f"❌ 异步页面爬取失败: 返回空内容")
                return False
                
        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.error_message = f"异步页面爬取异常: {e}"
            result.error_stage = ProcessingStage.SCRAPING
            result.stage_times["scraping"] = time.time() - stage_start
            
            self.logger.error(f"❌ 异步页面爬取异常: {e}")
            return False
    
    async def process_multiple_urls_concurrent(self, urls: List[str]) -> List[ProcessingResult]:
        """
        真正的并发批量处理（核心改进）
        """
        if not urls:
            self.logger.warning("⚠️ URL列表为空")
            return []
        
        self.logger.info(f"🚀 开始并发处理 {len(urls)} 个URL，最大并发数: {self.max_concurrent}")
        
        start_time = time.time()
        
        # 使用asyncio.gather实现真正并发
        tasks = [self.process_single_url_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 如果某个任务出现异常，创建失败结果
                error_result = ProcessingResult(url=urls[i])
                error_result.status = ProcessingStatus.FAILED
                error_result.error_message = f"并发处理异常: {result}"
                error_result.end_time = time.time()
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        # 统计结果
        total_time = time.time() - start_time
        success_count = sum(1 for r in processed_results if r.success)
        
        # 计算性能提升
        estimated_sequential_time = len(urls) * 15  # 假设顺序处理每个15秒
        speedup_ratio = estimated_sequential_time / total_time if total_time > 0 else 1
        
        self.logger.info(f"📊 并发批量处理完成!")
        self.logger.info(f"   总数: {len(processed_results)}")
        self.logger.info(f"   成功: {success_count}")
        self.logger.info(f"   失败: {len(processed_results) - success_count}")
        self.logger.info(f"   总耗时: {total_time:.2f}s")
        self.logger.info(f"   平均耗时: {total_time/len(processed_results):.2f}s/个")
        self.logger.info(f"   🚀 并发加速比: {speedup_ratio:.1f}x")
        self.logger.info(f"   成功率: {success_count/len(processed_results)*100:.1f}%")
        
        return processed_results
    
    def generate_report(self, results: List[ProcessingResult]) -> Dict[str, Any]:
        """
        生成处理报告（与同步版本共享逻辑）
        
        Args:
            results: 处理结果列表
            
        Returns:
            Dict: 报告数据
        """
        if not results:
            return {"error": "没有处理结果"}
        
        # 基本统计
        total_count = len(results)
        success_count = sum(1 for r in results if r.success)
        failed_count = total_count - success_count
        
        # 操作统计
        create_count = sum(1 for r in results 
                          if r.writing_result and r.writing_result.operation == WriteOperation.CREATE)
        update_count = sum(1 for r in results 
                          if r.writing_result and r.writing_result.operation == WriteOperation.UPDATE)
        
        # 时间统计
        total_time = sum(r.total_time for r in results)
        avg_time = total_time / total_count if total_count > 0 else 0
        
        # 阶段耗时统计
        stage_times = {}
        for stage in ["scraping", "extraction", "normalization", "writing"]:
            times = [r.stage_times.get(stage, 0) for r in results if r.stage_times.get(stage, 0) > 0]
            if times:
                stage_times[stage] = {
                    "avg": sum(times) / len(times),
                    "max": max(times),
                    "min": min(times)
                }
        
        # 错误统计
        error_stages = {}
        for result in results:
            if result.error_stage:
                stage = result.error_stage.value
                error_stages[stage] = error_stages.get(stage, 0) + 1
        
        # 计算性能提升（仅对异步版本）
        estimated_sequential_time = total_count * 15  # 假设顺序处理每个15秒
        actual_wall_time = max(r.total_time for r in results) if results else 0
        speedup_ratio = estimated_sequential_time / actual_wall_time if actual_wall_time > 0 else 1
        
        report = {
            "summary": {
                "total_count": total_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": success_count / total_count * 100 if total_count > 0 else 0,
                "estimated_speedup": speedup_ratio  # 新增：性能提升倍数
            },
            "operations": {
                "create_count": create_count,
                "update_count": update_count
            },
            "timing": {
                "total_time": total_time,
                "average_time": avg_time,
                "wall_clock_time": actual_wall_time,  # 新增：实际墙钟时间
                "stage_times": stage_times
            },
            "errors": {
                "error_stages": error_stages,
                "failed_urls": [r.url for r in results if not r.success]
            },
            "details": [r.to_dict() for r in results]
        }
        
        return report

# 继续同步版本的_load_database_schema方法
    def _load_database_schema(self) -> bool:
        """加载数据库Schema"""
        try:
            if not self.database_schema:
                self.logger.info("📋 加载Notion数据库Schema...")
                self.database_schema = get_database_schema()
                
                if self.database_schema:
                    self.logger.info(f"✅ Schema加载成功，包含 {len(self.database_schema.fields)} 个字段")
                    return True
                else:
                    self.logger.error("❌ Schema加载失败")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"❌ Schema加载异常: {e}")
            return False
    
    def _validate_url(self, url: str) -> bool:
        """验证URL格式"""
        try:
            if not url or not isinstance(url, str):
                return False
            
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                return False
            
            return True
        except Exception:
            return False
    
    async def _scrape_page(self, url: str, result: ProcessingResult) -> bool:
        """爬取页面内容"""
        stage_start = time.time()
        
        try:
            result.stage = ProcessingStage.SCRAPING
            result.status = ProcessingStatus.IN_PROGRESS
            
            self.logger.info(f"🕷️ 开始爬取页面: {url}")
            
            scraped_content = await self.web_scraper.scrape_to_markdown(url, wait_time=self.wait_time)
            
            if scraped_content:
                result.scraping_result = scraped_content
                result.status = ProcessingStatus.SUCCESS
                result.stage_times["scraping"] = time.time() - stage_start
                
                self.logger.info(f"✅ 页面爬取成功，内容长度: {len(scraped_content)} 字符")
                return True
            else:
                result.status = ProcessingStatus.FAILED
                result.error_message = "页面爬取返回空内容"
                result.error_stage = ProcessingStage.SCRAPING
                
                self.logger.error(f"❌ 页面爬取失败: 返回空内容")
                return False
                
        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.error_message = f"页面爬取异常: {e}"
            result.error_stage = ProcessingStage.SCRAPING
            result.stage_times["scraping"] = time.time() - stage_start
            
            self.logger.error(f"❌ 页面爬取异常: {e}")
            return False
    
    def _extract_information(self, scraped_content: str, url: str, result: ProcessingResult) -> bool:
        """使用LLM提取信息"""
        stage_start = time.time()
        
        try:
            result.stage = ProcessingStage.EXTRACTION
            result.status = ProcessingStatus.IN_PROGRESS
            
            self.logger.info(f"🧠 开始LLM信息提取...")
            
            extraction_result = extractor.extract(
                content=scraped_content,
                url=url,
                mode=ExtractionMode.FUNCTION_CALL,
                max_retries=self.max_retries
            )
            
            if extraction_result.success:
                result.extraction_result = extraction_result.to_dict()
                result.status = ProcessingStatus.SUCCESS
                result.stage_times["extraction"] = time.time() - stage_start
                
                extracted_data = extraction_result.data or {}
                self.logger.info(f"✅ 信息提取成功，提取 {len(extracted_data)} 个字段")
                
                # 记录提取的关键信息
                if "Company" in extracted_data:
                    self.logger.info(f"   📝 公司: {extracted_data.get('Company', '未知')}")
                if "Position" in extracted_data:
                    self.logger.info(f"   💼 职位: {extracted_data.get('Position', '未知')}")
                
                return True
            else:
                result.status = ProcessingStatus.FAILED
                result.error_message = f"LLM提取失败: {extraction_result.error or '未知错误'}"
                result.error_stage = ProcessingStage.EXTRACTION
                
                self.logger.error(f"❌ LLM信息提取失败: {result.error_message}")
                return False
                
        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.error_message = f"LLM提取异常: {e}"
            result.error_stage = ProcessingStage.EXTRACTION
            result.stage_times["extraction"] = time.time() - stage_start
            
            self.logger.error(f"❌ LLM提取异常: {e}")
            return False
    
    def _normalize_data(self, extracted_data: Dict[str, Any], result: ProcessingResult) -> bool:
        """数据归一化和验证"""
        stage_start = time.time()
        
        try:
            result.stage = ProcessingStage.NORMALIZATION
            result.status = ProcessingStatus.IN_PROGRESS
            
            self.logger.info(f"🔧 开始数据归一化...")
            
            normalization_result = normalizer.normalize(
                raw_data=extracted_data,
                database_schema=self.database_schema
            )
            
            if normalization_result.success:
                result.normalization_result = normalization_result.to_dict()
                result.status = ProcessingStatus.SUCCESS
                result.stage_times["normalization"] = time.time() - stage_start
                
                self.logger.info(f"✅ 数据归一化成功")
                
                # 记录归一化统计
                if normalization_result.error_count > 0:
                    self.logger.warning(f"   ⚠️ 发现 {normalization_result.error_count} 个错误")
                if normalization_result.warning_count > 0:
                    self.logger.info(f"   💡 发现 {normalization_result.warning_count} 个警告")
                
                return True
            else:
                result.status = ProcessingStatus.FAILED
                result.error_message = "数据归一化失败"
                result.error_stage = ProcessingStage.NORMALIZATION
                
                self.logger.error(f"❌ 数据归一化失败")
                return False
                
        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.error_message = f"数据归一化异常: {e}"
            result.error_stage = ProcessingStage.NORMALIZATION
            result.stage_times["normalization"] = time.time() - stage_start
            
            self.logger.error(f"❌ 数据归一化异常: {e}")
            return False
    
    def _write_to_notion(self, normalized_data: Dict[str, Any], result: ProcessingResult) -> bool:
        """写入Notion数据库"""
        stage_start = time.time()
        
        try:
            result.stage = ProcessingStage.WRITING
            result.status = ProcessingStatus.IN_PROGRESS
            
            self.logger.info(f"💾 开始写入Notion数据库...")
            
            # 获取归一化后的Notion属性
            notion_properties = normalized_data.get("notion_payload", {})
            
            write_result = notion_writer.upsert(
                properties=notion_properties,
                force_create=False  # 默认启用智能去重
            )
            
            if write_result.success:
                result.writing_result = write_result
                result.status = ProcessingStatus.SUCCESS
                result.stage = ProcessingStage.COMPLETED
                result.stage_times["writing"] = time.time() - stage_start
                result.end_time = time.time()
                
                operation_desc = "创建" if write_result.operation == WriteOperation.CREATE else "更新"
                self.logger.info(f"✅ Notion写入成功，{operation_desc}页面: {write_result.page_id}")
                
                return True
            else:
                result.status = ProcessingStatus.FAILED
                result.error_message = f"Notion写入失败: {write_result.error_message}"
                result.error_stage = ProcessingStage.WRITING
                
                self.logger.error(f"❌ Notion写入失败: {write_result.error_message}")
                return False
                
        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.error_message = f"Notion写入异常: {e}"
            result.error_stage = ProcessingStage.WRITING
            result.stage_times["writing"] = time.time() - stage_start
            
            self.logger.error(f"❌ Notion写入异常: {e}")
            return False
    
    async def process_single_url(self, url: str) -> ProcessingResult:
        """
        处理单个URL
        
        Args:
            url: 要处理的URL
            
        Returns:
            ProcessingResult: 处理结果
        """
        result = ProcessingResult(url=url)
        
        try:
            self.logger.info(f"🚀 开始处理URL: {url}")
            
            # 1. 验证URL
            result.stage = ProcessingStage.VALIDATION
            result.status = ProcessingStatus.IN_PROGRESS
            
            if not self._validate_url(url):
                result.status = ProcessingStatus.FAILED
                result.error_message = "URL格式无效"
                result.error_stage = ProcessingStage.VALIDATION
                return result
            
            # 2. 加载数据库Schema
            if not self._load_database_schema():
                result.status = ProcessingStatus.FAILED
                result.error_message = "数据库Schema加载失败"
                result.error_stage = ProcessingStage.VALIDATION
                return result
            
            # 3. 爬取页面
            if not await self._scrape_page(url, result):
                return result
            
            # 4. LLM信息提取
            if not self._extract_information(result.scraping_result, url, result):
                return result
            
            # 5. 数据归一化
            extracted_data = result.extraction_result.get("data", {}) if result.extraction_result else {}
            if not self._normalize_data(extracted_data, result):
                return result
            
            # 6. 写入Notion
            if not self._write_to_notion(result.normalization_result, result):
                return result
            
            self.logger.info(f"🎉 URL处理完成: {url} (耗时: {result.total_time:.2f}s)")
            
            return result
            
        except Exception as e:
            result.status = ProcessingStatus.FAILED
            result.error_message = f"处理异常: {e}"
            result.end_time = time.time()
            
            self.logger.error(f"❌ URL处理异常: {url} - {e}")
            return result
    
    async def process_multiple_urls(self, urls: List[str]) -> List[ProcessingResult]:
        """
        批量处理多个URL
        
        Args:
            urls: URL列表
            
        Returns:
            List[ProcessingResult]: 处理结果列表
        """
        if not urls:
            self.logger.warning("⚠️ URL列表为空")
            return []
        
        self.logger.info(f"🚀 开始批量处理 {len(urls)} 个URL...")
        
        results = []
        start_time = time.time()
        
        for i, url in enumerate(urls):
            self.logger.info(f"📋 处理第 {i + 1}/{len(urls)} 个URL...")
            
            result = await self.process_single_url(url)
            results.append(result)
            
            # 批量处理间隔
            if i < len(urls) - 1:
                await asyncio.sleep(self.batch_delay)
        
        # 统计结果
        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r.success)
        
        self.logger.info(f"📊 批量处理完成!")
        self.logger.info(f"   总数: {len(results)}")
        self.logger.info(f"   成功: {success_count}")
        self.logger.info(f"   失败: {len(results) - success_count}")
        self.logger.info(f"   总耗时: {total_time:.2f}s")
        self.logger.info(f"   平均耗时: {total_time/len(results):.2f}s/个")
        self.logger.info(f"   成功率: {success_count/len(results)*100:.1f}%")
        
        return results
    
    def generate_report(self, results: List[ProcessingResult]) -> Dict[str, Any]:
        """
        生成处理报告
        
        Args:
            results: 处理结果列表
            
        Returns:
            Dict: 报告数据
        """
        if not results:
            return {"error": "没有处理结果"}
        
        # 基本统计
        total_count = len(results)
        success_count = sum(1 for r in results if r.success)
        failed_count = total_count - success_count
        
        # 操作统计
        create_count = sum(1 for r in results 
                          if r.writing_result and r.writing_result.operation == WriteOperation.CREATE)
        update_count = sum(1 for r in results 
                          if r.writing_result and r.writing_result.operation == WriteOperation.UPDATE)
        
        # 时间统计
        total_time = sum(r.total_time for r in results)
        avg_time = total_time / total_count if total_count > 0 else 0
        
        # 阶段耗时统计
        stage_times = {}
        for stage in ["scraping", "extraction", "normalization", "writing"]:
            times = [r.stage_times.get(stage, 0) for r in results if r.stage_times.get(stage, 0) > 0]
            if times:
                stage_times[stage] = {
                    "avg": sum(times) / len(times),
                    "max": max(times),
                    "min": min(times)
                }
        
        # 错误统计
        error_stages = {}
        for result in results:
            if result.error_stage:
                stage = result.error_stage.value
                error_stages[stage] = error_stages.get(stage, 0) + 1
        
        report = {
            "summary": {
                "total_count": total_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": success_count / total_count * 100 if total_count > 0 else 0
            },
            "operations": {
                "create_count": create_count,
                "update_count": update_count
            },
            "timing": {
                "total_time": total_time,
                "average_time": avg_time,
                "stage_times": stage_times
            },
            "errors": {
                "error_stages": error_stages,
                "failed_urls": [r.url for r in results if not r.success]
            },
            "details": [r.to_dict() for r in results]
        }
        
        return report


# 全局主流程实例
main_pipeline = MainPipeline()
async_main_pipeline = AsyncMainPipeline()


async def process_url(url: str) -> Dict[str, Any]:
    """便捷函数：处理单个URL（同步管道的异步接口）"""
    result = await main_pipeline.process_single_url(url)
    return result.to_dict()


async def process_url_async(url: str) -> Dict[str, Any]:
    """便捷函数：异步处理单个URL"""
    result = await async_main_pipeline.process_single_url_async(url)
    return result.to_dict()


async def process_urls(urls: List[str]) -> Dict[str, Any]:
    """便捷函数：批量处理URL（同步管道的异步接口）"""
    results = await main_pipeline.process_multiple_urls(urls)
    report = main_pipeline.generate_report(results)
    return report


async def process_urls_concurrent(urls: List[str]) -> Dict[str, Any]:
    """便捷函数：并发批量处理URL"""
    results = await async_main_pipeline.process_multiple_urls_concurrent(urls)
    report = async_main_pipeline.generate_report(results)
    return report


def test_pipeline_connection() -> bool:
    """测试管道各组件连接"""
    try:
        logging.info("🔗 测试管道组件连接...")
        
        # 测试Notion连接
        if not notion_writer.test_connection():
            logging.error("❌ Notion连接失败")
            return False
        
        # 测试LLM连接
        if not extractor.test_connection():
            logging.error("❌ LLM连接失败")
            return False
        
        # 测试Schema加载
        schema = get_database_schema()
        if not schema:
            logging.error("❌ Schema加载失败")
            return False
        
        logging.info("✅ 管道组件连接正常")
        return True
        
    except Exception as e:
        logging.error(f"❌ 管道连接测试异常: {e}")
        return False
