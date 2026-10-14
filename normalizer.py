#!/usr/bin/env python3
import os
import sys
import argparse
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 1. Parsing command line arguments with argparse
parser = argparse.ArgumentParser(
    description="Boxing Gym Noise Analysis Script with Multi-File Overlay Normalization."
)
parser.add_argument(
    "-f", "--file", 
    type=str, 
    default=None, 
    help="Path to a single source measurement CSV file (optional if using batch mode)"
)
parser.add_argument(
    "-b", "--batch-folder", 
    type=str, 
    default="results/", 
    help="Folder containing processed CSV files to overlay and normalize (default: results/)"
)
parser.add_argument(
    "-e", "--exclude", 
    type=str, 
    nargs="+",  
    default=[], 
    help="Time intervals to exclude in HH:MM-HH:MM format (e.g., -e 12:00-13:30)"
)

args = parser.parse_args()
source_csv = args.file
batch_folder = args.batch_folder
exclude_intervals = args.exclude
results_folder = "results/"

if not os.path.exists(results_folder):
    os.makedirs(results_folder)

# ==========================================
# BATCH OVERLAY / NORMALIZATION MODE
# ==========================================
if source_csv is None:
    # Find all CSV files in the batch folder
    search_pattern = os.path.join(batch_folder, "*_data.csv")
    csv_files = glob.glob(search_pattern)
    
    if not csv_files:
        print(f"Error: No processed data CSV files found in folder '{batch_folder}'.")
        print("Run a single file analysis first or specify a file with -f.")
        exit(1)
        
    print(f"Found {len(csv_files)} files to normalize and overlay.")
    
    plt.figure(figsize=(14, 7))
    unit_label = None
    all_start_times = []
    all_end_times = []
    
    for file_path in csv_files:
        try:
            # Read CSV assuming format: Time, dB, Weighting
            temp_df = pd.read_csv(file_path, names=["Time", "dB", "Weighting"])
            temp_df["Time"] = pd.to_datetime(temp_df["Time"], errors="coerce")
            temp_df.dropna(subset=["Time"], inplace=True)
            temp_df.set_index("Time", inplace=True)
            temp_df.sort_index(inplace=True)
            
            if temp_df.empty:
                continue
                
            # Normalize time to time-of-day only (HH:MM:SS) for overlapping multi-day graphs
            # We create a dummy date base (today's date) so different days map to the exact same X-axis timeline
            base_date = pd.Timestamp("2026-01-01")
            temp_df.index = base_date + (temp_df.index - temp_df.index.normalize())
            
            w_mode = str(temp_df["Weighting"].iloc[0]).strip()
            if "dB C" in w_mode:
                unit_label = "dBC"
            elif "dB A" in w_mode:
                unit_label = "dBA"
            else:
                unit_label = "dB"
                
            file_label = os.path.basename(file_path).replace("_data.csv", "")
            
            # Plot individual file line with transparency
            plt.plot(temp_df.index, temp_df["dB"], alpha=0.5, linewidth=1.2, label=file_label)
            
            all_start_times.append(temp_df.index[0])
            all_end_times.append(temp_df.index[-1])
            print(f"-> Loaded and normalized: {os.path.basename(file_path)}")
        except Exception as ex:
            print(f"Warning: Could not process {file_path}. Error: {ex}")

    if unit_label is None:
        unit_label = "dB"

    # Formatting the normalized overlay chart
    if limit_value_fixed := (50 if unit_label == "dBC" else (35 if unit_label == "dBA" else None)):
        pass
    
    # Standard limit lines for reference
    limit_val = 50 if unit_label == "dBC" else (35 if unit_label == "dBA" else None)
    if limit_val is not None:
        plt.axhline(y=limit_val, color="red", linestyle="--", alpha=0.7, label=f"Threshold Limit ({limit_val} {unit_label})")

    # Set universal Y-axis decibel range for normalization
    # Locked cleanly from 35 dB up to 75 dB to match your scaling preferences
    plt.ylim(35, 75)

    plt.title(f"Normalized Noise Overlay Comparison ({unit_label}) - Multiple Sessions")
    plt.xlabel("Time of Day")
    plt.ylabel(f"Volume ({unit_label})")
    plt.grid(True, linestyle=":", alpha=0.6)
    plt.legend(loc="upper right", fontsize=9)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    overlay_img_path = os.path.join(results_folder, f"normalized_overlay_chart_{unit_label}.png")
    plt.savefig(overlay_img_path, dpi=150)
    print(f"\n-> Normalized comparison chart saved successfully as: {overlay_img_path}")
    plt.show()
    exit(0)


