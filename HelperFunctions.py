from config import GECKO_PATH
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import re


def get_soup(url: str, wait_class_name: str) -> BeautifulSoup:
    """
    Inizialises a new driver object and uses it to get the html source of a site specified by url.

    :Keyword arguments:
     - url - the url you want to get the source of
     - wait_class_name - the class name of the class you want to load before you fetch the source
    """
    options = FirefoxOptions()
    options.add_argument("--headless")
    driver = webdriver.Firefox(
        options=options,
        executable_path=GECKO_PATH,
    )

    # The website does not load fully when you dont wait for it to load
    driver.get(url)
    try:
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, wait_class_name))
        )
    except Exception as e:
        driver.close()
        raise e

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    driver.close()
    return soup


def get_domain(url: str) -> str:
    """Returns the domain given a url"""
    pattern = r"(\w+://)?[^/]+(?=/(?!/))"
    return re.search(pattern, url).group(0)
