import argparse
import json
from pathlib import Path

import yaml


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def load_data_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid dataset YAML: {path}")
    return data


def resolve_dataset_path(data_yaml: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (data_yaml.parent / path).resolve()


def class_names(data: dict) -> list[str]:
    names = data.get("names")
    if isinstance(names, dict):
        return [names[key] for key in sorted(names, key=lambda item: int(item))]
    if isinstance(names, list):
        return names
    raise SystemExit("Dataset YAML must define names as a list or class-id dictionary.")


def image_count(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for item in path.iterdir() if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS)


def validate_label_file(path: Path, number_of_classes: int) -> list[str]:
    errors = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            errors.append(f"{path}:{line_number} has fewer than 5 YOLO fields")
            continue
        try:
            class_id = int(float(parts[0]))
        except ValueError:
            errors.append(f"{path}:{line_number} has invalid class id {parts[0]!r}")
            continue
        if class_id < 0 or class_id >= number_of_classes:
            errors.append(f"{path}:{line_number} class id {class_id} is outside 0..{number_of_classes - 1}")
    return errors


def validate_dataset(data_yaml: Path, data: dict) -> tuple[Path, list[str]]:
    names = class_names(data)
    root = resolve_dataset_path(data_yaml, data.get("path", "."))
    errors = []

    for split in ["train", "val"]:
        image_dir = root / data[split]
        label_dir = root / data[split].replace("images", "labels", 1)
        count = image_count(image_dir)
        if count == 0:
            errors.append(f"No images found for {split}: {image_dir}")
        if not label_dir.is_dir():
            errors.append(f"Missing labels folder for {split}: {label_dir}")
            continue
        for label_file in label_dir.glob("*.txt"):
            errors.extend(validate_label_file(label_file, len(names)))

    if errors:
        message = "\n".join(f"- {error}" for error in errors[:40])
        if len(errors) > 40:
            message += f"\n- ...and {len(errors) - 40} more errors"
        raise SystemExit(f"Dataset is not ready for training:\n{message}")

    return root, names


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train an NHAI anomaly YOLO detector.")
    parser.add_argument("--data", default="training/nhai_anomalies.yaml", help="YOLO dataset YAML.")
    parser.add_argument("--model", default="yolov8n.pt", help="Base YOLO model or checkpoint.")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=960)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default=None, help="Example: 0, cpu, or leave empty for auto.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--patience", type=int, default=30)
    parser.add_argument("--project", default="training/runs")
    parser.add_argument("--name", default="nhai-yolov8")
    parser.add_argument("--cache", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--exist-ok", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Validate data and print training settings only.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_yaml = Path(args.data).resolve()
    data = load_data_config(data_yaml)
    root, names = validate_dataset(data_yaml, data)

    mapping = {str(index): name for index, name in enumerate(names)}
    print(f"Dataset root: {root}")
    print(f"Classes: {len(names)}")
    print("Class mapping:")
    print(json.dumps(mapping, indent=2))

    if args.dry_run:
        print("Dry run passed. Dataset is ready for YOLO training.")
        return

    from ultralytics import YOLO

    model = YOLO(args.model)
    results = model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        patience=args.patience,
        project=args.project,
        name=args.name,
        cache=args.cache,
        resume=args.resume,
        exist_ok=args.exist_ok,
    )

    save_dir = Path(results.save_dir)
    best_weights = save_dir / "weights" / "best.pt"
    print(f"Training complete: {save_dir}")
    print(f"Best weights: {best_weights}")
    print("Inference can auto-map classes because model class names match anomaly codes.")


if __name__ == "__main__":
    main()
