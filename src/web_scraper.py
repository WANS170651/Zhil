"""
Web爬虫模块
使用Playwright进行网页抓取和内容提取
"""

import asyncio
import logging
from typing import Optional
from playwright.async_api import async_playwright
import html2text


class WebScraper:
    """Web爬虫类"""
    
    def __init__(self, headless: bool = True):
        """
        初始化Web爬虫
        
        Args:
            headless: 是否使用无头模式
        """
        self.headless = headless
        self.logger = logging.getLogger(__name__)
        
        # 初始化HTML到Markdown转换器
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = True
        self.h2t.body_width = 0  # 不限制行宽
        
    async def scrape_to_markdown(self, url: str, wait_time: int = 2) -> Optional[str]:
        """
        爬取页面并转换为Markdown格式
        
        Args:
            url: 目标URL
            wait_time: 等待时间（秒）
            
        Returns:
            Markdown格式的页面内容，失败时返回None
        """
        try:
            async with async_playwright() as p:
                # 启动浏览器
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()
                
                # 设置用户代理
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
                
                # 访问页面
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                # 等待指定时间，确保动态内容加载
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                
                # 获取页面HTML内容
                content = await page.content()
                
                # 关闭浏览器
                await browser.close()
                
                # 转换为Markdown
                markdown = self.h2t.handle(content)
                
                # 清理和优化Markdown内容
                markdown = self._clean_markdown(markdown)
                
                self.logger.info(f"成功爬取页面: {url}, 内容长度: {len(markdown)}")
                return markdown
                
        except Exception as e:
            self.logger.error(f"爬取页面失败 {url}: {e}")
            return None
    
    def _clean_markdown(self, markdown: str) -> str:
        """
        清理和优化Markdown内容
        
        Args:
            markdown: 原始Markdown内容
            
        Returns:
            清理后的Markdown内容
        """
        if not markdown:
            return ""
        
        lines = markdown.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 移除过多的空行
            if line.strip() or (cleaned_lines and cleaned_lines[-1].strip()):
                cleaned_lines.append(line)
        
        # 限制连续空行不超过2行
        result_lines = []
        empty_count = 0
        
        for line in cleaned_lines:
            if line.strip():
                result_lines.append(line)
                empty_count = 0
            else:
                if empty_count < 2:
                    result_lines.append(line)
                empty_count += 1
        
        return '\n'.join(result_lines)
