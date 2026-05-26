# NebulaKB Tool Harness

## 定位

NebulaKB 的 Tool Harness 是轻量工具执行治理层，只覆盖工具、连接器和工作流工具节点的执行边界。

它不负责通用 Agent 编排，也不提供工程执行沙箱。权限、工作空间、工具授权和审计入口继续复用 NebulaKB 已有体系；Harness 只把执行前检查、参数脱敏、耗时、结果和错误记录成统一 observation。

## 第一版动作

- `tool.test_connection`
- `tool.execute`
- `tool.import`
- `tool.export`
- `workflow.tool_node.execute`

## 包结构

代码位于 `apps/tools/harness/`：

- `action.py`：定义 Harness action 名称。
- `policy.py`：复用现有 `PermissionConstants`、`RoleConstants` 和工具工作空间归属检查。
- `sanitizer.py`：递归脱敏敏感参数。
- `observation.py`：标准化 action、状态、耗时、输入、输出和错误。
- `service.py`：执行 callable，并把 observation 写入现有 `ToolRecord`。

## 记录格式

Harness 不新建审计表。工具执行仍写入 `tool_record`，并保留原有 `meta.input`、`meta.output` 字段，避免破坏现有 Tool Record API 和 UI。

`meta.harness` 保存标准化执行信息：

```json
{
  "input": {
    "api_key": "********",
    "query": "hello"
  },
  "output": {
    "answer": "ok"
  },
  "harness": {
    "action": "tool.execute",
    "status": "success",
    "started_at": "2026-05-26T00:00:00+00:00",
    "ended_at": "2026-05-26T00:00:01+00:00",
    "duration_ms": 1000,
    "error": null
  }
}
```

失败时 `ToolRecord.state` 写为 `FAILURE`，`meta.err_message` 和 `meta.harness.error` 保存错误原因。Harness 记录错误后继续抛出异常，交给工作流已有异常分支和 UI 状态处理。

## 接入点

- MCP 工具连接测试通过 `ToolHarnessService.test_connection()` 返回 observation。
- 工作流 `tool-node` 通过 `execute_workflow_tool_node()` 生成内联 observation，供节点详情展示。
- 工作流 `tool-lib-node` 通过 `execute_tool()` 写入现有 `ToolRecord`，并修正失败时吞异常的问题。

## 边界

Harness 不做：

- 新 RBAC 或独立权限表。
- 新审计/事件表。
- Docker、Firecracker、Kubernetes 等执行沙箱。
- Agent 计划、记忆、反思、任务拆解或自动修复循环。

这些能力如果需要，应放在更完整的 Agent/工程执行平台，而不是 NebulaKB 的轻量工具治理层。
