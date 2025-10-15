# AgIR-CVPipeline Roadmap

## v1.0 (baseline)
**Goal:** Stand up a minimal, reproducible end-to-end loop.  
**Features:**
- DB query → model → prelabels → CVAT refine → export → retrain
- Hydra configs, CLI entrypoint (`agir-cv`)
- Unit tests with synthetic fixtures
**Deliverable:** First working pipeline with dummy + one real model.
**Dependencies:** None

---

## v1.1 (extensions)
**Goal:** Persist intermediate results for traceability and dataset growth.  
**Features:**
- Save masks to LTS + update DB
- Generate cutouts from det/seg and store in LTS + DB
- Add reporting (`run_summary.json`, `errors.csv`)
**Deliverable:** DB tables + LTS storage updated automatically; reports generated per run.
**Dependencies:** v1.0 complete

---

## v1.2 (experiment tracking)
**Goal:** Enable reproducible model development and metric logging.  
**Features:**
- Integrate experiment tracking (e.g., Weights & Biases)
- Record training + validation metrics
**Deliverable:** All training runs logged with configs, metrics, artifacts.
**Dependencies:** v1.0 baseline training loop stable

---

## v1.3 (orchestration / automation)
**Goal:** Automate the loop for production-like workflows.  
**Features:**
- Airflow or Prefect integration
- Scheduled inference + CVAT upload DAG
- Export + retrain DAG triggered after CVAT review
**Deliverable:** Pipelines run on a schedule or trigger, with DAG visibility.
**Dependencies:** v1.0 + v1.1 (stable outputs and reporting)

---

## v2.0 (bigger vision)
**Goal:** Move beyond annotation refinement into large-scale dataset creation.  
**Features:**
- Full synthetic dataset generation
**Deliverable:** Synthetic images + annotations integrated into the same pipeline.
**Dependencies:** Stable retraining loop (v1.0–1.3)
