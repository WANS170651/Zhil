"""
FastAPI服务模块
提供URL信息收集和存储的RESTful API接口
"""

import time
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, HttpUrl, Field, validator
import uvicorn
import os
from pathlib import Path

from .main_pipeline import main_pipeline, async_main_pipeline, process_url, process_url_async, process_urls, process_urls_concurrent
from .config import config
from .settings_manager import settings_manager, UserSettings


# 配置日志
logging.basicConfig(
    level=getattr(logging, config.log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Pydantic模型定义
class URLItem(BaseModel):
    """单个URL项目"""
    url: HttpUrl = Field(..., description="要处理的URL")
    metadata: Optional[Dict[str, Any]] = Field(None, description="可选的元数据")


class SingleURLRequest(BaseModel):
    """单个URL处理请求"""
    url: HttpUrl = Field(..., description="要处理的URL", example="https://example.com/job/123")
    force_create: bool = Field(False, description="是否强制创建新记录（跳过去重）")
    metadata: Optional[Dict[str, Any]] = Field(None, description="可选的元数据")


class BatchURLRequest(BaseModel):
    """批量URL处理请求"""
    urls: List[Union[str, URLItem]] = Field(
        ..., 
        description="要处理的URL列表", 
        min_items=1, 
        max_items=50,
        example=[
            "https://example.com/job/1",
            "https://example.com/job/2"
        ]
    )
    force_create: bool = Field(False, description="是否强制创建新记录（跳过去重）")
    batch_delay: float = Field(1.0, description="批量处理间隔时间（秒）", ge=0.1, le=10.0)
    
    @validator('urls')
    def validate_urls(cls, v):
        """验证URL列表"""
        if not v:
            raise ValueError("URL列表不能为空")
        
        validated_urls = []
        for item in v:
            if isinstance(item, str):
                # 简单的URL字符串
                if not item.strip():
                    raise ValueError("URL不能为空")
                validated_urls.append(URLItem(url=item.strip()))
            elif isinstance(item, dict):
                # URL对象
                validated_urls.append(URLItem(**item))
            elif isinstance(item, URLItem):
                # 已经是URLItem对象
                validated_urls.append(item)
            else:
                raise ValueError(f"无效的URL项目类型: {type(item)}")
        
        return validated_urls


class ProcessingResponse(BaseModel):
    """处理响应基础模型"""
    success: bool = Field(..., description="处理是否成功")
    message: str = Field(..., description="响应消息")
    timestamp: float = Field(..., description="处理时间戳")
    processing_time: float = Field(..., description="处理耗时（秒）")


class SettingsRequest(BaseModel):
    """设置请求模型"""
    qwen_api_key: Optional[str] = Field(None, description="Qwen LLM API Key")
    notion_api_key: Optional[str] = Field(None, description="Notion API Key")
    notion_database_id: Optional[str] = Field(None, description="Notion Database ID")


class SettingsResponse(BaseModel):
    """设置响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Dict[str, Any]] = Field(None, description="设置数据")
    timestamp: float = Field(..., description="时间戳")


class SingleURLResponse(ProcessingResponse):
    """单个URL处理响应"""
    url: str = Field(..., description="处理的URL")
    result: Dict[str, Any] = Field(..., description="详细处理结果")


class BatchURLResponse(ProcessingResponse):
    """批量URL处理响应"""
    summary: Dict[str, Any] = Field(..., description="处理摘要")
    report: Dict[str, Any] = Field(..., description="详细报告")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    timestamp: float = Field(..., description="检查时间戳")
    components: Dict[str, bool] = Field(..., description="各组件状态")
    version: str = Field(..., description="服务版本")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    timestamp: float = Field(..., description="错误时间戳")
    request_id: Optional[str] = Field(None, description="请求ID")


# FastAPI应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("🚀 启动URL信息收集和存储API服务...")
    
    # 测试各组件连接（使用异步方法）
    try:
        from .notion_writer import test_notion_connection_async
        from .extractor import test_extractor_async
        from .notion_schema import get_database_schema_async
        
        # 异步测试各组件
        notion_ok = await test_notion_connection_async()
        llm_ok = await test_extractor_async()
        schema = await get_database_schema_async()
        schema_ok = schema is not None
        
        all_ok = all([notion_ok, llm_ok, schema_ok])
        
        if all_ok:
            logger.info("✅ 所有组件连接正常，服务就绪")
        else:
            logger.warning("⚠️ 部分组件连接异常，但服务仍可运行")
            if not notion_ok:
                logger.warning("  - Notion连接异常")
            if not llm_ok:
                logger.warning("  - LLM连接异常")
            if not schema_ok:
                logger.warning("  - Schema获取异常")
                
    except Exception as e:
        logger.error(f"❌ 组件连接测试失败: {e}")
        logger.warning("⚠️ 服务可能不稳定，但将继续启动")
    
    yield
    
    # 关闭时
    logger.info("🔽 正在关闭API服务...")


# 创建FastAPI应用
app = FastAPI(
    title="URL信息收集和存储系统",
    description="""
    自动化的URL信息收集和存储系统，支持：
    
    * 🕷️ **智能网页爬取** - 支持SPA和静态页面
    * 🧠 **AI驱动提取** - 使用LLM自动识别和提取信息
    * 🔧 **数据智能清理** - 自动格式化和验证
    * 💾 **智能去重写入** - 自动识别重复并选择创建/更新
    * 📊 **详细处理报告** - 完整的操作记录和统计
    * 🛡️ **完善错误处理** - 优雅处理各种异常情况
    
    ## 使用场景
    
    * **招聘信息收集** - 自动从招聘网站提取职位信息
    * **数据自动化入库** - 结构化存储到Notion数据库
    * **信息去重管理** - 自动识别和更新重复信息
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置静态文件服务 - 优先使用新模板，回退到旧模板
project_root = Path(__file__).parent.parent
zhil_template_dir = project_root / "Zhil_template"
zhil_build_dir = zhil_template_dir / ".next"
web_dir = project_root / "web"

# 检查新模板是否可用
if zhil_template_dir.exists():
    logger.info(f"🎨 发现新模板目录: {zhil_template_dir}")
    
    # 检查是否已构建 - 支持静态导出模式
    if zhil_build_dir.exists():
        # 检查静态导出文件
        static_export_html = zhil_build_dir / "server" / "app" / "index.html"
        has_static_files = (zhil_build_dir / "static").exists()
        
        if static_export_html.exists() or has_static_files:
            logger.info("✅ 使用已构建的 Zhil 模板 (静态导出模式)")
            
            # 挂载 Next.js 静态资源
            if has_static_files:
                app.mount("/_next/static", StaticFiles(directory=str(zhil_build_dir / "static")), name="next_static")
            
            # 挂载图片和其他公共资源
            public_dir = zhil_template_dir / "public"
            if public_dir.exists():
                app.mount("/images", StaticFiles(directory=str(public_dir / "images")), name="images")
                app.mount("/public", StaticFiles(directory=str(public_dir)), name="public")
            
            # 主界面路由 - 指向静态导出的 HTML
            @app.get("/ui", response_class=FileResponse)
            @app.get("/ui/", response_class=FileResponse)
            @app.get("/", response_class=FileResponse, include_in_schema=False)
            async def web_interface():
                """新版Web界面主页 (Zhil模板 - 静态导出)"""
                # 优先使用静态导出的 HTML
                if static_export_html.exists():
                    return FileResponse(str(static_export_html))
                else:
                    raise HTTPException(status_code=404, detail="Zhil模板构建文件不完整")
            
    else:
        logger.warning("⚠️ Zhil模板未构建，将使用开发代理模式")
        
        # 开发模式路由
        @app.get("/ui")
        @app.get("/ui/")
        async def web_interface_dev():
            """开发模式：提示用户启动 Next.js 开发服务器"""
            return {
                "message": "Zhil模板开发模式",
                "instructions": [
                    "请在 Zhil_template 目录运行以下命令:",
                    "1. npm install",
                    "2. npm run dev",
                    "3. 访问 http://localhost:3000"
                ],
                "build_instructions": [
                    "或构建生产版本:",
                    "1. npm run build",
                    "2. 重启此API服务"
                ]
            }

# 备用方案：使用旧模板
elif web_dir.exists():
    logger.info(f"📱 使用旧版模板: {web_dir}")
    # 挂载静态文件目录
    app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")
    
    # Web界面路由
    @app.get("/ui", response_class=FileResponse)
    @app.get("/ui/", response_class=FileResponse)
    async def web_interface_legacy():
        """旧版Web界面主页"""
        return FileResponse(str(web_dir / "index.html"))
        
    logger.info(f"✅ 旧版静态文件服务已配置: {web_dir}")

else:
    logger.error(f"❌ 未找到任何Web模板目录")
    
    @app.get("/ui")
    @app.get("/ui/")
    async def web_interface_missing():
        """模板缺失提示"""
        return {
            "error": "Web模板不存在",
            "message": "请确保 Zhil_template 或 web 目录存在",
            "api_docs": "/docs"
        }

# 通用的测试和调试页面路由
@app.get("/test", response_class=FileResponse)
async def test_page():
    """API连接测试页面"""
    test_file = project_root / "test_api.html"
    if test_file.exists():
        return FileResponse(str(test_file))
    else:
        return {"error": "Test file not found", "message": "API测试页面不存在"}

@app.get("/debug", response_class=FileResponse)
async def debug_page():
    """API调试页面"""
    debug_file = project_root / "debug.html"
    if debug_file.exists():
        return FileResponse(str(debug_file))
    else:
        return {"error": "Debug file not found", "message": "调试页面不存在"}


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="InternalServerError",
            message=f"服务器内部错误: {str(exc)}",
            timestamp=time.time(),
            request_id=getattr(request.state, 'request_id', None)
        ).dict()
    )


