#!/usr/bin/env python3
"""
CVAT Label Management Script
Adds or updates labels/classes in CVAT projects using the Python SDK
"""

from cvat_sdk import make_client
from pathlib import Path
import sys
from src.agir_cvtoolkit.pipelines.utils.species import SpeciesInfo
from src.agir_cvtoolkit.pipelines.utils.hydra_utils import read_yaml
# ============================================================================
# CONFIGURATION - Modify these values for your setup
# ============================================================================

# CVAT connection settings
keys = read_yaml(Path(".keys") / "default.yaml")['cvat']
CVAT_HOST = keys['host']  # Change to your CVAT server URL
USERNAME = keys.get("username")
PASSWORD = keys.get("password")
UPDATE_PROJECT_LABELS = False  # Set to True to update labels in existing project

# Project configuration
PROJECT_NAME = 'AgIR-SemiField'  # For creating new project
PROJECT_ID = 319384  # Set to existing project ID to update, or None to create new

species_info = SpeciesInfo(Path("/mnt/research-projects/s/screberg/longterm_images2/semifield-utils/species_information/species_info.json"))
species_info.load()

from pprint import pprint
bycname = species_info.by_common_name

labels = []
for k, v in bycname.items():
    name = v['common_name'].replace(" ", "_").lower()
    color = v['hex']
    label = {
        'name': name,
        'color': color,
        'attributes': [
            {
                'name': 'label_id',
                'mutable': False,
                'input_type': 'select',
                'default_value': '',
                'values': [''],
            },
        ]
    }
    labels.append(label)

# ============================================================================
# SCRIPT LOGIC - You shouldn't need to modify below this line
# ============================================================================

def create_project_with_labels(client, project_name, labels):
    """Create a new project with the specified labels."""
    print(f"Creating new project: '{project_name}'")
    
    project = client.projects.create(
        spec={
            'name': project_name,
            'labels': labels
        }
    )
    
    print(f"✓ Project created successfully (ID: {project.id})")
    print(f"  Labels added: {len(labels)}")
    for label in labels:
        attr_count = len(label.get('attributes', []))
        print(f"    - {label['name']} ({attr_count} attributes)")
    
    return project


def update_project_labels(client, project_id, labels):
    """Update labels in an existing project."""
    print(f"Updating project ID: {project_id}")
    
    try:
        project = client.projects.retrieve(project_id)
        print(f"  Found project: '{project.name}'")
        
        # Update the labels
        project.update({'labels': labels})
        
        print(f"✓ Labels updated successfully")
        print(f"  Total labels: {len(labels)}")
        for label in labels:
            attr_count = len(label.get('attributes', []))
            print(f"    - {label['name']} ({attr_count} attributes)")
        
        return project
        
    except Exception as e:
        print(f"✗ Error updating project: {e}")
        sys.exit(1)


def list_project_labels(client, project_id):
    """List current labels in a project."""
    try:
        project = client.projects.retrieve(project_id)
        labels = project.get_labels()
        print(f"\nCurrent labels in project '{project.name}':")
        if labels:
            for label in labels:
                
                print(f"  - {label.name} (color: {label.color})")
                if hasattr(label, 'attributes') and label.attributes:
                    for attr in label.attributes:
                        print(f"      • {attr.name} ({attr.input_type})")
        else:
            print("  No labels found")
            
    except Exception as e:
        print(f"✗ Error retrieving project: {e}")
        sys.exit(1)


def main():
    print("=" * 70)
    print("CVAT Label Management Script")
    print("=" * 70)
    
    # Connect to CVAT
    print(f"\nConnecting to CVAT at {CVAT_HOST}...")
    try:
        client = make_client(host=CVAT_HOST, credentials=(USERNAME, PASSWORD))
        print("✓ Connected successfully\n")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        sys.exit(1)
    
    # Decide whether to create new project or update existing
    if PROJECT_ID is not None:
        # Update existing project
        if UPDATE_PROJECT_LABELS:
            update_project_labels(client, PROJECT_ID, labels)
        list_project_labels(client, PROJECT_ID)
    else:
        # Create new project
        # project = create_project_with_labels(client, PROJECT_NAME, labels)
        # print(f"\nProject URL: {CVAT_HOST}/projects/{project.id}")
        None
    
    print("\n" + "=" * 70)
    print("Done!")
    print("=" * 70)


if __name__ == '__main__':
    main()