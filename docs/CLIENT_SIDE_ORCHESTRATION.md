# Practical Workaround: Client-Side Query Orchestration

## Implementation Guide

This guide provides a practical workaround for the multi-tool orchestration issue by implementing client-side query detection and routing.

## Strategy

Instead of relying on Claude to call both tools, we:
1. Analyze the user's query
2. Detect if it needs policy info, data, or both
3. Make separate API calls for each tool
4. Combine the results ourselves

## Code Implementation

### Step 1: Add Query Analyzer

Add this function to your `Streamlit.py`:

```python
def analyze_query(query: str) -> dict:
    """
    Analyze query to determine which tools are needed.
    Returns dict with 'needs_faq' and 'needs_data' flags.
    """
    query_lower = query.lower()
    
    # Keywords that indicate data/analytics questions
    data_keywords = [
        'how many', 'count', 'total', 'sum', 'average', 
        'revenue', 'sales', 'orders', 'customers',
        'statistics', 'metrics', 'analytics', 'data',
        'number of', 'amount', 'quantity', 'top',
        'performance', 'trend', 'growth'
    ]
    
    # Keywords that indicate policy/FAQ questions
    policy_keywords = [
        'policy', 'procedure', 'how do i', 'how can i',
        'what is the process', 'what are the steps',
        'return', 'refund', 'shipping', 'warranty',
        'faq', 'question', 'help', 'support'
    ]
    
    needs_data = any(keyword in query_lower for keyword in data_keywords)
    needs_faq = any(keyword in query_lower for keyword in policy_keywords)
    
    # Additional heuristics
    # If query has "and" and both types, likely compound
    if ' and ' in query_lower:
        # Check both sides of "and"
        parts = query_lower.split(' and ')
        for part in parts:
            if any(kw in part for kw in data_keywords):
                needs_data = True
            if any(kw in part for kw in policy_keywords):
                needs_faq = True
    
    return {
        'needs_faq': needs_faq,
        'needs_data': needs_data,
        'is_compound': needs_faq and needs_data
    }
```

### Step 2: Create Targeted API Calls

Add these functions:

```python
def call_faq_only(query: str):
    """Call only the Faq Search tool"""
    payload = {
        "model": "claude-3-5-sonnet",
        "messages": [{"role": "user", "content": [{"type": "text", "text": query}]}],
        "tools": [
            {"tool_spec": {"type": "cortex_search", "name": "Faq Search"}}
        ],
        "tool_resources": {
            "Faq Search": {
                "name": CORTEX_SEARCH_DOCUMENTATION, 
                "max_results": 3, 
                "title_column": "RELATIVE_PATH",
                "id_column": "CHUNK_INDEX",
                "experimental": {"returnConfidenceScores": True}
            }
        },
        "response_instruction": "Search the FAQ documents and provide relevant policy information."
    }
    
    resp = _snowflake.send_snow_api_request(
        "POST", API_ENDPOINT, {}, {'stream': True}, 
        payload, None, API_TIMEOUT
    )
    
    if resp["status"] == 200:
        return json.loads(resp["content"])
    return None

def call_analyst_only(query: str):
    """Call only the Sales Analyst tool"""
    payload = {
        "model": "claude-3-5-sonnet",
        "messages": [{"role": "user", "content": [{"type": "text", "text": query}]}],
        "tools": [
            {"tool_spec": {"type": "cortex_analyst_text_to_sql", "name": "Sales Analyst"}}
        ],
        "tool_resources": {
            "Sales Analyst": {"semantic_model_file": SEMANTIC_MODEL}
        },
        "response_instruction": "Query the sales database and provide quantitative insights."
    }
    
    resp = _snowflake.send_snow_api_request(
        "POST", API_ENDPOINT, {}, {'stream': True}, 
        payload, None, API_TIMEOUT
    )
    
    if resp["status"] == 200:
        return json.loads(resp["content"])
    return None
```

### Step 3: Implement Smart Orchestrator

Replace the query handling in `main()`:

```python
def smart_query_handler(query: str, debug_mode=True):
    """
    Intelligently route queries to appropriate tools
    """
    analysis = analyze_query(query)
    
    if debug_mode:
        st.info(f"Query Analysis: FAQ={'✓' if analysis['needs_faq'] else '✗'}, "
                f"Data={'✓' if analysis['needs_data'] else '✗'}, "
                f"Compound={'✓' if analysis['is_compound'] else '✗'}")
    
    all_text = ""
    all_sql = ""
    all_citations = []
    
    # Handle compound queries with separate calls
    if analysis['is_compound']:
        st.info("🔀 Detected compound query - routing to multiple tools")
        
        # Call FAQ first
        if analysis['needs_faq']:
            with st.spinner("Searching FAQ documents..."):
                faq_response = call_faq_only(query)
                text, sql, citations = process_sse_response(faq_response, debug_mode)
                all_text += f"**Policy Information:**\n\n{text}\n\n"
                all_citations.extend(citations)
        
        # Call Analyst second
        if analysis['needs_data']:
            with st.spinner("Querying sales database..."):
                data_response = call_analyst_only(query)
                text, sql, citations = process_sse_response(data_response, debug_mode)
                all_text += f"**Data Analysis:**\n\n{text}"
                all_sql = sql
        
        return all_text, all_sql, all_citations
    
    # Single tool queries - use original method
    else:
        response = snowflake_api_call(query, 1)
        return process_sse_response(response, debug_mode)
```

### Step 4: Update Main Function

Modify the query handling section:

```python
if query := st.chat_input("Would you like to learn?"):
    # Add user message to chat
    with st.chat_message("user"):
        st.markdown(query)
    st.session_state.messages.append({"role": "user", "content": query})
    
    # Get response with smart routing
    with st.spinner("Processing your request..."):
        text, sql, citations = smart_query_handler(
            query, 
            st.session_state.get('debug_mode', True)
        )
        
        # Add assistant response to chat
        if text:
            text = text.replace("【†", "[").replace("†】", "]")
            st.session_state.messages.append({"role": "assistant", "content": text})
            
            with st.chat_message("assistant"):
                st.markdown(text.replace("•", "\n\n"))
                if citations:
                    display_citations(citations)
    
        # Display SQL if present
        if sql:
            st.markdown("### Generated SQL")
            st.code(sql, language="sql")
            sales_results = run_snowflake_query(sql)
            if sales_results:
                st.write("### Sales Metrics Report")
                st.dataframe(sales_results)
```

## Testing the Workaround

### Test Query 1: Compound Question
```
"What is the refund policy and how many orders were placed?"
```

**Expected Behavior:**
1. 🔀 Detected compound query - routing to multiple tools
2. Searching FAQ documents... ✓
3. Querying sales database... ✓
4. **Policy Information:** [FAQ results]
5. **Data Analysis:** [SQL results and count]

### Test Query 2: FAQ Only
```
"What is the shipping policy?"
```

**Expected Behavior:**
1. Query Analysis: FAQ=✓, Data=✗, Compound=✗
2. [Single FAQ call]

### Test Query 3: Data Only
```
"How many orders were placed last month?"
```

**Expected Behavior:**
1. Query Analysis: FAQ=✗, Data=✓, Compound=✗
2. [Single Analyst call]

## Advantages of This Approach

1. ✅ **Guaranteed Tool Execution**: You control which tools are called
2. ✅ **No LLM Decision-Making**: Doesn't rely on Claude's judgment
3. ✅ **Predictable Behavior**: Same query always routes the same way
4. ✅ **Clear User Feedback**: Shows which tools are being used
5. ✅ **Fallback to Original**: Single-tool queries still use original method

## Limitations

1. ❌ **Keyword-Based Detection**: May miss nuanced queries
2. ❌ **False Positives**: Might call tools unnecessarily
3. ❌ **Two API Calls**: Slower for compound queries
4. ❌ **Doubled Costs**: Each tool call costs separately

## Improvements

### Use LLM for Classification
Replace keyword matching with another LLM call:

```python
def llm_analyze_query(query: str) -> dict:
    """Use small LLM to classify query intent"""
    classification_prompt = f"""
    Classify this query:
    "{query}"
    
    Return JSON:
    {{
        "needs_faq": true/false,
        "needs_data": true/false
    }}
    """
    # Make classification call to simpler/cheaper model
    # Parse response
    return result
```

### Add User Confirmation
For compound queries, ask user to confirm:

```python
if analysis['is_compound']:
    st.warning("This question requires both FAQ search and database query. Proceed?")
    if st.button("Yes, query both"):
        # Execute both tools
```

### Cache Results
Avoid duplicate calls:

```python
@st.cache_data(ttl=300)
def call_faq_cached(query):
    return call_faq_only(query)
```

## Conclusion

This workaround bypasses Claude's reluctance to call multiple tools by:
1. Taking control of tool orchestration
2. Making explicit, separate API calls
3. Combining results client-side

**Trade-off**: More complexity, but guaranteed to work.

**Result**: Reliable multi-tool responses for compound queries.
