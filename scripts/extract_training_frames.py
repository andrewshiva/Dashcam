import argparse
from pathlib import Path

import cv2


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def iter_videos(input_path: Path) -> list[Path]:
    if input_path.is_file() and input_path.suffix.lower() in VIDEO_EXTENSIONS:
        return [input_path]
    if input_path.is_dir():
        return sorted(
            path
            for path in input_path.rglob("*")
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
        )
    return []


def unique_output_path(output_dir: Path, video_path: Path, frame_index: int) -> Path:
    stem = video_path.stem.replace(" ", "_")
    return output_dir / f"{stem}_frame_{frame_index:06d}.jpg"


def extract_frames(
    video_path: Path,
    output_dir: Path,
    seconds: float,
    every_n_frames: int | None,
    max_frames: int | None,
    quality: int,
) -> int:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Skipped unreadable video: {video_path}")
        return 0

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    interval = every_n_frames or max(1, int(round(fps * seconds)))
    frame_index = 0
    saved = 0

    while True:
        success, frame = cap.read()
        if not success:
            break

        if frame_index % interval == 0:
            output_path = unique_output_path(output_dir, video_path, frame_index)
            cv2.imwrite(str(output_path), frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            saved += 1
            if max_frames is not None and saved >= max_frames:
                break

        frame_index += 1

    cap.release()
    print(f"{video_path.name}: saved {saved} frames")
    return saved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract dashcam video frames for YOLO labeling.")
    parser.add_argument("--input", default="Sample", help="Video file or folder containing videos.")
    parser.add_argument(
        "--output",
        default="training/datasets/nhai_road_anomalies/images/unlabeled",
        help="Folder where extracted frames will be written.",
    )
    parser.add_argument("--seconds", type=float, default=2.0, help="Seconds between sampled frames.")
    parser.add_argument("--every-n-frames", type=int, default=None, help="Override sampling interval by frame count.")
    parser.add_argument("--max-frames-per-video", type=int, default=None, help="Optional cap per source video.")
    parser.add_argument("--quality", type=int, default=92, help="JPEG quality from 1 to 100.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    videos = iter_videos(input_path)
    if not videos:
        raise SystemExit(f"No videos found under {input_path}")

    total = 0
    for video_path in videos:
        total += extract_frames(
            video_path=video_path,
            output_dir=output_dir,
            seconds=args.seconds,
            every_n_frames=args.every_n_frames,
            max_frames=args.max_frames_per_video,
            quality=max(1, min(100, args.quality)),
        )

    print(f"Done. Saved {total} frames to {output_dir}")


if __name__ == "__main__":
    main()
