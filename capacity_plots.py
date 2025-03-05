import os
import matplotlib.pyplot as plt
import numpy as np
import csv
import matplotlib.dates as mdates
from datetime import datetime
import matplotlib.ticker as mticker
import pandas as pd
from datetime import timedelta

def read_capacity_estimation_data():
    data = dict()
    with open('data/capacity.csv', 'r') as f:
        reader = csv.reader(f)
        # skip the header
        next(reader)
        for row in reader:
            name = row[0].split('_')[0]
            date = int(row[1])
            upper_spillway_capacity = float(row[2]) 
            lower_spillway_capacity = float(row[3])
            upper_crest_capacity = float(row[4])
            lower_crest_capacity = float(row[5])
            # convert cubic meters to cubic yards
            upper_spillway_capacity *= 1.30795
            lower_spillway_capacity *= 1.30795
            upper_crest_capacity *= 1.30795
            lower_crest_capacity *= 1.30795
            if name not in data:
                data[name] = dict()
            data[name][date] = {'Upper_spillway_capacity': upper_spillway_capacity, 'Lower_spillway_capacity': lower_spillway_capacity, 'Upper_crest_capacity': upper_crest_capacity, 'Lower_crest_capacity': lower_crest_capacity}
    return data

def read_capacity_design_data(data):
    max_capacity_data = dict()
    try:
        file_path = 'data/LA_DB_info.xlsx'
        df = pd.read_excel(file_path, sheet_name='Engineering_design_data')

        # Iterate through all sheets and print content
        for sheet_name, sheet_data in df.items():
            if sheet_name == "Debris Basin":
                # get the values of sheet_data as a list 
                debris_basins = sheet_data.values.tolist()[1:]
            elif sheet_name == "Maximum Debris Capacity":
                maximum_capacity = sheet_data.values.tolist()[1:]

        # select the debris basins in the data
        for i, debris_basin in enumerate(debris_basins):
            if debris_basin in data:
                max_capacity_data[debris_basin] = maximum_capacity[i]
        return max_capacity_data

        
                


    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"Error reading Excel file: {e}")


def plot_capacity(data):
    # Create a 4x3 grid of subplots
    N_rows = 4
    N_cols = 3
    fig, axs = plt.subplots(N_rows, N_cols, figsize=(20, 20), sharex=True, sharey=True)

    # Sort names alphabetically
    names = sorted(data.keys())

    # Variables to store legend handles
    spillway_line = None
    crest_line = None



    all_formatted_dates = []
    for i, name in enumerate(names):

        # Get row and column index for subplot
        row, col = divmod(i, N_cols)

        # Get the data for the name
        name_data = data[name]

        # Get the dates and convert YYYYMMDD to datetime objects
        dates = sorted(name_data.keys())
        formatted_dates = [datetime.strptime(str(date), "%Y%m%d") for date in dates]

        for formatted_date in formatted_dates:
            if formatted_date not in all_formatted_dates:
                all_formatted_dates.append(formatted_date)


        # Compute middle capacities and variances
        middle_spillway_capacities = [
            0.5 * (name_data[date]['Upper_spillway_capacity'] + name_data[date]['Lower_spillway_capacity'])
            for date in dates
        ]
        middle_crest_capacities = [
            0.5 * (name_data[date]['Upper_crest_capacity'] + name_data[date]['Lower_crest_capacity'])
            for date in dates
        ]
        variance_spillway = [
            0.5 * abs(name_data[date]['Upper_spillway_capacity'] - name_data[date]['Lower_spillway_capacity'])
            for date in dates
        ]
        variance_crest = [
            0.5 * abs(name_data[date]['Upper_crest_capacity'] - name_data[date]['Lower_crest_capacity'])
            for date in dates
        ]

        # Plot middle spillway capacity with variance as error bars
        # spillway_plot = axs[row, col].errorbar(formatted_dates, middle_spillway_capacities, yerr=variance_spillway, fmt='-o', label="Spillway", capsize=3)

        # Plot middle crest capacity with variance as error bars
        crest_plot = axs[row, col].errorbar(formatted_dates, middle_crest_capacities, yerr=variance_crest, fmt='-s', label="Crest", capsize=3)

        # Store line objects for legend (only once)
        # if spillway_line is None:
        #     spillway_line = spillway_plot[0]  # Get Line2D instance
        if crest_line is None:
            crest_line = crest_plot[0]  # Get Line2D instance

        
        storm_dates = [datetime.strptime(str(d), "%Y%m%d") for d in [20250127, 20250206, 20250212]]

        for storm_date in storm_dates:
            start_date = storm_date - timedelta(days=1)  # Start of shading (2 days before)
            end_date = storm_date + timedelta(days=1)    # End of shading (2 days after)
            axs[row, col].axvspan(start_date, end_date, color='gray', alpha=0.3, label="Storm Event")

        # Set exact dates as ticks (evenly spaced)
        axs[row, col].set_xticks(all_formatted_dates)
        axs[row, col].set_xticklabels([d.strftime("%m/%d") for d in all_formatted_dates], rotation=45, fontsize=20)

        # Format y-axis with comma separators (1,000 or 1,000,000)
        axs[row, col].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
        # Set y-axis font size
        axs[row, col].tick_params(axis='y', labelsize=20)

        # Set title
        axs[row, col].set_title(name, fontsize=20)
        # Set dotted-line grid
        axs[row, col].grid(True, linestyle='-.', linewidth=0.5)

    # Remove empty subplots
    for i in range(len(names), N_rows * N_cols):
        row, col = divmod(i, N_cols)
        fig.delaxes(axs[row, col])

    # Adjust suptitle and legend positions
    fig.suptitle("Remaining Debris Basin Capacity", fontsize=24, y=0.97)
    # fig.legend([spillway_line, crest_line], ["Spillway", "Crest"], loc="upper center", fontsize=20, ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.955))

    # Add overall x and y labels
    fig.text(0.5, 0.04, "Date", ha="center", fontsize=24)  # X-axis label at bottom center
    fig.text(0.02, 0.5, "Remaining debris basin capacity, cubic yard", va="center", rotation="vertical", fontsize=24)  # Y-axis label at left center

    # Adjust layout to fit everything properly
    plt.tight_layout(rect=[0.05, 0.05, 1, 0.95])  # Ensures space for labels
    # save the plot
    plt.savefig('docs/capacity_plots/capacity.png')
    plt.show()
        

