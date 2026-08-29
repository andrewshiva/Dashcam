import argparse
import random
import shutil
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def find_labeled_images(images_dir: Path, labels_dir: Path) -> list[Path]:
    images = sorted(
        path
        for path in images_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    return [image for image in images if (labels_dir / f"{image.stem}.txt").exists()]


def split_items(items: list[Path], train_ratio: float, val_ratio: float) -> dict[str, list[Path]]:
    train_end = int(len(items) * train_ratio)
    val_end = train_end + int(len(items) * val_ratio)
    return {
        "train": items[:train_end],
        "val": items[train_end:val_end],
        "test": items[val_end:],
    }


def copy_split(split_name: str, images: list[Path], source_labels: Path, dataset_root: Path) -> None:
    image_output = dataset_root / "images" / split_name
    label_output = dataset_root / "labels" / split_name
    image_output.mkdir(parents=True, exist_ok=True)
    label_output.mkdir(parents=True, exist_ok=True)

    for image in images:
        label = source_labels / f"{image.stem}.txt"
        shutil.copy2(image, image_output / image.name)
        shutil.copy2(label, label_output / label.name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split labeled YOLO images into train/val/test folders.")
    parser.add_argument("--dataset-root", default="training/datasets/nhai_road_anomalies")
    parser.add_argument("--images", default=None, help="Source labeled images folder.")
    parser.add_argument("--labels", default=None, help="Source labeled labels folder.")
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = Path(args.dataset_root)
    source_images = Path(args.images) if args.images else dataset_root / "images" / "labeled"
    source_labels = Path(args.labels) if args.labels else dataset_root / "labels" / "labeled"

    if not source_images.is_dir():
        raise SystemExit(f"Missing labeled images folder: {source_images}")
    if not source_labels.is_dir():
        raise SystemExit(f"Missing labeled labels folder: {source_labels}")
    if args.train_ratio <= 0 or args.val_ratio < 0 or args.train_ratio + args.val_ratio >= 1:
        raise SystemExit("Ratios must leave a non-zero test split. Example: train=0.8 val=0.15")

    items = find_labeled_images(source_images, source_labels)
    if not items:
        raise SystemExit("No image/label pairs found. Each image needs a matching .txt label file.")

    random.Random(args.seed).shuffle(items)
    splits = split_items(items, args.train_ratio, args.val_ratio)
    for split_name, split_images in splits.items():
        copy_split(split_name, split_images, source_labels, dataset_root)
        print(f"{split_name}: {len(split_images)} images")

    print(f"Done. Split {len(items)} image/label pairs under {dataset_root}")


if __name__ == "__main__":
    main()
