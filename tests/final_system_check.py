"""
系统最终验证脚本
快速检查整个系统的就绪状态
"""

import sys
import os
import asyncio
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import config
from src.notion_schema import get_database_schema
from src.extractor import extractor
from src.notion_writer import notion_writer
from src.main_pipeline import test_pipeline_connection


def check_project_structure():
    """检查项目结构完整性"""
    print("📁 检查项目结构...")
    
    required_files = [
        "src/config.py",
        "src/notion_schema.py", 
        "src/llm_schema_builder.py",
        "src/extractor.py",
        "src/normalizer.py",
        "src/notion_writer.py",
        "src/main_pipeline.py",
        "src/api_service.py",
        "start_api.py",
        "requirements.txt",
        "PROJECT_DELIVERY_SUMMARY.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"   ❌ 缺少文件: {missing_files}")
        return False
    else:
        print(f"   ✅ 所有核心文件存在 ({len(required_files)} 个)")
        return True


def check_configuration():
    """检查配置完整性"""
    print("⚙️ 检查系统配置...")
    
    try:
        if config.validate():
            print("   ✅ 配置验证通过")
            return True
        else:
            print("   ❌ 配置验证失败")
            return False
    except Exception as e:
        print(f"   ❌ 配置检查异常: {e}")
        return False


def check_core_modules():
    """检查核心模块"""
    print("🔧 检查核心模块...")
    
    modules_status = {}
    
    # 检查Schema模块
    try:
        schema = get_database_schema()
        modules_status["schema"] = schema is not None
    except:
        modules_status["schema"] = False
    
    # 检查LLM模块
    try:
        modules_status["llm"] = extractor.test_connection()
    except:
        modules_status["llm"] = False
    
    # 检查Notion模块
    try:
        modules_status["notion"] = notion_writer.test_connection()
    except:
        modules_status["notion"] = False
    
    # 检查管道模块
    try:
        modules_status["pipeline"] = test_pipeline_connection()
    except:
        modules_status["pipeline"] = False
    
    all_ok = all(modules_status.values())
    
    for module, status in modules_status.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {module}: {'正常' if status else '异常'}")
    
    return all_ok


def check_test_results():
    """检查测试结果"""
    print("🧪 检查测试结果...")
    
    report_file = Path("tests/e2e_test_report.json")
    
    if not report_file.exists():
        print("   ❌ 测试报告不存在")
        return False
    
    try:
        import json
        with open(report_file, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        success_rate = report.get("success_rate", 0)
        total_tests = report.get("total_tests", 0)
        passed_tests = report.get("passed_tests", 0)
        
        print(f"   📊 测试通过率: {success_rate}%")
        print(f"   📋 测试详情: {passed_tests}/{total_tests} 通过")
        
        if success_rate >= 80:
            print("   ✅ 测试结果达标")
            return True
        else:
            print("   ⚠️ 测试结果不达标")
            return False
            
    except Exception as e:
        print(f"   ❌ 测试报告解析失败: {e}")
        return False


def generate_system_status():
    """生成系统状态报告"""
    print("\n" + "="*60)
    print("📋 系统最终状态报告")
    print("="*60)
    
    checks = [
        ("项目结构", check_project_structure),
        ("系统配置", check_configuration), 
        ("核心模块", check_core_modules),
        ("测试结果", check_test_results)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} 检查异常: {e}")
            results.append((check_name, False))
        print()
    
    # 汇总结果
    passed_checks = sum(1 for _, success in results if success)
    total_checks = len(results)
    success_rate = (passed_checks / total_checks) * 100
    
    print("📊 检查汇总:")
    for check_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {status} {check_name}")
    
    print(f"\n🎯 总体状态:")
    print(f"  检查通过率: {success_rate:.1f}% ({passed_checks}/{total_checks})")
    
    if success_rate >= 100:
        print("  🎉 系统完全就绪！")
        system_status = "完全就绪"
    elif success_rate >= 80:
        print("  ✅ 系统基本就绪！")
        system_status = "基本就绪"
    else:
        print("  ⚠️ 系统存在问题，需要修复")
        system_status = "需要修复"
    
    # 保存状态报告
    try:
        status_report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system_status": system_status,
            "success_rate": success_rate,
            "checks": [
                {"name": name, "passed": success}
                for name, success in results
            ]
        }
        
        with open("SYSTEM_STATUS.json", 'w', encoding='utf-8') as f:
            import json
            json.dump(status_report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 系统状态已保存到: SYSTEM_STATUS.json")
        
    except Exception as e:
        print(f"⚠️ 保存状态报告失败: {e}")
    
    print("\n" + "="*60)
    print("🚀 URL信息收集和存储系统 - 系统验证完成")
    print("="*60)
    
    return success_rate >= 80


def main():
    """主函数"""
    print("🔍 URL信息收集和存储系统 - 最终状态验证")
    print("检查系统各组件的就绪状态")
    print("-" * 60)
    
    try:
        system_ready = generate_system_status()
        
        if system_ready:
            print("\n🎉 恭喜！系统已准备好投入生产使用！")
            return True
        else:
            print("\n⚠️ 系统存在问题，请检查并修复后重新验证")
            return False
            
    except Exception as e:
        print(f"\n❌ 系统验证过程异常: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
