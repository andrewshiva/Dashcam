import argparse
import json
import random
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


@dataclass(frozen=True)
class CandidateImage:
    image_path: Path
    label_path: Path
    source_split: str
    relative_path: Path
    class_ids: frozenset[int]

    @property
    def key(self) -> str:
        return str(self.image_path.resolve())


def load_dataset_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid dataset YAML: {path}")
    return data


def class_names(data: dict) -> list[str]:
    names = data.get("names")
    if isinstance(names, dict):
        return [names[key] for key in sorted(names, key=lambda item: int(item))]
    if isinstance(names, list):
        return names
    raise SystemExit("Dataset YAML must define names as a list or class-id dictionary.")


def resolve_dataset_root(data_yaml: Path, data: dict, override: str | None) -> Path:
    if override:
        return Path(override).resolve()
    root = Path(data.get("path", "."))
    if root.is_absolute():
        return root
    return (data_yaml.parent / root).resolve()


def parse_source_splits(value: str) -> list[str]:
    splits = [item.strip() for item in value.split(",") if item.strip()]
    if not splits:
        raise SystemExit("At least one source split is required.")
    return splits


def parse_label_file(path: Path, number_of_classes: int) -> tuple[set[int], list[str]]:
    class_ids: set[int] = set()
    errors: list[str] = []
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
            continue
        class_ids.add(class_id)
    return class_ids, errors


