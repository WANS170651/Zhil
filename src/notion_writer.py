"""
NotionWriter模块
实现幂等的Notion写入逻辑，支持创建和更新操作
支持同步和异步两种模式
"""

import time
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import requests
import httpx

from .config import config
from .notion_schema import DatabaseSchema, get_database_schema


class WriteOperation(Enum):
    """写入操作类型"""
    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"


@dataclass
class WriteResult:
    """写入结果"""
    success: bool
    operation: WriteOperation
    page_id: Optional[str] = None
    url: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    existing_page_found: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "operation": self.operation.value,
            "page_id": self.page_id,
            "url": self.url,
            "error_message": self.error_message,
            "processing_time": self.processing_time,
            "existing_page_found": self.existing_page_found
        }


class NotionWriterError(Exception):
    """NotionWriter相关异常"""
    pass


class NotionWriter:
    """Notion数据库写入器（同步版本）"""
    
    def __init__(self):
        """初始化NotionWriter"""
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {config.notion_token}",
            "Notion-Version": config.notion_version,
            "Content-Type": "application/json",
        }
        
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


class AsyncNotionWriter:
    """异步Notion数据库写入器"""
    
    def __init__(self):
        """初始化异步NotionWriter"""
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
    
    async def _make_request_async(self, method: str, url: str, **kwargs) -> httpx.Response:
        """异步HTTP请求"""
        try:
            response = await self.client.request(method, url, **kwargs)
            return response
        except httpx.RequestError as e:
            raise NotionWriterError(f"异步请求失败: {e}")
    
    async def _query_pages_by_url_async(self, url: str, database_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """异步根据URL查询现有页面"""
        if database_id is None:
            database_id = config.notion_database_id
        
        # 构建查询条件
        query_filter = {
            "property": "URL",
            "url": {"equals": url}
        }
        
        query_payload = {
            "filter": query_filter,
            "page_size": 10
        }
        
        query_url = f"{self.base_url}/databases/{database_id}/query"
        
        try:
            response = await self._make_request_async("POST", query_url, json=query_payload)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                self.logger.warning(f"异步查询页面失败: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"异步查询页面异常: {e}")
            return []
    
    async def _create_page_async(self, properties: Dict[str, Any], database_id: Optional[str] = None) -> WriteResult:
        """异步创建新页面"""
        start_time = time.time()
        
        if database_id is None:
            database_id = config.notion_database_id
        
        payload = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        
        create_url = f"{self.base_url}/pages"
        
        try:
            self.logger.info(f"📝 异步创建新页面...")
            
            response = await self._make_request_async("POST", create_url, json=payload)
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                page_id = data.get("id")
                
                # 尝试获取URL
                url = None
                if "URL" in properties and "url" in properties["URL"]:
                    url = properties["URL"]["url"]
                
                self.logger.info(f"✅ 异步页面创建成功，Page ID: {page_id}")
                
                return WriteResult(
                    success=True,
                    operation=WriteOperation.CREATE,
                    page_id=page_id,
                    url=url,
                    processing_time=processing_time
                )
            else:
                error_msg = f"异步创建页面失败: {response.status_code} - {response.text}"
                self.logger.error(f"❌ {error_msg}")
                
                return WriteResult(
                    success=False,
                    operation=WriteOperation.CREATE,
                    error_message=error_msg,
                    processing_time=processing_time
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"异步创建页面异常: {e}"
            self.logger.error(f"❌ {error_msg}")
            
            return WriteResult(
                success=False,
                operation=WriteOperation.CREATE,
                error_message=error_msg,
                processing_time=processing_time
            )
    
    async def _update_page_async(self, page_id: str, properties: Dict[str, Any]) -> WriteResult:
        """异步更新现有页面"""
        start_time = time.time()
        
        payload = {
            "properties": properties
        }
        
        update_url = f"{self.base_url}/pages/{page_id}"
        
        try:
            self.logger.info(f"🔄 异步更新页面 {page_id}...")
            
            response = await self._make_request_async("PATCH", update_url, json=payload)
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # 尝试获取URL
                url = None
                if "URL" in properties and "url" in properties["URL"]:
                    url = properties["URL"]["url"]
                
                self.logger.info(f"✅ 异步页面更新成功，Page ID: {page_id}")
                
                return WriteResult(
                    success=True,
                    operation=WriteOperation.UPDATE,
                    page_id=page_id,
                    url=url,
                    processing_time=processing_time,
                    existing_page_found=True
                )
            else:
                error_msg = f"异步更新页面失败: {response.status_code} - {response.text}"
                self.logger.error(f"❌ {error_msg}")
                
                return WriteResult(
                    success=False,
                    operation=WriteOperation.UPDATE,
                    page_id=page_id,
                    error_message=error_msg,
                    processing_time=processing_time,
                    existing_page_found=True
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"异步更新页面异常: {e}"
            self.logger.error(f"❌ {error_msg}")
            
            return WriteResult(
                success=False,
                operation=WriteOperation.UPDATE,
                page_id=page_id,
                error_message=error_msg,
                processing_time=processing_time,
                existing_page_found=True
            )
    
    async def upsert_async(self, properties: Dict[str, Any], database_id: Optional[str] = None,
                          force_create: bool = False) -> WriteResult:
        """异步幂等写入（创建或更新）"""
        try:
            # 获取URL用于查重
            url = None
            if "URL" in properties and "url" in properties["URL"]:
                url = properties["URL"]["url"]
            
            if not url:
                self.logger.warning("⚠️ 没有URL字段，无法查重，将异步创建新页面")
                return await self._create_page_async(properties, database_id)
            
            # 如果强制创建，跳过查重
            if force_create:
                self.logger.info("🚀 强制创建模式，跳过查重")
                return await self._create_page_async(properties, database_id)
            
            # 异步查询现有页面
            self.logger.info(f"🔍 异步查询现有页面，URL: {url}")
            existing_pages = await self._query_pages_by_url_async(url, database_id)
            
            if existing_pages:
                # 找到现有页面，执行更新
                page_id = existing_pages[0].get("id")
                self.logger.info(f"📋 找到现有页面 {len(existing_pages)} 个，将异步更新第一个: {page_id}")
                return await self._update_page_async(page_id, properties)
            else:
                # 没有找到现有页面，创建新页面
                self.logger.info("📝 未找到现有页面，将异步创建新页面")
                return await self._create_page_async(properties, database_id)
                
        except Exception as e:
            error_msg = f"异步Upsert操作异常: {e}"
            self.logger.error(f"❌ {error_msg}")
            
            return WriteResult(
                success=False,
                operation=WriteOperation.CREATE,
                error_message=error_msg
            )
    
    async def batch_upsert_async(self, items: List[Dict[str, Any]], database_id: Optional[str] = None,
                                force_create: bool = False, max_concurrent: int = 3) -> List[WriteResult]:
        """异步批量写入"""
        self.logger.info(f"🚀 开始异步批量写入，共 {len(items)} 个项目，最大并发数: {max_concurrent}")
        
        # 使用信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_item(i: int, properties: Dict[str, Any]) -> WriteResult:
            async with semaphore:
                self.logger.info(f"📋 异步处理第 {i + 1}/{len(items)} 个项目...")
                return await self.upsert_async(properties, database_id, force_create)
        
        # 并发执行所有写入操作
        tasks = [process_item(i, properties) for i, properties in enumerate(items)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = WriteResult(
                    success=False,
                    operation=WriteOperation.CREATE,
                    error_message=f"异步批量写入异常: {result}"
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)
        
        # 统计结果
        success_count = sum(1 for r in processed_results if r.success)
        create_count = sum(1 for r in processed_results if r.operation == WriteOperation.CREATE and r.success)
        update_count = sum(1 for r in processed_results if r.operation == WriteOperation.UPDATE and r.success)
        
        self.logger.info(f"✅ 异步批量写入完成，成功: {success_count}/{len(items)}")
        self.logger.info(f"📊 操作统计 - 创建: {create_count}, 更新: {update_count}")
        
        return processed_results
    
    async def test_connection_async(self) -> bool:
        """测试异步Notion API连接"""
        try:
            self.logger.info("🔗 测试异步Notion API连接...")
            
            # 尝试获取数据库信息
            database_id = config.notion_database_id
            test_url = f"{self.base_url}/databases/{database_id}"
            
            response = await self._make_request_async("GET", test_url)
            
            if response.status_code == 200:
                self.logger.info("✅ 异步Notion API连接正常")
                return True
            else:
                self.logger.error(f"❌ 异步Notion API连接异常: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 异步Notion API连接失败: {e}")
            return False

# 继续同步版本的_make_request方法
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """发起HTTP请求"""
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            raise NotionWriterError(f"请求失败: {e}")
    
    def _query_pages_by_url(self, url: str, database_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        根据URL查询现有页面
        
        Args:
            url: 要查询的URL
            database_id: 数据库ID，默认使用配置中的ID
            
        Returns:
            匹配的页面列表
        """
        if database_id is None:
            database_id = config.notion_database_id
        
        # 构建查询条件
        query_filter = {
            "property": "URL",  # 假设URL字段名为URL
            "url": {
                "equals": url
            }
        }
        
        query_payload = {
            "filter": query_filter,
            "page_size": 10  # 限制返回数量
        }
        
        query_url = f"{self.base_url}/databases/{database_id}/query"
        
        try:
            response = self._make_request("POST", query_url, json=query_payload)
            
            if response.ok:
                data = response.json()
                return data.get("results", [])
            else:
                self.logger.warning(f"查询页面失败: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"查询页面异常: {e}")
            return []
    
    def _create_page(self, properties: Dict[str, Any], database_id: Optional[str] = None) -> WriteResult:
        """
        创建新页面
        
        Args:
            properties: 页面属性
            database_id: 数据库ID
            
        Returns:
            WriteResult: 写入结果
        """
        start_time = time.time()
        
        if database_id is None:
            database_id = config.notion_database_id
        
        payload = {
            "parent": {"database_id": database_id},
            "properties": properties
        }
        
        create_url = f"{self.base_url}/pages"
        
        try:
            self.logger.info(f"📝 创建新页面...")
            
            response = self._make_request("POST", create_url, json=payload)
            processing_time = time.time() - start_time
            
            if response.ok:
                data = response.json()
                page_id = data.get("id")
                
                # 尝试获取URL
                url = None
                if "URL" in properties and "url" in properties["URL"]:
                    url = properties["URL"]["url"]
                
                self.logger.info(f"✅ 页面创建成功，Page ID: {page_id}")
                
                return WriteResult(
                    success=True,
                    operation=WriteOperation.CREATE,
                    page_id=page_id,
                    url=url,
                    processing_time=processing_time
                )
            else:
                error_msg = f"创建页面失败: {response.status_code} - {response.text}"
                self.logger.error(f"❌ {error_msg}")
                
                return WriteResult(
                    success=False,
                    operation=WriteOperation.CREATE,
                    error_message=error_msg,
                    processing_time=processing_time
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"创建页面异常: {e}"
            self.logger.error(f"❌ {error_msg}")
            
            return WriteResult(
                success=False,
                operation=WriteOperation.CREATE,
                error_message=error_msg,
                processing_time=processing_time
            )
    
    def _update_page(self, page_id: str, properties: Dict[str, Any]) -> WriteResult:
        """
        更新现有页面
        
        Args:
            page_id: 页面ID
            properties: 要更新的属性
            
        Returns:
            WriteResult: 写入结果
        """
        start_time = time.time()
        
        payload = {
            "properties": properties
        }
        
        update_url = f"{self.base_url}/pages/{page_id}"
        
        try:
            self.logger.info(f"🔄 更新页面 {page_id}...")
            
            response = self._make_request("PATCH", update_url, json=payload)
            processing_time = time.time() - start_time
            
            if response.ok:
                data = response.json()
                
                # 尝试获取URL
                url = None
                if "URL" in properties and "url" in properties["URL"]:
                    url = properties["URL"]["url"]
                
                self.logger.info(f"✅ 页面更新成功，Page ID: {page_id}")
                
                return WriteResult(
                    success=True,
                    operation=WriteOperation.UPDATE,
                    page_id=page_id,
                    url=url,
                    processing_time=processing_time,
                    existing_page_found=True
                )
            else:
                error_msg = f"更新页面失败: {response.status_code} - {response.text}"
                self.logger.error(f"❌ {error_msg}")
                
                return WriteResult(
                    success=False,
                    operation=WriteOperation.UPDATE,
                    page_id=page_id,
                    error_message=error_msg,
                    processing_time=processing_time,
                    existing_page_found=True
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"更新页面异常: {e}"
            self.logger.error(f"❌ {error_msg}")
            
            return WriteResult(
                success=False,
                operation=WriteOperation.UPDATE,
                page_id=page_id,
                error_message=error_msg,
                processing_time=processing_time,
                existing_page_found=True
            )
    
    def upsert(self, properties: Dict[str, Any], database_id: Optional[str] = None,
               force_create: bool = False) -> WriteResult:
        """
        幂等写入（创建或更新）
        
        Args:
            properties: 页面属性
            database_id: 数据库ID
            force_create: 强制创建新页面，不检查重复
            
        Returns:
            WriteResult: 写入结果
        """
        try:
            # 获取URL用于查重
            url = None
            if "URL" in properties and "url" in properties["URL"]:
                url = properties["URL"]["url"]
            
            if not url:
                self.logger.warning("⚠️ 没有URL字段，无法查重，将创建新页面")
                return self._create_page(properties, database_id)
            
            # 如果强制创建，跳过查重
            if force_create:
                self.logger.info("🚀 强制创建模式，跳过查重")
                return self._create_page(properties, database_id)
            
            # 查询现有页面
            self.logger.info(f"🔍 查询现有页面，URL: {url}")
            existing_pages = self._query_pages_by_url(url, database_id)
            
            if existing_pages:
                # 找到现有页面，执行更新
                page_id = existing_pages[0].get("id")
                self.logger.info(f"📋 找到现有页面 {len(existing_pages)} 个，将更新第一个: {page_id}")
                return self._update_page(page_id, properties)
            else:
                # 没有找到现有页面，创建新页面
                self.logger.info("📝 未找到现有页面，将创建新页面")
                return self._create_page(properties, database_id)
                
        except Exception as e:
            error_msg = f"Upsert操作异常: {e}"
            self.logger.error(f"❌ {error_msg}")
            
            return WriteResult(
                success=False,
                operation=WriteOperation.CREATE,  # 默认操作类型
                error_message=error_msg
            )
    
    def batch_upsert(self, items: List[Dict[str, Any]], database_id: Optional[str] = None,
                    force_create: bool = False) -> List[WriteResult]:
        """
        批量写入
        
        Args:
            items: 要写入的属性列表
            database_id: 数据库ID
            force_create: 强制创建新页面
            
        Returns:
            List[WriteResult]: 写入结果列表
        """
        results = []
        
        self.logger.info(f"🚀 开始批量写入，共 {len(items)} 个项目")
        
        for i, properties in enumerate(items):
            self.logger.info(f"📋 处理第 {i + 1}/{len(items)} 个项目...")
            
            result = self.upsert(properties, database_id, force_create)
            results.append(result)
            
            # 批量处理间隔，避免API限流
            if i < len(items) - 1:
                time.sleep(0.5)
        
        # 统计结果
        success_count = sum(1 for r in results if r.success)
        create_count = sum(1 for r in results if r.operation == WriteOperation.CREATE and r.success)
        update_count = sum(1 for r in results if r.operation == WriteOperation.UPDATE and r.success)
        
        self.logger.info(f"✅ 批量写入完成，成功: {success_count}/{len(items)}")
        self.logger.info(f"📊 操作统计 - 创建: {create_count}, 更新: {update_count}")
        
        return results
    
    def delete_page(self, page_id: str) -> WriteResult:
        """
        删除页面（移动到垃圾桶）
        
        Args:
            page_id: 页面ID
            
        Returns:
            WriteResult: 操作结果
        """
        start_time = time.time()
        
        payload = {
            "archived": True
        }
        
        update_url = f"{self.base_url}/pages/{page_id}"
        
        try:
            self.logger.info(f"🗑️ 删除页面 {page_id}...")
            
            response = self._make_request("PATCH", update_url, json=payload)
            processing_time = time.time() - start_time
            
            if response.ok:
                self.logger.info(f"✅ 页面删除成功，Page ID: {page_id}")
                
                return WriteResult(
                    success=True,
                    operation=WriteOperation.UPDATE,  # 删除实际上是更新archived状态
                    page_id=page_id,
                    processing_time=processing_time
                )
            else:
                error_msg = f"删除页面失败: {response.status_code} - {response.text}"
                self.logger.error(f"❌ {error_msg}")
                
                return WriteResult(
                    success=False,
                    operation=WriteOperation.UPDATE,
                    page_id=page_id,
                    error_message=error_msg,
                    processing_time=processing_time
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"删除页面异常: {e}"
            self.logger.error(f"❌ {error_msg}")
            
            return WriteResult(
                success=False,
                operation=WriteOperation.UPDATE,
                page_id=page_id,
                error_message=error_msg,
                processing_time=processing_time
            )
    
    def get_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        获取页面详情
        
        Args:
            page_id: 页面ID
            
        Returns:
            页面数据或None
        """
        get_url = f"{self.base_url}/pages/{page_id}"
        
        try:
            response = self._make_request("GET", get_url)
            
            if response.ok:
                return response.json()
            else:
                self.logger.error(f"获取页面失败: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"获取页面异常: {e}")
            return None
    
    def test_connection(self) -> bool:
        """测试Notion API连接"""
        try:
            self.logger.info("🔗 测试Notion API连接...")
            
            # 尝试获取数据库信息
            database_id = config.notion_database_id
            test_url = f"{self.base_url}/databases/{database_id}"
            
            response = self._make_request("GET", test_url)
            
            if response.ok:
                self.logger.info("✅ Notion API连接正常")
                return True
            else:
                self.logger.error(f"❌ Notion API连接异常: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Notion API连接失败: {e}")
            return False


# 全局NotionWriter实例
notion_writer = NotionWriter()
async_notion_writer = AsyncNotionWriter()


def write_to_notion(properties: Dict[str, Any], database_id: Optional[str] = None,
                   force_create: bool = False) -> Dict[str, Any]:
    """便捷函数：写入Notion数据库（同步版本）"""
    result = notion_writer.upsert(properties, database_id, force_create)
    return result.to_dict()


async def write_to_notion_async(properties: Dict[str, Any], database_id: Optional[str] = None,
                               force_create: bool = False) -> Dict[str, Any]:
    """便捷函数：异步写入Notion数据库"""
    result = await async_notion_writer.upsert_async(properties, database_id, force_create)
    return result.to_dict()


def test_notion_connection() -> bool:
    """便捷函数：测试Notion连接（同步版本）"""
    return notion_writer.test_connection()


async def test_notion_connection_async() -> bool:
    """便捷函数：测试异步Notion连接"""
    return await async_notion_writer.test_connection_async()
