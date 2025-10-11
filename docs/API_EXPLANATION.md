# Understanding Snowflake Cortex Agent API

## API Overview: `/api/v2/cortex/agent:run`

### Type: **Ad-Hoc Agent Execution**

This is NOT a pre-configured, persistent agent. Instead, it's a **runtime agent execution endpoint** where you define everything in each request.

## Key Characteristics

### 1. Stateless Execution
- Each API call is completely independent
- No memory between requests
- No conversation history maintained
- You must include full context in each call

### 2. Configuration Per Request
Every API call requires you to specify:
- Which LLM model to use
- What tools are available
- How to configure each tool
- What instructions to follow

### 3. Tool Execution Flow

```
Request → Agent Runtime → LLM Decision → Tool Selection → Tool Execution → Response Assembly
```

**Detailed Flow:**
1. **Your App** sends request with query, tools, and config
2. **Cortex Agent Runtime** initializes with your specifications
3. **LLM** analyzes query and decides which tool(s) to use
4. **Agent** executes the selected tool(s)
5. **Results** are streamed back via Server-Sent Events (SSE)

## API Structure Breakdown

### Endpoint
```
POST /api/v2/cortex/agent:run
```

### Request Components

#### 1. Model Selection
```json
{
  "model": "claude-sonnet-4-5"
}
```
- Determines which LLM brain the agent uses
- Available: claude-3-5-sonnet, claude-3-7-sonnet, claude-sonnet-4-5
- Different models have different reasoning capabilities

#### 2. Messages (User Input)
```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "What is the refund policy?"
        }
      ]
    }
  ]
}
```
- The user's question or request
- Currently only single-turn (no conversation history support in this implementation)

#### 3. Tools Definition
```json
{
  "tools": [
    {
      "tool_spec": {
        "type": "cortex_search",        // Tool type
        "name": "Faq Search"             // Friendly name for LLM
      }
    },
    {
      "tool_spec": {
        "type": "cortex_analyst_text_to_sql",
        "name": "Sales Analyst"
      }
    }
  ]
}
```

**Available Tool Types:**
- `cortex_search` - Hybrid search (semantic + keyword) over documents
- `cortex_analyst_text_to_sql` - Natural language to SQL conversion
- Others: Custom functions, web search, etc.

#### 4. Tool Resources (Configuration)
```json
{
  "tool_resources": {
    "Sales Analyst": {
      "semantic_model_file": "@STAGE_NAME/semantic_model.yaml"
    },
    "Faq Search": {
      "name": "CORTEX_SEARCH_SERVICE_NAME",
      "max_results": 3,
      "title_column": "RELATIVE_PATH",
      "id_column": "CHUNK_INDEX",
      "experimental": {
        "returnConfidenceScores": true
      }
    }
  }
}
```

**Cortex Analyst Config:**
- `semantic_model_file`: Path to YAML file defining database schema, tables, relationships

**Cortex Search Config:**
- `name`: Name of the Cortex Search service
- `max_results`: Maximum number of search results to return
- `title_column`: Which column to use as document title
- `id_column`: Unique identifier column
- `experimental.returnConfidenceScores`: Include relevance scores

