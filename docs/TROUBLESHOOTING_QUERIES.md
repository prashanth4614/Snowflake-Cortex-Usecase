# Troubleshooting: Agent Returns COUNT Instead of Detailed Results

## Problem Description

**User asks:** "List down the overall orders and the total amount of that order"

**Expected:** Table showing each order with its ID and total amount

**Got Instead:**
1. Message saying "no orders in database"
2. SQL query with `COUNT(*)` 
3. Result showing `Total Records: 5`

## Root Cause

The Cortex Analyst is interpreting your question in two ways:

1. **First interpretation:** Check if orders exist (validation query)
2. **Second interpretation:** Count total orders (aggregate query)

Neither interpretation matches your actual intent: **list individual orders with details**.

## Why This Happens

### Issue 1: Ambiguous Phrasing
The phrase "overall orders" can be interpreted as:
- ❌ "total number of orders" (COUNT)
- ✅ "all individual orders" (LIST)

### Issue 2: Analyst Being Too Cautious
Cortex Analyst sometimes runs validation queries first:
```sql
-- Validation query
SELECT COUNT(*) FROM orders WHERE 1=0;  -- Returns 0

-- Then says "no data" even though this was just a check
```

### Issue 3: Aggregate vs Detail Confusion
"Total amount" can mean:
- ❌ Sum of all order amounts (SUM)
- ✅ The amount field for each order (DETAIL)

## Solutions

### ✅ Solution 1: Use More Specific Language

**Instead of:**
> "List down the overall orders and the total amount of that order"

**Use:**
> "Show me a table of all orders with their order_id and total_amount"

**Or:**
> "Display each order's ID and amount in a list"

**Or:**
> "What are the individual orders with their order IDs and amounts?"

### Key Phrases to Use

| Want to see... | Good phrases | Avoid |
|---------------|-------------|--------|
| Individual rows | "Show me each...", "List all...", "Display individual..." | "overall", "total count" |
| Detail fields | "with their [field_name]", "including [field]" | "total", "sum" |
| Specific columns | "order_id and total_amount", "columns: id, amount" | Vague references |

### ✅ Solution 2: Update Agent Instructions

Add response instructions to your agent configuration:

```sql
-- In Snowsight or SQL
ALTER AGENT CORTEX_SALES_AGENT
SET RESPONSE_INSTRUCTIONS = '
When users ask to "list" or "show" data, return individual rows with specific columns.
Do not return COUNT(*) unless explicitly asked for counts or totals.
For listing queries, return at least these columns: ID, key metrics, and dates.
Limit to 100 rows by default unless specified otherwise.
';
```

### ✅ Solution 3: Enhance Semantic Model

Add better descriptions and examples to `CORTEX_AGENT_SALES.yaml`:

```yaml
tables:
  - name: ORDERS
    base_table:
      database: CORTEX_AGENTS
      schema: CORTEX_AGENTS_SALES
      table: ORDERS
    description: |
      Contains all customer orders with their details.
      Use this table when users ask to "list", "show", or "display" orders.
      Return individual rows with order_id, total_amount, and other details.
    dimensions:
      - name: ORDER_ID
        description: |
          Unique identifier for each order. 
          Always include this when listing orders.
        expr: ORDER_ID
        data_type: VARCHAR
        
      - name: TOTAL_AMOUNT
        description: |
          The total monetary value of the order.
          This is the individual order amount, not a sum.
        expr: TOTAL_AMOUNT
        data_type: NUMBER
    
    # Add verified queries for common patterns
    verified_queries:
      - name: list_all_orders
        question: "Show me all orders"
        sql: |
          SELECT 
            order_id,
            total_amount,
            order_date,
            order_status
          FROM CORTEX_AGENTS.CORTEX_AGENTS_SALES.ORDERS
          ORDER BY order_date DESC
          LIMIT 100
      
      - name: list_orders_with_amounts
        question: "List orders with their amounts"
        sql: |
          SELECT 
            order_id,
            total_amount,
            customer_id,
            order_date
          FROM CORTEX_AGENTS.CORTEX_AGENTS_SALES.ORDERS
          ORDER BY total_amount DESC
          LIMIT 100
```

