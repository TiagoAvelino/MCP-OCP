# Client-GPT.py Code Walkthrough

This document explains each function and method in `client-gpt.py` to help you understand how the MCP client works.

---

## 📋 Table of Contents

1. [Imports and Constants](#imports-and-constants)
2. [Data Structures](#data-structures)
3. [Helper Functions](#helper-functions)
4. [LLM Decision Function](#llm-decision-function)
5. [Main Agent Loop](#main-agent-loop)

---

## 🔧 Imports and Constants

### Lines 1-17: Setup

```python
from fastmcp import Client
from openai import OpenAI
```

**Purpose:** Import the MCP client library and OpenAI SDK (works with any OpenAI-compatible API).

**Constants (Lines 14-17):**

- `TOOL_VERIFY_STATUS`: Name of the tool to check cluster status
- `TOOL_LIST_NODES`: Name of the tool to list nodes
- `TOOL_UPGRADE`: Name of the tool to upgrade OpenShift

**Why:** These constants prevent typos and make it easy to change tool names in one place.

---

## 📦 Data Structures

### Lines 23-28: `Decision` Class

```python
@dataclass
class Decision:
    tool_name: Optional[str]    # Which tool to call (None = stop)
    args: Dict[str, Any]        # Arguments for the tool
    reason: str                 # Why this decision was made
    stop: bool = False          # Should we stop the loop?
```

**Purpose:** A data structure to hold the LLM's decision about what to do next.

**Fields:**

- `tool_name`: The MCP tool the LLM wants to call (e.g., "verificar_status_sistema")
- `args`: Parameters to pass to that tool (e.g., `{"componente": "cluster"}`)
- `reason`: The LLM's explanation for choosing this action
- `stop`: If `True`, the agent should stop (e.g., cluster is failing)

**Example:**

```python
Decision(
    tool_name="verificar_status_sistema",
    args={"componente": "cluster"},
    reason="Need to check cluster health before proceeding",
    stop=False
)
```

---

## 🛠️ Helper Functions

### Lines 34-50: `extract_text()`

```python
def extract_text(result: Any) -> str:
```

**Purpose:** Extracts readable text from MCP tool responses.

**What it does:**

1. Checks if result is `None` → returns empty string
2. Looks for `.content` attribute (FastMCP format)
3. If content is a list, extracts text from first item
4. Falls back to converting the whole result to string

**Why needed:** MCP tools return structured objects, but we need plain text to show the user and send to the LLM.

**Example:**

```python
# MCP returns: ToolResult(content=[TextContent(text="Cluster is healthy")])
# extract_text() returns: "Cluster is healthy"
```

---

### Lines 58-89: `parse_json_object()`

```python
def parse_json_object(text: str) -> Dict[str, Any]:
```

**Purpose:** Parses JSON from LLM output, even if it's wrapped in markdown or has extra text.

**What it does:**

1. Removes markdown code fences (`json ... `)
2. Tries to parse the cleaned text as JSON
3. If that fails, finds the first `{...}` block and parses that
4. Validates it's a dictionary (not a list or string)

**Why needed:** LLMs sometimes wrap JSON in markdown or add explanatory text. This function handles all cases.

**Example inputs it handles:**

````python
# Pure JSON:
'{"tool_name": "test", "args": {}}'

# With markdown:
'```json\n{"tool_name": "test"}\n```'

# With extra text:
'Here is the decision: {"tool_name": "test"}'
````

---

### Lines 95-128: `normalize_tools()`

```python
def normalize_tools(tools: Any) -> List[Dict[str, Any]]:
```

**Purpose:** Converts MCP tool list into a standardized format.

**What it does:**

1. Handles `None` → returns empty list
2. Handles dict with "tools" key → extracts the list
3. Handles list of tools → processes each tool
4. Extracts `name`, `description`, and `inputSchema` from each tool
5. Filters out tools without names

**Why needed:** MCP can return tools in different formats. This normalizes them to a consistent structure.

**Input examples:**

```python
# Format 1: Direct list
[{"name": "tool1", "description": "..."}, ...]

# Format 2: Wrapped in dict
{"tools": [{"name": "tool1", ...}, ...]}

# Format 3: Object attributes
[ToolObject(name="tool1", description="..."), ...]
```

**Output:** Always a list of dicts with `name`, `description`, `inputSchema`.

---

## 🤖 LLM Decision Function

### Lines 134-235: `llm_decide_next_action()`

```python
def llm_decide_next_action(
    *,
    openai_client: OpenAI,
    model: str,
    objective: str,
    observed_state: Dict[str, str],
    tools_catalog: List[Dict[str, Any]],
    allowed_tools: List[str],
    write_tools: List[str],
) -> Decision:
```

**Purpose:** Asks the LLM to decide what action to take next.

**Parameters:**

- `openai_client`: The OpenAI client (works with any compatible API)
- `model`: Model name (e.g., "llama-32-3b-instruct")
- `objective`: What we're trying to achieve
- `observed_state`: Current cluster status (from previous tool calls)
- `tools_catalog`: List of available MCP tools
- `allowed_tools`: Which tools the LLM is allowed to use (safety)
- `write_tools`: Which tools can modify the cluster (need approval)

**Step-by-step:**

1. **Filter tools (Lines 152-157):**

   - Creates a brief list with only `name` and `description`
   - Only includes tools from `allowed_tools` (safety filter)

2. **Build prompt (Lines 159-184):**

   - Creates system instructions telling the LLM its role
   - Includes the objective
   - Lists allowed tools and write tools
   - Specifies the exact JSON format required

3. **Call LLM API (Lines 192-200):**

   - Uses `chat.completions.create()` (standard OpenAI API)
   - Sends system message (instructions) and user message (current state + tools)
   - Temperature 0.7 for some creativity but still focused

4. **Extract response (Lines 204-210):**

   - Gets text from `resp.choices[0].message.content`
   - Validates it's not empty

5. **Parse JSON (Line 212):**

   - Uses `parse_json_object()` to extract the decision

6. **Validate and extract fields (Lines 214-224):**

   - Gets `tool_name`, `args`, `reason`, `stop` from parsed JSON
   - Validates types (tool_name must be string or null, args must be dict)

7. **Safety check (Lines 226-233):**

   - **CRITICAL:** If LLM suggests a tool not in `allowed_tools`, returns a stop decision
   - This prevents the LLM from calling unauthorized tools

8. **Return Decision (Line 235):**
   - Returns a `Decision` object with all the information

**Why this design:**

- Safety: Hardcoded allowlist prevents unauthorized tool calls
- Flexibility: LLM can reason about which tool to use
- Transparency: Returns reason for debugging

---

## 🔄 Main Agent Loop

### Lines 241-341: `main()`

**Purpose:** The main orchestration function that runs the agent loop.

**Flow:**

#### 1. Parse Arguments (Lines 242-251)

```python
parser = argparse.ArgumentParser(...)
```

- Sets up command-line arguments
- Gets server path, model, objective, max steps, etc.

#### 2. Setup API Client (Lines 253-264)

```python
api_key = args.api_key or os.getenv("OPENAI_API_KEY") or None
api_base = args.api_base or os.getenv("OPENAI_BASE_URL")
oai = OpenAI(api_key=api_key, base_url=api_base)
```

- Gets API key and base URL from args or environment
- Creates OpenAI client (works with any compatible provider)

#### 3. Define Tool Lists (Lines 266-269)

```python
READ_TOOLS = [TOOL_VERIFY_STATUS, TOOL_LIST_NODES]
WRITE_TOOLS = [TOOL_UPGRADE]
ALLOWED_TOOLS = READ_TOOLS + WRITE_TOOLS
```

- Separates read-only tools from write tools
- Combines into allowed list

#### 4. Connect to MCP Server (Lines 271-276)

```python
async with Client(args.server_path) as client:
    await client.ping()
    tools_raw = await client.list_tools()
    tools_catalog = normalize_tools(tools_raw)
```

- Connects to MCP server (runs `server-gpt.py` as subprocess)
- Pings to verify connection
- Lists available tools and normalizes them

#### 5. Main Loop (Lines 278-341)

For each step (up to `max_steps`):

**A. OBSERVE (Lines 281-299)**

```python
observed_state: Dict[str, str] = {}
res_cluster = await client.call_tool(TOOL_VERIFY_STATUS, {"componente": "cluster"})
observed_state["cluster"] = extract_text(res_cluster)
res_nodes = await client.call_tool(TOOL_LIST_NODES, {})
observed_state["nodes"] = extract_text(res_nodes)
```

- Calls read-only tools to gather current state
- Stores results in `observed_state` dict
- This gives the LLM context about the cluster

**B. DECIDE (Lines 301-314)**

```python
decision = llm_decide_next_action(
    openai_client=oai,
    model=args.model,
    objective=args.objective,
    observed_state=observed_state,
    tools_catalog=tools_catalog,
    allowed_tools=ALLOWED_TOOLS,
    write_tools=WRITE_TOOLS,
)
```

- Calls `llm_decide_next_action()` to get LLM's decision
- LLM analyzes observed state and chooses next tool

**C. Check Stop Condition (Lines 319-321)**

```python
if decision.stop or not decision.tool_name:
    print(f"\nStopping. Reason: {decision.reason}")
    return
```

- If LLM says to stop or no tool chosen, exit loop

**D. Safety Gate (Lines 323-329)**

```python
if decision.tool_name in WRITE_TOOLS and not args.approve:
    print("\nThis action is a WRITE operation and requires approval.")
    return
```

- **CRITICAL SAFETY:** If LLM wants to use a write tool (like upgrade) and `--approve` flag not set, stop
- Prevents accidental cluster modifications

**E. ACT (Lines 331-339)**

```python
result = await client.call_tool(decision.tool_name, decision.args)
print("Tool result:")
print(extract_text(result))
```

- Executes the tool the LLM chose
- Prints the result

**F. Sleep (Line 341)**

```python
await asyncio.sleep(args.sleep)
```

- Waits before next iteration (gives cluster time to update)

---

## 🔄 Overall Flow Diagram

```
START
  │
  ├─> Parse arguments
  ├─> Setup OpenAI client
  ├─> Connect to MCP server
  ├─> Get available tools
  │
  └─> LOOP (for each step):
      │
      ├─> OBSERVE: Call read tools → Get cluster state
      │
      ├─> DECIDE: Ask LLM → Get next action
      │
      ├─> Check: Should we stop? → YES → EXIT
      │
      ├─> Check: Is it a write tool? → YES → Need --approve? → NO → EXIT
      │
      ├─> ACT: Execute the tool
      │
      └─> Sleep → Next iteration
```

---

## 🔐 Safety Features

1. **Tool Allowlist:** LLM can only use tools in `ALLOWED_TOOLS`
2. **Write Tool Protection:** Write tools require `--approve` flag
3. **Hardcoded Safety Check:** Even if LLM suggests unauthorized tool, code rejects it
4. **Error Handling:** Try/except blocks prevent crashes

---

## 💡 Key Design Decisions

1. **Why separate OBSERVE/DECIDE/ACT?**

   - Clear separation of concerns
   - Makes it easy to debug what the LLM is thinking
   - Allows for future improvements (e.g., caching observations)

2. **Why use constants for tool names?**

   - Prevents typos
   - Easy to update if tool names change
   - Makes code more maintainable

3. **Why normalize tools?**

   - MCP can return tools in different formats
   - Normalization makes rest of code simpler
   - Handles edge cases gracefully

4. **Why extract text from results?**
   - MCP returns structured objects
   - LLM needs plain text
   - Users want readable output

---

## 🧪 Testing Tips

- **Test with `--max-steps 1`:** See one iteration
- **Test without `--approve`:** Verify safety gate works
- **Test with invalid tool:** Verify allowlist enforcement
- **Check logs:** Each step prints what it's doing

---

## 📝 Summary

The client implements an **agentic loop**:

1. **Observes** the current state (reads cluster info)
2. **Decides** what to do next (asks LLM)
3. **Acts** on the decision (calls MCP tool)
4. **Repeats** until objective met or stopped

All with **safety gates** to prevent unauthorized actions.

---

## 🎭 How the Client Works: The Complete Orchestration Process

Here's how the entire orchestration process works from start to finish:

### 🚀 Initialization Phase

**1. Client Starts**

- You run the script: `python client-gpt.py server-gpt.py --api-base https://your-llm-endpoint.com`
- The script parses command-line arguments and sets up configuration

**2. Connect to LLM Provider**

- The client initializes the OpenAI SDK (works with any OpenAI-compatible API)
- It connects to your LLM endpoint (e.g., `https://llama-32-3b-instruct-my-first-model.apps.ocp...`)
- If successful, the client is ready to send messages to the LLM

**3. Connect to MCP Server**

- The client launches your MCP server (`server-gpt.py`) as a subprocess
- It establishes a communication channel using stdio (standard input/output)
- The client sends a ping to verify the connection works
- It requests the list of available tools from the server

### 🔄 Main Orchestration Loop

Once both connections are established, the orchestration loop begins:

**Step 1: OBSERVE - Gather Current State**

The client needs to understand the current state of your OpenShift cluster before making decisions. It does this by:

- **Invoking MCP tools** to collect information:
  - Calls `verificar_status_sistema` with `{"componente": "cluster"}` → Gets cluster version, health status
  - Calls `listar_nodes` → Gets list of all nodes and their status
- **Storing the results** in an `observed_state` dictionary
- This gives the LLM a complete picture of what's happening in the cluster

**Step 2: DECIDE - Ask LLM What to Do Next**

With the current state in hand, the client now asks the LLM to make a decision. This happens in two parts:

**A. The FIRST Message: System Instructions (Role Definition)**

Before anything else, the client sends a **system message** that defines the LLM's role and rules. This is the **first thing** the LLM receives:

```python
{
  "role": "system",
  "content": """
You are an operations coordinator for an OpenShift cluster.
Your job: choose the next SINGLE MCP tool call to help achieve the objective.

Objective:
- Assess cluster health and suggest safe next steps.

You MUST follow these rules:
1) You may ONLY choose a tool from this allowlist:
['verificar_status_sistema', 'listar_nodes', 'iniciar_upgrade_openshift']

2) If you choose one of these write tools, you MUST still choose it, but mark it clearly:
write_tools = ['iniciar_upgrade_openshift']

3) If the observed state indicates the cluster is failing/degraded, set stop=true and tool_name=null.

4) Output MUST be a single JSON object with EXACT keys:
{
  "tool_name": string|null,
  "args": object,
  "reason": string,
  "stop": boolean
}

No markdown. No code fences. No extra text.
"""
}
```

**This system message:**

- Tells the LLM its role: "operations coordinator for OpenShift"
- Explains its job: choose the next tool to call
- Provides the objective (from `--objective` argument)
- Lists allowed tools (safety constraint)
- Defines write tools that need approval
- Specifies the exact JSON format required for the response

**B. The SECOND Message: Current State and Available Tools**

After the system message, the client sends a **user message** with the current situation:

```python
{
  "role": "user",
  "content": {
    "observed_state": {
      "cluster": "Current version: 4.12.0\nDesired version: 4.12.0\nAvailable: True | Progressing: False | Failing: False",
      "nodes": "- node1 | Ready=True | kubelet=1.28.0\n- node2 | Ready=True | kubelet=1.28.0"
    },
    "available_tools": [
      {
        "name": "verificar_status_sistema",
        "description": "Verifica o status de um componente do sistema. Útil antes de iniciar atualizações."
      },
      {
        "name": "listar_nodes",
        "description": "Lists cluster nodes with basic info (name, ready, kubelet version)."
      },
      {
        "name": "iniciar_upgrade_openshift",
        "description": "Starts an OpenShift cluster upgrade by setting ClusterVersion.spec.desiredUpdate."
      }
    ]
  }
}
```

**This user message contains:**

- `observed_state`: The current cluster status gathered from previous tool calls
  - `cluster`: Version, health status, update progress
  - `nodes`: List of nodes and their readiness status
- `available_tools`: List of tools the LLM can choose from (with descriptions)

**C. How the Client Asks the LLM**

The client uses the OpenAI `chat.completions.create()` API:

```python
resp = openai_client.chat.completions.create(
    model="llama-32-3b-instruct",
    messages=[
        {"role": "system", "content": developer_instructions},  # First message
        {"role": "user", "content": json.dumps(user_input)},     # Second message
    ],
    temperature=0.7,
)
```

**The LLM's Response:**

The LLM analyzes the situation and responds with a JSON object:

```json
{
  "tool_name": "verificar_status_sistema",
  "args": { "componente": "api" },
  "reason": "Cluster and nodes look healthy. Checking API status to ensure full system health before proceeding.",
  "stop": false
}
```

**What the LLM is doing:**

- Analyzing the observed state (cluster version, node status)
- Considering the objective (assess cluster health)
- Looking at available tools and their descriptions
- Deciding which tool would be most useful next
- Providing a reason for its choice
- Deciding if we should stop (e.g., if cluster is failing)

**Important Notes:**

1. **The system message is sent ONCE per conversation** - it defines the LLM's role and rules
2. **The user message is sent EVERY iteration** - it contains the updated observed state
3. **Each iteration is a fresh conversation** - the client doesn't maintain conversation history between steps
4. **The LLM only sees the current state** - it doesn't remember previous decisions (though the observed state includes results from previous tool calls)

### 📨 Message Flow Diagram

Here's exactly what gets sent to the LLM in each DECIDE step:

```
┌─────────────────────────────────────────────────────────────┐
│ CLIENT → LLM: Message 1 (SYSTEM - Role Definition)        │
├─────────────────────────────────────────────────────────────┤
│ Role: "system"                                              │
│ Content:                                                    │
│   "You are an operations coordinator for OpenShift..."     │
│   - Your role                                              │
│   - Your objective                                         │
│   - Allowed tools list                                     │
│   - Write tools list                                       │
│   - Output format requirements                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ CLIENT → LLM: Message 2 (USER - Current Situation)        │
├─────────────────────────────────────────────────────────────┤
│ Role: "user"                                                │
│ Content (JSON):                                             │
│   {                                                         │
│     "observed_state": {                                     │
│       "cluster": "Current version: 4.12.0...",             │
│       "nodes": "- node1 | Ready=True..."                   │
│     },                                                      │
│     "available_tools": [                                    │
│       {"name": "verificar_status_sistema", ...},            │
│       {"name": "listar_nodes", ...},                       │
│       {"name": "iniciar_upgrade_openshift", ...}           │
│     ]                                                       │
│   }                                                         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ LLM → CLIENT: Response (Decision)                           │
├─────────────────────────────────────────────────────────────┤
│ JSON Response:                                              │
│   {                                                         │
│     "tool_name": "verificar_status_sistema",               │
│     "args": {"componente": "api"},                         │
│     "reason": "Checking API status...",                    │
│     "stop": false                                           │
│   }                                                         │
└─────────────────────────────────────────────────────────────┘
```

### 🔍 What Happens in the First Iteration?

**The very first time** the client sends messages to the LLM:

1. **System message** (first message ever):

   - Defines the LLM as "operations coordinator"
   - Sets the objective (e.g., "Assess cluster health")
   - Lists all allowed tools
   - Explains the output format

2. **User message** (first user message):

   - Contains the `observed_state` from the OBSERVE step
   - This state was gathered by calling:
     - `verificar_status_sistema({"componente": "cluster"})` → cluster info
     - `listar_nodes({})` → nodes info
   - Contains the `available_tools` list with descriptions

3. **LLM responds** with its first decision:
   - Analyzes the initial cluster state
   - Chooses which tool to call next
   - Provides reasoning

**In subsequent iterations**, the same pattern repeats, but the `observed_state` contains updated information from previous tool executions.

**Step 3: VALIDATE - Safety Checks**

Before executing anything, the client performs safety checks:

- **Tool allowlist check**: Is the suggested tool in the allowed list? If not, stop immediately
- **Write operation check**: Is this a write tool (like upgrade)? If yes, is the `--approve` flag set? If not, stop and require approval
- **Stop condition check**: Did the LLM say to stop? If yes, exit the loop

**Step 4: ACT - Execute the Decision**

If all safety checks pass, the client executes the action:

- **Invokes the MCP tool** that the LLM chose
- For example: `call_tool("verificar_status_sistema", {"componente": "api"})`
- The MCP server receives the request, executes the Python function, and returns the result
- The client extracts the readable text from the result and displays it

**Step 5: REPEAT**

- The client waits a few seconds (configurable with `--sleep`)
- Then it goes back to **Step 1** (OBSERVE) to gather updated state
- The loop continues until:
  - Maximum steps reached (`--max-steps`)
  - LLM decides to stop
  - A safety check fails
  - An error occurs

### 📊 Complete Flow Example

Here's what happens in a typical run:

```
1. Client starts → Connects to LLM ✅ → Connects to MCP server ✅

2. Step 1: OBSERVE
   → Calls "verificar_status_sistema" → Returns: "Current version: 4.12.0, Status: Healthy"
   → Calls "listar_nodes" → Returns: "3 nodes, all Ready"
   → Stores in observed_state

3. Step 2: DECIDE
   → Sends to LLM: "Objective: Check cluster health. Current state: [cluster info, nodes info]"
   → LLM responds: {"tool_name": "verificar_status_sistema", "args": {"componente": "api"}, "reason": "Check API status"}
   → Client validates: ✅ Tool is allowed, ✅ Not a write tool

4. Step 3: ACT
   → Calls "verificar_status_sistema" with {"componente": "api"}
   → Returns: "API: Online. Latency low."
   → Displays result

5. Step 4: REPEAT
   → Waits 8 seconds
   → Goes back to Step 1 with updated state
```

### 🔐 Safety Throughout

At every step, safety is enforced:

- **Connection phase**: If LLM or MCP server can't connect, the client exits
- **Observation phase**: Errors are caught and reported, but don't crash the client
- **Decision phase**: LLM suggestions are validated against hardcoded allowlists
- **Action phase**: Write operations require explicit approval

### 🎯 The Big Picture

**The whole orchestration process works like this:**

1. **The client starts** and establishes connections to both the LLM provider and the MCP server
2. **After successful connections**, it begins sending messages to the LLM
3. **With those messages**, the LLM receives context about the cluster and available tools
4. **The LLM responds** with decisions about which functions to invoke
5. **The client invokes different MCP functions** (like `verificar_status_sistema`, `listar_nodes`) based on LLM decisions
6. **Those functions return cluster status** and other information
7. **The results are fed back to the LLM** in the next iteration, creating a feedback loop
8. **The process repeats** until the objective is achieved, a safety check fails, or maximum steps are reached

This creates an **intelligent agent** that can autonomously explore and interact with your OpenShift cluster, making decisions based on real-time information, while always respecting safety boundaries you've defined.
