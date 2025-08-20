"""
主流程模块演示脚本
展示完整的URL→Notion处理管道
"""

import sys
import os
import asyncio
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main_pipeline import main_pipeline, process_url, process_urls, test_pipeline_connection
from src.main_pipeline import ProcessingStatus, ProcessingStage


async def demo_single_url():
    """演示单个URL的完整处理流程"""
    print("🚀 单个URL处理演示")
    print("="*50)
    
    # 使用快手校招的真实URL
    demo_url = "https://campus.kuaishou.cn/recruit/campus/e/#/campus/job-info/9822"
    
    print(f"📋 目标URL: {demo_url}")
    print(f"🎯 处理流程: 爬取 → LLM提取 → 数据清理 → Notion写入")
    print(f"⏱️ 开始处理...\n")
    
    start_time = time.time()
    
    # 使用主流程处理URL
    result = await main_pipeline.process_single_url(demo_url)
    
    total_time = time.time() - start_time
    
    print(f"\n📊 处理结果总结:")
    print(f"="*40)
    print(f"URL: {result.url}")
    print(f"状态: {'✅ 成功' if result.success else '❌ 失败'}")
    print(f"最终阶段: {result.stage.value}")
    print(f"总耗时: {total_time:.2f}秒")
    
    if result.stage_times:
        print(f"\n⏱️ 各阶段耗时:")
        for stage, duration in result.stage_times.items():
            print(f"  {stage}: {duration:.2f}s")
    
    if result.success and result.writing_result:
        print(f"\n💾 Notion写入结果:")
        print(f"  操作类型: {result.writing_result.operation.value}")
        print(f"  页面ID: {result.writing_result.page_id}")
        if result.writing_result.url:
            print(f"  URL: {result.writing_result.url}")
    
    if result.error_message:
        print(f"\n❌ 错误信息:")
        print(f"  阶段: {result.error_stage.value if result.error_stage else '未知'}")
        print(f"  错误: {result.error_message}")
    
    return result.success


async def demo_batch_processing():
    """演示批量URL处理"""
    print("\n\n📦 批量URL处理演示")
    print("="*50)
    
    # 使用一些测试URL（混合真实和测试URL）
    test_urls = [
        "https://www.example.com/demo1",  # 简单测试页面
        "https://campus.kuaishou.cn/recruit/campus/e/#/campus/job-info/9822",  # 真实招聘页面
        "https://www.example.com/demo2"   # 另一个简单测试页面
    ]
    
    print(f"📋 处理URL列表:")
    for i, url in enumerate(test_urls, 1):
        print(f"  {i}. {url}")
    
    print(f"\n🚀 开始批量处理...\n")
    
    start_time = time.time()
    
    # 使用便捷函数进行批量处理
    report = await process_urls(test_urls)
    
    total_time = time.time() - start_time
    
    print(f"\n📊 批量处理报告:")
    print(f"="*40)
    
    summary = report.get("summary", {})
    print(f"总数: {summary.get('total_count', 0)}")
    print(f"成功: {summary.get('success_count', 0)}")
    print(f"失败: {summary.get('failed_count', 0)}")
    print(f"成功率: {summary.get('success_rate', 0):.1f}%")
    
    timing = report.get("timing", {})
    print(f"总耗时: {timing.get('total_time', 0):.2f}s")
    print(f"平均耗时: {timing.get('average_time', 0):.2f}s/个")
    
    operations = report.get("operations", {})
    if operations.get('create_count', 0) > 0 or operations.get('update_count', 0) > 0:
        print(f"\n💾 Notion操作:")
        print(f"  创建: {operations.get('create_count', 0)}")
        print(f"  更新: {operations.get('update_count', 0)}")
    
    errors = report.get("errors", {})
    if errors.get("failed_urls"):
        print(f"\n❌ 失败的URL:")
        for url in errors["failed_urls"]:
            print(f"  - {url}")
    
    return summary.get('success_count', 0) > 0


async def demo_error_handling():
    """演示错误处理能力"""
    print("\n\n🛡️ 错误处理演示")
    print("="*50)
    
    # 各种错误情况
    error_cases = [
        ("空URL", ""),
        ("无效格式", "not-a-valid-url"),
        ("不存在的域名", "https://nonexistent-12345.com/test"),
        ("无效协议", "ftp://example.com/test")
    ]
    
    print("测试各种错误情况的处理:")
    
    for case_name, test_url in error_cases:
        print(f"\n🧪 测试: {case_name}")
        print(f"   URL: {test_url or '(空)'}")
        
        try:
            result = await main_pipeline.process_single_url(test_url)
            
            if result.success:
                print(f"   ⚠️ 意外成功（应该失败）")
            else:
                print(f"   ✅ 正确失败")
                print(f"   错误阶段: {result.error_stage.value if result.error_stage else '未知'}")
                print(f"   错误信息: {result.error_message}")
        except Exception as e:
            print(f"   ✅ 异常处理正确: {e}")
    
    return True


