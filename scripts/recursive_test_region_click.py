"""
递归测试 004: 区域框选 + OCR 识别 + 右键 — 通过 CLI 直通（非 MCP）

测试流程:
  1. 先让用户框选区域 → 拿到坐标 JSON
  2. 再把坐标喂给新 Claude → Claude 生成并执行 DSL
  3. DSL: OCR_FIND 目标 → 找到则右键

运行方式:
  python scripts/recursive_test_region_click.py [目标文字]

原理:
  新 Claude Code 使用 lobster CLI 命令 (lobster exec) 而非 MCP 工具。
  坐标预先采集，Claude 直接拿到完整信息，不需要多轮交互。
"""

import sys, os, json, subprocess

# 强制 UTF-8 编码，避免 GBK 终端输出问题
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
os.environ["PYTHONIOENCODING"] = "utf-8"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def build_prompt(target_text: str, region_json: str) -> str:
    return f"""你正在测试 Lobster 的独有能力。只有 CLI 命令可用。
项目路径: {PROJECT_DIR}

坐标: {region_json}
目标: 找到桌面图标「{target_text}」并右键

可用 DSL 关键字（只使用这些）:
  OCR_FIND <文字>         → 全屏搜索文字, 设置 _ocr_found/_ocr_x/_ocr_y
  IF <条件> ... ELSE ... END
  CLICK <目标> [RIGHT]    → 左键/右键
  TYPE <文字>             → 打字
  WAIT <秒>
  SCREENSHOT <路径>

任务:
1. 运行: lobster exec "OCR_FIND {target_text}
   IF _ocr_found
     CLICK {{_ocr_x}},{{_ocr_y}} RIGHT
     TYPE 已找到{target_text}并右键
   ELSE
     TYPE 未找到{target_text}
   END"

2. 报告结果。不需要请求权限，直接执行。
"""  # noqa: E501


def run_test(target_text: str = "回收站"):
    print("=" * 60)
    print(f"递归测试 004: 区域框选 + OCR + 右键")
    print(f"目标文字: {target_text}")
    print("=" * 60)

    # 阶段 1: 用户框选区域
    print(f"\n[阶段1] 请框选桌面图标区域（确保「{target_text}」在选框内）")
    region_path = os.path.join(PROJECT_DIR, "scripts", "_test_004_region.json")
    result = subprocess.run(
        ["python", "cli/lobster.py", "region-select",
         f"请框选桌面图标区域（包含{target_text}图标）"],
        cwd=PROJECT_DIR,
        capture_output=True,
        timeout=120,
    )
    stdout = result.stdout.decode("utf-8", errors="replace").strip()
    stderr = result.stderr.decode("utf-8", errors="replace").strip()

    if result.returncode != 0 or not stdout:
        print(f"区域选择失败: {stderr}")
        sys.exit(1)

    # 解析 JSON
    try:
        region = json.loads(stdout)
    except json.JSONDecodeError:
        print(f"无法解析区域: {stdout}")
        sys.exit(1)

    if region.get("cancelled"):
        print("用户取消了区域选择")
        sys.exit(0)

    x, y, w, h = region["x"], region["y"], region["w"], region["h"]
    region_str = f"({x},{y}) {w}×{h}"
    region_json = json.dumps(region, ensure_ascii=False)
    print(f"  区域已选择: {region_str}  坐标: {region_json}")

    # 保存坐标供 Claude 使用
    with open(region_path, "w", encoding="utf-8") as f:
        json.dump(region, f, ensure_ascii=False)

    # 阶段 2: 启动新 Claude
    print(f"\n[阶段2] 启动新 Claude Code 实例执行任务...")
    prompt = build_prompt(target_text, region_json)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        ["claude", "-p", prompt, "--dangerously-skip-permissions"],
        cwd=PROJECT_DIR,
        capture_output=True,
        timeout=300,
        env=env,
    )
    stdout = result.stdout.decode("utf-8", errors="replace")
    stderr = result.stderr.decode("utf-8", errors="replace")

    print(f"\n--- Claude 输出 ---")
    # GBK 安全输出 — 过滤不可见字符
    safe_stdout = stdout.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
    safe_stdout = safe_stdout.encode("gbk", errors="replace").decode("gbk", errors="replace")
    print(safe_stdout)
    if stderr.strip():
        print(f"\n--- stderr ---")
        safe_stderr = stderr[:2000].encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        safe_stderr = safe_stderr.encode("gbk", errors="replace").decode("gbk", errors="replace")
        print(safe_stderr)
    print(f"\n退出码: {result.returncode}")

    # 保存结果
    log_path = os.path.join(PROJECT_DIR, "scripts", "_test_004_result.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"递归测试 004 结果\n")
        f.write(f"目标文字: {target_text}\n")
        f.write(f"框选区域: {region_json}\n")
        f.write(f"返回码: {result.returncode}\n\n")
        f.write(stdout)
        if stderr.strip():
            f.write(f"\n\n--- stderr ---\n{stderr}")
    print(f"\n结果已保存: {log_path}")

    return result.returncode == 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "回收站"
    success = run_test(target)
    sys.exit(0 if success else 1)
