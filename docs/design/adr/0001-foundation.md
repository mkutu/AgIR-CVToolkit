# ADR 0001: Foundation of AgIR-CVPipeline

## Status
Accepted

## Context
The AgIR ecosystem (SemiF / Field databases, LTS storage, CVAT annotation server) needs a **unified computer vision pipeline** to support iterative dataset refinement:

- **Query DB** (SemiF/Field) to select images.
- **Run models** (segmentation/detection) to generate proposed labels.
- **Upload to CVAT** for human refinement.
- **Export refined labels** back into a normalized format.
- **Retrain models** with updated labels.
- **(Optional) Save outputs** (masks, cutouts) to long-term storage (LTS) and update DB tables.

Previously, tooling was ad-hoc: scripts scattered across repos, each with its own configs. This ADR defines the foundation for a single integrated toolkit.

## Decision
We will create a new repository named **AgIR-CVPipeline**, which provides an **end-to-end vision data pipeline** with the following properties:

1. **Objective**
   - Automate the iterative loop: **Query DB → Model → Propose Labels → CVAT Refine → Export → Retrain**.
   - Support optional data product generation (**masks, cutouts**) and **DB/LTS updates**.

2. **Requirement types**
   - **Functional**
      - Update necessary file requirements like species_info mapping, most current detection, and segmentation model
      - Query SemiF/Field DBs with filters.
      - Run segmentation/detection models (Torch, SMP, YOLO, etc.).
      - Generate outputs (full-sized masks, bounding box coordinates, cutouts) in standard formats.
      - Upload images and prelabels to CVAT (projects, tasks).
      - Export annotations from CVAT in Yolo/Mask formats.
      - Normalize annotations into a canonical schema.
      - Update DBs with new artifacts (optional).
      - Save artifacts to LTS storage (optional).
   - **Non-functional**
      - Reproducibility: each run stores configs, environment, model hashes.
      - Observability: structured logs + per-run reports.
      - Idempotency: safe to re-run same command without duplication.
      - Extensibility: easy to add new models, formats, or storage backends.
      - Portability: works on shared servers, HPC, or local dev without sudo.
      - Testability: unit tests with synthetic fixtures; CI validation.

3. **Architecture principles**
   - **Hydra-first config management** (clear config groups: `source/`, `model/`, `pipeline/`, `cvat/`, `io/`).
   - **Single CLI entrypoint** with subcommands (`infer`, `upload-cvat`, `export-cvat`, `make-cutouts`, etc.).
   - **Interfaces, not scripts**: define clear contracts (`ImageSource`, `ModelRunner`, `StorageSink`, `DbWriter`, `CvatClient`, `Pipeline`).
   - **One repo, multiple modules**: DB, models, CVAT, LTS are integrated but separated in code.
   - **Data contracts explicit**: JSON schemas for predictions, masks, cutouts, exports.

4. **Scope (v1)**
   - Query DB → Model → Prelabels → CVAT refine → Export → Retrain.
   - Minimal dummy model + CVAT mock client to validate wiring.
   - Add masks → LTS + DB as optional modules.
   - Add cutouts → LTS + DB as optional modules.

5. **Out of scope (for v1)**
   - Active learning strategies, experiment tracking (W&B).
   - Large-scale distributed training.
   - Complex CVAT admin (user management, quotas).
   - Visualization dashboards beyond quick inspection plots.

6. **Deliverables**
   - Repo scaffold (`pyproject.toml`, Hydra configs, src layout, tests).
   - `docs/requirements.md` detailing functional & non-functional requirements.
   - Minimal working CLI with dummy pipeline (DB → dummy model → output masks).
   - Unit tests with small fixtures.
   - Pre-commit + CI for lint/test.

## Consequences
- **Benefits**: unified pipeline, less duplication, easier onboarding, repeatable runs.
- **Trade-offs**: repo becomes broad (not CVAT-only); requires discipline to keep modules modular.
- **Risks**: scope creep if optional (LTS, cutouts) is merged too early; mitigated by config flags and ADRs.

## Related ADRs
- 0002: Segmentation framework choice (SMP vs custom).
- 0003: Detection framework choice (YOLO vs Detectron2).
- 0004: Prelabel format (bitmap vs polygons).
- 0005: Task creation strategy in CVAT (per class vs per folder vs per date).