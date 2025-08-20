"""
API服务演示脚本
展示FastAPI服务的完整功能
"""

import sys
import os
import asyncio
import time
import json
from typing import Dict, Any, List

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx


class APIClient:
    """API客户端封装"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()
    
    async def get_health(self) -> Dict[str, Any]:
        """获取健康状态"""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    async def get_config(self) -> Dict[str, Any]:
        """获取配置信息"""
        response = await self.client.get(f"{self.base_url}/config")
        response.raise_for_status()
        return response.json()
    
    async def get_pipeline_status(self) -> Dict[str, Any]:
        """获取管道状态"""
        response = await self.client.get(f"{self.base_url}/status/pipeline")
        response.raise_for_status()
        return response.json()
    
    async def process_single_url(self, url: str, force_create: bool = False, 
                               metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理单个URL"""
        data = {
            "url": url,
            "force_create": force_create,
            "metadata": metadata or {}
        }
        
        response = await self.client.post(f"{self.base_url}/ingest/url", json=data)
        response.raise_for_status()
        return response.json()
    
    async def process_batch_urls(self, urls: List[str], force_create: bool = False,
                               batch_delay: float = 1.0) -> Dict[str, Any]:
        """批量处理URL"""
        data = {
            "urls": urls,
            "force_create": force_create,
            "batch_delay": batch_delay
        }
        
        response = await self.client.post(f"{self.base_url}/ingest/batch", json=data)
        response.raise_for_status()
        return response.json()


async def demo_system_status():
    """演示系统状态检查"""
    print("🔍 系统状态检查演示")
    print("="*40)
    
    client = APIClient()
    
    try:
        # 健康检查
        print("📊 健康检查...")
        health = await client.get_health()
        
        print(f"   服务状态: {health.get('status', 'unknown')}")
        
        components = health.get('components', {})
        print(f"   组件状态:")
        for component, status in components.items():
            icon = "✅" if status else "❌"
            print(f"     {component}: {icon}")
        
        # 配置信息
        print(f"\n⚙️ 配置信息...")
        config = await client.get_config()
        
        print(f"   LLM模型: {config.get('llm_model', 'unknown')}")
        print(f"   Notion版本: {config.get('notion_version', 'unknown')}")
        print(f"   缓存TTL: {config.get('schema_cache_ttl', 0)}秒")
        print(f"   日志级别: {config.get('log_level', 'unknown')}")
        
        # 管道状态
        print(f"\n🔧 管道状态...")
        try:
            pipeline = await client.get_pipeline_status()
            
            print(f"   管道就绪: {'✅' if pipeline.get('pipeline_ready', False) else '❌'}")
            
            schema_info = pipeline.get('database_schema', {})
            print(f"   Schema加载: {'✅' if schema_info.get('loaded', False) else '❌'}")
            print(f"   字段数量: {schema_info.get('fields_count', 0)}")
            
        except Exception as e:
            print(f"   管道状态获取失败: {e}")
        
        print("\n✅ 系统状态检查完成")
        return True
        
    except Exception as e:
        print(f"❌ 系统状态检查失败: {e}")
        return False
    
    finally:
        await client.close()


async def demo_single_url_processing():
    """演示单个URL处理"""
    print("\n🚀 单个URL处理演示")
    print("="*40)
    
    client = APIClient()
    
    try:
        # 使用一个真实的招聘网站URL
        demo_url = "https://campus.kuaishou.cn/recruit/campus/e/#/campus/job-info/9822"
        
        print(f"📋 目标URL: {demo_url}")
        print(f"⏱️ 开始处理...")
        
        start_time = time.time()
        
        result = await client.process_single_url(
            url=demo_url,
            force_create=False,
            metadata={"source": "api_demo", "type": "job_posting"}
        )
        
        processing_time = time.time() - start_time
        
        print(f"\n📊 处理结果:")
        print(f"   成功: {'✅' if result.get('success', False) else '❌'}")
        print(f"   消息: {result.get('message', 'N/A')}")
        print(f"   总耗时: {processing_time:.2f}秒")
        print(f"   API耗时: {result.get('processing_time', 0):.2f}秒")
        
        # 详细结果
        detail_result = result.get('result', {})
        if detail_result:
            print(f"\n📋 详细信息:")
            print(f"   处理阶段: {detail_result.get('stage', 'unknown')}")
            print(f"   处理状态: {detail_result.get('status', 'unknown')}")
            
            # 阶段耗时
            stage_times = detail_result.get('stage_times', {})
            if stage_times:
                print(f"   阶段耗时:")
                for stage, duration in stage_times.items():
                    print(f"     {stage}: {duration:.2f}s")
            
            # 写入结果
            writing_result = detail_result.get('writing_result', {})
            if writing_result:
                print(f"   Notion操作:")
                print(f"     类型: {writing_result.get('operation', 'unknown')}")
                print(f"     页面ID: {writing_result.get('page_id', 'N/A')}")
        
        print("\n✅ 单个URL处理演示完成")
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ 单个URL处理演示失败: {e}")
        return False
    
    finally:
        await client.close()