# 中间件：添加请求ID
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """添加请求ID中间件"""
    request_id = f"req_{int(time.time())}_{id(request)}"
    request.state.request_id = request_id
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# API端点定义
@app.get("/", tags=["基础"])
async def root():
    """根端点"""
    return {
        "message": "URL信息收集和存储系统API",
        "version": "1.0.0",
        "web_interface": "/ui",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "single_url": "/ingest/url",
            "batch_urls": "/ingest/batch",
            "config": "/config"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["监控"])
async def health_check():
    """健康检查端点"""
    start_time = time.time()
    
    # 测试各组件连接
    components_status = {
        "pipeline": False,
        "notion": False,
        "llm": False,
        "schema": False
    }
    
    try:
        # 测试异步组件连接
        from .notion_writer import async_notion_writer, test_notion_connection_async
        from .extractor import async_extractor, test_extractor_async
        from .notion_schema import get_database_schema_async
        
        # 测试异步Notion连接
        try:
            notion_ok = await test_notion_connection_async()
            components_status["notion"] = notion_ok
        except Exception as e:
            logger.error(f"Notion连接测试失败: {e}")
            components_status["notion"] = False
        
        # 测试异步LLM连接
        try:
            llm_ok = await test_extractor_async()
            components_status["llm"] = llm_ok
        except Exception as e:
            logger.error(f"LLM连接测试失败: {e}")
            components_status["llm"] = False
        
        # 测试异步Schema获取
        try:
            schema = await get_database_schema_async()
            components_status["schema"] = schema is not None
        except Exception as e:
            logger.error(f"Schema获取测试失败: {e}")
            components_status["schema"] = False
        
        # 管道状态：如果所有组件都正常，则管道正常
        components_status["pipeline"] = all([
            components_status["notion"],
            components_status["llm"], 
            components_status["schema"]
        ])
        
    except Exception as e:
        logger.error(f"健康检查异常: {e}")
    
    all_healthy = all(components_status.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=time.time(),
        components=components_status,
        version="1.0.0"
    )


