# How to use

Add udevrules to read from USB without requiring `sudo`. 

```bash
sudo cp 99-benetech.rules /etc/udev/rules.d/

sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then use `start.sh`, that should handle virtual envs and the packages required in `requirements.txt`.

## More information

This is based on two python scripts.
* `gm1355.py` reads Benetech gm1355b output from USB and quits after user provided break (eg. ctrl-c).
  * populates `log/` folder for the analyze script.
    * `data.csv`
    * `raw_log.txt` (this might roll over to `raw_log.txt.1` etc if the file size gets too big. Mainly for debugging purposes for now)
* `analyze.py` reads the output and generates reports to `./results/` folder.
  * parses `log/data.csv` and outputs:
    * `<timestamp>_<measurement_type (dbA / dBC)>_chart.png`: image based on data
    * `<timestamp>_<measurement_type (dbA / dBC)>_data.csv`: original data.csv renamed with first timestamp in the log
    * `<timestamp>_<measurement_type (dbA / dBC)>_report.txt`: small summary of the measurement

## analyze-with-exclude.py

There's a new tool for now as I didn't want to overwrite the original `analyze.py` but added an alternative for more information.
`analyze-with-exclude.py` supports few command line options.

Example:

```bash
python analyze-with-exclude -f results/20261012_123526_dBC_data.csv -e 17:45-17:55 20:21-20:41
```

Analyzes file `results/20261012_123526_dBC_data.csv`
Excludes times `17:45-17:55` and `20:21-20:41`
Creates new files for the original data to the same results folder:
`20261012_123526_dBC_data_cleaned.csv`
`20261012_123526_dBC_report_cleaned.txt`
`20261012_123526_dBC_chart_cleaned.png`

Todo:
* maybe store all results in one zip?
* maybe go through the zip if there is a need for exclusion?