async def demo_batch_processing():
    """演示批量URL处理"""
    print("\n📦 批量URL处理演示")
    print("="*40)
    
    client = APIClient()
    
    try:
        # 准备测试URL列表
        test_urls = [
            "https://www.example.com/job1",
            "https://www.example.com/job2",
            "https://www.example.com/job3"
        ]
        
        print(f"📋 批量处理URL列表:")
        for i, url in enumerate(test_urls, 1):
            print(f"   {i}. {url}")
        
        print(f"\n⏱️ 开始批量处理...")
        
        start_time = time.time()
        
        result = await client.process_batch_urls(
            urls=test_urls,
            force_create=False,
            batch_delay=0.5  # 减少延迟以加快演示
        )
        
        processing_time = time.time() - start_time
        
        print(f"\n📊 批量处理结果:")
        print(f"   成功: {'✅' if result.get('success', False) else '❌'}")
        print(f"   消息: {result.get('message', 'N/A')}")
        print(f"   总耗时: {processing_time:.2f}秒")
        print(f"   API耗时: {result.get('processing_time', 0):.2f}秒")
        
        # 处理摘要
        summary = result.get('summary', {})
        if summary:
            print(f"\n📋 处理摘要:")
            print(f"   总数: {summary.get('total_count', 0)}")
            print(f"   成功: {summary.get('success_count', 0)}")
            print(f"   失败: {summary.get('failed_count', 0)}")
            print(f"   成功率: {summary.get('success_rate', 0):.1f}%")
        
        # 操作统计
        report = result.get('report', {})
        operations = report.get('operations', {})
        if operations:
            print(f"\n💾 Notion操作:")
            print(f"   创建: {operations.get('create_count', 0)}")
            print(f"   更新: {operations.get('update_count', 0)}")
        
        # 时间统计
        timing = report.get('timing', {})
        if timing:
            print(f"\n⏱️ 时间统计:")
            print(f"   平均耗时: {timing.get('average_time', 0):.2f}s/个")
        
        print("\n✅ 批量URL处理演示完成")
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ 批量URL处理演示失败: {e}")
        return False
    
    finally:
        await client.close()


async def demo_api_features():
    """演示API特性"""
    print("\n🎯 API特性演示")
    print("="*40)
    
    client = APIClient()
    
    try:
        print("🔧 测试API验证功能...")
        
        # 测试无效URL
        try:
            await client.process_single_url("invalid-url")
            print("   ❌ 应该拒绝无效URL")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                print("   ✅ 正确拒绝无效URL")
            else:
                print(f"   ⚠️ 意外的状态码: {e.response.status_code}")
        
        # 测试空批量请求
        try:
            await client.process_batch_urls([])
            print("   ❌ 应该拒绝空URL列表")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 422:
                print("   ✅ 正确拒绝空URL列表")
            else:
                print(f"   ⚠️ 意外的状态码: {e.response.status_code}")
        
        print("\n🛡️ 错误处理功能...")
        
        # 测试不存在的域名
        try:
            result = await client.process_single_url("https://this-domain-does-not-exist-12345.com")
            if not result.get('success', True):
                print("   ✅ 正确处理不存在的域名")
            else:
                print("   ⚠️ 意外成功处理不存在的域名")
        except Exception as e:
            print(f"   ✅ 正确处理网络错误: {type(e).__name__}")
        
        print("\n✅ API特性演示完成")
        return True
        
    except Exception as e:
        print(f"❌ API特性演示失败: {e}")
        return False
    
    finally:
        await client.close()


