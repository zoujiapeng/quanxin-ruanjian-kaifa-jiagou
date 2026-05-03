# Lobster — 项目架构说明

> 低 Token AI 自动化执行系统。用户一句话 → AI 生成 DSL → 本地执行。

## 架构概览

```
用户输入 (自然语言)
    │
    ▼
┌─────────────────────────────┐
│  规划层: Claude API         │  1-3 次 API 调用
│  输入任务 → 输出 DSL        │
└──────────┬──────────────────┘
           │ DSL 文本
           ▼
┌─────────────────────────────┐
│  执行层: Python 引擎        │  本地执行
│  DSL→AST→状态机→节点调度    │
│  Flask + SocketIO 服务器    │
└──────────┬──────────────────┘
           │ 交互指令
           ▼
┌─────────────────────────────┐
│  感知层: OpenCV/Tesseract   │  屏幕交互
│  图像识别/OCR/鼠标键盘模拟   │
└─────────────────────────────┘
```

## 核心设计: 功能即注册 (Feature Registry)

`python/features/registry.py` — 整个系统的核心。

### @feature() 装饰器
新增功能只需一处声明，MCP/CLI/HTTP/DSL 全部自动生成：

```python
@feature(
    name="click_target",
    display_name="点击目标",
    description="语义点击",
    category=F.ACTION,
    params=[P("target", "str", "目标")],
    returns="bool",
    dsl_keyword="CLICK",
    dsl_template="CLICK {target}",
)
def click_target(target: str) -> bool:
    ...
```

注册后自动获得：
| 接口 | 生成方式 |
|------|----------|
| MCP 工具 | `registry.export_mcp_tools()` → `lobster_click_target` |
| HTTP API | `POST /api/feature/click_target` |
| CLI 命令 | `lobster call click-target` |
| DSL 指令 | `CLICK {target}` |
| 测试用例 | `lobster test` 自动执行 |

### FeatureSpec 数据结构 (registry.py)
- `name` — 唯一标识（snake_case）
- `cli_command` — CLI 命令名（自动从 name 生成 kebab-case）
- `mcp_tool_name` — MCP 工具名（自动加 `lobster_` 前缀）
- `http_endpoint` — HTTP 路径（自动 `/api/feature/<name>`）
- `handler` — 实际执行函数
- `params` — `ParamSpec` 列表
- `test_cases` — `TestCase` 列表

### 注册表方法
| 方法 | 用途 |
|------|------|
| `registry.register(spec)` | 注册功能 |
| `registry.get(name)` | 按名称查找 |
| `registry.all()` | 所有功能（按加载顺序） |
| `registry.by_category(cat)` | 按类别过滤 |
| `registry.execute(name, **kwargs)` | 执行功能 |
| `registry.run_tests(skip_ci=True)` | 运行所有测试 |
| `registry.export_mcp_tools()` | MCP 工具列表 |
| `registry.export_openapi()` | OpenAPI 3.0 规格 |
| `registry.export_claude_context()` | Claude 可读的 Markdown |
| `registry.export_dsl_reference()` | DSL 语法参考 |

## 已注册功能 (20 个)

### Action (5) — `action_features.py`
click_target, type_text, scroll, drag, hotkey

### Perception (6) — `perception_features.py`
ocr_find_text, ocr_extract_all, find_image, detect_color, detect_progress, screenshot

### AI (3) — `ai_debug_features.py`
ai_generate_dsl, dsl_to_graph, graph_to_dsl

### Debug (6) — `ai_debug_features.py`
debug_get_logs, debug_run_tests, debug_list_features, debug_validate_dsl, debug_system_info, debug_generate_test_flow

## 三层代码结构

### 1. Python 后端 (`python/`)
```
python/
├── server.py                  # Flask + SocketIO (端口 7788)
├── features/                  # 功能注册系统
│   ├── registry.py            # 注册表核心
│   ├── _utils.py              # 共享工具 (parse_region, resolve_coord, sim_delay)
│   ├── state.py               # 运行时日志缓冲区
│   ├── action_features.py     # 动作功能
│   ├── perception_features.py # 感知功能
│   ├── ai_debug_features.py   # AI + 调试功能
│   └── feature_template.py    # 新增功能模板
├── engine/                    # DSL 执行引擎
│   ├── dsl_parser.py          # 递归下降解析器
│   ├── executor.py            # 状态机执行器
│   └── scheduler.py           # 优先级队列调度
├── perception/                # 视觉感知模块
│   ├── vision.py              # 模板匹配/颜色/进度条
│   └── ocr.py                 # Tesseract OCR
├── interaction/               # 交互模块
│   └── actions.py             # 鼠标/键盘/弹窗/宏
├── mcp/                       # MCP 服务端
│   └── server.py              # stdio 协议，动态生成工具
└── macros/                    # DSL 宏脚本
```

### 2. CLI (`cli/`)
```
cli/
├── lobster.py       # 主 CLI（16 个命令，flat dispatch）
└── lobster_mcp.py   # MCP 入口封装
```

命令列表: `run`, `run-file`, `run-sync`, `parse`, `health`, `status`, `pause`, `resume`, `stop`, `logs`, `restart`, `call`, `list`, `info`, `test`, `mcp`

### 3. Electron 桌面应用 (`electron/`)
```
electron/
└── src/
    ├── main/         # 主进程（窗口、Python 进程管理）
    └── renderer/     # React + React Flow 流程图编辑器
        ├── App.tsx
        ├── store/    # Zustand 状态管理
        └── components/
            ├── Canvas/           # React Flow 画布
            ├── NodeLibrary/      # 节点库面板
            ├── PropertyPanel/    # 属性面板
            └── common/           # 通用组件
                ├── LogPanel.tsx  # 执行日志面板
                ├── TopBar.tsx
                └── StatusBar.tsx
```

## 端口与服务
- 后端: `localhost:7788` (Flask + WebSocket)
- 前端: `localhost:5173` (Vite dev server)
- MCP: stdio 协议（无独立端口）

## 启动方式
```bash
# 启动后端
cd python && python server.py

# 启动前端 (Electron)
npm run dev

# CLI 命令
lobster run "CLICK 开始"
lobster call click-target target=确认

# MCP 服务
lobster mcp
```

## 已知问题 / 注意事项

### Windows GBK 编码
Windows 终端默认 GBK，Python print 含中文或特殊字符会报错。修复方式：
```python
if sys.platform == "win32":
    for s in (sys.stdin, sys.stdout, sys.stderr):
        try: s.reconfigure(encoding="utf-8")
        except Exception: pass
```
- print 中不要用 emoji
- 文件读写指定 `encoding="utf-8"`
- 所有 Python 脚本顶部已处理此问题

### 模拟模式
感知/交互模块加载失败时自动降级为 SIMULATION_MODE，registry.execute 返回模拟值而非报错。

### 多 Python 进程
旧 server 进程可能占用端口 7788。用 `lobster restart` 自动 kill 旧进程。

## 扩展指南: 新增功能

```
3 步:
1. python/features/xxx.py  + @feature() 装饰器
2. python/server.py 顶部 import
3. 验证: lobster test && lobster list
```

详细模板见 `python/features/feature_template.py`。

## 文件关系图

```
新增 xxx.py
    → 在 server.py import（触发 @feature()）
    → registry.register(spec)
    → MCP 工具: mcp/server.py 下次 tools/list 自动包含
    → HTTP 路由: server.py /api/feature/<name> 自动可用
    → CLI 调用: lobster call xxx key=val 直接使用
```
