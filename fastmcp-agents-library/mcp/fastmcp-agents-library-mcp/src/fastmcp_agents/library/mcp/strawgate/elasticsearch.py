import os

from fastmcp.mcp_config import TransformingStdioMCPServer


def elasticsearch_mcp() -> TransformingStdioMCPServer:
    return TransformingStdioMCPServer(
        command="uvx",
        env={
            "ES_HOST": os.getenv("ES_HOST"),
            "ES_API_KEY": os.getenv("ES_API_KEY"),
        },
        args=[
            "strawgate-es-mcp",
        ],
        tools={},
    )


# READ_ONLY_ELASTICSEARCH_TOOLS = {
#     "indices_data_streams_stats",
#     "summarize_data_stream",
#     "indices_stats",
#     "indices_mapping",
#     "indices_settings",
#     "indices_aliases",
#     "indices_templates",
#     "indices_get",
# }

# def read_only_elasticsearch_mcp() -> TransformingStdioMCPServer:
#     return TransformingStdioMCPServer(
#         command="uvx",
#         env={
#             "ES_HOST": os.getenv("ES_HOST"),
#             "ES_API_KEY": os.getenv("ES_API_KEY"),
#         },
#         args=[
#             "strawgate-es-mcp",
#         ],
#         tools={},
#     )