#### 5. Response Instruction (Optional)
```json
{
  "response_instruction": "Answer concisely using the available tools."
}
```
- Guides the LLM on how to format responses
- Should influence tool selection (but doesn't always work for multi-tool)

### Response Format: Server-Sent Events (SSE)

The API returns a **stream** of events:

```json
{
  "event": "message.delta",
  "data": {
    "delta": {
      "content": [
        {
          "type": "tool_use",
          "tool_use": {
            "type": "cortex_search",
            "name": "Faq Search"
          }
        }
      ]
    }
  }
}
```

**Event Types:**
- `message.delta` - Incremental response data
- Content types within delta:
  - `tool_use` - Indicates a tool is being called
  - `tool_results` - Results from tool execution
  - `text` - LLM-generated text response

## The Multi-Tool Problem Explained

### What SHOULD Happen (According to Docs)

**Query:** "What is the refund policy and how many orders in 2025?"

**Expected Agent Behavior:**
1. LLM analyzes query → Identifies TWO needs:
   - Policy information (Search tool)
   - Order count (Analyst tool)
2. Agent calls BOTH tools
3. Search returns: "Refunds processed in 5-7 days..."
4. Analyst returns: SQL query + results (e.g., 150 orders)
5. LLM combines: "Refunds are processed... There were 150 orders in 2025."

### What ACTUALLY Happens

**Observed Behavior:**
1. LLM analyzes query
2. Agent calls ONLY Search tool
3. Search returns policy info
4. LLM says: "I cannot provide order count information" OR "Would you like me to query the database using the Sales Analyst tool?"
5. **Second tool is NEVER executed**

### Why This Is Problematic

**It's not a technical failure** - the LLM is making a deliberate decision to:
- Only call one tool
- Ask for permission before calling the second tool
- Be "conservative" in tool usage

**Possible Reasons:**
1. **Safety Guardrails**: Claude models may have built-in restrictions on multi-tool calls
2. **Token/Cost Optimization**: LLM might avoid "unnecessary" tool calls
3. **Unclear Intent**: LLM might think user wants to confirm before querying database
4. **API Limitations**: Snowflake's implementation might limit tool calls per request
5. **Tool Orchestration Logic**: The agent runtime might not properly support parallel or sequential multi-tool execution

### Evidence It's LLM Behavior, Not API Limitation

1. ✅ Official Snowflake docs explicitly mention multi-tool support
2. ✅ The API accepts multiple tools in configuration
3. ✅ No error messages when providing multiple tools
4. ✅ Debug logs show LLM is aware of both tools
5. ❌ But LLM consistently chooses to call only one
6. ❌ Even with aggressive prompting: "MUST use ALL tools"

## Comparison: Ad-Hoc vs Persistent Agents

### Ad-Hoc Agent (What You're Using)
- Defined per request
- No state between calls
- Full flexibility
- You control everything
- **Downside**: Must handle orchestration yourself

### Persistent Agent (Not Available in This API)
- Pre-configured in Snowflake
- Can maintain conversation history
- Pre-defined tools and behavior
- More "set and forget"
- **Downside**: Less flexible

## Why Client-Side Orchestration Works

Your current working solution:

```python
# 1. Analyze query with LLM
split_result = llm_split_query(query)

# 2. Call Search with policy-specific part
search_response = agent_api(split_result['search_query'], tools=['search_only'])

# 3. Call Analyst with data-specific part  
analyst_response = agent_api(split_result['analyst_query'], tools=['analyst_only'])

# 4. Combine results yourself
final_response = combine(search_response, analyst_response)
```

**Why this works:**
- Each API call has ONLY ONE tool
- LLM has no choice - must use that tool
- No ambiguity in tool selection
- You control the orchestration logic

**Trade-offs:**
- ✅ 100% reliable
- ✅ Predictable behavior
- ✅ Full control over query splitting
- ❌ More API calls (3 instead of 1)
- ❌ More code complexity
- ❌ Higher latency (sequential calls)

## Best Practices for Your Use Case

### When to Use Single Tool per Call
- Compound queries requiring multiple tools
- When you need guaranteed tool execution
- When you want explicit control over orchestration

### When to Trust LLM Orchestration
- Simple queries clearly needing one tool
- When user intent is unambiguous
- Exploratory queries where tool choice is flexible

### Hybrid Approach (What You Implemented)
```python
if needs_both_tools(query):
    # Client-side orchestration
    return orchestrate_manually(query)
else:
    # Let LLM decide
    return agent_api(query, all_tools)
```

## Summary for Reddit Post

**Key Points to Emphasize:**

1. **API Type**: Ad-hoc agent execution, stateless, configuration per request
2. **The Issue**: LLM refuses to call multiple tools even when both are clearly needed
3. **Not a Bug**: Tools work individually, API accepts multiple tools, docs say it's supported
4. **LLM Behavior**: Consistent across Claude 3.5, 3.7, and 4.5
5. **Workaround**: Client-side orchestration (works perfectly but adds complexity)
6. **Question**: Is this expected? Is there a configuration to force multi-tool usage?

## Additional Resources

- **Snowflake Cortex Agent Docs**: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agent
- **Cortex Search**: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search
- **Cortex Analyst**: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst

## Questions to Ask on Reddit

1. Has anyone successfully used Cortex Agent with multiple tools in a single query?
2. Is there an undocumented parameter or configuration option?
3. Is this a known limitation that Snowflake is working on?
4. Do I need to use a different API endpoint for multi-tool orchestration?
5. Are there examples of multi-tool agent usage in Snowflake documentation?

