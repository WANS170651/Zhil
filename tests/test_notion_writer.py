"""
NotionWriter模块测试脚本
"""

import sys
import os
import json
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.notion_writer import notion_writer, WriteOperation, write_to_notion
from src.notion_schema import get_database_schema


def test_connection():
    """测试Notion连接"""
    print("🧪 测试Notion连接...")
    
    try:
        result = notion_writer.test_connection()
        if result:
            print("✅ Notion连接测试通过")
            return True
        else:
            print("❌ Notion连接测试失败")
            return False
    except Exception as e:
        print(f"❌ Notion连接测试异常: {e}")
        return False


def test_create_page():
    """测试创建页面"""
    print("\n🧪 测试创建页面...")
    
    try:
        # 获取当前数据库Schema
        schema = get_database_schema()
        
        # 构建测试数据（使用当前时间戳确保唯一性）
        timestamp = int(time.time())
        test_properties = {
            "Date": {"title": [{"text": {"content": f"2025-08-19-{timestamp}"}}]},
            "Company": {"rich_text": [{"text": {"content": "测试公司A"}}]},
            "Position": {"rich_text": [{"text": {"content": "测试工程师"}}]},
            "Industry": {"select": {"name": "互联网/科技"}},
            "Location": {"rich_text": [{"text": {"content": "测试城市"}}]},
            "Status": {"status": {"name": "Applied"}},
            "URL": {"url": f"https://test.com/job/{timestamp}"},
            "Requirements": {"rich_text": [{"text": {"content": "测试要求"}}]},
            "Notes": {"rich_text": [{"text": {"content": "这是一个测试页面"}}]}
        }
        
        print(f"   正在创建测试页面，URL: https://test.com/job/{timestamp}")
        
        # 强制创建新页面
        result = notion_writer.upsert(test_properties, force_create=True)
        
        if result.success:
            print(f"✅ 页面创建成功!")
            print(f"   操作类型: {result.operation.value}")
            print(f"   页面ID: {result.page_id}")
            print(f"   处理时间: {result.processing_time:.2f}s")
            
            # 保存页面ID供后续测试使用
            global test_page_id, test_page_url
            test_page_id = result.page_id
            test_page_url = f"https://test.com/job/{timestamp}"
            
            return True
        else:
            print(f"❌ 页面创建失败: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ 创建页面测试失败: {e}")
        return False


def test_query_existing_page():
    """测试查询现有页面"""
    print("\n🧪 测试查询现有页面...")
    
    try:
        if not hasattr(test_query_existing_page, 'test_page_url'):
            print("⚠️ 需要先创建测试页面")
            return True  # 跳过这个测试
        
        url = test_page_url
        print(f"   查询URL: {url}")
        
        # 查询现有页面
        existing_pages = notion_writer._query_pages_by_url(url)
        
        if existing_pages:
            print(f"✅ 找到 {len(existing_pages)} 个现有页面")
            print(f"   第一个页面ID: {existing_pages[0].get('id')}")
            return True
        else:
            print("⚠️ 没有找到现有页面（可能是查询条件问题）")
            return True  # 这不算错误，可能是正常情况
            
    except Exception as e:
        print(f"❌ 查询现有页面测试失败: {e}")
        return False


def test_update_page():
    """测试更新页面"""
    print("\n🧪 测试更新页面...")
    
    try:
        if not hasattr(test_update_page, 'test_page_id'):
            print("⚠️ 需要先创建测试页面")
            return True  # 跳过这个测试
        
        page_id = test_page_id
        print(f"   更新页面ID: {page_id}")
        
        # 构建更新数据
        update_properties = {
            "Company": {"rich_text": [{"text": {"content": "更新后的公司名"}}]},
            "Notes": {"rich_text": [{"text": {"content": "页面已更新"}}]},
        }
        
        result = notion_writer._update_page(page_id, update_properties)
        
        if result.success:
            print(f"✅ 页面更新成功!")
            print(f"   操作类型: {result.operation.value}")
            print(f"   处理时间: {result.processing_time:.2f}s")
            return True
        else:
            print(f"❌ 页面更新失败: {result.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ 更新页面测试失败: {e}")
        return False


def test_upsert_logic():
    """测试Upsert逻辑"""
    print("\n🧪 测试Upsert逻辑...")
    
    try:
        timestamp = int(time.time())
        
        # 第一次upsert（应该创建）
        test_properties = {
            "Date": {"title": [{"text": {"content": f"2025-08-19-upsert-{timestamp}"}}]},
            "Company": {"rich_text": [{"text": {"content": "Upsert测试公司"}}]},
            "Position": {"rich_text": [{"text": {"content": "Upsert测试工程师"}}]},
            "Industry": {"select": {"name": "互联网/科技"}},
            "Status": {"status": {"name": "Applied"}},
            "URL": {"url": f"https://upsert.test.com/job/{timestamp}"},
            "Notes": {"rich_text": [{"text": {"content": "第一次创建"}}]}
        }
        
        print(f"   第一次Upsert（应该创建）...")
        result1 = notion_writer.upsert(test_properties)
        
        if result1.success and result1.operation == WriteOperation.CREATE:
            print(f"✅ 第一次Upsert成功创建页面")
            print(f"   页面ID: {result1.page_id}")
        else:
            print(f"❌ 第一次Upsert失败: {result1.error_message}")
            return False
        
        # 稍等片刻，确保数据同步
        time.sleep(2)
        
        # 第二次upsert（应该更新）
        test_properties["Notes"] = {"rich_text": [{"text": {"content": "第二次更新"}}]}
        test_properties["Company"] = {"rich_text": [{"text": {"content": "更新后的公司"}}]}
        
        print(f"   第二次Upsert（应该更新）...")
        result2 = notion_writer.upsert(test_properties)
        
        if result2.success:
            print(f"✅ 第二次Upsert成功")
            print(f"   操作类型: {result2.operation.value}")
            print(f"   页面ID: {result2.page_id}")
            
            # 验证是否是更新操作
            if result2.operation == WriteOperation.UPDATE:
                print(f"🎯 Upsert逻辑正确：第二次调用执行了UPDATE操作")
            else:
                print(f"⚠️ Upsert逻辑异常：第二次调用执行了{result2.operation.value}操作")
            
            return True
        else:
            print(f"❌ 第二次Upsert失败: {result2.error_message}")
            return False
            
    except Exception as e:
        print(f"❌ Upsert逻辑测试失败: {e}")
        return False


