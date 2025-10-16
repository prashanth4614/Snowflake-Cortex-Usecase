# Architecture & Design Decisions

## Overview

This project demonstrates two approaches to building intelligent agents with Snowflake Cortex:

1. **Pre-configured Agent** (Production) - `Streamlit_agent.py`
2. **Client-side Orchestration** (Proof of Concept) - `Streamlit.py`

## Key Finding: Multi-Tool Orchestration

### Discovery

Through extensive testing, we discovered a **critical architectural difference** between Snowflake's two agent approaches:

| Approach | Endpoint | Multi-Tool Support | Use Case |
|----------|----------|-------------------|----------|
| **Pre-configured Agent** | `/api/v2/databases/{db}/schemas/{schema}/agents/{name}:run` | ✅ **Automatic** | Production applications |
| **Ad-hoc Agent** | `/api/v2/cortex/agent:run` | ⚠️ **Manual Required** | Quick prototyping |

### Why Pre-configured Agents Handle Compound Queries Better

#### 1. **Persistent Configuration**
- Agent object stored in Snowflake with tools, instructions, and orchestration logic
- No need to pass tool definitions in each request
- Configuration managed centrally via SQL or Snowsight UI

#### 2. **Advanced LLM-based Orchestration**
Pre-configured agents implement a sophisticated 4-phase workflow:

```
┌─────────────┐
│  Planning   │ → Parse query, split into sub-tasks
└──────┬──────┘
       │
┌──────▼──────┐
│  Tool Use   │ → Select and execute appropriate tools
└──────┬──────┘
       │
┌──────▼──────┐
│ Reflection  │ → Evaluate results, iterate if needed
└──────┬──────┘
       │
┌──────▼──────┐
│   Response  │ → Generate final answer with citations
└─────────────┘
```

**Example:** Query: "What are the top 3 distributors and what's the refund policy?"

The agent automatically:
1. **Splits** into two sub-tasks
2. **Routes** SQL query to Cortex Analyst (structured data)
3. **Routes** policy question to Cortex Search (unstructured data)
4. **Combines** results into coherent response

#### 3. **Thread Support**
- Server-side conversation context management
- No need to send full history in each request
- Reduces payload size and improves performance

```python
# Create thread once
thread_id = create_thread()

# Reference in subsequent calls
response = agent_call(query, thread_id=thread_id, parent_message_id=last_msg_id)
```

#### 4. **Enterprise Features**
- Access control via RBAC
- Audit logging and monitoring
- Performance metrics and tracing
- Feedback collection

### Ad-hoc Agent Limitations

The ad-hoc agent (`/api/v2/cortex/agent:run`) was designed for:
- **Quick experimentation** without creating database objects
- **Single-tool scenarios** or simple workflows
- **Prototyping** before productionizing

**Limitations for compound queries:**
- Tools defined per-request (verbose payload)
- Simpler orchestration model
- No persistent state between requests
- Limited reflection and iteration

## Implementation Journey

### Phase 1: Initial Challenge
**Problem:** Ad-hoc agent wouldn't call multiple tools for compound queries

Example query: *"What are the top 3 distributors and what's the refund policy?"*

**Observed behavior:**
- LLM selected only ONE tool (either Analyst OR Search)
- Never combined results from both tools
- Tried various `tool_choice` parameters without success

### Phase 2: Client-side Orchestration (`Streamlit.py`)
**Solution:** Implement manual orchestration in application code

```python
# Split query using LLM
split_response = split_query(user_query)

# Call each tool separately
analyst_result = call_analyst(sql_query)
search_result = call_search(search_query)

# Combine results
final_response = combine_results(analyst_result, search_result)
```

**Result:** ✅ Works 100% reliably but requires manual orchestration logic

**Pros:**
- Full control over tool routing
- Predictable behavior
- Explicit error handling per tool

**Cons:**
- More complex application code
- Must maintain orchestration logic
- LLM calls for splitting and combining
- Higher latency (multiple API calls)

### Phase 3: Pre-configured Agent (`Streamlit_agent.py`)
**Discovery:** Pre-configured agents handle multi-tool orchestration automatically!

```python
# Create agent in Snowflake (one-time setup)
CREATE AGENT CORTEX_SALES_AGENT
WITH TOOLS (
    CORTEX_ANALYST_SEMANTIC_VIEW,
    CORTEX_SEARCH_SERVICE
)
INSTRUCTIONS = 'Use Analyst for metrics, Search for policies';

# Simple API call - orchestration happens automatically
response = agent.run(query, thread_id=thread_id)
```

**Result:** ✅✅ Automatic multi-tool orchestration without client-side logic!

**Benefits:**
- **Zero orchestration code** in application
- **Intelligent tool routing** by agent
- **Thread support** for context
- **Enterprise-ready** with RBAC and monitoring

## Response Format Differences

