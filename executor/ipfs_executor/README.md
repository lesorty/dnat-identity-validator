# IPFS Executor

This directory runs one execution from two IPFS CIDs:
- CSV dataset CID
- Python script CID

It downloads both files, builds a `vm_runtime` bundle, sends the bundle to the executor HTTP API, and stores artifacts in `executor/executions/<execution_id>`.

## Run

```powershell
cd executor\ipfs_executor
python run_from_cids.py --dataset-cid <DATASET_CID> --script-cid <SCRIPT_CID>
```

Optional:

```powershell
python run_from_cids.py --dataset-cid <DATASET_CID> --script-cid <SCRIPT_CID> --ipfs-api-url http://localhost:5001 --executor-url http://localhost:5000 --executions-dir ..\executions
```

## Output files

Each run writes:
- `dataset.csv`
- `application.py`
- `bundle.tar.gz`
- `result.json` (response from `vm_runtime`)
- `stdout.txt`
- `stderr.txt`
- `metadata.json`
