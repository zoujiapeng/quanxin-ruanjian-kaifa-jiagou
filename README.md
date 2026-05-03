# Lobster — Claude Code 的"双手"

> Claude Code 负责规划，Lobster 负责执行。LOOP/WAIT/IF 在本地引擎跑，不消耗 API token。
> MCP 是唯一的交互接口——Claude Code 通过 tools/list 发现能力、tools/call 调用能力。

---

## 架构概览

```
Claude Code (规划层)
    │  MCP protocol (tools/list → tools/call)
    ▼
Lobster MCP Server (python/mcp/server.py)
    │  @feature() registry (104 features)
    ▼
本地 DSL 执行引擎
    │  LOOP / WAIT / IF / SUBROUTINE / PARALLEL / WHEN / WITH
    ▼
8 层架构: registry → features → dsl_parser → executor
    → triggers → planner → healing → fusion
```

## 设计原则

**新增功能只改一个文件** — `@feature()` 装饰器声明后，MCP 工具/CLI 命令/HTTP API/DSL 语法全部自动同步。

## 与市面方案对比

| 类别 | 代表 | Lobster 区别 |
|------|------|-------------|
| 通用 MCP 服务 | Playwright MCP, Browserbase | 不止浏览器，覆盖桌面/系统/跨应用 |
| 桌面自动化框架 | PyAutoGUI, Playwright | 是 MCP 服务端，LLM 可直接调用 |
| Agent 框架 | AutoGPT, CrewAI | 不自己做规划，专注执行层，免 token |

**核心差异**: 免 token 控制流 + 桌面 GUI 操作 + MCP 协议驱动 + 指令库组合体系

## 架构层次

```
registry          功能注册表（@feature 装饰器）
    → features    104 个功能（action/perception/AI/system/control/...）
    → dsl_parser  递归下降解析器（13 种 NodeType）
    → executor    状态机执行器（IDLE/RUNNING/PAUSED/STOPPED/ERROR/FINISHED）
    → triggers    反应式事件引擎（file/process/window/clipboard/network）
    → planner     AI 规划引擎（observe→think→act→evaluate）
    → store       SQLite 持久化（checkpoint/telemetry/vault）
    → healing     自愈管道（retry→a11y→offset→escalate）
    → fusion      多模态融合（OCR+image+a11y 加权投票）
    → optimizer   Telemetry 驱动的 DSL 优化分析
    → plugin      动态插件 SDK
```

## 项目结构

```
lobster/
├── python/
│   ├── server.py            # Flask + SocketIO 后端 (/api/feature/<name> 自动路由)
│   ├── mcp/server.py        # MCP stdio 服务端（registry 动态生成工具 + 流式通知）
│   ├── cli/lobster.py       # CLI 入口（flat dispatch）
│   ├── features/            # 功能注册文件（@feature 装饰器）
│   │   ├── registry.py      # 注册表核心
│   │   ├── action_features.py
│   │   ├── perception_features.py
│   │   ├── ai_debug_features.py
│   │   ├── system_features.py
│   │   ├── dsl_features.py
│   │   ├── browser_features.py      (待完善)
│   │   ├── input_features.py        (待完善)
│   │   ├── window_features.py       (待完善)
│   │   ├── system_control_features.py (待完善)
│   │   ├── clipboard_features.py    (待完善)
│   │   ├── network_features.py      (待完善)
│   │   ├── timer_features.py        (待完善)
│   │   ├── filedialog_features.py   (待完善)
│   │   ├── a11y_features.py         (待完善)
│   │   ├── macro_features.py        (待完善)
│   │   ├── multimedia_features.py   (待完善)
│   │   ├── fusion_features.py
│   │   ├── persistence_features.py
│   │   ├── healing_features.py
│   │   ├── trigger_features.py
│   │   ├── ai_plan_features.py
│   │   └── plugin_features.py
│   ├── engine/
│   │   ├── dsl_parser.py    # DSL 解析器（CLICK/WAIT/LOOP/IF/SUBROUTINE/CALL/PARALLEL/WHEN/WITH）
│   │   ├── executor.py      # 状态机执行器（暂停/恢复/停止/重试/自愈/线程安全）
│   │   ├── scheduler.py     # 任务调度器
│   │   ├── triggers.py      # 反应式事件引擎
│   │   ├── planner.py       # AI 规划引擎（LLM 闭环 + 持久化 checkpoint）
│   │   ├── store.py         # SQLite 持久化存储
│   │   ├── healing.py       # 自愈管道
│   │   └── optimizer.py     # Telemetry 驱动优化分析
│   ├── perception/          # 感知层
│   │   ├── vision.py        # 截图/模板匹配/变化检测/颜色/进度条
│   │   ├── ocr.py           # OCR 引擎（PaddleOCR→EasyOCR→Tesseract 降级）
│   │   └── fusion.py        # 多模态融合引擎
│   └── interaction/
│       └── actions.py       # 鼠标/键盘/语义点击/等待/弹窗/宏
├── electron/                # Electron 前端
│   ├── src/main/            # Electron 主进程
│   ├── src/renderer/        # React 前端（React Flow + Zustand）
│   └── public/
├── cli/                     # CLI 入口
├── shared/types.ts          # TypeScript 共享类型
├── tests/run_tests.py       # 测试套件（注册表/解析器/往返/单元测试）
└── CLAUDE.md                # Claude Code 指令
```

