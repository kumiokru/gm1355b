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
* `gm1355.py` reads Benetech gm1355b output from USB and quits after user provided break (eg. ctrl c).
* `analyze.py` reads the output and generates reports to ./log/ folder.

