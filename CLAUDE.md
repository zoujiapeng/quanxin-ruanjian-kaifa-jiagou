# Lobster — Claude Code 的"双手"

> Lobster 是 Claude Code 的执行层扩展。MCP 是唯一的交互接口。
> Claude Code 负责规划，Lobster 负责执行——循环/等待/重试在本地跑，不消耗 token。

## 核心哲学

**Lobster 的存在是为了让 Claude Code 能做到原本做不到的事：**

1. **免 Token 执行** — LOOP/WAIT/IF 等控制流在本地引擎跑，Claude Code 只生成一次 DSL，后续迭代不消耗 API token
2. **GUI 操作** — Claude Code 读不了屏幕、点不了按钮、拖不动窗口，Lobster 通过 OCR+图像识别+模拟输入补全这些能力
3. **指令库组合** — 核心能力不是单个功能，而是如何组合。Claude Code 应能自主规划拆解任务 → 选择合适的工具链 → 编排执行
4. **MCP 是唯一接口** — Claude Code 通过 `tools/list` 发现能力、`tools/call` 调用能力。工具的描述和参数设计必须对 Claude Code 极度友好（清晰语义、完备 example、合理粒度）

**优先级**: 架构扩展性 > 工具数量。组合框架必须先完备（已有 @feature + LOOP/IF/WAIT），工具库慢慢积累。

## 系统架构

```
Claude Code (规划层)
    │  MCP protocol (tools/list → tools/call)
    ▼
Lobster MCP Server (python/mcp/server.py)
    │  @feature() registry
    ▼
本地执行引擎 (DSL → AST → 状态机)
    │  LOOP / WAIT / IF 控制流 (免token)
    ▼
感知层 (OCR/图像/颜色) + 交互层 (鼠标/键盘/窗口)
```

**设计原则**: 新增功能只改一个文件（`@feature()` 装饰器），MCP/CLI/HTTP/DSL 全部自动同步。

## 指令库组合模式

Claude Code 收到任务后应自主规划工具链。以下是对应常见任务的组合模式：

### 模式 1: 感知→动作→验证
```
OCR查找文字 → CLICK点击 → WAIT反馈 → OCR验证结果
```
**适用**: 表单填写、按钮点击、弹窗处理。`ocr_find_text` 定位坐标 → `click_target` 点击 → `popup_close` / `ocr_find_text` 验证。

### 模式 2: 循环监控（免token）
```
LOOP 检查
  color_check / detect_color / detect_progress → 检测状态
  WAIT 变化 / WAIT 稳定 → 等待条件
  IF 条件 → CLICK / TYPE / DRAG → 执行动作
END
```
**适用**: 等待进度条完成、监控页面变化、自动化流水线。DSL 一次性生成后本地引擎循环，不消耗 token。

### 模式 3: 多步流程编排
```
find_image (定位模板) → click_target (点击) → ocr_extract_all (提取文字)
→ ai_generate_dsl (分析结果并生成下一步) → DSL执行
```
**适用**: 复杂任务中 AI 需要阅读屏幕内容后决策的场景。

### 模式 4: 调试诊断
```
debug_system_info → debug_run_tests → debug_get_logs → debug_validate_dsl
```
**适用**: 系统出问题时先检查状态，再跑测试，看日志，验证 DSL。

### 如何选择工具
- `detect_process` / `find_processes` — 检查目标软件是否运行
- `focus_window` — 切换到目标窗口后再操作
- `type_clipboard` — 替代 `type_text`，绕过输入法问题
- `screenshot` + `ocr_*` — 检验操作结果
- `hotkey` — 需要系统级快捷键时用

## 场景模板

以下是一线可用的 prompt 模板，直接复制给 Claude Code 使用：

### 模板 1: 跨应用数据搬运
```
用户需要从 [应用A] 复制数据到 [应用B]。
流程: 
1. 用 detect_process/find_processes 确认两个应用都在运行
2. focus_window 切换到应用A
3. 截图+OCR提取内容或用快捷键复制
4. focus_window 切换到应用B
5. CLICK/TYPE 粘贴数据
6. 截图验证结果

执行步骤分解后用 DSL 实现，优先用 type_clipboard 替代 type_text。
```

### 模板 2: 定时监控任务
```
用户需要每隔 [N] 分钟检查 [条件]，满足时执行 [动作]。
方案: 用 DSL LOOP + WAIT 实现免token监控。
LOOP 监控循环
  screenshot → ocr_find_text / color_check 检测状态
  IF 条件满足
    CLICK / TYPE 执行动作
    WAIT 确认结果
  END
  WAIT N秒
END
用 lobster run 提交后本地引擎循环，不消耗token。
```

### 模板 3: Web 自动化（通过 Playwright）
```
需要: [具体的浏览器操作]
方案: 如果已安装 Playwright (pip install playwright)，使用 browser_* 功能。
如果未安装，提示用户安装:
  pip install playwright && playwright install chromium

browser_navigate → browser_get_url 确认 → 
browser_list_tabs/switch_tab 多标签管理 → 
操作完成后用 screenshot 验证
```

### 模板 4: 故障恢复
```
用户反馈 [功能/流程] 出错了。
诊断流程:
1. debug_system_info — 获取系统状态
2. debug_run_tests — 运行测试
3. debug_get_logs — 查看最新日志
4. 如果是 DSL 语法问题 → debug_validate_dsl / parse_dsl
5. 如果是功能调用失败 → dsl_optimize_analyze 分析 telemetry

修复后建议:
- 如果是超时问题 → 调整 timeout 参数
- 如果是参数问题 → 检查输入格式
- 如果是环境问题 → 检查进程/窗口状态
```

### 模板 5: DSL 流程编排
```
用户需要: [复杂多步骤任务]
拆解方法:
1. 先列出所有步骤（用自然语言）
2. 识别可以并行执行的步骤（用 PARALLEL/WITH）
3. 识别需要循环监控的步骤（用 LOOP）
4. 识别条件分支（用 IF/ELSE）
5. 如果步骤太多，封装为 SUBROUTINE
6. 最终组装成完整 DSL

执行方法:
- 短流程: lobster run-sync "..." 
- 长流程/监控: lobster call run_dsl dsl='...'
- 复杂流程: 写入 .lobster 文件后 lobster run-file xxx.lobster
```

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

注册后自动获得：
- **MCP 工具**: `lobster_my_feature`
- **CLI 命令**: `lobster call my_feature --target XXX`
- **HTTP API**: `POST /api/feature/my_feature`
- **DSL 语法**: `MY_CMD XXX`
- **测试用例**: `lobster test` 自动执行

## 关键文件
- `python/features/registry.py` — 注册表核心
- `python/features/action_features.py` — 动作功能 (CLICK/TYPE/SCROLL/DRAG/HOTKEY)
- `python/features/perception_features.py` — 感知功能 (OCR/图像/颜色/进度条)
- `python/features/browser_features.py` — 浏览器功能（基于 Playwright）
- `python/features/ai_debug_features.py` — AI + 调试功能
- `python/mcp/server.py` — MCP 服务端（从 registry 动态生成工具 + 流式通知）
- `cli/lobster.py` — CLI 入口
- `python/server.py` — HTTP 后端（registry 自动路由）
- `python/engine/optimizer.py` — Telemetry 驱动 DSL 优化分析

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