## 快速开始

### 1. 安装后端依赖
```bash
cd python
pip install -r requirements.txt
```

### 2. 启动后端
```bash
cd python && python server.py
# Lobster v2 | Port:7788 | Features:104 | REAL
```

### 3. MCP 配置 (Claude Desktop)
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

### 4. CLI 使用
```bash
lobster list              # 查看所有功能
lobster info click-target # 查看功能详情
lobster parse "CLICK 目标" # 验证 DSL
lobster test              # 运行测试
```

### 5. 运行测试
```bash
python tests/run_tests.py
# 104 功能注册, DSL 解析器/往返/单元测试全部通过
```

## DSL 语法

```
CLICK <target>                    # 点击目标（文字/图像/坐标）
WAIT <condition>                  # 等待条件
LOOP <tag>  ...  END              # 循环
IF <cond>  ...  [ELSE ...]  END   # 条件判断
SUBROUTINE name(p1, p2) ... END   # 子程序定义
CALL name(arg1, arg2)             # 调用子程序
IMPORT "<path>"                   # 导入外部 DSL
RETURN [value]                    # 从子程序返回
PARALLEL ... WITH ...  END        # 并行分支（支持异质执行）
WHEN EVENT_TYPE config ... END    # 事件触发
WITH <handler> ... END            # 异质执行（临时切换 action handler）
```

## API 接口

- `GET /api/health` — 健康检查
- `GET /api/registry?format=json|markdown|mcp|openapi|dsl` — 注册表导出
- `POST/GET /api/feature/<name>` — 调用功能（自动类型转换）
- `POST /api/dsl/parse` — DSL 解析
- `POST /api/dsl/run` / `run-sync` — DSL 执行
- `GET /api/dsl/state` — DSL 热重载状态
- `POST /api/executor/pause|resume|stop` — 执行器控制
- `GET /api/executor/status` — 执行器状态
- `GET /api/logs` — 日志
- WebSocket: `node_highlight`, `dsl_update`, `dsl_parse_validate` — 实时事件

## 技术栈

- **MCP 协议**: stdio JSON-RPC (tools/list + tools/call + 流式 notification)
- **后端**: Python 3.10+ / Flask / SocketIO / SQLite
- **感知**: OpenCV / Tesseract / PaddleOCR / EasyOCR
- **交互**: pyautogui / win32gui / pyperclip / psutil
- **前端** (Electron): React 18 + TypeScript + React Flow 11 + Zustand 4
