# Troubleshooting: Both Tools Not Being Called

## The Issue You're Seeing

**Query:** "What is the refund policy and how many orders were placed in 2025?"

**Current Output:**
- ✅ Refund policy information (from FAQ Search)
- ❌ "I don't have information about orders" (Sales Analyst not called)

## Why This Is Happening

The response shows that **only one tool is being called** instead of both. This could be due to:

1. **Orchestration Mode** - Make sure "Client-Side (Reliable)" is selected
2. **Keyword Detection** - The query should trigger both tools
3. **API Responses** - Both API calls need to succeed

## Quick Fixes

### Fix 1: Verify Orchestration Mode

**Check the sidebar:**
- ✅ Should be: **"Client-Side (Reliable)"** (selected)
- ❌ Not: "LLM-Based (Experimental)"

The LLM-based mode will fail to call both tools (as we discovered).

### Fix 2: Enable Debug Mode Temporarily

1. Check the **"Debug Mode"** checkbox in sidebar
2. Ask the same query again
3. You should see:
   ```
   🎯 Fetching policy information and data analytics...
   ✅ Retrieved information from both sources
   ```

If you DON'T see this, the orchestration isn't working.

### Fix 3: Test the Query Intent Detection

The query "what is the refund policy and how many orders were placed in 2025?" should trigger:
- **refund** → `search_keywords` → needs_search = True
- **how many** → `analyst_keywords` → needs_analyst = True
- **2025** → `analyst_keywords` → needs_analyst = True
- **orders** → `analyst_keywords` → needs_analyst = True

So `needs_both = True` ✅

## Expected Behavior

### With Client-Side Orchestration (Correct)

**Step 1:** Query analysis detects both keywords
- Found "refund policy" → needs FAQ search
- Found "how many" + "orders" + "2025" → needs data analysis
- Conclusion: needs_both = True

**Step 2:** Call FAQ Search
- Request sent with `tool_filter='search_only'`
- Returns: Refund policy information

**Step 3:** Call Sales Analyst
- Request sent with `tool_filter='analyst_only'`
- Returns: Order count + SQL query

**Step 4:** Combine results
- Policy text + Order count text
- Show combined response

### With LLM-Based Orchestration (Broken)

**Step 1:** Send query with both tools available

**Step 2:** LLM calls FAQ Search
- Returns: Refund policy information

**Step 3:** LLM decides NOT to call Sales Analyst
- Says: "I don't have information..."
- **This is the bug we're avoiding!**

## Verification Steps

### Step 1: Check Current Settings

Look at the sidebar and confirm:
```
Orchestration Mode: Client-Side (Reliable) ✓
Debug Mode: [X] (checked)
Model: claude-sonnet-4-5
```

### Step 2: Test Query

Ask: "What is the refund policy and how many orders were placed in 2025?"

### Step 3: Look for These Messages

**If working correctly:**
```
🎯 Fetching policy information and data analytics...
✅ Retrieved information from both sources

[Refund policy answer]
[Order count answer]
[SQL query section]
```

**If NOT working:**
```
[Only refund policy answer]
[No order count]
[No SQL query]
```

## Manual Override Test

Try this query format that makes it very explicit:

```
I need two things:
1. What is the refund policy?
2. How many orders were placed in 2025?
```

This should definitely trigger `needs_both = True`.

## Check the Keyword Lists

The app detects intent based on these keywords:

### FAQ/Policy Keywords (triggers Faq Search):
- policy, procedure, how do i, how to, what is the process
- refund, return, shipping, warranty, faq, guidelines
- rules, documentation, manual, instructions

### Data/Analytics Keywords (triggers Sales Analyst):
- how many, count, total, number of, sum, average
- orders, revenue, sales, metrics, statistics, data
- 2024, 2025, last year, this year, yesterday, today
- last month, last week, quarter, ytd

**Your query contains:**
- ✅ "refund" → FAQ keyword
- ✅ "policy" → FAQ keyword
- ✅ "how many" → Analytics keyword
- ✅ "orders" → Analytics keyword
- ✅ "2025" → Analytics keyword

So it **should** trigger both tools!

## Debug the Flow

### Turn on Debug Mode and check for these indicators:

**1. Query Intent Detection:**
Should show internally: `needs_both = True`

**2. First API Call:**
Should call with `tool_filter='search_only'`

**3. Second API Call:**
Should call with `tool_filter='analyst_only'`

**4. Result Combination:**
Should combine both text responses

## If It Still Doesn't Work

### Option 1: Check API Responses

The issue might be:
- First API call succeeds (FAQ)
- Second API call fails silently (Sales Analyst)

**Solution:** Error handling has been added to catch this.

### Option 2: Check Semantic Model

The Sales Analyst tool requires a valid semantic model:
```
@CORTEX_AGENTS.CORTEX_AGENTS_SALES.Cortex_Analyst_Stage/CORTEX_AGENT_SALES.yaml
```

**Verify:**
1. The file exists
2. The path is correct
3. Your role has access to it

### Option 3: Test Each Tool Separately

**Test FAQ Search only:**
```
What is the refund policy?
```
Should work and show policy.

**Test Sales Analyst only:**
```
How many orders were placed in 2025?
```
Should work and show count + SQL.

**If both work separately but not together:**
- The client-side orchestration has a bug
- Check the error messages in the app

## Expected Final Output

When working correctly, you should see:

```
Based on the provided information, refunds are processed within 
5-7 business days after the returned item is received and inspected.

According to the sales data, there were [X number] orders placed in 2025.

[SQL Query section showing the query used]
[Data table with results]
[Citations from FAQ documents]
```

## Quick Test Commands

### Test 1: FAQ Only
```
What is the refund policy?
```
Expected: Policy info, no SQL

### Test 2: Data Only
```
How many orders in 2025?
```
Expected: Count + SQL, no citations

### Test 3: Both (Your Query)
```
What is the refund policy and how many orders were placed in 2025?
```
Expected: Policy + Count + SQL + Citations

## Summary

✅ **Orchestration Mode:** Must be "Client-Side (Reliable)"  
✅ **Debug Mode:** Turn ON to see what's happening  
✅ **Query Keywords:** "refund policy" + "how many orders" + "2025" triggers both  
✅ **Expected Output:** Both policy and order count in the response  

**If you're still seeing "I don't have information about orders", the Sales Analyst API call is either failing or not being made.**

Turn on Debug Mode and look for error messages or missing API calls.
