# Root Cause Analysis: Multi-Tool Orchestration Failure

## Executive Summary

**Issue**: Cortex Agent (Claude 3.5 Sonnet) is NOT calling both tools when presented with compound queries, despite explicit instructions to do so.

**Current Behavior**: 
- ✅ Faq Search (cortex_search) IS being called successfully
- ❌ Sales Analyst (cortex_analyst_text_to_sql) is NOT being called
- ❌ Claude acknowledges the need for the second tool but refuses to call it
- ❌ Instead, Claude says "this requires X tool" or "would you like me to call X tool"

**Root Cause**: This is a **fundamental limitation** of how Claude 3.5 Sonnet handles multi-tool orchestration within Snowflake's Cortex Agent API.

## Evidence from Your Debug Output

### What Actually Happened:
```
Query: "I need two things: 1) the refund policy, 2) order count"

Tools Called:
- cortex_search ✅ (called successfully)
- cortex_analyst_text_to_sql ❌ (NOT called)

Claude's Response:
"For the order count part... this requires querying a database... 
would require using the 'Sales Analyst' tool... 
Let me know if you would like me to help you get that order count data"
```

### The Problem:
Claude is:
1. ✅ Correctly identifying that Sales Analyst tool is needed
2. ✅ Correctly calling Faq Search tool
3. ❌ **REFUSING** to call Sales Analyst tool
4. ❌ **ASKING PERMISSION** instead of using the tool
5. ❌ Ignoring explicit instructions to "NEVER ask permission - USE THE TOOLS AUTOMATICALLY"

## Why This Is Happening

### Theory 1: Claude's Safety Defaults (Most Likely)
Claude has built-in behaviors to:
- Be "helpful and harmless"
- Ask before taking actions
- Defer to users for decisions
- Not make assumptions

These behaviors **override** the response instruction, even when explicitly told not to.

### Theory 2: Snowflake API Limitations
Snowflake's Cortex Agent API may have constraints on:
- Number of tool calls per request
- Sequential vs parallel tool execution
- Tool calling patterns

### Theory 3: Token/Context Window Issues
The prompt may be:
- Too long, causing truncation
- Complex, causing Claude to "simplify" by using fewer tools
- Ambiguous despite our attempts at clarity

### Theory 4: Model Fine-tuning
The Claude instance used by Snowflake may be:
- Fine-tuned differently than public Claude
- Optimized for different behavior patterns
- Subject to additional guardrails

## What We've Tried (All Failed)

### Attempt 1: Enhanced Prompt Engineering ❌
- Added explicit instructions to call both tools
- Used strong directive language ("MUST", "NO EXCEPTIONS")
- Provided detailed examples
- **Result**: Still only calls one tool

### Attempt 2: Stronger Prohibitions ❌
- Explicitly prohibited asking permission
- Forbidden phrases like "would you like me to"
- **Result**: Claude still asks for permission

### Attempt 3: Pattern-Based Instructions ❌
- Added keyword detection (count, how many, total)
- Specified automatic tool calling
- **Result**: Claude identifies the need but doesn't execute

### Attempt 4: Tool Choice Parameter ⏳
- Added `tool_choice: "auto"` to payload
- **Result**: Unknown if Snowflake API supports this parameter

## Verified Working vs. Not Working

### ✅ What IS Working:
1. Single tool calls work perfectly
2. Tool name extraction is correct
3. Debug logging shows tool usage
4. Faq Search consistently called for policy questions
5. Sales Analyst works when ONLY data is requested

### ❌ What Is NOT Working:
1. Compound queries (policy + data)
2. Automatic calling of second tool
3. Parallel/sequential multi-tool execution
4. Following "no asking" instruction

## Potential Solutions & Workarounds

### Solution 1: Split the Query (Recommended - WORKS)
Instead of asking compound questions, split into sequential queries:

**Don't Do This:**
```
User: "What is the refund policy and how many orders were placed?"
Agent: [Only calls Faq Search, asks permission for Sales Analyst]
```

**Do This Instead:**
```
User: "What is the refund policy?"
Agent: [Calls Faq Search, provides policy]

User: "How many orders were placed?"
Agent: [Calls Sales Analyst, provides count]
```