def plot_capacity_raito(data, max_capacity_data):
    # Create a 4x3 grid of subplots
    N_rows = 4
    N_cols = 3
    fig, axs = plt.subplots(N_rows, N_cols, figsize=(20, 20), sharex=True, sharey=True)

    # Sort names alphabetically
    names = sorted(data.keys())

    # Variables to store legend handles
    spillway_line = None
    crest_line = None

    all_formatted_dates = []
    for i, name in enumerate(names):

        # Get row and column index for subplot
        row, col = divmod(i, N_cols)

        # Get the data for the name
        name_data = data[name]

        # Get the dates and convert YYYYMMDD to datetime objects
        dates = sorted(name_data.keys())
        formatted_dates = [datetime.strptime(str(date), "%Y%m%d") for date in dates]

        for formatted_date in formatted_dates:
            if formatted_date not in all_formatted_dates:
                all_formatted_dates.append(formatted_date)


        # Compute middle capacities and variances
        middle_spillway_capacities = [
            0.5 * (name_data[date]['Upper_spillway_capacity'] + name_data[date]['Lower_spillway_capacity'])/max_capacity_data[name]
            for date in dates
        ]
        middle_crest_capacities = [
            0.5 * (name_data[date]['Upper_crest_capacity'] + name_data[date]['Lower_crest_capacity'])/max_capacity_data[name]
            for date in dates
        ]
        # limit the ratio to 1
        middle_spillway_capacities = [min(1, x) for x in middle_spillway_capacities]
        middle_crest_capacities = [min(1, x) for x in middle_crest_capacities]

        variance_spillway = [
            0.5 * abs(name_data[date]['Upper_spillway_capacity'] - name_data[date]['Lower_spillway_capacity'])/max_capacity_data[name]
            for date in dates
        ]
        variance_crest = [
            0.5 * abs(name_data[date]['Upper_crest_capacity'] - name_data[date]['Lower_crest_capacity'])/max_capacity_data[name]
            for date in dates
        ]

        # Plot middle spillway capacity with variance as error bars
        # spillway_plot = axs[row, col].errorbar(formatted_dates, middle_spillway_capacities, yerr=variance_spillway, fmt='-o', label="Spillway", capsize=3)

        # Plot middle crest capacity with variance as error bars
        crest_plot = axs[row, col].errorbar(formatted_dates, middle_crest_capacities, yerr=variance_crest, fmt='-s', label="Crest", capsize=3)

        # Store line objects for legend (only once)
        # if spillway_line is None:
        #     spillway_line = spillway_plot[0]  # Get Line2D instance
        if crest_line is None:
            crest_line = crest_plot[0]  # Get Line2D instance

        storm_dates = [datetime.strptime(str(d), "%Y%m%d") for d in [20250127, 20250206, 20250212]]

        for storm_date in storm_dates:
            start_date = storm_date - timedelta(days=1)  # Start of shading (2 days before)
            end_date = storm_date + timedelta(days=1)    # End of shading (2 days after)
            axs[row, col].axvspan(start_date, end_date, color='gray', alpha=0.3, label="Storm Event")

        # Set exact dates as ticks (evenly spaced)
        axs[row, col].set_xticks(all_formatted_dates)
        axs[row, col].set_xticklabels([d.strftime("%m/%d") for d in all_formatted_dates], rotation=45, fontsize=20)

        # Format y-axis with percentage
        axs[row, col].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0%}"))
        # Set y-axis font size
        axs[row, col].tick_params(axis='y', labelsize=20)

        # Set title
        axs[row, col].set_title(name, fontsize=20)
        # dot dash grid
        axs[row, col].grid(True, linestyle='-.', linewidth=0.5)


    # Remove empty subplots
    for i in range(len(names), N_rows * N_cols):
        row, col = divmod(i, N_cols)
        fig.delaxes(axs[row, col])

    # Adjust suptitle and legend positions
    fig.suptitle("Remaining Debris Basin Capacity relative to the Design Capacity", fontsize=24, y=0.97)
    # fig.legend([spillway_line, crest_line], ["Spillway", "Crest"], loc="upper center", fontsize=20, ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.955))

    # Add overall x and y labels
    fig.text(0.5, 0.04, "Date", ha="center", fontsize=24)  # X-axis label at bottom center
    fig.text(0.02, 0.5, "Remaining debris basin capacity relative to the design capacity, %", va="center", rotation="vertical", fontsize=24)  # Y-axis label at left center

    # Adjust layout to fit everything properly
    plt.tight_layout(rect=[0.05, 0.05, 1, 0.95])  # Ensures space for labels
    # save the plot
    plt.savefig('docs/capacity_plots/capacity_ratio.png')
    plt.show()

