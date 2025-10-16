```sh
AgIR-CVToolkit/
│   docs/
│   ├── README.md                           # Navigation hub
│   ├── query_quickstart.md                 # 5-minute tutorial
│   ├── db_query_usage.md                   # Full guide
│   ├── query_specs_quick_reference.md      # Specs guide
│   ├── hydra_config_quick_ref.md           # Config guide
│   ├── repo_skeleton.md                    # Structure
│   ├── roadmap.md                          # Roadmap
│   └── design/                             
│       ├── adr/
│       │   └── 0001-foundation.md
│       └── FR-01.md
│
├─ src/
│  └─ agir_cvtoolkit/
│     ├─ conf/
│     │  ├─ __init__.py
│     │  ├─ config.yaml
│     │  ├─ io/
│     │  │  └─ default.yaml
│     │  ├─ cvat/
│     │  │  └─ default.yaml
│     │  ├─ seg_inference/
│     │  │  └─ default.yaml
│     │  └─ db/
│     │     └─ default.yaml
│     ├─ __init__.py
│     ├─ cli.py
│     ├─ core/
│     │  ├─ logging_utils.py
│     │  └─ db/
│     │     ├─ __init__.py          # Export AgirDB, QuerySpec, ImageRecord
│     │     ├─ agir_db.py           # Main unified DB class
│     │     ├─ types.py             # QuerySpec, ImageRecord dataclasses
│     │     └─ filters.py           # Filter parsing utilities
│     └─ pipelines/
│        ├─ stages/
│        │  ├─ seg_infer.py
│        │  └─ query.py
│        ├─ artifacts/
│        │  └─ layouts.py
│        └─ utils/
│           ├─ hydra_utils.py
│           ├─ serializers.py
│           ├─ query_utils.py
│           ├─ seg_utils.py
│           └─ query_parse.py
├─ tests/
│  ├─ test_cli_field_query.py
│  ├─ test_cli_semif_query.py
│  └─ data/
│     ├─ images/
│     │  ├─ red.png
│     │  ├─ green.png
│     │  └─ checker.png
│     └─ db/
│        ├─ test_semif.db
│        └─ test_field.db
│
├─ runs/
│  └─ <project_name>/<subname>/   # run_id
│     ├─ manifest.jsonl           # one row per item (authoritative index)
│     ├─ cfg.yaml                 # frozen/expanded config used
│     ├─ metrics.json             # summary stats
│     ├─ logs/                    # text logs
│     ├─ query/                   # the exact query outputs (immutable)
│     │  ├─ query.parquet
│     │  ├─ query.jsonl
│     │  ├─ query.csv
│     │  └─ query_spec.json       # Query parameters (never overwritten)
│     ├─ images/                  # resolved image sources used for this run
│     │  ├─ <image_id>.jpg        # copy or hardlink, optional (see below)
│     ├─ masks/                   # canonical model outputs (for CVAT/analysis)
│     │  ├─ <image_stem>.png      # uint8 indexed, 0=bg, 1..K=classes
│     │  └─ colormaps/legend.json # optional palette
│     ├─ yolo_txt/                # Not implemented yet (if doing YOLO-style labels too)
│     │  └─ <image_stem>.txt
│     └─ upload/                  # Not implemented yet: ready-to-ship bundles for CVAT per-task
│        ├─ task_seedheads/
│        │  ├─ images/ (compressed copies)
│        │  ├─ masks/
│        │  └─ manifest.csv
│        └─ task_leaf_issues/
│
├─ pyproject.toml
├─ environment.yml
└─ README.md
```