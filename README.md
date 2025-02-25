# The Study of Debris Flows

1. Data organization
```
./data/
    ├── capacity.csv
    ├── BaileyBasin_20250125
    │   ├── pointcloud.las
    │   ├── dsm.tif  # DSM
    │   ├── dem.tif  # ground DEM
    │   └── height_references.csv  # reference heights
    ├── BaileyBasin_20250210
    │   └── ...
    ├── BaileyBasin_20250219
    │   └── ...
    └── Auburn_20250125
        └── ...
```

`capacity.csv` records the results of the capacity estimation. The `capacity_estimation.py` excludes the processed data in this file and appends new data:
```
Name, date, upper_spillway_capacity, lower_spillway_capacity, upper_crest_capacity, lower_crest_capacity
```

`height_references.csv` should include the reference heights for capacity estimation:
```
spillway_elevation, 310.0
crest_elevation, 312.0
```