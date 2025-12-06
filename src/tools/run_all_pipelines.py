import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path("src").absolute()))

from bioetl.interfaces.cli.app import app

# Pipeline dependency order
PIPELINES = [
    "assay_chembl",
    "activity_chembl",
    "target_chembl",
    "document_chembl",
    "testitem_chembl"
]

def run_pipeline(name: str, limit: int) -> dict:
    start_time = datetime.now(timezone.utc)
    print(f"\n{'='*50}")
    print(f"Starting pipeline: {name}")
    print(f"{'='*50}")
    
    # Mock args
    # Assume standard config location based on name: {entity}_chembl -> configs/pipelines/chembl/{entity}.yaml
    entity = name.split('_')[0]
    config_path = f"configs/pipelines/chembl/{entity}.yaml"
    output_path = f"data/output/{entity}"
    
    sys.argv = [
        "bioetl", 
        "run", 
        name,
        "--config", config_path,
        "--output", output_path,
        "--limit", str(limit)
    ]
    
    success = False
    error = None
    
    try:
        app()
        success = True
    except SystemExit as e:
        if e.code != 0:
            success = False
            error = f"Exit code {e.code}"
        else:
            success = True
    except Exception as e:
        success = False
        error = str(e)
        
    end_time = datetime.now(timezone.utc)
    duration = (end_time - start_time).total_seconds()
    
    return {
        "name": name,
        "success": success,
        "duration_sec": duration,
        "error": error,
        "timestamp": end_time.isoformat()
    }

def main():
    # Ensure report dir
    report_dir = Path("reports/chembl_all")
    report_dir.mkdir(parents=True, exist_ok=True)
    
    limit = 100
    results = []
    
    print(f"Running all ChEMBL pipelines with limit={limit}...")
    
    for name in PIPELINES:
        res = run_pipeline(name, limit)
        results.append(res)
        if not res["success"]:
            print(f"[ERROR] Pipeline {name} failed! Stopping sequence.")
            break
            
    # Generate report
    summary_path = report_dir / "summary.md"
    qc_path = report_dir / "qc.json"
    
    # Write QC JSON
    with open(qc_path, "w") as f:
        json.dump(results, f, indent=2)
        
    # Write Summary MD
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# ChEMBL Pipelines Execution Report\n\n")
        f.write(f"**Date:** {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"**Limit:** {limit}\n\n")
        f.write("| Pipeline | Status | Duration (s) | Error |\n")
        f.write("|----------|--------|--------------|-------|\n")
        for r in results:
            status = "OK" if r["success"] else "FAIL"
            err = r["error"] if r["error"] else "-"
            f.write(f"| {r['name']} | {status} | {r['duration_sec']:.2f} | {err} |\n")
            
    print(f"\nReport generated: {summary_path}")

if __name__ == "__main__":
    main()

