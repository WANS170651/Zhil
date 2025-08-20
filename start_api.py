"""
API服务启动脚本
"""

import argparse
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.api_service import start_server


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="启动URL信息收集和存储系统API服务")
    
    parser.add_argument("--host", default="0.0.0.0", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    parser.add_argument("--reload", action="store_true", help="启用热重载（开发模式）")
    parser.add_argument("--log-level", default="info", 
                      choices=["debug", "info", "warning", "error"],
                      help="日志级别")
    
    args = parser.parse_args()
    
    print("🚀 启动URL信息收集和存储系统API服务")
    print(f"📡 服务地址: http://{args.host}:{args.port}")
    print(f"📚 API文档: http://{args.host}:{args.port}/docs")
    print(f"🔍 健康检查: http://{args.host}:{args.port}/health")
    print("-" * 50)
    
    try:
        start_server(
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level=args.log_level
        )
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
