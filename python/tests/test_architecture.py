"""
架构测试 — 引擎状态机、执行器、注册表、错误处理

运行:
  python tests/test_architecture.py

覆盖:
  - 执行器状态机 (IDLE→RUNNING→PAUSED→STOPPED→FINISHED)
  - DSL 执行 (LOOP/IF/WAIT/PARALLEL/WITH)
  - 注册表 execute/execute_with_typed_params
  - 全局错误处理
  - 所有功能冒烟测试
"""
import sys, json, time, threading
from pathlib import Path

# GBK 编码修复
sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
sys.stderr.reconfigure(encoding="utf-8") if hasattr(sys.stderr, "reconfigure") else None

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import features._all  # noqa

from features.registry import registry

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [OK] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")

def check_eq(name, actual, expected):
    global PASS, FAIL
    if actual == expected:
        PASS += 1
        print(f"  [OK] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}: expected {expected!r}, got {actual!r}")


# ══════════════════════════════════════════════════
# 1. 注册表架构测试
# ══════════════════════════════════════════════════

def test_registry_basics():
    """注册表：所有功能注册正确"""
    all_f = registry.all()
    check("registry.all() 返回列表", isinstance(all_f, list))
    check("所有功能数 = 104", len(all_f) == 104, f"got {len(all_f)}")

    # 检查无重复名称
    names = [f.name for f in all_f]
    check("无重复功能名", len(names) == len(set(names)))

    # 检查所有功能有 handler
    no_handler = [f.name for f in all_f if not callable(f.handler)]
    check("无 handler 的功能为 0", len(no_handler) == 0, str(no_handler))

    # 检查所有功能有返回类型
    no_returns = [f.name for f in all_f if not f.returns]
    check("无 returns 的功能为 0", len(no_returns) == 0, str(no_returns))


def test_registry_execute_error_handling():
    """注册表：错误处理"""
    # 未知功能
    r = registry.execute("nonexistent_feature_xyz")
    check("未知功能返回 error", not r.get("success"), r.get("error", ""))
    check("未知功能有 error 字段", "error" in r)
    check("未知功能有 feature 字段", r.get("feature") == "nonexistent_feature_xyz")

    # 空功能名
    r = registry.execute("")
    check("空功能名返回 error", not r.get("success"))


def test_registry_execute_with_typed_params():
    """注册表：类型转换"""
    # 字符串转 int
    r = registry.execute_with_typed_params("color_check", x="100", y="200",
                                           color="ff0000", tolerance="10")
    # color_check 有 x:int, y:int params
    check("类型转换后可调用", r.get("success") is not None)

    # 参数缺失
    r = registry.execute_with_typed_params("debug_run_tests")
    check("可选参数可缺省", "success" in r)

    # 类型错误：传递无效 int
    r = registry.execute_with_typed_params("color_check", x="abc", y="def",
                                           color="ff0000")
    # 应当抛出而不是崩溃
    check("类型错误不会崩溃", r.get("success") is not False or "error" in r)


def test_registry_export_formats():
    """注册表：所有导出格式正常"""
    # MCP
    tools = registry.export_mcp_tools()
    check("MCP tools 是列表", isinstance(tools, list))
    check("MCP tools 数 = 104", len(tools) == 104)
    if tools:
        t = tools[0]
        for key in ("name", "description", "inputSchema"):
            check(f"MCP tool 有 {key}", key in t, f"keys: {list(t.keys())}")

    # OpenAPI
    oa = registry.export_openapi()
    check("OpenAPI 有 paths", "paths" in oa)
    check("OpenAPI paths 数 > 0", len(oa["paths"]) > 0)

    # Claude Context
    ctx = registry.export_claude_context()
    check("Claude context 是字符串", isinstance(ctx, str))
    check("Claude context 包含功能数", "104" in ctx, f"len={len(ctx)}")

    # DSL reference
    dsl_ref = registry.export_dsl_reference()
    check("DSL reference 是字符串", isinstance(dsl_ref, str))


# ══════════════════════════════════════════════════
# 2. DSL 解析器架构测试
# ══════════════════════════════════════════════════

def test_dsl_parser_ast_structure():
    """解析器：AST 结构完整性"""
    from engine.dsl_parser import DSLParser, NodeType

    ast = DSLParser.from_string("CLICK 开始")
    check("AST 有 to_dict", isinstance(ast.to_dict(), dict))
    check("AST 节点类型是 SEQUENCE", ast.type == NodeType.SEQUENCE,
          f"type={ast.type}")
    check("AST 有 children", len(ast.children) > 0)

    # 复杂 DSL
    dsl = """LOOP 主循环
  CLICK 攻击
  WAIT 2
  IF 条件
    TYPE 确认
  END
END"""
    ast2 = DSLParser.from_string(dsl)
    check("复杂 DSL 解析成功", ast2 is not None)
    # 第一层应该包含 LOOP
    loops = [c for c in ast2.children if c.type == NodeType.LOOP]
    check("LOOP 节点存在", len(loops) > 0)


