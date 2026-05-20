NHAI_TOR_ANOMALIES = {
    "pothole": {
        "category": "pavement",
        "label": "Potholes",
        "model_group": "pavement_model",
    },
    "cracking": {
        "category": "pavement",
        "label": "Cracking",
        "model_group": "pavement_model",
    },
    "rutting": {
        "category": "pavement",
        "label": "Rutting",
        "model_group": "pavement_model",
    },
    "rain_cut": {
        "category": "shoulders",
        "label": "Rain Cuts",
        "model_group": "shoulder_model",
    },
    "edge_drop_uneven_shoulder": {
        "category": "shoulders",
        "label": "Edge Drop & Unevenness of Shoulders",
        "model_group": "shoulder_model",
    },
    "vegetation_growth_shoulder": {
        "category": "shoulders",
        "label": "Vegetation Growth on Shoulders",
        "model_group": "shoulder_model",
    },
    "damaged_kerb": {
        "category": "kerb_median",
        "label": "Damaged Kerb",
        "model_group": "kerb_median_model",
    },
    "faded_kerb_painting": {
        "category": "kerb_median",
        "label": "Faded Kerb Painting",
        "model_group": "kerb_median_model",
    },
    "reduced_sight_distance_plantation": {
        "category": "plantation",
        "label": "Reduced Visibility/Sight Distance due to Plantation Growth",
        "model_group": "plantation_model",
    },
    "missing_plants_irregular_gaps": {
        "category": "plantation",
        "label": "Missing Plants/Irregular Gaps in Plantation",
        "model_group": "plantation_model",
    },
    "damaged_deteriorated_plants": {
        "category": "plantation",
        "label": "Deteriorated/Damaged Plants",
        "model_group": "plantation_model",
    },
    "damaged_missing_drain_cover": {
        "category": "drainage",
        "label": "Damaged/Missing Cover Slabs over Drain",
        "model_group": "drainage_model",
    },
    "water_stagnation": {
        "category": "drainage",
        "label": "Water Stagnation",
        "model_group": "drainage_model",
    },
    "damaged_footpath": {
        "category": "footpath",
        "label": "Damaged Footpath",
        "model_group": "footpath_model",
    },
    "damaged_crash_barrier": {
        "category": "crash_barrier",
        "label": "Damaged Crash Barrier",
        "model_group": "crash_barrier_model",
    },
    "faded_crash_barrier_painting": {
        "category": "crash_barrier",
        "label": "Faded Painting of Crash Barrier & Guard Rail",
        "model_group": "crash_barrier_model",
    },
    "damaged_signboard": {
        "category": "signboards_overhead_structures",
        "label": "Damaged Sign Boards/Sign Structures",
        "model_group": "signage_model",
    },
    "poor_signboard_visibility": {
        "category": "signboards_overhead_structures",
        "label": "Visibility of Signages",
        "model_group": "signage_model",
    },
    "damaged_blinker_attenuator_delineator_antiglare": {
        "category": "road_furniture",
        "label": "Damaged Blinkers/Attenuators/Delineators/Anti-Glare",
        "model_group": "road_furniture_model",
    },
    "damaged_road_stud_rumble_strip_hazard_marker": {
        "category": "road_furniture",
        "label": "Damaged Road Studs/Rumble Strips/Hazard Markers",
        "model_group": "road_furniture_model",
    },
    "poor_marker_visibility": {
        "category": "road_furniture",
        "label": "Visibility of Road Studs/Hazard Markers",
        "model_group": "road_furniture_model",
    },
    "faded_pavement_marking": {
        "category": "pavement_marking",
        "label": "Faded Pavement Marking",
        "model_group": "pavement_marking_model",
    },
    "poor_pavement_marking_visibility": {
        "category": "pavement_marking",
        "label": "Pavement Marking Visibility",
        "model_group": "pavement_marking_model",
    },
    "damaged_bus_shelter": {
        "category": "bus_bay_truck_lay_bye",
        "label": "Damaged Bus Shelter",
        "model_group": "bus_bay_model",
    },
    "bus_bay_truck_lay_bye_defect": {
        "category": "bus_bay_truck_lay_bye",
        "label": "Bus Bay/Truck Lay Bye Defect",
        "model_group": "bus_bay_model",
    },
    "damaged_highway_lighting": {
        "category": "highway_lighting",
        "label": "Damaged Highway Lights",
        "model_group": "lighting_model",
    },
    "road_clear": {
        "category": "status",
        "label": "Road Clear",
        "model_group": "fallback",
    },
}

MODEL_GROUPS = {
    anomaly["model_group"]
    for anomaly in NHAI_TOR_ANOMALIES.values()
}


def anomaly_metadata(anomaly_code: str) -> dict:
    anomaly = NHAI_TOR_ANOMALIES.get(anomaly_code, {})
    return {
        "anomaly_code": anomaly_code,
        "category": anomaly.get("category", "unknown"),
        "label": anomaly.get("label", anomaly_code.replace("_", " ").title()),
        "model_group": anomaly.get("model_group", "unknown"),
    }