def find_images(image_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in image_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def scan_split(
    dataset_root: Path,
    split: str,
    number_of_classes: int,
) -> tuple[list[CandidateImage], list[str]]:
    image_dir = dataset_root / "images" / split
    label_dir = dataset_root / "labels" / split
    warnings: list[str] = []
    candidates: list[CandidateImage] = []

    if not image_dir.is_dir():
        warnings.append(f"Missing images folder for split '{split}': {image_dir}")
        return candidates, warnings
    if not label_dir.is_dir():
        warnings.append(f"Missing labels folder for split '{split}': {label_dir}")
        return candidates, warnings

    missing_labels = 0
    empty_labels = 0
    invalid_labels = 0
    for image_path in find_images(image_dir):
        relative_path = image_path.relative_to(image_dir)
        label_path = (label_dir / relative_path).with_suffix(".txt")
        if not label_path.exists():
            missing_labels += 1
            continue
        class_ids, errors = parse_label_file(label_path, number_of_classes)
        if errors:
            invalid_labels += 1
            warnings.extend(errors[:5])
            continue
        if not class_ids:
            empty_labels += 1
            continue
        candidates.append(
            CandidateImage(
                image_path=image_path,
                label_path=label_path,
                source_split=split,
                relative_path=relative_path,
                class_ids=frozenset(class_ids),
            )
        )

    if missing_labels:
        warnings.append(f"Skipped {missing_labels} image(s) in split '{split}' with no matching label file.")
    if empty_labels:
        warnings.append(f"Skipped {empty_labels} negative/empty label image(s) in split '{split}'.")
    if invalid_labels:
        warnings.append(f"Skipped {invalid_labels} image(s) in split '{split}' with invalid labels.")
    return candidates, warnings


def class_targets(number_of_classes: int, total: int, per_class: int | None) -> dict[int, int]:
    if total < number_of_classes:
        raise SystemExit(f"--total must be at least the number of classes ({number_of_classes}).")
    if per_class is not None:
        if per_class <= 0:
            raise SystemExit("--per-class must be greater than zero.")
        if per_class * number_of_classes > total:
            raise SystemExit("--total must be at least --per-class times the number of classes.")
        return {class_id: per_class for class_id in range(number_of_classes)}

    base, remainder = divmod(total, number_of_classes)
    return {
        class_id: base + (1 if class_id < remainder else 0)
        for class_id in range(number_of_classes)
    }


def select_balanced_subset(
    candidates: list[CandidateImage],
    targets: dict[int, int],
    total: int,
    seed: int,
) -> tuple[list[CandidateImage], Counter[int]]:
    rng = random.Random(seed)
    shuffled = list(candidates)
    rng.shuffle(shuffled)

    by_class: dict[int, list[CandidateImage]] = defaultdict(list)
    for candidate in shuffled:
        for class_id in candidate.class_ids:
            by_class[class_id].append(candidate)

    selected: list[CandidateImage] = []
    selected_keys: set[str] = set()
    counts: Counter[int] = Counter()

    while len(selected) < total:
        progress = False
        ordered_classes = sorted(targets, key=lambda class_id: (counts[class_id] - targets[class_id], class_id))
        for class_id in ordered_classes:
            if len(selected) >= total:
                break
            if counts[class_id] >= targets[class_id]:
                continue
            best = next(
                (
                    candidate
                    for candidate in by_class.get(class_id, [])
                    if candidate.key not in selected_keys
                ),
                None,
            )
            if not best:
                continue
            selected.append(best)
            selected_keys.add(best.key)
            for detected_class_id in best.class_ids:
                counts[detected_class_id] += 1
            progress = True
        if not progress:
            break

    if len(selected) < total:
        remaining = [candidate for candidate in shuffled if candidate.key not in selected_keys]
        remaining.sort(
            key=lambda candidate: (
                -sum(max(targets[class_id] - counts[class_id], 0) for class_id in candidate.class_ids),
                candidate.source_split,
                str(candidate.relative_path),
            )
        )
        for candidate in remaining:
            if len(selected) >= total:
                break
            selected.append(candidate)
            selected_keys.add(candidate.key)
            for detected_class_id in candidate.class_ids:
                counts[detected_class_id] += 1

    return selected, counts


def path_as_posix(path: Path) -> str:
    return path.as_posix()


def relative_path_for_yaml(output_yaml: Path, output_root: Path) -> str:
    try:
        return path_as_posix(output_root.resolve().relative_to(output_yaml.parent.resolve()))
    except ValueError:
        return path_as_posix(output_root.resolve())


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def ensure_clean_output(output_root: Path, clear: bool) -> None:
    output_root = output_root.resolve()
    workspace = Path.cwd().resolve()
    if not is_relative_to(output_root, workspace):
        raise SystemExit(f"Refusing to manage output outside the workspace: {output_root}")

    if clear and output_root.exists():
        shutil.rmtree(output_root)
        return

    image_output = output_root / "images" / "test"
    label_output = output_root / "labels" / "test"
    existing_files = []
    for folder in [image_output, label_output]:
        if folder.exists():
            existing_files.extend(path for path in folder.rglob("*") if path.is_file())
    if existing_files:
        raise SystemExit(f"Output already contains files. Re-run with --clear to rebuild: {output_root}")


def copy_selected_images(selected: list[CandidateImage], output_root: Path) -> None:
    image_output = output_root / "images" / "test"
    label_output = output_root / "labels" / "test"
    image_output.mkdir(parents=True, exist_ok=True)
    label_output.mkdir(parents=True, exist_ok=True)

    for candidate in selected:
        destination_relative = Path(candidate.source_split) / candidate.relative_path
        destination_image = image_output / destination_relative
        destination_label = (label_output / destination_relative).with_suffix(".txt")
        destination_image.parent.mkdir(parents=True, exist_ok=True)
        destination_label.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate.image_path, destination_image)
        shutil.copy2(candidate.label_path, destination_label)


def write_test_yaml(output_yaml: Path, output_root: Path, names: list[str]) -> None:
    output_yaml.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "path": relative_path_for_yaml(output_yaml, output_root),
        "train": "images/test",
        "val": "images/test",
        "test": "images/test",
        "names": {index: name for index, name in enumerate(names)},
    }
    with output_yaml.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def build_report(
    *,
    data_yaml: Path,
    dataset_root: Path,
    output_root: Path,
    output_yaml: Path,
    report_path: Path,
    source_splits: list[str],
    names: list[str],
    candidates: list[CandidateImage],
    selected: list[CandidateImage],
    counts: Counter[int],
    targets: dict[int, int],
    total: int,
    minimum_gate: int,
    warnings: list[str],
) -> dict:
    per_class_counts = {names[class_id]: counts[class_id] for class_id in range(len(names))}
    per_class_targets = {names[class_id]: targets[class_id] for class_id in range(len(names))}
    missing_classes = [name for name, count in per_class_counts.items() if count == 0]
    below_minimum_gate = [name for name, count in per_class_counts.items() if count < minimum_gate]
    below_recommended_gate = [
        names[class_id]
        for class_id in range(len(names))
        if counts[class_id] < targets[class_id]
    ]
    selected_files = [
        path_as_posix(Path(candidate.source_split) / candidate.relative_path)
        for candidate in selected
    ]

    return {
        "data_yaml": path_as_posix(data_yaml),
        "dataset_root": path_as_posix(dataset_root),
        "output_root": path_as_posix(output_root),
        "output_yaml": path_as_posix(output_yaml),
        "report_path": path_as_posix(report_path),
        "source_splits": source_splits,
        "requested_total_images": total,
        "selected_images": len(selected),
        "candidate_images": len(candidates),
        "target_images_per_class": {
            "minimum": min(targets.values()),
            "maximum": max(targets.values()),
        },
        "minimum_gate_images_per_class": minimum_gate,
        "enough_for_minimum_gate": len(selected) >= minimum_gate * len(names) and not below_minimum_gate,
        "enough_for_recommended_gate": len(selected) >= total and not below_recommended_gate,
        "per_class_counts": per_class_counts,
        "per_class_targets": per_class_targets,
        "missing_classes": missing_classes,
        "below_minimum_gate": below_minimum_gate,
        "below_recommended_gate": below_recommended_gate,
        "warnings": warnings,
        "selected_files": selected_files,
    }


