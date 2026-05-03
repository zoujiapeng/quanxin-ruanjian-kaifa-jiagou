"""
E2E 集成测试 — 启动后端并测试 HTTP API 各端点

运行:
  python tests/test_e2e.py

依赖:
  pip install requests
"""
import sys, json, time, subprocess, os, signal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python"))

BACKEND_URL = "http://localhost:7788"
PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [OK] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} {detail}")


def req(method, path, **kw):
    import requests
    kwargs = {"timeout": kw.pop("timeout", 10)}
    kwargs.update(kw)
    r = getattr(requests, method)(f"{BACKEND_URL}{path}", **kwargs)
    return r.json()


class E2ETest:
    """E2E 集成测试套件"""

    def test_health(self):
        """健康检查"""
        data = req("get", "/api/health")
        check("health 返回 ok", data.get("status") == "ok",
              f"got: {data.get('status')}")
        check("health 返回功能数 > 0", data.get("features", 0) > 0,
              f"features: {data.get('features')}")
        check("health 有 version", bool(data.get("version")),
              f"version: {data.get('version')}")

    def test_registry_formats(self):
        """注册表导出格式"""
        for fmt in ("json", "markdown", "mcp", "openapi", "dsl"):
            data = req("get", f"/api/registry?format={fmt}")
            if fmt == "json":
                check(f"registry format={fmt} 是列表", isinstance(data, list),
                      f"type: {type(data).__name__}")
                check("registry 列表非空", len(data) > 0,
                      f"count: {len(data)}")
            elif fmt == "mcp":
                check(f"registry format={fmt} 有 tools", "tools" in data,
                      f"keys: {list(data.keys())}")
                check("mcp tools > 0", len(data.get("tools", [])) > 0)
            elif fmt == "openapi":
                check(f"registry format={fmt} 有 paths", "paths" in data,
                      f"keys: {list(data.keys())}")

    def test_features_list(self):
        """功能列表"""
        data = req("get", "/api/features")
        check("features 是列表", isinstance(data, list))
        check("features 非空", len(data) > 0)
        if data:
            f = data[0]
            check("feature 有 name", "name" in f)
            check("feature 有 category", "category" in f)
            check("feature 有 description", "description" in f)

    def test_features_by_category(self):
        """按分类筛选"""
        data = req("get", "/api/features?category=action")
        check("category=action 是列表", isinstance(data, list))
        if data:
            all_action = all(f.get("category") == "action" for f in data)
            check("category=action 全部是 action 类型", all_action)

    def test_dsl_parse(self):
        """DSL 解析"""
        data = req("post", "/api/dsl/parse", json={"dsl": "CLICK test"})
        check("dsl parse 成功", data.get("success", False),
              f"error: {data.get('error', '')}")
        if data.get("success"):
            ast = data.get("ast", {})
            check("dsl parse 有 type", "type" in ast)
            check("dsl parse 有 children", "children" in ast)

    def test_dsl_parse_invalid(self):
        """DSL 解析 - 非法输入"""
        import requests
        r = requests.post(f"{BACKEND_URL}/api/dsl/parse",
                          json={"dsl": "INVALID_CMD"}, timeout=10)
        data = r.json()
        check("dsl parse 非法输入返回 400", r.status_code == 400,
              f"status: {r.status_code}")

    def test_feature_call(self):
        """调用功能 - debug_list_features"""
        data = req("get", "/api/feature/debug_list_features")
        check("call feature 成功", data.get("success", False),
              f"error: {data.get('error', '')}")
        if data.get("success"):
            result = data.get("result", [])
            check("feature 结果非空", len(result) > 0)

    def test_feature_call_with_body(self):
        """POST 调用功能带参数"""
        data = req("post", "/api/feature/debug_list_features",
                   json={"format_": "json"})
        check("POST call feature 成功", data.get("success", False),
              f"error: {data.get('error', '')}")

    def test_feature_not_found(self):
        """调用不存在的功能"""
        import requests
        r = requests.get(f"{BACKEND_URL}/api/feature/nonexistent_feature_xxx",
                         timeout=10)
        data = r.json()
        check("不存在功能返回 404", r.status_code == 404,
              f"status: {r.status_code}")
        check("404 有 error 字段", "error" in data)

    def test_executor_status(self):
        """执行器状态"""
        data = req("get", "/api/executor/status")
        check("executor status 有 state", "state" in data,
              f"state: {data.get('state', '?')}")
        check("executor status 有 queue", "queue" in data)

    def test_logs(self):
        """日志"""
        data = req("get", "/api/logs")
        check("logs 返回 dict", isinstance(data, dict))
        check("logs 有 logs 字段", "logs" in data)

    def test_dsl_state(self):
        """DSL 状态"""
        data = req("get", "/api/dsl/state")
        check("dsl state 有 dsl", "dsl" in data)
        check("dsl state 有 executor_state", "executor_state" in data)

    def run_all(self):
        tests = [
            self.test_health,
            self.test_registry_formats,
            self.test_features_list,
            self.test_features_by_category,
            self.test_dsl_parse,
            self.test_dsl_parse_invalid,
            self.test_feature_call,
            self.test_feature_call_with_body,
            self.test_feature_not_found,
            self.test_executor_status,
            self.test_logs,
            self.test_dsl_state,
        ]
        print(f"\nE2E 集成测试 ({len(tests)} 项)\n" + "=" * 40)
        for t in tests:
            try:
                t()
            except Exception as e:
                global FAIL
                FAIL += 1
                print(f"  [FAIL] {t.__name__}: {e}")
        print(f"\n结果: {PASS} 通过, {FAIL} 失败\n")
        return FAIL


def main():
    # 检查后端是否运行
    import requests
    try:
        r = requests.get(f"{BACKEND_URL}/api/health", timeout=3)
        print(f"后端运行中: {BACKEND_URL}")
    except requests.exceptions.ConnectionError:
        print(f"后端未运行 ({BACKEND_URL})")
        print("请先启动: cd python && python server.py")
        return 1

    suite = E2ETest()
    failures = suite.run_all()
    return failures


if __name__ == "__main__":
    sys.exit(main())
