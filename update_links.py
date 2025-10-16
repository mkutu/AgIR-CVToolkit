#!/usr/bin/env python3
"""
update_links.py - Automatically update internal markdown links

Usage:
    python update_links.py docs/
"""

import re
import os
from pathlib import Path

# Map of old paths to new paths
LINK_MAP = {
    # Database docs
    'semif_database_documentation.md': 'DATABASES/semif_database_documentation.md',
    'field_database_documentation.md': 'DATABASES/field_database_documentation.md',
    
    # Getting started
    'query_quickstart.md': 'GETTING_STARTED/query_quickstart.md',
    'quick_refs/pipeline_overview.md': 'GETTING_STARTED/pipeline_overview.md',
    
    # Query stage
    'db_query_usage.md': 'PIPELINE_STAGES/01_query/db_query_usage.md',
    'query_specs_quick_reference.md': 'PIPELINE_STAGES/01_query/query_specs_quick_reference.md',
    'query_example_guide.md': 'PIPELINE_STAGES/01_query/query_example_guide.md',
    
    # Inference
    'seg_inference_quickstart.md': 'PIPELINE_STAGES/02_inference/seg_inference_quickstart.md',
    
    # CVAT
    'cvat_upload_usage.md': 'PIPELINE_STAGES/03_cvat_upload/cvat_upload_usage.md',
    'quick_refs/cvat_upload_quick_start.md': 'PIPELINE_STAGES/03_cvat_upload/cvat_upload_quick_start.md',
    'cvat_download_usage.md': 'PIPELINE_STAGES/04_cvat_download/cvat_download_usage.md',
    
    # Preprocessing & Training
    'preprocessing_pipeline_usage.md': 'PIPELINE_STAGES/05_preprocessing/preprocessing_pipeline_usage.md',
    'train_pipeline_usage.md': 'PIPELINE_STAGES/06_training/train_pipeline_usage.md',
    
    # Configuration
    'hydra_config_quick_ref.md': 'CONFIGURATION/hydra_config_quick_ref.md',
    
    # Quick references
    'quick_refs/quick_refs_all.md': 'QUICK_REFERENCES/quick_refs_all.md',
    'quick_refs.md': 'QUICK_REFERENCES/quick_refs_consolidated.md',
    
    # Architecture
    'repo_skeleton.md': 'ARCHITECTURE/repo_skeleton.md',
    'roadmap.md': 'ARCHITECTURE/roadmap.md',
    'design/adr/0001-foundation.md': 'ARCHITECTURE/design/adr/0001-foundation.md',
    'design/FR-01.md': 'ARCHITECTURE/design/feature_requirements/FR-01.md',
}

def calculate_relative_path(from_file, to_file):
    """Calculate relative path from one file to another."""
    from_dir = Path(from_file).parent
    to_path = Path(to_file)
    
    try:
        rel_path = os.path.relpath(to_path, from_dir)
        return rel_path.replace('\\', '/')  # Normalize to forward slashes
    except ValueError:
        # Files on different drives (Windows)
        return to_file

def update_links_in_file(file_path, docs_root):
    """Update all markdown links in a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all markdown links: [text](path)
    link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    
    def replace_link(match):
        text = match.group(1)
        old_link = match.group(2)
        
        # Skip external links
        if old_link.startswith(('http://', 'https://', '#')):
            return match.group(0)
        
        # Remove anchor if present
        anchor = ''
        if '#' in old_link:
            old_link, anchor = old_link.split('#', 1)
            anchor = '#' + anchor
        
        # Check if this link needs updating
        if old_link in LINK_MAP:
            new_absolute_path = docs_root / LINK_MAP[old_link]
            new_relative_path = calculate_relative_path(file_path, new_absolute_path)
            new_link = new_relative_path + anchor
            print(f"  {old_link} → {new_link}")
            return f'[{text}]({new_link})'
        
        return match.group(0)
    
    new_content = re.sub(link_pattern, replace_link, content)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main(docs_dir):
    """Update links in all markdown files."""
    docs_root = Path(docs_dir)
    updated_count = 0
    
    for md_file in docs_root.rglob('*.md'):
        print(f"\nChecking {md_file}...")
        if update_links_in_file(md_file, docs_root):
            updated_count += 1
    
    print(f"\n✅ Updated {updated_count} files")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python update_links.py docs/")
        sys.exit(1)
    
    main(sys.argv[1])