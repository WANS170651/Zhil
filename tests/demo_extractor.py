"""
Extractor模块演示脚本
展示完整的LLM内容抽取流程
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.extractor import extractor, ExtractionMode
from src.notion_schema import get_database_schema


def demo_extraction_process():
    """演示完整的抽取流程"""
    print("🚀 Extractor模块功能演示")
    print("="*50)
    
    # 1. 显示当前数据库Schema
    print("📊 当前数据库Schema:")
    schema = get_database_schema()
    print(f"   数据库: {schema.title}")
    print(f"   字段数: {len(schema.fields)}")
    print(f"   必填字段: {schema.title_field}")
    
    # 显示枚举字段
    enum_fields = []
    for field_name, field in schema.fields.items():
        if field.options:
            enum_fields.append(f"{field_name}({len(field.options)}选项)")
    print(f"   枚举字段: {', '.join(enum_fields)}")
    
    # 2. 演示内容抽取
    print(f"\n💼 演示招聘信息抽取:")
    print("-" * 30)
    
    sample_job = {
        "content": """
阿里巴巴 - 云计算架构师

【基本信息】
公司名称：阿里巴巴集团
职位名称：高级云计算架构师
工作地点：杭州市余杭区
所属行业：互联网/科技
发布时间：2025年8月19日

【职位描述】
负责阿里云基础设施架构设计和优化，参与大规模分布式系统建设，
为客户提供稳定可靠的云计算服务。

【岗位要求】
• 计算机或相关专业硕士及以上学历
• 8年以上大型分布式系统开发经验
• 精通Java、Go、Python等编程语言
• 熟悉Docker、Kubernetes等容器技术
• 有公有云平台架构经验者优先

【薪资福利】
• 薪资范围：60K-100K/月
• 16薪 + 年终奖 + 股权激励
• 六险一金 + 商业保险
• 弹性工作 + 带薪年假
• 技术培训 + 职业发展通道

联系邮箱：jobs@alibaba-inc.com
""",
        "url": "https://job.alibaba.com/zhaopin/position_detail.htm?positionId=123456"
    }
    
    # 打印样本内容摘要
    lines = sample_job["content"].strip().split('\n')
    print(f"   内容长度: {len(sample_job['content'])} 字符")
    print(f"   内容行数: {len(lines)} 行")
    print(f"   URL: {sample_job['url']}")
    
    # 3. 执行抽取
    print(f"\n🔄 正在抽取...")
    
    result = extractor.extract(
        content=sample_job["content"],
        url=sample_job["url"],
        mode=ExtractionMode.FUNCTION_CALL
    )
    
    # 4. 展示结果
    if result.success:
        print(f"✅ 抽取成功!")
        print(f"   处理时间: {result.processing_time:.2f}秒")
        print(f"   Token消耗: {result.tokens_used}")
        print(f"   抽取模式: {result.mode}")
        
        print(f"\n📋 抽取结果:")
        print("-" * 30)
        
        if result.data:
            for field_name, value in result.data.items():
                if value:  # 只显示非空字段
                    # 处理长文本显示
                    if isinstance(value, str) and len(value) > 80:
                        display_value = value[:80] + "..."
                    else:
                        display_value = value
                    
                    # 检查是否为枚举字段
                    field_info = schema.fields.get(field_name)
                    if field_info and field_info.options:
                        options = [opt.name for opt in field_info.options]
                        is_valid = value in options
                        status = "✓" if is_valid else "⚠"
                        print(f"   {status} {field_name}: {display_value}")
                        if not is_valid:
                            print(f"       (可选: {options[:3]}...)")
                    else:
                        print(f"   ✓ {field_name}: {display_value}")
        
        print(f"\n🎯 数据验证:")
        print(f"   必填字段检查: {'✓' if result.data.get(schema.title_field) else '✗'}")
        print(f"   URL字段设置: {'✓' if result.data.get(schema.url_field) == sample_job['url'] else '✗'}")
        
        # 枚举字段验证
        enum_valid_count = 0
        enum_total_count = 0
        for field_name, field in schema.fields.items():
            if field.options and field_name in result.data:
                enum_total_count += 1
                if result.data[field_name] in [opt.name for opt in field.options]:
                    enum_valid_count += 1
        
        if enum_total_count > 0:
            print(f"   枚举字段验证: {enum_valid_count}/{enum_total_count} 通过")
        
    else:
        print(f"❌ 抽取失败: {result.error}")
    
    return result.success


def demo_batch_processing():
    """演示批量处理能力"""
    print(f"\n🚀 批量处理演示")
    print("="*30)
    
    # 模拟多个招聘信息
    batch_jobs = [
        {
            "content": "美团 - 高级产品经理，负责外卖业务产品规划，地点北京，互联网/科技行业",
            "url": "https://zhaopin.meituan.com/jobs/001"
        },
        {
            "content": "字节跳动 - 数据科学家，TikTok数据分析，上海，互联网/科技",
            "url": "https://jobs.bytedance.com/position/002"
        }
    ]
    
    print(f"📋 准备批量处理 {len(batch_jobs)} 个职位...")
    
    # 执行批量处理
    results = extractor.batch_extract(batch_jobs)
    
    # 统计结果
    success_count = sum(1 for r in results if r.success)
    total_time = sum(r.processing_time for r in results if r.processing_time)
    total_tokens = sum(r.tokens_used for r in results if r.tokens_used)
    
    print(f"\n📊 批量处理结果:")
    print(f"   成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
    print(f"   总耗时: {total_time:.2f}秒")
    print(f"   总Token: {total_tokens}")
    print(f"   平均耗时: {total_time/len(results):.2f}秒/个")
    
    # 显示部分结果
    for i, result in enumerate(results):
        if result.success and result.data:
            company = result.data.get('Company', '未知公司')
            position = result.data.get('Position', '未知职位')
            print(f"   [{i+1}] {company} - {position}")


def demo_different_modes():
    """演示不同抽取模式"""
    print(f"\n🔄 抽取模式对比演示")
    print("="*35)
    
    sample_content = "腾讯招聘算法工程师，地点深圳，互联网/科技行业，负责推荐算法优化"
    sample_url = "https://careers.tencent.com/job/test"
    
    modes = [
        (ExtractionMode.FUNCTION_CALL, "函数调用模式"),
        (ExtractionMode.JSON_RESPONSE, "JSON响应模式")
    ]
    
    for mode, mode_name in modes:
        print(f"\n🧪 {mode_name}:")
        result = extractor.extract(sample_content, sample_url, mode=mode)
        
        if result.success:
            print(f"   ✅ 成功 - 耗时: {result.processing_time:.2f}s")
            if result.data:
                fields_count = len([v for v in result.data.values() if v])
                print(f"   📊 有效字段: {fields_count}个")
        else:
            print(f"   ❌ 失败: {result.error}")


def main():
    """主演示函数"""
    print("🎯 Extractor模块完整功能演示")
    print("=" * 60)
    
    try:
        # 演示核心抽取流程
        success1 = demo_extraction_process()
        
        # 演示批量处理
        demo_batch_processing()
        
        # 演示不同模式
        demo_different_modes()
        
        print("\n" + "="*60)
        if success1:
            print("🎉 演示完成！Extractor模块功能强大，ready for production!")
        else:
            print("⚠️ 演示中发现问题，请检查配置和网络连接")
        print("="*60)
        
    except Exception as e:
        print(f"❌ 演示异常: {e}")


if __name__ == "__main__":
    main()
