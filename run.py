import uvicorn
import sys
import os

if __name__ == "__main__":
    # --- START PATH FIX ---
    # Add the project root to the Python path
    # This ensures 'app' can be found
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    # --- END PATH FIX ---
    
    print(f"Added {project_root} to Python path")
    print("Starting Uvicorn server...")
    
    # We programmatically run uvicorn here
    # This is equivalent to: uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
    uvicorn.run("app.main:app", host="127.0.0.1", port=9000, reload=True)