async def demo_real_world_scenario():
    """演示真实世界应用场景"""
    print("\n\n🌍 真实应用场景演示")
    print("="*50)
    
    print("📖 场景描述:")
    print("某求职者使用我们的系统收集和管理招聘信息。")
    print("系统会自动从各种招聘网站抓取职位信息，")
    print("使用AI提取结构化数据，并存储到Notion数据库中。")
    
    # 模拟用户提供的招聘URL
    job_urls = [
        "https://campus.kuaishou.cn/recruit/campus/e/#/campus/job-info/9822"  # 快手数据分析师
    ]
    
    print(f"\n🎯 用户需求:")
    print(f"  - 自动提取职位信息")
    print(f"  - 结构化存储到数据库")
    print(f"  - 支持去重和更新")
    print(f"  - 提供详细的处理报告")
    
    print(f"\n🚀 开始处理招聘信息...")
    
    all_success = True
    for i, url in enumerate(job_urls, 1):
        print(f"\n📋 处理第 {i}/{len(job_urls)} 个职位...")
        print(f"   URL: {url}")
        
        result = await main_pipeline.process_single_url(url)
        
        if result.success:
            print(f"   ✅ 处理成功")
            if result.writing_result:
                op_type = "创建" if result.writing_result.operation.name == "CREATE" else "更新"
                print(f"   💾 {op_type}了Notion记录")
                print(f"   📄 页面ID: {result.writing_result.page_id}")
        else:
            print(f"   ❌ 处理失败: {result.error_message}")
            all_success = False
    
    if all_success:
        print(f"\n🎉 所有职位处理完成！")
        print(f"✨ 用户现在可以在Notion中查看和管理这些职位信息了。")
    else:
        print(f"\n⚠️ 部分职位处理失败，但系统能够优雅处理错误。")
    
    return all_success


async def main():
    """主演示函数"""
    print("🎯 URL信息收集和存储系统 - 完整演示")
    print("="*60)
    
    # 测试管道连接
    print("🔗 测试系统连接...")
    if not test_pipeline_connection():
        print("❌ 系统连接失败，无法继续演示")
        return
    
    print("✅ 系统连接正常，开始演示...\n")
    
    demos = [
        ("单个URL处理", demo_single_url),
        ("批量URL处理", demo_batch_processing),
        ("错误处理能力", demo_error_handling),
        ("真实应用场景", demo_real_world_scenario)
    ]
    
    demo_results = []
    
    for demo_name, demo_func in demos:
        try:
            print(f"🎬 {demo_name} 演示")
            result = await demo_func()
            demo_results.append((demo_name, result))
        except Exception as e:
            print(f"❌ {demo_name} 演示异常: {e}")
            demo_results.append((demo_name, False))
    
    # 总结
    print("\n" + "="*60)
    print("📊 演示总结")
    print("="*60)
    
    success_count = sum(1 for _, success in demo_results if success)
    total_count = len(demo_results)
    
    for demo_name, success in demo_results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{demo_name}: {status}")
    
    print(f"\n🎯 总体成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("\n🎉 所有演示成功！系统运行完美！")
        print("🚀 URL信息收集和存储系统已准备就绪，可以投入使用！")
    elif success_count >= total_count * 0.5:
        print("\n✅ 大部分演示成功！系统基本正常运行！")
        print("💡 部分失败可能是由于网络连接或特定URL问题。")
    else:
        print("\n⚠️ 演示结果不理想，请检查系统配置和网络连接。")
    
    print("\n🔑 系统核心特性:")
    print("  ✅ 智能网页爬取 - 支持SPA页面")
    print("  ✅ AI驱动提取 - 自动识别招聘信息")
    print("  ✅ 数据智能清理 - 自动格式化和验证")
    print("  ✅ 智能去重写入 - 避免重复记录")
    print("  ✅ 完善错误处理 - 优雅处理各种异常")
    print("  ✅ 详细处理报告 - 完整的操作记录")


if __name__ == "__main__":
    asyncio.run(main())
