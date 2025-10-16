# Cortex Agent JSON Format Guide

## Overview

The `CORTEX_AGENT_SALES.json` file contains the agent definition. This document explains the structure and how it's used for agent creation.

## Current JSON Structure

The current JSON file follows the **GET response format** from the Snowflake REST API:

```json
{
  "data": {
    "agent_spec": { ... },  // The actual agent specification
    "name": "CORTEX_SALES_AGENT",
    "database_name": "SNOWFLAKE_INTELLIGENCE",
    "schema_name": "AGENTS",
    "owner": "ACCOUNTADMIN",
    "created_on": "2025-10-13T03:04:36.731+00:00"
  },
  "code": null,
  "message": null,
  "success": true
}
```

## ✅ This Format Works!

The code is designed to extract the correct `agent_spec` from this GET response format:

```python
def load_agent_config() -> Optional[Dict]:
    config = json.load(f)
    return config.get('data', {}).get('agent_spec', {})
    # Returns just the agent_spec object
```

## Agent Spec Structure

The `agent_spec` object contains:

### 1. **Models** (Required)
```json
{
  "models": {
    "orchestration": "claude-3-5-sonnet"
  }
}
```

### 2. **Orchestration** (Optional)
```json
{
  "orchestration": {}
}
```

### 3. **Instructions** (Required)
```json
{
  "instructions": {
    "orchestration": "Tool selection and query type rules...",
    "response": "Response formatting guidelines..."
  }
}
```

### 4. **Tools** (Required)
```json
{
  "tools": [
    {
      "tool_spec": {
        "type": "cortex_analyst_text_to_sql",
        "name": "Cortex Sales Analyst",
        "description": "Table schemas and descriptions..."
      }
    },
    {
      "tool_spec": {
        "type": "cortex_search",
        "name": "Cortex-Sales-Search",
        "description": ""
      }
    }
  ]
}
```

### 5. **Tool Resources** (Required)
```json
{
  "tool_resources": {
    "Cortex Sales Analyst": {
      "execution_environment": {
        "type": "warehouse",
        "warehouse": ""
      },
      "semantic_model_file": "@CORTEX_AGENTS.SALES.CORTEX_ANALYST_STAGE/CORTEX_AGENT_SALES.yaml"
    },
    "Cortex-Sales-Search": {
      "id_column": "RELATIVE_PATH",
      "max_results": 4,
      "name": "CORTEX_AGENTS.SALES.DOCS",
      "title_column": "CHUNK"
    }
  }
}
```

## How the Code Uses This

### 1. **Loading Configuration**
```python
agent_spec = load_agent_config()
# Returns the agent_spec object (not the entire GET response)
```

### 2. **Creating Agent**
```python
payload = {
    "name": AGENT_NAME,
    "agent_spec": json.dumps(agent_spec)  # Convert to JSON string
}
```

### 3. **POST Request**
The API expects:
```json
{
  "name": "CORTEX_SALES_AGENT",
  "agent_spec": "<json_string_of_agent_spec>"
}
```

## Validation Checklist

✅ **Current JSON is valid** if it has:
- [x] `data.agent_spec` object
- [x] `models.orchestration` field
- [x] `instructions` object with `orchestration` and `response`
- [x] `tools` array with tool specs
- [x] `tool_resources` object matching tool names

✅ **Your JSON file has all required fields!**

## Alternative Format (If Needed)

If you want to simplify the file structure, you could store just the `agent_spec`:

```json
{
  "models": {
    "orchestration": "claude-3-5-sonnet"
  },
  "instructions": { ... },
  "tools": [ ... ],
  "tool_resources": { ... }
}
```

Then update `load_agent_config()`:
```python
def load_agent_config() -> Optional[Dict]:
    with open(config_path, 'r') as f:
        return json.load(f)  # Return entire file as agent_spec
```

## Recommendations

1. **Keep current format**: It matches the GET response structure, making it easy to update from Snowsight
2. **The code handles it correctly**: `load_agent_config()` extracts just what's needed
3. **No changes required**: Your current JSON and code work together properly

## Testing

To verify the agent creation works:

1. Delete the agent in Snowsight (if it exists)
2. Run the Streamlit app
3. It will detect missing agent and create it automatically
4. Check debug mode to see the creation payload

## Common Issues

❌ **Issue**: "Failed to create agent"
✅ **Fix**: Check that all resources exist:
- Search service: `CORTEX_AGENTS.SALES.DOCS`
- Semantic model: `@CORTEX_AGENTS.SALES.CORTEX_ANALYST_STAGE/CORTEX_AGENT_SALES.yaml`
- Database/Schema: `SNOWFLAKE_INTELLIGENCE.AGENTS`

❌ **Issue**: "Permission denied"
✅ **Fix**: Ensure you have `CREATE CORTEX AGENT` privilege

## Summary

✅ **Your JSON format is correct!**
✅ **Your code handles it properly!**
✅ **Agent creation should work as-is!**

The current implementation extracts `data.agent_spec` from your GET-response-formatted JSON and converts it to the string format needed for POST agent creation.