### ✅ Solution 4: Use Follow-up Questions

If you get a COUNT result, immediately ask:
> "No, show me the individual orders as a table with order_id and total_amount columns"

The thread context will help the agent understand the correction.

### ✅ Solution 5: Add Orchestration Instructions

Update agent orchestration to prefer detail over aggregates:

```sql
ALTER AGENT CORTEX_SALES_AGENT
SET ORCHESTRATION_INSTRUCTIONS = '
For Cortex Analyst queries:
- When users say "list", "show", or "display", return individual rows
- When users say "count", "total", or "sum", return aggregates
- Default to showing detail rows with LIMIT 100 unless aggregation is clearly requested
- Always include ID columns when listing data
';
```

## Example Queries That Work Well

### ✅ Good Queries (Get Detail Rows)

```
"Show me the first 10 orders with their IDs and amounts"
"Display all orders in a table format with order_id, total_amount, and date"
"What are the individual orders? Include order ID and amount"
"List each order showing the order ID and how much it was for"
"Give me a table of orders with columns: order_id, total_amount"
```

### ❌ Problematic Queries (May Get Aggregates)

```
"What are the overall orders?"  ← Too vague
"Show me the total orders"      ← "total" suggests COUNT
"List the orders and amounts"   ← Ambiguous phrasing
```

## Testing Your Fix

Try these queries in sequence:

**Test 1: Explicit listing**
```
"Show me all orders as a table with order_id and total_amount"
```
**Expected:** Table with individual rows

**Test 2: With limit**
```
"Display the first 5 orders with their ID and amount"
```
**Expected:** Exactly 5 rows

**Test 3: With sorting**
```
"List all orders sorted by total_amount descending, showing order_id and amount"
```
**Expected:** Individual rows sorted by amount

**Test 4: Follow-up correction**
```
First: "Show me the orders"
If COUNT: "No, I want individual rows, not a count"
```
**Expected:** Agent corrects to show rows

## Quick Reference

### Query Intent Mapping

| User Intent | Correct SQL | Wrong SQL |
|-------------|-------------|-----------|
| List orders | `SELECT order_id, total_amount FROM orders` | `SELECT COUNT(*) FROM orders` |
| Count orders | `SELECT COUNT(*) FROM orders` | `SELECT order_id FROM orders` |
| Sum amounts | `SELECT SUM(total_amount) FROM orders` | `SELECT total_amount FROM orders` |
| Individual amounts | `SELECT order_id, total_amount FROM orders` | `SELECT SUM(total_amount) FROM orders` |

### Language Patterns

**For Detail Rows:**
- "Show me **each** order..."
- "**List all** orders..."
- "Display **individual** orders..."
- "What are the **specific** orders..."
- "Give me a **table** of orders..."

**For Aggregates:**
- "How **many** orders..."
- "What's the **total** amount..."
- "**Count** the orders..."
- "**Sum** of all orders..."

## Advanced: Custom Instructions in Query

You can include instructions directly in your query:

```
"Show me a table with these exact columns: order_id and total_amount. 
Return individual rows, not counts. Limit to 20 rows."
```

This explicit instruction helps the agent understand exactly what you want.

## Debugging Steps

If you continue getting COUNT instead of rows:

1. **Check semantic model** - Verify verified_queries are defined
2. **Enable debug mode** - See the SQL before it executes
3. **Check agent instructions** - Verify orchestration and response instructions
4. **Try explicit column names** - "show columns order_id and total_amount"
5. **Use follow-up** - Correct the agent in the next message

## Summary

**Problem:** Vague phrases like "overall orders" trigger COUNT instead of detail rows

**Solution:** Use explicit phrases like "show each order" or "list all orders as a table"

**Best Practice:** Include column names in your question: "with order_id and total_amount"

**Quick Fix:** If you get COUNT, immediately say "No, show individual rows not a count"

---

**Pro Tip:** The phrase "**Show me a table of...**" is one of the most reliable patterns for getting individual rows rather than aggregates!