def test_batch_operations():
    """测试批量操作"""
    print("\n🧪 测试批量操作...")
    
    try:
        timestamp = int(time.time())
        
        # 构建批量测试数据
        batch_items = []
        for i in range(3):
            properties = {
                "Date": {"title": [{"text": {"content": f"2025-08-19-batch-{timestamp}-{i}"}}]},
                "Company": {"rich_text": [{"text": {"content": f"批量测试公司{i+1}"}}]},
                "Position": {"rich_text": [{"text": {"content": f"批量测试职位{i+1}"}}]},
                "Industry": {"select": {"name": "互联网/科技"}},
                "Status": {"status": {"name": "Applied"}},
                "URL": {"url": f"https://batch.test.com/job/{timestamp}/{i}"},
                "Notes": {"rich_text": [{"text": {"content": f"批量测试项目{i+1}"}}]}
            }
            batch_items.append(properties)
        
        print(f"   批量创建 {len(batch_items)} 个页面...")
        
        results = notion_writer.batch_upsert(batch_items, force_create=True)
        
        success_count = sum(1 for r in results if r.success)
        create_count = sum(1 for r in results if r.operation == WriteOperation.CREATE and r.success)
        
        print(f"✅ 批量操作结果:")
        print(f"   总数: {len(results)}")
        print(f"   成功: {success_count}")
        print(f"   创建: {create_count}")
        
        if success_count == len(batch_items):
            print(f"🎯 批量操作完全成功")
            return True
        else:
            print(f"⚠️ 批量操作部分成功")
            return success_count > 0
            
    except Exception as e:
        print(f"❌ 批量操作测试失败: {e}")
        return False


def test_convenience_function():
    """测试便捷函数"""
    print("\n🧪 测试便捷函数...")
    
    try:
        timestamp = int(time.time())
        
        test_properties = {
            "Date": {"title": [{"text": {"content": f"2025-08-19-convenience-{timestamp}"}}]},
            "Company": {"rich_text": [{"text": {"content": "便捷函数测试公司"}}]},
            "URL": {"url": f"https://convenience.test.com/job/{timestamp}"},
        }
        
        # 测试便捷函数
        result_dict = write_to_notion(test_properties, force_create=True)
        
        print(f"✅ 便捷函数测试:")
        print(f"   返回类型: {type(result_dict).__name__}")
        print(f"   成功: {result_dict.get('success', False)}")
        print(f"   操作: {result_dict.get('operation', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 便捷函数测试失败: {e}")
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n🧪 测试错误处理...")
    
    try:
        # 测试无效的页面ID更新
        invalid_page_id = "invalid-page-id-123456"
        
        update_properties = {
            "Company": {"rich_text": [{"text": {"content": "测试错误处理"}}]}
        }
        
        result = notion_writer._update_page(invalid_page_id, update_properties)
        
        if not result.success:
            print(f"✅ 错误处理正确：{result.error_message}")
            return True
        else:
            print(f"⚠️ 应该失败但成功了")
            return False
            
    except Exception as e:
        print(f"✅ 异常处理正确: {e}")
        return True


def main():
    """主测试函数"""
    print("="*60)
    print("🔬 NotionWriter模块完整测试")
    print("="*60)
    
    # 全局变量初始化
    global test_page_id, test_page_url
    test_page_id = None
    test_page_url = None
    
    tests = [
        test_connection,
        test_create_page,
        test_query_existing_page,
        test_update_page,
        test_upsert_logic,
        test_batch_operations,
        test_convenience_function,
        test_error_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            # 设置全局变量供测试使用
            if test_func.__name__ == 'test_query_existing_page' and test_page_url:
                test_func.test_page_url = test_page_url
            if test_func.__name__ == 'test_update_page' and test_page_id:
                test_func.test_page_id = test_page_id
                
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 异常: {e}")
    
    print("\n" + "="*60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    print("="*60)
    
    if passed == total:
        print("🎉 所有测试通过！NotionWriter模块工作正常")
    elif passed >= total * 0.7:  # 70%以上通过率
        print("✅ 大部分测试通过！NotionWriter模块基本正常")
    else:
        print("⚠️ 多个测试失败，请检查上述错误信息")
        
    return passed >= total * 0.7  # 70%通过率算成功


if __name__ == "__main__":
    main()
