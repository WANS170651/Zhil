"""
NotionWriter模块演示脚本
展示完整的Notion数据库写入流程
"""

import sys
import os
import json
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.notion_writer import notion_writer, WriteOperation
from src.notion_schema import get_database_schema


def demo_basic_operations():
    """演示基本的增删改查操作"""
    print("🚀 基本操作演示")
    print("="*50)
    
    timestamp = int(time.time())
    
    # 构建测试数据
    test_data = {
        "Date": {"title": [{"text": {"content": f"2025-08-19-demo-{timestamp}"}}]},
        "Company": {"rich_text": [{"text": {"content": "演示公司"}}]},
        "Position": {"rich_text": [{"text": {"content": "高级演示工程师"}}]},
        "Industry": {"select": {"name": "互联网/科技"}},
        "Location": {"rich_text": [{"text": {"content": "演示城市"}}]},
        "Status": {"status": {"name": "Applied"}},
        "URL": {"url": f"https://demo.example.com/job/{timestamp}"},
        "Requirements": {"rich_text": [{"text": {"content": "5年以上工作经验，熟悉各种演示技巧"}}]},
        "Notes": {"rich_text": [{"text": {"content": "这是一个演示页面，展示NotionWriter功能"}}]}
    }
    
    print("📝 1. 创建页面演示")
    print("-" * 30)
    
    # 强制创建新页面
    print(f"   正在创建新页面...")
    result = notion_writer.upsert(test_data, force_create=True)
    
    if result.success:
        print(f"✅ 页面创建成功!")
        print(f"   📋 页面ID: {result.page_id}")
        print(f"   🔗 URL: {result.url}")
        print(f"   ⏱️ 耗时: {result.processing_time:.2f}秒")
        demo_page_id = result.page_id
    else:
        print(f"❌ 页面创建失败: {result.error_message}")
        return False
    
    print(f"\n🔍 2. 查询页面演示")
    print("-" * 30)
    
    # 查询刚创建的页面
    print(f"   正在查询页面详情...")
    page_data = notion_writer.get_page(demo_page_id)
    
    if page_data:
        print(f"✅ 页面查询成功!")
        print(f"   📄 页面对象: {page_data.get('object')}")
        print(f"   📅 创建时间: {page_data.get('created_time')}")
        print(f"   🔄 最后编辑: {page_data.get('last_edited_time')}")
    else:
        print(f"❌ 页面查询失败")
    
    print(f"\n🔄 3. 更新页面演示")
    print("-" * 30)
    
    # 更新页面内容
    update_data = {
        "Company": {"rich_text": [{"text": {"content": "更新后的演示公司"}}]},
        "Notes": {"rich_text": [{"text": {"content": "页面已被更新 - " + time.strftime('%H:%M:%S')}}]},
        "Position": {"rich_text": [{"text": {"content": "首席演示官"}}]}
    }
    
    print(f"   正在更新页面内容...")
    update_result = notion_writer._update_page(demo_page_id, update_data)
    
    if update_result.success:
        print(f"✅ 页面更新成功!")
        print(f"   ⏱️ 耗时: {update_result.processing_time:.2f}秒")
    else:
        print(f"❌ 页面更新失败: {update_result.error_message}")
    
    return demo_page_id