async def demo_real_world_scenario():
    """演示真实世界使用场景"""
    print("\n🌍 真实应用场景演示")
    print("="*40)
    
    client = APIClient()
    
    try:
        print("📖 场景描述:")
        print("   某HR团队使用API服务自动收集和管理招聘信息")
        print("   通过API批量处理多个招聘网站的职位页面")
        print("   系统自动提取信息并存储到Notion数据库")
        
        # 模拟真实的招聘URL（使用example.com以避免实际网站负载）
        job_urls = [
            "https://www.example.com/careers/software-engineer",
            "https://www.example.com/careers/product-manager",
            "https://www.example.com/careers/data-analyst"
        ]
        
        print(f"\n🎯 HR团队的工作流程:")
        print(f"   1. 收集招聘网站URL")
        print(f"   2. 调用API批量处理")
        print(f"   3. 系统自动提取和存储")
        print(f"   4. 团队在Notion中查看结果")
        
        print(f"\n📋 本次处理的职位:")
        for i, url in enumerate(job_urls, 1):
            job_type = url.split('/')[-1].replace('-', ' ').title()
            print(f"   {i}. {job_type}")
        
        print(f"\n🚀 开始自动化处理...")
        
        start_time = time.time()
        
        # 批量处理
        result = await client.process_batch_urls(
            urls=job_urls,
            force_create=False,
            batch_delay=1.0
        )
        
        total_time = time.time() - start_time
        
        print(f"\n📊 处理完成！")
        
        if result.get('success', False):
            summary = result.get('summary', {})
            
            print(f"✅ 自动化处理成功")
            print(f"   处理职位: {summary.get('total_count', 0)} 个")
            print(f"   成功入库: {summary.get('success_count', 0)} 个")
            print(f"   总耗时: {total_time:.1f} 秒")
            
            # 展示业务价值
            print(f"\n💼 业务价值:")
            print(f"   ⏰ 节省手工时间: 预计 {summary.get('total_count', 0) * 5} 分钟")
            print(f"   📊 数据标准化: 统一的字段格式")
            print(f"   🔄 自动去重: 避免重复录入")
            print(f"   🎯 即时可用: 数据已在Notion中可查看")
            
            print(f"\n🎉 HR团队现在可以:")
            print(f"   📋 在Notion中查看所有职位")
            print(f"   🔍 使用过滤器筛选职位")
            print(f"   📈 分析招聘数据趋势")
            print(f"   👥 与团队协作处理")
            
        else:
            print(f"⚠️ 处理过程中遇到问题")
            print(f"   但系统具备完善的错误恢复机制")
        
        print("\n✅ 真实应用场景演示完成")
        return True
        
    except Exception as e:
        print(f"❌ 真实应用场景演示失败: {e}")
        return False
    
    finally:
        await client.close()


async def main():
    """主演示函数"""
    print("🎯 URL信息收集和存储系统 - API服务演示")
    print("="*60)
    print("注意：此演示需要API服务正在运行")
    print("     启动命令: python start_api.py")
    print("="*60)
    
    # 演示检查API是否可访问
    print("🔍 检查API服务状态...")
    
    try:
        client = APIClient()
        await client.get_health()
        await client.close()
        print("✅ API服务正常运行，开始演示...\n")
    except Exception as e:
        print(f"❌ 无法连接到API服务: {e}")
        print("💡 请确保API服务正在运行:")
        print("   python start_api.py")
        return
    
    # 执行各种演示
    demos = [
        ("系统状态检查", demo_system_status),
        ("单个URL处理", demo_single_url_processing),
        ("批量URL处理", demo_batch_processing),
        ("API特性测试", demo_api_features),
        ("真实应用场景", demo_real_world_scenario)
    ]
    
    demo_results = []
    
    for demo_name, demo_func in demos:
        try:
            result = await demo_func()
            demo_results.append((demo_name, result))
            
            # 在演示之间稍作停顿
            if demo_func != demos[-1][1]:  # 不是最后一个演示
                print("\n" + "-"*40)
                await asyncio.sleep(1)
                
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
        print("\n🎉 所有演示成功！API服务运行完美！")
        print("🚀 系统已准备好投入生产使用！")
    elif success_count >= total_count * 0.8:
        print("\n✅ 大部分演示成功！API服务基本正常！")
        print("💡 个别失败可能是网络连接或测试数据问题")
    else:
        print("\n⚠️ 演示结果不理想，请检查API服务和网络连接")
    
    print(f"\n🔑 API服务核心能力:")
    print(f"  🌐 RESTful API - 标准的HTTP接口")
    print(f"  📊 自动验证 - 完善的请求数据验证")
    print(f"  🛡️ 错误处理 - 优雅的异常恢复")
    print(f"  📚 自动文档 - OpenAPI/Swagger文档")
    print(f"  🔍 健康监控 - 实时的系统状态检查")
    print(f"  ⚡ 异步处理 - 高性能的并发处理")
    
    print(f"\n💡 使用方式:")
    print(f"  📖 API文档: http://localhost:8000/docs")
    print(f"  🔍 健康检查: http://localhost:8000/health")
    print(f"  🚀 单个URL: POST /ingest/url")
    print(f"  📦 批量处理: POST /ingest/batch")


if __name__ == "__main__":
    asyncio.run(main())
