from OmniFlowCentral.mcp_app.server import mcp


def test_mcp_tools_expose_read_only_annotations():
    tools = {tool.name: tool for tool in mcp._tool_manager.list_tools()}
    expected = {
        "query_dataset",
        "dataset_search",
        "saos_search",
        "saos_detail",
        "search",
        "fetch",
        "migration_matrix",
    }
    assert set(tools.keys()) == expected

    for name, tool in tools.items():
        annotations = tool.annotations
        assert annotations is not None, f"{name} must define tool annotations"
        assert annotations.readOnlyHint is True, f"{name} should be marked read-only"
        assert annotations.destructiveHint is False, f"{name} should not be destructive"
        assert annotations.openWorldHint is False, f"{name} should not use open-world side effects"
        assert annotations.idempotentHint is True, f"{name} should be idempotent"
        assert isinstance(tool.description, str) and tool.description.strip(), f"{name} should have a description"
