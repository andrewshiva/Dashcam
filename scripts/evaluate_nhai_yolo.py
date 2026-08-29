import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a trained NHAI YOLO model on a held-out test split.")
    parser.add_argument("--weights", required=True, help="Path to trained YOLO weights, for example best.pt.")
    parser.add_argument("--data", default="training/nhai_anomalies_test1000.yaml", help="YOLO dataset YAML.")
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default=None, help="Example: 0, cpu, or leave empty for auto.")
    parser.add_argument("--project", default="training/runs/eval")
    parser.add_argument("--name", default="test1000")
    parser.add_argument("--conf", type=float, default=0.001)
    parser.add_argument("--iou", type=float, default=0.7)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--save-json", action="store_true", help="Save COCO-style JSON predictions when supported.")
    parser.add_argument("--plots", action="store_true", help="Save confusion matrix and validation plots.")
    parser.add_argument("--exist-ok", action="store_true")
    return parser.parse_args()


def metric_value(obj: object, name: str) -> float | None:
    value = getattr(obj, name, None)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    args = parse_args()
    weights = Path(args.weights).resolve()
    data_yaml = Path(args.data).resolve()

    if not weights.exists():
        raise SystemExit(f"Missing weights file: {weights}")
    if not data_yaml.exists():
        raise SystemExit(f"Missing dataset YAML: {data_yaml}")

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit("Missing ultralytics. Install the AI inference requirements or run: pip install ultralytics") from exc

    model = YOLO(str(weights))
    results = model.val(
        data=str(data_yaml),
        split=args.split,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        conf=args.conf,
        iou=args.iou,
        workers=args.workers,
        save_json=args.save_json,
        plots=args.plots,
        exist_ok=args.exist_ok,
    )

    print(f"Evaluation complete: {results.save_dir}")
    box_metrics = getattr(results, "box", None)
    if box_metrics is not None:
        for label, attr in [("mAP50-95", "map"), ("mAP50", "map50"), ("mAP75", "map75")]:
            value = metric_value(box_metrics, attr)
            if value is not None:
                print(f"{label}: {value:.4f}")


if __name__ == "__main__":
    main()