def write_report(report_path: Path, report: dict) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a balanced 1000-image YOLO test subset for NHAI anomalies.")
    parser.add_argument("--data", default="training/nhai_anomalies.yaml", help="Source YOLO dataset YAML.")
    parser.add_argument("--dataset-root", default=None, help="Override dataset root. Defaults to the YAML path value.")
    parser.add_argument("--source-splits", default="test", help="Comma-separated source splits, for example: test,val")
    parser.add_argument("--output-root", default="training/datasets/nhai_road_anomalies_test1000")
    parser.add_argument("--output-yaml", default="training/nhai_anomalies_test1000.yaml")
    parser.add_argument("--report", default="training/testset_1000_report.json")
    parser.add_argument("--total", type=int, default=1000)
    parser.add_argument("--per-class", type=int, default=None, help="Target images per class. Defaults to total/classes.")
    parser.add_argument("--minimum-gate", type=int, default=10, help="Minimum images per class to mark the test as usable.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--clear", action="store_true", help="Delete and rebuild the output root after safety checks.")
    parser.add_argument("--dry-run", action="store_true", help="Print the report without copying files or writing outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_yaml = Path(args.data).resolve()
    data = load_dataset_yaml(data_yaml)
    names = class_names(data)
    dataset_root = resolve_dataset_root(data_yaml, data, args.dataset_root)
    source_splits = parse_source_splits(args.source_splits)
    output_root = Path(args.output_root).resolve()
    output_yaml = Path(args.output_yaml).resolve()
    report_path = Path(args.report).resolve()
    targets = class_targets(len(names), args.total, args.per_class)

    all_candidates: list[CandidateImage] = []
    warnings: list[str] = []
    for split in source_splits:
        candidates, split_warnings = scan_split(dataset_root, split, len(names))
        all_candidates.extend(candidates)
        warnings.extend(split_warnings)

    selected, counts = select_balanced_subset(all_candidates, targets, args.total, args.seed)
    report = build_report(
        data_yaml=data_yaml,
        dataset_root=dataset_root,
        output_root=output_root,
        output_yaml=output_yaml,
        report_path=report_path,
        source_splits=source_splits,
        names=names,
        candidates=all_candidates,
        selected=selected,
        counts=counts,
        targets=targets,
        total=args.total,
        minimum_gate=args.minimum_gate,
        warnings=warnings,
    )

    if args.dry_run:
        print(json.dumps(report, indent=2))
        return

    ensure_clean_output(output_root, args.clear)
    copy_selected_images(selected, output_root)
    write_test_yaml(output_yaml, output_root, names)
    write_report(report_path, report)

    print(f"Selected images: {len(selected)} / {args.total}")
    print(f"Test YAML: {output_yaml}")
    print(f"Report: {report_path}")
    if report["enough_for_recommended_gate"]:
        print("Requested test gate passed.")
    elif report["below_recommended_gate"]:
        print("Some classes are below the recommended gate; see the report for details.")
    else:
        print("Per-class gate passed, but the selected image count is below the requested total.")


if __name__ == "__main__":
    main()
