# Project scope from the FYP proposal

The October 2026 proposal describes a **computer-vision-based pothole detection, geolocation and nearby-hazard alert** prototype for daylight paved roads around Biratnagar. This page is a development plan, not a claim that the proposed features already work.

## Intended flow

1. A consenting rider records a journey in a foreground **Android Expo app**. It saves video and timestamped GPS readings, then uploads after the rider has safely stopped.
2. **Django and Django REST Framework** accept authenticated uploads and retain the private capture session and GPS trace.
3. A separate worker runs OpenCV and YOLO on the uploaded video, tracks candidate potholes across frames, and estimates approximate locations from video/GPS timing.
4. A reviewer checks evidence, corrects locations, resolves suggested duplicates and approves hazards. Keep sightings and review history even when several sightings refer to one hazard.
5. Only verified hazards appear on the public Leaflet/OpenStreetMap map. A later foreground Android ride can announce nearby verified hazards with audio. An “ahead” warning needs validated direction and road context.

The phone does not run YOLO. Do not infer pothole depth or physical severity from ordinary video. Public map points are approximate; raw video and full routes remain private, and evidence images need face/plate privacy handling.

## Proposal objectives and evidence

| Objective | Proposed target | Current state |
|---|---|---|
| Android collection | 10 complete five-minute sessions with foreground GPS and upload after stopping | Not built. The iPhone browser recorder is a feasibility experiment only. |
| Dataset | About 1,500–2,500 selected labeled frames from at least 12 journeys on six road sections, including hard negatives | Not started. |
| Detection comparison | YOLO11n baseline versus fine-tuned YOLO26n and YOLO26s on held-out roads; compare quality, CPU time and complete job time | Not started. |
| Tracking | Review 30 sequences manually | Not started. |
| Geolocation | Reference locations for at least 20 distinct potholes; report median and 90th-percentile error | Not started. |
| Duplicate grouping | At least 30 labeled pairs, including nearby distinct potholes; measure false merges | Not started. |
| Backend and service | Django/DRF roles, PostgreSQL, reviewer workflow, verified-only map and foreground Android alerts | Django health routes and PostgreSQL connection work; the rest is not built. |
| Validation | System/timing checks and feedback from 5–8 consenting adults in stationary or controlled settings | Not started. |

Use road/journey separation for model evaluation so adjacent frames do not leak into the held-out set. The proposed schedule runs from October 2026 through May 2027. Android phone availability should be confirmed before planning a device test; the browser experiment does not establish Android behavior.

## Backend data-model progress

The first private **CaptureSession** model now stores an owner's recording start/end timestamps and creation time; see [Django lesson 3](django-step-3.md). Video upload is not implemented yet. Timestamped GPS readings and candidate sightings will follow in later lessons. A **Hazard** is the reviewed road defect that may combine sightings from multiple journeys. Review status belongs to this workflow; a latitude/longitude pair alone is not a public report.

There is a local, untracked `reports/models.py` draft with a coordinate-only `Report`. It has not been migrated as the proposal schema. Review that draft separately when the sighting and hazard models are designed.

The proposed minimalist 3D reviewer dashboard is a **visual reference only**. No frontend implementation or real hazard data is included in this milestone.
