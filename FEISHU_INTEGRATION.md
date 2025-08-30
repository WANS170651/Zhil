# 飞书多维表格集成功能

## 概述

本项目已成功集成飞书多维表格写入功能，现在可以同时将爬取到的URL信息写入Notion和飞书多维表格。

## 新增功能

### 1. 飞书多维表格写入器 (`src/feishu_writer.py`)
- **Token管理系统**: 自动管理`tenant_access_token`和`user_access_token`
- **缓存机制**: Token自动缓存和刷新，有效期内复用
- **批量写入**: 支持单条和批量记录创建
- **异步支持**: 提供同步和异步两种写入模式
- **错误处理**: 完善的错误处理和重试机制

### 2. 飞书数据规范化器 (`src/feishu_normalizer.py`)
- **智能字段映射**: 自动将通用字段映射到飞书字段名
- **数据类型转换**: 支持文本、数字、日期、复选框、URL等多种字段类型
- **模糊匹配**: 使用模糊匹配改善字段名识别准确性
- **数据验证**: 自动验证和清理数据

### 3. 主处理管道集成 (`src/main_pipeline.py`)
- **双写模式**: 同时写入Notion和飞书多维表格
- **独立处理**: 飞书写入失败不影响Notion写入
- **异步处理**: 支持真正的并发处理
- **错误隔离**: 飞书相关错误不影响主流程

### 4. 配置系统扩展
- **动态配置**: 支持环境变量和用户设置两种配置方式
- **Web界面**: 可通过前端界面配置飞书参数
- **配置验证**: 自动验证配置完整性

## 配置说明

### 环境变量配置

在`.env`文件中添加以下配置：

```bash
# 飞书应用配置
FEISHU_APP_ID=your_feishu_app_id
FEISHU_APP_SECRET=your_feishu_app_secret
FEISHU_APP_TOKEN=your_feishu_app_token
FEISHU_TABLE_ID=your_feishu_table_id
```

### Web界面配置

1. 启动服务：`python start_web_demo.py`
2. 访问：http://127.0.0.1:8000/ui
3. 点击"设置"卡片
4. 在"飞书多维表格配置"部分填入相关参数
5. 点击"测试"验证连接
6. 点击"保存"保存配置

### 配置文件说明

配置会保存在`config/user_settings.ini`文件中：

```ini
[DEFAULT]
# 飞书应用ID
feishu_app_id = cli_xxxxxxxxx
# 飞书应用Secret  
feishu_app_secret = xxxxxxxxxxxxxxx
# 飞书多维表格Token
feishu_app_token = bascnxxxxxxxxx
# 飞书表格ID
feishu_table_id = tblxxxxxxx
```

## 飞书应用设置

### 1. 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建应用，获取`APP_ID`和`APP_SECRET`
3. 在应用管理中配置权限范围

### 2. 权限配置

需要以下权限：
- `bitable:app` - 多维表格应用权限
- `bitable:app:readonly` - 多维表格只读权限  
- `base:record:create` - 记录创建权限
- `base:record:read` - 记录读取权限

### 3. 获取表格信息

1. 创建或打开飞书多维表格
2. 从URL中获取`app_token`和`table_id`：
   ```
   https://example.feishu.cn/base/bascnxxxxxxxxx?table=tblxxxxxxx&view=vewxxxxxxx
                             ^^^^^^^^^^^^^^^^         ^^^^^^^^^^
                             app_token               table_id
   ```

## 使用方法

### 自动双写模式

配置完成后，正常的URL处理会自动同时写入Notion和飞书：

```python
# API调用
curl -X POST "http://localhost:8000/ingest/url" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com/job-posting"}'
```

### 仅飞书写入

如果只需要写入飞书多维表格：

```python
from src.feishu_writer import write_to_feishu

# 准备数据
fields = {
    "公司名称": "测试公司",
    "职位名称": "软件工程师", 
    "工作地点": "北京",
    "薪资": 25000,
    "链接": "https://example.com/job"
}

# 写入飞书
result = write_to_feishu(fields)
print(result)
```

### 数据规范化

```python
from src.feishu_normalizer import normalize_for_feishu

# 原始数据
raw_data = {
    "company": "Test Company",
    "position": "Software Engineer",
    "salary": "20k-30k", 
    "location": "Beijing"
}

# 规范化为飞书格式
result = normalize_for_feishu(raw_data)
feishu_fields = result["feishu_payload"]["fields"]
```

## 字段映射

系统会自动将通用字段映射到飞书字段：

| 通用字段 | 飞书字段 | 类型 |
|---------|---------|------|
| company | 公司名称 | 文本 |
| position | 职位名称 | 文本 |
| location | 工作地点 | 文本 |
| salary | 薪资 | 数字 |
| url | 链接 | URL |
| publish_date | 发布时间 | 日期 |
| experience | 工作经验 | 文本 |
| education | 学历要求 | 文本 |
| tags | 标签 | 多选 |
| status | 状态 | 单选 |

