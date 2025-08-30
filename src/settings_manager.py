"""
设置管理模块
处理用户设置的保存、加载和验证
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import configparser

logger = logging.getLogger(__name__)


@dataclass
class UserSettings:
    """用户设置数据类"""
    qwen_api_key: Optional[str] = None
    notion_api_key: Optional[str] = None
    notion_database_id: Optional[str] = None
    feishu_app_id: Optional[str] = None
    feishu_app_secret: Optional[str] = None
    feishu_app_token: Optional[str] = None
    feishu_table_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserSettings':
        """从字典创建实例"""
        return cls(**data)


class SettingsManager:
    """设置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化设置管理器
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认路径
        """
        if config_file is None:
            # 默认配置文件路径
            project_root = Path(__file__).parent.parent
            config_dir = project_root / "config"
            config_dir.mkdir(exist_ok=True)
            config_file = config_dir / "user_settings.ini"
        
        self.config_file = Path(config_file)
        self.config = configparser.ConfigParser()
        
        # 确保配置文件存在
        self._ensure_config_file()
    
    def _ensure_config_file(self):
        """确保配置文件存在"""
        if not self.config_file.exists():
            # 创建默认配置文件
            self.config['DEFAULT'] = {
                'qwen_api_key': '',
                'notion_api_key': '',
                'notion_database_id': '',
                'feishu_app_id': '',
                'feishu_app_secret': '',
                'feishu_app_token': '',
                'feishu_table_id': ''
            }
            self.save_settings(UserSettings())
            logger.info(f"创建默认配置文件: {self.config_file}")
    
    def load_settings(self) -> UserSettings:
        """加载用户设置"""
        try:
            if not self.config_file.exists():
                logger.warning(f"配置文件不存在: {self.config_file}")
                return UserSettings()
            
            self.config.read(self.config_file, encoding='utf-8')
            
            # 从配置文件读取设置
            settings = UserSettings(
                qwen_api_key=self.config.get('DEFAULT', 'qwen_api_key', fallback=''),
                notion_api_key=self.config.get('DEFAULT', 'notion_api_key', fallback=''),
                notion_database_id=self.config.get('DEFAULT', 'notion_database_id', fallback=''),
                feishu_app_id=self.config.get('DEFAULT', 'feishu_app_id', fallback=''),
                feishu_app_secret=self.config.get('DEFAULT', 'feishu_app_secret', fallback=''),
                feishu_app_token=self.config.get('DEFAULT', 'feishu_app_token', fallback=''),
                feishu_table_id=self.config.get('DEFAULT', 'feishu_table_id', fallback='')
            )
            
            logger.info("用户设置加载成功")
            return settings
            
        except Exception as e:
            logger.error(f"加载用户设置失败: {e}")
            return UserSettings()
    
    def save_settings(self, settings: UserSettings) -> bool:
        """保存用户设置"""
        try:
            # 确保配置目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 更新配置
            if 'DEFAULT' not in self.config:
                self.config['DEFAULT'] = {}
            
            self.config['DEFAULT']['qwen_api_key'] = settings.qwen_api_key or ''
            self.config['DEFAULT']['notion_api_key'] = settings.notion_api_key or ''
            self.config['DEFAULT']['notion_database_id'] = settings.notion_database_id or ''
            self.config['DEFAULT']['feishu_app_id'] = settings.feishu_app_id or ''
            self.config['DEFAULT']['feishu_app_secret'] = settings.feishu_app_secret or ''
            self.config['DEFAULT']['feishu_app_token'] = settings.feishu_app_token or ''
            self.config['DEFAULT']['feishu_table_id'] = settings.feishu_table_id or ''
            
            # 写入文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            
            logger.info(f"用户设置保存成功: {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存用户设置失败: {e}")
            return False
    
    def update_settings(self, updates: Dict[str, Any]) -> UserSettings:
        """更新部分设置"""
        try:
            # 加载当前设置
            current_settings = self.load_settings()
            
            # 应用更新
            if 'qwen_api_key' in updates:
                current_settings.qwen_api_key = updates['qwen_api_key']
            if 'notion_api_key' in updates:
                current_settings.notion_api_key = updates['notion_api_key']
            if 'notion_database_id' in updates:
                current_settings.notion_database_id = updates['notion_database_id']
            if 'feishu_app_id' in updates:
                current_settings.feishu_app_id = updates['feishu_app_id']
            if 'feishu_app_secret' in updates:
                current_settings.feishu_app_secret = updates['feishu_app_secret']
            if 'feishu_app_token' in updates:
                current_settings.feishu_app_token = updates['feishu_app_token']
            if 'feishu_table_id' in updates:
                current_settings.feishu_table_id = updates['feishu_table_id']
            
            # 保存更新后的设置
            if self.save_settings(current_settings):
                logger.info("设置更新成功")
                return current_settings
            else:
                raise Exception("保存设置失败")
                
        except Exception as e:
            logger.error(f"更新设置失败: {e}")
            raise
    
    def get_effective_settings(self) -> UserSettings:
        """获取有效设置（用户设置优先，环境变量作为后备）"""
        user_settings = self.load_settings()
        
        # 如果用户设置为空，使用环境变量
        effective_settings = UserSettings(
            qwen_api_key=user_settings.qwen_api_key or os.getenv('DASHSCOPE_API_KEY'),
            notion_api_key=user_settings.notion_api_key or os.getenv('NOTION_TOKEN'),
            notion_database_id=user_settings.notion_database_id or os.getenv('NOTION_DATABASE_ID'),
            feishu_app_id=user_settings.feishu_app_id or os.getenv('FEISHU_APP_ID'),
            feishu_app_secret=user_settings.feishu_app_secret or os.getenv('FEISHU_APP_SECRET'),
            feishu_app_token=user_settings.feishu_app_token or os.getenv('FEISHU_APP_TOKEN'),
            feishu_table_id=user_settings.feishu_table_id or os.getenv('FEISHU_TABLE_ID')
        )
        
        return effective_settings
    
    def validate_settings(self, settings: UserSettings) -> Dict[str, bool]:
        """验证设置"""
        validation_results = {
            'qwen_api_key': bool(settings.qwen_api_key and len(settings.qwen_api_key) > 10),
            'notion_api_key': bool(settings.notion_api_key and len(settings.notion_api_key) > 10),
            'notion_database_id': bool(settings.notion_database_id and len(settings.notion_database_id) > 10),
            'feishu_app_id': bool(settings.feishu_app_id and len(settings.feishu_app_id) > 10),
            'feishu_app_secret': bool(settings.feishu_app_secret and len(settings.feishu_app_secret) > 10),
            'feishu_app_token': bool(settings.feishu_app_token and len(settings.feishu_app_token) > 10),
            'feishu_table_id': bool(settings.feishu_table_id and len(settings.feishu_table_id) > 10)
        }
        
        return validation_results


# 全局设置管理器实例
settings_manager = SettingsManager()
