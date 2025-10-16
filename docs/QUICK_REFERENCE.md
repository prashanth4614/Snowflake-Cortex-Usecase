# Quick Reference - Pre-configured Agent Implementation

## 🚀 One-Page Cheat Sheet

### Core API Call

```python
import _snowflake
import json

# Simple (no threads)
payload = {
    "model": "claude-sonnet-4-5",
    "messages": [{"role": "user", "content": [{"type": "text", "text": query}]}]
}

# With threads (recommended)
payload = {
    "model": "claude-sonnet-4-5",
    "thread_id": 12345,
    "parent_message_id": 42,
    "messages": [{"role": "user", "content": [{"type": "text", "text": query}]}]
}

# Make request
resp = _snowflake.send_snow_api_request(
    "POST",
    "/api/v2/databases/DB/schemas/SCHEMA/agents/AGENT_NAME:run",
    {},
    {'stream': True},
    payload,
    None,
    50000
)

response_content = json.loads(resp["content"])
```

---

### Response Structure

```python
# Event types in response array
for event in response_content:
    event_type = event.get('event')
    
    if event_type == "metadata":
        # Thread info
        message_id = event['data']['message_id']
        role = event['data']['role']
    
    elif event_type == "response":
        # Main response - all content here
        for item in event['data']['content']:
            
            if item['type'] == "thinking":
                # Agent's reasoning
                thinking_text = item['text']
            
            elif item['type'] == "tool_use":
                # Tool invocation
                tool_name = item['tool_use']['name']
                tool_type = item['tool_use']['type']
                tool_input = item['tool_use']['input']
            
            elif item['type'] == "tool_result":
                # Tool execution result
                result_content = item['tool_result']['content']
                for r in result_content:
                    if r['type'] == 'json':
                        # SQL from Cortex Analyst
                        sql = r['json'].get('sql', '')
                        # Search results from Cortex Search
                        search_results = r['json'].get('search_results', [])
            
            elif item['type'] == "text":
                # Final response text
                text = item['text']
                # Citations
                for annotation in item.get('annotations', []):
                    if annotation['type'] == 'cortex_search_citation':
                        doc_id = annotation['doc_id']
                        doc_title = annotation['doc_title']
```

---

### Thread Management

```python
# Create thread
def create_thread():
    resp = _snowflake.send_snow_api_request(
        "POST",
        "/api/v2/cortex/threads",
        {},
        {},
        {"origin_application": "my_app"},
        None,
        50000
    )
    return json.loads(resp["content"])['thread_id']

# Use in session state
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = create_thread()
    st.session_state.parent_message_id = 0

# Each turn
response = call_agent(
    query,
    thread_id=st.session_state.thread_id,
    parent_message_id=st.session_state.parent_message_id
)

# Update for next turn
text, sql, citations, metadata = process_response(response)
st.session_state.parent_message_id = metadata['message_id']
```

---

### Agent Setup (SQL)

```sql
-- Create agent
CREATE AGENT my_agent
IN SCHEMA my_schema
WITH DISPLAY_NAME = 'My Agent';

-- Add Cortex Analyst tool
ALTER AGENT my_agent
ADD TOOL cortex_analyst_semantic_view(
    NAME => 'Analyst Tool',
    SEMANTIC_VIEW => 'my_db.my_schema.my_semantic_model',
    WAREHOUSE => 'my_wh',
    QUERY_TIMEOUT => 60
);

-- Add Cortex Search tool
ALTER AGENT my_agent
ADD TOOL cortex_search_service(
    NAME => 'Search Tool',
    SERVICE => 'my_db.my_schema.my_search_service'
);

-- Add instructions
ALTER AGENT my_agent
SET ORCHESTRATION_INSTRUCTIONS = 'Use Analyst for metrics, Search for policies',
    RESPONSE_INSTRUCTIONS = 'Be concise and friendly';

-- Grant access
GRANT USAGE ON AGENT my_agent TO ROLE my_role;
```

---

### Common Patterns

#### Pattern 1: Simple Query
```python
query = "What are total sales?"
response = agent_call(query)
text, sql, citations, _ = process_response(response)

# Display
st.write(text)
if sql:
    st.code(sql, language='sql')
```