### 自定义字段映射

可以在`src/feishu_normalizer.py`中的`field_mapping`字典添加新的映射关系：

```python
self.field_mapping = {
    "custom_field": "自定义字段",
    # ... 其他映射
}
```

## Token管理

### 自动Token管理

系统会自动处理Token的获取、缓存和刷新：

- `tenant_access_token`: 应用级别token，有效期2小时
- `user_access_token`: 用户级别token，有效期2小时
- 自动缓存到`.feishu_cache/`目录
- 过期前5分钟自动刷新

### 手动Token管理

```python
from src.feishu_writer import FeishuTokenManager

# 创建Token管理器
token_manager = FeishuTokenManager(app_id, app_secret)

# 获取tenant token
tenant_token = token_manager.get_tenant_access_token()

# 获取user token（需要refresh_token）
user_token, new_refresh_token = token_manager.get_user_access_token(refresh_token)
```

## 错误处理

### 常见错误及解决方案

1. **配置错误**
   ```
   错误: FEISHU_APP_ID环境变量未设置
   解决: 在.env文件或Web界面中配置飞书参数
   ```

2. **权限错误**
   ```
   错误: 飞书API返回错误: 权限不足
   解决: 检查飞书应用权限配置
   ```

3. **Token错误**
   ```
   错误: 获取tenant_access_token失败
   解决: 检查APP_ID和APP_SECRET是否正确
   ```

4. **表格访问错误**
   ```
   错误: 表格不存在或无权限
   解决: 检查APP_TOKEN和TABLE_ID，确保应用有访问权限
   ```

## 性能优化

### 并发处理

系统支持真正的并发处理，可显著提升处理速度：

```python
# 批量URL处理
urls = ["url1", "url2", "url3", "url4", "url5"]

# 并发处理（推荐）
results = await async_main_pipeline.process_multiple_urls_concurrent(urls)

# 可设置最大并发数
async_main_pipeline.max_concurrent = 3
```

### 缓存优化

- Token自动缓存，避免重复请求
- 数据库Schema缓存
- 智能重试机制

## API参考

### 新增API端点

1. **设置管理**
   - `GET /settings` - 获取当前设置
   - `POST /settings` - 保存设置
   - `POST /settings/test` - 测试设置连接

2. **处理增强**
   - 所有现有的URL处理端点现在都支持飞书写入
   - 飞书写入失败不影响主要功能

### 响应格式

处理结果现在包含飞书写入信息：

```json
{
  "success": true,
  "message": "异步处理成功", 
  "url": "https://example.com",
  "result": {
    "stage": "completed",
    "writing_result": {
      "success": true,
      "operation": "create",
      "page_id": "notion_page_id"
    },
    "feishu_writing_result": {
      "success": true,
      "operation": "create", 
      "record_id": "feishu_record_id"
    }
  }
}
```

## 测试和调试

### 运行集成测试

```bash
python test_feishu_integration.py
```

### 健康检查

访问 `http://localhost:8000/health` 查看系统状态，包括飞书连接状态。

### 日志调试

系统会输出详细的飞书处理日志：

```
2024-01-01 12:00:00 - INFO - 🔧 开始飞书数据规范化...
2024-01-01 12:00:00 - INFO - ✅ 飞书数据规范化成功
2024-01-01 12:00:00 - INFO - 📋 开始异步写入飞书多维表格...
2024-01-01 12:00:00 - INFO - ✅ 异步飞书写入成功，记录ID: recxxxxxx
```

## 注意事项

1. **权限要求**: 飞书应用需要具备多维表格相关权限
2. **网络要求**: 需要能够访问飞书API (open.feishu.cn)
3. **配置优先级**: 用户设置 > 环境变量
4. **错误隔离**: 飞书相关错误不会影响Notion写入
5. **并发限制**: 建议设置合理的并发数避免API限流

## 技术架构

```
URL处理请求
     ↓
主处理管道 (main_pipeline.py)
     ↓
┌─────────────────┬─────────────────┐
│   Notion写入    │   飞书写入      │
│                 │                 │
│ notion_writer   │ feishu_writer   │
│ normalizer      │ feishu_normalizer│
└─────────────────┴─────────────────┘
     ↓                     ↓
  Notion数据库          飞书多维表格
```

## 总结

飞书多维表格集成功能已完全就绪，支持：

✅ 完整的Token管理和缓存机制  
✅ 智能数据规范化和字段映射  
✅ 同步和异步写入模式  
✅ Web界面配置和测试  
✅ 完善的错误处理和日志  
✅ 并发处理和性能优化  
✅ 详细的API文档和测试  

现在您可以同时将URL信息写入Notion和飞书多维表格，享受双重数据存储的便利！

