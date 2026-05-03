"""
DSL Parser: 将 Lobster DSL 文本解析为 AST
支持: CLICK, WAIT, LOOP, IF, END, RUN
       SUBROUTINE, CALL, IMPORT, RETURN
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional
from enum import Enum


class NodeType(str, Enum):
    CLICK = "CLICK"
    WAIT = "WAIT"
    LOOP = "LOOP"
    IF = "IF"
    END = "END"
    RUN = "RUN"
    SEQUENCE = "SEQUENCE"
    SUBROUTINE = "SUBROUTINE"
    CALL = "CALL"
    IMPORT = "IMPORT"
    RETURN = "RETURN"
    WHEN = "WHEN"
    PARALLEL = "PARALLEL"
    WITH = "WITH"


@dataclass
class ASTNode:
    type: NodeType
    args: str = ""
    children: List[ASTNode] = field(default_factory=list)
    else_children: List[ASTNode] = field(default_factory=list)
    line: int = 0
    params: List[str] = field(default_factory=list)      # SUBROUTINE param names
    call_args: List[str] = field(default_factory=list)    # CALL arg expressions
    event_key: str = ""                                   # WHEN trigger type
    config: str = ""                                      # WHEN config string

    def to_dict(self) -> dict:
        d = {
            "type": self.type.value,
            "args": self.args,
            "line": self.line,
            "children": [c.to_dict() for c in self.children],
            "else_children": [c.to_dict() for c in self.else_children],
        }
        if self.params:
            d["params"] = self.params
        if self.call_args:
            d["call_args"] = self.call_args
        if self.event_key:
            d["event_key"] = self.event_key
            d["config"] = self.args
        return d


class DSLParseError(Exception):
    def __init__(self, msg: str, line: int = 0):
        super().__init__(f"[Line {line}] {msg}")
        self.line = line


class DSLParser:
    """
    Lobster DSL 解析器
    语法规则:
      CLICK <target>
      WAIT <condition>
      LOOP [label] ... END
      IF <condition> ... [ELSE ...] END
      RUN <macro_name>
      SUBROUTINE name(param1, param2) ... END
      CALL name(arg1, arg2)
      IMPORT "<path>"
      RETURN [value]
    """

    KEYWORDS = {"CLICK", "WAIT", "LOOP", "IF", "ELSE", "END", "RUN",
                "SUBROUTINE", "CALL", "IMPORT", "RETURN", "WHEN",
                "PARALLEL", "WITH"}

    def __init__(self):
        self._tokens: List[tuple[int, str, str]] = []
        self._pos = 0
        self.subroutines: dict[str, ASTNode] = {}

    def parse(self, source: str) -> ASTNode:
        self._tokens = self._tokenize(source)
        self._pos = 0
        self.subroutines = {}
        root = ASTNode(type=NodeType.SEQUENCE, args="root")
        root.children = self._parse_block(end_triggers=set())
        return root

    # ── tokenizer ────────────────────────────────────────────────
    def _tokenize(self, source: str) -> List[tuple[int, str, str]]:
        tokens = []
        for lineno, raw in enumerate(source.splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^([A-Z_]+)\s*(.*)", line)
            if not m:
                raise DSLParseError(f"无法识别的语法: '{line}'", lineno)
            keyword, args = m.group(1), m.group(2).strip()
            if keyword not in self.KEYWORDS:
                raise DSLParseError(f"未知指令: '{keyword}'", lineno)
            tokens.append((lineno, keyword, args))
        return tokens

    # ── recursive descent parser ──────────────────────────────────
    def _peek(self) -> Optional[tuple[int, str, str]]:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _consume(self) -> tuple[int, str, str]:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _parse_block(self, end_triggers: set) -> List[ASTNode]:
        """解析节点块直到遇到 end_triggers、END、ELSE 或 WITH"""
        nodes: List[ASTNode] = []
        while self._pos < len(self._tokens):
            tok = self._peek()
            if tok is None:
                break
            lineno, keyword, args = tok
            if keyword in end_triggers or keyword == "END":
                break
            if keyword == "ELSE":
                break
            if keyword == "WITH":
                break
            self._consume()

            if keyword == "CLICK":
                nodes.append(ASTNode(NodeType.CLICK, args, line=lineno))

            elif keyword == "WAIT":
                nodes.append(ASTNode(NodeType.WAIT, args, line=lineno))

            elif keyword == "RUN":
                nodes.append(ASTNode(NodeType.RUN, args, line=lineno))

            elif keyword == "LOOP":
                node = ASTNode(NodeType.LOOP, args, line=lineno)
                node.children = self._parse_block({"END"})
                self._expect("END", lineno)
                nodes.append(node)

            elif keyword == "IF":
                node = ASTNode(NodeType.IF, args, line=lineno)
                node.children = self._parse_block({"END", "ELSE"})
                nxt = self._peek()
                if nxt and nxt[1] == "ELSE":
                    self._consume()
                    node.else_children = self._parse_block({"END"})
                self._expect("END", lineno)
                nodes.append(node)

            elif keyword == "SUBROUTINE":
                name, params = self._parse_sub_header(args, lineno)
                if name in self.subroutines:
                    raise DSLParseError(f"子程序 '{name}' 重复定义", lineno)
                node = ASTNode(NodeType.SUBROUTINE, name, line=lineno)
                node.params = params
                node.children = self._parse_block({"END"})
                self._expect("END", lineno)
                self.subroutines[name] = node
                nodes.append(node)

            elif keyword == "CALL":
                name, call_args = self._parse_call_expr(args, lineno)
                node = ASTNode(NodeType.CALL, name, line=lineno)
                node.call_args = call_args
                nodes.append(node)

            elif keyword == "IMPORT":
                path = args.strip().strip('"').strip("'")
                if not path:
                    raise DSLParseError("IMPORT 需要文件路径", lineno)
                nodes.append(ASTNode(NodeType.IMPORT, path, line=lineno))

            elif keyword == "RETURN":
                nodes.append(ASTNode(NodeType.RETURN, args.strip(), line=lineno))

            elif keyword == "WHEN":
                event_key, config_str = self._parse_when_header(args, lineno)
                node = ASTNode(NodeType.WHEN, config_str, line=lineno)
                node.event_key = event_key
                node.children = self._parse_block({"END"})
                self._expect("END", lineno)
                nodes.append(node)

            elif keyword == "PARALLEL":
                node = ASTNode(NodeType.PARALLEL, args, line=lineno)
                # 第一个分支
                branch = self._parse_block({"END", "WITH"})
                node.children.append(ASTNode(NodeType.SEQUENCE, "branch_0", line=lineno, children=branch))
                # 后续 WITH 分支
                while self._peek() and self._peek()[1] == "WITH":
                    self._consume()
                    branch = self._parse_block({"END", "WITH"})
                    idx = len(node.children)
                    node.children.append(ASTNode(NodeType.SEQUENCE, f"branch_{idx}", line=lineno, children=branch))
                self._expect("END", lineno)
                nodes.append(node)

        return nodes

    def _expect(self, keyword: str, ref_line: int):
        tok = self._peek()
        if tok is None or tok[1] != keyword:
            got = tok[1] if tok else "EOF"
            raise DSLParseError(
                f"期望 '{keyword}'，但得到 '{got}'（从第{ref_line}行的块开始）",
                ref_line,
            )
        self._consume()

    def _parse_when_header(self, text: str, lineno: int):
        """WHEN FILE_CREATED "config" → ('FILE_CREATED', 'config')"""
        parts = text.strip().split(None, 1)
        if not parts:
            raise DSLParseError("WHEN 需要事件类型，如: WHEN FILE_CREATED path", lineno)
        event_key = parts[0]
        config_str = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else ""
        return event_key, config_str

    # ── sub / call helpers ───────────────────────────────────────
    def _parse_sub_header(self, text: str, lineno: int):
        """SUBROUTINE name(param1, param2) → ('name', ['param1', 'param2'])"""
        m = re.match(r"^(\w+)\s*\((.*)\)\s*$", text)
        if not m:
            raise DSLParseError(f"子程序格式错误: '{text}'，应为 name(param1, param2)", lineno)
        name = m.group(1)
        raw = m.group(2).strip()
        params = [p.strip() for p in raw.split(",") if p.strip()] if raw else []
        return name, params

    def _parse_call_expr(self, text: str, lineno: int):
        """CALL name(arg1, arg2) → ('name', ['arg1', 'arg2'])"""
        m = re.match(r"^(\w+)\s*\((.*)\)\s*$", text)
        if not m:
            raise DSLParseError(f"CALL 格式错误: '{text}'，应为 name(arg1, arg2)", lineno)
        name = m.group(1)
        raw = m.group(2).strip()
        args = [a.strip().strip("\"'") for a in raw.split(",") if a.strip()] if raw else []
        return name, args

    # ── utility ───────────────────────────────────────────────────
    @staticmethod
    def from_string(source: str) -> ASTNode:
        return DSLParser().parse(source)


# ── 快速测试 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    sample = """
SUBROUTINE login(user, pass)
  CLICK 用户名
  TYPE {user}
  CLICK 密码
  TYPE {pass}
  CLICK 登录
  WAIT 加载完成
END

CLICK 启动应用
WAIT 初始化
CALL login("admin", "123456")
CLICK 开始使用
"""
    ast = DSLParser.from_string(sample)
    print(json.dumps(ast.to_dict(), ensure_ascii=False, indent=2))
