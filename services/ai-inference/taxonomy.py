NHAI_TOR_ANOMALIES = {
    "pothole": {
        "category": "pavement",
        "label": "Potholes",
        "model_group": "pavement_model",
    },
    "alligator_cracking": {
        "category": "pavement",
        "label": "Alligator Cracking",
        "model_group": "pavement_model",
    },
    "rutting": {
        "category": "pavement",
        "label": "Rutting",
        "model_group": "pavement_model",
    },
    "rain_cut": {
        "category": "pavement",
        "label": "Rain Cuts",
        "model_group": "pavement_model",
    },
    "edge_drop": {
        "category": "shoulders",
        "label": "Edge Drop",
        "model_group": "shoulder_model",
    },
    "uneven_shoulder": {
        "category": "shoulders",
        "label": "Uneven Shoulder",
        "model_group": "shoulder_model",
    },
    "shoulder_vegetation": {
        "category": "shoulders",
        "label": "Shoulder Vegetation",
        "model_group": "shoulder_model",
    },
    "broken_kerb": {
        "category": "kerb_median",
        "label": "Broken Kerb",
        "model_group": "kerb_median_model",
    },
    "faded_kerb_paint": {
        "category": "kerb_median",
        "label": "Faded Kerb Paint",
        "model_group": "kerb_median_model",
    },
    "median_obstruction": {
        "category": "kerb_median",
        "label": "Median Obstruction",
        "model_group": "kerb_median_model",
    },
    "missing_plantation": {
        "category": "plantation",
        "label": "Missing Plantation",
        "model_group": "plantation_model",
    },
    "dead_plantation": {
        "category": "plantation",
        "label": "Dead Plantation",
        "model_group": "plantation_model",
    },
    "overgrown_plantation": {
        "category": "plantation",
        "label": "Overgrown Plantation",
        "model_group": "plantation_model",
    },
    "missing_drain_cover": {
        "category": "drainage",
        "label": "Missing Drain Cover",
        "model_group": "drainage_model",
    },
    "water_stagnation": {
        "category": "drainage",
        "label": "Water Stagnation",
        "model_group": "drainage_model",
    },
    "drain_blockage": {
        "category": "drainage",
        "label": "Drain Blockage",
        "model_group": "drainage_model",
    },
    "broken_paver_blocks": {
        "category": "footpath",
        "label": "Broken Paver Blocks",
        "model_group": "footpath_model",
    },
    "missing_tiles": {
        "category": "footpath",
        "label": "Missing Tiles",
        "model_group": "footpath_model",
    },
    "uneven_footpath": {
        "category": "footpath",
        "label": "Uneven Footpath",
        "model_group": "footpath_model",
    },
    "damaged_cc_barrier": {
        "category": "crash_barrier",
        "label": "Damaged CC Barrier",
        "model_group": "crash_barrier_model",
    },
    "bent_guard_rail": {
        "category": "crash_barrier",
        "label": "Bent Guard Rail",
        "model_group": "crash_barrier_model",
    },
    "faded_mbcb_paint": {
        "category": "crash_barrier",
        "label": "Faded MBCB Paint",
        "model_group": "crash_barrier_model",
    },
    "damaged_signboard": {
        "category": "signboards_overhead_structures",
        "label": "Damaged Signboards",
        "model_group": "signage_model",
    },
    "missing_retroreflective_sheeting": {
        "category": "signboards_overhead_structures",
        "label": "Missing Retroreflective Sheeting",
        "model_group": "signage_model",
    },
    "illegible_overhead_sign": {
        "category": "signboards_overhead_structures",
        "label": "Illegible Overhead Signs",
        "model_group": "signage_model",
    },
    "poor_night_visibility": {
        "category": "signboards_overhead_structures",
        "label": "Poor Night Visibility",
        "model_group": "signage_model",
    },
    "damaged_blinker": {
        "category": "road_furniture",
        "label": "Damaged Blinkers",
        "model_group": "road_furniture_model",
    },
    "broken_delineator": {
        "category": "road_furniture",
        "label": "Broken Delineators",
        "model_group": "road_furniture_model",
    },
    "damaged_attenuator": {
        "category": "road_furniture",
        "label": "Damaged Attenuators",
        "model_group": "road_furniture_model",
    },
    "anti_glare_screen_damage": {
        "category": "road_furniture",
        "label": "Anti-Glare Screen Damage",
        "model_group": "road_furniture_model",
    },
    "faded_lane_marking": {
        "category": "pavement_marking",
        "label": "Faded Lane Marking",
        "model_group": "pavement_marking_model",
    },
    "missing_lane_marking": {
        "category": "pavement_marking",
        "label": "Missing Lane Marking",
        "model_group": "pavement_marking_model",
    },
    "damaged_road_stud": {
        "category": "pavement_marking",
        "label": "Damaged Road Studs",
        "model_group": "pavement_marking_model",
    },
    "worn_rumble_strip": {
        "category": "pavement_marking",
        "label": "Worn Rumble Strips",
        "model_group": "pavement_marking_model",
    },
    "damaged_bus_shelter": {
        "category": "bus_bay_truck_lay_bye",
        "label": "Damaged Bus Shelter",
        "model_group": "bus_bay_model",
    },
    "faded_bus_bay_marking": {
        "category": "bus_bay_truck_lay_bye",
        "label": "Faded Bus Bay Marking",
        "model_group": "bus_bay_model",
    },
    "damaged_lay_by_sign": {
        "category": "bus_bay_truck_lay_bye",
        "label": "Damaged Lay-By Sign",
        "model_group": "bus_bay_model",
    },
    "broken_streetlight": {
        "category": "highway_lighting",
        "label": "Broken Streetlight",
        "model_group": "lighting_model",
    },
    "non_functional_lighting": {
        "category": "highway_lighting",
        "label": "Non-Functional Lighting",
        "model_group": "lighting_model",
    },
    "dark_highway_segment": {
        "category": "highway_lighting",
        "label": "Dark Highway Segment",
        "model_group": "lighting_model",
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