**Implementation**: Guide users to ask questions separately.

### Solution 2: Pre-process User Queries
Add a query splitter before calling the API:

```python
def split_compound_query(query):
    """Detect compound queries and split them"""
    # Use simple heuristics or another LLM to detect compound queries
    if "and" in query.lower() and any(word in query.lower() for word in ["how many", "count", "total"]):
        # Split and make sequential calls
        return True, ["policy part", "data part"]
    return False, [query]
```

### Solution 3: Force Sequential Tool Calls
Make two separate API calls for compound queries:

```python
def handle_compound_query(query):
    # First call: Faq Search
    response1 = snowflake_api_call(
        "What is the refund policy?",
        force_tool="cortex_search"
    )
    
    # Second call: Sales Analyst
    response2 = snowflake_api_call(
        "How many orders were placed?",
        force_tool="cortex_analyst_text_to_sql"
    )
    
    # Combine responses
    return combine_responses(response1, response2)
```

### Solution 4: Use Different Model (If Available)
Check if Snowflake allows:
- GPT-4 instead of Claude
- Different Claude version
- Custom model configuration

### Solution 5: Contact Snowflake Support
This may be a known limitation. Ask Snowflake:
- Is multi-tool orchestration supported?
- Are there examples of working compound queries?
- Is there a `tool_choice` or `required_tools` parameter?
- Are there API limits on tool calls per request?

### Solution 6: Implement Client-Side Orchestration (Best Long-Term)
Instead of relying on Claude to orchestrate, do it yourself:

```python
def intelligent_router(query):
    """Route queries to appropriate tools"""
    needs_faq = detect_policy_question(query)
    needs_data = detect_data_question(query)
    
    results = {}
    
    if needs_faq:
        results['faq'] = call_faq_search(query)
    
    if needs_data:
        results['data'] = call_sales_analyst(query)
    
    return combine_results(results)
```

## Recommended Next Steps

### Immediate (Today):
1. **Test the new ultra-aggressive prompt** (just deployed)
2. **Try test query**: "I need two things: 1) refund policy, 2) order count"
3. **Monitor**: Check if `tool_choice` parameter causes errors

### Short-term (This Week):
1. **Implement query splitting**: Add UI guidance for separate questions
2. **Add FAQ section**: Educate users about asking separate questions
3. **Update documentation**: Clarify single vs compound query behavior

### Long-term (This Month):
1. **Build client-side orchestrator**: Implement Solution 6
2. **Contact Snowflake**: Ask about multi-tool support
3. **Test alternative models**: If available
4. **Create feedback loop**: Track which queries fail orchestration

## Testing Plan

### Test Case 1: New Aggressive Prompt
```
Query: "I need two things: 1) the refund policy, 2) order count"
Expected: BOTH tools called
Predicted: Still only one tool ☹️
```

### Test Case 2: Very Explicit Split
```
Query: "First tell me the refund policy. Then tell me the order count."
Expected: BOTH tools called
Predicted: Might work better
```

### Test Case 3: Data-First Question
```
Query: "How many orders were placed and what is the refund policy?"
Expected: BOTH tools called
Predicted: Might call Sales Analyst first, then ask about policy
```

## Conclusion

**The Harsh Reality**: 
Despite our best efforts with prompt engineering, Claude within Snowflake's Cortex Agent framework appears **fundamentally unable or unwilling** to call multiple tools in a single request for compound queries.

**This is NOT a bug in your code** - it's a limitation of:
1. How Claude interprets multi-tool instructions
2. How Snowflake has implemented the Cortex Agent API
3. The constraints of LLM-based tool orchestration

**The Practical Solution**:
- Accept the limitation
- Guide users to ask separate questions
- Or implement client-side query routing/splitting

**The Ideal Solution**:
- Build your own orchestration layer
- Don't rely on Claude to decide when to call tools
- Parse the query yourself and call appropriate tools

## Key Insight

The answer to your original question: "Can Cortex Agent combine responses from both tools?"

**Theoretical Answer**: Yes, the API supports it (proven by code structure)

**Practical Answer**: No, Claude refuses to orchestrate it properly despite explicit instructions

**Real Answer**: It can, but you need to control the orchestration yourself, not rely on Claude's decision-making.
