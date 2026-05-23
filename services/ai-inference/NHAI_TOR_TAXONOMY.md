# NHAI TOR Detection Taxonomy

The inference contract supports the following custom-training anomaly codes from the NHAI TOR annexure. `road_clear` is intentionally excluded; a clean road returns an empty detections list.

| Category | Anomaly Code | Label | Model Group |
| --- | --- | --- | --- |
| pavement | `pothole` | Potholes | `pavement_model` |
| pavement | `alligator_cracking` | Alligator Cracking | `pavement_model` |
| pavement | `rutting` | Rutting | `pavement_model` |
| pavement | `rain_cut` | Rain Cuts | `pavement_model` |
| shoulders | `edge_drop` | Edge Drop | `shoulder_model` |
| shoulders | `uneven_shoulder` | Uneven Shoulder | `shoulder_model` |
| shoulders | `shoulder_vegetation` | Shoulder Vegetation | `shoulder_model` |
| kerb_median | `broken_kerb` | Broken Kerb | `kerb_median_model` |
| kerb_median | `faded_kerb_paint` | Faded Kerb Paint | `kerb_median_model` |
| kerb_median | `median_obstruction` | Median Obstruction | `kerb_median_model` |
| plantation | `missing_plantation` | Missing Plantation | `plantation_model` |
| plantation | `dead_plantation` | Dead Plantation | `plantation_model` |
| plantation | `overgrown_plantation` | Overgrown Plantation | `plantation_model` |
| drainage | `missing_drain_cover` | Missing Drain Cover | `drainage_model` |
| drainage | `water_stagnation` | Water Stagnation | `drainage_model` |
| drainage | `drain_blockage` | Drain Blockage | `drainage_model` |
| footpath | `broken_paver_blocks` | Broken Paver Blocks | `footpath_model` |
| footpath | `missing_tiles` | Missing Tiles | `footpath_model` |
| footpath | `uneven_footpath` | Uneven Footpath | `footpath_model` |
| crash_barrier | `damaged_cc_barrier` | Damaged CC Barrier | `crash_barrier_model` |
| crash_barrier | `bent_guard_rail` | Bent Guard Rail | `crash_barrier_model` |
| crash_barrier | `faded_mbcb_paint` | Faded MBCB Paint | `crash_barrier_model` |
| signboards_overhead_structures | `damaged_signboard` | Damaged Signboards | `signage_model` |
| signboards_overhead_structures | `missing_retroreflective_sheeting` | Missing Retroreflective Sheeting | `signage_model` |
| signboards_overhead_structures | `illegible_overhead_sign` | Illegible Overhead Signs | `signage_model` |
| signboards_overhead_structures | `poor_night_visibility` | Poor Night Visibility | `signage_model` |
| road_furniture | `damaged_blinker` | Damaged Blinkers | `road_furniture_model` |
| road_furniture | `broken_delineator` | Broken Delineators | `road_furniture_model` |
| road_furniture | `damaged_attenuator` | Damaged Attenuators | `road_furniture_model` |
| road_furniture | `anti_glare_screen_damage` | Anti-Glare Screen Damage | `road_furniture_model` |
| pavement_marking | `faded_lane_marking` | Faded Lane Marking | `pavement_marking_model` |
| pavement_marking | `missing_lane_marking` | Missing Lane Marking | `pavement_marking_model` |
| pavement_marking | `damaged_road_stud` | Damaged Road Studs | `pavement_marking_model` |
| pavement_marking | `worn_rumble_strip` | Worn Rumble Strips | `pavement_marking_model` |
| bus_bay_truck_lay_bye | `damaged_bus_shelter` | Damaged Bus Shelter | `bus_bay_model` |
| bus_bay_truck_lay_bye | `faded_bus_bay_marking` | Faded Bus Bay Marking | `bus_bay_model` |
| bus_bay_truck_lay_bye | `damaged_lay_by_sign` | Damaged Lay-By Sign | `bus_bay_model` |
| highway_lighting | `broken_streetlight` | Broken Streetlight | `lighting_model` |
| highway_lighting | `non_functional_lighting` | Non-Functional Lighting | `lighting_model` |
| highway_lighting | `dark_highway_segment` | Dark Highway Segment | `lighting_model` |

Configure multiple model weights with:

```text
YOLO_MODEL_NAMES=yolov8n.pt,best-pavement.pt,best-signage.pt
```

Optionally route model groups with:

```text
MODEL_GROUP_MODEL_NAMES=pavement_model=best-pavement.pt|best-crack.pt;signage_model=best-signage.pt
```

If a custom YOLO model is trained with the class names in `training/nhai_anomalies.yaml`, inference maps class names automatically. `MODEL_CLASS_MAPPINGS_JSON` is only needed when deployed model class names differ from these anomaly codes.
