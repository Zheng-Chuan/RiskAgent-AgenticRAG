from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _filter_rows(rows: object, keep_ids: set[str]) -> list[dict]:
    if not isinstance(rows, list):
        return []
    out: list[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        item_id = str(row.get("id", "")).strip()
        if item_id in keep_ids:
            out.append(row)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--ids", nargs="+", required=True)
    args = parser.parse_args()

    dataset_path = Path(args.dataset_path)
    output_dir = Path(args.output_dir)
    keep_ids = {str(item).strip() for item in args.ids if str(item).strip()}
    if not keep_ids:
        raise ValueError("ids must not be empty")

    dataset = _load_json(dataset_path)
    subset = _filter_rows(dataset, keep_ids)
    if not subset:
        raise ValueError("no dataset rows matched requested ids")

    _write_json(output_dir / dataset_path.name, subset)

    for sidecar_name in ("qrels.json", "gate_labels.json", "qrels_gap_allowlist.json"):
        sidecar_path = dataset_path.with_name(sidecar_name)
        if not sidecar_path.exists():
            continue
        sidecar = _load_json(sidecar_path)
        filtered = _filter_rows(sidecar, keep_ids)
        _write_json(output_dir / sidecar_name, filtered)


if __name__ == "__main__":
    main()
