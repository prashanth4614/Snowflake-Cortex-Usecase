# Cortex Agent refuses to use multiple tools in one query - what am I doing wrong?

Hey everyone, I'm building a sales assistant in Snowflake using the Cortex Agent API and running into a weird issue. Hoping someone here has dealt with this before.

I've got two tools set up:
- Cortex Search (for searching through policy docs and FAQs)
- Cortex Analyst (for querying the sales database)

**Here's the problem:** When I ask a question that needs both tools, the agent only uses one and then just... stops. 

For example, if I ask: *"What is the refund policy and how many orders were placed in 2025?"*

The agent will search the docs and give me the refund policy (great!), but then says something like "I don't have information about the orders" or "Would you like me to query the database for you?" 

Like dude... yes! That's literally what I just asked you to do! Why are you asking permission??

**What I've tried so far:**

- Tested with claude-3-5-sonnet, claude-3-7-sonnet, and claude-sonnet-4-5 - all same behavior
- Added aggressive instructions like "You MUST use ALL relevant tools" and "Execute tools FIRST, explain later" - completely ignored
- Tried adding `tool_choice: "auto"` parameter - just got a 500 error (apparently not supported)

The weird thing is that single-tool queries work perfectly fine. Ask just about the policy? Works. Ask just about order counts? Works. Ask about both? Nope, only gets one.

**My current workaround** (which feels hacky but works):
I'm basically doing the agent's job for it - I split the query into parts, call each tool separately, and combine the results myself. It's 100% reliable but like... isn't the whole point of an agent to figure this stuff out on its own?

**My questions:**
1. Is this actually how it's supposed to work? Does the agent only call one tool per request by design?
2. Am I missing some configuration setting that enables multi-tool usage?
3. Has anyone here actually gotten Cortex Agent to use multiple tools in a single query?

I saw in the [Snowflake docs](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agent) that multi-tool support is definitely a thing, but I can't figure out how to make it happen.

Using Streamlit in Snowflake, hitting the `/api/v2/cortex/agent:run` endpoint.

Would really appreciate any pointers - feeling like I'm missing something obvious here!
