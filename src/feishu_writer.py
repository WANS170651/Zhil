"""
飞书多维表格写入模块
实现飞书Bitable API调用，支持批量新增记录
包含Token管理、缓存和刷新机制
"""

import time
import json
import logging
import asyncio
import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import requests
import httpx
from pathlib import Path

from .config import config


class FeishuWriteOperation(Enum):
    """飞书写入操作类型"""
    CREATE = "create"
    SKIP = "skip"


@dataclass
class FeishuWriteResult:
    """飞书写入结果"""
    success: bool
    operation: FeishuWriteOperation
    record_id: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "operation": self.operation.value,
            "record_id": self.record_id,
            "error_message": self.error_message,
            "processing_time": self.processing_time
        }


class FeishuWriterError(Exception):
    """飞书Writer相关异常"""
    pass


class FeishuTokenManager:
    """飞书Token管理器，负责token的获取、缓存和刷新"""
    
    def __init__(self, app_id: str, app_secret: str, cache_dir: Optional[str] = None):
        """
        初始化Token管理器
        
        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用Secret
            cache_dir: 缓存目录，默认使用项目根目录下的.feishu_cache
        """
        self.app_id = app_id
        self.app_secret = app_secret
        
        # 设置缓存目录
        if cache_dir is None:
            project_root = Path(__file__).parent.parent
            cache_dir = project_root / ".feishu_cache"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Token缓存文件路径
        self.tenant_token_file = self.cache_dir / "tenant_access_token.json"
        self.user_token_file = self.cache_dir / "user_access_token.json"
        
        # 飞书API基础URL
        self.base_url = "https://open.feishu.cn"
        
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
    
    def _is_token_valid(self, token_data: Dict[str, Any]) -> bool:
        """检查token是否有效（未过期）"""
        if not token_data or 'expires_at' not in token_data:
            return False
        
        # 提前5分钟刷新token
        buffer_time = 300  # 5分钟
        return time.time() < (token_data['expires_at'] - buffer_time)
    
    def _save_token_cache(self, token_data: Dict[str, Any], token_type: str):
        """保存token到缓存文件"""
        try:
            cache_file = self.tenant_token_file if token_type == 'tenant' else self.user_token_file
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ {token_type}_access_token已缓存")
            
        except Exception as e:
            self.logger.error(f"❌ 保存{token_type}_access_token缓存失败: {e}")
    
    def _load_token_cache(self, token_type: str) -> Optional[Dict[str, Any]]:
        """从缓存文件加载token"""
        try:
            cache_file = self.tenant_token_file if token_type == 'tenant' else self.user_token_file
            
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            if self._is_token_valid(token_data):
                self.logger.info(f"✅ 从缓存加载有效的{token_type}_access_token")
                return token_data
            else:
                self.logger.info(f"⚠️ 缓存的{token_type}_access_token已过期")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ 加载{token_type}_access_token缓存失败: {e}")
            return None
    
    def get_tenant_access_token(self) -> str:
        """
        获取tenant_access_token（应用级别token）
        用于创建bitable、管理应用等操作
        """
        # 尝试从缓存加载
        cached_token = self._load_token_cache('tenant')
        if cached_token:
            return cached_token['access_token']
        
        # 缓存无效，重新获取
        self.logger.info("🔄 获取新的tenant_access_token...")
        
        url = f"{self.base_url}/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("code") == 0:
                access_token = data.get("tenant_access_token")
                expires_in = data.get("expire", 7200)  # 默认2小时
                
                # 保存到缓存
                token_data = {
                    "access_token": access_token,
                    "expires_in": expires_in,
                    "expires_at": time.time() + expires_in,
                    "created_at": time.time()
                }
                
                self._save_token_cache(token_data, 'tenant')
                
                self.logger.info("✅ 成功获取tenant_access_token")
                return access_token
            else:
                error_msg = f"获取tenant_access_token失败: {data.get('msg', '未知错误')}"
                self.logger.error(f"❌ {error_msg}")
                raise FeishuWriterError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"获取tenant_access_token网络请求失败: {e}"
            self.logger.error(f"❌ {error_msg}")
            raise FeishuWriterError(error_msg)
    
    def get_user_access_token(self, refresh_token: Optional[str] = None) -> Tuple[str, str]:
        """
        获取user_access_token（用户级别token）
        用于代表用户操作多维表格内容
        
        Args:
            refresh_token: 刷新token，如果为None则尝试从缓存获取
            
        Returns:
            Tuple[access_token, refresh_token]
            
        Note:
            首次使用需要通过OAuth流程获取，这里假设已经有refresh_token
            实际部署时需要实现完整的OAuth授权流程
        """
        # 尝试从缓存加载
        if refresh_token is None:
            cached_token = self._load_token_cache('user')
            if cached_token:
                return cached_token['access_token'], cached_token.get('refresh_token', '')
        
        # 如果没有refresh_token，无法自动获取user_access_token
        if refresh_token is None:
            error_msg = (
                "无法获取user_access_token: 缺少refresh_token。"
                "请先通过OAuth流程获取refresh_token，或配置为手动提供。"
            )
            self.logger.error(f"❌ {error_msg}")
            raise FeishuWriterError(error_msg)
        
        # 使用refresh_token获取新的user_access_token
        self.logger.info("🔄 使用refresh_token获取新的user_access_token...")
        
        url = f"{self.base_url}/open-apis/auth/v3/access_token"
        headers = {
            "Authorization": f"Bearer {self.get_tenant_access_token()}",
            "Content-Type": "application/json"
        }
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("code") == 0:
                access_token = data.get("access_token")
                new_refresh_token = data.get("refresh_token")
                expires_in = data.get("expires_in", 7200)  # 默认2小时
                
                # 保存到缓存
                token_data = {
                    "access_token": access_token,
                    "refresh_token": new_refresh_token,
                    "expires_in": expires_in,
                    "expires_at": time.time() + expires_in,
                    "created_at": time.time()
                }
                
                self._save_token_cache(token_data, 'user')
                
                self.logger.info("✅ 成功获取user_access_token")
                return access_token, new_refresh_token
            else:
                error_msg = f"获取user_access_token失败: {data.get('msg', '未知错误')}"
                self.logger.error(f"❌ {error_msg}")
                raise FeishuWriterError(error_msg)
                
        except requests.exceptions.RequestException as e:
            error_msg = f"获取user_access_token网络请求失败: {e}"
            self.logger.error(f"❌ {error_msg}")
            raise FeishuWriterError(error_msg)


