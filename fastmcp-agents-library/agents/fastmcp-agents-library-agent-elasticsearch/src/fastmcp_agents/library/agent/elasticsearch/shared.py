import os

from fastmcp.mcp_config import TransformingStdioMCPServer
from fastmcp.tools.tool_transform import ToolTransformConfig

from fastmcp_agents.library.mcp.strawgate.knowledge_base_mcp import (
    SeedKnowledgeBaseRequest,
    seed_knowledge_base,
)

base_elasticsearch_mcp = TransformingStdioMCPServer(
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

esql_instructions = """
When you are asked to perform a task that requires you to perform an ESQL query.

You have access to a knowledge base to answer questions. This knowledge base has two types of information in information:
1. ES|QL Query Syntax and tips
2. The Elastic Commmon Schema, a set of common fields (not exhaustive)

Do not specify a Knowledge base when running queries, then they will run against all KBs

You should leverage the knowledge base to determine what functionality of ESQL is relevant for the task and what fields to recommend
to the user to resolve the task.

```
# What's ES|QL?

It's not SQL. ESQL is a query language for Elasticsearch. It is a powerful tool for querying and analyzing data in Elasticsearch.

You can author ES|QL queries to find specific events, perform statistical analysis, and create visualizations.
It supports a wide range of commands, functions, and operators to perform various data operations, such as filter,
aggregation, time-series analysis, and more. It initially supported a subset of the features available in Query DSL,
but it is rapidly evolving with every Elastic Cloud Serverless and Stack release.

ES|QL is designed to be easy to read and write, making it accessible for users with varying levels of technical expertise.
It is particularly useful for data analysts, security professionals, and developers who need to work with large datasets in Elasticsearch.

How does it work?
ES|QL uses pipes (|) to manipulate and transform data in a step-by-step fashion. This approach allows you to compose a series
of operations, where the output of one operation becomes the input for the next, enabling complex data transformations and analysis.

Here's a simple example of an ES|QL query:

FROM sample_data
| SORT @timestamp DESC
| LIMIT 3
Note that each line in the query represents a step in the data processing pipeline:

The FROM clause specifies the index or data stream to query
The SORT clause sorts the data by the @timestamp field in descending order
The LIMIT clause restricts the output to the top 3 results
```

When calculating metrics, bucketing by time requires careful consideration of the query. here's an example of how to bucket by week:

```esql
FROM employees
| STATS COUNT(*) BY BUCKET(hire_date, 1 week)
```

You can also assign friendly names to these stats and buckets:
```esql
FROM employees
| STATS hires_per_week = COUNT(*) BY week = BUCKET(hire_date, 1 week)
| SORT week
```

You will always verify that every command you use is valid and has a supporting piece of documentation from the knowledge base.
If you cannot find a piece of documentation for the command, that means it is not a valid command so do not use it. If you cannot
solve the task with commands that exist, you will report failure for the task.

When building a query it's helpful to build the query in stages, adding one command at a time and testing it.

If there are parts that are variable (like a threshold, or a date range, source index, etc) that the user will need to provide,
you should indicate as such in your response.

Things to avoid:
- Targeting `metrics-*` or `logs-*` indices. Use more specific targets.
- Add a limit to your queries: `| limit 100`
- When querying with ES|QL if a field you're targeting doesn't actually exist in a mapping it will error. You must
    only target fields that exist when running ES|QL queries.
- You cannot use `AS` to name fields, the syntax is `field_name = expression`
"""

knowledge_base_instructions = """
You have access to a knowledge base to answer questions. This knowledge base has two types of information in information:
1. ES|QL Query Syntax and tips
2. The Elastic Common Schema, a set of common fields (not exhaustive)

When searching the Knowledge Base you should almost never perform only one query. You should perform several queries!
1. Start with high-level questions about the problem and task, for example what kind of query and what types of fields might
be relevant to the task.
2. Narrow down to more specific questions, for example more specific information on a specific ES|QL command or field.

You should never answer a user question without having first queried the knowledge base. If you cannot query the knowledge
base you will report failure for the task.
"""


formatting_instructions = """
Provide answers in Markdown and explain each part of the query with links to documentation for that part of the query.
"""

elasticsearch_mcp = base_elasticsearch_mcp.model_copy()
elasticsearch_mcp.tools = {
    "esql_query": ToolTransformConfig(
        tags={"esql"},
    ),
    "summarize_data_streams": ToolTransformConfig(
        tags={"data_streams"},
    ),
    "indices_data_streams_stats": ToolTransformConfig(
        name="get_data_streams",
        tags={"data_streams"},
    ),
}
elasticsearch_mcp.include_tags = {"esql", "data_streams"}


async def prepare_knowledge_base(knowledge_base_mcp: TransformingStdioMCPServer) -> None:
    await seed_knowledge_base(
        kb_mcp=knowledge_base_mcp,
        knowledge_base_requests=[
            SeedKnowledgeBaseRequest(
                knowledge_base="ESQL", seed_urls=["https://www.elastic.co/docs/reference/query-languages/esql/"], overwrite=True
            ),
            SeedKnowledgeBaseRequest(
                knowledge_base="Elastic Common Schema", seed_urls=["https://www.elastic.co/docs/reference/ecs/"], overwrite=True
            ),
        ],
    )