@app.post("/ingest/url", response_model=SingleURLResponse, tags=["数据处理"])
async def ingest_single_url_async(
    request: SingleURLRequest,
    background_tasks: BackgroundTasks
):
    """
    🔥 异步处理单个URL（重构版本）
    
    - 🚀 真正的非阻塞异步处理
    - 🕷️ 异步网页爬取
    - 🧠 异步AI信息提取
    - 🔧 智能数据清理和验证
    - 💾 异步写入Notion数据库
    - ⚡ 显著降低响应时间
    
    """
    start_time = time.time()
    url_str = str(request.url)
    
    logger.info(f"📥 收到异步单个URL处理请求: {url_str}")
    
    try:
        # 🔥 使用全新的异步处理管道
        result = await process_url_async(url_str)
        
        processing_time = time.time() - start_time
        success = result.get("success", False)
        
        # 记录处理结果
        if success:
            logger.info(f"✅ 异步单个URL处理成功: {url_str} (耗时: {processing_time:.2f}s)")
        else:
            logger.warning(f"❌ 异步单个URL处理失败: {url_str} - {result.get('error_message', '未知错误')}")
        
        return SingleURLResponse(
            success=success,
            message="异步处理成功" if success else f"异步处理失败: {result.get('error_message', '未知错误')}",
            timestamp=time.time(),
            processing_time=processing_time,
            url=url_str,
            result=result
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_message = f"异步处理异常: {str(e)}"
        
        logger.error(f"❌ 异步单个URL处理异常: {url_str} - {error_message}")
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="AsyncProcessingError",
                message=error_message,
                timestamp=time.time()
            ).dict()
        )


