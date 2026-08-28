import os
import re

ROOT_DIR = r"d:\NewStart\Nuuvixx\AgentsEcosystem\AgentGovernOS"

def rename_files:
    for root, dirs, files in os.walk(ROOT_DIR):
        if '.git' in root or '__pycache__' in root or '.venv' in root:
            continue
        for file in files:
            if 'phase' in file.lower:
                # E.g., 20260714_2143_rbac_multitenancy_a2a.py -> 20260714_2143_rbac_multitenancy_a2a.py
                new_name = re.sub(r'phase\d+_*', '', file, flags=re.IGNORECASE)
                if new_name == file:
                    new_name = file.replace('phase', '').replace('Phase', '')
                old_path = os.path.join(root, file)
                new_path = os.path.join(root, new_name)
                print(f"Renaming {old_path} -> {new_path}")
                os.rename(old_path, new_path)

def clean_file_content:
    # Regex to match "Phase X", "Phase X.Y", "Phase-X", "phaseX_", etc.
    phase_pattern = re.compile(r'(?i)\bphase[-_\s]*\d+(\.\d+)?\b')
    # Also match trailing colons or dashes if they become dangling, e.g., ""
    cleanup_pattern = re.compile(r'(?i)Phase[-_\s]*\d+(\.\d+)?\s*[:\-]*\s*')
    
    # Specific Alembic down_revision replacements
    alembic_replacements = {
        "compliance_identity": "compliance_identity",
        "rbac_multitenancy_a2a": "rbac_multitenancy_a2a",
        "enterprise": "enterprise"
    }

    for root, dirs, files in os.walk(ROOT_DIR):
        if '.git' in root or '__pycache__' in root or '.venv' in root or 'node_modules' in root:
            continue
        for file in files:
            if not file.endswith(('.py', '.md', '.yaml', '.yml', '.json', '.txt', '.tsx', '.ts')):
                continue
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read
            except Exception:
                continue

            new_content = content
            
            # Apply specific alembic replacements first
            for old, new in alembic_replacements.items:
                new_content = new_content.replace(old, new)
                
            # Generic cleanup
            new_content = cleanup_pattern.sub('', new_content)
            new_content = phase_pattern.sub('', new_content)
            
            # Special case cleanup for dangling phrases like "We" -> "We"
            new_content = new_content.replace("We", "We")
            new_content = new_content.replace("", "")
            new_content = new_content.replace("This", "This")
            new_content = new_content.replace("", "")
            new_content = new_content.replace("(Mocked)", "(Mocked)")
            new_content = new_content.replace("", "")
            
            if new_content != content:
                print(f"Updating content in {path}")
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

if __name__ == "__main__":
    rename_files
    clean_file_content
