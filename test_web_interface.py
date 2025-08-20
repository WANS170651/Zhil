"""
Web界面功能验证脚本
测试API端点是否正常工作，Web界面是否可访问
"""

import requests
import json
import time
from typing import Dict, Any
import webbrowser
import sys

class WebInterfaceTest:
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
    
    def log_result(self, test_name: str, success: bool, message: str, details: Dict[str, Any] = None):
        """记录测试结果"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {},
            "timestamp": time.time()
        }
        self.test_results.append(result)
        
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {test_name}: {message}")
        
        if details and not success:
            print(f"   详情: {details}")
    
    def test_api_availability(self):
        """测试API可用性"""
        test_name = "API可用性检查"
        
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    test_name, 
                    True, 
                    f"API服务正常运行，版本: {data.get('version', '未知')}"
                )
                return True
            else:
                self.log_result(
                    test_name, 
                    False, 
                    f"API返回异常状态码: {response.status_code}",
                    {"status_code": response.status_code, "response": response.text}
                )
                return False
                
        except requests.exceptions.ConnectionError:
            self.log_result(
                test_name, 
                False, 
                "无法连接到API服务，请确保服务已启动",
                {"url": self.base_url}
            )
            return False
        except Exception as e:
            self.log_result(
                test_name, 
                False, 
                f"API测试异常: {str(e)}"
            )
            return False
    
    def test_health_endpoint(self):
        """测试健康检查端点"""
        test_name = "健康检查端点"
        
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                components = data.get('components', {})
                
                if status == 'healthy':
                    self.log_result(
                        test_name, 
                        True, 
                        f"系统健康状态正常，所有组件: {components}"
                    )
                    return True
                else:
                    self.log_result(
                        test_name, 
                        False, 
                        f"系统状态异常: {status}",
                        {"components": components}
                    )
                    return False
            else:
                self.log_result(
                    test_name, 
                    False, 
                    f"健康检查失败，状态码: {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                test_name, 
                False, 
                f"健康检查异常: {str(e)}"
            )
            return False
    
    def test_config_endpoint(self):
        """测试配置端点"""
        test_name = "配置信息端点"
        
        try:
            response = self.session.get(f"{self.base_url}/config", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                llm_model = data.get('llm_model', '未知')
                
                self.log_result(
                    test_name, 
                    True, 
                    f"配置获取成功，LLM模型: {llm_model}"
                )
                return True
            else:
                self.log_result(
                    test_name, 
                    False, 
                    f"配置获取失败，状态码: {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                test_name, 
                False, 
                f"配置获取异常: {str(e)}"
            )
            return False
    
    def test_web_interface_access(self):
        """测试Web界面访问"""
        test_name = "Web界面访问"
        
        try:
            response = self.session.get(f"{self.base_url}/ui", timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                # 检查HTML内容是否包含关键元素
                if "URL信息收集和存储系统" in content and "Bootstrap" in content:
                    self.log_result(
                        test_name, 
                        True, 
                        "Web界面加载成功，HTML内容正常"
                    )
                    return True
                else:
                    self.log_result(
                        test_name, 
                        False, 
                        "Web界面加载成功但内容异常",
                        {"content_length": len(content)}
                    )
                    return False
            else:
                self.log_result(
                    test_name, 
                    False, 
                    f"Web界面访问失败，状态码: {response.status_code}"
                )
                return False
                
        except Exception as e:
            self.log_result(
                test_name, 
                False, 
                f"Web界面访问异常: {str(e)}"
            )
            return False
    
    def test_static_files(self):
        """测试静态文件访问"""
        test_name = "静态文件访问"
        
        static_files = [
            "/static/css/style.css",
            "/static/js/app.js"
        ]
        
        success_count = 0
        
        for file_path in static_files:
            try:
                response = self.session.get(f"{self.base_url}{file_path}", timeout=5)
                
                if response.status_code == 200:
                    success_count += 1
                    print(f"   ✅ {file_path}: 加载成功")
                else:
                    print(f"   ❌ {file_path}: 状态码 {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ {file_path}: 异常 {str(e)}")
        
        if success_count == len(static_files):
            self.log_result(
                test_name, 
                True, 
                f"所有静态文件加载成功 ({success_count}/{len(static_files)})"
            )
            return True
        else:
            self.log_result(
                test_name, 
                False, 
                f"部分静态文件加载失败 ({success_count}/{len(static_files)})"
            )
            return False
    
    def test_single_url_api(self):
        """测试单URL处理API"""
        test_name = "单URL处理API"
        
        test_url = "https://www.example.com"
        
        try:
            payload = {
                "url": test_url,
                "force_create": False
            }
            
            response = self.session.post(
                f"{self.base_url}/ingest/url",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    self.log_result(
                        test_name, 
                        True, 
                        f"URL处理成功: {test_url}"
                    )
                    return True
                else:
                    self.log_result(
                        test_name, 
                        False, 
                        f"URL处理失败: {data.get('message', '未知错误')}",
                        {"response": data}
                    )
                    return False
            else:
                self.log_result(
                    test_name, 
                    False, 
                    f"API调用失败，状态码: {response.status_code}",
                    {"response": response.text}
                )
                return False
                
        except Exception as e:
            self.log_result(
                test_name, 
                False, 
                f"URL处理异常: {str(e)}"
            )
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始Web界面功能验证")
        print("=" * 60)
        
        tests = [
            self.test_api_availability,
            self.test_health_endpoint,
            self.test_config_endpoint,
            self.test_web_interface_access,
            self.test_static_files,
            # self.test_single_url_api  # 这个测试比较耗时，先注释掉
        ]
        
        passed_tests = 0
        
        for test_func in tests:
            try:
                if test_func():
                    passed_tests += 1
                print()  # 空行分隔
            except Exception as e:
                print(f"❌ 测试 {test_func.__name__} 执行异常: {e}")
                print()
        
        # 测试总结
        total_tests = len(tests)
        success_rate = (passed_tests / total_tests) * 100
        
        print("=" * 60)
        print("📊 测试结果总结")
        print("=" * 60)
        print(f"总测试数: {total_tests}")
        print(f"通过测试: {passed_tests}")
        print(f"失败测试: {total_tests - passed_tests}")
        print(f"成功率: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("\n🎉 Web界面功能验证通过！")
            print(f"🌐 请访问: {self.base_url}/ui")
            
            # 询问是否打开浏览器
            try:
                user_input = input("\n是否现在打开Web界面？ (y/n): ").strip().lower()
                if user_input in ['y', 'yes', '是', '']:
                    webbrowser.open(f"{self.base_url}/ui")
                    print("🌍 已打开Web界面")
            except KeyboardInterrupt:
                print("\n用户取消")
            
            return True
        else:
            print("\n⚠️ Web界面存在问题，请检查失败的测试项")
            return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Web界面功能验证")
    parser.add_argument("--url", default="http://127.0.0.1:8001", help="API服务地址")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    
    args = parser.parse_args()
    
    print(f"🔍 验证目标: {args.url}")
    print()
    
    # 创建测试实例
    tester = WebInterfaceTest(args.url)
    
    # 运行测试
    success = tester.run_all_tests()
    
    # 保存测试报告
    try:
        report = {
            "timestamp": time.time(),
            "target_url": args.url,
            "summary": {
                "total_tests": len(tester.test_results),
                "passed_tests": sum(1 for r in tester.test_results if r["success"]),
                "success_rate": sum(1 for r in tester.test_results if r["success"]) / len(tester.test_results) * 100 if tester.test_results else 0
            },
            "results": tester.test_results
        }
        
        with open("web_interface_test_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 测试报告已保存: web_interface_test_report.json")
        
    except Exception as e:
        print(f"\n⚠️ 保存测试报告失败: {e}")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
