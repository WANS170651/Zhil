"""
端到端测试脚本
验证整个URL信息收集和存储系统的完整功能
"""

import sys
import os
import asyncio
import time
import json
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入所有核心模块
from src.config import config
from src.notion_schema import get_database_schema, schema_api
from src.extractor import extractor
from src.normalizer import normalizer
from src.notion_writer import notion_writer
from src.main_pipeline import main_pipeline, test_pipeline_connection
from demo_script.web_scraper import WebScraper


@dataclass
class TestResult:
    """测试结果"""
    test_name: str
    success: bool
    duration: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class E2ETestSuite:
    """端到端测试套件"""
    results: List[TestResult] = field(default_factory=list)
    start_time: float = 0
    end_time: float = 0
    
    @property
    def total_tests(self) -> int:
        return len(self.results)
    
    @property
    def passed_tests(self) -> int:
        return sum(1 for r in self.results if r.success)
    
    @property
    def failed_tests(self) -> int:
        return self.total_tests - self.passed_tests
    
    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100
    
    @property
    def total_duration(self) -> float:
        return self.end_time - self.start_time if self.end_time > 0 else 0
    
    def add_result(self, result: TestResult):
        """添加测试结果"""
        self.results.append(result)
    
    def get_summary(self) -> Dict[str, Any]:
        """获取测试摘要"""
        return {
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "success_rate": round(self.success_rate, 2),
            "total_duration": round(self.total_duration, 2),
            "individual_results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "duration": round(r.duration, 2),
                    "message": r.message
                }
                for r in self.results
            ]
        }


