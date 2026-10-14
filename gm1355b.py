#!/usr/bin/env python
# -*- coding: utf-8 -*-

import usb.core
import usb.util
import logging
from logging.handlers import RotatingFileHandler
import time
import os
import datetime
import sys

# USB identifiers for Benetech GT1355B
VENDOR_ID = 0x64BD
PRODUCT_ID = 0x74E3

raw_logger = None
raw_log_file_name = "raw_log.txt"
raw_log_file_size = 10 * 1024 * 1024
csv_logger = None
csv_log_file_name = "data.csv"
stdio_logger = None
logging_folder = "log/"
device = None

# Sampling interval set to 125 ms (8 times per second)
target_interval = 0.125                     

cmd_buffer_linux = [0xb3, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

def init_logging():
    global stdio_logger, raw_logger, csv_logger
    if not os.path.exists(logging_folder):
        os.makedirs(logging_folder)

    csv_logger = logging.getLogger('csv_logger')
    csv_logger.setLevel(logging.INFO)
    path = os.path.join(logging_folder, csv_log_file_name)
    
    handler = logging.FileHandler(path, mode='w', encoding='utf-8')
    handler.setFormatter(logging.Formatter("%(message)s"))
    csv_logger.addHandler(handler)

    raw_logger = logging.getLogger('raw_logger')
    raw_logger.setLevel(logging.INFO)
    path = os.path.join(logging_folder, raw_log_file_name)
    
    handler = RotatingFileHandler(path, mode='w', maxBytes=raw_log_file_size, backupCount=3)
    handler.setFormatter(logging.Formatter("%(message)s"))
    raw_logger.addHandler(handler)

    stdio_logger = logging.getLogger()
    stdio = logging.StreamHandler()
    stdio.setLevel(logging.INFO)
    stdio.setFormatter(logging.Formatter("%(message)s"))
    stdio_logger.addHandler(stdio)
    return

def get_units(value):
    if (value & 16) == 16:
        return 'dB C'
    else:
        return 'dB A'

def get_max_lock(value):
    if (value & 32) == 32:
        return 'Max lock on'
    else:
        return 'Max lock off'

def get_speed(value):
    if (value & 64) == 64:
        return 'Fast'
    else:
        return 'Slow'

def get_range(value):
    if (value & 4) == 4:
        return '80 - 130'
    elif (value & 3) == 3:
        return '60 - 110'
    elif (value & 2) == 2:
        return '50 - 100'
    elif (value & 1) == 1:
        return '30 - 80'
    else:
        return '30 - 130'

def get_dB(value1, value2):
    dB = (value1 * 256 + value2) * 0.1
    return dB

def process_sample(data):
    t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:22]
    db_val = get_dB(data[0], data[1])
    status_byte = data[2]
    
    print(f"[{t}] {db_val:.1f} {get_units(status_byte)} ({get_speed(status_byte)})", flush=True)
    
    csv_logger.info(f"{t},{db_val:.1f},{get_units(status_byte)}")
    raw_logger.info(f"{t},{db_val:.1f},{get_units(status_byte)},{get_speed(status_byte)},{get_max_lock(status_byte)},{get_range(status_byte)},{list(data)}")
    return

def close_usb():
    global device
    if device is not None:
        try:
            usb.util.dispose_resources(device)
            raw_logger.info("USB device closed successfully.")
        except Exception as e:
            raw_logger.error(f"Error closing USB device: {e}")
    return

def init_usb():
    global device
    device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
    
    if device is None:
        raw_logger.error("Device not found. Please check the USB connection.")
        sys.exit(1)

    if device.is_kernel_driver_active(0):
        try:
            device.detach_kernel_driver(0)
            raw_logger.info("Kernel driver detached from the meter.")
        except usb.core.USBError as e:
            raw_logger.error(f"Could not detach kernel driver: {e}")
            sys.exit(1)

    try:
        device.set_configuration()
        raw_logger.info("USB connection initialized successfully.")
    except usb.core.USBError as e:
        raw_logger.error(f"Device configuration failed: {e}")
        sys.exit(1)
    return

def capture_data():
    global device
    print("Press Ctrl + C to stop measuring.")
    print("Waiting for data...\n")
    
    try:
        while True:
            start_time = time.time()  # Otetaan silmukan alkamisaika talteen
            
            try:
                device.write(0x02, cmd_buffer_linux, 100)
                data = device.read(0x81, 8, 100)
                
                if len(data) >= 4:
                    process_sample(data)
                    
            except usb.core.USBError as e:
                if e.errno == 110:  # Timeout, continue trying
                    continue
                else:
                    raw_logger.error(f"USB error while reading data: {e}")
                    break
            
            # KORJAUS: Lasketaan dynaaminen uniaika viiveiden kompensoimiseksi
            elapsed_time = time.time() - start_time
            sleep_time = target_interval - elapsed_time
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            else:
                # Jos USB-liikenne oli hitaampaa kuin 125ms, ei odoteta ollenkaan vaan jatketaan heti
                pass
            
    except KeyboardInterrupt:
        print("\nMeasurement stopped by user.")
        raw_logger.info("Measurement interrupted from keyboard (Ctrl+C).")
        
    return

if __name__ == '__main__':
    init_logging()
    raw_logger.info("Capturing data started ...")
    init_usb()
    capture_data()
    close_usb()
    raw_logger.info("Script ended")