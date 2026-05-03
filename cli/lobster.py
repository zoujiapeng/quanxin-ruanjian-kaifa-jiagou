#!/usr/bin/env python3
"""
Lobster CLI - 命令行自动化工具

用法:
  lobster run "CLICK 开始"
  lobster run-file task.lobster
  lobster health / status / pause / resume / stop
  lobster call click-target target="确认"
  lobster list [category]
  lobster info <feature>
  lobster test [category]
  lobster mcp                    # 启动 MCP 服务端
"""
import sys, os, json, time
from pathlib import Path

if sys.platform == "win32":
    for s in (sys.stdin, sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

BACKEND_URL = os.getenv("LOBSTER_URL", "http://localhost:7788")

def _url(): return os.environ.get("LOBSTER_URL", BACKEND_URL)


def _req(method, path, **kw):
    if not HAS_REQUESTS:
        print("需要安装 requests 库: pip install requests", file=sys.stderr)
        sys.exit(1)
    try:
        kwargs = {"timeout": kw.pop("timeout", 15)}
        kwargs.update(kw)
        r = getattr(requests, method)(f"{_url()}{path}", **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        print(f"无法连接后端 ({_url()})", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr)
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# 命令实现
# ═══════════════════════════════════════════════════════════════

def cmd_run(args):
    dsl = args[0] if args else ""
    if dsl == "-" and not sys.stdin.isatty():
        dsl = sys.stdin.read()
    if not dsl.strip():
        print("错误: DSL 内容为空", file=sys.stderr); sys.exit(1)
    data = _req("post", "/api/dsl/run", json={"dsl": dsl})
    print(f"任务已提交 (ID: {data['task_id']})")

def cmd_run_file(args):
    path = Path(args[0])
    if not path.exists():
        print(f"文件不存在: {path}", file=sys.stderr); sys.exit(1)
    cmd_run([path.read_text("utf-8")])

def cmd_parse(args):
    dsl = args[0] if args else ""
    try:
        from engine.dsl_parser import DSLParser
        ast = DSLParser.from_string(dsl)
        print(json.dumps(ast.to_dict(), ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"解析失败: {e}", file=sys.stderr); sys.exit(1)

def cmd_health(args):
    data = _req("get", "/api/health")
    print(f"后端: {data.get('status', '?')}")
    print(f"执行器: {data.get('executor_state', '?')}")
    print(f"功能数: {data.get('features', 0)}")
    print(f"模式: {'真实' if not data.get('simulation_mode') else '模拟'}")

def cmd_status(args):
    data = _req("get", "/api/executor/status")
    print(f"状态: {data['state']}")
    print(f"队列: {data['queue'].get('queued', 0)} 个")
    for h in data['queue'].get('history', [])[-5:]:
        print(f"  [{h['status']}] {h['task_id']} ({h['elapsed']}s)")

def cmd_pause(args):   print(f"已暂停 (状态: {_req('post','/api/executor/pause')['state']})")
def cmd_resume(args):  print(f"已恢复 (状态: {_req('post','/api/executor/resume')['state']})")
def cmd_stop(args):    print(f"已停止 (状态: {_req('post','/api/executor/stop')['state']})")

def cmd_logs(args):
    count = int(args[0]) if args else 50
    data = _req("get", f"/api/logs?count={count}")
    for e in data.get("logs", []):
        ts = time.strftime("%H:%M:%S", time.localtime(e["ts"]))
        print(f"[{ts}] {e['msg']}")

def cmd_restart(args):
    import subprocess
    print("重启后端...")
    if sys.platform == "win32":
        subprocess.run("taskkill /f /fi \"WINDOWTITLE eq python*server*\" 2>nul", shell=True)
    else:
        subprocess.run("pkill -f 'python.*server.py' 2>/dev/null", shell=True)
    time.sleep(1)
    port = args[0] if args else os.getenv("LOBSTER_PORT", "7788")
    env = os.environ.copy()
    env["LOBSTER_PORT"] = str(port)
    backend_dir = Path(__file__).resolve().parent.parent / "python"
    log_path = backend_dir / "server.log"
    kwargs = {"stdout": open(log_path, "w", encoding="utf-8"), "stderr": subprocess.STDOUT}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(["python", "server.py"], cwd=str(backend_dir), env=env, **kwargs)
    print(f"后端启动中, 日志: {log_path}")

def cmd_run_sync(args):
    dsl = args[0] if args else ""
    if dsl == "-" and not sys.stdin.isatty():
        dsl = sys.stdin.read()
    if not dsl.strip():
        print("错误: DSL 内容为空", file=sys.stderr); sys.exit(1)
    print("执行中...")
    data = _req("post", "/api/dsl/run-sync", json={"dsl": dsl, "timeout": 30}, timeout=40)
    for e in data.get("logs", []):
        print(f"  {e['msg']}")
    print(f"\n状态: {data.get('state','?')}  耗时: {data.get('elapsed',0)}s")
    if not data.get("success"):
        print(f"错误: {data.get('error','未知')}", file=sys.stderr)
        sys.exit(1)

def cmd_call(args):
    """lobster call <feature> [key=value ...]"""
    if not args:
        print("用法: lobster call <功能名> [key=value ...]", file=sys.stderr)
        sys.exit(1)
    name = args[0]
    kwargs = {}
    for a in args[1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            kwargs[k.strip()] = v.strip()
        elif a.startswith("--") and "=" in a[2:]:
            k, v = a[2:].split("=", 1)
            kwargs[k.strip()] = v.strip()
    try:
        resp = requests.post(f"{_url()}/api/feature/{name}", json=kwargs, timeout=30)
        data = resp.json()
    except Exception as e:
        print(f"请求失败: {e}", file=sys.stderr); sys.exit(1)
    if data.get("success"):
        result = data.get("result", "")
        if isinstance(result, (dict, list)):
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)
        ms = data.get("elapsed_ms", 0)
        print(f"\n# 耗时: {ms}ms")
    else:
        print(f"错误: {data.get('error', '未知')}", file=sys.stderr)
        avail = data.get("available", [])
        if avail:
            print(f"可用功能: {', '.join(avail)}", file=sys.stderr)
        sys.exit(1)

def cmd_list(args):
    category = args[0] if args else ""
    params = f"?category={category}" if category else ""
    data = _req("get", f"/api/features{params}")
    if not data:
        print("(无功能)")
        return
    cats = {}
    for f in data:
        cats.setdefault(f["category"], []).append(f)
    for cat, feats in cats.items():
        print(f"\n[{cat.upper()}]")
        for f in feats:
            dsl = f"  DSL: {f['dsl_keyword']}" if f.get("dsl_keyword") else ""
            print(f"  {f['name']:25s} {f['display_name']}{dsl}")

def cmd_info(args):
    if not args:
        print("用法: lobster info <功能名>", file=sys.stderr); sys.exit(1)
    data = _req("get", f"/api/feature/{args[0]}") if False else None
    # 从注册表获取 (不需要后端)
    try:
        import features._all  # noqa
        from features.registry import registry
        spec = registry.get(args[0])
        if not spec:
            print(f"功能 '{args[0]}' 不存在", file=sys.stderr)
            sys.exit(1)
        d = spec.to_dict()
        print(f"名称: {d['name']} ({d['display_name']})")
        print(f"描述: {d['description']}")
        print(f"类别: {d['category']}")
        print(f"MCP工具: {d['mcp_tool_name']}")
        print(f"HTTP: {d['http_endpoint']}")
        if d.get("dsl_keyword"):
            print(f"DSL: {d['dsl_template']}")
        print(f"\n参数 ({len(d['params'])}):")
        for p in d["params"]:
            req = "必填" if p["required"] else f"可选, 默认={p['default']}"
            print(f"  --{p['name']} ({p['type']}) {req}")
            print(f"    {p['description']}")
        print(f"\n返回值: {d['returns']}")
        if d.get("examples"):
            print(f"\n示例:")
            for ex in d["examples"]:
                print(f"  {ex}")
        if d.get("test_cases"):
            print(f"\n测试用例: {len(d['test_cases'])} 个")
    except Exception as e:
        print(f"获取失败: {e}", file=sys.stderr)
        sys.exit(1)

def cmd_test(args):
    category = args[0] if args else ""
    data = _req("post", "/api/feature/debug_run_tests",
                json={"category": category, "skip_ci": True})
    if not data.get("success"):
        print(f"测试失败: {data.get('error', '未知')}", file=sys.stderr)
        sys.exit(1)
    result = data.get("result", {})
    passed, failed, skipped = result.get("passed", 0), result.get("failed", 0), result.get("skipped", 0)
    for d in result.get("details", []):
        icon = {"passed": "OK", "failed": "FAIL", "skipped": "SKIP"}.get(d["status"], "?")
        print(f"  [{icon}] [{d['feature']}] {d['test']}")
    print(f"\n结果: {passed} 通过, {failed} 失败, {skipped} 跳过")
    if failed:
        sys.exit(1)

def cmd_mcp(args):
    """启动 MCP 服务端"""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))
    from mcp.server import serve
    serve()

def cmd_region_select(args):
    """用户交互式框选区域 (无需后端, 直接显示 tkinter 窗口)

    用法: lobster region-select [message]
         lobster region-select "请框选进度条区域"
    输出: {"x": 100, "y": 200, "w": 300, "h": 50}
    """
    message = args[0] if args else "请拖拽选择监控区域"
    try:
        from interaction.region_picker import RegionPicker
    except ImportError:
        print("错误: 无法导入 RegionPicker", file=sys.stderr)
        sys.exit(1)
    region = RegionPicker.pick(message)
    if region:
        x, y, w, h = region
        result = {"x": x, "y": y, "w": w, "h": h}
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps({"cancelled": True}))


