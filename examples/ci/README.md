# Collaboration check

Copy `collaboration-check.yml` to `.github/workflows/collaboration-check.yml` in the repo that contains the LangGraph app.

The job fails the pull request when a YAML check fails: the agents ran out of order, a handoff never happened, or a required state key was gone at the end.

Repository secrets:

- `SWARMOS_API_URL` — hosted SwarmOS API, with no trailing path
- `SWARMOS_API_KEY` — project key from the dashboard

Change `--workflow myapp.workflow` to the module that defines `run_workflow(input_data, config)`. The YAML files live in `./tests`. Create the first one with `swarmos init`.

A finding that SwarmOS can edit safely prints `swarmos apply TRACE_ID FINDING_ID`. Run that in the app repo. The hosted API does not write to the repo.
