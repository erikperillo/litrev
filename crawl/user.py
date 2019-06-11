#!/usr/bin/env python3

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from requests.utils import urlparse
import datetime as dt
import os

_FILE_DIR = os.path.abspath(os.path.dirname(__file__))
MAX_N_RETRIES = 5


def retry(max_n_times=1, verbose=True):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            for i in range(max_n_times):
                try:
                    ret = fn(*args, **kwargs)
                    return ret
                except Exception as e:
                    if verbose:
                        print('FAIL #{} @{}: "{}" - trying again'.format(
                            i+1, fn.__name__, e))
                    exc = e
            else:
                raise exc
        return wrapper
    return decorator


def get_chrome_driver(webdriver_path, page_load_timeout=25, headless=False):
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')
    driver = webdriver.Chrome(webdriver_path, chrome_options=options)
    if page_load_timeout is not None:
        driver.set_page_load_timeout(page_load_timeout)
    return driver


def is_in_domain(driver, netloc):
    driver_meta = urlparse(getattr(driver, 'current_url', ''))
    return driver_meta.netloc == netloc


def is_in_page(driver, url):
    meta_a = urlparse(url)
    meta_b = urlparse(getattr(driver, 'current_url', ''))
    return all([
        meta_a.netloc == meta_b.netloc,
        meta_a.path.rstrip('/') == meta_b.path.rstrip('/'),
    ])


@retry(MAX_N_RETRIES)
def access(driver, url, refresh=False):
    if refresh or not is_in_page(driver, url):
        driver.get(url)


def put_text(elem, text, clear=True):
    if clear:
        elem.clear()
    elem.send_keys(text)


def click(elem):
    elem.click()


class User:
    def __init__(self, driver, verbose=True):
        self.info = print if verbose else (lambda *a, **ka: None)
        self.driver = driver


    def access(self, url, refresh=False):
        self.info('acessing "{}"...'.format(url), flush=True, end=' ')
        access(self.driver, url, refresh=refresh)
        self.info('done.')


class ArxivUser(User):
    def get_results_elems(self):
        elems = self.driver.find_elements_by_class_name('arxiv-result')
        return elems


    def _get_title_elem(self, result_elem):
        elem = result_elem.find_element_by_class_name('title')
        return elem


    def get_title(self, result_elem):
        elem = self._get_title_elem(result_elem)
        title = elem.text.lower()
        return title


    def _get_authors_elem(self, result_elem):
        elem = result_elem.find_element_by_class_name('authors')
        return elem


    def _get_arxiv_id_elem(self, result_elem):
        elem = result_elem.find_element_by_class_name('list-title')
        elem = elem.find_element_by_tag_name('a')
        return elem


    def get_arxiv_id(self, result_elem):
        elem = self._get_arxiv_id_elem(result_elem)
        arxiv_id = elem.text.split(':')[1]
        return arxiv_id


    def _get_short_abstract_elem(self, result_elem):
        elem = result_elem.find_element_by_class_name('abstract-short')
        return elem


    def _get_expand_abstract_elem(self, short_abstract_elem):
        elem = short_abstract_elem.find_element_by_tag_name('a')
        return elem


    def _expand_abstract(self, short_abstract_elem):
        elem = self._get_expand_abstract_elem(short_abstract_elem)
        click(elem)


    def _get_full_abstract_elem(self, result_elem):
        elem = result_elem.find_element_by_class_name('abstract-full')
        return elem


    def get_abstract(self, result_elem):
        full_abstract_elem = self._get_full_abstract_elem(result_elem)
        if full_abstract_elem.value_of_css_property('display') == 'none':
            short_abstract_elem = self._get_short_abstract_elem(result_elem)
            self._expand_abstract(short_abstract_elem)
        #the last 7 chars are text of the button 'Less'
        text = full_abstract_elem.text[:-7].lower()
        return text


    def _get_authors_elems(self, result_elem):
        elem = result_elem.find_element_by_class_name('authors')
        elems = elem.find_elements_by_tag_name('a')
        return elems


    def get_authors(self, result_elem):
        elems = self._get_authors_elems(result_elem)
        authors = [e.text.lower() for e in elems]
        return authors


    def _get_submission_date_elem(self, result_elem):
        classes_to_avoid = {
            'list-title',
            'title',
            'authors',
            'abstract',
        }
        elems = result_elem.find_elements_by_tag_name('p')
        for elem in elems:
            classes = elem.get_attribute('class').split(' ')
            if not any(c in classes_to_avoid for c in classes):
                return elem
        raise ValueError('element not found')


    def _get_submission_date_text(self, result_elem):
        elem = self._get_submission_date_elem(result_elem)
        text = elem.text.split(';')[0].lower()
        assert text.startswith('submitted')
        text = text.lstrip('submitted ')
        return text


    _MONTHS = [
        'january',
        'february',
        'march',
        'april',
        'may',
        'june',
        'july',
        'august',
        'september',
        'october',
        'november',
        'december',
    ]
    _MONTHS_N_MAP = {m: i+1 for i, m in enumerate(_MONTHS)}


    def get_submission_date(self, result_elem):
        text = self._get_submission_date_text(result_elem)
        day = int(text.split(' ')[0])
        month = ArxivUser._MONTHS_N_MAP[text.split(' ')[1].rstrip(',')]
        year = int(text.split(' ')[-1])
        date = dt.date(year, month, day)
        return date


    def _get_next_results_page_btn_elem(self):
        try:
            elem = self.driver.find_element_by_class_name('pagination-next')
        except NoSuchElementException:
            return None
        return elem


    def go_to_next_results_page(self):
        elem = self._get_next_results_page_btn_elem()
        if elem is None:
            return False
        click(elem)
        return True


    def get_publication_data(self, result_elem, raise_on_error=True):
        data = {
            'title': None,
            'abstract': None,
            'authors': None,
            'submission_date': None,
            'arxiv_id': None,
        }
        try:
            data['title'] = self.get_title(result_elem)
            data['abstract'] = self.get_abstract(result_elem)
            data['authors'] = self.get_authors(result_elem)
            data['arxiv_id'] = self.get_arxiv_id(result_elem)
            data['submission_date'] = self.get_submission_date(result_elem)
        except Exception as e:
            if raise_on_error:
                raise e
            self.info('ERROR: {}'.format(e))
        return data