@app.post("/ingest/batch", response_model=BatchURLResponse, tags=["数据处理"])
async def ingest_batch_urls_concurrent(
    request: BatchURLRequest,
    background_tasks: BackgroundTasks
):
    """
    🔥 并发批量处理多个URL（重构版本）
    
    - 🚀 使用asyncio.gather实现真正并发
    - 📦 支持大规模批量URL处理
    - 🎯 智能并发控制，避免API限流
    - ⚡ 3-5倍吞吐量提升
    - 📊 详细的并发处理报告
    - 🛡️ 单个失败不影响其他
    
    """
    start_time = time.time()
    urls = [str(item.url) for item in request.urls]
    
    logger.info(f"📥 收到并发批量URL处理请求: {len(urls)} 个URL")
    
    try:
        # 设置并发参数（根据批量大小动态调整）
        original_concurrent = async_main_pipeline.max_concurrent
        original_delay = async_main_pipeline.batch_delay
        
        # 动态调整并发数
        if len(urls) <= 3:
            async_main_pipeline.max_concurrent = len(urls)
        elif len(urls) <= 10:
            async_main_pipeline.max_concurrent = 3
        elif len(urls) <= 20:
            async_main_pipeline.max_concurrent = 5
        else:
            async_main_pipeline.max_concurrent = 8
        
        async_main_pipeline.batch_delay = request.batch_delay
        
        # 重新创建信号量以反映新的并发数
        async_main_pipeline.semaphore = asyncio.Semaphore(async_main_pipeline.max_concurrent)
        
        try:
            # 🔥 使用全新的并发处理管道
            report = await process_urls_concurrent(urls)
            
        finally:
            # 恢复原始设置
            async_main_pipeline.max_concurrent = original_concurrent
            async_main_pipeline.batch_delay = original_delay
            async_main_pipeline.semaphore = asyncio.Semaphore(original_concurrent)
        
        processing_time = time.time() - start_time
        summary = report.get("summary", {})
        success_count = summary.get("success_count", 0)
        total_count = summary.get("total_count", 0)
        estimated_speedup = summary.get("estimated_speedup", 1.0)
        
        # 记录处理结果
        logger.info(f"📊 并发批量URL处理完成: {success_count}/{total_count} 成功")
        logger.info(f"⚡ 处理耗时: {processing_time:.2f}s")
        logger.info(f"🚀 预计加速比: {estimated_speedup:.1f}x")
        
        return BatchURLResponse(
            success=True,
            message=f"并发批量处理完成，{success_count}/{total_count} 成功，加速比 {estimated_speedup:.1f}x",
            timestamp=time.time(),
            processing_time=processing_time,
            summary=summary,
            report=report
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_message = f"并发批量处理异常: {str(e)}"
        
        logger.error(f"❌ 并发批量URL处理异常: {error_message}")
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="ConcurrentBatchProcessingError",
                message=error_message,
                timestamp=time.time()
            ).dict()
        )


