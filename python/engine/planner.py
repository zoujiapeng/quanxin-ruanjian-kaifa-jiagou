"""
AI 规划引擎: 内部 Agent 闭环
自然语言目标 → 自主分解 → 选工具 → 执行 → 反馈 → 调整
"""
from __future__ import annotations
import json
import os
import time
import base64
import uuid
from typing import Any, Optional
from dataclasses import dataclass, field

from engine.store import get_store, Checkpoint


@dataclass
class PlanStep:
    action: str
    params: dict
    result: Any = None
    error: str = ""
    elapsed_ms: float = 0.0
    observation: str = ""


class Planner:
    """
    自主规划执行引擎

    流程:
      1. observe — 截图 + OCR 获取当前状态
      2. think — LLM 分析目标 + 状态 → 选择下一步动作
      3. act — 调用 registry 执行
      4. evaluate — 检查目标是否达成
      5. loop — 未达成则回到 1

    免 token 关键路径:
      Claude Code 下发一个自然语言意图,
      Planner 自主完成观察→规划→执行→验证闭环,
      中间 LLM 调用消耗的是本地配置的 API key, 不是 Claude Code 的 token
    """

    def __init__(self, api_key: str = ""):
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._registry = None
        self._steps: list[PlanStep] = []
        self._max_iterations = 10
        self._client = None
        self._task_id = ""

    def _ensure_client(self):
        if self._client is None and self._api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self._api_key)
            except Exception:
                pass

    def set_registry(self, registry):
        """设置功能注册表引用"""
        self._registry = registry

    # ── 主入口 ──────────────────────────────────────────────────

    def plan_and_execute(self, goal: str, context: Optional[dict] = None,
                         max_iterations: int = 10) -> dict:
        """
        接收自然语言目标，自主完成规划-执行-反馈闭环

        Args:
            goal: 自然语言目标，如 "打开微信给张三发消息"
            context: 额外上下文信息
            max_iterations: 最大规划迭代次数

        Returns:
            dict{success, steps, result, error}
        """
        self._steps = []
        self._max_iterations = max_iterations
        self._ensure_client()
        self._task_id = uuid.uuid4().hex[:12]

        if not self._client:
            return {
                "success": False,
                "error": "未配置 API Key，无法启动 AI 规划",
                "steps": [],
            }

        state = {
            "goal": goal,
            "context": context or {},
            "previous_steps": [],
            "last_observation": "",
        }

        for iteration in range(1, max_iterations + 1):
            # 1. 观察
            observation = self._observe()
            state["last_observation"] = observation

            # 2. 思考 → 决策
            plan = self._think(state)
            if not plan:
                break

            if plan.get("done"):
                self._save_checkpoint(iteration, state, "completed")
                return self._result(success=True, message=plan.get("reason", "目标完成"))

            # 3. 执行
            step_result = self._act(plan)

            # 4. 记录
            step = PlanStep(
                action=plan.get("action", "unknown"),
                params=plan.get("params", {}),
                result=step_result.get("result"),
                error=step_result.get("error", ""),
                elapsed_ms=step_result.get("elapsed_ms", 0),
                observation=observation[:200],
            )
            self._steps.append(step)
            state["previous_steps"].append({
                "action": step.action,
                "params": step.params,
                "success": not step.error,
                "result": str(step.result)[:200] if step.result else None,
            })

            # 保存 checkpoint
            self._save_checkpoint(iteration, state, "running")

            # 5. 检查致命错误
            if step_result.get("error") and "无法恢复" in str(step_result.get("error", "")):
                self._save_checkpoint(iteration, state, "error")
                return self._result(success=False, error=step_result["error"])

        self._save_checkpoint(max_iterations, state, "finished")
        return self._result(
            success=False,
            error=f"超过最大迭代次数 ({max_iterations})",
        )

    # ── 持久化 ────────────────────────────────────────────────────

    def _save_checkpoint(self, iteration: int, state: dict, status: str):
        """保存当前规划状态到 store"""
        try:
            store = get_store()
            cp = Checkpoint(
                task_id=self._task_id,
                dsl=f"planner:{state.get('goal', '')[:100]}",
                state=status,
                completed_indices=list(range(len(self._steps))),
                variables={
                    "goal": state.get("goal", ""),
                    "context": state.get("context", {}),
                    "iteration": iteration,
                    "steps": [
                        {"action": s.action, "params": s.params,
                         "error": s.error, "elapsed_ms": s.elapsed_ms}
                        for s in self._steps
                    ],
                    "last_observation": state.get("last_observation", ""),
                },
                scope_count=1,
                node_info=f"planner iteration {iteration}/{self._max_iterations}",
            )
            store.save_checkpoint(cp)
        except Exception as e:
            pass  # checkpoint 失败不阻塞主流程

    def restore_session(self, task_id: str) -> Optional[dict]:
        """从 store 恢复之前中断的规划 session

        Args:
            task_id: checkpoint 的 task_id

        Returns:
            dict{goal, steps, iteration, last_observation} 或 None
        """
        try:
            store = get_store()
            cp = store.get_checkpoint(task_id)
            if cp is None:
                return None
            self._task_id = task_id
            variables = cp.variables
            self._steps = [
                PlanStep(action=s["action"], params=s["params"],
                         error=s.get("error", ""), elapsed_ms=s.get("elapsed_ms", 0))
                for s in variables.get("steps", [])
            ]
            return {
                "goal": variables.get("goal", ""),
                "context": variables.get("context", {}),
                "steps": variables.get("steps", []),
                "iteration": variables.get("iteration", 0),
                "last_observation": variables.get("last_observation", ""),
                "task_id": task_id,
                "state": cp.state,
            }
        except Exception as e:
            return None

    # ── 内部步骤 ────────────────────────────────────────────────

    def _observe(self) -> str:
        """获取当前状态描述（截图 + OCR 文本）"""
        texts = []
        try:
            from perception.ocr import OCREngine
            engine = OCREngine()
            results = engine.extract_all()
            if results:
                texts = [r.text for r in results[:20]]
        except Exception:
            pass

        try:
            from perception.vision import ScreenCapture
            import cv2
            img = ScreenCapture.capture()
            h, w = img.shape[:2]
            resolution = f"{w}x{h}"
        except Exception:
            resolution = "unknown"

        obs = f"屏幕分辨率: {resolution}\n"
        if texts:
            obs += f"当前可见文字: {', '.join(texts)}\n"
        obs += f"已执行 {len(self._steps)} 步"
        return obs

    def _think(self, state: dict) -> Optional[dict]:
        """LLM 分析并决策下一步"""
        tools_desc = self._build_tools_prompt()
        steps_summary = "\n".join(
            f"  {i+1}. {s['action']}({s['params']}) → "
            f"{'成功' if s['success'] else '失败: ' + str(s.get('result', ''))}"
            for i, s in enumerate(state["previous_steps"])
        ) or "  尚未执行任何步骤"

        prompt = f"""你是 Lobster 自动化系统的 AI 规划引擎。
目标: {state['goal']}

可用工具:
{tools_desc}

已执行步骤:
{steps_summary}

当前观察:
{state['last_observation']}

请决定下一步操作。以 JSON 格式回复，不要加 markdown 代码块。

如果目标已完成，回复:
{{"done": true, "reason": "目标完成的理由"}}

否则，回复执行下一步:
{{"action": "工具名", "params": {{"参数1": "值1", ...}}, "rationale": "为什么选这个"}}

参数值使用 {{变量名}} 引用之前步骤的输出（如果有需要）。
"""

        try:
            msg = self._client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=512,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text.strip()
            # 提取 JSON
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                text = text.rsplit("```", 1)[0] if "```" in text else text
            plan = json.loads(text)
            return plan
        except Exception as e:
            # 解析失败时尝试简单重试
            return {"action": "screenshot", "params": {}, "rationale": f"规划解析失败: {e}，尝试观察"}

    def _act(self, plan: dict) -> dict:
        """执行规划的动作"""
        action = plan.get("action", "")
        params = plan.get("params", {})

        if action == "screenshot":
            # 内置动作：截图观察
            try:
                from features.perception_features import screenshot
                result = screenshot()
                return {"success": True, "result": f"截图完成 ({result.get('width')}x{result.get('height')})"}
            except Exception as e:
                return {"error": str(e)}

        if not self._registry:
            return {"error": "规划器未绑定 registry"}

        start = time.time()
        try:
            result = self._registry.execute_with_typed_params(action, **params)
            elapsed_ms = round((time.time() - start) * 1000, 1)
            if result.get("success"):
                return {"success": True, "result": result.get("result"), "elapsed_ms": elapsed_ms}
            return {"error": result.get("error", "未知错误"), "elapsed_ms": elapsed_ms}
        except Exception as e:
            elapsed_ms = round((time.time() - start) * 1000, 1)
            return {"error": str(e), "elapsed_ms": elapsed_ms}

    # ── 辅助 ────────────────────────────────────────────────────

    def _build_tools_prompt(self) -> str:
        """从 registry 生成工具描述"""
        if not self._registry:
            return "(无可用工具)"
        lines = []
        for spec in self._registry.all():
            if spec.deprecated or "待完善" in spec.tags:
                continue
            params_desc = ", ".join(
                f"{p.name}({p.type})" for p in spec.params
            )
            lines.append(f"  {spec.name}({params_desc}) — {spec.description[:100]}")
        return "\n".join(lines[:50])  # 限制工具数量避免超 token

    def _result(self, success: bool, message: str = "", error: str = "") -> dict:
        return {
            "success": success,
            "message": message,
            "error": error,
            "steps_count": len(self._steps),
            "steps": [
                {
                    "action": s.action,
                    "params": s.params,
                    "error": s.error,
                    "elapsed_ms": s.elapsed_ms,
                }
                for s in self._steps
            ],
        }

    def get_history(self) -> list[dict]:
        return [
            {
                "action": s.action,
                "params": s.params,
                "error": s.error,
                "elapsed_ms": s.elapsed_ms,
            }
            for s in self._steps
        ]


# 全局工厂
_planner_instance: Optional[Planner] = None


def get_planner(api_key: str = "") -> Planner:
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = Planner(api_key=api_key)
    return _planner_instance
