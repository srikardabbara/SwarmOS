# SwarmOS

## What SwarmOS is

SwarmOS analyzes agent-to-agent communication inside a LangGraph run. It reads the trace and shows the information each agent handed to the next one: the task that was passed, the text the next agent never used, and a fact that changed along the way.

Use that to write more efficient instructions, drop messages that never affect the next step, and find the handoff where the output went wrong.

Run the site on your laptop, then follow the Instructions page to connect the agent.

## Run it on your laptop

You need Python 3.10 or newer, Node.js, and npm. Use two terminals, and leave both servers running.

### 1. Download the project

```bash
git clone https://github.com/srikardabbara/SwarmOS.git
cd SwarmOS
```

### 2. Install SwarmOS from this folder

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[backend]"
```

On Windows, activate the environment with `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

### 3. Start the backend

In that same terminal:

```bash
cd backend
python -m uvicorn api.main:app --reload --port 8000
```

The API is at http://localhost:8000. The first run creates a local database in the `backend` folder.

### 4. Start the website

Open a second terminal, go back to the `SwarmOS` folder, and run:

```bash
cd frontend
npm install
npm run dev
```

The site is at http://localhost:3000.

### 5. Connect the agent

Open [http://localhost:3000/start](http://localhost:3000/start) and follow **Connect a project**. That page creates the SwarmOS project key and walks through the LangSmith key, the agent name or ID, and the command that reads the newest trace.

When that page shows `pip install swarmos`, skip that line. The virtual environment from step 2 already provides the `swarmos` command. In a terminal where that environment is active, paste the rest of the exports from the page, then run:

```bash
source .venv/bin/activate
swarmos langsmith
```

Run `source` from the `SwarmOS` folder. On Windows, use `.venv\Scripts\activate`. The command prints a link. Open it, or go back to Runs and open the new row.

## License

MIT. See [LICENSE](LICENSE).