def save_results(data, max_capacity_data):
    with open('data/results.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Date', 'Spillway Capacity (cy)', 'Spillway Capacity Uncertainty (cy)', 'Crest Capacity (cy)', 'Crest Capacity Uncertainty (cy)', 'Spillway Capacity Ratio', 'Crest Capacity Ratio', "Max Design Capacity (cy)"])
        for name, dates in data.items():
            for date, capacities in dates.items():
                spillway_capacity = int(0.5 * (capacities['Upper_spillway_capacity'] + capacities['Lower_spillway_capacity']))
                spillway_capacity_uncertainty = int(0.5 * abs(capacities['Upper_spillway_capacity'] - capacities['Lower_spillway_capacity']))
                crest_capacity = int(0.5 * (capacities['Upper_crest_capacity'] + capacities['Lower_crest_capacity']))
                crest_capacity_uncertainty = int(0.5 * abs(capacities['Upper_crest_capacity'] - capacities['Lower_crest_capacity']))
                spillway_capacity_ratio = spillway_capacity / max_capacity_data[name]
                spillway_capacity_ratio = "{:.2%}".format(spillway_capacity_ratio)
                crest_capacity_ratio = crest_capacity / max_capacity_data[name]
                crest_capacity_ratio = "{:.2%}".format(crest_capacity_ratio)
                writer.writerow([name, date, spillway_capacity, spillway_capacity_uncertainty, crest_capacity, crest_capacity_uncertainty, spillway_capacity_ratio, crest_capacity_ratio, max_capacity_data[name]])
        
# main 
if __name__ == '__main__':
    data = read_capacity_estimation_data()
    plot_capacity(data)
    max_capacity_data = read_capacity_design_data(data)
    plot_capacity_raito(data, max_capacity_data)
    save_results(data, max_capacity_data)

