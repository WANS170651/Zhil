"""
FastAPI服务模块
提供URL信息收集和存储的RESTful API接口
"""

import time
import logging
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

from .main_pipeline import main_pipeline, process_url, process_urls, test_pipeline_connection
from .config import config


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
    
    # 测试各组件连接
    if test_pipeline_connection():
        logger.info("✅ 所有组件连接正常，服务就绪")
    else:
        logger.error("❌ 组件连接测试失败，服务可能不稳定")
    
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

# 配置静态文件服务
web_dir = Path(__file__).parent.parent / "web"
if web_dir.exists():
    # 挂载静态文件目录
    app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")
    
    # Web界面路由
    @app.get("/ui", response_class=FileResponse)
    @app.get("/ui/", response_class=FileResponse)
    async def web_interface():
        """Web界面主页"""
        return FileResponse(str(web_dir / "index.html"))
    
    logger.info(f"✅ 静态文件服务已配置: {web_dir}")
else:
    logger.warning(f"⚠️ Web目录不存在: {web_dir}")


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
        # 测试管道连接
        pipeline_ok = test_pipeline_connection()
        components_status["pipeline"] = pipeline_ok
        
        # 详细组件测试
        from .notion_writer import notion_writer
        from .extractor import extractor
        from .notion_schema import get_database_schema
        
        components_status["notion"] = notion_writer.test_connection()
        components_status["llm"] = extractor.test_connection()
        components_status["schema"] = get_database_schema() is not None
        
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
async def ingest_single_url(
    request: SingleURLRequest,
    background_tasks: BackgroundTasks
):
    """
    处理单个URL
    
    - 🕷️ 自动爬取网页内容
    - 🧠 使用AI提取结构化信息
    - 🔧 数据清理和验证
    - 💾 智能写入Notion数据库
    
    """
    start_time = time.time()
    url_str = str(request.url)
    
    logger.info(f"📥 收到单个URL处理请求: {url_str}")
    
    try:
        # 处理URL
        result = await process_url(url_str)
        
        processing_time = time.time() - start_time
        success = result.get("success", False)
        
        # 记录处理结果
        if success:
            logger.info(f"✅ 单个URL处理成功: {url_str} (耗时: {processing_time:.2f}s)")
        else:
            logger.warning(f"❌ 单个URL处理失败: {url_str} - {result.get('error_message', '未知错误')}")
        
        return SingleURLResponse(
            success=success,
            message="处理成功" if success else f"处理失败: {result.get('error_message', '未知错误')}",
            timestamp=time.time(),
            processing_time=processing_time,
            url=url_str,
            result=result
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_message = f"处理异常: {str(e)}"
        
        logger.error(f"❌ 单个URL处理异常: {url_str} - {error_message}")
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="ProcessingError",
                message=error_message,
                timestamp=time.time()
            ).dict()
        )


@app.post("/ingest/batch", response_model=BatchURLResponse, tags=["数据处理"])
async def ingest_batch_urls(
    request: BatchURLRequest,
    background_tasks: BackgroundTasks
):
    """
    批量处理多个URL
    
    - 📦 支持批量URL处理
    - 🔄 可配置处理间隔
    - 📊 详细的批量处理报告
    - 🛡️ 单个失败不影响其他
    
    """
    start_time = time.time()
    urls = [str(item.url) for item in request.urls]
    
    logger.info(f"📥 收到批量URL处理请求: {len(urls)} 个URL")
    
    try:
        # 设置批量处理参数
        original_delay = main_pipeline.batch_delay
        main_pipeline.batch_delay = request.batch_delay
        
        try:
            # 处理批量URL
            report = await process_urls(urls)
            
        finally:
            # 恢复原始设置
            main_pipeline.batch_delay = original_delay
        
        processing_time = time.time() - start_time
        summary = report.get("summary", {})
        success_count = summary.get("success_count", 0)
        total_count = summary.get("total_count", 0)
        
        # 记录处理结果
        logger.info(f"📊 批量URL处理完成: {success_count}/{total_count} 成功 (耗时: {processing_time:.2f}s)")
        
        return BatchURLResponse(
            success=True,
            message=f"批量处理完成，{success_count}/{total_count} 成功",
            timestamp=time.time(),
            processing_time=processing_time,
            summary=summary,
            report=report
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_message = f"批量处理异常: {str(e)}"
        
        logger.error(f"❌ 批量URL处理异常: {error_message}")
        
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="BatchProcessingError",
                message=error_message,
                timestamp=time.time()
            ).dict()
        )


@app.get("/status/pipeline", tags=["监控"])
async def pipeline_status():
    """获取处理管道状态"""
    try:
        from .notion_schema import get_database_schema
        
        schema = get_database_schema()
        
        return {
            "pipeline_ready": test_pipeline_connection(),
            "database_schema": {
                "loaded": schema is not None,
                "fields_count": len(schema.fields) if schema else 0,
                "title_field": schema.title_field_name if schema else None,
                "url_field": schema.url_field_name if schema else None
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
