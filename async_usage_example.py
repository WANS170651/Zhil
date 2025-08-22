#!/usr/bin/env python3
"""
异步使用示例
展示如何使用重构后的异步API
"""

import asyncio
import time
import sys
import os

# 添加源码路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.main_pipeline import process_url_async, process_urls_concurrent


async def example_single_url():
    """单URL异步处理示例"""
    print("🔥 单URL异步处理示例")
    print("=" * 40)
    
    url = "https://httpbin.org/json"
    print(f"处理URL: {url}")
    
    start_time = time.time()
    
    try:
        result = await process_url_async(url)
        processing_time = time.time() - start_time
        
        print(f"✅ 处理完成，耗时: {processing_time:.2f}s")
        print(f"成功状态: {result.get('success', False)}")
        
        if result.get('success'):
            print("📊 处理详情:")
            stage_times = result.get('stage_times', {})
            for stage, time_cost in stage_times.items():
                print(f"  {stage}: {time_cost:.2f}s")
        
        return result
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return None


async def example_concurrent_batch():
    """并发批量处理示例"""
    print("\n🚀 并发批量处理示例")
    print("=" * 40)
    
    urls = [
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/2", 
        "https://httpbin.org/delay/1",
        "https://httpbin.org/json",
    ]
    
    print(f"处理URL数量: {len(urls)}")
    
    start_time = time.time()
    
    try:
        report = await process_urls_concurrent(urls)
        processing_time = time.time() - start_time
        
        print(f"✅ 批量处理完成，耗时: {processing_time:.2f}s")
        
        summary = report.get('summary', {})
        print(f"📊 处理摘要:")
        print(f"  总数: {summary.get('total_count', 0)}")
        print(f"  成功: {summary.get('success_count', 0)}")
        print(f"  失败: {summary.get('failed_count', 0)}")
        print(f"  成功率: {summary.get('success_rate', 0):.1f}%")
        print(f"  预计加速比: {summary.get('estimated_speedup', 1):.1f}x")
        
        # 显示时间统计
        timing = report.get('timing', {})
        print(f"⏱️ 时间统计:")
        print(f"  总处理时间: {timing.get('total_time', 0):.2f}s")
        print(f"  平均处理时间: {timing.get('average_time', 0):.2f}s")
        print(f"  实际墙钟时间: {timing.get('wall_clock_time', 0):.2f}s")
        
        return report
        
    except Exception as e:
        print(f"❌ 批量处理失败: {e}")
        return None


async def performance_comparison():
    """性能对比示例"""
    print("\n⚡ 性能对比示例")
    print("=" * 40)
    
    urls = [
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
        "https://httpbin.org/delay/1",
    ]
    
    print(f"测试URL数量: {len(urls)}")
    
    # 模拟顺序处理时间（实际不执行，只是估算）
    estimated_sequential_time = len(urls) * 2  # 假设每个URL顺序处理需要2秒
    print(f"预计顺序处理时间: {estimated_sequential_time}s")
    
    # 异步并发处理
    print("🚀 开始异步并发处理...")
    start_time = time.time()
    
    try:
        report = await process_urls_concurrent(urls)
        actual_time = time.time() - start_time
        
        success_count = report.get('summary', {}).get('success_count', 0)
        speedup = estimated_sequential_time / actual_time if actual_time > 0 else 1
        
        print(f"✅ 并发处理完成:")
        print(f"  实际耗时: {actual_time:.2f}s")
        print(f"  成功处理: {success_count}/{len(urls)}")
        print(f"  🚀 加速比: {speedup:.1f}x")
        print(f"  时间节省: {((estimated_sequential_time - actual_time) / estimated_sequential_time * 100):.1f}%")
        
        return speedup
        
    except Exception as e:
        print(f"❌ 性能对比失败: {e}")
        return None


async def main():
    """主演示函数"""
    print("🎯 异步API使用示例")
    print("=" * 60)
    
    # 示例1: 单URL处理
    await example_single_url()
    
    # 示例2: 并发批量处理
    await example_concurrent_batch()
    
    # 示例3: 性能对比
    speedup = await performance_comparison()
    
    # 总结
    print("\n🎉 异步API示例完成！")
    print("=" * 60)
    
    print("📈 重构收益总结:")
    print("✅ 真正的非阻塞异步处理")
    print("✅ 并发批量处理能力")
    print("✅ 智能并发控制")
    print("✅ 显著的性能提升")
    
    if speedup and speedup > 1:
        print(f"✅ 实测加速比: {speedup:.1f}x")
    
    print("\n💡 使用建议:")
    print("- 单URL处理: 使用 process_url_async()")
    print("- 批量处理: 使用 process_urls_concurrent()")
    print("- 大批量处理: 建议分批次处理，避免过度并发")
    print("- API端点: /ingest/url 和 /ingest/batch 已重构为异步")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 示例被用户中断")
    except Exception as e:
        print(f"\n❌ 示例异常: {e}")
        import traceback
        traceback.print_exc()