class FeishuWriter:
    """飞书多维表格写入器（同步版本）"""
    
    def __init__(self, 
                 app_id: Optional[str] = None,
                 app_secret: Optional[str] = None,
                 app_token: Optional[str] = None,
                 table_id: Optional[str] = None):
        """
        初始化飞书写入器
        
        Args:
            app_id: 飞书应用ID，为空时从配置获取
            app_secret: 飞书应用Secret，为空时从配置获取
            app_token: 飞书多维表格Token，为空时从配置获取
            table_id: 飞书表格ID，为空时从配置获取
        """
        # 从配置获取参数
        self.app_id = app_id or getattr(config, 'feishu_app_id', None)
        self.app_secret = app_secret or getattr(config, 'feishu_app_secret', None)
        self.app_token = app_token or getattr(config, 'feishu_app_token', None)
        self.table_id = table_id or getattr(config, 'feishu_table_id', None)
        
        # 验证必需参数
        if not all([self.app_id, self.app_secret, self.app_token, self.table_id]):
            missing_params = []
            if not self.app_id: missing_params.append("app_id")
            if not self.app_secret: missing_params.append("app_secret")
            if not self.app_token: missing_params.append("app_token")
            if not self.table_id: missing_params.append("table_id")
            
            raise FeishuWriterError(f"缺少必需参数: {', '.join(missing_params)}")
        
        # 飞书API基础URL
        self.base_url = "https://open.feishu.cn"
        
        # 初始化Token管理器
        self.token_manager = FeishuTokenManager(self.app_id, self.app_secret)
        
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
    
    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """发起HTTP请求"""
        try:
            response = requests.request(method, url, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            raise FeishuWriterError(f"请求失败: {e}")
    
    def _get_auth_headers(self, token_type: str = "tenant") -> Dict[str, str]:
        """
        获取认证头部
        
        Args:
            token_type: token类型，"tenant" 或 "user"
        """
        if token_type == "tenant":
            token = self.token_manager.get_tenant_access_token()
        else:
            token, _ = self.token_manager.get_user_access_token()
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def batch_create_records(self, records: List[Dict[str, Any]], 
                           use_user_token: bool = True) -> List[FeishuWriteResult]:
        """
        批量创建记录
        
        Args:
            records: 记录列表，每个记录包含fields字段
            use_user_token: 是否使用用户token，默认True
            
        Returns:
            List[FeishuWriteResult]: 写入结果列表
        """
        start_time = time.time()
        
        if not records:
            self.logger.warning("⚠️ 记录列表为空")
            return []
        
        self.logger.info(f"📝 开始批量创建记录，共 {len(records)} 条")
        
        # 构建API URL
        url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/batch_create"
        
        # 准备请求数据
        payload = {
            "records": records
        }
        
        # 获取认证头部
        token_type = "user" if use_user_token else "tenant"
        headers = self._get_auth_headers(token_type)
        
        try:
            response = self._make_request("POST", url, headers=headers, json=payload, timeout=30)
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("code") == 0:
                    # 成功创建记录
                    created_records = data.get("data", {}).get("records", [])
                    results = []
                    
                    for i, record in enumerate(created_records):
                        record_id = record.get("record_id") or record.get("id")
                        
                        result = FeishuWriteResult(
                            success=True,
                            operation=FeishuWriteOperation.CREATE,
                            record_id=record_id,
                            processing_time=processing_time / len(created_records)
                        )
                        results.append(result)
                    
                    self.logger.info(f"✅ 批量创建记录成功，创建了 {len(created_records)} 条记录")
                    return results
                else:
                    # API返回错误
                    error_msg = f"飞书API返回错误: {data.get('msg', '未知错误')} (code: {data.get('code')})"
                    self.logger.error(f"❌ {error_msg}")
                    
                    # 返回失败结果
                    return [FeishuWriteResult(
                        success=False,
                        operation=FeishuWriteOperation.CREATE,
                        error_message=error_msg,
                        processing_time=processing_time
                    ) for _ in records]
            else:
                error_msg = f"HTTP请求失败: {response.status_code} - {response.text}"
                self.logger.error(f"❌ {error_msg}")
                
                return [FeishuWriteResult(
                    success=False,
                    operation=FeishuWriteOperation.CREATE,
                    error_message=error_msg,
                    processing_time=processing_time
                ) for _ in records]
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"批量创建记录异常: {e}"
            self.logger.error(f"❌ {error_msg}")
            
            return [FeishuWriteResult(
                success=False,
                operation=FeishuWriteOperation.CREATE,
                error_message=error_msg,
                processing_time=processing_time
            ) for _ in records]
    
    def create_single_record(self, fields: Dict[str, Any], 
                           use_user_token: bool = True) -> FeishuWriteResult:
        """
        创建单条记录
        
        Args:
            fields: 记录字段数据
            use_user_token: 是否使用用户token
            
        Returns:
            FeishuWriteResult: 写入结果
        """
        records = [{"fields": fields}]
        results = self.batch_create_records(records, use_user_token)
        return results[0] if results else FeishuWriteResult(
            success=False,
            operation=FeishuWriteOperation.CREATE,
            error_message="未知错误"
        )
    
    def test_connection(self, use_user_token: bool = True) -> bool:
        """
        测试飞书连接
        
        Args:
            use_user_token: 是否使用用户token
        """
        try:
            self.logger.info("🔗 测试飞书多维表格连接...")
            
            # 先获取应用信息，验证基本连接
            app_url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.app_token}"
            
            token_type = "user" if use_user_token else "tenant"
            headers = self._get_auth_headers(token_type)
            
            response = self._make_request("GET", app_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    app_name = data.get("data", {}).get("name", "未知应用")
                    self.logger.info(f"✅ 飞书应用连接成功: {app_name}")
                    
                    # 验证表格是否存在
                    tables_url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.app_token}/tables"
                    tables_response = self._make_request("GET", tables_url, headers=headers, timeout=30)
                    
                    if tables_response.status_code == 200:
                        tables_data = tables_response.json()
                        if tables_data.get("code") == 0:
                            tables = tables_data.get("data", {}).get("items", [])
                            # 查找指定的表格
                            target_table = None
                            for table in tables:
                                if table.get("table_id") == self.table_id:
                                    target_table = table
                                    break
                            
                            if target_table:
                                table_name = target_table.get("name", "未知表格")
                                self.logger.info(f"✅ 飞书多维表格连接成功，表格名称: {table_name}")
                                return True
                            else:
                                self.logger.error(f"❌ 未找到指定的表格ID: {self.table_id}")
                                return False
                        else:
                            self.logger.error(f"❌ 获取表格列表失败: {tables_data.get('msg', '未知错误')}")
                            return False
                    else:
                        self.logger.error(f"❌ 获取表格列表请求失败: {tables_response.status_code}")
                        return False
                else:
                    self.logger.error(f"❌ 飞书API返回错误: {data.get('msg', '未知错误')}")
                    return False
            else:
                self.logger.error(f"❌ 飞书连接失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 飞书连接测试异常: {e}")
            return False


