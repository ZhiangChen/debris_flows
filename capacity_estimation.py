from utils import *

import csv
import os
import numpy as np
from natsort import natsorted 

def check_capacity_csv():
    capaticy_csv = 'data/capacity.csv'
    if not os.path.exists(capaticy_csv):
        # Create a new capacity.csv file
        with open(capaticy_csv, 'w') as f:
            f.write('Name, Date, Upper_spillway_capacity, Lower_spillway_capacity, Upper_crest_capacity, Lower_crest_capacity\n')
            f.close()

        # return an empty dictionary
        return {}
    else:
        # Read the capacity.csv file
        with open(capaticy_csv, 'r') as f:
            lines = f.readlines()
            f.close()

        processed_data = {}
        for i in range(1, len(lines)):
            # check if this line is empty
            if len(lines[i]) == 1:
                continue
            name = lines[i].split(',')[0]
            date = int(lines[i].split(',')[1])
            upper_spillway_capacity = float(lines[i].split(',')[2])
            lower_spillway_capacity = float(lines[i].split(',')[3])
            upper_crest_capacity = float(lines[i].split(',')[4])
            lower_crest_capacity = float(lines[i].split(',')[5])
            processed_data[name] = {
                'Date': date,
                'Upper_spillway_capacity': upper_spillway_capacity,
                'Lower_spillway_capacity': lower_spillway_capacity,
                'Upper_crest_capacity': upper_crest_capacity,
                'Lower_crest_capacity': lower_crest_capacity
            }

        return processed_data
    
def process_capacity_estimation():
    processed_data = check_capacity_csv()
    processed_folders = list(processed_data.keys())
    print(f"Processed folders: {processed_folders}")
    # list all folders under the data folder
    folders = [f for f in os.listdir('data') if os.path.isdir(os.path.join('data', f))]
    # sort the folders
    folders = natsorted(folders)
    for folder in folders:
        # check if the folder is already processed
        if folder in processed_data:
            continue
        print(f"Processing folder: {folder}")
        # get the path of the folder
        folder_path = os.path.join('data', folder)
        # get the list of files in the folder
        files = os.listdir(folder_path)
        # continue if the folder is empty
        if len(files) == 0:
            continue
        # check whether height_references.csv exists
        if 'height_references.csv' not in files:
            # create a new height_references.csv file
            with open(os.path.join(folder_path, 'height_references.csv'), 'w') as f:
                f.write('spillway_elevation, 0\n')
                f.write('crest_elevation, 0\n')
                f.close()
            continue
        # read the height_references.csv file
        with open(os.path.join(folder_path, 'height_references.csv'), 'r') as f:
            lines = f.readlines()
            f.close()
        # get the height references
        spillway_height = float(lines[0].split(',')[1])
        crest_height = float(lines[1].split(',')[1])

        if spillway_height == 0 or crest_height == 0:
            continue

        result = dict()
        result['Name'] = folder
        result['Date'] = int(folder.split('_')[-1])
        if 'dsm.tif' in files:
            dsm_file = os.path.join(folder_path, 'dsm.tif')
            lower_spillway_capacity = estimate_volume(dsm_file, spillway_height, os.path.join(folder_path, 'dsm_spillway_masked.tif'))
            lower_crest_capacity = estimate_volume(dsm_file, crest_height, os.path.join(folder_path, 'dsm_crest_masked.tif'))
            result['Lower_spillway_capacity'] = lower_spillway_capacity
            result['Lower_crest_capacity'] = lower_crest_capacity

        if 'dem.tif' in files:
            dem_file = os.path.join(folder_path, 'dem.tif')
            upper_spillway_capacity = estimate_volume(dem_file, spillway_height, os.path.join(folder_path, 'dem_spillway_masked.tif'))
            upper_crest_capacity = estimate_volume(dem_file, crest_height, os.path.join(folder_path, 'dem_crest_masked.tif'))
            result['Upper_spillway_capacity'] = upper_spillway_capacity
            result['Upper_crest_capacity'] = upper_crest_capacity

        if ('dsm.tif' in files) and ('dem.tif' in files):
            # append the result to the capacity.csv file
            with open('data/capacity.csv', 'a') as f:
                f.write(f"{result['Name']}, {result['Date']}, {result['Upper_spillway_capacity']}, {result['Lower_spillway_capacity']}, {result['Upper_crest_capacity']}, {result['Lower_crest_capacity']}\n")
                f.close()
            continue

        # check if .las file exists
        pc_files = [f for f in files if f.endswith('.las')]
        if len(pc_files) == 1:
            las_file = os.path.join(folder_path, pc_files[0])
            dsm_file = os.path.join(folder_path, 'dsm.tif')
            dem_file = os.path.join(folder_path, 'dem.tif')
            pointcloud2dem(las_file, dem_file, resolution=0.5, method='linear', classification_filter=[2])
            pointcloud2dem(las_file, dsm_file, resolution=0.5, method='linear')
            lower_spillway_capacity = estimate_volume(dsm_file, spillway_height, os.path.join(folder_path, 'dsm_spillway_masked.tif'))
            lower_crest_capacity = estimate_volume(dsm_file, crest_height, os.path.join(folder_path, 'dsm_crest_masked.tif'))
            upper_spillway_capacity = estimate_volume(dem_file, spillway_height, os.path.join(folder_path, 'dem_spillway_masked.tif'))
            upper_crest_capacity = estimate_volume(dem_file, crest_height, os.path.join(folder_path, 'dem_crest_masked.tif'))
            result['Lower_spillway_capacity'] = lower_spillway_capacity
            result['Lower_crest_capacity'] = lower_crest_capacity
            result['Upper_spillway_capacity'] = upper_spillway_capacity
            result['Upper_crest_capacity'] = upper_crest_capacity
            # append the result to the capacity.csv file
            with open('data/capacity.csv', 'a') as f:
                f.write(f"{result['Name']}, {result['Date']}, {result['Upper_spillway_capacity']}, {result['Lower_spillway_capacity']}, {result['Upper_crest_capacity']}, {result['Lower_crest_capacity']}\n")
                f.close()

        # if result is empty, raise an error
        result_keys = list(result.keys())
        if len(result_keys) > 2:
            print("No DSM or DEM or LAS file found")
        
def sort_csv():
    with open('data/capacity.csv', 'r') as f:
        lines = f.readlines()
        f.close()
    data = []
    for i in range(1, len(lines)):
        name = lines[i].split(',')[0]
        date = int(lines[i].split(',')[1])
        upper_spillway_capacity = float(lines[i].split(',')[2])
        lower_spillway_capacity = float(lines[i].split(',')[3])
        upper_crest_capacity = float(lines[i].split(',')[4])
        lower_crest_capacity = float(lines[i].split(',')[5])
        data.append([name, date, upper_spillway_capacity, lower_spillway_capacity, upper_crest_capacity, lower_crest_capacity])
    data = np.array(data)
    # sort the data by name
    data = data[data[:, 0].argsort()]
    with open('data/capacity.csv', 'w') as f:
        f.write('Name, Date, Upper_spillway_capacity, Lower_spillway_capacity, Upper_crest_capacity, Lower_crest_capacity\n')
        for i in range(len(data)):
            f.write(f"{data[i][0]}, {data[i][1]}, {data[i][2]}, {data[i][3]}, {data[i][4]}, {data[i][5]}\n")
        f.close()

if __name__ == "__main__":
    process_capacity_estimation()
    sort_csv()


