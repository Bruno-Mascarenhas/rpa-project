import os
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler

import requests
import shutil
from RPA.Robocorp.WorkItems import WorkItems

def convert_date(date_str: str) -> datetime:    
    now = datetime.now()
    date_str = date_str.strip().replace(".", "")

    # Check if string is in "1h ago" or "1m ago" format
    if date_str.endswith("m ago"):
        minutes_ago = int(date_str.split('m')[0])
        delta = timedelta(minutes=minutes_ago)
        return now - delta
    elif date_str.endswith("h ago"):
        hours_ago = int(date_str.split('h')[0])
        delta = timedelta(hours=hours_ago)
        return now - delta
    
    # Check if string is in "month day" or "month day, year" format
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            tmp = date_str
            if len(date_str.split(',')) == 1:
                # add current year to string
                tmp = f"{date_str}, {now.year}"
            dt = datetime.strptime(tmp, fmt)
            return dt
        except:
            pass
    
    # Invalid date format
    raise ValueError(f"Invalid date format: {date_str}")

def download_image(url: str, download_dir: str) -> str:
    filename = os.path.basename(url).split("?")[0]
    # Download image from URL and save it to the download folder
    try:
        # I did it usign requests library because I was unable to use RPA.HTTP library (triggered SO level error)
        bin_image = requests.get(url, allow_redirects=True)
        open(os.path.join(download_dir, filename), "wb").write(bin_image.content)
    except Exception as e:
        filename = ""
    return filename

def configure_logger() -> logging.Logger:
    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler('robot.log', maxBytes=1024*1024, backupCount=2)

    # Change level of handlers to DEBUG or INFO (production)
    console_handler.setLevel(logging.DEBUG if os.getenv('PROD', False) else logging.INFO)
    file_handler.setLevel(logging.DEBUG if os.getenv('PROD', False) else logging.INFO)

    # Create a formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

def clear_downloads(download_dir: str) -> None:
    try:
        os.makedirs(download_dir, exist_ok=True)
        jpg_files = [file for file in os.listdir(download_dir) if file.endswith('.jpg') or file.endswith('.png')]
        for file in jpg_files:
            os.remove(os.path.join(download_dir, file))
    except:
        raise Exception("Error cleaning download folder")

def save_to_cloud(files: list) -> None:
    # Upload files to Control Room output
    try:
        items = WorkItems()
        items.get_input_work_item()

        for file in files:
            items.add_work_item_file(file)

        items.save_work_item()
    except:
        raise Exception("Error uploading files to Control Room")