#### Pattern 2: Compound Query (Auto-handled!)
```python
query = "Show top products AND explain return policy"
# Agent automatically:
# 1. Calls Cortex Analyst for products
# 2. Calls Cortex Search for policy
# 3. Combines results

response = agent_call(query)
text, sql, citations, _ = process_response(response)

# Both tools were used automatically!
st.write(text)  # Combined response
if citations:
    display_citations(citations)
```

#### Pattern 3: Conversation
```python
# Query 1
response = agent_call("What are top distributors?", thread_id=123, parent_msg_id=0)
_, _, _, meta1 = process_response(response)

# Query 2 - understands context!
response = agent_call("What about the second one?", thread_id=123, parent_msg_id=meta1['message_id'])
_, _, _, meta2 = process_response(response)
```

---

### Debugging

```python
# Show raw response
if debug_mode:
    with st.expander("Raw Response"):
        st.json(response_content)

# Show each event
for i, event in enumerate(response_content):
    if debug_mode:
        with st.expander(f"Event {i}: {event.get('event')}"):
            st.json(event)

# Track tools called
tools_used = []
for event in response_content:
    if event.get('event') == 'response':
        for item in event['data']['content']:
            if item['type'] == 'tool_use':
                tools_used.append(item['tool_use']['name'])

if debug_mode:
    st.info(f"Tools used: {', '.join(set(tools_used))}")
```

---

### Error Handling

```python
try:
    resp = _snowflake.send_snow_api_request(...)
    
    if resp["status"] != 200:
        st.error(f"HTTP {resp['status']}: {resp.get('reason')}")
        return None
    
    response_content = json.loads(resp["content"])
    
except json.JSONDecodeError:
    st.error("Invalid response format")
    return None
    
except Exception as e:
    st.error(f"Request failed: {str(e)}")
    return None
```

---

### Performance Tips

1. **Use threads** - Reduces payload, faster context
2. **Stream responses** - Set `{'stream': True}` in params
3. **Cache thread_id** - Create once per conversation
4. **Timeout properly** - Set appropriate API_TIMEOUT
5. **Debug only when needed** - Toggle via checkbox

---

### Key Differences: Pre-configured vs Ad-hoc

| Feature | Pre-configured | Ad-hoc |
|---------|---------------|--------|
| Endpoint | `/agents/{name}:run` | `/cortex/agent:run` |
| Tools | Stored in agent | In request payload |
| Multi-tool | ✅ Automatic | ⚠️ Manual |
| Event | `"response"` | `"message.delta"` |
| Thread | ✅ Supported | ⚠️ Limited |
| Best for | Production | Prototyping |

---

### Common Issues

**Issue:** Empty response despite 200 OK
```python
# Check event type
if event.get('event') == "response":  # ✅ Pre-configured
    # not "message.delta"
```

**Issue:** Multi-tool not working
```python
# ✅ Pre-configured agent handles automatically
# ❌ Ad-hoc agent needs manual orchestration
```

**Issue:** Context not maintained
```python
# ✅ Use threads
thread_id = create_thread()
# ✅ Update parent_message_id each turn
parent_message_id = metadata['message_id']
```

---

### Streamlit Boilerplate

```python
import streamlit as st
import json
import _snowflake

# Session state
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = create_thread()
if 'parent_message_id' not in st.session_state:
    st.session_state.parent_message_id = 0
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg['role']):
        st.write(msg['content'])

# Input
if query := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": query})
    
    with st.chat_message("user"):
        st.write(query)
    
    # Get response
    response = agent_call(
        query,
        thread_id=st.session_state.thread_id,
        parent_message_id=st.session_state.parent_message_id
    )
    
    text, sql, citations, metadata = process_response(response)
    
    # Update state
    st.session_state.parent_message_id = metadata['message_id']
    st.session_state.messages.append({"role": "assistant", "content": text})
    
    # Display
    with st.chat_message("assistant"):
        st.write(text)
```

---

### Resources

- **Docs**: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents
- **API Reference**: https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-run
- **Architecture Guide**: `docs/ARCHITECTURE.md`
- **Full Implementation**: `Streamlit_agent.py`

---

**Pro Tip:** Pre-configured agents are production-ready. Ad-hoc agents need client-side orchestration for compound queries. Always use threads for conversations!
