# Getting Started with SwarmOS

This guide will help you get SwarmOS up and running in 5 minutes.

## Prerequisites

- Python 3.10+ (for SDK and backend)
- Node.js 18+ (for dashboard, optional)
- A LangGraph multi-agent workflow

## Quick Start

### 1. Install SwarmOS

```bash
# Install the SDK
pip install -e .

# Optional: Install backend dependencies
pip install -e ".[backend]"
```

### 2. Instrument Your Workflow

Add 3 lines to your existing LangGraph workflow:

```python
from swarmos import SwarmOSAdapter
from langgraph.graph import StateGraph

# Your existing workflow
graph = StateGraph(YourState)
# ... add nodes and edges ...

# Add SwarmOS instrumentation
adapter = SwarmOSAdapter(workflow_id="my-workflow")
app = graph.compile()

# Run with tracing
result = app.invoke(
    your_input,
    config={"callbacks": [adapter.callback_handler]}
)

# See what happened
adapter.print_summary()
```

### 3. Run the Example

```bash
# Run the included example
python examples/simple_workflow.py
```

You should see:
- Agent execution traced
- Event capture working
- Handoff detection
- Summary printed to console

### 4. Create Your First Test

Create `tests/my_test.yaml`:

```yaml
name: "My first test"
description: "Test agent collaboration"

input:
  messages:
    - role: user
      content: "Test input"

expectations:
  - type: agent_sequence
    agents: ["planner", "researcher", "writer"]
  
  - type: handoff_occurred
    from: "planner"
    to: "researcher"
```

### 5. Run Tests with YAML

```python
from swarmos.runner import TestExecutor, load_scenario

# Load scenario
scenario = load_scenario("tests/my_test.yaml")

# Run test
executor = TestExecutor()
result = executor.run_scenario(scenario, your_workflow_function)

# View results
executor.print_result(result)
```

See `examples/test_with_yaml.py` for a complete example.

### 6. Start the Dashboard (Optional)

```bash
# Start backend API
cd backend
uvicorn api.main:app --reload

# In another terminal, start frontend
cd frontend
npm install
npm run dev
```

Then:
1. Configure your adapter to send to backend:
   ```python
   adapter = SwarmOSAdapter(
       workflow_id="my-workflow",
       api_url="http://localhost:8000",
       auto_send=True
   )
   ```

2. Run your workflow

3. Open http://localhost:3000 to see the dashboard

## What You Get

### ✅ Instant Feedback
See exactly which agents ran, in what order, with what data.

### ✅ Collaboration Validation
Catch broken handoffs, context loss, and coordination failures.

### ✅ Visual Workflow Graph
Interactive visualization of your agent workflow.

### ✅ Automated Testing
Define expectations in YAML and run them automatically.

### ✅ Zero Config Dashboard
See results in a beautiful web UI with no setup.

## Common Use Cases

### Catching Broken Handoffs

```yaml
expectations:
  - type: handoff_occurred
    from: "agent_a"
    to: "agent_b"
```

Detects when Agent A declares a handoff but Agent B never receives it.

### Verifying Context Preservation

```yaml
expectations:
  - type: context_preserved
    after_handoff:
      from: "researcher"
      to: "writer"
    required_keys: ["research_findings", "source_urls"]
```

Ensures critical data isn't lost during agent transitions.

### Checking Agent Sequence

```yaml
expectations:
  - type: agent_sequence
    agents: ["planner", "researcher", "writer"]
```

Validates agents execute in the correct order.

## Next Steps

1. **Read the docs**: Check `docs/` for detailed guides
2. **Try validators**: See `swarmos/validators/` for all validation types
3. **Customize tests**: Create complex scenarios in YAML
4. **Deploy dashboard**: Host on Vercel (frontend) + Render (backend) for free
5. **Integrate CI/CD**: Run tests in your pipeline

## Troubleshooting

**Q: No events captured**
- Make sure you're passing the callback: `config={"callbacks": [adapter.callback_handler]}`
- Check that your workflow is actually executing
- Try the included example first

**Q: Handoffs not detected**
- LangGraph handoffs use `Command(goto="agent_name")`
- SwarmOS detects these automatically
- Check if your workflow uses a different pattern

**Q: Dashboard shows no traces**
- Ensure backend is running: `uvicorn api.main:app --reload`
- Set `auto_send=True` in your adapter
- Check console for error messages

## Learn More

- [Full Documentation](docs/)
- [API Reference](docs/api.md)
- [Validation Types](docs/validators.md)
- [Example Workflows](examples/)
- [Deployment Guide](docs/deployment.md)

## Get Help

- 🐛 [Report a bug](https://github.com/swarmos/swarmos/issues)
- 💬 [Ask a question](https://github.com/swarmos/swarmos/discussions)
- 📧 Email: support@swarmos.dev

---

**Ready to test your multi-agent system?** Try the examples and see what SwarmOS catches!
