"""
╔══════════════════════════════════════════════════════════════════╗
║           Lobster 功能注册系统 (Feature Registry)                 ║
║                                                                  ║
║  设计原则：功能即注册                                              ║
║  ─────────────────────────────────────────────────────────────  ║
║  1. 新增功能只需一处声明 @feature(...)                             ║
║  2. MCP工具、CLI命令、HTTP API 全部自动生成                        ║
║  3. Claude Code 可读取注册表自主调试和扩展                         ║
║  4. 测试用例随功能一起注册，自动可测                               ║
╚══════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations
import importlib
import importlib.util
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
from pathlib import Path


class FeatureCategory(str, Enum):
    ACTION      = "action"
    PERCEPTION  = "perception"
    CONTROL     = "control"
    MACRO       = "macro"
    AI          = "ai"
    SYSTEM      = "system"
    DEBUG       = "debug"


@dataclass
class ParamSpec:
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    example: Any = None


@dataclass
class TestCase:
    name: str
    params: dict
    expected_type: str  # "success" | "non_null" | "bool_true" | "custom"
    validator: Optional[Callable] = None
    skip_in_ci: bool = False


@dataclass
class FeatureSpec:
    name: str
    display_name: str
    description: str
    category: FeatureCategory
    handler: Callable
    params: List[ParamSpec]
    returns: str
    dsl_keyword: Optional[str] = None
    dsl_template: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    test_cases: List[TestCase] = field(default_factory=list)
    version: str = "1.0.0"
    deprecated: bool = False
    tags: List[str] = field(default_factory=list)

    # 自动生成的字段
    mcp_tool_name: str = ""
    cli_command: str = ""
    http_endpoint: str = ""

    def __post_init__(self):
        if not self.mcp_tool_name:
            self.mcp_tool_name = f"lobster_{self.name}"
        if not self.cli_command:
            self.cli_command = self.name.replace("_", "-")
        if not self.http_endpoint:
            self.http_endpoint = f"/api/feature/{self.name}"

    def to_mcp_schema(self) -> dict:
        properties = {}
        required = []
        for p in self.params:
            prop = {"type": p.type, "description": p.description}
            if p.example is not None:
                prop["examples"] = [p.example]
            if p.default is not None:
                prop["default"] = p.default
            properties[p.name] = prop
            if p.required:
                required.append(p.name)
        return {
            "name": self.mcp_tool_name,
            "description": f"{self.display_name}: {self.description}",
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def to_cli_help(self) -> str:
        lines = [f"  {self.cli_command} - {self.display_name}", f"    描述: {self.description}"]
        for p in self.params:
            req = "" if p.required else f" (默认: {p.default})"
            lines.append(f"    --{p.name} [{p.type}]{req}: {p.description}")
        if self.examples:
            lines.append(f"    示例: lobster call {self.name} {' '.join(f'{ list(p.name for p in self.params[:2])}...' if self.params else '')}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category.value,
            "params": [asdict(p) for p in self.params],
            "returns": self.returns,
            "dsl_keyword": self.dsl_keyword,
            "dsl_template": self.dsl_template,
            "examples": self.examples,
            "mcp_tool_name": self.mcp_tool_name,
            "cli_command": self.cli_command,
            "http_endpoint": self.http_endpoint,
            "version": self.version,
            "deprecated": self.deprecated,
            "tags": self.tags,
        }


class FeatureRegistry:
    _instance: Optional["FeatureRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._features: Dict[str, FeatureSpec] = {}
            cls._instance._load_order: List[str] = []
        return cls._instance

    def register(self, spec: FeatureSpec):
        if spec.name in self._features:
            raise ValueError(f"功能 '{spec.name}' 已注册")
        self._features[spec.name] = spec
        self._load_order.append(spec.name)
        return spec

    @property
    def plugins(self) -> List[dict]:
        """已加载的插件列表"""
        if not hasattr(self, "_plugins"):
            self._plugins = {}
        return [{"name": k, "path": str(v)} for k, v in self._plugins.items()]

    def load_plugin(self, plugin_path: str, namespace: str = "") -> dict:
        """
        从外部路径加载功能插件

        Args:
            plugin_path: .py 文件路径或包含 __init__.py 的目录路径
            namespace: 插件命名空间（可选，用于避免名称冲突）

        Returns:
            dict{success, features_loaded, error}
        """
        if not hasattr(self, "_plugins"):
            self._plugins = {}

        path = Path(plugin_path)
        if not path.exists():
            return {"success": False, "error": f"路径不存在: {plugin_path}"}

        # 计算模块名
        if path.is_file() and path.suffix == ".py":
            module_name = namespace or f"lobster_plugin_{path.stem}"
        elif path.is_dir():
            init_file = path / "__init__.py"
            if not init_file.exists():
                return {"success": False, "error": f"目录插件需要 __init__.py: {plugin_path}"}
            module_name = namespace or f"lobster_plugin_{path.name}"
            path = init_file
        else:
            return {"success": False, "error": f"不支持的插件路径: {plugin_path}"}

        if module_name in self._plugins:
            return {"success": False, "error": f"插件 '{module_name}' 已加载"}

        # 记录加载前的功能数
        before_count = len(self._features)

        try:
            # 动态导入
            spec = importlib.util.spec_from_file_location(module_name, str(path))
            if spec is None or spec.loader is None:
                return {"success": False, "error": f"无法加载模块: {module_name}"}
            mod = importlib.util.module_from_spec(spec)
            # 将模块加入 sys.modules 以便内部 import 正常工作
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)

            loaded = len(self._features) - before_count
            self._plugins[module_name] = str(path)

            return {
                "success": True,
                "features_loaded": loaded,
                "module": module_name,
            }
        except Exception as e:
            return {"success": False, "error": f"加载插件失败: {e}"}

    def unload_plugin(self, name_or_path: str) -> bool:
        """卸载一个已加载的插件"""
        if not hasattr(self, "_plugins"):
            return False

        # 按名称或路径查找
        module_name = None
        for m, p in list(self._plugins.items()):
            if m == name_or_path or str(p) == name_or_path:
                module_name = m
                break

        if not module_name:
            return False

        # 移除该模块注册的功能
        # 注意：功能没有标记属于哪个插件，这里只从 plugins 列表移除
        # 功能本身保留在 registry 中
        del self._plugins[module_name]
        if module_name in sys.modules:
            del sys.modules[module_name]
        return True

    def get(self, name: str) -> Optional[FeatureSpec]:
        return self._features.get(name)

    def all(self) -> List[FeatureSpec]:
        return [self._features[n] for n in self._load_order]

    def by_category(self, cat: FeatureCategory) -> List[FeatureSpec]:
        return [f for f in self.all() if f.category == cat and not f.deprecated]

    def by_dsl_keyword(self, keyword: str) -> Optional[FeatureSpec]:
        for f in self.all():
            if f.dsl_keyword and f.dsl_keyword.upper() == keyword.upper():
                return f
        return None

    def execute(self, feature_name: str, **kwargs) -> dict:
        """执行功能。第一个参数用 feature_name 避免和功能参数名冲突。"""
        spec = self.get(feature_name)
        if spec is None:
            return {"success": False, "error": f"未知功能: {feature_name}", "feature": feature_name}
        if spec.deprecated:
            return {"success": False, "error": f"功能 '{feature_name}' 已废弃", "feature": feature_name}

        start = time.time()
        try:
            for p in spec.params:
                if p.name not in kwargs and not p.required and p.default is not None:
                    kwargs[p.name] = p.default
            result = spec.handler(**kwargs)
            return {
                "success": True,
                "result": result,
                "feature": feature_name,
                "elapsed_ms": round((time.time() - start) * 1000, 1),
            }
        except TypeError as e:
            return {"success": False, "error": f"参数错误: {e}", "feature": feature_name}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "feature": feature_name,
                "elapsed_ms": round((time.time() - start) * 1000, 1),
            }

    def execute_with_typed_params(self, feature_name: str, **raw_kwargs) -> dict:
        """带类型转换的参数执行"""
        spec = self.get(feature_name)
        if not spec:
            return {"success": False, "error": f"未知功能: {feature_name}"}
        kwargs = {}
        for p in spec.params:
            if p.name in raw_kwargs:
                kwargs[p.name] = _convert_type(raw_kwargs[p.name], p.type)
            elif not p.required and p.default is not None:
                kwargs[p.name] = p.default
        return self.execute(feature_name, **kwargs)

    def export_mcp_tools(self) -> List[dict]:
        return [f.to_mcp_schema() for f in self.all() if not f.deprecated]

    def export_openapi(self) -> dict:
        paths = {}
        for spec in self.all():
            if spec.deprecated:
                continue
            body_props = {}
            required = []
            for p in spec.params:
                body_props[p.name] = {"type": p.type, "description": p.description}
                if p.required:
                    required.append(p.name)
            paths[spec.http_endpoint] = {
                "post": {
                    "summary": spec.display_name,
                    "description": spec.description,
                    "operationId": spec.name,
                    "tags": [spec.category.value],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"type": "object", "properties": body_props, "required": required}
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": spec.returns, "content": {"application/json": {"schema": {"type": "object"}}}}
                    },
                }
            }
        return {"openapi": "3.0.0", "info": {"title": "Lobster API", "version": "2.0.0"}, "paths": paths}

    def export_claude_context(self) -> str:
        lines = [
            "# Lobster 功能注册表",
            f"# 共 {len(self._features)} 个功能",
            f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        for cat in FeatureCategory:
            features = self.by_category(cat)
            if not features:
                continue
            lines.append(f"\n## {cat.value.upper()}: {CAT_NAMES.get(cat, cat.value)}")
            for f in features:
                lines.append(f"- **{f.name}** → MCP: `{f.mcp_tool_name}`")
                lines.append(f"  - {f.description}")
                if f.dsl_template:
                    lines.append(f"  - DSL: `{f.dsl_template}`")
                lines.append(f"  - 参数: {', '.join(f'{p.name}:{p.type}' for p in f.params)}")
        lines.extend([
            "",
            "## 如何新增功能",
            "1. 在 python/features/ 目录创建 .py 文件",
            "2. 使用 @feature() 装饰器声明功能",
            "3. 在 server.py 顶部 import 该文件",
            "MCP / CLI / HTTP API 全部自动同步。",
        ])
        return "\n".join(lines)

    def export_dsl_reference(self) -> str:
        lines = ["# Lobster DSL 语法参考\n"]
        for f in self.all():
            if not f.dsl_keyword:
                continue
            lines.append(f"## {f.dsl_keyword}")
            lines.append(f"{f.display_name} - {f.description}\n")
            lines.append(f"语法: `{f.dsl_template}`\n")
            for p in f.params:
                lines.append(f"- `{p.name}` ({p.type}): {p.description}")
            if f.examples:
                lines.append("\n示例:")
                for ex in f.examples:
                    lines.append(f"  `{ex}`")
            lines.append("")
        lines += [
            "## 控制流（内置，不通过注册表）",
            "- `LOOP <标签>` / `END` — 循环",
            "- `IF <条件>` / `ELSE` / `END` — 条件判断",
            "- `WAIT <条件>` — 等待: 文字:X / 图像:X / 稳定 / 变化 / 消失:X",
        ]
        return "\n".join(lines)

    def run_tests(self, category: Optional[FeatureCategory] = None, skip_ci: bool = True) -> dict:
        features = self.by_category(category) if category else self.all()
        results = {"passed": 0, "failed": 0, "skipped": 0, "details": []}
        for spec in features:
            for tc in spec.test_cases:
                if skip_ci and tc.skip_in_ci:
                    results["skipped"] += 1
                    results["details"].append({"feature": spec.name, "test": tc.name, "status": "skipped"})
                    continue
                result = self.execute(spec.name, **tc.params)
                passed = False
                if tc.expected_type == "success":
                    passed = result.get("success", False)
                elif tc.expected_type == "non_null":
                    passed = result.get("success") and result.get("result") is not None
                elif tc.expected_type == "bool_true":
                    passed = result.get("success") and result.get("result") is True
                elif tc.expected_type == "custom" and tc.validator:
                    try:
                        passed = tc.validator(result)
                    except Exception:
                        passed = False
                results["details"].append({
                    "feature": spec.name, "test": tc.name,
                    "status": "passed" if passed else "failed",
                    "result": result,
                })
                if passed:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
        return results


CAT_NAMES = {
    FeatureCategory.ACTION: "交互动作",
    FeatureCategory.PERCEPTION: "感知识别",
    FeatureCategory.CONTROL: "控制流",
    FeatureCategory.MACRO: "宏指令",
    FeatureCategory.AI: "AI规划",
    FeatureCategory.SYSTEM: "系统功能",
    FeatureCategory.DEBUG: "调试诊断",
}

registry = FeatureRegistry()


def feature(name, display_name, description, category, params, returns,
            dsl_keyword=None, dsl_template=None, examples=None,
            test_cases=None, tags=None, version="1.0.0"):
    """功能注册装饰器"""
    def decorator(fn):
        spec = FeatureSpec(
            name=name, display_name=display_name, description=description,
            category=category, handler=fn, params=params, returns=returns,
            dsl_keyword=dsl_keyword, dsl_template=dsl_template,
            examples=examples or [], test_cases=test_cases or [],
            tags=tags or [], version=version,
        )
        registry.register(spec)
        fn._lobster_spec = spec
        return fn
    return decorator


def _convert_type(value: str, target_type: str):
    """将字符串参数转换为目标类型"""
    if target_type in ("number", "float"):
        return float(value)
    if target_type == "int":
        return int(value)
    if target_type == "boolean":
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")
    return value  # str


P = ParamSpec
TC = TestCase
F = FeatureCategory
