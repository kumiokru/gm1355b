#!/usr/bin/env python3
import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 1. Parsing command line arguments with argparse
parser = argparse.ArgumentParser(
    description="Boxing Gym Noise Analysis Script with Filtering Capabilities."
)
parser.add_argument(
    "-f", "--file", 
    type=str, 
    default="log/data.csv", 
    help="Path to the source measurement CSV file (default: log/data.csv)"
)
parser.add_argument(
    "-e", "--exclude", 
    type=str, 
    nargs="+",  # Allows multiple intervals separated by spaces
    default=[], 
    help="Time intervals to exclude in HH:MM-HH:MM format (e.g., -e 12:00-13:30 16:00-17:00)"
)

args = parser.parse_args()
source_csv = args.file
exclude_intervals = args.exclude

results_folder = "results/"

if not os.path.exists(source_csv):
    print(f"Error: Source file '{source_csv}' not found.")
    exit(1)

print(f"Using source file: '{source_csv}'")
print("Loading measurement data...")
df = pd.read_csv(source_csv, names=["Time", "dB", "Weighting"])

if df.empty:
    print("Error: The data file is empty.")
    exit(1)

if not os.path.exists(results_folder):
    os.makedirs(results_folder)

# Convert time and set index
df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
df.dropna(subset=["Time"], inplace=True)
df.set_index("Time", inplace=True)
df.sort_index(inplace=True)

# --- EXCLUSION FILTER ---
original_samples = len(df)
filtered_intervals_text = []

# Apply time mask for exclusion
mask = pd.Series(False, index=df.index)
for interval in exclude_intervals:
    try:
        start_str, end_str = interval.split("-")
        in_interval = (df.index.time >= pd.to_datetime(start_str).time()) & (df.index.time <= pd.to_datetime(end_str).time())
        mask = mask | in_interval
        filtered_intervals_text.append(f"{start_str} - {end_str}")
    except Exception as e:
        print(f"Warning: Invalid interval format '{interval}'. Use HH:MM-HH:MM (e.g., -e 12:00-13:30)")

# Keep only rows that are NOT in the mask
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
    title_unit = "A-hearing (Human Hearing)"
else:
    unit_label = "dB"
    limit_value = None
    limit_label = ""
    title_unit = "Unknown weighting"

first_timestamp = df.index[0]
filename_prefix = first_timestamp.strftime("%Y%m%d_%H%M%S")

# CONDITIONAL SUFFIX: Only adds '_filtered' if the -e flag was explicitly used
file_suffix = "_filtered" if exclude_intervals else ""

output_csv_name = f"{filename_prefix}_{unit_label}{file_suffix}_data.csv"
output_csv_path = os.path.join(results_folder, output_csv_name)

output_img_name = f"{filename_prefix}_{unit_label}{file_suffix}_chart.png"
output_img_path = os.path.join(results_folder, output_img_name)

output_report_name = f"{filename_prefix}_{unit_label}{file_suffix}_report.txt"
output_report_path = os.path.join(results_folder, output_report_name)

# Save the updated data slice to results folder
df.to_csv(output_csv_path, header=False)
print(f"-> Data saved as: {output_csv_path}")

# Analysis
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

# --- CORRECTED ROLLING 1-HOUR INTERVAL CALCULATION ---
# 1 hour = 28,800 samples at 0.125s intervals. 
# We require at least 25,000 samples (~58 mins) to prevent partial windows at the start.
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
report_lines.append(f"--------------------------------------------------")

if len(peaks) > 0:
    report_lines.append(f"TOP 5 LOUDEST BOXING IMPACTS:")
    print_df = peaks.sort_values(by="dB", ascending=False).head(5)
    for index, row in print_df.iterrows():
        report_lines.append(f" - [{index.strftime('%H:%M:%S.%f')[:11]}] {row['dB']:.1f} {unit_label}")
else:
    report_lines.append(f"No individual impacts over 60 {unit_label} detected.")
report_lines.append(f"==================================================")

full_report_text = "\n".join(report_lines)
print(full_report_text)

with open(output_report_path, "w", encoding="utf-8") as f:
    f.write(full_report_text)
print(f"-> Text report saved successfully as: {output_report_path}")

# Plotting
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

plt.title(f"Boxing Gym Noise Analysis - Session {first_timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({title_unit})")
plt.xlabel("Time")
plt.ylabel(f"Volume ({unit_label})")
plt.grid(True, linestyle=":", alpha=0.6)
plt.legend(loc="upper right")
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

plt.savefig(output_img_path, dpi=150)
print(f"-> Graph saved successfully as: {output_img_path}")
plt.show()