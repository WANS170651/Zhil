"""
Normalizer模块演示脚本
展示数据归一化和验证的完整流程
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.normalizer import normalizer, ValidationResult
from src.notion_schema import get_database_schema


def demo_data_types_normalization():
    """演示各种数据类型的归一化"""
    print("🚀 数据类型归一化演示")
    print("="*50)
    
    print("📅 日期归一化:")
    date_tests = [
        "2025-08-19",      # 标准格式
        "2025/08/19",      # 需要转换
        "19-08-2025",      # 需要转换
        "today",           # 相对日期
        "invalid-date"     # 无效日期
    ]
    
    for test_date in date_tests:
        normalized, result, message = normalizer._normalize_date(test_date)
        status_icon = {"valid": "✓", "fixed": "🔧", "invalid": "✗", "empty": "○"}.get(result.value, "?")
        print(f"   {status_icon} {test_date:15} → {normalized}")
        if message:
            print(f"      💬 {message}")
    
    print(f"\n🔢 数字归一化:")
    number_tests = [
        123,               # 整数
        "45.67",          # 字符串数字
        "1,234",          # 千分位
        "¥1,234.56",      # 货币符号
        "invalid"         # 无效数字
    ]
    
    for test_num in number_tests:
        normalized, result, message = normalizer._normalize_number(test_num)
        status_icon = {"valid": "✓", "fixed": "🔧", "invalid": "✗", "empty": "○"}.get(result.value, "?")
        print(f"   {status_icon} {test_num:15} → {normalized}")
    
    print(f"\n🔗 URL归一化:")
    url_tests = [
        "https://example.com",     # 完整URL
        "www.example.com",         # 缺少协议
        "example.com",             # 简单域名
        "invalid-url"              # 无效URL
    ]
    
    for test_url in url_tests:
        normalized, result, message = normalizer._normalize_url(test_url)
        status_icon = {"valid": "✓", "fixed": "🔧", "invalid": "✗", "empty": "○"}.get(result.value, "?")
        print(f"   {status_icon} {test_url:25} → {normalized}")


def demo_fuzzy_matching():
    """演示模糊匹配功能"""
    print(f"\n🎯 模糊匹配演示")
    print("="*30)
    
    schema = get_database_schema()
    
    # 获取Industry字段的选项
    industry_field = schema.fields.get('Industry')
    if industry_field and industry_field.options:
        print("🏭 行业字段模糊匹配:")
        print(f"   可选项: {[opt.name for opt in industry_field.options[:5]]}...")
        
        test_inputs = [
            "互联网/科技",        # 精确匹配
            "互联网科技",         # 模糊匹配
            "科技互联网",         # 模糊匹配
            "IT",                # 可能匹配
            "不存在的行业"        # 无匹配
        ]
        
        for test_input in test_inputs:
            normalized, result, message = normalizer._normalize_select(test_input, industry_field.options)
            status_icon = {"valid": "✓", "fixed": "🔧", "invalid": "✗", "empty": "○"}.get(result.value, "?")
            print(f"   {status_icon} {test_input:15} → {normalized}")
            if message:
                print(f"      💬 {message}")
    
    # 获取Status字段的选项
    status_field = schema.fields.get('Status')
    if status_field and status_field.options:
        print(f"\n📊 状态字段模糊匹配:")
        print(f"   可选项: {[opt.name for opt in status_field.options[:5]]}...")
        
        test_inputs = [
            "Applied",           # 精确匹配
            "已投递",            # 中文匹配
            "Offer",            # 精确匹配
            "面试中",            # 可能匹配
            "不存在状态"         # 无匹配
        ]
        
        for test_input in test_inputs:
            normalized, result, message = normalizer._normalize_select(test_input, status_field.options)
            status_icon = {"valid": "✓", "fixed": "🔧", "invalid": "✗", "empty": "○"}.get(result.value, "?")
            print(f"   {status_icon} {test_input:15} → {normalized}")
            if message:
                print(f"      💬 {message}")


def demo_complete_normalization():
    """演示完整的数据归一化流程"""
    print(f"\n🔄 完整归一化流程演示")
    print("="*40)
    
    schema = get_database_schema()
    
    # 模拟LLM输出的混乱数据
    messy_data = {
        "Company": "  阿里巴巴集团  ",           # 需要trim
        "Position": "高级Java开发工程师",         # 正常
        "Industry": "互联网科技",                # 需要模糊匹配到"互联网/科技"
        "Location": "杭州市余杭区",              # 正常
        "Status": "已投递",                     # 需要模糊匹配到"Applied"
        "URL": "job.alibaba.com/position/123",  # 需要添加https://
        "Date": "2025/08/19",                   # 需要格式转换
        "Requirements": "本科及以上学历，5年以上Java开发经验，熟悉Spring框架",
        "Notes": "公司实力强，发展前景好，团队技术氛围浓厚，值得加入！",
        "ExtraField": "这个字段不在Schema中"     # 额外字段，会被忽略
    }
    
    print("📋 原始数据:")
    for key, value in messy_data.items():
        print(f"   • {key}: {value}")
    
    print(f"\n🔧 执行归一化...")
    result = normalizer.normalize(messy_data, schema)
    
    print(f"\n📊 归一化结果:")
    print(f"   ✅ 成功: {result.success}")
    print(f"   📈 处理字段: {len(result.field_results)}")
    print(f"   ❌ 错误数: {result.error_count}")
    print(f"   ⚠️  警告数: {result.warning_count}")
    
    if result.notion_payload:
        print(f"   📦 Notion字段: {len(result.notion_payload)}")
    
    print(f"\n📋 字段处理详情:")
    for field_result in result.field_results:
        status_icons = {
            ValidationResult.VALID: "✅",
            ValidationResult.FIXED: "🔧", 
            ValidationResult.INVALID: "❌",
            ValidationResult.EMPTY: "⭕"
        }
        icon = status_icons.get(field_result.result, "❓")
        
        print(f"   {icon} {field_result.field_name}:")
        print(f"      输入: {field_result.original_value}")
        print(f"      输出: {field_result.normalized_value}")
        
        if field_result.warning_message:
            print(f"      ⚠️  {field_result.warning_message}")
        if field_result.error_message:
            print(f"      ❌ {field_result.error_message}")
    
    return result


def demo_notion_payload():
    """演示Notion API Payload生成"""
    print(f"\n📦 Notion API Payload演示")
    print("="*35)
    
    schema = get_database_schema()
    
    # 干净的测试数据
    clean_data = {
        "Company": "腾讯科技",
        "Position": "高级前端工程师", 
        "Industry": "互联网/科技",
        "Location": "深圳市南山区",
        "Status": "Applied",
        "URL": "https://careers.tencent.com/job/123",
        "Date": "2025-08-19",
        "Requirements": "本科及以上学历，3年以上前端开发经验"
    }
    
    result = normalizer.normalize(clean_data, schema)
    
    if result.success and result.notion_payload:
        print(f"✅ 成功生成Notion Payload，包含 {len(result.notion_payload)} 个字段")
        
        print(f"\n📄 Payload结构示例:")
        for field_name, payload in list(result.notion_payload.items())[:4]:  # 只显示前4个
            print(f"\n   📌 {field_name}:")
            print(f"      {json.dumps(payload, indent=6, ensure_ascii=False)}")
        
        print(f"\n💡 这个Payload可以直接用于Notion API创建页面:")
        print(f"   POST https://api.notion.com/v1/pages")
        print(f"   Body: {{'parent': {{'database_id': 'xxx'}}, 'properties': payload}}")
        
        return True
    else:
        print(f"❌ Payload生成失败: {result.error_message}")
        return False


def demo_strict_vs_loose_mode():
    """演示严格模式vs宽松模式"""
    print(f"\n⚖️  严格模式 vs 宽松模式对比")
    print("="*45)
    
    schema = get_database_schema()
    
    test_data = {
        "Industry": "互联网科技",  # 模糊匹配测试
        "Status": "投递中",       # 模糊匹配测试
        "Date": "2025/08/19",    # 格式转换测试
        "URL": "example.com"     # 协议添加测试
    }
    
    # 宽松模式
    print("🔓 宽松模式 (默认):")
    loose_normalizer = normalizer  # 默认就是宽松模式
    loose_result = loose_normalizer.normalize(test_data, schema)
    
    print(f"   成功: {loose_result.success}")
    print(f"   错误: {loose_result.error_count}, 警告: {loose_result.warning_count}")
    
    # 严格模式
    print(f"\n🔒 严格模式:")
    from src.normalizer import DataNormalizer
    strict_normalizer = DataNormalizer(strict_mode=True)
    strict_result = strict_normalizer.normalize(test_data, schema)
    
    print(f"   成功: {strict_result.success}")
    print(f"   错误: {strict_result.error_count}, 警告: {strict_result.warning_count}")
    
    print(f"\n🔍 对比分析:")
    print(f"   宽松模式允许模糊匹配和格式修复")
    print(f"   严格模式要求数据完全准确")
    print(f"   生产环境建议使用宽松模式，提高容错率")


def main():
    """主演示函数"""
    print("🎯 Normalizer模块完整功能演示")
    print("=" * 60)
    
    try:
        demo_data_types_normalization()
        demo_fuzzy_matching()
        result = demo_complete_normalization()
        demo_notion_payload()
        demo_strict_vs_loose_mode()
        
        print("\n" + "="*60)
        if result and result.success:
            print("🎉 演示完成！Normalizer模块功能强大，ready for production!")
        else:
            print("🔧 演示完成！Normalizer模块具备强大的数据清理能力")
        print("="*60)
        
    except Exception as e:
        print(f"❌ 演示异常: {e}")


if __name__ == "__main__":
    main()
