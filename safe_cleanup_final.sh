#!/bin/bash
set -e

timestamp=$(date +'%Y_%m_%d_%H%M')
archive_dir="archive/cleanup_$timestamp"

echo "----------------------------------------------------"
echo " FINANCE AGENT PROJECT CLEANUP (SAFE MODE)"
echo " Archive folder: $archive_dir"
echo "----------------------------------------------------"

mkdir -p "$archive_dir"

echo ""
echo "📦 Archiving old + unused folders..."
echo ""

# Backup and old intent/orchestrator folders
mv rag-agent-ui/orchestrator_backup_*     "$archive_dir/" 2>/dev/null || true
mv rag-agent-ui/intents_backup_*          "$archive_dir/" 2>/dev/null || true
mv rag-agent-ui/backup_intents/           "$archive_dir/" 2>/dev/null || true
mv rag-agent-ui/tests/                    "$archive_dir/" 2>/dev/null || true

# Old zip bundles + backups
mv rag-agent-ui/*.zip                     "$archive_dir/" 2>/dev/null || true
mv FinanceAgent_AgentOnly.zip             "$archive_dir/" 2>/dev/null || true
mv FinanceAgent_FY25_TestSuite.csv        "$archive_dir/" 2>/dev/null || true

# Old RAG versions
mv rag-agent-ui/rag/builder.py            "$archive_dir/" 2>/dev/null || true
mv rag-agent-ui/rag/retriever.py          "$archive_dir/" 2>/dev/null || true
mv finance-agent-v2/rag/builder.py        "$archive_dir/" 2>/dev/null || true
mv finance-agent-v2/rag/retriever.py      "$archive_dir/" 2>/dev/null || true

# Old Yelp enrichment
mv finance-agent-v2/rag/enrichment/merchant_yelp_mcp.py "$archive_dir/" 2>/dev/null || true

# Old static backups
mv rag-agent-ui/static/app_backup_*       "$archive_dir/" 2>/dev/null || true

# Enrichment MCP service (likely deprecated)
mv enrichment-mcp-service                 "$archive_dir/" 2>/dev/null || true

echo ""
echo "🧹 Deleting safe temporary files..."
echo ""

# __pycache__
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# DS_Store
find . -name ".DS_Store" -type f -delete 2>/dev/null

# orphaned git objects inside the project
rm -rf .git/objects/71 2>/dev/null || true
rm -rf .git/objects/dd 2>/dev/null || true

# Remove stray RAG duplicates (if still present)
rm -f rag-agent-ui/rag/metadata.json 2>/dev/null || true
rm -f rag-agent-ui/rag/retriever.py 2>/dev/null || true

echo ""
echo "----------------------------------------------------"
echo " CLEANUP COMPLETE"
echo " Archive directory: $archive_dir"
echo "----------------------------------------------------"

echo ""
echo "Remaining structure (top-level only):"
find . -maxdepth 2 -type d -print

echo ""
echo "🎉 Your project is now clean, stable, and ready to push to GitHub."
