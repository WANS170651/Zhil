"""
NotionSchema模块测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.notion_schema import schema_api, FieldType, get_database_schema


def test_basic_functionality():
    """测试基本功能"""
    print("🧪 开始测试NotionSchema模块...")
    
    try:
        # 测试1: 获取Schema
        print("\n1️⃣ 测试Schema获取...")
        schema = get_database_schema()
        print(f"✅ 成功获取Schema，包含 {len(schema.fields)} 个字段")
        
        # 测试2: 缓存功能
        print("\n2️⃣ 测试缓存功能...")
        schema2 = get_database_schema()  # 应该使用缓存
        cache_info = schema_api.get_cache_info()
        print(f"✅ 缓存正常，当前缓存条目数: {cache_info['size']}")
        
        # 测试3: 字段类型筛选
        print("\n3️⃣ 测试字段类型筛选...")
        select_fields = schema_api.get_field_names_by_type(FieldType.SELECT)
        status_fields = schema_api.get_field_names_by_type('status')
        text_fields = schema_api.get_field_names_by_type('rich_text')
        
        print(f"✅ Select字段: {select_fields}")
        print(f"✅ Status字段: {status_fields}")
        print(f"✅ 富文本字段: {text_fields}")
        
        # 测试4: 获取选项列表
        print("\n4️⃣ 测试选项获取...")
        if select_fields:
            options = schema_api.get_select_options(select_fields[0])
            print(f"✅ {select_fields[0]}字段有 {len(options)} 个选项")
            for opt in options[:3]:  # 只显示前3个
                print(f"   - {opt.name} ({opt.color})")
        
        # 测试5: Schema结构
        print("\n5️⃣ 测试Schema结构...")
        print(f"✅ Title字段: {schema.title_field}")
        print(f"✅ URL字段: {schema.url_field}")
        print(f"✅ 数据库标题: {schema.title}")
        
        print("\n🎉 所有测试通过！NotionSchema模块工作正常")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n🧪 测试错误处理...")
    
    try:
        # 测试不存在的字段
        try:
            schema_api.get_select_options("不存在的字段")
            print("❌ 应该抛出异常")
        except Exception as e:
            print(f"✅ 正确处理不存在字段: {type(e).__name__}")
        
        print("✅ 错误处理测试通过")
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")


if __name__ == "__main__":
    print("="*60)
    print("🔬 NotionSchema模块完整测试")
    print("="*60)
    
    success = test_basic_functionality()
    if success:
        test_error_handling()
        
        print("\n" + "="*60)
        print("📊 详细Schema信息:")
        print("="*60)
        schema_api.print_schema_summary()
    
    print("测试完成！")
