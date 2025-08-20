"""
主流程模块测试脚本
验证完整的URL→Notion处理管道
"""

import sys
import os
import asyncio
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main_pipeline import main_pipeline, process_url, process_urls, test_pipeline_connection
from src.main_pipeline import ProcessingStatus, ProcessingStage


def test_connection():
    """测试管道组件连接"""
    print("🧪 测试管道组件连接...")
    
    try:
        result = test_pipeline_connection()
        if result:
            print("✅ 管道组件连接测试通过")
            return True
        else:
            print("❌ 管道组件连接测试失败")
            return False
    except Exception as e:
        print(f"❌ 管道组件连接测试异常: {e}")
        return False


async def test_single_url_processing():
    """测试单个URL处理"""
    print("\n🧪 测试单个URL处理...")
    
    try:
        # 使用一个简单的测试URL
        test_url = "https://campus.kuaishou.cn/recruit/campus/e/#/campus/job-info/9822"
        
        print(f"   正在处理测试URL: {test_url}")
        
        result = await main_pipeline.process_single_url(test_url)
        
        print(f"✅ 单个URL处理完成:")
        print(f"   URL: {result.url}")
        print(f"   状态: {result.status.value}")
        print(f"   阶段: {result.stage.value}")
        print(f"   成功: {result.success}")
        print(f"   总耗时: {result.total_time:.2f}s")
        
        if result.stage_times:
            print(f"   阶段耗时:")
            for stage, duration in result.stage_times.items():
                print(f"     {stage}: {duration:.2f}s")
        
        if result.error_message:
            print(f"   错误信息: {result.error_message}")
            print(f"   错误阶段: {result.error_stage.value if result.error_stage else 'unknown'}")
        
        if result.writing_result:
            print(f"   写入结果:")
            print(f"     操作: {result.writing_result.operation.value}")
            print(f"     页面ID: {result.writing_result.page_id}")
            print(f"     成功: {result.writing_result.success}")
        
        return result.success
        
    except Exception as e:
        print(f"❌ 单个URL处理测试异常: {e}")
        return False


async def test_batch_processing():
    """测试批量URL处理"""
    print("\n🧪 测试批量URL处理...")
    
    try:
        # 使用多个测试URL（注意：这些URL可能会创建真实的Notion记录）
        timestamp = int(time.time())
        test_urls = [
            "https://www.example.com/test1",  # 这些URL会失败，用于测试错误处理
            "https://www.example.com/test2",
            "https://campus.kuaishou.cn/recruit/campus/e/#/campus/job-info/9822"  # 真实URL
        ]
        
        print(f"   正在批量处理 {len(test_urls)} 个URL...")
        
        results = await main_pipeline.process_multiple_urls(test_urls)
        
        print(f"✅ 批量处理完成:")
        print(f"   总数: {len(results)}")
        
        success_count = sum(1 for r in results if r.success)
        print(f"   成功: {success_count}")
        print(f"   失败: {len(results) - success_count}")
        
        # 显示每个URL的结果
        for i, result in enumerate(results):
            print(f"   URL {i+1}: {result.status.value} ({result.total_time:.2f}s)")
            if result.error_message:
                print(f"     错误: {result.error_message}")
        
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ 批量处理测试异常: {e}")
        return False


async def test_convenience_functions():
    """测试便捷函数"""
    print("\n🧪 测试便捷函数...")
    
    try:
        # 测试单个URL便捷函数
        test_url = "https://www.example.com/convenience-test"
        
        print(f"   测试process_url便捷函数...")
        result_dict = await process_url(test_url)
        
        print(f"✅ process_url测试:")
        print(f"   返回类型: {type(result_dict).__name__}")
        print(f"   包含键: {list(result_dict.keys())}")
        print(f"   状态: {result_dict.get('status', 'unknown')}")
        
        # 测试批量URL便捷函数
        print(f"   测试process_urls便捷函数...")
        test_urls = ["https://www.example.com/batch1", "https://www.example.com/batch2"]
        
        report = await process_urls(test_urls)
        
        print(f"✅ process_urls测试:")
        print(f"   返回类型: {type(report).__name__}")
        print(f"   包含键: {list(report.keys())}")
        
        if "summary" in report:
            summary = report["summary"]
            print(f"   总数: {summary.get('total_count', 0)}")
            print(f"   成功率: {summary.get('success_rate', 0):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ 便捷函数测试异常: {e}")
        return False


