#!/usr/bin/env python3
"""
Lobster 自动化测试套件
可被 Claude Code 通过 MCP 或 CLI 调用，实现自主调试
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import features.action_features      # noqa
import features.perception_features  # noqa
import features.ai_debug_features    # noqa
import features.system_features      # noqa

from features.registry import registry


class Colors:
    GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"
    CYAN = "\033[96m"; BOLD = "\033[1m"; RESET = "\033[0m"


def run_suite(skip_ci=True, verbose=False):
    print(f"\n{Colors.BOLD}Lobster Test Suite{Colors.RESET}")
    print("=" * 50)
    results = registry.run_tests(skip_ci=skip_ci)
    for d in results["details"]:
        s = d["status"]
        icon = f"{Colors.GREEN}OK{Colors.RESET}" if s == "passed" else \
               f"{Colors.YELLOW}--{Colors.RESET}" if s == "skipped" else \
               f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  [{icon}] [{d['feature']}] {d['test']}")
        if verbose and s == "failed":
            err = d.get("result", {}).get("error", "")
            if err:
                print(f"    {Colors.RED}{err}{Colors.RESET}")
    p, f, s = results["passed"], results["failed"], results["skipped"]
    color = Colors.GREEN if f == 0 else Colors.RED
    print(f"\n{color}{p} passed, {f} failed, {s} skipped{Colors.RESET}\n")
    return f


def run_dsl_roundtrip():
    print(f"\n{Colors.BOLD}DSL <-> 流程图 往返测试{Colors.RESET}")
    test_dsls = [
        "CLICK 开始",
        "CLICK 开始\nWAIT 完成",
        "LOOP 主循环\n  CLICK 攻击\nEND",
        "IF 条件\n  CLICK A\nELSE\n  CLICK B\nEND",
    ]
    passed = 0
    for dsl in test_dsls:
        graph_r = registry.execute("dsl_to_graph", dsl=dsl)
        if not graph_r["success"]:
            print(f"  {Colors.RED}FAIL DSL->图: {graph_r.get('error')}{Colors.RESET}")
            continue
        back_r = registry.execute(
            "graph_to_dsl",
            nodes=json.dumps(graph_r["result"]["nodes"]),
            edges=json.dumps(graph_r["result"]["edges"]),
        )
        ok = back_r["success"]
        if ok:
            print(f"  {Colors.GREEN}OK{Colors.RESET} {dsl[:40]!r}")
            passed += 1
        else:
            print(f"  {Colors.RED}FAIL{Colors.RESET} {dsl[:40]!r}")
    print(f"\n{passed}/{len(test_dsls)} 通过\n")
    return len(test_dsls) - passed


def run_parser_test():
    print(f"\n{Colors.BOLD}DSL 解析器测试{Colors.RESET}")
    from engine.dsl_parser import DSLParser
    cases = [
        ("CLICK 开始", True),
        ("WAIT 完成", True),
        ("LOOP 标签\n  CLICK A\nEND", True),
        ("IF 条件\n  CLICK A\nELSE\n  CLICK B\nEND", True),
        ("INVALID_CMD arg", False),
        ("LOOP\n  CLICK A", False),
    ]
    passed = 0
    for dsl, should_pass in cases:
        try:
            DSLParser.from_string(dsl)
            ok = should_pass
        except Exception:
            ok = not should_pass
        icon = f"{Colors.GREEN}OK{Colors.RESET}" if ok else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  [{icon}] {dsl[:40]!r}")
        if ok:
            passed += 1
    print(f"\n{passed}/{len(cases)} 通过\n")
    return len(cases) - passed


def run_registry_test():
    print(f"\n{Colors.BOLD}注册表完整性测试{Colors.RESET}")
    errors = []
    for spec in registry.all():
        if not spec.name:
            errors.append("功能缺少 name")
        if not spec.description:
            errors.append(f"[{spec.name}] 缺少 description")
        try:
            schema = spec.to_mcp_schema()
            assert "name" in schema
        except Exception as e:
            errors.append(f"[{spec.name}] MCP schema: {e}")
        try:
            spec.to_cli_help()
        except Exception as e:
            errors.append(f"[{spec.name}] CLI help: {e}")

    if errors:
        for e in errors:
            print(f"  {Colors.RED}FAIL{Colors.RESET} {e}")
    else:
        print(f"  {Colors.GREEN}OK{Colors.RESET} 所有 {len(registry.all())} 个功能通过")
    print(f"  MCP 工具: {len(registry.export_mcp_tools())}")
    try:
        oa = registry.export_openapi()
        print(f"  OpenAPI: {len(oa['paths'])} 个路径")
    except Exception as e:
        errors.append(f"OpenAPI: {e}")
    return len(errors)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Lobster 测试套件")
    parser.add_argument("--include-ci", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--suite", choices=["all", "unit", "parser", "registry", "roundtrip"], default="all")
    args = parser.parse_args()

    failures = 0
    if args.suite in ("all", "registry"):
        failures += run_registry_test()
    if args.suite in ("all", "parser"):
        failures += run_parser_test()
    if args.suite in ("all", "roundtrip"):
        failures += run_dsl_roundtrip()
    if args.suite in ("all", "unit"):
        failures += run_suite(skip_ci=not args.include_ci, verbose=args.verbose)

    if failures == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}所有测试通过!{Colors.RESET}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}{failures} 个测试失败{Colors.RESET}")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