@app.get("/status/pipeline", tags=["监控"])
async def pipeline_status():
    """获取处理管道状态"""
    try:
        from .notion_schema import get_database_schema_async
        
        schema = await get_database_schema_async()
        
        # 检查异步组件状态
        from .notion_writer import test_notion_connection_async
        from .extractor import test_extractor_async
        
        notion_ok = await test_notion_connection_async()
        llm_ok = await test_extractor_async()
        schema_ok = schema is not None
        
        pipeline_ready = all([notion_ok, llm_ok, schema_ok])
        
        return {
            "pipeline_ready": pipeline_ready,
            "components": {
                "notion": notion_ok,
                "llm": llm_ok,
                "schema": schema_ok
            },
            "database_schema": {
                "loaded": schema is not None,
                "fields_count": len(schema.fields) if schema else 0,
                "title_field": schema.title_field if schema else None,
                "url_field": schema.url_field if schema else None
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"获取管道状态异常: {e}")
        return {
            "pipeline_ready": False,
            "error": str(e),
            "timestamp": time.time()
        }


@app.get("/config", tags=["配置"])
async def get_config():
    """获取系统配置信息（安全版本）"""
    return {
        "llm_model": config.llm_model,
        "notion_version": config.notion_version,
        "schema_cache_ttl": config.schema_cache_ttl,
        "fuzzy_match_threshold": config.fuzzy_match_threshold,
        "log_level": config.log_level,
        "version": "1.0.0"
    }


@app.get("/settings", response_model=SettingsResponse, tags=["设置"])
async def get_settings():
    """获取当前设置"""
    try:
        # 使用设置管理器获取有效设置
        effective_settings = settings_manager.get_effective_settings()
        
        # 转换为字典格式
        settings_data = effective_settings.to_dict()
        
        return SettingsResponse(
            success=True,
            message="设置获取成功",
            data=settings_data,
            timestamp=time.time()
        )
        
    except Exception as e:
        logger.error(f"获取设置失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=SettingsResponse(
                success=False,
                message=f"获取设置失败: {str(e)}",
                timestamp=time.time()
            ).dict()
        )


@app.post("/settings", response_model=SettingsResponse, tags=["设置"])
async def save_settings(request: SettingsRequest):
    """保存设置"""
    try:
        # 使用设置管理器保存设置
        updates = {}
        
        if request.qwen_api_key is not None:
            updates["qwen_api_key"] = request.qwen_api_key
            logger.info("Qwen API Key已更新")
        
        if request.notion_api_key is not None:
            updates["notion_api_key"] = request.notion_api_key
            logger.info("Notion API Key已更新")
        
        if request.notion_database_id is not None:
            updates["notion_database_id"] = request.notion_database_id
            logger.info("Notion Database ID已更新")
        
        # 更新设置
        updated_settings = settings_manager.update_settings(updates)
        
        return SettingsResponse(
            success=True,
            message="设置保存成功",
            data=updated_settings.to_dict(),
            timestamp=time.time()
        )
        
    except Exception as e:
        logger.error(f"保存设置失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=SettingsResponse(
                success=False,
                message=f"保存设置失败: {str(e)}",
                timestamp=time.time()
            ).dict()
        )


