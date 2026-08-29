# NHAI Custom YOLO Training

This folder contains the training contract for the 40 NHAI anomaly classes. The class names in `nhai_anomalies.yaml` are anomaly codes on purpose: the inference service can map custom YOLO class names directly back to the application taxonomy.

`dataset_sources.yaml` records the source plan for each anomaly, including whether it can start from a public dataset or needs custom NHAI dashcam annotation.

`dataset_recommendations.yaml` is the working source manifest for the current 40-class plan. It names the best public seed dataset where one exists, and marks the classes that still require custom NHAI dashcam labeling. `test_plan_1000.yaml` defines the acceptance-test target: 1,000 labeled images, balanced as 25 images for each of the 40 anomaly classes.

## Dataset Layout

After labeling and splitting, the dataset should look like this:

```text
training/datasets/nhai_road_anomalies/
  images/
    train/
    val/
    test/
  labels/
    train/
    val/
    test/
```

Each label file uses YOLO detection format:

```text
class_id x_center y_center width height
```

Coordinates must be normalized from `0` to `1`. Empty `.txt` files are valid for negative images with no anomaly.

## Workflow

1. Extract frames for annotation:

```powershell
python scripts/extract_training_frames.py --input Sample --seconds 2 --max-frames-per-video 200
```

2. Label the extracted images with the class order in `training/nhai_anomalies.yaml`.

   For polygon or segmentation sources, export polygons/masks as YOLO boxes for this detector. Keep the original masks if you later train YOLO segmentation models for markings, rutting, water, vegetation, or lighting regions.

3. Export labeled images to:

```text
training/datasets/nhai_road_anomalies/images/labeled
training/datasets/nhai_road_anomalies/labels/labeled
```

4. Split labeled data into train/val/test:

```powershell
python scripts/split_yolo_dataset.py
```

5. Validate before training:

```powershell
python scripts/train_nhai_yolo.py --dry-run
```

6. Train:

```powershell
python scripts/train_nhai_yolo.py --model yolov8n.pt --epochs 100 --imgsz 960 --batch 8
```

The trained weights are written under `training/runs/`. Use the `weights/best.pt` file for deployment.

## 1000-Image Test Set

Build the held-out test subset after the `test` split has labeled images:

```powershell
python scripts/build_yolo_test_subset.py --total 1000
```

This creates:

```text
training/datasets/nhai_road_anomalies_test1000/
training/nhai_anomalies_test1000.yaml
training/testset_1000_report.json
```

The builder defaults to `images/test` and `labels/test` so the evaluation remains held out. For an early smoke test from unsplit labeled data, make the fallback explicit:

```powershell
python scripts/build_yolo_test_subset.py --source-splits labeled --total 1000 --dry-run
```

Run evaluation once trained weights exist:

```powershell
python scripts/evaluate_nhai_yolo.py --weights training/runs/nhai-yolov8/weights/best.pt --data training/nhai_anomalies_test1000.yaml --plots
```

The minimum usable gate is 10 labeled test images per class. The recommended gate is 25 per class, which gives the requested 1,000-image test.

## Deployment Note

If the trained model keeps the class names from `nhai_anomalies.yaml`, set:

```text
YOLO_MODEL_NAMES=best.pt
```

No `MODEL_CLASS_MAPPINGS_JSON` override is needed because inference can read the model class names and map them to anomaly codes.
