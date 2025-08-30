"""
配置管理模块
处理环境变量加载、配置验证和默认值设置
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class Config:
    """应用配置类"""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        初始化配置
        
        Args:
            env_file: .env文件路径，如果为None则自动查找
        """
        # 自动查找.env文件
        if env_file is None:
            env_file = self._find_env_file()
        
        if env_file and Path(env_file).exists():
            load_dotenv(dotenv_path=env_file)
            print(f"✅ 已加载配置文件: {env_file}")
        else:
            print("⚠️  未找到.env文件，将使用环境变量")
    
    def _find_env_file(self) -> Optional[str]:
        """自动查找.env文件"""
        # 当前目录
        current_dir = Path.cwd()
        
        # 可能的路径列表
        possible_paths = [
            current_dir / ".env",                    # 项目根目录
            current_dir.parent / ".env",             # 上级目录
            Path(__file__).parent.parent / ".env",   # 代码文件的上级目录
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        return None
    
    # Notion配置
    @property
    def notion_token(self) -> str:
        # 优先使用用户设置，然后使用环境变量
        try:
            from .settings_manager import settings_manager
            effective_settings = settings_manager.get_effective_settings()
            if effective_settings.notion_api_key:
                return effective_settings.notion_api_key
        except Exception:
            pass
        
        token = os.getenv("NOTION_TOKEN")
        if not token:
            raise ValueError("NOTION_TOKEN环境变量未设置")
        return token
    
    @property
    def notion_database_id(self) -> str:
        # 优先使用用户设置，然后使用环境变量
        try:
            from .settings_manager import settings_manager
            effective_settings = settings_manager.get_effective_settings()
            if effective_settings.notion_database_id:
                return effective_settings.notion_database_id
        except Exception:
            pass
        
        db_id = os.getenv("NOTION_DATABASE_ID")
        if not db_id:
            raise ValueError("NOTION_DATABASE_ID环境变量未设置")
        return db_id
    
    @property
    def notion_version(self) -> str:
        return os.getenv("NOTION_VERSION", "2022-06-28")
    
    # LLM配置
    @property
    def dashscope_api_key(self) -> str:
        # 优先使用用户设置，然后使用环境变量
        try:
            from .settings_manager import settings_manager
            effective_settings = settings_manager.get_effective_settings()
            if effective_settings.qwen_api_key:
                return effective_settings.qwen_api_key
        except Exception:
            pass
        
        key = os.getenv("DASHSCOPE_API_KEY")
        if not key:
            raise ValueError("DASHSCOPE_API_KEY环境变量未设置")
        return key
    
    @property
    def llm_model(self) -> str:
        return os.getenv("LLM_MODEL", "qwen-flash")
    
    @property
    def llm_base_url(self) -> str:
        return os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    
    # 飞书配置
    @property
    def feishu_app_id(self) -> str:
        # 优先使用用户设置，然后使用环境变量
        try:
            from .settings_manager import settings_manager
            effective_settings = settings_manager.get_effective_settings()
            if effective_settings.feishu_app_id:
                return effective_settings.feishu_app_id
        except Exception:
            pass
        
        app_id = os.getenv("FEISHU_APP_ID")
        if not app_id:
            raise ValueError("FEISHU_APP_ID环境变量未设置")
        return app_id
    
    @property
    def feishu_app_secret(self) -> str:
        # 优先使用用户设置，然后使用环境变量
        try:
            from .settings_manager import settings_manager
            effective_settings = settings_manager.get_effective_settings()
            if effective_settings.feishu_app_secret:
                return effective_settings.feishu_app_secret
        except Exception:
            pass
        
        app_secret = os.getenv("FEISHU_APP_SECRET")
        if not app_secret:
            raise ValueError("FEISHU_APP_SECRET环境变量未设置")
        return app_secret
    
    @property
    def feishu_app_token(self) -> str:
        # 优先使用用户设置，然后使用环境变量
        try:
            from .settings_manager import settings_manager
            effective_settings = settings_manager.get_effective_settings()
            if effective_settings.feishu_app_token:
                return effective_settings.feishu_app_token
        except Exception:
            pass
        
        app_token = os.getenv("FEISHU_APP_TOKEN")
        if not app_token:
            raise ValueError("FEISHU_APP_TOKEN环境变量未设置")
        return app_token
    
    @property
    def feishu_table_id(self) -> str:
        # 优先使用用户设置，然后使用环境变量
        try:
            from .settings_manager import settings_manager
            effective_settings = settings_manager.get_effective_settings()
            if effective_settings.feishu_table_id:
                return effective_settings.feishu_table_id
        except Exception:
            pass
        
        table_id = os.getenv("FEISHU_TABLE_ID")
        if not table_id:
            raise ValueError("FEISHU_TABLE_ID环境变量未设置")
        return table_id
    
    # 缓存配置
    @property
    def schema_cache_ttl(self) -> int:
        """Schema缓存TTL（秒），默认30分钟"""
        return int(os.getenv("SCHEMA_CACHE_TTL", "1800"))
    
    @property
    def schema_cache_maxsize(self) -> int:
        """Schema缓存最大条目数"""
        return int(os.getenv("SCHEMA_CACHE_MAXSIZE", "100"))
    
    # 数据处理配置
    @property
    def fuzzy_match_threshold(self) -> int:
        """模糊匹配阈值"""
        return int(os.getenv("FUZZY_MATCH_THRESHOLD", "70"))
    
    # 爬虫配置
    @property
    def scraper_headless(self) -> bool:
        """爬虫是否无头模式"""
        return os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"
    
    @property
    def scraper_wait_time(self) -> int:
        """爬虫等待时间（秒）"""
        return int(os.getenv("SCRAPER_WAIT_TIME", "2"))
    
    # 重试配置
    @property
    def max_retries(self) -> int:
        """最大重试次数"""
        return int(os.getenv("MAX_RETRIES", "3"))
    
    @property
    def retry_delay(self) -> float:
        """重试延迟（秒）"""
        return float(os.getenv("RETRY_DELAY", "1.0"))
    
    # 日志配置
    @property
    def log_level(self) -> str:
        """日志级别"""
        return os.getenv("LOG_LEVEL", "INFO").upper()
    
    def validate(self) -> bool:
        """验证配置完整性"""
        try:
            # 检查必需的配置项
            _ = self.notion_token
            _ = self.notion_database_id
            _ = self.dashscope_api_key
            
            print("✅ 配置验证通过")
            return True
            
        except ValueError as e:
            print(f"❌ 配置验证失败: {e}")
            return False


# 全局配置实例
config = Config()
