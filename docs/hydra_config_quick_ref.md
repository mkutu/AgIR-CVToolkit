# Pipeline Configuration Management

Each stage in the AgIR CV Toolkit pipeline (e.g., **query**, **infer-seg**) uses a shared configuration file that automatically tracks your settings, parameters, and runtime information. This ensures full **reproducibility** and **continuity** across multiple runs and stages.

---

## How Configuration Files Work

When you run a command such as:

```bash
agir-cv query --dataset semif --filters "common_name=barley"
```

or later:

```bash
agir-cv infer-seg
```

the toolkit automatically:

1. **Creates or updates** a configuration file (`cfg.yaml`) inside your run folder:

   ```
   outputs/runs/<project.name>/<project.subname>/cfg.yaml
   ```

2. **Saves all stage parameters** (CLI flags, Hydra settings, dataset info, etc.) in one place.

3. **Adds runtime information**, such as:

   * Stage name (`query`, `infer-seg`, etc.)
   * User and host
   * Timestamp
   * Git commit (if available)
   * CLI overrides used
   * Paths to logs, outputs, and reports

---

* **Nothing gets lost:** Missing command-line options in later stages don’t reset previous settings — only new or updated ones are added.
* **Reproducible runs:** The saved config file represents a complete record of what was run and how.
* **Shared workspace:** All outputs (logs, queries, masks, plots, manifests, etc.) for the same run live under the same folder.

---

## Example Folder Layout

```
outputs/
└── runs/
    └── agir_semif/001/
        ├── cfg.yaml            # Unified configuration
        ├── metrics.json        # Stage metrics
        ├── manifest.jsonl      # Run manifest
        ├── logs/
        ├── query/
        │   ├── query.csv       # Query results
        │   └── query_spec.csv  # Query parameters used
        ├── images/
        ├── masks/
        ├── cutouts/
        └── plots/
```

---

## Recommended Usage

1. Run each stage in sequence (`query`, then `infer`), using the same `--dataset` and `--project` values.
2. Avoid manually editing `cfg.yaml` — the toolkit handles updates automatically. This is simply a record and is not used in processing. Change the default configs in `src/agir_cvtoolkit/conf` to adjust default settings.
3. To start a **fresh run**, change the project name or subname to create a new run folder.
