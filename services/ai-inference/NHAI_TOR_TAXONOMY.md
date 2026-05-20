# NHAI TOR Detection Taxonomy

The inference contract supports the following anomaly codes from the NHAI TOR annexure. Actual detection accuracy depends on the model weights configured for each model group.

| Category | Anomaly Code | Label | Model Group |
| --- | --- | --- | --- |
| pavement | `pothole` | Potholes | `pavement_model` |
| pavement | `cracking` | Cracking | `pavement_model` |
| pavement | `rutting` | Rutting | `pavement_model` |
| shoulders | `rain_cut` | Rain Cuts | `shoulder_model` |
| shoulders | `edge_drop_uneven_shoulder` | Edge Drop & Unevenness of Shoulders | `shoulder_model` |
| shoulders | `vegetation_growth_shoulder` | Vegetation Growth on Shoulders | `shoulder_model` |
| kerb_median | `damaged_kerb` | Damaged Kerb | `kerb_median_model` |
| kerb_median | `faded_kerb_painting` | Faded Kerb Painting | `kerb_median_model` |
| plantation | `reduced_sight_distance_plantation` | Reduced Visibility/Sight Distance due to Plantation Growth | `plantation_model` |
| plantation | `missing_plants_irregular_gaps` | Missing Plants/Irregular Gaps in Plantation | `plantation_model` |
| plantation | `damaged_deteriorated_plants` | Deteriorated/Damaged Plants | `plantation_model` |
| drainage | `damaged_missing_drain_cover` | Damaged/Missing Cover Slabs over Drain | `drainage_model` |
| drainage | `water_stagnation` | Water Stagnation | `drainage_model` |
| footpath | `damaged_footpath` | Damaged Footpath | `footpath_model` |
| crash_barrier | `damaged_crash_barrier` | Damaged Crash Barrier | `crash_barrier_model` |
| crash_barrier | `faded_crash_barrier_painting` | Faded Painting of Crash Barrier & Guard Rail | `crash_barrier_model` |
| signboards_overhead_structures | `damaged_signboard` | Damaged Sign Boards/Sign Structures | `signage_model` |
| signboards_overhead_structures | `poor_signboard_visibility` | Visibility of Signages | `signage_model` |
| road_furniture | `damaged_blinker_attenuator_delineator_antiglare` | Damaged Blinkers/Attenuators/Delineators/Anti-Glare | `road_furniture_model` |
| road_furniture | `damaged_road_stud_rumble_strip_hazard_marker` | Damaged Road Studs/Rumble Strips/Hazard Markers | `road_furniture_model` |
| road_furniture | `poor_marker_visibility` | Visibility of Road Studs/Hazard Markers | `road_furniture_model` |
| pavement_marking | `faded_pavement_marking` | Faded Pavement Marking | `pavement_marking_model` |
| pavement_marking | `poor_pavement_marking_visibility` | Pavement Marking Visibility | `pavement_marking_model` |
| bus_bay_truck_lay_bye | `damaged_bus_shelter` | Damaged Bus Shelter | `bus_bay_model` |
| bus_bay_truck_lay_bye | `bus_bay_truck_lay_bye_defect` | Bus Bay/Truck Lay Bye Defect | `bus_bay_model` |
| highway_lighting | `damaged_highway_lighting` | Damaged Highway Lights | `lighting_model` |
| status | `road_clear` | Road Clear | `fallback` |

Configure multiple model weights with:

```text
YOLO_MODEL_NAMES=yolov8n.pt,best-pavement.pt,best-signage.pt
```

Optionally route model groups with:

```text
MODEL_GROUP_MODEL_NAMES=pavement_model=best-pavement.pt|best-crack.pt;signage_model=best-signage.pt
```

Class-to-anomaly mappings can be supplied with `MODEL_CLASS_MAPPINGS_JSON` lines:

```text
best-pavement.pt={"0":"pothole","1":"cracking","2":"rutting"}
best-signage.pt={"0":"damaged_signboard","1":"poor_signboard_visibility"}
```