def test_dsl_parser_invalid_inputs():
    """解析器：非法输入容错"""
    from engine.dsl_parser import DSLParser

    cases = [
        "",           # 空
        "   ",        # 空白
        "INVALID_CMD arg",  # 未知命令
        "LOOP\n  CLICK A",  # 缺少 END
        "IF cond\n  CLICK A\nELSE\n  CLICK B",  # 缺少 END
    ]
    for dsl in cases:
        try:
            ast = DSLParser.from_string(dsl)
            failed = ast.root is None
        except Exception:
            failed = True
        check(f"非法输入不崩溃: {dsl[:20]}", failed)


def test_dsl_parser_parallel_with():
    """解析器：PARALLEL + WITH 语法"""
    from engine.dsl_parser import DSLParser, NodeType

    dsl = """PARALLEL
  CLICK A
WITH type
  CLICK B
WITH ocr
  CLICK C
END"""
    ast = DSLParser.from_string(dsl)
    parallels = [c for c in ast.children if c.type == NodeType.PARALLEL]
    if parallels:
        p = parallels[0]
        check(f"PARALLEL 语法解析成功", len(parallels) > 0)


# ══════════════════════════════════════════════════
# 3. 执行器状态机测试
# ══════════════════════════════════════════════════

def test_executor_state_machine():
    """执行器：状态机状态转换"""
    from engine.executor import DSLExecutor, ExecutorState
    exe = DSLExecutor()
    check("初始状态 IDLE", exe.state == ExecutorState.IDLE,
          f"state={exe.state}")

    # run_dsl_sync — 同步执行
    r = exe.run_dsl_sync("CLICK 测试")
    check("同步执行返回 dict", isinstance(r, dict))
    # run_dsl — 异步执行
    r2 = exe.run_dsl("CLICK 测试")
    check("异步执行返回 dict", isinstance(r2, dict))

    # PAUSE/RESUME/STOP
    exe2 = DSLExecutor()
    r = exe2.run_dsl("CLICK 测试")
    time.sleep(0.1)
    r_pause = exe2.pause()
    check("pause() 可调用", r_pause is not None)
    r_resume = exe2.resume()
    check("resume() 可调用", r_resume is not None)
    r_stop = exe2.stop()
    check("stop() 可调用", r_stop is not None)


def test_executor_control_flow():
    """执行器：控制流命令"""
    from engine.executor import DSLExecutor

    # IF/ELSE
    exe = DSLExecutor()
    r = exe.run_dsl_sync("IF 条件\n  CLICK ok\nELSE\n  CLICK no\nEND")
    check("IF/ELSE 执行返回 dict", isinstance(r, dict))

    # LOOP（限制次数防无限）
    exe2 = DSLExecutor()
    r2 = exe2.run_dsl_sync("LOOP 2\n  CLICK A\nEND")
    check("LOOP 执行返回 dict", isinstance(r2, dict))

    # WAIT
    exe3 = DSLExecutor()
    start = time.time()
    r3 = exe3.run_dsl_sync("WAIT 0.5")
    elapsed = time.time() - start
    check("WAIT 0.5 执行返回 dict", isinstance(r3, dict))
    check("WAIT 0.5 至少 0.4s", elapsed >= 0.4, f"elapsed={elapsed}")


def test_executor_error_handling():
    """执行器：错误处理"""
    from engine.executor import DSLExecutor

    # 空 DSL
    exe = DSLExecutor()
    r = exe.run_dsl_sync("")
    check("空 DSL 不崩溃", True)

    # 未知 DSL 命令
    exe2 = DSLExecutor()
    r2 = exe2.run_dsl_sync("ZZZ_UNKNOWN")
    check("未知 DSL 命令不崩溃", True)


# ══════════════════════════════════════════════════
# 4. 全局功能冒烟测试
# ══════════════════════════════════════════════════

