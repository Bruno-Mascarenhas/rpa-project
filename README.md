## Project Description

This project is a Python-based web scraper designed to extract news articles from the website "The New York Times". The program allows the user to input a search phrase and a news category, as well as the number of months to search within, the maximum number of files to extract, and the path to a directory where the article images will be stored.

The program then uses Selenium and other Python libraries to navigate the site, extract relevant information, and save the results to a Excel file.

## Requirements

To run the program, you will need to install the following Python dependencies:

- `python=3.9.13`
- `pip=22.1.2`
- `rpaframework==22.0.0`


## Usage

To use the program, run the `task.py` file with the following parameters (.env file):

- `search_phrase`: A string containing the search phrase to be used.
- `news_category`: A string containing the news category to be searched, separated by commas.
- `num_months`: An integer representing the number of months to search within.
- `download_dir`: A string containing the path to the directory where the article images will be stored.
- `excel_filename`: A string containing the name of the Excel file to be created.
- `num_files`: An integer representing the maximum number of files to extract.

## Example

```python
from news_scraper import NewsScraper

scraper = NewsScraper(search_phrase="climate change", news_category="World, Climate", num_months=6, download_dir="downloads", excel_filename="articles.xlsx", num_files=50)
scraper.run()
```

This example creates a `NewsScraper` object and searches for articles containing the phrase "climate change" in the "World" and "Climate" categories, within the last 6 months. It saves the article images to a directory called "images" and saves the results to an Excel file called "articles.xlsx". It extracts a maximum of 50 files.