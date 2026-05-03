# Lobster — Claude Code 调试指南

## 系统架构

```
功能注册 (python/features/*.py)
    │
    ├── @feature(...) 装饰器 → registry
    │
    ├── registry.export_mcp_tools()  → MCP Server 自动提供
    ├── /api/feature/<name>          → HTTP API 自动可用
    ├── lobster call <name>          → CLI 自动注册
    └── DSL keyword                  → DSL 解析器识别
```

**核心原则**: 新增功能只改一个文件，其他全部自动同步。

## 调试流程

### 1. 了解系统
```bash
lobster list              # 查看所有功能
lobster info click-target # 查看功能详情
```

### 2. 运行测试
```bash
python python/tests/run_tests.py
lobster test
```

### 3. 验证 DSL
```bash
lobster parse "CLICK 目标"
```

### 4. 调用功能
```bash
lobster call click-target target="确认" timeout=5
```

## 新增功能（3 步）

### Step 1: 创建功能文件
```python
# python/features/my_feature.py
from features.registry import feature, P, TC, FeatureCategory as F

@feature(
    name="my_feature",
    display_name="我的功能",
    description="描述",
    category=F.ACTION,
    params=[P("target", "str", "目标")],
    returns="bool",
    dsl_keyword="MY_CMD",
    dsl_template="MY_CMD {target}",
    test_cases=[TC("basic", {"target": "test"}, "bool_true", skip_in_ci=True)],
)
def my_feature(target: str) -> bool:
    return True
```

### Step 2: 在 server.py 导入
```python
# python/server.py 顶部添加：
import features.my_feature  # noqa
```

### Step 3: 验证
```bash
lobster test
lobster list
```

## MCP 配置 (Claude Desktop)
```json
{
  "mcpServers": {
    "lobster": {
      "command": "python",
      "args": ["C:\\Users\\zou\\Desktop\\claude1\\cli\\lobster_mcp.py"]
    }
  }
}
```

## 关键文件
- `python/features/registry.py` — 注册表核心
- `python/features/action_features.py` — 动作功能 (CLICK/TYPE/SCROLL/DRAG/HOTKEY)
- `python/features/perception_features.py` — 感知功能 (OCR/图像/颜色/进度条)
- `python/features/ai_debug_features.py` — AI + 调试功能
- `python/mcp/server.py` — MCP 服务端
- `cli/lobster.py` — CLI 入口
- `python/server.py` — HTTP 后端
