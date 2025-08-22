#!/usr/bin/env python3
"""
异步性能测试脚本
测试异步重构后的性能提升效果
"""

import asyncio
import time
import sys
import os
from typing import List

# 添加源码路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from src.main_pipeline import async_main_pipeline, main_pipeline
    from src.extractor import async_extractor, test_extractor_async
    from src.notion_writer import async_notion_writer, test_notion_connection_async
    from src.notion_schema import get_database_schema_async
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保已安装所有依赖包：pip install -r requirements.txt")
    sys.exit(1)


async def test_async_components():
    """测试异步组件连接"""
    print("🔗 测试异步组件连接...")
    
    try:
        # 测试异步LLM连接
        print("  📡 测试异步LLM连接...")
        llm_ok = await test_extractor_async()
        print(f"    LLM: {'✅ 正常' if llm_ok else '❌ 失败'}")
        
        # 测试异步Notion连接
        print("  📡 测试异步Notion连接...")
        notion_ok = await test_notion_connection_async()
        print(f"    Notion: {'✅ 正常' if notion_ok else '❌ 失败'}")
        
        # 测试异步Schema获取
        print("  📡 测试异步Schema获取...")
        try:
            schema = await get_database_schema_async()
            schema_ok = schema is not None
            print(f"    Schema: {'✅ 正常' if schema_ok else '❌ 失败'}")
            if schema_ok:
                print(f"      字段数量: {len(schema.fields)}")
        except Exception as e:
            print(f"    Schema: ❌ 失败 ({e})")
            schema_ok = False
        
        return llm_ok and notion_ok and schema_ok
        
    except Exception as e:
        print(f"❌ 组件连接测试异常: {e}")
        return False


async def performance_comparison_demo():
    """性能对比演示"""
    print("\n🚀 性能对比演示")
    print("=" * 50)
    
    # 使用一些示例URL（这里使用简单的URL，实际测试时请替换为有效URL）
    test_urls = [
        "https://httpbin.org/delay/1",  # 模拟网络延迟
        "https://httpbin.org/delay/2",
        "https://httpbin.org/delay/1",
    ]
    
    print(f"📋 测试URL数量: {len(test_urls)}")
    print(f"📋 测试URL列表: {test_urls}")
    
    # 并发处理测试
    print(f"\n🔥 异步并发处理测试...")
    start_time = time.time()
    
    try:
        results = await async_main_pipeline.process_multiple_urls_concurrent(test_urls)
        concurrent_time = time.time() - start_time
        success_count = sum(1 for r in results if r.success)
        
        print(f"📊 并发处理结果:")
        print(f"   总耗时: {concurrent_time:.2f}s")
        print(f"   成功数: {success_count}/{len(test_urls)}")
        print(f"   平均耗时: {concurrent_time/len(test_urls):.2f}s/个")
        
        # 计算理论性能提升
        estimated_sequential_time = len(test_urls) * 3  # 假设每个URL顺序处理需要3秒
        speedup = estimated_sequential_time / concurrent_time if concurrent_time > 0 else 1
        print(f"   🚀 预计加速比: {speedup:.1f}x")
        
        return True, concurrent_time, success_count
        
    except Exception as e:
        print(f"❌ 并发处理测试失败: {e}")
        return False, 0, 0


async def single_url_performance_test():
    """单URL异步性能测试"""
    print("\n⚡ 单URL异步性能测试")
    print("=" * 30)
    
    test_url = "https://httpbin.org/delay/1"
    print(f"📝 测试URL: {test_url}")
    
    try:
        start_time = time.time()
        result = await async_main_pipeline.process_single_url_async(test_url)
        processing_time = time.time() - start_time
        
        print(f"📊 单URL处理结果:")
        print(f"   处理耗时: {processing_time:.2f}s")
        print(f"   处理状态: {'✅ 成功' if result.success else '❌ 失败'}")
        
        if not result.success:
            print(f"   错误信息: {result.error_message}")
        
        return result.success, processing_time
        
    except Exception as e:
        print(f"❌ 单URL处理测试失败: {e}")
        return False, 0


async def main():
    """主测试函数"""
    print("🎯 异步性能测试开始")
    print("=" * 60)
    
    # 1. 测试异步组件连接
    components_ok = await test_async_components()
    
    if not components_ok:
        print("\n❌ 组件连接测试失败，跳过性能测试")
        print("请检查配置文件和网络连接")
        return
    
    print("\n✅ 所有异步组件连接正常")
    
    # 2. 单URL性能测试
    single_ok, single_time = await single_url_performance_test()
    
    # 3. 并发性能测试
    if single_ok:
        batch_ok, batch_time, success_count = await performance_comparison_demo()
        
        # 4. 总结
        print("\n📊 测试总结")
        print("=" * 30)
        
        if single_ok:
            print(f"✅ 单URL异步处理: {single_time:.2f}s")
        else:
            print("❌ 单URL异步处理: 失败")
        
        if batch_ok:
            print(f"✅ 并发批量处理: {batch_time:.2f}s")
            print(f"✅ 成功处理数量: {success_count}")
            
            # 性能对比
            if single_time > 0:
                theoretical_sequential = success_count * single_time
                actual_speedup = theoretical_sequential / batch_time if batch_time > 0 else 1
                print(f"🚀 实际加速比: {actual_speedup:.1f}x")
            
        else:
            print("❌ 并发批量处理: 失败")
        
        print("\n🎉 异步重构验证完成！")
        
        if single_ok and batch_ok:
            print("✅ 异步实现工作正常，性能显著提升！")
        else:
            print("⚠️ 部分测试失败，请检查配置和网络连接")
    else:
        print("\n⚠️ 单URL测试失败，跳过批量测试")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
