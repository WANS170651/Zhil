"""
API服务测试脚本
验证FastAPI服务的功能
"""

import sys
import os
import asyncio
import time
import json
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import httpx
except ImportError:
    httpx = None
    
from fastapi.testclient import TestClient

from src.api_service import app


# 创建测试客户端
client = TestClient(app)


def test_root_endpoint():
    """测试根端点"""
    print("🧪 测试根端点...")
    
    response = client.get("/")
    
    print(f"   状态码: {response.status_code}")
    print(f"   响应内容: {response.json()}")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    
    print("✅ 根端点测试通过")
    return True


def test_health_endpoint():
    """测试健康检查端点"""
    print("\n🧪 测试健康检查端点...")
    
    response = client.get("/health")
    
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   服务状态: {data.get('status', 'unknown')}")
        print(f"   组件状态:")
        components = data.get('components', {})
        for component, status in components.items():
            status_icon = "✅" if status else "❌"
            print(f"     {component}: {status_icon}")
        
        assert "status" in data
        assert "components" in data
        assert "timestamp" in data
        
        print("✅ 健康检查端点测试通过")
        return True
    else:
        print(f"❌ 健康检查失败: {response.status_code}")
        return False


def test_config_endpoint():
    """测试配置端点"""
    print("\n🧪 测试配置端点...")
    
    response = client.get("/config")
    
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   配置信息:")
        for key, value in data.items():
            print(f"     {key}: {value}")
        
        assert "llm_model" in data
        assert "version" in data
        
        print("✅ 配置端点测试通过")
        return True
    else:
        print(f"❌ 配置端点测试失败: {response.status_code}")
        return False


def test_pipeline_status_endpoint():
    """测试管道状态端点"""
    print("\n🧪 测试管道状态端点...")
    
    response = client.get("/status/pipeline")
    
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   管道就绪: {data.get('pipeline_ready', False)}")
        
        schema_info = data.get('database_schema', {})
        print(f"   数据库Schema:")
        print(f"     已加载: {schema_info.get('loaded', False)}")
        print(f"     字段数量: {schema_info.get('fields_count', 0)}")
        
        assert "pipeline_ready" in data
        assert "database_schema" in data
        
        print("✅ 管道状态端点测试通过")
        return True
    else:
        print(f"❌ 管道状态端点测试失败: {response.status_code}")
        return False


def test_single_url_endpoint():
    """测试单个URL处理端点"""
    print("\n🧪 测试单个URL处理端点...")
    
    # 测试数据
    test_data = {
        "url": "https://www.example.com/test-api",
        "force_create": False,
        "metadata": {"source": "api_test"}
    }
    
    print(f"   请求数据: {test_data}")
    
    response = client.post("/ingest/url", json=test_data)
    
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   处理成功: {data.get('success', False)}")
        print(f"   处理时间: {data.get('processing_time', 0):.2f}s")
        print(f"   消息: {data.get('message', 'N/A')}")
        
        result = data.get('result', {})
        if result:
            print(f"   处理结果:")
            print(f"     阶段: {result.get('stage', 'unknown')}")
            print(f"     状态: {result.get('status', 'unknown')}")
        
        assert "success" in data
        assert "url" in data
        assert "result" in data
        
        print("✅ 单个URL处理端点测试通过")
        return True
    else:
        print(f"❌ 单个URL处理端点测试失败: {response.status_code}")
        try:
            error_data = response.json()
            print(f"   错误信息: {error_data}")
        except:
            print(f"   响应内容: {response.text}")
        return False