def demo_upsert_intelligence():
    """演示智能Upsert功能"""
    print(f"\n🧠 智能Upsert演示")
    print("="*35)
    
    timestamp = int(time.time())
    unique_url = f"https://smart-upsert.demo.com/job/{timestamp}"
    
    # 第一次调用 - 应该创建
    print("📝 第一次调用（期望：创建新页面）")
    print("-" * 40)
    
    first_data = {
        "Date": {"title": [{"text": {"content": f"2025-08-19-smart-{timestamp}"}}]},
        "Company": {"rich_text": [{"text": {"content": "智能公司 v1.0"}}]},
        "Position": {"rich_text": [{"text": {"content": "AI工程师"}}]},
        "Industry": {"select": {"name": "互联网/科技"}},
        "Status": {"status": {"name": "Applied"}},
        "URL": {"url": unique_url},
        "Notes": {"rich_text": [{"text": {"content": "第一版数据"}}]}
    }
    
    result1 = notion_writer.upsert(first_data)
    
    if result1.success:
        print(f"✅ 第一次调用成功")
        print(f"   🎯 操作类型: {result1.operation.value}")
        print(f"   📋 页面ID: {result1.page_id}")
        print(f"   🔍 是否发现现有页面: {result1.existing_page_found}")
    else:
        print(f"❌ 第一次调用失败: {result1.error_message}")
        return False
    
    # 等待一下确保数据同步
    print(f"\n⏳ 等待数据同步...")
    time.sleep(3)
    
    # 第二次调用 - 应该更新
    print("🔄 第二次调用（期望：更新现有页面）")
    print("-" * 40)
    
    second_data = first_data.copy()
    second_data["Company"] = {"rich_text": [{"text": {"content": "智能公司 v2.0（已更新）"}}]}
    second_data["Notes"] = {"rich_text": [{"text": {"content": "第二版数据 - 这是更新后的内容"}}]}
    second_data["Position"] = {"rich_text": [{"text": {"content": "高级AI工程师"}}]}
    
    result2 = notion_writer.upsert(second_data)
    
    if result2.success:
        print(f"✅ 第二次调用成功")
        print(f"   🎯 操作类型: {result2.operation.value}")
        print(f"   📋 页面ID: {result2.page_id}")
        print(f"   🔍 是否发现现有页面: {result2.existing_page_found}")
        
        # 验证智能判断
        if result1.operation == WriteOperation.CREATE and result2.operation == WriteOperation.UPDATE:
            print(f"\n🧠 智能判断完美：")
            print(f"   ✅ 第一次: CREATE（新页面）")
            print(f"   ✅ 第二次: UPDATE（现有页面）")
            print(f"   🎯 页面ID一致: {result1.page_id == result2.page_id}")
        else:
            print(f"\n⚠️ 智能判断异常：")
            print(f"   第一次: {result1.operation.value}")
            print(f"   第二次: {result2.operation.value}")
    else:
        print(f"❌ 第二次调用失败: {result2.error_message}")
    
    return True


def demo_batch_processing():
    """演示批量处理能力"""
    print(f"\n📦 批量处理演示")
    print("="*30)
    
    timestamp = int(time.time())
    
    # 构建多个不同公司的招聘信息
    companies_data = [
        {
            "name": "阿里巴巴",
            "position": "云计算架构师",
            "location": "杭州",
            "requirements": "8年以上分布式系统经验"
        },
        {
            "name": "腾讯",
            "position": "AI算法专家",
            "location": "深圳",
            "requirements": "机器学习博士学位优先"
        },
        {
            "name": "字节跳动",
            "position": "全栈工程师",
            "location": "北京",
            "requirements": "React/Node.js全栈开发经验"
        }
    ]
    
    batch_items = []
    for i, company in enumerate(companies_data):
        properties = {
            "Date": {"title": [{"text": {"content": f"2025-08-19-batch-{timestamp}-{i}"}}]},
            "Company": {"rich_text": [{"text": {"content": company["name"]}}]},
            "Position": {"rich_text": [{"text": {"content": company["position"]}}]},
            "Industry": {"select": {"name": "互联网/科技"}},
            "Location": {"rich_text": [{"text": {"content": company["location"]}}]},
            "Status": {"status": {"name": "Applied"}},
            "URL": {"url": f"https://batch-demo.com/{timestamp}/{i}"},
            "Requirements": {"rich_text": [{"text": {"content": company["requirements"]}}]},
            "Notes": {"rich_text": [{"text": {"content": f"批量演示 - {company['name']}"}}]}
        }
        batch_items.append(properties)
    
    print(f"📋 准备批量处理 {len(batch_items)} 个职位:")
    for i, company in enumerate(companies_data):
        print(f"   {i+1}. {company['name']} - {company['position']}")
    
    print(f"\n🚀 开始批量处理...")
    
    results = notion_writer.batch_upsert(batch_items, force_create=True)
    
    # 统计结果
    success_count = sum(1 for r in results if r.success)
    create_count = sum(1 for r in results if r.operation == WriteOperation.CREATE and r.success)
    total_time = sum(r.processing_time for r in results if r.processing_time)
    
    print(f"\n📊 批量处理结果:")
    print(f"   📈 总数: {len(results)}")
    print(f"   ✅ 成功: {success_count}")
    print(f"   📝 创建: {create_count}")
    print(f"   ⏱️ 总耗时: {total_time:.2f}秒")
    print(f"   📊 平均耗时: {total_time/len(results):.2f}秒/个")
    print(f"   🎯 成功率: {success_count/len(results)*100:.1f}%")
    
    if success_count == len(batch_items):
        print(f"🎉 批量处理完美成功！")
    
    return success_count == len(batch_items)


