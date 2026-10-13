#!/usr/bin/env python3
import os
import shutil
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Paths configuration
source_csv = "log/data.csv"
results_folder = "results/"

if not os.path.exists(source_csv):
    print(f"Error: Source file '{source_csv}' not found. Run your capture script first.")
    exit(1)

print("Loading measurement data...")
# Read the current data.csv
df = pd.read_csv(source_csv, names=["Time", "dB", "Weighting"])

if df.empty:
    print("Error: The data file is empty.")
    exit(1)

# Ensure the results directory exists
if not os.path.exists(results_folder):
    os.makedirs(results_folder)

# Convert the timestamp column to datetime objects for analysis
df["Time"] = pd.to_datetime(df["Time"])

# Set Time as index for rolling window calculations
df.set_index("Time", inplace=True)

# 1. Determine the weighting type (A or C) from the data
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

# 2. Get the timestamps and format for file names
first_timestamp = df.index[0]
filename_prefix = first_timestamp.strftime("%Y%m%d_%H%M%S")

# Define unique destination file names inside the 'results' folder
archived_csv_name = f"{filename_prefix}_{unit_label}_data.csv"
archived_csv_path = os.path.join(results_folder, archived_csv_name)
output_img_name = f"{filename_prefix}_{unit_label}_chart.png"
output_img_path = os.path.join(results_folder, output_img_name)
output_report_name = f"{filename_prefix}_{unit_label}_report.txt"
output_report_path = os.path.join(results_folder, output_report_name)

# Copy the original data.csv to the new unique name in results/ (reset index temporarily for copy)
df.to_csv(archived_csv_path, header=False)
print(f"-> Data archived successfully as: {archived_csv_path}")

# 3. Analyze the results
max_value = df["dB"].max()
avg_value = df["dB"].mean()

# Calculate total duration of the session
total_samples = len(df)
total_seconds = total_samples * 0.125
total_minutes = total_seconds / 60

# --- PROSENTUAALINEN YLITYSLASKURI (EXCEEDANCE CALCULATOR) ---
exceeded_samples = df[df["dB"] > limit_value]
num_exceeded = len(exceeded_samples)
exceeded_percentage = (num_exceeded / total_samples) * 100 if total_samples > 0 else 0
exceeded_minutes = (num_exceeded * 0.125) / 60

# --- FIXED: ADVANCED ROLLING 1-HOUR ANALYSIS (WORST HOUR LEQ) ---
# Calculate rolling average over 1 hour (3600 seconds / 0.125s interval = 28800 samples)
# Using '60Min' time offset window requires datetime index
rolling_mean = df["dB"].rolling("60Min").mean()

worst_hour_avg = rolling_mean.max()
worst_hour_end = rolling_mean.idxmax()
# Calculate start time of that 1-hour window
worst_hour_start = worst_hour_end - pd.Timedelta(minutes=60)

# Find sharp impacts or loud moments (peaks over 60 dB)
peaks = df[df["dB"] > 60.0]

# --- GENERATE REPORT TEXT ---
report_lines = []
report_lines.append(f"==================================================")
report_lines.append(f"     BOXING GYM NOISE ANALYSIS REPORT ({unit_label})")
report_lines.append(f"==================================================")
report_lines.append(f"Session Start: {first_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
report_lines.append(f"Total Duration: {total_minutes:.1f} minutes ({total_samples} samples)")
report_lines.append(f"Weighting Mode: {title_unit}")
report_lines.append(f"--------------------------------------------------")
report_lines.append(f"Global Average Noise Level ({unit_label}): {avg_value:.1f} {unit_label}")
report_lines.append(f"Highest Peak Level (Lmax): {max_value:.1f} {unit_label}")
report_lines.append(f"Impact Peaks Over 60 {unit_label}: {len(peaks)} times")
report_lines.append(f"--------------------------------------------------")
report_lines.append(f"HEALTH OFFICIAL CRITICAL METRICS (ROLLING 1-HOUR):")
report_lines.append(f"Worst 1-Hour Continuous Interval: {worst_hour_start.strftime('%H:%M:%S')} - {worst_hour_end.strftime('%H:%M:%S')}")
report_lines.append(f"Worst 1-Hour Average Level (Leq,1h): {worst_hour_avg:.1f} {unit_label}")
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

# Combine lines into a single string
full_report_text = "\n".join(report_lines)

# Print the report to the terminal
print(full_report_text)

# Save the report to the text file in results/
with open(output_report_path, "w", encoding="utf-8") as f:
    f.write(full_report_text)
print(f"-> Text report saved successfully as: {output_report_path}")

# 4. Plot the graph for visualization
plt.figure(figsize=(12, 6))
plt.plot(df.index, df["dB"], label=f"Measured noise ({unit_label})", color="royalblue", alpha=0.6)

# Highlight the worst 1-hour window on the graph with a translucent gray block
plt.axvspan(worst_hour_start, worst_hour_end, color='gray', alpha=0.15, 
            label=f"Worst 1-Hour Window ({worst_hour_avg:.1f} {unit_label})")

# Visual reference lines
plt.axhline(y=avg_value, color="orange", linestyle=":", label=f"Session average ({avg_value:.1f} {unit_label})")

if limit_value is not None:
    plt.axhline(y=limit_value, color="red", linestyle="--", label=f"{limit_label}: {limit_value} {unit_label}")
    
    # Text box in the graph for the percentage and worst hour results
    stats_text = (f"Threshold: {limit_value} {unit_label}\n"
                  f"Exceeded: {exceeded_percentage:.1f}%\n"
                  f"Worst 1h Leq: {worst_hour_avg:.1f} {unit_label}\n"
                  f"Worst Time: {worst_hour_start.strftime('%H:%M')}-{worst_hour_end.strftime('%H:%M')}")
    
    plt.gca().text(0.02, 0.05, stats_text, transform=plt.gca().transAxes, 
                   bbox=dict(facecolor='white', alpha=0.9, edgecolor='red', boxstyle='round,pad=0.5'),
                   fontsize=10, color='darkred')

plt.title(f"Boxing Gym Noise Analysis - Session {first_timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({title_unit})")
plt.xlabel("Time")
plt.ylabel(f"Volume ({unit_label})")
plt.grid(True, linestyle=":", alpha=0.6)
plt.legend(loc="upper right")

# Format X axis to show time cleanly
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

# Save the plot with the matching unique timestamp and unit name to results/
plt.savefig(output_img_path, dpi=150)
print(f"-> Graph saved successfully as: {output_img_path}")

# Show the plot window
plt.show()