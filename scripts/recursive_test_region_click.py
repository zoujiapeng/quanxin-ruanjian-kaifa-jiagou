"""
递归测试 004: 区域框选 + OCR 识别 + 右键 — 通过 CLI 直通（非 MCP）

测试目标:
  验证新 Claude Code 实例可以通过 CLI 命令 (非 MCP) 完成:
  1. 请求用户交互式框选区域 → 获得 JSON 坐标
  2. 用 OCR 识别区域文字
  3. 找到指定文字后右键

运行方式:
  python scripts/recursive_test_region_click.py

原理:
  通过 claude -p 启动新 Claude 实例，prompt 指示其使用 lobster CLI 命令
  (lobster exec / lobster region-select) 而非 MCP 工具。
"""

import sys, os, json, subprocess, tempfile, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def build_prompt(target_text: str = "回收站") -> str:
    """构造发给新 Claude 的 prompt，强制使用 CLI 直通"""
    return f"""你正在测试 Lobster 的独有能力测试。你的环境没有 MCP 工具，
必须只通过 CLI 命令完成任务。项目路径: {PROJECT_DIR}

任务：判断桌面图标区域是否有「{target_text}」这个图标，如果有就在它上面右键。

步骤：
1. 告诉用户运行以下命令框选区域：
   lobster region-select "请框选桌面图标区域（包含{target_text}图标）"
   用户框选后会返回 JSON，格式：{{"x":100,"y":200,"w":300,"h":50}}

2. 用户返回 JSON 坐标后，用这些坐标构造 DSL 并执行：
   lobster exec "OCR_EXTRACT
   OCR_FIND {target_text}
   IF _ocr_found
     CLICK {{_ocr_x}},{{_ocr_y}} RIGHT
     TYPE 已找到{target_text}并在其位置右键
   ELSE
     TYPE 未找到{target_text}
   END"

3. 把执行结果和找到的文字报告给用户。

重要：只使用 lobster CLI 命令，绝对不要试图用 MCP 工具或 python 脚本。
"""  # noqa: E501


def run_test(target_text: str = "回收站"):
    print(f"=" * 60)
    print(f"递归测试 004: 区域框选 + OCR + 右键")
    print(f"目标文字: {target_text}")
    print(f"=" * 60)

    prompt = build_prompt(target_text)
    prompt_path = os.path.join(PROJECT_DIR, "scripts", "_test_004_prompt.txt")
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"\nPrompt 已写入: {prompt_path}")
    print(f"\n启动新 Claude Code 实例...")
    print(f"(等待用户交互完成后新 Claude 会退出)\n")

    result = subprocess.run(
        ["claude", "-p", prompt],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        timeout=600,
    )

    print(f"\n--- Claude 输出 ---")
    print(result.stdout)
    if result.stderr:
        print(f"\n--- stderr ---")
        print(result.stderr[:2000])
    print(f"\n退出码: {result.returncode}")

    # 保存结果
    log_path = os.path.join(PROJECT_DIR, "scripts", "_test_004_result.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"返回码: {result.returncode}\n\n")
        f.write(result.stdout)
        if result.stderr:
            f.write(f"\n\n--- stderr ---\n{result.stderr}")
    print(f"\n结果已保存: {log_path}")

    return result.returncode == 0


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "回收站"
    success = run_test(target)
    sys.exit(0 if success else 1)
