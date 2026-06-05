# 🧦 Dobby's K8s Resource Resizer

> *"Dobby is free. And so is your wasted CPU."*

A Kubernetes namespace CPU/memory request auto-resizer built for the **Platform9 AI Edition Hackathon 2026**. Uses [Goldilocks](https://goldilocks.docs.fairwinds.com/) + VPA to generate rightsizing recommendations, then posts them to Slack and optionally applies them automatically.

Identified **$177/month in savings** from `prajwal-hack-region-1` on the first run.

---

## How It Works

```
Goldilocks + VPA  →  Python Controller  →  Slack Bot  →  K8s Deployments
(Helm charts)        (VPA reader +          (Socket mode,   (auto-patched,
                      cost calculator)       no ingress)     opt-in only)
```

VPA observes real pod CPU/memory usage. Goldilocks creates one `VerticalPodAutoscaler` object per Deployment. The controller reads recommendations, calculates cost delta using AWS on-demand pricing, and posts to a Slack channel. Auto-apply is off by default and requires explicit opt-in.

### Two Modes

| Mode | Behavior |
|---|---|
| **Recommend** | Posts rightsizing recommendations + estimated monthly savings to Slack |
| **Auto-apply** | Patches `resources.requests` on Deployments when deviation exceeds threshold |

---

## Slack Commands

| Command | Description |
|---|---|
| `/resize recommend` | Show all recommendations with cost savings |
| `/resize apply` | Apply all recommendations immediately |
| `/resize status` | Show current config (namespaces, threshold, auto-apply state) |
| `/resize autoapply on\|off` | Toggle auto-apply mode |

---

## Architecture

```
hack-resizer/
├── controller/
│   ├── config.py              # Env-var config + K8s client setup
│   ├── vpa_reader.py          # Read VPA objects, build WorkloadRec list
│   ├── cost_calculator.py     # Parse CPU/memory, compute monthly savings
│   ├── deployment_patcher.py  # Patch Deployment resource requests
│   ├── slack_notifier.py      # Build + send Slack block messages
│   ├── slack_commands.py      # Slack Bolt app + slash command handlers
│   ├── scheduler.py           # Periodic auto-apply loop
│   └── main.py                # Entrypoint: scheduler thread + Slack socket handler
├── k8s/
│   ├── 00-namespace.yaml      # hack-resizer namespace
│   ├── 01-rbac.yaml           # ServiceAccount, ClusterRole (VPA read), scoped Role (Deployment patch)
│   ├── 02-configmap.yaml      # Runtime config
│   ├── 03-secret.yaml.template # Template — copy, fill in tokens, apply manually
│   └── 04-deployment.yaml     # Controller Deployment
├── helm/
│   └── install.sh             # Install VPA + Goldilocks via Helm, label namespaces
├── tests/                     # 28 unit tests (pytest + unittest.mock)
└── slides/index.html          # Hackathon presentation (Harry Potter theme)
```

---

## Safety Constraints

- RBAC gives the controller **patch access only on target namespaces** — no cluster-wide write access
- VPA runs in **recommendation-only mode** — no auto-eviction of pods
- Auto-apply is **off by default** — toggle with `/resize autoapply on`
- Only patches `resources.requests`, **never `resources.limits`**
- Escape hatch: add annotation `hack-resizer/skip: "true"` to any Deployment to exclude it

---

## Setup

### 1. Prerequisites

- Kubernetes cluster with Helm
- Slack app with socket mode enabled (Bot Token `xoxb-*`, App Token `xapp-*`)

### 2. Install VPA + Goldilocks

```bash
cd helm
bash install.sh
```

This installs VPA (recommendation-only, no updater/admission controller) and Goldilocks, then labels the target namespaces so Goldilocks creates VPA objects for their Deployments.

### 3. Configure Secrets

```bash
cp k8s/03-secret.yaml.template k8s/03-secret.yaml
# Fill in SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_SIGNING_SECRET
kubectl apply -f k8s/03-secret.yaml
```

### 4. Apply K8s Manifests

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/01-rbac.yaml
kubectl apply -f k8s/02-configmap.yaml
kubectl apply -f k8s/04-deployment.yaml
```

### 5. Configuration

Edit `k8s/02-configmap.yaml` to tune behavior:

| Variable | Default | Description |
|---|---|---|
| `NAMESPACES` | `prajwal-hack,prajwal-hack-region-1` | Comma-separated list of target namespaces |
| `THRESHOLD_PERCENT` | `20` | Minimum deviation (%) before auto-apply acts |
| `SCHEDULE_INTERVAL_MINUTES` | `60` | How often the auto-apply loop runs |
| `SLACK_CHANNEL` | `#k8s-hack-resizer` | Channel to post messages to |
| `NODE_INSTANCE_TYPE` | `m5.xlarge` | AWS instance type for cost calculation |
| `AUTO_APPLY_ENABLED` | `false` | Set to `true` to enable auto-apply on startup |

### 6. Build + Deploy

```bash
docker build -t your-registry/hack-resizer:latest .
docker push your-registry/hack-resizer:latest
# Update image in k8s/04-deployment.yaml, then apply
```

---

## Running Tests

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -v
```

28 tests covering cost calculation, VPA parsing, deployment patching, Slack block building, and the scheduler threshold logic.

---

## Cost Calculation

Uses static AWS on-demand pricing for the configured instance type:

| Instance | CPU ($/core/hr) | Memory ($/GiB/hr) |
|---|---|---|
| m5.xlarge | $0.048 | $0.006 |

Monthly saving = `delta_cpu_cores × cpu_price × 730 + delta_mem_gib × mem_price × 730`

---

## Built With

- [Goldilocks](https://goldilocks.docs.fairwinds.com/) — VPA object management per Deployment
- [VPA](https://github.com/kubernetes/autoscaler/tree/master/vertical-pod-autoscaler) — usage-based resource recommendations
- [Slack Bolt](https://slack.dev/bolt-python/) — slash command handling via socket mode
- [kubernetes Python client](https://github.com/kubernetes-client/python) — VPA reads + Deployment patches

---

*Platform9 AI Edition Hackathon · June 2026*