def test_batch_url_endpoint():
    """测试批量URL处理端点"""
    print("\n🧪 测试批量URL处理端点...")
    
    # 测试数据
    test_data = {
        "urls": [
            "https://www.example.com/test-batch-1",
            "https://www.example.com/test-batch-2"
        ],
        "force_create": False,
        "batch_delay": 0.5
    }
    
    print(f"   请求数据: {test_data}")
    
    response = client.post("/ingest/batch", json=test_data)
    
    print(f"   状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   处理成功: {data.get('success', False)}")
        print(f"   处理时间: {data.get('processing_time', 0):.2f}s")
        print(f"   消息: {data.get('message', 'N/A')}")
        
        summary = data.get('summary', {})
        if summary:
            print(f"   处理摘要:")
            print(f"     总数: {summary.get('total_count', 0)}")
            print(f"     成功: {summary.get('success_count', 0)}")
            print(f"     失败: {summary.get('failed_count', 0)}")
        
        assert "success" in data
        assert "summary" in data
        assert "report" in data
        
        print("✅ 批量URL处理端点测试通过")
        return True
    else:
        print(f"❌ 批量URL处理端点测试失败: {response.status_code}")
        try:
            error_data = response.json()
            print(f"   错误信息: {error_data}")
        except:
            print(f"   响应内容: {response.text}")
        return False


def test_invalid_requests():
    """测试无效请求处理"""
    print("\n🧪 测试无效请求处理...")
    
    # 测试无效的单个URL请求
    print("   测试无效URL...")
    invalid_single = {"url": "not-a-valid-url"}
    response = client.post("/ingest/url", json=invalid_single)
    print(f"     状态码: {response.status_code}")
    assert response.status_code == 422  # 验证错误
    
    # 测试空的批量URL请求
    print("   测试空URL列表...")
    invalid_batch = {"urls": []}
    response = client.post("/ingest/batch", json=invalid_batch)
    print(f"     状态码: {response.status_code}")
    assert response.status_code == 422  # 验证错误
    
    print("✅ 无效请求处理测试通过")
    return True


def test_openapi_docs():
    """测试OpenAPI文档端点"""
    print("\n🧪 测试API文档端点...")
    
    # 测试OpenAPI JSON
    response = client.get("/openapi.json")
    print(f"   OpenAPI JSON状态码: {response.status_code}")
    assert response.status_code == 200
    
    openapi_data = response.json()
    assert "openapi" in openapi_data
    assert "info" in openapi_data
    assert "paths" in openapi_data
    
    # 测试Swagger UI
    response = client.get("/docs")
    print(f"   Swagger UI状态码: {response.status_code}")
    assert response.status_code == 200
    
    # 测试ReDoc
    response = client.get("/redoc")
    print(f"   ReDoc状态码: {response.status_code}")
    assert response.status_code == 200
    
    print("✅ API文档端点测试通过")
    return True


def run_api_tests():
    """运行所有API测试"""
    print("="*60)
    print("🔬 FastAPI服务完整测试")
    print("="*60)
    
    tests = [
        ("根端点", test_root_endpoint),
        ("健康检查", test_health_endpoint),
        ("配置端点", test_config_endpoint),
        ("管道状态", test_pipeline_status_endpoint),
        ("单个URL处理", test_single_url_endpoint),
        ("批量URL处理", test_batch_url_endpoint),
        ("无效请求处理", test_invalid_requests),
        ("API文档", test_openapi_docs)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试 {test_name} 异常: {e}")
    
    print("\n" + "="*60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    print("="*60)
    
    if passed == total:
        print("🎉 所有测试通过！API服务工作正常")
    elif passed >= total * 0.8:  # 80%以上通过率
        print("✅ 大部分测试通过！API服务基本正常")
    else:
        print("⚠️ 多个测试失败，请检查API服务配置")
    
    return passed >= total * 0.8


def main():
    """主函数"""
    print("🎯 FastAPI服务测试工具")
    print("注意：这些测试使用TestClient，无需启动实际服务器")
    print("-" * 50)
    
    success = run_api_tests()
    
    if success:
        print("\n🚀 API服务准备就绪！")
        print("💡 可以使用以下命令启动服务:")
        print("   python start_api.py")
        print("   或者: python start_api.py --reload  # 开发模式")
    else:
        print("\n⚠️ API服务可能存在问题，请检查配置和依赖")
    
    return success


if __name__ == "__main__":
    main()