class E2ETestRunner:
    """端到端测试运行器"""
    
    def __init__(self):
        self.suite = E2ETestSuite()
        self.test_data = self._prepare_test_data()
    
    def _prepare_test_data(self) -> Dict[str, Any]:
        """准备测试数据"""
        return {
            # 真实招聘网站URL（用于完整流程测试）
            "real_job_url": "https://campus.kuaishou.cn/recruit/campus/e/#/campus/job-info/9822",
            
            # 测试URL列表
            "test_urls": [
                "https://www.example.com/e2e-test-1",
                "https://www.example.com/e2e-test-2",
                "https://www.example.com/e2e-test-3"
            ],
            
            # 无效URL列表
            "invalid_urls": [
                "",
                "not-a-url",
                "ftp://invalid.com",
                "https://non-existent-domain-12345.com"
            ],
            
            # 预期的数据结构
            "expected_fields": [
                "Date", "Company", "Position", "Industry", 
                "Location", "Status", "URL", "Requirements", "Notes"
            ]
        }
    
    async def _run_test(self, test_name: str, test_func, *args, **kwargs) -> TestResult:
        """运行单个测试"""
        print(f"\n🧪 运行测试: {test_name}")
        print("-" * 50)
        
        start_time = time.time()
        
        try:
            result = await test_func(*args, **kwargs) if asyncio.iscoroutinefunction(test_func) else test_func(*args, **kwargs)
            
            duration = time.time() - start_time
            
            if isinstance(result, tuple):
                success, message, details = result
            elif isinstance(result, bool):
                success = result
                message = "测试完成" if success else "测试失败"
                details = {}
            else:
                success = bool(result)
                message = "测试完成"
                details = result if isinstance(result, dict) else {}
            
            test_result = TestResult(
                test_name=test_name,
                success=success,
                duration=duration,
                message=message,
                details=details
            )
            
            status = "✅ 通过" if success else "❌ 失败"
            print(f"结果: {status} (耗时: {duration:.2f}s)")
            print(f"说明: {message}")
            
            return test_result
            
        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"测试异常: {str(e)}"
            
            test_result = TestResult(
                test_name=test_name,
                success=False,
                duration=duration,
                message=error_msg,
                error=str(e)
            )
            
            print(f"结果: ❌ 异常 (耗时: {duration:.2f}s)")
            print(f"错误: {error_msg}")
            
            return test_result
    
    def test_configuration(self) -> Tuple[bool, str, Dict[str, Any]]:
        """测试配置完整性"""
        print("🔧 检查系统配置...")
        
        try:
            # 验证必需的环境变量
            config.validate()
            
            # 检查配置属性
            config_details = {
                "notion_token": bool(config.notion_token),
                "notion_database_id": bool(config.notion_database_id),
                "dashscope_api_key": bool(config.dashscope_api_key),
                "llm_model": config.llm_model,
                "log_level": config.log_level
            }
            
            print(f"   ✅ 所有必需配置项已设置")
            
            return True, "配置验证通过", config_details
            
        except Exception as e:
            return False, f"配置验证失败: {e}", {}
    
    def test_component_connections(self) -> Tuple[bool, str, Dict[str, Any]]:
        """测试组件连接"""
        print("🔗 检查组件连接...")
        
        components = {}
        
        try:
            # 测试Notion连接
            print("   🔍 测试Notion API...")
            notion_ok = notion_writer.test_connection()
            components["notion"] = notion_ok
            
            # 测试LLM连接
            print("   🧠 测试LLM连接...")
            llm_ok = extractor.test_connection()
            components["llm"] = llm_ok
            
            # 测试Schema加载
            print("   📋 测试Schema加载...")
            schema = get_database_schema()
            schema_ok = schema is not None
            components["schema"] = schema_ok
            
            # 测试管道整体连接
            print("   🔧 测试管道连接...")
            pipeline_ok = test_pipeline_connection()
            components["pipeline"] = pipeline_ok
            
            all_ok = all(components.values())
            
            if all_ok:
                return True, "所有组件连接正常", components
            else:
                failed_components = [k for k, v in components.items() if not v]
                return False, f"组件连接失败: {failed_components}", components
                
        except Exception as e:
            return False, f"组件连接测试异常: {e}", components
    
    async def test_web_scraping(self) -> Tuple[bool, str, Dict[str, Any]]:
        """测试网页爬取功能"""
        print("🕷️ 测试网页爬取功能...")
        
        scraper = WebScraper(headless=True)
        test_url = self.test_data["test_urls"][0]
        
        try:
            print(f"   📄 爬取测试URL: {test_url}")
            
            content = await scraper.scrape_to_markdown(test_url, wait_time=2)
            
            if content and len(content) > 100:
                details = {
                    "url": test_url,
                    "content_length": len(content),
                    "has_title": "# Example Domain" in content,
                    "has_content": "illustrative examples" in content
                }
                
                print(f"   ✅ 爬取成功，内容长度: {len(content)} 字符")
                
                return True, "网页爬取功能正常", details
            else:
                return False, "爬取内容为空或过短", {"content_length": len(content) if content else 0}
                
        except Exception as e:
            return False, f"网页爬取失败: {e}", {}
    
    async def test_llm_extraction(self) -> Tuple[bool, str, Dict[str, Any]]:
        """测试LLM信息提取"""
        print("🧠 测试LLM信息提取...")
        
        # 使用真实的招聘页面进行测试
        test_url = self.test_data["real_job_url"]
        
        try:
            # 先爬取内容
            print("   📄 爬取真实招聘页面...")
            scraper = WebScraper(headless=True)
            content = await scraper.scrape_to_markdown(test_url, wait_time=2)
            
            if not content:
                return False, "无法爬取测试页面内容", {}
            
            print(f"   🧠 使用LLM提取信息...")
            
            # 进行信息提取
            result = extractor.extract(
                content=content,
                url=test_url,
                max_retries=2
            )
            
            if result.success and result.data:
                extracted_fields = list(result.data.keys())
                expected_fields = self.test_data["expected_fields"]
                
                # 检查是否提取到关键字段
                key_fields_found = sum(1 for field in ["Company", "Position", "Industry"] 
                                     if field in extracted_fields)
                
                details = {
                    "extracted_fields": extracted_fields,
                    "field_count": len(extracted_fields),
                    "key_fields_found": key_fields_found,
                    "processing_time": result.processing_time,
                    "tokens_used": result.tokens_used,
                    "company": result.data.get("Company", "N/A"),
                    "position": result.data.get("Position", "N/A")
                }
                
                if key_fields_found >= 2:  # 至少找到2个关键字段
                    print(f"   ✅ 提取成功，找到 {key_fields_found} 个关键字段")
                    return True, "LLM信息提取正常", details
                else:
                    return False, f"关键字段提取不足，仅找到 {key_fields_found} 个", details
            else:
                return False, f"LLM提取失败: {result.error}", {"error": result.error}
                
        except Exception as e:
            return False, f"LLM提取测试异常: {e}", {}
    
    def test_data_normalization(self) -> Tuple[bool, str, Dict[str, Any]]:
        """测试数据归一化"""
        print("🔧 测试数据归一化...")
        
        # 准备测试数据
        test_data = {
            "Date": "2025-08-19-e2e-test",
            "Company": "测试公司",
            "Position": "测试工程师",
            "Industry": "互联网/科技",
            "Location": "北京",
            "Status": "Applied",
            "URL": "https://e2e.test.com/job/123",
            "Requirements": "3年以上工作经验",
            "Notes": "端到端测试数据"
        }
        
        try:
            print("   🔧 执行数据归一化...")
            
            # 获取数据库Schema
            schema = get_database_schema()
            if not schema:
                return False, "无法获取数据库Schema", {}
            
            # 执行归一化
            result = normalizer.normalize(test_data, schema)
            
            if result.success:
                details = {
                    "input_fields": len(test_data),
                    "output_fields": len(result.notion_payload) if result.notion_payload else 0,
                    "error_count": result.error_count,
                    "warning_count": result.warning_count,
                    "has_title": "Date" in (result.notion_payload or {}),
                    "has_url": "URL" in (result.notion_payload or {})
                }
                
                print(f"   ✅ 归一化成功，错误: {result.error_count}, 警告: {result.warning_count}")
                return True, "数据归一化正常", details
            else:
                return False, "数据归一化失败", {"error_message": result.error_message}
                
        except Exception as e:
            return False, f"数据归一化测试异常: {e}", {}
    
    def test_notion_writing(self) -> Tuple[bool, str, Dict[str, Any]]:
        """测试Notion写入功能"""
        print("💾 测试Notion写入功能...")
        
        # 准备测试数据
        timestamp = int(time.time())
        test_properties = {
            "Date": {"title": [{"text": {"content": f"2025-08-19-e2e-{timestamp}"}}]},
            "Company": {"rich_text": [{"text": {"content": "端到端测试公司"}}]},
            "Position": {"rich_text": [{"text": {"content": "E2E测试工程师"}}]},
            "Industry": {"select": {"name": "互联网/科技"}},
            "Location": {"rich_text": [{"text": {"content": "测试城市"}}]},
            "Status": {"status": {"name": "Applied"}},
            "URL": {"url": f"https://e2e-test.com/job/{timestamp}"},
            "Requirements": {"rich_text": [{"text": {"content": "端到端测试要求"}}]},
            "Notes": {"rich_text": [{"text": {"content": "这是端到端测试创建的记录"}}]}
        }
        
        try:
            print(f"   💾 写入测试数据到Notion...")
            
            # 执行写入
            result = notion_writer.upsert(test_properties, force_create=True)
            
            if result.success:
                details = {
                    "operation": result.operation.value,
                    "page_id": result.page_id,
                    "processing_time": result.processing_time,
                    "url": result.url
                }
                
                print(f"   ✅ 写入成功，操作: {result.operation.value}, 页面ID: {result.page_id}")
                return True, "Notion写入功能正常", details
            else:
                return False, f"Notion写入失败: {result.error_message}", {}
                
        except Exception as e:
            return False, f"Notion写入测试异常: {e}", {}
    
    async def test_complete_pipeline(self) -> Tuple[bool, str, Dict[str, Any]]:
        """测试完整流水线"""
        print("🚀 测试完整处理流水线...")
        
        test_url = self.test_data["real_job_url"]
        
        try:
            print(f"   🔄 执行完整流水线处理...")
            print(f"   📄 URL: {test_url}")
            
            # 执行完整流水线
            result = await main_pipeline.process_single_url(test_url)
            
            if result.success:
                details = {
                    "url": result.url,
                    "final_stage": result.stage.value,
                    "status": result.status.value,
                    "total_time": result.total_time,
                    "stage_times": result.stage_times,
                    "writing_result": result.writing_result.to_dict() if result.writing_result else None
                }
                
                print(f"   ✅ 流水线执行成功")
                print(f"   📊 总耗时: {result.total_time:.2f}秒")
                print(f"   📋 最终阶段: {result.stage.value}")
                
                if result.writing_result:
                    print(f"   💾 Notion操作: {result.writing_result.operation.value}")
                
                return True, "完整流水线正常", details
            else:
                error_details = {
                    "error_stage": result.error_stage.value if result.error_stage else None,
                    "error_message": result.error_message,
                    "stage_times": result.stage_times
                }
                
                return False, f"流水线执行失败: {result.error_message}", error_details
                
        except Exception as e:
            return False, f"完整流水线测试异常: {e}", {}
    
    async def test_batch_processing(self) -> Tuple[bool, str, Dict[str, Any]]:
        """测试批量处理"""
        print("📦 测试批量处理功能...")
        
        test_urls = self.test_data["test_urls"][:2]  # 使用前2个测试URL
        
        try:
            print(f"   📋 批量处理 {len(test_urls)} 个URL...")
            
            # 执行批量处理
            results = await main_pipeline.process_multiple_urls(test_urls)
            
            success_count = sum(1 for r in results if r.success)
            total_count = len(results)
            
            details = {
                "total_urls": total_count,
                "successful_urls": success_count,
                "failed_urls": total_count - success_count,
                "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
                "individual_results": [
                    {
                        "url": r.url,
                        "success": r.success,
                        "stage": r.stage.value,
                        "total_time": r.total_time
                    }
                    for r in results
                ]
            }
            
            if success_count > 0:
                print(f"   ✅ 批量处理完成，成功率: {success_count}/{total_count}")
                return True, "批量处理功能正常", details
            else:
                return False, "批量处理全部失败", details
                
        except Exception as e:
            return False, f"批量处理测试异常: {e}", {}
    
    async def test_error_handling(self) -> Tuple[bool, str, Dict[str, Any]]:
        """测试错误处理"""
        print("🛡️ 测试错误处理能力...")
        
        invalid_urls = self.test_data["invalid_urls"]
        error_results = []
        
        try:
            for url in invalid_urls:
                print(f"   ⚠️ 测试无效URL: {url or '(空URL)'}")
                
                result = await main_pipeline.process_single_url(url)
                
                error_results.append({
                    "url": url,
                    "success": result.success,
                    "error_stage": result.error_stage.value if result.error_stage else None,
                    "error_message": result.error_message
                })
            
            # 所有无效URL都应该失败
            all_failed_as_expected = all(not r["success"] for r in error_results)
            
            details = {
                "tested_invalid_urls": len(invalid_urls),
                "all_failed_as_expected": all_failed_as_expected,
                "error_results": error_results
            }
            
            if all_failed_as_expected:
                print(f"   ✅ 错误处理正确，所有无效URL都被正确拒绝")
                return True, "错误处理功能正常", details
            else:
                return False, "部分无效URL未被正确处理", details
                
        except Exception as e:
            return False, f"错误处理测试异常: {e}", {}
    
    async def test_performance_baseline(self) -> Tuple[bool, str, Dict[str, Any]]:
        """测试性能基准"""
        print("⚡ 测试系统性能基准...")
        
        test_url = self.test_data["test_urls"][0]
        
        try:
            # 执行多次测试以获取平均性能
            iterations = 3
            times = []
            
            print(f"   📊 执行 {iterations} 次性能测试...")
            
            for i in range(iterations):
                start_time = time.time()
                result = await main_pipeline.process_single_url(test_url)
                end_time = time.time()
                
                if result.success:
                    times.append(end_time - start_time)
                    print(f"   第 {i+1} 次: {end_time - start_time:.2f}s")
            
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                details = {
                    "iterations": iterations,
                    "successful_runs": len(times),
                    "average_time": avg_time,
                    "min_time": min_time,
                    "max_time": max_time,
                    "individual_times": times
                }
                
                # 性能基准：平均处理时间应在15秒以内
                performance_ok = avg_time <= 15.0
                
                if performance_ok:
                    print(f"   ✅ 性能基准通过，平均耗时: {avg_time:.2f}秒")
                    return True, "性能基准测试通过", details
                else:
                    print(f"   ⚠️ 性能基准不达标，平均耗时: {avg_time:.2f}秒（期望 ≤15秒）")
                    return False, f"性能不达标，平均耗时: {avg_time:.2f}秒", details
            else:
                return False, "性能测试全部失败", {}
                
        except Exception as e:
            return False, f"性能测试异常: {e}", {}
    
    async def run_all_tests(self) -> E2ETestSuite:
        """运行所有端到端测试"""
        print("🔬 开始端到端测试套件")
        print("="*60)
        
        self.suite.start_time = time.time()
        
        # 定义所有测试
        tests = [
            ("配置完整性检查", self.test_configuration),
            ("组件连接测试", self.test_component_connections),
            ("网页爬取测试", self.test_web_scraping),
            ("LLM信息提取测试", self.test_llm_extraction),
            ("数据归一化测试", self.test_data_normalization),
            ("Notion写入测试", self.test_notion_writing),
            ("完整流水线测试", self.test_complete_pipeline),
            ("批量处理测试", self.test_batch_processing),
            ("错误处理测试", self.test_error_handling),
            ("性能基准测试", self.test_performance_baseline)
        ]
        
        # 逐个执行测试
        for test_name, test_func in tests:
            result = await self._run_test(test_name, test_func)
            self.suite.add_result(result)
        
        self.suite.end_time = time.time()
        
        return self.suite
    
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*60)
        print("📊 端到端测试摘要报告")
        print("="*60)
        
        print(f"测试概况:")
        print(f"  总测试数: {self.suite.total_tests}")
        print(f"  通过测试: {self.suite.passed_tests}")
        print(f"  失败测试: {self.suite.failed_tests}")
        print(f"  成功率: {self.suite.success_rate:.1f}%")
        print(f"  总耗时: {self.suite.total_duration:.2f}秒")
        
        print(f"\n详细结果:")
        for result in self.suite.results:
            status = "✅" if result.success else "❌"
            print(f"  {status} {result.test_name}: {result.message} ({result.duration:.2f}s)")
        
        # 系统就绪评估
        print(f"\n🎯 系统就绪评估:")
        
        if self.suite.success_rate >= 90:
            print("🎉 系统完全就绪！所有核心功能正常运行")
            print("✅ 可以安全投入生产环境使用")
        elif self.suite.success_rate >= 80:
            print("✅ 系统基本就绪！大部分功能正常运行")
            print("💡 建议修复失败的测试项目后投入使用")
        elif self.suite.success_rate >= 60:
            print("⚠️ 系统部分就绪，存在一些问题")
            print("🔧 需要修复关键问题后才能投入使用")
        else:
            print("❌ 系统未就绪，存在严重问题")
            print("🚨 必须修复所有关键问题才能使用")
        
        # 保存测试报告
        self._save_test_report()
    
    def _save_test_report(self):
        """保存测试报告"""
        try:
            report_path = Path("tests/e2e_test_report.json")
            
            summary = self.suite.get_summary()
            summary["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
            summary["system_ready"] = self.suite.success_rate >= 80
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            print(f"\n📄 测试报告已保存: {report_path}")
            
        except Exception as e:
            print(f"⚠️ 保存测试报告失败: {e}")


async def main():
    """主函数"""
    print("🚀 URL信息收集和存储系统 - 端到端测试")
    print("本测试将验证整个系统的完整功能")
    print("-" * 60)
    
    # 创建测试运行器
    runner = E2ETestRunner()
    
    try:
        # 运行所有测试
        suite = await runner.run_all_tests()
        
        # 打印摘要
        runner.print_summary()
        
        # 返回结果
        return suite.success_rate >= 80
        
    except Exception as e:
        print(f"❌ 端到端测试执行异常: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    
    if success:
        print("\n🎉 端到端测试成功完成！系统ready for production！")
    else:
        print("\n⚠️ 端到端测试发现问题，请查看详细报告")
    
    exit(0 if success else 1)