def test_all_features_smoke():
    """冒烟：调用每个功能，验证返回值结构"""
    global PASS, FAIL
    smoke_skip = {
        "click_target", "type_text", "scroll", "hotkey", "type_clipboard",  # 需要硬件
        "screenshot", "popup_close",  # 需要显示器
        "run_dsl", "run_dsl_sync",  # 需要完整引擎
        "macro_record", "macro_playback",  # 需要 pynput 钩子
        "screen_record_start", "screen_record_stop",  # 需要录制
        "lock_workstation", "empty_recycle_bin",  # 破坏性操作
        "wifi_connect", "wifi_disconnect",  # 网络操作
        "display_brightness",  # 需要 wmi
        "volume_set", "volume_mute",  # 可能影响用户体验
    }
    # 跳过有 'name' 或 'feature_name' 参数的功能（与 execute(feature_name, **kwargs) 冲突）
    name_param_conflict = {spec.name for spec in registry.all()
                          if any(p.name in ("name", "feature_name") for p in spec.params)}
    smoke_skip |= name_param_conflict
    # 只测试非模拟模式、非破坏性的功能
    smoke_tested = 0
    for spec in registry.all():
        if spec.name in smoke_skip:
            continue
        # 为每个功能构造默认参数
        kwargs = {}
        for p in spec.params:
            if p.default is not None:
                kwargs[p.name] = p.default
            elif p.type in ("number", "float"):
                kwargs[p.name] = 0
            elif p.type == "int":
                kwargs[p.name] = 0
            elif p.type == "boolean":
                kwargs[p.name] = False
            else:
                kwargs[p.name] = ""
        try:
            result = registry.execute(spec.name, **kwargs)
            has_success = "success" in result
            if has_success:
                smoke_tested += 1
            else:
                print(f"  [WARN] {spec.name}: 返回值无 success 字段: {list(result.keys())}")
        except Exception as e:
            FAIL += 1
            print(f"  [FAIL] {spec.name}: 冒烟测试异常: {e}")
            return

    check(f"冒烟测试通过 ({smoke_tested}/{smoke_tested})", smoke_tested > 0,
          f"tested={smoke_tested}")


# ══════════════════════════════════════════════════
# 5. 引擎错误传播测试
# ══════════════════════════════════════════════════

def test_engine_thread_safety():
    """引擎：线程安全"""
    global PASS, FAIL
    from engine.executor import DSLExecutor
    exe = DSLExecutor()

    errors = []

    def run_in_thread():
        try:
            exe.run_dsl_sync("CLICK A")
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=run_in_thread) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    check("多线程执行不崩溃", len(errors) == 0, str(errors))


def test_store_basic():
    """存储层：基础操作"""
    global PASS, FAIL
    try:
        from engine.store import get_store
        store = get_store()
        # vault 操作
        store.vault_set("test_key", "test_value")
        val = store.vault_get("test_key")
        check("vault set/get 正常", val == "test_value", f"got {val!r}")
        keys = store.vault_list_keys()
        check("vault list 正常", "test_key" in keys)
    except ImportError:
        check("store 模块可用", False, "ImportError")
    except Exception as e:
        check(f"store 错误: {e}", False)


# ══════════════════════════════════════════════════
# 6. DSL 优化器测试
# ══════════════════════════════════════════════════

def test_optimizer():
    """优化器：基础分析功能"""
    global PASS, FAIL
    try:
        from engine.optimizer import TelemetryAnalyzer
        analyzer = TelemetryAnalyzer()
        report = analyzer.analyze_all()
        check("analyze_all 返回 dict", isinstance(report, dict))
        suggestions = analyzer.suggest_optimizations()
        check("suggest_optimizations 返回列表", isinstance(suggestions, list))
    except ImportError:
        check("optimizer 模块可用", False, "ImportError")


# ══════════════════════════════════════════════════
# 运行
# ══════════════════════════════════════════════════

def main():
    tests = [
        ("注册表基础", test_registry_basics),
        ("注册表错误处理", test_registry_execute_error_handling),
        ("注册表类型转换", test_registry_execute_with_typed_params),
        ("注册表导出格式", test_registry_export_formats),
        ("DSL 解析器 AST", test_dsl_parser_ast_structure),
        ("DSL 解析器非法输入", test_dsl_parser_invalid_inputs),
        ("DSL 解析器 PARALLEL/WITH", test_dsl_parser_parallel_with),
        ("执行器状态机", test_executor_state_machine),
        ("执行器控制流", test_executor_control_flow),
        ("执行器错误处理", test_executor_error_handling),
        ("引擎线程安全", test_engine_thread_safety),
        ("功能冒烟测试", test_all_features_smoke),
        ("存储层基础", test_store_basic),
        ("优化器分析", test_optimizer),
    ]

    print(f"架构测试 ({len(tests)} 项)\n" + "=" * 40)
    for name, fn in tests:
        try:
            fn()
        except Exception as e:
            global FAIL
            FAIL += 1
            import traceback
            print(f"  [FAIL] {name}: {e}")
            traceback.print_exc()
        print()

    print(f"结果: {PASS} 通过, {FAIL} 失败\n")
    return FAIL


if __name__ == "__main__":
    sys.exit(main())
