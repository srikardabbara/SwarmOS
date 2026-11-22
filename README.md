# SwarmOS

> Testing and reliability for LangGraph multi-agent systems

## What is this?

SwarmOS helps you test whether your agents **collaborate correctly**—not just whether they produce good individual answers.

Building with LangGraph? Add SwarmOS to catch broken handoffs, context loss, and coordination failures before production.

## The Problem

Traditional testing doesn't catch multi-agent failures:

```
✓ Agent A works
✓ Agent B works  
✓ Agent C works
✗ But A→B handoff loses context    👈 SwarmOS finds this
```

You test agents. SwarmOS tests **COLLABORATION**.

## Quick Start

### Installation

```bash
pip install swarmos
```

### Add to Your LangGraph Workflow

Add 3 lines to your existing workflow:

```python
from swarmos import SwarmOSAdapter
from langgraph.graph import StateGraph

# Your existing workflow
graph = StateGraph(State)
# ... add nodes and edges ...

# Add SwarmOS instrumentation
adapter = SwarmOSAdapter()
app = graph.compile()

# Run with tracing
result = app.invoke(
    input_data,
    config={"callbacks": [adapter.callback_handler]}
)
```

### Define a Test

Create `tests/handoff_test.yaml`:

```yaml
name: "Support to billing handoff"
description: "Verify support agent hands off to billing agent correctly"

input:
  messages:
    - role: user
      content: "I want to cancel my subscription"

expectations:
  - type: agent_sequence
    agents: ["support_agent", "billing_agent"]
  
  - type: handoff_occurred
    from: "support_agent"
    to: "billing_agent"
  
  - type: context_preserved
    required_keys: ["user_id", "subscription_id"]
```

### Run Tests

```bash
swarmos test
```

### View Results

```bash
swarmos dashboard
```

Then open your browser to see the interactive visualization.

## Why SwarmOS?

### What SwarmOS Catches

**Broken Handoffs**
- Agent A declares handoff but Agent B never executes

**Context Loss**
- Critical state keys disappear between agent transitions

**Message Schema Violations**
- Downstream agents receive malformed data

**Tool Call Failures**
- Agents skip required tool calls in multi-step workflows

**Coordination Loops**
- Agents get stuck passing control back and forth

## Features

- **🔍 Workflow Instrumentation**: Capture every agent invocation, message, and handoff
- **✅ Test Scenarios**: Define expectations in simple YAML
- **📊 Interactive Visualization**: See your agent workflow in real-time
- **🎯 Smart Validation**: Detect handoff failures, context loss, and coordination issues
- **⚡ Fast Setup**: 3 lines of code, 5-minute integration
- **🔗 LangGraph Native**: Built specifically for LangGraph workflows

## Documentation

- [Getting Started Guide](docs/getting-started.md)
- [Test Scenarios](docs/test-scenarios.md)
- [Validation Types](docs/validators.md)
- [CLI Reference](docs/cli.md)
- [API Documentation](docs/api.md)

## Examples

Check out [`examples/`](examples/) for complete working examples:

- **Research Workflow**: Planner → Researcher → Writer
- **Customer Support**: Support → Billing → Resolution
- **Code Review**: Analyzer → Reviewer → Approver

## Development

### Setup

```bash
git clone https://github.com/swarmos/swarmos.git
cd swarmos
pip install -e ".[dev,backend]"
```

### Run Tests

```bash
pytest
```

### Start Backend (for dashboard)

```bash
cd backend
uvicorn api.main:app --reload
```

### Start Frontend (for dashboard)

```bash
cd frontend
npm install
npm run dev
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Developer's LangGraph Workflow                 │
│  ┌──────┐    ┌──────┐    ┌──────┐             │
│  │Agent │───→│Agent │───→│Agent │             │
│  │  A   │    │  B   │    │  C   │             │
│  └──┬───┘    └──┬───┘    └──┬───┘             │
│     │            │            │                 │
│     └────────────┴────────────┘                 │
│                  │                              │
│         SwarmOSAdapter                          │
│         (captures events)                       │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │ SwarmOS Backend  │
        │   (FastAPI)      │
        │                  │
        │ - Event Storage  │
        │ - Test Runner    │
        │ - Validators     │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │ SwarmOS Dashboard│
        │  (React + Vercel)│
        │                  │
        │ - Workflow Graph │
        │ - Test Results   │
        │ - Trace Timeline │
        └──────────────────┘
```

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- 📧 Email: support@swarmos.dev
- 💬 Discord: [Join our community](https://discord.gg/swarmos)
- 🐛 Issues: [GitHub Issues](https://github.com/swarmos/swarmos/issues)

---

**Built for LangGraph developers who want their multi-agent systems to actually work in production.**
