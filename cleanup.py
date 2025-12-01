import os
import shutil

BASE_DIR = os.getcwd()
NEW_BASE = os.path.join(BASE_DIR, "finance-agent-v2")

# --- Helper functions ---
def safe_mkdir(path):
    os.makedirs(path, exist_ok=True)

def safe_move(src, dest):
    if os.path.exists(src):
        shutil.move(src, dest)
        print(f"✅ Moved: {src} → {dest}")
    else:
        print(f"⚠️  Skipped (not found): {src}")

def safe_remove(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
            print(f"🗑️  Removed directory: {path}")
        else:
            os.remove(path)
            print(f"🗑️  Removed file: {path}")

# --- 1. Create new folder structure ---
dirs_to_create = [
    "agent/connectors",
    "agent/utils",
    "rag/enrichment",
    "rag/index",
    "tests"
]
for d in dirs_to_create:
    safe_mkdir(os.path.join(NEW_BASE, d))

# --- 2. Move/rename key files ---
safe_move(os.path.join(BASE_DIR, "agent.py"), os.path.join(NEW_BASE, "agent", "orchestrator.py"))
safe_move(os.path.join(BASE_DIR, "app.py"), os.path.join(NEW_BASE, "app.py"))
safe_move(os.path.join(BASE_DIR, "requirements.txt"), os.path.join(NEW_BASE, "requirements.txt"))
safe_move(os.path.join(BASE_DIR, "Procfile"), os.path.join(NEW_BASE, "Procfile"))
safe_move(os.path.join(BASE_DIR, "test_Agent.py"), os.path.join(NEW_BASE, "tests", "test_agent.py"))
safe_move(os.path.join(BASE_DIR, "transactions_debug.json"), os.path.join(NEW_BASE, "transactions_debug.json"))

# MCP and enrichment moves
safe_move(os.path.join(BASE_DIR, "mcp"), os.path.join(NEW_BASE, "agent", "connectors"))
safe_move(os.path.join(BASE_DIR, "merchant_google_enrichment.py"), os.path.join(NEW_BASE, "rag", "enrichment", "merchant_mcp.py"))
if os.path.exists(os.path.join(BASE_DIR, "merchant_yelp_enrichment.py")):
    safe_move(os.path.join(BASE_DIR, "merchant_yelp_enrichment.py"), os.path.join(NEW_BASE, "rag", "enrichment", "merchant_yelp_mcp.py"))

# --- 3. Remove deprecated files and folders ---
deprecated = [
    "rag.py",
    "run_all.sh",
    "__pycache__",
    "venv",
    "gateway"
]
for item in deprecated:
    safe_remove(os.path.join(BASE_DIR, item))

# --- 4. Merge environment files ---
env_candidates = ["test.env", "ender-env.txt", "ender-new.env"]
merged_env_path = os.path.join(NEW_BASE, ".env")

with open(merged_env_path, "w") as merged:
    for f in env_candidates:
        path = os.path.join(BASE_DIR, f)
        if os.path.exists(path):
            with open(path) as src:
                merged.write(f"# Contents from {f}\n")
                merged.write(src.read() + "\n\n")
            print(f"✅ Merged env: {f}")

# --- 5. Optional: move static folder if you use it ---
if os.path.exists(os.path.join(BASE_DIR, "static")):
    safe_move(os.path.join(BASE_DIR, "static"), os.path.join(NEW_BASE, "static"))

print("\n🎯 Cleanup complete!")
print(f"New project structure created under: {NEW_BASE}")