class AsyncFeishuWriter:
    """飞书多维表格写入器（异步版本）"""
    
    def __init__(self,
                 app_id: Optional[str] = None,
                 app_secret: Optional[str] = None,
                 app_token: Optional[str] = None,
                 table_id: Optional[str] = None):
        """
        初始化异步飞书写入器
        
        Args:
            app_id: 飞书应用ID，为空时从配置获取
            app_secret: 飞书应用Secret，为空时从配置获取
            app_token: 飞书多维表格Token，为空时从配置获取
            table_id: 飞书表格ID，为空时从配置获取
        """
        # 从配置获取参数
        self.app_id = app_id or getattr(config, 'feishu_app_id', None)
        self.app_secret = app_secret or getattr(config, 'feishu_app_secret', None)
        self.app_token = app_token or getattr(config, 'feishu_app_token', None)
        self.table_id = table_id or getattr(config, 'feishu_table_id', None)
        
        # 验证必需参数
        if not all([self.app_id, self.app_secret, self.app_token, self.table_id]):
            missing_params = []
            if not self.app_id: missing_params.append("app_id")
            if not self.app_secret: missing_params.append("app_secret")
            if not self.app_token: missing_params.append("app_token")
            if not self.table_id: missing_params.append("table_id")
            
            raise FeishuWriterError(f"缺少必需参数: {', '.join(missing_params)}")
        
        # 飞书API基础URL
        self.base_url = "https://open.feishu.cn"
        
        # 初始化Token管理器
        self.token_manager = FeishuTokenManager(self.app_id, self.app_secret)
        
        # 异步HTTP客户端
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5)
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
            raise FeishuWriterError(f"异步请求失败: {e}")
    
    def _get_auth_headers(self, token_type: str = "tenant") -> Dict[str, str]:
        """
        获取认证头部
        
        Args:
            token_type: token类型，"tenant" 或 "user"
        """
        if token_type == "tenant":
            token = self.token_manager.get_tenant_access_token()
        else:
            token, _ = self.token_manager.get_user_access_token()
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    async def batch_create_records_async(self, records: List[Dict[str, Any]], 
                                       use_user_token: bool = True) -> List[FeishuWriteResult]:
        """
        异步批量创建记录
        
        Args:
            records: 记录列表，每个记录包含fields字段
            use_user_token: 是否使用用户token，默认True
            
        Returns:
            List[FeishuWriteResult]: 写入结果列表
        """
        start_time = time.time()
        
        if not records:
            self.logger.warning("⚠️ 记录列表为空")
            return []
        
        self.logger.info(f"📝 开始异步批量创建记录，共 {len(records)} 条")
        
        # 构建API URL
        url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/batch_create"
        
        # 准备请求数据
        payload = {
            "records": records
        }
        
        # 获取认证头部
        token_type = "user" if use_user_token else "tenant"
        headers = self._get_auth_headers(token_type)
        
        try:
            response = await self._make_request_async("POST", url, headers=headers, json=payload)
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("code") == 0:
                    # 成功创建记录
                    created_records = data.get("data", {}).get("records", [])
                    results = []
                    
                    for i, record in enumerate(created_records):
                        record_id = record.get("record_id") or record.get("id")
                        
                        result = FeishuWriteResult(
                            success=True,
                            operation=FeishuWriteOperation.CREATE,
                            record_id=record_id,
                            processing_time=processing_time / len(created_records)
                        )
                        results.append(result)
                    
                    self.logger.info(f"✅ 异步批量创建记录成功，创建了 {len(created_records)} 条记录")
                    return results
                else:
                    # API返回错误
                    error_msg = f"飞书API返回错误: {data.get('msg', '未知错误')} (code: {data.get('code')})"
                    self.logger.error(f"❌ {error_msg}")
                    
                    # 返回失败结果
                    return [FeishuWriteResult(
                        success=False,
                        operation=FeishuWriteOperation.CREATE,
                        error_message=error_msg,
                        processing_time=processing_time
                    ) for _ in records]
            else:
                error_msg = f"HTTP请求失败: {response.status_code} - {response.text}"
                self.logger.error(f"❌ {error_msg}")
                
                return [FeishuWriteResult(
                    success=False,
                    operation=FeishuWriteOperation.CREATE,
                    error_message=error_msg,
                    processing_time=processing_time
                ) for _ in records]
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"异步批量创建记录异常: {e}"
            self.logger.error(f"❌ {error_msg}")
            
            return [FeishuWriteResult(
                success=False,
                operation=FeishuWriteOperation.CREATE,
                error_message=error_msg,
                processing_time=processing_time
            ) for _ in records]
    
    async def create_single_record_async(self, fields: Dict[str, Any], 
                                       use_user_token: bool = True) -> FeishuWriteResult:
        """
        异步创建单条记录
        
        Args:
            fields: 记录字段数据
            use_user_token: 是否使用用户token
            
        Returns:
            FeishuWriteResult: 写入结果
        """
        records = [{"fields": fields}]
        results = await self.batch_create_records_async(records, use_user_token)
        return results[0] if results else FeishuWriteResult(
            success=False,
            operation=FeishuWriteOperation.CREATE,
            error_message="未知错误"
        )
    
    async def test_connection_async(self, use_user_token: bool = True) -> bool:
        """
        异步测试飞书连接
        
        Args:
            use_user_token: 是否使用用户token
        """
        try:
            self.logger.info("🔗 异步测试飞书多维表格连接...")
            
            # 先获取应用信息，验证基本连接
            app_url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.app_token}"
            
            token_type = "user" if use_user_token else "tenant"
            headers = self._get_auth_headers(token_type)
            
            response = await self._make_request_async("GET", app_url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    app_name = data.get("data", {}).get("name", "未知应用")
                    self.logger.info(f"✅ 异步飞书应用连接成功: {app_name}")
                    
                    # 验证表格是否存在
                    tables_url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.app_token}/tables"
                    tables_response = await self._make_request_async("GET", tables_url, headers=headers)
                    
                    if tables_response.status_code == 200:
                        tables_data = tables_response.json()
                        if tables_data.get("code") == 0:
                            tables = tables_data.get("data", {}).get("items", [])
                            # 查找指定的表格
                            target_table = None
                            for table in tables:
                                if table.get("table_id") == self.table_id:
                                    target_table = table
                                    break
                            
                            if target_table:
                                table_name = target_table.get("name", "未知表格")
                                self.logger.info(f"✅ 异步飞书多维表格连接成功，表格名称: {table_name}")
                                return True
                            else:
                                self.logger.error(f"❌ 未找到指定的表格ID: {self.table_id}")
                                return False
                        else:
                            self.logger.error(f"❌ 获取表格列表失败: {tables_data.get('msg', '未知错误')}")
                            return False
                    else:
                        self.logger.error(f"❌ 获取表格列表请求失败: {tables_response.status_code}")
                        return False
                else:
                    self.logger.error(f"❌ 飞书API返回错误: {data.get('msg', '未知错误')}")
                    return False
            else:
                self.logger.error(f"❌ 异步飞书连接失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 异步飞书连接测试异常: {e}")
            return False
    
    async def get_table_fields_async(self, use_user_token: bool = False) -> Dict[str, Any]:
        """
        异步获取飞书表格的字段信息
        
        Args:
            use_user_token: 是否使用用户token
            
        Returns:
            Dict: 包含字段信息的字典
        """
        try:
            self.logger.info("📋 获取飞书表格字段信息...")
            
            # 获取表格字段的API端点
            url = f"{self.base_url}/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/fields"
            
            token_type = "user" if use_user_token else "tenant"
            headers = self._get_auth_headers(token_type)
            
            response = await self._make_request_async("GET", url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    fields = data.get("data", {}).get("items", [])
                    
                    # 整理字段信息
                    field_info = {}
                    for field in fields:
                        field_name = field.get("field_name", "")
                        field_id = field.get("field_id", "")
                        field_type = field.get("type", 1)  # 1=文本，2=数字，等等
                        
                        # 根据字段类型确定数据类型
                        data_type = self._get_field_data_type(field_type)
                        
                        field_info[field_name] = {
                            "field_id": field_id,
                            "type": field_type,
                            "data_type": data_type,
                            "field_name": field_name
                        }
                    
                    self.logger.info(f"✅ 成功获取 {len(field_info)} 个字段信息")
                    for name, info in field_info.items():
                        self.logger.info(f"   📝 {name} ({info['data_type']})")
                    
                    return {
                        "success": True,
                        "fields": field_info,
                        "field_count": len(field_info)
                    }
                else:
                    error_msg = f"飞书API返回错误: {data.get('msg', '未知错误')}"
                    self.logger.error(f"❌ {error_msg}")
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"HTTP请求失败: {response.status_code} - {response.text}"
                self.logger.error(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            error_msg = f"获取表格字段异常: {e}"
            self.logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
    
    def _get_field_data_type(self, field_type: int) -> str:
        """
        根据飞书字段类型返回数据类型描述
        
        Args:
            field_type: 飞书字段类型码
            
        Returns:
            str: 数据类型描述
        """
        type_mapping = {
            1: "text",          # 多行文本
            2: "number",        # 数字
            3: "single_select", # 单选
            4: "multi_select",  # 多选
            5: "date",          # 日期
            7: "checkbox",      # 复选框
            11: "user",         # 人员
            13: "phone",        # 电话号码
            15: "url",          # 超链接
            17: "attachment",   # 附件
            18: "single_link",  # 单向关联
            19: "formula",      # 公式
            20: "duplex_link",  # 双向关联
            21: "location",     # 地理位置
            22: "group",        # 分组
            23: "created_time", # 创建时间
            24: "modified_time",# 最后更新时间
            25: "created_user", # 创建人
            26: "modified_user",# 修改人
            1001: "auto_number" # 自动编号
        }
        return type_mapping.get(field_type, f"unknown_type_{field_type}")


# 全局实例（需要在配置设置后初始化）
feishu_writer: Optional[FeishuWriter] = None
async_feishu_writer: Optional[AsyncFeishuWriter] = None


def initialize_feishu_writers():
    """初始化飞书写入器全局实例"""
    global feishu_writer, async_feishu_writer
    
    try:
        # 检查是否有必需的配置
        required_attrs = ['feishu_app_id', 'feishu_app_secret', 'feishu_app_token', 'feishu_table_id']
        missing_attrs = []
        
        for attr in required_attrs:
            try:
                value = getattr(config, attr)
                if not value or value.strip() == "":
                    missing_attrs.append(attr)
            except (ValueError, AttributeError):
                missing_attrs.append(attr)
        
        if missing_attrs:
            logging.getLogger(__name__).warning(
                f"⚠️ 飞书写入器初始化跳过，缺少配置: {', '.join(missing_attrs)}"
            )
            return False
        
        feishu_writer = FeishuWriter()
        async_feishu_writer = AsyncFeishuWriter()
        
        logging.getLogger(__name__).info("✅ 飞书写入器全局实例初始化成功")
        return True
        
    except Exception as e:
        logging.getLogger(__name__).error(f"❌ 飞书写入器初始化失败: {e}")
        return False


def write_to_feishu(fields: Dict[str, Any], use_user_token: bool = True) -> Dict[str, Any]:
    """
    便捷函数：写入飞书多维表格（同步版本）
    
    Args:
        fields: 字段数据
        use_user_token: 是否使用用户token
        
    Returns:
        Dict: 写入结果
    """
    if feishu_writer is None:
        return {
            "success": False,
            "error_message": "飞书写入器未初始化，请检查配置"
        }
    
    result = feishu_writer.create_single_record(fields, use_user_token)
    return result.to_dict()


async def write_to_feishu_async(fields: Dict[str, Any], use_user_token: bool = True) -> Dict[str, Any]:
    """
    便捷函数：异步写入飞书多维表格
    
    Args:
        fields: 字段数据
        use_user_token: 是否使用用户token
        
    Returns:
        Dict: 写入结果
    """
    if async_feishu_writer is None:
        return {
            "success": False,
            "error_message": "异步飞书写入器未初始化，请检查配置"
        }
    
    result = await async_feishu_writer.create_single_record_async(fields, use_user_token)
    return result.to_dict()


def test_feishu_connection(use_user_token: bool = True) -> bool:
    """
    便捷函数：测试飞书连接（同步版本）
    
    Args:
        use_user_token: 是否使用用户token
    """
    if feishu_writer is None:
        return False
    
    return feishu_writer.test_connection(use_user_token)


async def test_feishu_connection_async(use_user_token: bool = True) -> bool:
    """
    便捷函数：异步测试飞书连接
    
    Args:
        use_user_token: 是否使用用户token
    """
    if async_feishu_writer is None:
        return False
    
    return await async_feishu_writer.test_connection_async(use_user_token)
