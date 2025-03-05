import numpy as np
import rasterio
from scipy.interpolate import griddata
import cv2
import laspy
import os
import copy
from rasterio.transform import from_origin

def clear_las():
    data_folders = [os.path.join('data', f) for f in os.listdir('data') if os.path.isdir(os.path.join('data', f))]
    # remove all las files in the data folder
    for folder in data_folders:
        files = os.listdir(folder)
        for f in files:
            if f.endswith('.las'):
                os.remove(os.path.join(folder, f))

def clear_data():
    data_folders = [os.path.join('data', f) for f in os.listdir('data') if os.path.isdir(os.path.join('data', f))]
    # remove all files in the data folder except .csv .las
    for folder in data_folders:
        files = os.listdir(folder)
        for f in files:
            if f.endswith('.csv') or f.endswith('.las'):
                continue
            os.remove(os.path.join(folder, f))

def interpolate_nodata(dem_data, nodata_value):
    """
    Interpolate and fill nodata cells in a 2D DEM array using
    a two-step approach:
      1) Linear interpolation (via griddata)
      2) Nearest-neighbor fallback for any unfilled cells

    Parameters
    ----------
    dem_data : 2D np.ndarray
        DEM array with valid elevation values and nodata_value for missing areas.
    nodata_value : float
        The value in dem_data that represents nodata/missing data.

    Returns
    -------
    filled_dem : 2D np.ndarray
        A copy of the DEM array with nodata cells filled.
        Cells that could not be filled remain with nodata_value.
    """

    # 1. Identify valid vs. nodata cells
    valid_mask = (dem_data != nodata_value)
    # If your DEM uses NaN for nodata, you can do valid_mask = ~np.isnan(dem_data).

    # find the largest contour of the valid_mask
    # contours, _ = cv2.findContours(valid_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # contours = sorted(contours, key=cv2.contourArea, reverse=True)
    # valid_mask_contour = np.zeros_like(dem_data, dtype=np.uint8)
    # cv2.drawContours(valid_mask_contour, contours, 0, 1, thickness=cv2.FILLED)
    
    # 2. Create arrays of x,y coordinates for every pixel
    rows, cols = dem_data.shape
    # Note: we use np.arange(cols) for x, np.arange(rows) for y
    # because array indexing is [row, col].
    # We'll build a meshgrid for consistent shape with dem_data
    X, Y = np.meshgrid(np.arange(cols), np.arange(rows))

    # 3. Prepare input points and values for interpolation
    # points : array of (x, y) for valid cells
    # values : corresponding elevation
    points = np.column_stack((X[valid_mask], Y[valid_mask]))
    values = dem_data[valid_mask].astype(float)

    # 4. First Pass: Linear interpolation across the full grid
    #    Some cells might remain NaN if they can't be linearly interpolated
    #    (e.g., entire row or large holes).
    dem_linear = griddata(points, values, (X, Y), method='linear')

    # 5. Identify which cells remain NaN after the linear pass
    #    We'll fill those with a second pass of 'nearest' interpolation
    #    to avoid big holes.
    still_nan_mask = np.isnan(dem_linear)

    # 6. Second Pass: Nearest-neighbor interpolation for the leftover NaNs
    dem_nearest = griddata(points, values, (X, Y), method='nearest')

    # 7. Combine the two results:
    #    - If linear pass gave a valid number, use it
    #    - Else, use nearest-neighbor
    #    - If something is still NaN (extremely rare), keep nodata_value
    filled_dem = dem_linear.copy()
    filled_dem[still_nan_mask] = dem_nearest[still_nan_mask]

    # 8. Any cells that remain NaN after both passes can be set to nodata_value
    #    (This might occur if 100% of the DEM was nodata, or big data gaps.)
    remaining_nan_mask = np.isnan(filled_dem)
    filled_dem[remaining_nan_mask] = nodata_value

    return filled_dem

def read_dem(dem_path):
    """
    Read a single-band DEM (GeoTIFF) using Rasterio.
    
    Parameters
    ----------
    dem_path : str
        The file path to the DEM in GeoTIFF format.
    
    Returns
    -------
    dem_data : numpy.ndarray
        2D NumPy array of elevation values (float or int).
    pixel_width : float
        Horizontal size of each pixel in map units (e.g., meters).
    pixel_height : float
        Vertical size of each pixel in map units (e.g., meters).
    nodata_value : float or None
        The no-data value defined in the DEM (if any).
    profile : dict
        Raster metadata/profile from Rasterio.
    """
    with rasterio.open(dem_path) as src:
        # Read the first (and typically only) band
        dem_data = src.read(1)
        
        # Profile contains metadata such as transform, CRS, dtype, etc.
        profile = src.profile
        
        # The pixel size is found in the transform
        # Typically: (pixel_width, 0, x_min, 0, -pixel_height, y_max, ...)
        transform = src.transform
        pixel_width = abs(transform[0])
        pixel_height = abs(transform[4])
        
        # The no-data value may be stored in the profile as "nodata"
        nodata_value = profile.get('nodata', None)
    
    return dem_data, pixel_width, pixel_height, nodata_value, profile