def demo_real_world_scenario():
    """演示真实世界使用场景"""
    print(f"\n🌍 真实场景演示")
    print("="*30)
    
    print("📖 场景描述:")
    print("   某用户正在求职，使用我们的系统自动收集和整理招聘信息。")
    print("   系统需要：")
    print("   1. 自动检测重复职位（基于URL）")
    print("   2. 新职位时创建记录")
    print("   3. 已存在职位时更新信息")
    print("   4. 批量处理多个来源的信息")
    
    timestamp = int(time.time())
    
    # 模拟从不同网站抓取的同一职位信息
    job_url = f"https://real-world-demo.com/job/{timestamp}"
    
    print(f"\n🕷️ 第一次爬取（来源：公司官网）")
    print("-" * 40)
    
    first_crawl = {
        "Date": {"title": [{"text": {"content": f"2025-08-19-real-{timestamp}"}}]},
        "Company": {"rich_text": [{"text": {"content": "创新科技公司"}}]},
        "Position": {"rich_text": [{"text": {"content": "高级Python开发工程师"}}]},
        "Industry": {"select": {"name": "互联网/科技"}},
        "Location": {"rich_text": [{"text": {"content": "上海市浦东新区"}}]},
        "Status": {"status": {"name": "Applied"}},
        "URL": {"url": job_url},
        "Requirements": {"rich_text": [{"text": {"content": "5年Python经验，熟悉Django/Flask"}}]},
        "Notes": {"rich_text": [{"text": {"content": "来源：公司官网"}}]}
    }
    
    result1 = notion_writer.upsert(first_crawl)
    print(f"   结果: {result1.operation.value} - {'成功' if result1.success else '失败'}")
    
    # 等待
    time.sleep(2)
    
    print(f"\n🕷️ 第二次爬取（来源：招聘网站，信息更详细）")
    print("-" * 50)
    
    second_crawl = {
        "Date": {"title": [{"text": {"content": f"2025-08-19-real-{timestamp}"}}]},
        "Company": {"rich_text": [{"text": {"content": "创新科技公司"}}]},
        "Position": {"rich_text": [{"text": {"content": "高级Python开发工程师"}}]},
        "Industry": {"select": {"name": "互联网/科技"}},
        "Location": {"rich_text": [{"text": {"content": "上海市浦东新区张江高科技园区"}}]},  # 更详细
        "Status": {"status": {"name": "Applied"}},
        "URL": {"url": job_url},  # 相同URL，应该更新
        "Requirements": {"rich_text": [{"text": {"content": "5年以上Python开发经验，精通Django/Flask框架，熟悉Redis/MySQL，有微服务架构经验"}}]},  # 更详细
        "Notes": {"rich_text": [{"text": {"content": "来源：招聘网站，薪资：25-40K，福利：六险一金+期权"}}]}  # 更多信息
    }
    
    result2 = notion_writer.upsert(second_crawl)
    print(f"   结果: {result2.operation.value} - {'成功' if result2.success else '失败'}")
    
    print(f"\n📊 智能去重效果:")
    if result1.success and result2.success:
        if result1.operation == WriteOperation.CREATE and result2.operation == WriteOperation.UPDATE:
            print(f"   ✅ 完美去重：相同URL的职位被正确识别并更新")
            print(f"   📋 页面ID保持一致: {result1.page_id == result2.page_id}")
            print(f"   🔄 信息得到更新和丰富")
        else:
            print(f"   ⚠️ 去重逻辑需要调整")
    
    print(f"\n💡 实际应用价值:")
    print(f"   🎯 避免重复记录：相同职位在数据库中只有一条记录")
    print(f"   📈 信息增量更新：后续爬取可以丰富现有记录")
    print(f"   🚀 自动化程度高：无需人工干预去重判断")
    print(f"   📊 数据质量保证：始终保持最新最完整的信息")
    
    return True


def main():
    """主演示函数"""
    print("🎯 NotionWriter模块完整功能演示")
    print("=" * 60)
    
    try:
        # 检查连接
        if not notion_writer.test_connection():
            print("❌ Notion连接失败，无法进行演示")
            return
        
        print("✅ Notion连接正常，开始演示...\n")
        
        # 演示各个功能
        demo_basic_operations()
        demo_upsert_intelligence()
        demo_batch_processing()
        demo_real_world_scenario()
        
        print("\n" + "="*60)
        print("🎉 演示完成！NotionWriter模块功能强大，ready for production!")
        print("🔑 核心特性：")
        print("   ✅ 智能去重 - 基于URL自动判断创建/更新")
        print("   ✅ 批量处理 - 高效处理大量数据")
        print("   ✅ 错误恢复 - 完善的异常处理机制")
        print("   ✅ 性能优化 - 合理的API调用频率控制")
        print("="*60)
        
    except Exception as e:
        print(f"❌ 演示异常: {e}")


if __name__ == "__main__":
    main()