# ==========================================
# SINGLE FILE ANALYSIS MODE (Original Workflow)
# ==========================================
if not os.path.exists(source_csv):
    print(f"Error: Source file '{source_csv}' not found.")
    exit(1)

print(f"Using source file: '{source_csv}'")
print("Loading measurement data...")
df = pd.read_csv(source_csv, names=["Time", "dB", "Weighting"])

if df.empty:
    print("Error: The data file is empty.")
    exit(1)

# Convert time and set index
df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
df.dropna(subset=["Time"], inplace=True)
df.set_index("Time", inplace=True)
df.sort_index(inplace=True)

# --- EXCLUSION FILTER ---
original_samples = len(df)
filtered_intervals_text = []

mask = pd.Series(False, index=df.index)
for interval in exclude_intervals:
    try:
        start_str, end_str = interval.split("-")
        in_interval = (df.index.time >= pd.to_datetime(start_str).time()) & (df.index.time <= pd.to_datetime(end_str).time())
        mask = mask | in_interval
        filtered_intervals_text.append(f"{start_str} - {end_str}")
    except Exception as e:
        print(f"Warning: Invalid interval format '{interval}'. Use HH:MM-HH:MM")

df = df[~mask]
removed_samples = original_samples - len(df)

if removed_samples > 0:
    print(f"-> Filtered out {removed_samples} samples based on user absence ({', '.join(filtered_intervals_text)}).")

if df.empty:
    print("Error: All data was filtered out! Check your time intervals.")
    exit(1)

# Determine weighting mode
weighting_mode = str(df["Weighting"].iloc[0]).strip()

if "dB C" in weighting_mode:
    unit_label = "dBC"
    limit_value = 50
    limit_label = "General Low-Frequency Baseline (50 dBC)"
    title_unit = "C-weighting (Low-Frequency/Impacts)"
elif "dB A" in weighting_mode:
    unit_label = "dBA"
    limit_value = 35
    limit_label = "Housing Health Decree Limit (Day LAeq 35 dBA)"
    title_unit = "A-weighting (Human Hearing)"
else:
    unit_label = "dB"
    limit_value = None
    limit_label = ""
    title_unit = "Unknown weighting"

first_timestamp = df.index[0]
filename_prefix = first_timestamp.strftime("%Y%m%d_%H%M%S")

file_suffix = "_filtered" if exclude_intervals else ""

output_csv_name = f"{filename_prefix}_{unit_label}{file_suffix}_data.csv"
output_csv_path = os.path.join(results_folder, output_csv_name)
output_img_name = f"{filename_prefix}_{unit_label}{file_suffix}_chart.png"
output_img_path = os.path.join(results_folder, output_img_name)
output_report_name = f"{filename_prefix}_{unit_label}{file_suffix}_report.txt"
output_report_path = os.path.join(results_folder, output_report_name)

df.to_csv(output_csv_path, header=False)
print(f"-> Data saved as: {output_csv_path}")

# Analysis Calculations
max_value = df["dB"].max()
leq_value = 10 * np.log10((10 ** (df["dB"] / 10)).mean())

total_samples = len(df)
total_seconds = total_samples * 0.125
total_minutes = total_seconds / 60

if limit_value is not None:
    exceeded_samples = df[df["dB"] > limit_value]
    num_exceeded = len(exceeded_samples)
    exceeded_percentage = (num_exceeded / total_samples) * 100 if total_samples > 0 else 0
    exceeded_minutes = (num_exceeded * 0.125) / 60
else:
    exceeded_percentage = 0
    exceeded_minutes = 0

samples_per_hour = int(60 * 60 / 0.125)
min_periods_val = 25000 if len(df) >= samples_per_hour else len(df)

rolling_power_mean = (10 ** (df["dB"] / 10)).rolling("60Min", min_periods=min_periods_val).mean()
rolling_leq = 10 * np.log10(rolling_power_mean)

