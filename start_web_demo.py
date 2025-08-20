#!/usr/bin/env python3
"""
URL信息收集和存储系统 - Web界面演示启动脚本
提供完整的Web界面和API服务
"""

import os
import sys
import time
import webbrowser
import subprocess
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ 错误: 需要Python 3.8或更高版本")
        return False
    
    print(f"✅ Python版本: {sys.version}")
    
    # 检查项目结构
    required_files = [
        "src/api_service.py",
        "src/config.py",
        "web/index.html",
        "web/static/css/style.css",
        "web/static/js/app.js"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not (project_root / file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ 缺少必需文件: {missing_files}")
        return False
    
    print("✅ 项目结构完整")
    
    # 检查环境变量
    env_file = project_root / ".env"
    if not env_file.exists():
        print("⚠️ 警告: 未找到.env文件")
        print("   请确保配置了必要的环境变量:")
        print("   - NOTION_TOKEN")
        print("   - NOTION_DATABASE_ID") 
        print("   - DASHSCOPE_API_KEY")
        return False
    
    print("✅ 环境配置文件存在")
    return True

def install_dependencies():
    """安装依赖（如果需要）"""
    print("📦 检查依赖...")
    
    try:
        import fastapi
        import uvicorn
        import requests
        import playwright
        print("✅ 核心依赖已安装")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("💡 运行以下命令安装依赖:")
        print("   pip install -r requirements.txt")
        return False

def test_api_connection():
    """测试API连接"""
    print("🔗 测试API连接...")
    
    try:
        # 导入并测试配置
        from src.config import config
        config.validate()
        print("✅ 配置验证通过")
        
        # 测试组件连接
        from src.main_pipeline import test_pipeline_connection
        if test_pipeline_connection():
            print("✅ 所有组件连接正常")
            return True
        else:
            print("⚠️ 部分组件连接失败，服务可能不稳定")
            return True  # 仍然允许启动，但给出警告
            
    except Exception as e:
        print(f"❌ API连接测试失败: {e}")
        return False

def start_web_server(host="127.0.0.1", port=8000, auto_open=True):
    """启动Web服务器"""
    print(f"🚀 启动Web服务器 http://{host}:{port}")
    
    try:
        # 导入FastAPI应用
        from src.api_service import app
        
        # 启动信息
        print("=" * 60)
        print("🌐 URL信息收集和存储系统 - Web界面演示")
        print("=" * 60)
        print(f"📱 Web界面: http://{host}:{port}/ui")
        print(f"📚 API文档: http://{host}:{port}/docs")
        print(f"❤️ 健康检查: http://{host}:{port}/health")
        print(f"🔧 系统配置: http://{host}:{port}/config")
        print("=" * 60)
        print("💡 使用说明:")
        print("1. 打开Web界面进行交互操作")
        print("2. 输入URL，系统将自动提取信息并存储到Notion")
        print("3. 支持单个URL和批量URL处理")
        print("4. 查看处理历史和系统状态")
        print("5. 按 Ctrl+C 停止服务")
        print("=" * 60)
        
        # 自动打开浏览器
        if auto_open:
            def open_browser():
                time.sleep(2)  # 等待服务启动
                try:
                    webbrowser.open(f"http://{host}:{port}/ui")
                    print(f"🌍 已自动打开浏览器: http://{host}:{port}/ui")
                except:
                    print(f"💡 请手动打开浏览器访问: http://{host}:{port}/ui")
            
            import threading
            threading.Thread(target=open_browser, daemon=True).start()
        
        # 启动Uvicorn服务器
        import uvicorn
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            reload=False  # 生产模式，不启用热重载
        )
        
    except KeyboardInterrupt:
        print("\n👋 用户中断，正在停止服务...")
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print("🎯 URL信息收集和存储系统 - Web界面演示启动器")
    print("=" * 60)
    
    # 环境检查
    if not check_environment():
        print("\n❌ 环境检查失败，请解决上述问题后重试")
        return False
    
    # 依赖检查
    if not install_dependencies():
        print("\n❌ 依赖检查失败，请安装必要的依赖")
        return False
    
    # API连接测试
    if not test_api_connection():
        print("\n❌ API连接测试失败，请检查配置")
        return False
    
    print("\n✅ 所有检查通过，准备启动Web服务...")
    print()
    
    # 启动Web服务器
    try:
        # 解析命令行参数
        import argparse
        parser = argparse.ArgumentParser(description="启动Web界面演示")
        parser.add_argument("--host", default="127.0.0.1", help="服务器地址")
        parser.add_argument("--port", type=int, default=8000, help="服务器端口")
        parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
        
        args = parser.parse_args()
        
        return start_web_server(
            host=args.host,
            port=args.port,
            auto_open=not args.no_browser
        )
        
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        return False

if __name__ == "__main__":
    success = main()
    
    if not success:
        print("\n⚠️ 启动失败，请检查错误信息并重试")
        sys.exit(1)
    else:
        print("\n👋 服务已停止，感谢使用！")
        sys.exit(0)
