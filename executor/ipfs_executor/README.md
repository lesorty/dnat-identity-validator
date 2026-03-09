# IPFS Executor

This directory runs one execution from two IPFS CIDs:
- CSV dataset CID
- Python script CID

It downloads both files, executes the script with the dataset, and stores artifacts in `executor/executions/<execution_id>`.

## Run

```powershell
cd executor\ipfs_executor
python run_from_cids.py --dataset-cid <DATASET_CID> --script-cid <SCRIPT_CID>
```

Optional:

```powershell
python run_from_cids.py --dataset-cid <DATASET_CID> --script-cid <SCRIPT_CID> --ipfs-api-url http://localhost:5001 --executions-dir ..\executions
```

## Output files

Each run writes:
- `dataset.csv`
- `application.py`
- `result.json` (if your script writes it)
- `stdout.txt`
- `stderr.txt`
- `metadata.json`