def estimate_volume(dem_path, reference_elevation, save_path=None):
    """
    Estimate the volume of a reservoir above a reference elevation.
    
    Parameters
    ----------
    dem_path : str
        The file path to the DEM in GeoTIFF format.
    reference_elevation : float
        The reference elevation in the same units as the DEM.
    
    Returns
    -------
    volume : float
        The estimated volume above the reference elevation.
    """
    # Read the DEM
    dem_data, pixel_width, pixel_height, nodata_value, profile = read_dem(dem_path)

    # Get the center pixel coordinates of the DEM
    rows, cols = dem_data.shape
    center_x = cols // 2
    center_y = rows // 2
    
    # Linearly interpolate the elevation values at nodata pixels
    dem_filled = interpolate_nodata(dem_data, nodata_value)

    # find the largest contour in dem_data
    dem_data_mask = np.where(dem_data != nodata_value, 1, 0)
    contours, _ = cv2.findContours(dem_data_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    largest_contour = contours[0]
    dem_data_contour = np.zeros_like(dem_data, dtype=np.uint8)
    cv2.drawContours(dem_data_contour, [largest_contour], 0, 1, thickness=cv2.FILLED)

    # keep the values of the largest contour in dem_filled
    dem_filled = np.where(dem_data_contour, dem_filled, 9999)

    # Get a mask of DEM cells below the reference elevation
    below_ref_mask = dem_filled < reference_elevation

    # Find contours in the binary image
    contours, _ = cv2.findContours(below_ref_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Sort the contours by area (largest first)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    # remove small contours 
    area_threshold = 20
    contours = [contour for contour in contours if cv2.contourArea(contour) > area_threshold]

    if len(contours) == 0:
        return 0
    largest_contour = contours[0]
    ref_mask = np.zeros_like(dem_filled, dtype=np.uint8)
    cv2.drawContours(ref_mask, [largest_contour], 0, 1, thickness=cv2.FILLED)

    # # Calculate the centroid of each contour
    # centroids = [np.mean(contour, axis=0).squeeze() for contour in contours]

    # if len(centroids) == 0:
    #     return 0

    # # Find the contour with the centroid closest to the center of the DEM
    # centroid_distances = [np.linalg.norm([center_x - centroid[0], center_y - centroid[1]]) for centroid in centroids]
    # closest_contour_idx = np.argmin(centroid_distances)
    # closest_contour = contours[closest_contour_idx]

    # # Update the mask to only include the closest contour
    # ref_mask = np.zeros_like(dem_filled, dtype=np.uint8)
    # cv2.drawContours(ref_mask, [closest_contour], -1, 1, thickness=cv2.FILLED)



    # Calculate the volume between the reference elevation and the DEM
    volume = np.sum((reference_elevation - dem_filled) * ref_mask) * pixel_width * pixel_height

    if save_path is not None:
        # save the dem with the ref_mask
        masked_dem = np.where(ref_mask, dem_filled, reference_elevation)
        profile.update(nodata=reference_elevation)
        with rasterio.open(save_path, 'w', **profile) as dst:
            dst.write(masked_dem, 1)

    return volume
    
def extract_ground_points(input_las, output_las=None):
    las = laspy.read(input_las)
    
    # Boolean mask for ground-classified points (2)
    ground_mask = (las.classification == 2)
    
    # Create a new, empty LasData object with the same point format and version
    ground_points = laspy.create(
        point_format=las.header.point_format,
        file_version=las.header.version
    )
    
    # Copy the header (including scale, offset, etc.) using deepcopy
    ground_points.header = copy.deepcopy(las.header)
    
    # Slice each dimension in the original file to keep only ground points
    for dim_name in las.point_format.dimension_names:
        ground_points[dim_name] = las[dim_name][ground_mask]
    
    if output_las is not None:
        ground_points.write(output_las)
        print(f"Ground points saved to: {output_las}")
    
    return ground_points

def pointcloud2dem(
    las_path,
    dem_path,
    resolution=1.0,
    method='linear',
    classification_filter=None
):
    """
    Convert a LAS/LAZ point cloud into a DEM (GeoTIFF) by gridding the z-values.
    
    Parameters
    ----------
    las_path : str
        Path to the input LAS/LAZ file.
    dem_path : str
        Path to the output GeoTIFF DEM.
    resolution : float, optional
        The desired output cell size (in the same horizontal units as the LAS).
        Default is 1.0 (e.g., 1 meter).
    method : {'linear', 'nearest', 'cubic'}, optional
        Interpolation method passed to scipy.interpolate.griddata.
    classification_filter : list of int, optional
        List of classification codes to keep. If None, use all points.
        Example: [2] to keep only ground points. 
    """
    # 1. Read the LAS file
    las = laspy.read(las_path)
    
    # 2. Extract coordinates and classification
    #    Note: las.x, las.y, las.z are NumPy arrays (scaled by header offsets/scales)
    x = las.x
    y = las.y
    z = las.z
    
    # If the LAS has classification data and we only want certain classes:
    if classification_filter is not None and hasattr(las, "classification"):
        class_mask = np.isin(las.classification, classification_filter)
        x = x[class_mask]
        y = y[class_mask]
        z = z[class_mask]

    # 3. Determine the bounding box
    min_x, max_x = np.min(x), np.max(x)
    min_y, max_y = np.min(y), np.max(y)

    # 4. Create a grid of desired resolution
    #    We'll define a 2D array that spans [min_x, max_x] and [min_y, max_y]
    grid_x, grid_y = np.meshgrid(
        np.arange(min_x, max_x, resolution),
        np.arange(min_y, max_y, resolution)
    )

    # 5. Interpolate z-values onto the grid
    #    Using griddata with the chosen method (e.g., 'linear' or 'nearest')
    points = np.column_stack((x, y))
    grid_z = griddata(points, z, (grid_x, grid_y), method=method)
    
    # 6. Handle any NaN cells (if 'linear' or 'cubic' can't interpolate at edges)
    #    Simple approach: set them to a special nodata value, e.g., -9999
    nodata_val = -9999
    nan_mask = np.isnan(grid_z)
    grid_z[nan_mask] = nodata_val

    # 7. Prepare the raster metadata for rasterio
    #    Transform assumes top-left corner is (min_x, max_y)
    #    with pixel sizes (resolution, resolution).
    #    But note that in many GIS conventions, 'y' decreases as we go down rows,
    #    so we pass a negative for pixel height if we want a north-up raster.
    transform = from_origin(min_x, min_y, resolution, -resolution)

    # We'll assume a single-band float32 raster.
    # If you know your CRS, you can parse it from the LAS header or specify directly
    # E.g., if las.header.parse_crs() works in your laspy version:
    try:
        crs_info = las.header.parse_crs()
    except:
        crs_info = None  # or set it to a known EPSG like "EPSG:32611"

    new_profile = {
        "driver": "GTiff",
        "height": grid_z.shape[0],
        "width": grid_z.shape[1],
        "count": 1,
        "dtype": str(grid_z.dtype),
        "nodata": nodata_val,
        "transform": transform,
        "crs": crs_info  # or a known string like "EPSG:xxxxx"
    }

    with rasterio.open(dem_path, "w", **new_profile) as dst:
        dst.write(grid_z, 1)
    
    print(f"DEM saved to: {dem_path}")


if __name__ == "__main__":
    None
    # Example usage
    # dem_file = "./data/auburn.tif"
    # ref_elev = 1286  # feet, matching DEM units
    # ref_elev = ref_elev * 0.3048  # convert feet to meters
    # volume = estimate_volume(dem_file, ref_elev, save_path="./data/masked_dem_ardurn.tif")
    # volume_cy = volume * 1.30795  # convert cubic meters to cubic yards
    # print(f"Estimated volume above {ref_elev:.2f} meters: {volume:.2f} cubic meters")
    # print(f"Estimated volume above {ref_elev:.2f} meters: {volume_cy:.2f} cubic yards")

    # Example usage for extracting ground points
    # input_las = "./data/bailey_basin.las"
    # output_las = "./data/bailey_basin_ground.las"
    # # assert input file exists
    # if not os.path.exists(input_las):
    #     raise FileNotFoundError(f"Input LAS file not found: {input_las}")
    # extract_ground_points(input_las, output_las)
    # print("Ground points extracted and saved.")

    # Example usage for converting point cloud to DEM
    las_file = "./data/Sunnyside_20250223/20250223_SunnySide.las"
    dem_file = "./data/Sunnyside_20250223/dem.tif"
    #pointcloud2dem(las_file, dem_file, resolution=0.5, method='linear', classification_filter=[2])
    # dem_file = "./data/bailey_basin_dem.tif"
    # pointcloud2dem(las_file, dem_file, resolution=0.5, method='linear')

    #clear_data()
    clear_las()