worst_hour_avg = rolling_leq.max()
worst_hour_end = rolling_leq.idxmax()
worst_hour_start = worst_hour_end - pd.Timedelta(minutes=60)
if worst_hour_start < df.index[0]:
    worst_hour_start = df.index[0]

peaks = df[df["dB"] > 60.0]

# --- GENERATE REPORT TEXT ---
report_lines = []
report_lines.append(f"==================================================")
report_lines.append(f"     BOXING GYM NOISE ANALYSIS REPORT ({unit_label})")
report_lines.append(f"==================================================")
report_lines.append(f"Session Start: {first_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
report_lines.append(f"Analyzed Duration: {total_minutes:.1f} minutes ({total_samples} samples)")
if filtered_intervals_text:
    report_lines.append(f"Excluded User Absence: {', '.join(filtered_intervals_text)}")
report_lines.append(f"Weighting Mode: {title_unit}")
report_lines.append(f"--------------------------------------------------")
report_lines.append(f"Global Equivalent Noise Level (Leq): {leq_value:.1f} {unit_label}")
report_lines.append(f"Highest Peak Level (Lmax): {max_value:.1f} {unit_label}")
report_lines.append(f"Impact Peaks Over 60 {unit_label}: {len(peaks)} times")
report_lines.append(f"--------------------------------------------------")
report_lines.append(f"HEALTH OFFICIAL CRITICAL METRICS (ROLLING 1-HOUR):")
report_lines.append(f"Worst Continuous Interval: {worst_hour_start.strftime('%H:%M:%S')} - {worst_hour_end.strftime('%H:%M:%S')}")
report_lines.append(f"Worst Interval Average Level (Leq,1h): {worst_hour_avg:.1f} {unit_label}")
report_lines.append(f"--------------------------------------------------")
report_lines.append(f"THRESHOLD EXCEEDANCE DETAILS:")
report_lines.append(f"Target Reference Limit: {limit_value} {unit_label}")
report_lines.append(f"Time Spent ABOVE Limit: {exceeded_minutes:.1f} minutes")
report_lines.append(f"Percentage of Session ABOVE Limit: {exceeded_percentage:.1f} %")
report_lines.append(f"==================================================")

full_report_text = "\n".join(report_lines)
print(full_report_text)

with open(output_report_path, "w", encoding="utf-8") as f:
    f.write(full_report_text)
print(f"-> Text report saved successfully as: {output_report_path}")

# Plotting single file with normalized Y-axis range (35 to 75 dB)
plt.figure(figsize=(12, 6))
plt.plot(df.index, df["dB"], label=f"Measured noise ({unit_label})", color="royalblue", alpha=0.6)

plt.axvspan(worst_hour_start, worst_hour_end, color='gray', alpha=0.15, 
            label=f"Worst Window ({worst_hour_avg:.1f} {unit_label})")
plt.axhline(y=leq_value, color="orange", linestyle=":", label=f"Session Leq ({leq_value:.1f} {unit_label})")

if limit_value is not None:
    plt.axhline(y=limit_value, color="red", linestyle="--", label=f"{limit_label}: {limit_value} {unit_label}")
    
    stats_text = (f"Threshold: {limit_value} {unit_label}\n"
                  f"Exceeded: {exceeded_percentage:.1f}%\n"
                  f"Worst Leq: {worst_hour_avg:.1f} {unit_label}\n"
                  f"Worst Time: {worst_hour_start.strftime('%H:%M')}-{worst_hour_end.strftime('%H:%M')}")
    
    plt.gca().text(0.02, 0.05, stats_text, transform=plt.gca().transAxes, 
                   bbox=dict(facecolor='white', alpha=0.9, edgecolor='red', boxstyle='round,pad=0.5'),
                   fontsize=10, color='darkred')

plt.ylim(35, 75)
plt.title(f"Boxing Gym Noise Analysis - Session {first_timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({title_unit})")
plt.xlabel("Time")
plt.ylabel(f"Volume ({unit_label})")
plt.grid(True, linestyle=":", alpha=0.6)
plt.legend(loc="upper right")
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

plt.savefig(output_img_path, dpi=150)
print(f"-> Graph saved successfully as: {output_img_path}")
plt.show()