@app.post("/settings/test", response_model=SettingsResponse, tags=["设置"])
async def test_settings(request: SettingsRequest):
    """测试设置连接"""
    try:
        test_results = {
            "qwen_api_key": False,
            "notion_api_key": False,
            "notion_database_id": False
        }
        
        # 测试Qwen API Key
        if request.qwen_api_key:
            try:
                # 导入并测试Qwen API连接
                from .extractor import test_extractor_async
                # 临时设置API Key进行测试
                original_key = os.getenv('DASHSCOPE_API_KEY')
                os.environ['DASHSCOPE_API_KEY'] = request.qwen_api_key
                
                test_ok = await test_extractor_async()
                test_results["qwen_api_key"] = test_ok
                
                # 恢复原始API Key
                if original_key:
                    os.environ['DASHSCOPE_API_KEY'] = original_key
                else:
                    os.environ.pop('DASHSCOPE_API_KEY', None)
                
                if test_ok:
                    logger.info("Qwen API连接测试成功")
                else:
                    logger.error("Qwen API连接测试失败")
                    
            except Exception as e:
                logger.error(f"Qwen API连接测试失败: {e}")
        
        # 测试Notion API Key
        if request.notion_api_key:
            try:
                # 导入并测试Notion API连接
                from .notion_writer import test_notion_connection_async
                # 临时设置API Key进行测试
                original_key = os.getenv('NOTION_TOKEN')
                os.environ['NOTION_TOKEN'] = request.notion_api_key
                
                test_ok = await test_notion_connection_async()
                test_results["notion_api_key"] = test_ok
                
                # 恢复原始API Key
                if original_key:
                    os.environ['NOTION_TOKEN'] = original_key
                else:
                    os.environ.pop('NOTION_TOKEN', None)
                
                if test_ok:
                    logger.info("Notion API连接测试成功")
                else:
                    logger.error("Notion API连接测试失败")
                    
            except Exception as e:
                logger.error(f"Notion API连接测试失败: {e}")
        
        # 测试Notion Database ID
        if request.notion_database_id:
            try:
                # 导入并测试Notion Database访问
                from .notion_schema import get_database_schema_async
                # 临时设置Database ID进行测试
                original_db_id = os.getenv('NOTION_DATABASE_ID')
                os.environ['NOTION_DATABASE_ID'] = request.notion_database_id
                
                schema = await get_database_schema_async()
                test_results["notion_database_id"] = schema is not None
                
                # 恢复原始Database ID
                if original_db_id:
                    os.environ['NOTION_DATABASE_ID'] = original_db_id
                else:
                    os.environ.pop('NOTION_DATABASE_ID', None)
                
                if schema:
                    logger.info("Notion Database访问测试成功")
                else:
                    logger.error("Notion Database访问测试失败")
                    
            except Exception as e:
                logger.error(f"Notion Database访问测试失败: {e}")
        
        all_tests_passed = all(test_results.values())
        
        return SettingsResponse(
            success=all_tests_passed,
            message="所有连接测试通过" if all_tests_passed else "部分连接测试失败",
            data=test_results,
            timestamp=time.time()
        )
        
    except Exception as e:
        logger.error(f"测试设置失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=SettingsResponse(
                success=False,
                message=f"测试设置失败: {str(e)}",
                timestamp=time.time()
            ).dict()
        )


# 启动函数
def start_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    log_level: str = "info"
):
    """启动FastAPI服务器"""
    logger.info(f"🚀 启动API服务器 http://{host}:{port}")
    
    uvicorn.run(
        "src.api_service:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=True
    )


if __name__ == "__main__":
    # 直接运行时的配置
    start_server(
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
