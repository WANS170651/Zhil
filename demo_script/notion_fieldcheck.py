import os
import json
import requests
from pprint import pprint
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


def print_http_error(resp: requests.Response):
    """打印更友好的错误信息"""
    print(f"[HTTP {resp.status_code}] URL: {resp.request.method} {resp.url}")
    try:
        data = resp.json()
        print("- Error JSON:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        # 常见定位：字段名/类型/状态名不匹配
        msg = data.get("message")
        code = data.get("code")
        if msg:
            print(f"- message: {msg}")
        if code:
            print(f"- code: {code}")
    except Exception:
        print("- Raw text:")
        print(resp.text)


def get_database_schema():
    """拉取数据库 schema，核对字段真实名字与类型（尤其 title/status/select）"""
    url = f"{BASE_URL}/databases/{DATABASE_ID}"
    resp = requests.get(url, headers=HEADERS)
    if not resp.ok:
        print_http_error(resp)
        return None

    data = resp.json()
    print("✅ Database schema fetched.\n")
    # 打印 title 字段 & 列出每个属性名和类型
    props = data.get("properties", {})
    title_field = None
    for name, meta in props.items():
        if meta.get("type") == "title":
            title_field = name
            break

    print(f"Title 属性名: {title_field}\n")
    print("属性列表（名称 → 类型）:")
    for name, meta in props.items():
        print(f"- {name} → {meta.get('type')}")

    # 打印 Status 与 Select 的可选项，方便对照
    for name, meta in props.items():
        t = meta.get("type")
        if t == "status":
            opts = meta.get("status", {}).get("options", [])
            print(f"\nStatus 选项（{name}）:")
            for o in opts:
                print(f"  - {o.get('name')}")
        elif t == "select":
            opts = meta.get("select", {}).get("options", [])
            print(f"\nSelect 选项（{name}）:")
            for o in opts:
                print(f"  - {o.get('name')}")

    print("\n")
    return data

if __name__ == "__main__":
    # 1) 先看 schema，确认各字段类型/选项
    schema = get_database_schema()
    if not schema:
        exit(1)