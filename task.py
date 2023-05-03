import os
import glob
import logging

from src.news_scraper import NewsScraper
from src.util import clear_downloads, save_to_cloud, get_env

search_phrase = get_env("SEARCH_PHRASE", "Dollar")
news_category = get_env("NEWS_CATEGORY", "Books,Technology,Travel")
num_months = int(get_env("NUM_MONTHS", 2))

excel_filename = get_env("EXCEL_FILENAME", "articles.xlsx")
download_folder = get_env("DOWNLOAD_FOLDER", os.path.join(os.getcwd(), "output"))

NUM_FILES = os.getenv("NUM_FILES", 30)
MAX_SIZE = os.getenv("MAX_SIZE", 1000000)

def main() -> None:
    #Log info with the current parameters
    logging.info(f"Search phrase: {search_phrase}")
    logging.info(f"News category: {news_category}")
    logging.info(f"Number of months: {num_months}")
    logging.info(f"Excel filename: {excel_filename}")
    logging.info(f"Download folder: {download_folder}")

    # Cleaning the donwload folder (cleanup from previous runs and
    # keep with the maximum quantity of files allowed)
    clear_downloads(download_folder)

    scraper = NewsScraper(search_phrase, news_category, num_months, download_folder, excel_filename, num_files=NUM_FILES)
    scraper.run()

    # Upload files to Control Room
    save_to_cloud(glob.glob(os.path.join(download_folder, "*.jpg")) + 
                glob.glob(os.path.join(download_folder, "*.png")))
    
    save_to_cloud([os.path.join(download_folder, "articles.xlsx")])

if __name__ == "__main__":
    main()
