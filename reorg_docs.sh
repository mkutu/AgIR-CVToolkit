mv docs/quick_refs/seg_infer_quick_start.md docs/PIPELINE_STAGES/02_inference/
mv docs/quick_refs/hydra_config_quick_ref.md docs/CONFIGURATION/

# # Create new directory structure
# mkdir -p docs/GETTING_STARTED
# mkdir -p docs/DATABASES
# mkdir -p docs/PIPELINE_STAGES/{01_query,02_inference,03_cvat_upload,04_cvat_download,05_preprocessing,06_training}
# mkdir -p docs/CONFIGURATION
# mkdir -p docs/QUICK_REFERENCES
# mkdir -p docs/ARCHITECTURE/design/{adr,feature_requirements}

# # Move database documentation
# mv docs/semif_database_documentation.md docs/DATABASES/
# mv docs/field_database_documentation.md docs/DATABASES/

# # Move getting started guides
# mv docs/query_quickstart.md docs/GETTING_STARTED/
# cp docs/quick_refs/pipeline_overview.md docs/GETTING_STARTED/

# # Move pipeline stage docs
# mv docs/db_query_usage.md docs/PIPELINE_STAGES/01_query/
# mv docs/query_specs_quick_reference.md docs/PIPELINE_STAGES/01_query/
# mv docs/query_example_guide.md docs/PIPELINE_STAGES/01_query/

# mv docs/quick_refs/seg_inference_quickstart.md docs/PIPELINE_STAGES/02_inference/

# mv docs/cvat_upload_usage.md docs/PIPELINE_STAGES/03_cvat_upload/
# mv docs/quick_refs/cvat_upload_quick_start.md docs/PIPELINE_STAGES/03_cvat_upload/

# mv docs/cvat_download_usage.md docs/PIPELINE_STAGES/04_cvat_download/

# mv docs/preprocessing_pipeline_usage.md docs/PIPELINE_STAGES/05_preprocessing/

# mv docs/train_pipeline_usage.md docs/PIPELINE_STAGES/06_training/

# # Move configuration docs
# mv docs/hydra_config_quick_ref.md docs/CONFIGURATION/

# # Move quick references
# mv docs/quick_refs/quick_refs_all.md docs/QUICK_REFERENCES/
# mv docs/quick_refs.md docs/QUICK_REFERENCES/quick_refs_consolidated.md

# # Move architecture docs
# mv docs/repo_skeleton.md docs/ARCHITECTURE/
# mv docs/roadmap.md docs/ARCHITECTURE/
# mv docs/design/adr/0001-foundation.md docs/ARCHITECTURE/design/adr/
# mv docs/design/FR-01.md docs/ARCHITECTURE/design/feature_requirements/

# Update central README
# (Use the artifact created above)