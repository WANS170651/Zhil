import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_VERSION = os.getenv("NOTION_VERSION", "2022-06-28")

BASE_URL = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

def create_page(
    date_title: str,
    company: str,
    location: str,
    industry_name: str,
    position: str,
    requirements: str,
    status_name: str,
    url_value: str,
    notes: str,
):
    """根据你的字段创建一条记录。
    约定：Date 是 title；Industry 是 select；Status 是 status。
    """

    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Date": {"title": [{"text": {"content": date_title}}]},
            "Company": {"rich_text": [{"text": {"content": company}}]},
            "Location": {"rich_text": [{"text": {"content": location}}]},
            "Position": {"rich_text": [{"text": {"content": position}}]},
            "Requirements": {"rich_text": [{"text": {"content": requirements}}]},
            "Notes": {"rich_text": [{"text": {"content": notes}}]},
            "Industry": {"select": {"name": industry_name}},
            "Status": {"status": {"name": status_name}},
            "URL": {"url": url_value},
        },
    }

    url = f"{BASE_URL}/pages"
    resp = requests.post(url, headers=HEADERS, data=json.dumps(payload))
    if not resp.ok:
        print(f"Error creating page: {resp.status_code} - {resp.text}")
        return None

    data = resp.json()
    print("Page created successfully.")
    # 打印生成的 Page ID，作为唯一标识
    print("Page ID:", data.get("id"))
    return data


if __name__ == "__main__":

    sample = dict(
        date_title="2025-08-18",
        company="快手123",
        location="北京",
        industry_name="互联网/科技",     # 若 400 提示选项不存在，请先在 UI 新建或改成已有
        position="数据分析师",
        requirements="熟悉 SQL、会数据建模与可视化",
        status_name="Applied",       # 必须与 UI 中 Status 的选项名完全一致
        url_value="https://example.com/job/123",
        notes="备注：优先考虑",
    )
    create_page(**sample)

