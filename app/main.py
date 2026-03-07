import sys
from pathlib import Path
from app.services.ast_parser import get_chunks_from_file

def main():
    """Main entry point for Universal Build Documentor."""
    if len(sys.argv) < 2:
        print("Usage: python -m app.main <path_to_python_file>")
        sys.exit(1)

    target_path = Path(sys.argv[1])
    if not (target_path.exists() and target_path.is_file()):
        print(f"Error: Python file not found: {target_path}")
        sys.exit(1)

    print(f"\n--- Documenting: {target_path.name} ---")
    
    try:
        # Extract chunks (classes and functions) from the file
        chunks = get_chunks_from_file(target_path, hierarchical=True)
        
        print(f"Extracted {len(chunks)} top-level code chunks.\n")
        
        for chunk in chunks:
            display_chunk(chunk)
            
        print("\n--- Extraction Complete ---")
            
    except Exception as e:
        print(f"An error occurred during parsing: {e}")
        sys.exit(1)

def display_chunk(chunk, indent=0):
    """Helper to display extracted chunk metadata."""
    prefix = "  " * indent
    name = chunk['name']
    ctype = chunk['type'].capitalize()
    start = chunk['start_line']
    end = chunk['end_line']
    
    print(f"{prefix}📌 {ctype}: {name} (Lines {start}-{end})")
    
    doc = chunk.get('docstring')
    if doc:
        # Show first line of docstring
        doc_first = doc.strip().split('\n')[0]
        print(f"{prefix}   ↳ Doc: \"{doc_first}...\"")
    
    # Recursively display children (methods in a class, for example)
    for child in chunk.get('children', []):
        display_chunk(child, indent + 1)

if __name__ == "__main__":
    main()
