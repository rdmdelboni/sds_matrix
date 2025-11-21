#!/usr/bin/env python3
"""
Migration script to update Python 3.9+ typing imports.

Changes:
- dict -> dict
- list -> list
- Optional -> object | None
- tuple -> tuple
- set -> set
"""

import re
from pathlib import Path

def process_typing_imports(content: str) -> str:
    """Process and remove old-style typing imports."""
    lines = content.split('\n')
    new_lines = []
    
    for line in lines:
        # Remove 'from typing import' lines that only have old-style imports
        if line.strip().startswith('from typing import'):
            # Extract what's being imported
            imports_part = line.split('import')[1]
            
            # list of things to keep (non-deprecated)
            keep_imports = []
            items = [item.strip() for item in imports_part.split(',')]
            
            deprecated = {'dict', 'list', 'tuple', 'set', 'Optional'}
            for item in items:
                if item and item not in deprecated:
                    keep_imports.append(item)
            
            # If anything left to import, keep the line; otherwise skip
            if keep_imports:
                new_line = f"from typing import {', '.join(keep_imports)}"
                new_lines.append(new_line)
            # else: skip this line (remove it)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # Clean up multiple blank lines from removed imports
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    return content

def migrate_type_annotations(content: str) -> str:
    """Migrate old-style type annotations to Python 3.10+ style."""
    
    # Pattern replacements (order matters!)
    replacements = [
        # dict[str, ...] patterns
        (r'\bDict\[str,\s*([^\]]+)\]', r'dict[str, \1]'),
        (r'\bDict\[([^,]+),\s*([^\]]+)\]', r'dict[\1, \2]'),
        (r'\bDict\b', 'dict'),
        
        # list patterns
        (r'\bList\[([^\]]+)\]', r'list[\1]'),
        (r'\bList\b', 'list'),
        
        # set patterns
        (r'\bSet\[([^\]]+)\]', r'set[\1]'),
        (r'\bSet\b', 'set'),
        
        # tuple patterns
        (r'\bTuple\[([^\]]+)\]', r'tuple[\1]'),
        (r'\bTuple\b', 'tuple'),
        
        # Optional patterns
        (r'\bOptional\[([^\]]+)\]', r'\1 | None'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    return content

def migrate_file(filepath: str) -> bool:
    """Migrate a single file. Returns True if changes were made."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = original_content
        
        # Process imports
        content = process_typing_imports(content)
        
        # Migrate annotations
        content = migrate_type_annotations(content)
        
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Main migration function."""
    workspace = Path('/home/rdmdelboni/Work/Gits/sds_matrix')
    
    # Find all Python files
    python_files = list(workspace.rglob('*.py'))
    
    # Exclude common directories
    excluded = {'.venv', 'venv', '__pycache__', '.git', 'htmlcov'}
    python_files = [f for f in python_files 
                   if not any(part in excluded for part in f.parts)]
    
    print(f"Found {len(python_files)} Python files to process")
    
    changed_files = []
    for filepath in python_files:
        if migrate_file(str(filepath)):
            changed_files.append(str(filepath))
            print(f"✓ Updated: {filepath.relative_to(workspace)}")
    
    print(f"\n✓ Migration complete: {len(changed_files)} files updated")
    
    if changed_files:
        print("\nUpdated files:")
        for f in sorted(changed_files):
            print(f"  - {Path(f).relative_to(workspace)}")

if __name__ == '__main__':
    main()
