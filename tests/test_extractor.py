"""
Extractor模块测试脚本
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.extractor import extractor, ExtractionMode, extract_from_content


def test_connection():
    """测试LLM连接"""
    print("🧪 测试LLM连接...")
    
    try:
        result = extractor.test_connection()
        if result:
            print("✅ LLM连接测试通过")
            return True
        else:
            print("❌ LLM连接测试失败")
            return False
    except Exception as e:
        print(f"❌ LLM连接测试异常: {e}")
        return False


def test_function_call_extraction():
    """测试函数调用模式抽取"""
    print("\n🧪 测试函数调用模式抽取...")
    
    # 模拟网页内容
    sample_content = """
# 字节跳动 - 高级前端工程师

**公司**: 字节跳动
**职位**: 高级前端工程师
**地点**: 北京·朝阳区
**行业**: 互联网/科技

## 职位要求
- 3年以上前端开发经验
- 精通React、Vue等主流框架
- 熟悉JavaScript、TypeScript
- 有移动端开发经验优先

## 公司介绍
字节跳动是一家全球领先的科技公司，旗下产品包括抖音、今日头条等。

**薪资**: 面议
**福利**: 五险一金、带薪年假、弹性工作
"""
    
    sample_url = "https://job.bytedance.com/position/7123456789"
    
    try:
        result = extractor.extract(
            content=sample_content,
            url=sample_url,
            mode=ExtractionMode.FUNCTION_CALL
        )
        
        print(f"✅ 抽取结果:")
        print(f"   成功: {result.success}")
        if result.success and result.data:
            print(f"   数据字段数: {len(result.data)}")
            print(f"   处理时间: {result.processing_time:.2f}s")
            print(f"   Token使用: {result.tokens_used}")
            
            # 显示关键字段
            key_fields = ['Company', 'Position', 'Industry', 'Location', 'URL']
            print(f"\n📋 关键字段:")
            for field in key_fields:
                if field in result.data:
                    print(f"   • {field}: {result.data[field]}")
        else:
            print(f"   错误: {result.error}")
        
        return result.success
        
    except Exception as e:
        print(f"❌ 函数调用模式测试失败: {e}")
        return False


def test_json_response_extraction():
    """测试JSON响应模式抽取"""
    print("\n🧪 测试JSON响应模式抽取...")
    
    sample_content = """
快手 - 数据分析师

公司名称: 快手科技
招聘职位: 高级数据分析师
工作地点: 北京市海淀区
所属行业: 互联网/科技

岗位职责:
1. 负责产品数据分析和用户行为分析
2. 建立数据指标体系和监控体系  
3. 为产品优化提供数据支持

任职要求:
- 本科及以上学历，统计学、数学等相关专业
- 3年以上数据分析工作经验
- 精通SQL、Python、Excel等工具
- 具备良好的逻辑思维和沟通能力

福利待遇: 13薪 + 股票期权 + 弹性工作制
"""
    
    sample_url = "https://zhaopin.kuaishou.com/jobs/123456"
    
    try:
        result = extractor.extract(
            content=sample_content,
            url=sample_url,
            mode=ExtractionMode.JSON_RESPONSE
        )
        
        print(f"✅ JSON响应抽取结果:")
        print(f"   成功: {result.success}")
        if result.success and result.data:
            print(f"   数据字段数: {len(result.data)}")
            print(f"   处理时间: {result.processing_time:.2f}s")
            
            # 显示部分数据
            for field, value in list(result.data.items())[:4]:
                print(f"   • {field}: {value}")
        else:
            print(f"   错误: {result.error}")
        
        return result.success
        
    except Exception as e:
        print(f"❌ JSON响应模式测试失败: {e}")
        return False


def test_error_handling():
    """测试错误处理"""
    print("\n🧪 测试错误处理...")
    
    try:
        # 测试空内容
        result = extractor.extract(
            content="",
            url="https://example.com"
        )
        print(f"   空内容测试: {'通过' if not result.success else '未通过'}")
        
        # 测试无效URL  
        result = extractor.extract(
            content="一些内容",
            url=""
        )
        print(f"   空URL测试: {'处理' if result else '异常'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False


def test_convenience_function():
    """测试便捷函数"""
    print("\n🧪 测试便捷函数...")
    
    try:
        result_dict = extract_from_content(
            content="测试公司招聘前端工程师，地点北京",
            url="https://test.com/job/123"
        )
        
        print(f"✅ 便捷函数测试:")
        print(f"   返回类型: {type(result_dict).__name__}")
        print(f"   成功: {result_dict.get('success', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 便捷函数测试失败: {e}")
        return False


def test_real_job_extraction():
    """测试真实招聘信息抽取"""
    print("\n🧪 测试真实招聘信息抽取...")
    
    # 更真实的招聘信息
    real_job_content = """
腾讯 - 高级Java开发工程师

【职位信息】
职位名称：高级Java开发工程师
所在部门：微信事业群
工作地点：深圳市南山区腾讯滨海大厦
薪资范围：25K-40K

【岗位职责】
1. 负责微信后台核心业务系统的开发和维护
2. 参与系统架构设计，保证系统的高可用性和扩展性
3. 优化系统性能，解决高并发场景下的技术难题
4. 指导初中级工程师，提升团队整体技术水平

【任职要求】
1. 计算机相关专业本科及以上学历
2. 5年以上Java开发经验，熟悉Spring、MyBatis等框架
3. 熟悉分布式系统设计，有大型互联网项目经验
4. 熟悉Redis、MySQL、消息队列等中间件
5. 良好的代码规范和文档编写习惯

【福利待遇】
- 薪资：25-40K * 14薪
- 股票期权
- 六险一金
- 免费三餐 + 下午茶
- 年度体检 + 带薪年假
- 技术培训 + 内部转岗机会

【联系方式】
邮箱：hr@tencent.com
电话：0755-86013388

发布时间：2025年8月19日
有效期至：2025年9月19日
"""
    
    real_url = "https://careers.tencent.com/tencentcareer/api/post/Query?PostId=1654321"
    
    try:
        print(f"   正在抽取真实招聘信息...")
        
        result = extractor.extract(
            content=real_job_content,
            url=real_url,
            mode=ExtractionMode.FUNCTION_CALL
        )
        
        if result.success:
            print(f"✅ 真实信息抽取成功!")
            print(f"   处理时间: {result.processing_time:.2f}s")
            print(f"   Token使用: {result.tokens_used}")
            
            # 详细显示抽取结果
            print(f"\n📊 抽取结果详情:")
            if result.data:
                for field, value in result.data.items():
                    if value:  # 只显示非空字段
                        # 截断长文本
                        display_value = str(value)
                        if len(display_value) > 50:
                            display_value = display_value[:50] + "..."
                        print(f"   • {field}: {display_value}")
                        
            return True
        else:
            print(f"❌ 真实信息抽取失败: {result.error}")
            return False
            
    except Exception as e:
        print(f"❌ 真实信息抽取测试异常: {e}")
        return False


def main():
    """主测试函数"""
    print("="*60)
    print("🔬 Extractor模块完整测试")
    print("="*60)
    
    tests = [
        test_connection,
        test_function_call_extraction,
        test_json_response_extraction,
        test_error_handling,
        test_convenience_function,
        test_real_job_extraction
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
        print("🎉 所有测试通过！Extractor模块工作正常")
    else:
        print("⚠️ 部分测试失败，请检查上述错误信息")
        
    return passed == total


if __name__ == "__main__":
    main()
