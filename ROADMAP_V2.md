# Brakwater agent: Roadmap v2

Goal of v2: not a perfect product, but a realistic project where Babis uses, understands
and can explain the tools that AI / ML / MLOps job ads in the Netherlands ask for.

## Rules for every step (Claude Code, please follow)

1. One step at a time. Show a plan in 3-5 lines first and wait for OK.
2. Every tool must have a real job in the project. No tool just to have it.
3. Exact logic stays in plain, tested Python. The LLM only does language work.
4. Keys only from environment variables. Never in files, logs or git.
5. Nothing is sent to suppliers and nothing is written to the ERP.
6. Fake mode keeps working without a key. Real LLM runs are done by Babis.
7. Free / local first. Cloud only in the last step, with a budget alert, then destroy.
8. After each step: short summary in simple words, what changed per file,
   how to run it, and 2 questions to check Babis understood.
9. Each step ends with tests passing and its own commit.

## Step 0. Close version 1
- Fix: after a rebuild, reviews made on old decisions must be "outdated" and must not
  count ("Reviewed 17 of 21" bug). Test for exactly this case.
- README: what it does, screenshot, how to run, design decisions
  (LLM for language only, guardrails in code, human approval, fake mode).
- git tag v1.0
- Done when: tests pass, README exists, tag exists.

## Step 1. Eval set + MLflow
- eval/gold.csv: Babis labels the 34 LLM orders blind (expected action, ERP update,
  email needed). Template script without the LLM answers.
- eval/run_eval.py: accuracy, confusion table, list of wrong orders.
- Log every eval run to MLflow (local server in docker-compose): params (model,
  prompt version, mode), metrics (accuracy per action), the wrong-orders table as artifact.
- Done when: two runs (e.g. two prompt versions) can be compared in the MLflow UI.
- Asked by: Elsevier, DLL, Samba.

## Step 2. LangGraph
- Same pipeline as a graph: load orders -> triage -> decide (LLM) -> guardrails ->
  ERP proposal -> draft email -> human approval (interrupt) -> save.
- State as a typed object, checkpointer (SQLite) so an approval can resume later.
- The Streamlit UI approves through the graph interrupt.
- Done when: eval accuracy is the same as the plain version (no regression).
- Asked by: Schuberg Philis, Accenture, Elsevier.

## Step 3. LangSmith
- Trace every graph run: inputs/outputs per node, tokens, cost, latency, retries.
- Optional: compare with Langfuse (self-hosted) in a short note.
- Done when: one real run is visible as a trace, and cost per run is known.
- Asked by: Elsevier.

## Step 4. MCP
- Wrap the Keelson ERP API as an MCP server (tools: list_open_orders, get_order,
  get_supplier, get_project). Read-only.
- The agent uses the ERP through MCP. Claude Desktop can also ask it questions.
- Done when: the agent works through MCP, tests pass.
- Asked by: Elsevier.

## Step 5. RAG over supplier contracts
- Add a few fake supplier framework agreements (PDF/markdown) with price, delivery
  and penalty clauses ("raamafspraak 2026").
- Index in a vector DB (Qdrant or pgvector), hybrid search (BM25 + embeddings, an
  e5 / BERT-family embedding model), small retrieval eval (recall@k).
- When a memo mentions price or delay, the agent retrieves the relevant clause and
  cites it in the reason. Price still always goes to a human.
- Done when: PO26-0334 (8% surcharge) shows the contract clause next to the decision.
- Asked by: Elsevier, Schuberg Philis.

## Step 6. PySpark / Databricks + Dagster
- Generate a larger history of orders (e.g. 2 years, thousands of POs) with a script.
- PySpark job: supplier reliability (average delay, % late, trend). Run locally,
  then the same notebook in Databricks Free Edition.
- Dagster: daily pipeline as assets (orders -> flags -> decisions -> supplier stats),
  with caching so the LLM is only called for new or changed orders, and reviews stay
  valid while the order is unchanged.
- Done when: Dagster UI shows the asset graph and a daily schedule.
- Asked by: Samba, DLL, Vattenfall, Flow Traders (Spark/Databricks), CuspAI (Dagster).

## Step 7. Prometheus + Grafana
- The agent exposes metrics: decisions per action, LLM calls, cost, latency,
  retries, fallbacks, guardrail triggers, reviews pending.
- Grafana dashboard in docker-compose, saved as JSON in the repo.
- Done when: the dashboard shows the numbers of a real run.
- Asked by: Hogeschool Rotterdam, Elsevier.

## Step 8. Kubernetes (local)
- Run all services on a local cluster (kind or minikube): API, agent job, app,
  MLflow, Grafana. Kubernetes manifests or a small Helm chart.
- The daily build as a CronJob. Secrets as Kubernetes secrets (not in git).
- Done when: the app works from the cluster.
- Asked by: Hogeschool Rotterdam, CuspAI, UvA.

## Step 9. Terraform + Azure + CI/CD
- GitHub Actions: tests and image build on every push.
- Terraform: Azure resource group, container registry, Container Apps (API + app),
  a scheduled job for the daily build, Key Vault for the API key, budget alert.
- terraform destroy at the end. Write down the cost.
- Done when: the app ran in Azure once, and everything was destroyed.
- Asked by: Hogeschool Rotterdam, DLL, Vattenfall.

## Interview summary (goal)
"I built an LLM agent end to end: evaluated with MLflow, orchestrated with LangGraph
and human approval, traced with LangSmith, ERP access through MCP, RAG over supplier
contracts, data pipelines with PySpark and Dagster, monitored with Grafana, deployed
on Kubernetes and on Azure with Terraform and CI/CD."
