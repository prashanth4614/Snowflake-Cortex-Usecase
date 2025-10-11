# Snowflake Cortex Agent: Multi-Tool Orchestration Issue

## Background

I'm building a sales assistant using Snowflake's Cortex Agent API (`/api/v2/cortex/agent:run`) with two tools:

1. **Cortex Search** (`cortex_search`) - For searching policy documents and FAQs
2. **Cortex Analyst** (`cortex_analyst_text_to_sql`) - For querying sales database via natural language

## The Problem

When I send a **compound query** that requires BOTH tools, the LLM only executes ONE tool and refuses to call the second one, even with explicit instructions.

### Example Query:
```
"What is the refund policy and how many orders were placed in 2025?"
```

**Expected Behavior:**
- Call Cortex Search → Get refund policy
- Call Cortex Analyst → Get order count from database
- Combine both results

**Actual Behavior:**
- Only calls Cortex Search
- Returns policy info
- Says: "I cannot provide information about orders" or "Would you like me to help you get that data using the Sales Analyst tool?" (asking permission instead of executing)

## What I've Tried

### 1. Multiple Claude Models
- ❌ `claude-3-5-sonnet` - Same issue
- ❌ `claude-3-7-sonnet` - Same issue  
- ❌ `claude-sonnet-4-5` - Same issue (even with advanced agentic capabilities)

### 2. Aggressive Response Instructions
```json
{
  "response_instruction": "You MUST use ALL relevant tools to answer the question. 
  If the query has multiple parts, call multiple tools. 
  Execute tools FIRST, then explain. DO NOT ask for permission."
}
```
**Result:** Still only calls one tool

### 3. Tried `tool_choice` Parameter
```json
{
  "tool_choice": "auto"
}
```
**Result:** 500 Error - Parameter not supported by Snowflake API

## API Details

**Endpoint:** `/api/v2/cortex/agent:run`

**Request Structure:**
```json
{
  "model": "claude-sonnet-4-5",
  "messages": [
    {
      "role": "user",
      "content": [{"type": "text", "text": "compound query here"}]
    }
  ],
  "tools": [
    {
      "tool_spec": {
        "type": "cortex_analyst_text_to_sql",
        "name": "Sales Analyst"
      }
    },
    {
      "tool_spec": {
        "type": "cortex_search",
        "name": "Faq Search"
      }
    }
  ],
  "tool_resources": {
    "Sales Analyst": {
      "semantic_model_file": "@STAGE/semantic_model.yaml"
    },
    "Faq Search": {
      "name": "DOCS_SEARCH_SERVICE",
      "max_results": 3
    }
  },
  "response_instruction": "Use all relevant tools..."
}
```

**Response:** SSE (Server-Sent Events) stream with tool usage tracking

## Observations

1. **Tool awareness works**: Debug output shows LLM recognizes both tools are available
2. **Single-tool queries work perfectly**: 
   - "What is the refund policy?" → ✅ Calls Search
   - "How many orders in 2025?" → ✅ Calls Analyst
3. **Multi-tool refusal is consistent**: Even Claude Sonnet 4.5 (designed for agentic workflows) refuses to call both
4. **LLM asks permission**: Instead of executing, it says things like "Would you like me to query the database?"

## Current Workaround

I implemented **client-side orchestration**:

1. Use an LLM to split compound query into tool-specific parts
2. Call each tool separately with its relevant query part
3. Combine results in my application code

**This works 100% reliably**, but defeats the purpose of having an intelligent agent.

## Questions for the Community

1. **Is this expected behavior?** Should Cortex Agent only call one tool per request?

2. **Is there a configuration I'm missing?** Any hidden parameters to enable multi-tool orchestration?

3. **Is this an LLM limitation?** Do the Claude models have some built-in restriction against calling multiple tools?

4. **Has anyone successfully used Cortex Agent with multiple tools in one query?** If so, how?

5. **Is this documented somewhere?** The official Snowflake docs say multi-tool support exists, but don't mention limitations.

## Environment

- **Platform:** Snowflake (Streamlit in Snowflake)
- **API:** `/api/v2/cortex/agent:run` (Ad-hoc agent execution)
- **Models Tested:** claude-3-5-sonnet, claude-3-7-sonnet, claude-sonnet-4-5
- **Region:** [Your region - may affect model availability]

## What Works

✅ Single tool queries  
✅ Client-side orchestration (splitting queries manually)  
✅ Tool configuration and access  
✅ SSE response processing  

## What Doesn't Work

❌ LLM automatically calling multiple tools for compound queries  
❌ `tool_choice` parameter (returns 500 error)  
❌ Aggressive prompting to force multi-tool usage  

---

**Has anyone experienced this? Is this a known limitation or am I missing something fundamental about how Cortex Agent is supposed to work?**

Any insights would be greatly appreciated!

## Additional Context

- Verified from official Snowflake documentation that multi-tool orchestration IS supported
- The agent API is stateless (each request is independent)
- No conversation history is maintained between calls
- Both tools work independently without issues

