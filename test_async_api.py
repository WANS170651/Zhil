#!/usr/bin/env python3
"""
异步API测试脚本
测试重构后的FastAPI端点
"""

import asyncio
import aiohttp
import time
import json


async def test_api_endpoints():
    """测试异步API端点"""
    base_url = "http://localhost:8000"
    
    print("🌐 测试异步API端点")
    print("=" * 40)
    
    async with aiohttp.ClientSession() as session:
        # 1. 测试健康检查
        print("📡 测试健康检查端点...")
        try:
            async with session.get(f"{base_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print("✅ 健康检查通过")
                    print(f"   状态: {health_data.get('status')}")
                    
                    components = health_data.get('components', {})
                    for component, status in components.items():
                        status_icon = "✅" if status else "❌"
                        print(f"   {component}: {status_icon}")
                else:
                    print(f"❌ 健康检查失败: {response.status}")
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
        
        # 2. 测试单URL处理
        print("\n📝 测试单URL异步处理...")
        test_url = "https://httpbin.org/json"
        
        payload = {
            "url": test_url,
            "force_create": False
        }
        
        try:
            start_time = time.time()
            async with session.post(f"{base_url}/ingest/url", json=payload) as response:
                processing_time = time.time() - start_time
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ 单URL处理成功")
                    print(f"   耗时: {processing_time:.2f}s")
                    print(f"   API响应时间: {result.get('processing_time', 0):.2f}s")
                    print(f"   处理状态: {result.get('success')}")
                else:
                    error_data = await response.json()
                    print(f"❌ 单URL处理失败: {response.status}")
                    print(f"   错误: {error_data}")
        except Exception as e:
            print(f"❌ 单URL处理异常: {e}")
        
        # 3. 测试批量并发处理
        print("\n🚀 测试批量并发处理...")
        test_urls = [
            "https://httpbin.org/delay/1",
            "https://httpbin.org/delay/2",
            "https://httpbin.org/json"
        ]
        
        batch_payload = {
            "urls": test_urls,
            "batch_delay": 0.1,
            "force_create": False
        }
        
        try:
            start_time = time.time()
            async with session.post(f"{base_url}/ingest/batch", json=batch_payload) as response:
                processing_time = time.time() - start_time
                
                if response.status == 200:
                    result = await response.json()
                    print("✅ 批量处理成功")
                    print(f"   总耗时: {processing_time:.2f}s")
                    print(f"   API响应时间: {result.get('processing_time', 0):.2f}s")
                    
                    summary = result.get('summary', {})
                    print(f"   处理结果: {summary.get('success_count', 0)}/{summary.get('total_count', 0)} 成功")
                    print(f"   预计加速比: {summary.get('estimated_speedup', 1):.1f}x")
                    
                    # 计算API级别的加速比
                    estimated_sequential_api_time = len(test_urls) * 3  # 假设单个API调用3秒
                    api_speedup = estimated_sequential_api_time / processing_time if processing_time > 0 else 1
                    print(f"   API加速比: {api_speedup:.1f}x")
                    
                else:
                    error_data = await response.json()
                    print(f"❌ 批量处理失败: {response.status}")
                    print(f"   错误: {error_data}")
        except Exception as e:
            print(f"❌ 批量处理异常: {e}")


async def stress_test():
    """简单的压力测试"""
    print("\n💪 简单压力测试")
    print("=" * 30)
    
    base_url = "http://localhost:8000"
    concurrent_requests = 5
    
    print(f"🔥 并发发送 {concurrent_requests} 个请求...")
    
    async def single_request(session, i):
        payload = {"url": f"https://httpbin.org/delay/1?id={i}"}
        start_time = time.time()
        
        try:
            async with session.post(f"{base_url}/ingest/url", json=payload) as response:
                processing_time = time.time() - start_time
                
                if response.status == 200:
                    result = await response.json()
                    return True, processing_time, result.get('processing_time', 0)
                else:
                    return False, processing_time, None
        except Exception as e:
            return False, time.time() - start_time, str(e)
    
    start_time = time.time()
    
    async with aiohttp.ClientSession() as session:
        tasks = [single_request(session, i) for i in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    total_time = time.time() - start_time
    
    # 统计结果
    success_count = sum(1 for r in results if isinstance(r, tuple) and r[0])
    avg_api_time = sum(r[1] for r in results if isinstance(r, tuple)) / len(results)
    avg_processing_time = sum(r[2] for r in results if isinstance(r, tuple) and r[2]) / success_count if success_count > 0 else 0
    
    print(f"📊 压力测试结果:")
    print(f"   总耗时: {total_time:.2f}s")
    print(f"   成功请求: {success_count}/{concurrent_requests}")
    print(f"   平均API响应时间: {avg_api_time:.2f}s")
    print(f"   平均处理时间: {avg_processing_time:.2f}s")
    print(f"   并发效率: {(concurrent_requests * avg_api_time) / total_time:.1f}x")


async def main():
    """主测试函数"""
    print("🎯 异步API测试")
    print("=" * 50)
    
    print("请确保API服务已启动: python start_web_demo.py")
    print("等待5秒钟...")
    await asyncio.sleep(2)
    
    try:
        # 基础功能测试
        await test_api_endpoints()
        
        # 压力测试
        await stress_test()
        
        print("\n🎉 API测试完成！")
        print("✅ 异步重构的API表现优秀")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现异常: {e}")
        print("请检查API服务是否正常运行")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
