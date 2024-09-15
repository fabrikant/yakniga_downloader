import argparse
import logging
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from pathvalidate import sanitize_filename
import js2py
import shutil
import re


logger = logging.getLogger(__name__)
site_url = "https://yakniga.org"


def get_file_list(book_soup):
    logger.debug("Парсинг страницы. Поиск адресов файлов для загрузки")
    result = None
    scripts = book_soup.findAll("script")
    for script in scripts:
        script_text = script.text
        if "basePath" in script_text:
            logger.debug("Обнаружен скрипт")

            script_text = script_text.replace(
                "window.__NUXT__=(",
                "",
            )

            re_match = re.search("}}}\(.+Chapter.+\)\)", script_text)
            str_args = re_match.group(0)[3:]
            script_text = script_text.replace(str_args, "")

            js_func = js2py.eval_js(script_text)
            # data = js_func(
            #     "Chapter",
            #     False,
            #     "id",
            #     None,
            #     "",
            #     True,
            #     "Genre",
            #     0,
            #     "Author",
            #     "Reader",
            #     "Book",
            #     "EbookCollection",
            #     "ChapterCollection",
            #     "GenreCollection",
            #     "system",
            # )

            data = js_func()

            result = data["apollo"]["defaultClient"].to_dict()
            return result
    return result


def download_mp3(url, path, filename, file_number=""):
    url_string = site_url + url
    logger.debug("try to download file: " + url_string)
    full_filename = Path(path) / sanitize_filename(f"{filename}.mp3")
    if file_number > 0:
        full_filename = Path(path) / sanitize_filename(
            f"{file_number:03d} {filename}.mp3"
        )
    res = requests.get(url_string, stream=True)
    if res.status_code == 200:
        with open(full_filename, "wb") as f:
            shutil.copyfileobj(res.raw, f)
        logger.warning(f"file has been downloaded and saved as: {full_filename}")
    else:
        logger.error(f"code: {res.status_code} while downloading: {url_string}")
        exit(1)


def download_book(book_url, output_folder):
    logger.debug(f"Запуск загрузки страницы книги: {book_url}")
    page = requests.get(book_url)
    book_html = page.text
    book_soup = BeautifulSoup(book_html, "html.parser")

    book_name = book_soup.find("h1").get_text()
    book_path = Path(output_folder) / sanitize_filename(book_name)
    Path(book_path).mkdir(exist_ok=True)

    mp3_list = get_file_list(book_soup)
    if mp3_list == None:
        logger.error("Не удалось найти список файлов")
        exit(1)

    num = 0
    for key, value in mp3_list.items():

        if "Chapter" in key:
            num += 1
            download_mp3(value["fileUrl"], book_path, value["name"], file_number=num)

    logger.warning("Загрузка завершена")


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    parser = argparse.ArgumentParser(description="Загрузчик книг с сайта yakniga.org")
    parser.add_argument("-o", "--output", help="Путь к папке загрузки", default=".")
    parser.add_argument("url", help="Адрес (url) страницы с книгой")

    args = parser.parse_args()
    logger.info(args)
    download_book(args.url, args.output)
