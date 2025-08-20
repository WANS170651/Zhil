"""
LLM Schema Builder模块测试脚本
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.notion_schema import get_database_schema
from src.llm_schema_builder import schema_builder, build_function_call_schema, build_system_prompt


def test_json_schema_building():
    """测试JSON Schema构建"""
    print("🧪 测试JSON Schema构建...")
    
    try:
        # 获取Notion Schema
        notion_schema = get_database_schema()
        
        # 构建JSON Schema
        json_schema = schema_builder.build_json_schema(notion_schema)
        
        print(f"✅ JSON Schema构建成功")
        print(f"   字段数量: {len(json_schema['properties'])}")
        print(f"   必填字段: {json_schema['required']}")
        print(f"   类型: {json_schema['type']}")
        
        # 验证基本结构
        assert json_schema["type"] == "object"
        assert "properties" in json_schema
        assert "required" in json_schema
        assert isinstance(json_schema["properties"], dict)
        assert isinstance(json_schema["required"], list)
        
        # 显示一些字段详情
        print("\n📋 字段详情（前3个）:")
        for i, (field_name, field_def) in enumerate(json_schema["properties"].items()):
            if i >= 3:
                break
            print(f"   • {field_name}:")
            print(f"     类型: {field_def.get('type', 'unknown')}")
            if 'enum' in field_def:
                print(f"     枚举: {field_def['enum'][:3]}...")
            if 'description' in field_def:
                print(f"     描述: {field_def['description'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ JSON Schema构建失败: {e}")
        return False


def test_function_call_schema():
    """测试OpenAI函数调用Schema"""
    print("\n🧪 测试函数调用Schema...")
    
    try:
        # 获取Notion Schema
        notion_schema = get_database_schema()
        
        # 构建函数调用Schema
        function_schema = schema_builder.build_function_call_schema(notion_schema)
        
        print(f"✅ 函数调用Schema构建成功")
        print(f"   函数名: {function_schema.name}")
        print(f"   描述长度: {len(function_schema.description)} 字符")
        
        # 转换为字典格式
        function_dict = function_schema.to_dict()
        
        # 验证结构
        assert "name" in function_dict
        assert "description" in function_dict
        assert "parameters" in function_dict
        assert function_dict["parameters"]["type"] == "object"
        
        print(f"   参数字段数: {len(function_dict['parameters']['properties'])}")
        print(f"   必填参数: {function_dict['parameters']['required']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 函数调用Schema构建失败: {e}")
        return False


def test_system_prompt():
    """测试系统提示词生成"""
    print("\n🧪 测试系统提示词生成...")
    
    try:
        # 获取Notion Schema
        notion_schema = get_database_schema()
        
        # 生成系统提示词
        system_prompt = schema_builder.build_system_prompt(notion_schema)
        
        print(f"✅ 系统提示词生成成功")
        print(f"   提示词长度: {len(system_prompt)} 字符")
        
        # 验证包含关键信息
        assert notion_schema.title in system_prompt
        assert "必填字段" in system_prompt or "字段要求" in system_prompt
        assert "提取规则" in system_prompt
        
        # 显示提示词摘要
        lines = system_prompt.split('\n')
        print(f"   行数: {len(lines)}")
        print(f"   开头: {lines[0][:60]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 系统提示词生成失败: {e}")
        return False


def test_example_output():
    """测试示例输出生成"""
    print("\n🧪 测试示例输出生成...")
    
    try:
        # 获取Notion Schema
        notion_schema = get_database_schema()
        
        # 生成示例输出
        example = schema_builder.generate_example_output(notion_schema)
        
        print(f"✅ 示例输出生成成功")
        print(f"   示例字段数: {len(example)}")
        
        # 显示示例数据
        print("\n📝 示例数据:")
        for field_name, value in list(example.items())[:5]:  # 只显示前5个
            print(f"   • {field_name}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ 示例输出生成失败: {e}")
        return False


def test_enum_handling():
    """测试枚举选项处理"""
    print("\n🧪 测试枚举选项处理...")
    
    try:
        # 获取Notion Schema
        notion_schema = get_database_schema()
        
        # 构建JSON Schema
        json_schema = schema_builder.build_json_schema(notion_schema)
        
        # 查找枚举字段
        enum_fields = []
        for field_name, field_def in json_schema["properties"].items():
            if "enum" in field_def:
                enum_fields.append(field_name)
        
        print(f"✅ 找到 {len(enum_fields)} 个枚举字段")
        
        for field_name in enum_fields:
            field_def = json_schema["properties"][field_name]
            print(f"   • {field_name}: {len(field_def['enum'])} 个选项")
            print(f"     选项: {field_def['enum'][:3]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 枚举选项处理失败: {e}")
        return False


def test_convenience_functions():
    """测试便捷函数"""
    print("\n🧪 测试便捷函数...")
    
    try:
        # 获取Notion Schema
        notion_schema = get_database_schema()
        
        # 测试便捷函数
        function_dict = build_function_call_schema(notion_schema)
        system_prompt = build_system_prompt(notion_schema)
        
        print(f"✅ 便捷函数测试成功")
        print(f"   build_function_call_schema: {type(function_dict).__name__}")
        print(f"   build_system_prompt: {len(system_prompt)} 字符")
        
        return True
        
    except Exception as e:
        print(f"❌ 便捷函数测试失败: {e}")
        return False


def save_example_outputs():
    """保存示例输出到文件（用于调试）"""
    print("\n💾 保存示例输出到文件...")
    
    try:
        # 获取Notion Schema
        notion_schema = get_database_schema()
        
        # 生成各种Schema
        json_schema = schema_builder.build_json_schema(notion_schema)
        function_schema = schema_builder.build_function_call_schema(notion_schema).to_dict()
        system_prompt = schema_builder.build_system_prompt(notion_schema)
        example_output = schema_builder.generate_example_output(notion_schema)
        
        # 保存到文件
        outputs = {
            "json_schema": json_schema,
            "function_schema": function_schema,
            "system_prompt": system_prompt,
            "example_output": example_output
        }
        
        output_file = "tests/llm_schema_examples.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(outputs, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 示例输出已保存到: {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ 保存示例输出失败: {e}")
        return False


def main():
    """主测试函数"""
    print("="*60)
    print("🔬 LLM Schema Builder模块完整测试")
    print("="*60)
    
    tests = [
        test_json_schema_building,
        test_function_call_schema,
        test_system_prompt,
        test_example_output,
        test_enum_handling,
        test_convenience_functions,
        save_example_outputs
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ 测试 {test_func.__name__} 异常: {e}")
    
    print("\n" + "="*60)
    print(f"📊 测试结果: {passed}/{total} 通过")
    print("="*60)
    
    if passed == total:
        print("🎉 所有测试通过！LLM Schema Builder模块工作正常")
    else:
        print("⚠️ 部分测试失败，请检查上述错误信息")


if __name__ == "__main__":
    main()
