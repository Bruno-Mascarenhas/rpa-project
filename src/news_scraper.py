import time
import re

from datetime import datetime

from RPA.Browser.Selenium import Selenium, By
from RPA.Excel.Files import Files
from dateutil.relativedelta import relativedelta

from .util import convert_date, download_image, configure_logger

logger = configure_logger()

class NewsScraper:
    def __init__(self, search_phrase: str, news_category: str, num_months: int, 
                    download_dir: str, excel_filename: str, num_files: int,
                    site_url: str = "https://www.nytimes.com/") -> None:
        
        self.search_phrase = search_phrase
        self.news_category = news_category
        self.num_months = num_months
        self.site_url = site_url
        self.download_dir = download_dir
        self.excel_filename = excel_filename
        self.max_files = num_files

        self.driver = Selenium()
        self.driver.set_selenium_implicit_wait(10)
        self.driver.set_selenium_speed(4)

    def __del__(self) -> None:
        self.driver.close_all_browsers()

    def run(self) -> None:
        try:
            self.driver.open_available_browser(self.site_url, maximized=True)
            self._search()
            self._apply_filters()
            self._extract_news()
        except Exception as e:
            logger.error(e)
        finally:
            self.driver.close_all_browsers()

    def _close_cookie_banner(self) -> None:
        try:
            self.driver.wait_and_click_button("xpath://button[@data-testid='expanded-dock-btn-selector']")
        except:
            logger.info("Cookie banner not found")

    def _search(self) -> None:
        try:
            self.driver.click_button("xpath://button[@data-test-id='search-button']")
            self.driver.input_text("xpath://input[@data-testid='search-input']", self.search_phrase)
            self.driver.click_button("xpath://button[@data-test-id='search-submit']")
        except Exception as e:
            logger.info("Search not resolved")
            logger.error(e)

    def _apply_filters(self) -> None:
        # Apply filters after closing cookie banner, just sort if there is no category
        self._close_cookie_banner()
        self.driver.click_button("xpath://button[@data-testid='search-multiselect-button']")

        for category in self.news_category.split(","):
            try:
                self.driver.wait_and_click_button(f"xpath://input[contains(@value,'{category.strip()}')]")
                time.sleep(1)    
            except:
                logger.info(f"Category {self.news_category} not found")

        try:
            self.driver.select_from_list_by_value("xpath://select[@data-testid='SearchForm-sortBy']", "newest")
            time.sleep(1)
        except:
            logger.info("Sorting not resolved")

        time.sleep(0.5)

    def _extract_news(self) -> None:
        # Determine time range for filtering news
        time.sleep(0.5)
        end_date = datetime.now()
        start_date = end_date.replace(day=1) - relativedelta(months=max(0,self.num_months-1))

        news = []
        ids = set()
        stop_processing = False

        while not stop_processing:
            # Get all articles on current page
            articles = self.driver.find_elements("xpath:.//li[@data-testid='search-bodega-result']")            
            
            if len(articles) == 0 or len(news) >= self.max_files:
                # No more articles or max number of files reached
                stop_processing = True
                break

            for article in articles:
                headline_element = article.find_element(By.XPATH, ".//h4[@class='css-2fgx4k']")
                headline = headline_element.text
                
                # Hash the headline to check for duplicates
                headline_hash = hash(headline)

                if headline_hash in ids:
                    continue
                else:
                    ids.add(headline_hash)

                # Get date to filter articles, if older than start date, stop processing (custom format)
                date_element = article.find_element(By.XPATH, ".//span[@class='css-17ubb9w']")
                date_str = date_element.text
                date = convert_date(date_str)
                
                if date < start_date:
                    stop_processing = True
                    break

                else:
                    try:
                        desc_element = article.find_element(By.XPATH, ".//p[@class='css-16nhkrn']")
                        description = desc_element.text
                    except Exception as e:
                        logger.error(e)
                        description = ""

                    try:
                        img_element = article.find_element(By.XPATH, ".//img[@class='css-rq4mmj']")
                        img_url = img_element.get_attribute("src")
                        img_filename = download_image(img_url, self.download_dir)
                    except Exception as e:
                        logger.error(e)
                        img_filename = ""

                    # Count number of search phrase occurrences in headline and description and is contains any amount of money
                    search_count = len(re.findall(self.search_phrase, f"{headline} {description}"))
                    money_found = bool(re.search(r"\$[\d,.]+|[\d,.]+ dollars|\d+ USD", f"{headline} {description}"))

                    # Store data in list
                    news.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "title": headline,
                        "description": description,
                        "picture_filename": img_filename,
                        "search_count": search_count,
                        "money_found": money_found
                    })

                    # Delay for next article (to avoid too long queries)
                    time.sleep(0.5)
            
            # Move to next page and wait for page to load after requesting more articles
            try:
                self.driver.wait_and_click_button("xpath://button[@data-testid='search-show-more-button']")
            except:
                break
            time.sleep(0.5)

        # Save news to EXCEL file
        self._store_news(news)

    def _store_news(self, news: list) -> None:
        # Create excel file with header and store the results
        excel_file = Files()
        workbook = excel_file.create_workbook()

        try:
            headers = ["date", "title", "description", "picture_filename", "search_count", "money_found"]
            for col, header in enumerate(headers, start=1):
                workbook.set_cell_value(1, col, header)

            for row, record in enumerate(news, start=2):
                for col, (key, value) in enumerate(record.items(), start=1):
                    workbook.set_cell_value(row, col, value)
        except:
            logger.error("Error while storing data to EXCEL file")
        
        workbook.save(f"{self.excel_filename}")
