import asyncio
import sys
from playwright.async_api import async_playwright
import html2text
import argparse
from pathlib import Path
import time


class WebScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.h = html2text.HTML2Text()
        self.h.ignore_links = False
        self.h.ignore_images = False
        self.h.body_width = 0  # 不限制行宽
        
    async def scrape_to_markdown(self, url, output_file=None, wait_time=2):
        """
        爬取网页并转换为Markdown
        
        Args:
            url: 要爬取的网页URL
            output_file: 输出文件路径，如果为None则打印到控制台
            wait_time: 等待页面加载的时间（秒）
        """
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            
            try:
                print(f"正在访问: {url}")
                
                # 访问页面
                await page.goto(url, wait_until='networkidle')
                
                # 等待页面完全加载
                await asyncio.sleep(wait_time)
                
                # 获取页面内容
                content = await page.content()
                title = await page.title()
                
                print(f"页面标题: {title}")
                
                # 转换为Markdown
                markdown_content = self.h.handle(content)
                
                # 添加标题和元信息
                markdown_with_meta = f"""# {title}

> 来源: {url}
> 爬取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}

---

{markdown_content}
"""
                
                # 输出结果
                if output_file:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(markdown_with_meta)
                    print(f"Markdown已保存到: {output_file}")
                else:
                    print("\n" + "="*50)
                    print("转换后的Markdown内容:")
                    print("="*50)
                    print(markdown_content)
                
                return markdown_with_meta
                
            except Exception as e:
                print(f"爬取失败: {e}")
                return None
            finally:
                await browser.close()
    
    async def scrape_multiple_pages(self, urls, output_dir="output"):
        """
        批量爬取多个页面
        
        Args:
            urls: URL列表
            output_dir: 输出目录
        """
        # 创建输出目录
        Path(output_dir).mkdir(exist_ok=True)
        
        results = []
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] 处理: {url}")
            
            # 生成文件名
            filename = f"page_{i}_{int(time.time())}.md"
            output_path = Path(output_dir) / filename
            
            result = await self.scrape_to_markdown(url, str(output_path))
            results.append({
                'url': url,
                'output_file': str(output_path),
                'success': result is not None
            })
            
            # 避免请求过于频繁
            await asyncio.sleep(1)
        
        return results


async def main():
    parser = argparse.ArgumentParser(description='网页爬取并转换为Markdown')
    parser.add_argument('url', help='要爬取的网页URL')
    parser.add_argument('-o', '--output', help='输出文件路径')
    parser.add_argument('--no-headless', action='store_true', help='显示浏览器窗口')
    parser.add_argument('--wait', type=int, default=2, help='等待页面加载的时间（秒）')
    
    args = parser.parse_args()
    
    # 创建爬虫实例
    scraper = WebScraper(headless=not args.no_headless)
    
    # 执行爬取
    await scraper.scrape_to_markdown(args.url, args.output, args.wait)


if __name__ == "__main__":
    # 如果没有命令行参数，运行测试
    if len(sys.argv) == 1:
        async def test_scraper():
            scraper = WebScraper(headless=True)
            
            # 测试URL列表
            test_urls = [
                "https://campus.kuaishou.cn/recruit/campus/e/#/campus/job-info/9822"
            ]
            
            print("开始测试网页爬取...")
            
            for url in test_urls:
                print(f"\n测试爬取: {url}")
                result = await scraper.scrape_to_markdown(url)
                if result:
                    print("✓ 爬取成功")
                else:
                    print("✗ 爬取失败")
                await asyncio.sleep(2)
        
        asyncio.run(test_scraper())
    else:
        asyncio.run(main())