### Pre-configured Agent Response
```json
{
  "event": "response",
  "data": {
    "role": "assistant",
    "content": [
      {
        "type": "thinking",
        "text": "User wants sales data AND policy info..."
      },
      {
        "type": "tool_use",
        "tool_use": {
          "type": "cortex_analyst_text2sql",
          "name": "Cortex Sales Analyst"
        }
      },
      {
        "type": "tool_result",
        "tool_result": {
          "content": [{"type": "json", "json": {"sql": "SELECT..."}}]
        }
      },
      {
        "type": "tool_use",
        "tool_use": {
          "type": "cortex_search",
          "name": "Cortex-Sales-Search"
        }
      },
      {
        "type": "tool_result",
        "tool_result": {
          "content": [{"type": "json", "json": {"search_results": [...]}}]
        }
      },
      {
        "type": "text",
        "text": "Here are the top 3 distributors... Regarding refunds...",
        "annotations": [
          {
            "type": "cortex_search_citation",
            "index": 0,
            "doc_id": "policy.pdf"
          }
        ]
      }
    ]
  }
}
```

### Ad-hoc Agent Response
```json
{
  "event": "message.delta",
  "data": {
    "delta": {
      "content": [
        {
          "type": "tool_results",
          "tool_results": {
            "content": [{"type": "json", "json": {...}}]
          }
        }
      ]
    }
  }
}
```

**Key Differences:**
- Event type: `response` vs `message.delta`
- Structure: `data.content[]` vs `data.delta.content[]`
- Tool results: `tool_result` vs `tool_results`
- Annotations: Embedded in text items vs separate

## Recommendations

### For Production Applications
✅ **Use Pre-configured Agents** (`Streamlit_agent.py`)

**When:**
- Need multi-tool orchestration
- Want conversation context (threads)
- Require enterprise features (RBAC, audit)
- Building user-facing applications

**Benefits:**
- Automatic intelligent orchestration
- Cleaner application code
- Better performance with threads
- Built-in monitoring and feedback

### For Prototyping
⚠️ **Use Ad-hoc Agent** with caution

**When:**
- Quick proof-of-concept
- Single-tool scenarios
- No database object creation allowed
- Experimenting with new tools

**Note:** For compound queries, implement client-side orchestration (see `Streamlit.py`)

### For Complex Workflows (Future)
🚀 **Consider LangGraph**

**When:**
- 3+ tools with complex routing
- Conditional logic between tools
- Human-in-the-loop workflows
- Advanced error handling and retries

See `docs/LANGGRAPH_DISCUSSION.md` for detailed analysis.

## Performance Characteristics

### Pre-configured Agent
- **Latency:** Single API call, ~2-5s for compound queries
- **Throughput:** Limited by Snowflake service quotas
- **Context:** Thread-based, server maintains state
- **Cost:** Per-token pricing for LLM + tool execution

### Client-side Orchestration
- **Latency:** Multiple API calls, ~5-10s for compound queries
- **Throughput:** Higher (parallel tool calls possible)
- **Context:** Client maintains state
- **Cost:** Additional LLM calls for splitting/combining

## Security & Governance

### Pre-configured Agent
- ✅ RBAC via `USAGE` privilege on agent object
- ✅ Tool-level access control
- ✅ Audit logs via `MONITOR` privilege
- ✅ Semantic model governance (row-level security)
- ✅ Cortex Search service permissions

### Ad-hoc Agent
- ⚠️ Requires `CORTEX_USER` or `CORTEX_AGENT_USER` role
- ⚠️ Client responsible for access control
- ⚠️ Limited audit capabilities
- ✅ Same tool-level security

## Monitoring & Debugging

### Pre-configured Agent
```sql
-- View agent interactions
SELECT * FROM TABLE(INFORMATION_SCHEMA.AGENT_HISTORY(
    AGENT_NAME => 'CORTEX_SALES_AGENT'
));

-- Check thread messages
SELECT * FROM TABLE(INFORMATION_SCHEMA.THREAD_MESSAGES(
    THREAD_ID => 12345
));
```

### Debug Mode in Application
Enable comprehensive debugging in Streamlit:
```python
debug_mode = st.checkbox("Debug Mode", value=False)
```

Shows:
- Raw API responses
- Individual SSE events
- Tool calls and results
- Metadata (thread IDs, message IDs)
- Performance metrics

## Conclusion

**Key Takeaway:** Pre-configured Cortex Agents are **enterprise-ready** and handle multi-tool orchestration **automatically**, making them the recommended approach for production applications.

The client-side orchestration in `Streamlit.py` serves as:
1. **Proof that multi-tool works** (validation)
2. **Fallback approach** if pre-configured agents unavailable
3. **Learning reference** for understanding orchestration logic

For new projects: **Start with pre-configured agents** and only implement manual orchestration if specific requirements demand it.