def cmd_exec(args):
    """直接执行 DSL (无需后端, 直接调用执行引擎)

    用法: lobster exec <dsl 代码>
         lobster exec "CLICK 开始"
         lobster exec script.lobster    # 自动检测文件
         echo "CLICK 开始" | lobster exec -

    这是新 Claude Code 最常用的命令:
    不需要 MCP 工具, 不需要后端服务器, 一行命令直接运行
    """
    dsl = args[0] if args else ""
    if dsl == "-" and not sys.stdin.isatty():
        dsl = sys.stdin.read()
    # 自动检测文件路径
    if dsl and not dsl.startswith(("CLICK", "WAIT", "LOOP", "IF", "SCREENSHOT",
                                    "TYPE", "LAUNCH", "FOCUS", "HOTKEY", "SET",
                                    "OCR_FIND", "OCR_EXTRACT", "REGION_SELECT",
                                    "SUBROUTINE", "CALL", "WHEN", "PARALLEL")):
        p = Path(dsl)
        if p.exists():
            dsl = p.read_text("utf-8")
    if not dsl.strip():
        print("用法: lobster exec \"CLICK 目标\"", file=sys.stderr)
        sys.exit(1)

    try:
        from engine.executor import DSLExecutor
        from interaction.actions import ActionHandler
        exe = DSLExecutor(action_handler=ActionHandler())
        # 把日志输出到控制台
        exe.on("log", lambda **kw: print(f"  {kw.get('message','')}", flush=True))
        exe.on("node_start", lambda **kw: print(f"  ▶ {kw['node_type']}: {str(kw.get('args',''))[:60]}", flush=True))
        result = exe.run_dsl_sync(dsl)
        success = result.get("success", True)
        state = result.get("state", "?")
        elapsed = result.get("elapsed", 0)
        if not success:
            print(f"\n✗ 执行失败: {result.get('error','未知错误')}", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"\n✓ 执行完成: state={state}")
    except Exception as e:
        print(f"执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════

COMMANDS = {
    "run": cmd_run, "run-file": cmd_run_file, "run-sync": cmd_run_sync,
    "exec": cmd_exec,
    "parse": cmd_parse, "health": cmd_health, "status": cmd_status,
    "pause": cmd_pause, "resume": cmd_resume, "stop": cmd_stop,
    "logs": cmd_logs, "restart": cmd_restart,
    "call": cmd_call, "list": cmd_list, "info": cmd_info, "test": cmd_test,
    "mcp": cmd_mcp,
    "region-select": cmd_region_select,
}

HELP = """Lobster CLI v2 - 低Token AI自动化执行系统

用法: lobster <command> [参数...]

后端 (需运行 lobster restart 启动):
  run <dsl>                 执行 DSL
  run-file <file>           从文件执行 DSL
  run-sync <dsl>            同步执行 DSL (等待完成)
  restart [port]            重启后端

直接 (无需后端):
  exec <dsl>                直接执行 DSL
  parse <dsl>               解析 DSL 为 AST
  region-select [message]   用户框选区域 → JSON

状态:
  health                    检查后端状态
  status                    查看执行器状态
  pause / resume / stop     控制执行器
  logs [n]                  查看执行日志

功能:
  call <name> [key=val...]  调用注册功能
  list [category]           列出功能
  info <name>               功能详情
  test [category]           运行测试

集成:
  mcp                       启动 MCP 服务端

新 Claude Code 工作流:
  1. lobster region-select "框选监控区域"  → 获得 JSON 坐标
  2. lobster exec "LOOP ... IF PROGRESS {x},{y},{w},{h} ..."  → 执行监控

示例:
  lobster run "CLICK 开始"
  lobster exec "CLICK 确认"
  lobster region-select "请框选进度条区域"
"""

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(HELP)
        return
    cmd = sys.argv[1]
    if cmd in COMMANDS:
        COMMANDS[cmd](sys.argv[2:])
    elif cmd == "feature":
        # lobster feature <name> [key=val...]
        cmd_call(sys.argv[2:])
    else:
        print(f"未知命令: {cmd}\n{HELP}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
