"""
LLM Schema Builder演示脚本
展示如何使用LLM Schema Builder为不同场景生成Schema
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.notion_schema import get_database_schema
from src.llm_schema_builder import build_function_call_schema, build_system_prompt


def demo_openai_function_call():
    """演示OpenAI函数调用集成"""
    print("🚀 OpenAI函数调用集成演示")
    print("="*50)
    
    # 获取Schema
    notion_schema = get_database_schema()
    
    # 生成函数调用Schema
    function_schema = build_function_call_schema(notion_schema)
    system_prompt = build_system_prompt(notion_schema)
    
    print("📋 函数调用配置:")
    print(f"函数名: {function_schema['name']}")
    print(f"参数数量: {len(function_schema['parameters']['properties'])}")
    print(f"必填参数: {function_schema['parameters']['required']}")
    
    print("\n💬 模拟LLM调用代码:")
    print("""
from openai import OpenAI

client = OpenAI(
    api_key="your-api-key",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

response = client.chat.completions.create(
    model="qwen-flash",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "网页内容: " + scraped_content}
    ],
    functions=[function_schema],
    function_call={"name": "extract_job_info"}
)

# 获取函数调用结果
function_call = response.choices[0].message.function_call
extracted_data = json.loads(function_call.arguments)
""")
    
    print("\n✨ 这就是完整的LLM集成方案！")


def demo_schema_validation():
    """演示Schema验证能力"""
    print("\n🔍 Schema验证能力演示")
    print("="*50)
    
    notion_schema = get_database_schema()
    function_schema = build_function_call_schema(notion_schema)
    
    # 模拟LLM输出
    mock_llm_output = {
        "Date": "2025-08-19",
        "Company": "字节跳动",
        "Position": "高级前端工程师",
        "Industry": "互联网/科技",  # 正确的枚举值
        "Status": "Applied",       # 正确的枚举值
        "URL": "https://job.bytedance.com/example",
        "Location": "北京·朝阳区",
        "Requirements": "3年以上前端开发经验，精通React/Vue",
        "Notes": "公司前景不错，团队氛围好"
    }
    
    print("✅ 有效的LLM输出示例:")
    for key, value in mock_llm_output.items():
        field_def = function_schema['parameters']['properties'].get(key, {})
        if 'enum' in field_def:
            status = "✓" if value in field_def['enum'] else "✗"
            print(f"  {status} {key}: {value} (枚举字段)")
        else:
            print(f"  ✓ {key}: {value}")
    
    print("\n❌ 无效输出示例:")
    invalid_output = mock_llm_output.copy()
    invalid_output["Industry"] = "自创行业"  # 不在枚举中
    invalid_output["Status"] = "自定义状态"   # 不在枚举中
    
    for key, value in invalid_output.items():
        field_def = function_schema['parameters']['properties'].get(key, {})
        if 'enum' in field_def:
            status = "✓" if value in field_def['enum'] else "✗"
            print(f"  {status} {key}: {value}")
            if status == "✗":
                print(f"      可选: {field_def['enum']}")


if __name__ == "__main__":
    print("🎯 LLM Schema Builder功能演示")
    print("=" * 60)
    
    demo_openai_function_call()
    demo_schema_validation()
    
    print("\n🎉 演示完成！LLM Schema Builder已ready for production！")
