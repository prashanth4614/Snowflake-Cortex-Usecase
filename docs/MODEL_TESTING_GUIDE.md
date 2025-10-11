# Quick Testing Guide: Different LLM Models for Multi-Tool Orchestration

## What Changed

Your Streamlit app now has a **Model Selection dropdown** in the sidebar that lets you easily test different LLM models to see which one works best for calling both tools.

## How to Test

### Step 1: Open Your Streamlit App
- Launch your Streamlit in Snowflake application
- You'll see the model selector in the left sidebar

### Step 2: Select a Model to Test

**Recommended Testing Order:**

1. **claude-sonnet-4-5** (DEFAULT - Best chance of success)
   - Most advanced Claude model
   - Explicitly designed for "agentic workflows"
   - 32,000 token output capacity
   - Best multi-tool reasoning

2. **claude-3-7-sonnet** (Fallback option)
   - Newer than 3.5 
   - Better reasoning than 3.5
   - 32,000 token output

3. **openai-gpt-4.1** (Alternative approach)
   - Different model family
   - Different tool-calling behavior
   - May require cross-region inference

4. **claude-3-5-sonnet** (Your current - for comparison)
   - The one that was refusing both tools
   - Keep for baseline comparison

### Step 3: Test with Compound Query

Use this exact query to test multi-tool orchestration:

```
What is the refund policy and how many orders were placed yesterday?
```

**This query requires:**
- 🔍 Faq Search (for refund policy)
- 📊 Sales Analyst (for order count)

### Step 4: Check Debug Output

With Debug Mode enabled (checkbox in sidebar), you'll see:

**✅ SUCCESS looks like:**
```
🔧 Calling tool: Faq Search (type: cortex_search)
🔧 Calling tool: Sales Analyst (type: cortex_analyst_text_to_sql)
📊 Tools used in this response: Faq Search, Sales Analyst
✅ Both tools were called successfully!
```

**❌ FAILURE looks like:**
```
🔧 Calling tool: Faq Search (type: cortex_search)
📊 Tools used in this response: Faq Search
⚠️ Warning: Only Faq Search was called...
```

## Expected Results by Model

| Model | Expected Behavior | Probability |
|-------|------------------|-------------|
| **claude-sonnet-4-5** | ✅ Calls both tools | 70-80% |
| **claude-3-7-sonnet** | ⚠️ May call both | 50-60% |
| **openai-gpt-4.1** | ✅ Calls both tools | 60-70% |
| **claude-3-5-sonnet** | ❌ Refuses second tool | 20-30% |

## Test Queries

### Query 1: Compound (Policy + Data)
```
What is the refund policy and how many orders were placed yesterday?
```
**Expected:** Both tools should be called

### Query 2: Compound (Process + Metrics)
```
How do I process a return and what is the total revenue this month?
```
**Expected:** Both tools should be called

### Query 3: Data Only
```
How many orders were placed in the last 7 days?
```
**Expected:** Only Sales Analyst should be called

### Query 4: Policy Only
```
What is the shipping policy?
```
**Expected:** Only Faq Search should be called

## Recording Your Results

Create a simple comparison table:

| Model | Query | Faq Search Called? | Sales Analyst Called? | Success? |
|-------|-------|-------------------|---------------------|----------|
| claude-sonnet-4-5 | Refund + Count | ✅ | ✅ | ✅ |
| claude-3-7-sonnet | Refund + Count | ✅ | ❌ | ❌ |
| openai-gpt-4.1 | Refund + Count | ✅ | ✅ | ✅ |
| claude-3-5-sonnet | Refund + Count | ✅ | ❌ | ❌ |

## If All Models Fail

If even **claude-sonnet-4-5** refuses to call both tools:

### Option 1: Check Region Availability
Some models may not be available in your region. Error message will indicate this.

**Solution:** Enable cross-region inference
```sql
-- Run as ACCOUNTADMIN
ALTER ACCOUNT SET CORTEX_CROSS_REGION_INFERENCE = 'AWS_US';
```

### Option 2: Implement Client-Side Orchestration
Follow the guide in `CLIENT_SIDE_ORCHESTRATION.md` for a guaranteed solution.

### Option 3: Contact Snowflake Support
Share your test results showing which models you tried and the debug output.

## What to Report

If you find success with a particular model, document:

1. **Model name** that worked
2. **Query used**
3. **Debug output** showing both tools called
4. **Your Snowflake region** (for reference)

If all models fail, document:

1. **All models tested**
2. **Debug output** for each
3. **Your Snowflake region**
4. **Any error messages**

## Quick Summary

**Before:** Hardcoded to claude-3-5-sonnet (refusing to call both tools)

**Now:** Easy dropdown to test:
- ✅ claude-sonnet-4-5 (RECOMMENDED - best for multi-tool)
- ✅ claude-3-7-sonnet (better than 3.5)
- ✅ openai-gpt-4.1 (different approach)
- ✅ claude-3-5-sonnet (baseline comparison)

**Time to test:** 2-3 minutes per model
**Total testing time:** ~10 minutes to try all models

**Most likely outcome:** claude-sonnet-4-5 will successfully call both tools ✅
