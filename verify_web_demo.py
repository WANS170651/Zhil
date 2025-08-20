#!/usr/bin/env python3
"""
快速验证Web界面演示
检查所有必需文件是否存在，配置是否正确
"""

import os
import sys
from pathlib import Path

def check_files():
    """检查文件完整性"""
    print("📁 检查文件完整性...")
    
    required_files = [
        # Web界面文件
        "web/index.html",
        "web/static/css/style.css", 
        "web/static/js/app.js",
        
        # 启动脚本
        "start_web_demo.py",
        "test_web_interface.py",
        
        # 核心源码
        "src/api_service.py",
        "src/config.py",
        "src/main_pipeline.py",
        "src/notion_schema.py",
        "src/extractor.py",
        "src/normalizer.py",
        "src/notion_writer.py",
        
        # 配置和文档
        "requirements.txt",
        ".env",
        "WEB_INTERFACE_DEMO.md"
    ]
    
    missing_files = []
    existing_files = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            existing_files.append(file_path)
            print(f"   ✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"   ❌ {file_path} (缺失)")
    
    print(f"\n📊 文件检查结果:")
    print(f"   总文件数: {len(required_files)}")
    print(f"   存在文件: {len(existing_files)}")
    print(f"   缺失文件: {len(missing_files)}")
    
    if missing_files:
        print(f"\n⚠️ 缺失的关键文件: {missing_files}")
        return False
    else:
        print(f"\n✅ 所有必需文件都存在")
        return True

def check_web_structure():
    """检查Web目录结构"""
    print("\n🌐 检查Web目录结构...")
    
    web_dir = Path("web")
    static_dir = web_dir / "static"
    css_dir = static_dir / "css"
    js_dir = static_dir / "js"
    
    if not web_dir.exists():
        print("   ❌ web目录不存在")
        return False
    
    if not static_dir.exists():
        print("   ❌ web/static目录不存在")
        return False
        
    if not css_dir.exists():
        print("   ❌ web/static/css目录不存在")
        return False
        
    if not js_dir.exists():
        print("   ❌ web/static/js目录不存在")
        return False
    
    print("   ✅ Web目录结构正确")
    return True

def check_config():
    """检查配置文件"""
    print("\n⚙️ 检查配置文件...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("   ❌ .env文件不存在")
        print("   💡 请创建.env文件并配置以下变量:")
        print("      NOTION_TOKEN=your_notion_token")
        print("      NOTION_DATABASE_ID=your_database_id")
        print("      DASHSCOPE_API_KEY=your_api_key")
        return False
    
    # 检查.env文件内容
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_vars = ['NOTION_TOKEN', 'NOTION_DATABASE_ID', 'DASHSCOPE_API_KEY']
        missing_vars = []
        
        for var in required_vars:
            if f"{var}=" not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"   ⚠️ .env文件缺少配置: {missing_vars}")
            return False
        else:
            print("   ✅ .env文件配置完整")
            return True
            
    except Exception as e:
        print(f"   ❌ 读取.env文件失败: {e}")
        return False

def check_dependencies():
    """检查依赖包"""
    print("\n📦 检查Python依赖...")
    
    try:
        import fastapi
        print("   ✅ fastapi")
    except ImportError:
        print("   ❌ fastapi (未安装)")
        return False
    
    try:
        import uvicorn
        print("   ✅ uvicorn")
    except ImportError:
        print("   ❌ uvicorn (未安装)")
        return False
    
    try:
        import requests
        print("   ✅ requests")
    except ImportError:
        print("   ❌ requests (未安装)")
        return False
    
    try:
        import playwright
        print("   ✅ playwright")
    except ImportError:
        print("   ❌ playwright (未安装)")
        return False
    
    print("   ✅ 所有必需依赖已安装")
    return True

def show_usage_instructions():
    """显示使用说明"""
    print("\n" + "="*60)
    print("🚀 Web界面启动说明")
    print("="*60)
    print()
    print("1. 启动Web界面:")
    print("   python start_web_demo.py")
    print()
    print("2. 访问Web界面:")
    print("   http://localhost:8000/ui")
    print()
    print("3. 查看API文档:")
    print("   http://localhost:8000/docs")
    print()
    print("4. 测试Web界面:")
    print("   python test_web_interface.py")
    print()
    print("5. 查看详细说明:")
    print("   打开 WEB_INTERFACE_DEMO.md")
    print()
    print("="*60)
    print("💡 提示:")
    print("- 首次启动可能需要一些时间初始化")
    print("- 确保网络连接正常，可以访问Notion和LLM服务")
    print("- 如遇问题，请查看控制台输出和错误信息")
    print("="*60)

def main():
    """主函数"""
    print("🔍 URL信息收集和存储系统 - Web界面验证")
    print("="*60)
    
    # 执行各项检查
    checks = [
        ("文件完整性", check_files),
        ("Web目录结构", check_web_structure),
        ("配置文件", check_config),
        ("Python依赖", check_dependencies)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            print(f"   ❌ {check_name}检查异常: {e}")
            all_passed = False
    
    print("\n" + "="*60)
    print("📊 验证结果总结")
    print("="*60)
    
    if all_passed:
        print("🎉 所有检查通过！Web界面已准备就绪")
        print()
        show_usage_instructions()
        return True
    else:
        print("⚠️ 部分检查失败，请解决上述问题后重试")
        print()
        print("💡 常见解决方案:")
        print("1. 安装依赖: pip install -r requirements.txt")
        print("2. 配置环境: 创建.env文件并填入必要的API密钥")
        print("3. 检查文件: 确保所有必需文件都存在")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
