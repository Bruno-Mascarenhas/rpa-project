import os
import re

from datetime import datetime

from RPA.Browser.Selenium import Selenium, By
from RPA.Excel.Files import Files
from selenium.common.exceptions import (
    WebDriverException, NoSuchElementException,
    ElementNotInteractableException, StaleElementReferenceException
)
from selenium.webdriver.remote.webelement import WebElement
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
        self.driver.set_selenium_implicit_wait(15) # type: ignore
        self.driver.set_selenium_speed(15) # type: ignore
        self.ids = set()
        self.news = []

    def __del__(self) -> None:
        self.driver.close_all_browsers()

    def run(self) -> None:
        # Open browser and search for news according to RPA best practices
        try:
            self.driver.open_available_browser(self.site_url, maximized=True)
            self._search()
            self._apply_filters()
            self._extract_news()
            self._store_news()
        except WebDriverException as exception:
            logger.error("Webdriver exception: %s", exception)
        except Exception as exception:
            logger.error("Error while running the process: %s", exception)
        finally:
            self.driver.close_all_browsers()

    def _close_cookie_banner(self) -> None:
        # Close cookie banner if it exists
        try:
            logger.info("Closing cookie banner...")
            self.driver.wait_and_click_button("xpath://button[@data-testid='expanded-dock-btn-selector']")
            return
        except NoSuchElementException:
            logger.info("Cookie banner not found")
        except Exception as exception:
            logger.info("Cookie banner not closed duo to %s", exception)
        raise Exception("Cookie banner not closed")
        
    def _search(self) -> None:
        try:
            # Search for the phrase and submit
            logger.info("Input search phrase and submiting search...")
            self.driver.click_button("xpath://button[@data-test-id='search-button']")
            self.driver.input_text("xpath://input[@data-testid='search-input']", self.search_phrase)
            self.driver.click_button("xpath://button[@data-test-id='search-submit']")
            return
        except ElementNotInteractableException:
            logger.info("Search button not found")
        except Exception as exception:
            logger.info("Search not resolved duo to %s", exception)
        raise Exception("Search not resolved")

    def _apply_filters(self) -> None:
        # Apply filters after closing cookie banner, just sort if there is no category
        self._close_cookie_banner()
        logger.info("Applying filters...")
        try:
            self.driver.click_button("xpath://button[@data-testid='search-multiselect-button']")
            multisel_xpath = "xpath://button[contains(@class, 'popup-visible') and @data-testid='search-multiselect-button']"
            self.driver.wait_until_page_contains_element(multisel_xpath)
        except NoSuchElementException:
            logger.info("Section button not found")
            raise Exception("Section button not found")

        # If there is no match for the category, just sort
        for category in self.news_category.split(","):
            try:
                logger.info("Selecting category %s...", category)
                self.driver.wait_and_click_button(f"xpath://input[contains(@value,'{category.strip()}')]")
            except ElementNotInteractableException:
                logger.info("Category %s not interactable", category)
            except NoSuchElementException:
                logger.info("Category %s not found", category)

        try:
            logger.info("Sorting by newest...")
            self.driver.select_from_list_by_value("xpath://select[@data-testid='SearchForm-sortBy']", "newest")
        except NoSuchElementException:
            logger.info("Sorting by newest option not found")
            raise Exception("Sorting not by newest resolved")

    def _extract_news(self) -> None:
        # Determine time range for filtering news
        end_date = datetime.now()
        start_date = end_date.replace(day=1) - relativedelta(months=max(0,self.num_months-1))

        first_page = True
        stop_processing = False

        while not stop_processing:
            # Get all articles on current page
            logger.info("Extracting articles..., current number of articles: %s", len(self.news))

            articles = self.driver.find_elements("xpath:.//li[@data-testid='search-bodega-result']") # type: ignore

            if len(articles) == 0 or len(self.news) >= self.max_files:
                # No more articles or max number of files reached
                stop_processing = True
                logger.info("Finished extracting articles, number of articles: %s", len(self.news))
                break

            try:
                stop_processing = self._process_articles(articles, start_date)
            except StaleElementReferenceException as exception:
                logger.info("Stale element reference exception: %s", exception)
                if first_page:
                    # If first page fails = is staleness of the page, false results
                    self.news = []
                    logger.info("No articles found")
                continue

            # Move to next page and wait for page to load after requesting more articles
            try:
                logger.info("Requesting more articles...")
                self.driver.wait_until_element_is_visible("xpath://button[@data-testid='search-show-more-button']")
                self.driver.wait_and_click_button("xpath://button[@data-testid='search-show-more-button']")
                first_page = False
            except NoSuchElementException:
                logger.info("No more articles to request")
                break
            except Exception as exception:
                logger.info("Error requesting more articles: %s", exception)
                break

    def _process_articles(self, articles: list[WebElement], start_date: datetime) -> bool:
        stop_processing = False

        for article in articles:
            # Get headline, check for duplicates and filter by date
            try:
                headline_element = article.find_element(By.XPATH, ".//li//a/*[1]")
                headline = headline_element.text
            except StaleElementReferenceException:
                logger.info("Stale element reference, trying again...")
                break

            # Hash the headline to check for duplicates
            headline_hash = hash(headline)

            if headline_hash in self.ids:
                continue

            self.ids.add(headline_hash)

            # Get date to filter articles, if older than start date, stop processing
            date_element = article.find_element(By.XPATH, ".//span[@data-testid='todays-date']")
            date_str = date_element.text
            date = convert_date(date_str)
            
            if date < start_date:
                stop_processing = True
                break

            try:
                logger.info("Processing article: %s", len(self.news)+1)
                # Get description and image name
                description, img_filename = self._get_article_details(article)
            except StaleElementReferenceException:
                # If stale element reference, skip bucket and try again
                logger.info("Stale element reference, trying again...")
                if headline_hash in self.ids:
                    self.ids.remove(headline_hash)
                break
            # Count number of search phrase occurrences in headline and description
            # and if contains any amount of money
            search_count = len(re.findall(self.search_phrase, f"{headline} {description}"))
            money_found = bool(re.search(r"\$[\d,.]+|[\d,.]+ dollars|\d+ USD", f"{headline} {description}"))

            # Store data in list
            self.news.append({
                "date": date.strftime("%Y-%m-%d"),
                "title": headline,
                "description": description,
                "picture_filename": img_filename,
                "search_count": search_count,
                "money_found": money_found
            })

        return stop_processing
    
    def _get_article_details(self, article: WebElement) -> tuple:
        try:
            desc_element = article.find_element(By.XPATH, ".//li//a/*[2]")
            description = desc_element.text
        except ElementNotInteractableException as exception:
            logger.error("Description not interactable: %s", exception)
        except NoSuchElementException as exception:
            logger.error("Description not found: %s", exception)
        finally:
            description = ""

        try:
            img_element = article.find_element(By.XPATH, ".//img")
            img_url = img_element.get_attribute("src")
            logger.info("Downloading image: %s, please wait...", img_url)
            img_filename = download_image(img_url, self.download_dir)
            logger.info("Image downloaded: %s", img_filename)
        except ElementNotInteractableException as exception:
            logger.error("Image not interactable: %s", exception)
        except NoSuchElementException as exception:
            logger.error("Image not found: %s", exception)
        finally:
            img_filename = ""

        return description, img_filename

    def _store_news(self) -> None:
        # Create excel file with header and store the results
        logger.info("Storing news to EXCEL file...")
        excel_file = Files()
        workbook = excel_file.create_workbook()

        try:
            headers = ["date", "title", "description", "picture_filename", "search_count", "money_found"]
            for col, header in enumerate(headers, start=1):
                workbook.set_cell_value(1, col, header)

            for row, record in enumerate(self.news, start=2):
                for col, (_, value) in enumerate(record.items(), start=1):
                    workbook.set_cell_value(row, col, value)
        except Exception as exception:
            logger.error("Error while storing data to EXCEL file: %s", exception)
            raise Exception("Error while storing data to EXCEL file")

        path_excel = os.path.join(self.download_dir, self.excel_filename)
        workbook.save(path_excel)
        logger.info("Finished storing news to EXCEL file. Exiting...")