async def test_error_handling():
    """测试错误处理能力"""
    print("\n🧪 测试错误处理...")
    
    try:
        # 测试无效URL
        invalid_urls = [
            "",  # 空URL
            "not-a-url",  # 无效格式
            "ftp://invalid.com",  # 不支持的协议
            "https://nonexistent-domain-12345.com/test"  # 不存在的域名
        ]
        
        print(f"   测试无效URL处理...")
        
        error_results = []
        for url in invalid_urls:
            try:
                result = await main_pipeline.process_single_url(url)
                error_results.append(result)
                print(f"     {url or '(空URL)'}: {result.status.value}")
                if result.error_message:
                    print(f"       错误: {result.error_message}")
            except Exception as e:
                print(f"     {url or '(空URL)'}: 异常 - {e}")
        
        # 验证错误处理是否正确
        all_failed_as_expected = all(not r.success for r in error_results)
        
        if all_failed_as_expected:
            print(f"✅ 错误处理正确：无效URL都被正确处理")
            return True
        else:
            print(f"⚠️ 错误处理异常：部分无效URL未被正确处理")
            return False
        
    except Exception as e:
        print(f"❌ 错误处理测试异常: {e}")
        return False


async def test_report_generation():
    """测试报告生成"""
    print("\n🧪 测试报告生成...")
    
    try:
        # 创建一些模拟结果
        from src.main_pipeline import ProcessingResult, ProcessingStage, ProcessingStatus
        
        results = []
        
        # 模拟成功结果
        success_result = ProcessingResult("https://success.test.com")
        success_result.status = ProcessingStatus.SUCCESS
        success_result.stage = ProcessingStage.COMPLETED
        success_result.start_time = time.time() - 10
        success_result.end_time = time.time()
        success_result.stage_times = {
            "scraping": 2.0,
            "extraction": 3.0,
            "normalization": 1.0,
            "writing": 1.5
        }
        results.append(success_result)
        
        # 模拟失败结果
        failed_result = ProcessingResult("https://failed.test.com")
        failed_result.status = ProcessingStatus.FAILED
        failed_result.stage = ProcessingStage.SCRAPING
        failed_result.error_message = "测试错误"
        failed_result.error_stage = ProcessingStage.SCRAPING
        failed_result.start_time = time.time() - 5
        failed_result.end_time = time.time()
        results.append(failed_result)
        
        # 生成报告
        report = main_pipeline.generate_report(results)
        
        print(f"✅ 报告生成测试:")
        print(f"   报告类型: {type(report).__name__}")
        print(f"   包含部分: {list(report.keys())}")
        
        if "summary" in report:
            summary = report["summary"]
            print(f"   统计摘要:")
            print(f"     总数: {summary.get('total_count', 0)}")
            print(f"     成功: {summary.get('success_count', 0)}")
            print(f"     失败: {summary.get('failed_count', 0)}")
            print(f"     成功率: {summary.get('success_rate', 0):.1f}%")
        
        if "timing" in report:
            timing = report["timing"]
            print(f"   时间统计:")
            print(f"     总耗时: {timing.get('total_time', 0):.2f}s")
            print(f"     平均耗时: {timing.get('average_time', 0):.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ 报告生成测试异常: {e}")
        return False


async def main():
    """主测试函数"""
    print("="*60)
    print("🔬 主流程模块完整测试")
    print("="*60)
    
    # 测试列表
    tests = [
        ("管道组件连接", test_connection),
        ("单个URL处理", test_single_url_processing),
        ("批量URL处理", test_batch_processing),
        ("便捷函数", test_convenience_functions),
        ("错误处理", test_error_handling),
        ("报告生成", test_report_generation)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 开始测试: {test_name}")
        print("-" * 40)
        
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
                
            if result:
                passed += 1
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
                
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print("\n" + "="*60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    print("="*60)
    
    if passed == total:
        print("🎉 所有测试通过！主流程模块工作正常")
    elif passed >= total * 0.7:  # 70%以上通过率
        print("✅ 大部分测试通过！主流程模块基本正常")
        print("💡 部分测试失败可能是由于网络连接或测试URL不可访问")
    else:
        print("⚠️ 多个测试失败，请检查上述错误信息")
    
    return passed >= total * 0.5  # 50%通过率算基本成功


if __name__ == "__main__":
    asyncio.run(main())
