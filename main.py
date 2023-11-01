import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException

import traceback
import time
import json
import logging
from logging.handlers import RotatingFileHandler

options = webdriver.ChromeOptions()
options.add_argument(
    '--user-agent=""Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5810.200 Safari/537.36""')
options.add_experimental_option('excludeSwitches', ['enable-logging'])

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s|%(name)s|%(levelname)s| %(message)s')

file_handler = RotatingFileHandler("parser.log", maxBytes=80000, backupCount=5)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)

logging.getLogger('selenium').setLevel(logging.WARNING)


def load_chat_list_from_file(file_path):
    try:
        with open(file_path, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_chat_list_to_file(chat_list, file_path):
    with open(file_path, 'w') as f:
        json.dump(list(chat_list), f)


def authorization(driver, use_tokens: bool):
    if use_tokens:
        try:
            with open("files/tokens.json", "r") as f:
                tokens = json.load(f)

            driver.get("https://web.telegram.org/a/")

            for key, value in tokens.items():
                set_item(driver, key, value)

            driver.refresh()
            time.sleep(3)
        except FileNotFoundError:
            logger.warning('File not found, please authorize in telegram, you have 60 seconds')
            driver.get("https://web.telegram.org/a/")
            time.sleep(60)
            tokens = driver.execute_script(
                "var tokens = {};\
                for (var i = 0; i < localStorage.length; i++){\
                    tokens[localStorage.key(i)] = localStorage.getItem(localStorage.key(i));\
                    };\
                return tokens;"
            )

            # with open("files/tokens.json", "w") as f:
            #     json.dump(tokens, f)
    else:
        driver.get("https://web.telegram.org/a/")
        time.sleep(60)


def extract_chats(driver):
    chat_list = set()
    unchanged_count = 0

    driver.execute_script("console.log('Вызван метод сбор списка чатов');")
    driver.execute_script("console.log('Поиск scrollable_container - div.chat-list');")

    scrollable_container = driver.find_element(By.CSS_SELECTOR, 'div.chat-list')

    previous_chats = []

    driver.execute_script("console.log('scrollable_container найден');")
    driver.execute_script("console.log('Запущен сбор списка чатов');")

    # scroll_bottom(driver, scrollable_container)
    driver.execute_script("console.log('Сбор чатов сверху вниз');")
    logger.info('Сбор чатов сверху вниз')

    while True:
        chat_list_element = driver.find_elements(By.CSS_SELECTOR, 'div.chat-list div')[1]
        current_chats = chat_list_element.find_elements(By.CSS_SELECTOR,
                                                        'div.ListItem.Chat.chat-item-clickable.private')

        if current_chats == previous_chats:
            unchanged_count += 1
            driver.execute_script(
                "console.log(`Текущий список чатов идентичен предыдущему. unchanged_count = ${arguments[0]}`);",
                unchanged_count)
        else:
            unchanged_count = 0
            for chat in current_chats:
                try:
                    chat_id = chat.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                except StaleElementReferenceException:
                    driver.execute_script(
                        "console.log('При парсинге идентификатора произошла ошибка StaleElementReferenceException');")
                    logger.exception('StaleElementReferenceException occurred!')
                    continue
                except Exception as E:
                    driver.execute_script(
                        "console.log('При парсинге идентификатора произошла ошибка');")
                    logger.exception(E)
                    continue
                chat_id = int(chat_id.replace('https://web.telegram.org/a/#', ''))
                chat_list.add(chat_id)
        if unchanged_count >= 1:
            driver.execute_script("arguments[0].scrollBy(0, -200);", scrollable_container)
            driver.execute_script("arguments[0].scrollBy(0, 400);", scrollable_container)
            time.sleep(1)
        if unchanged_count >= 5:
            driver.execute_script(
                "console.log('Первый этап сбора чатов закончен. Приступаю ко второму этапу..');")
            break
        previous_chats = current_chats

        driver.execute_script("arguments[0].scrollBy(0, 1500);", scrollable_container)
        time.sleep(1)

    driver.execute_script("console.log('Сбор чатов снизу вверх');")
    logger.info('Сбор чатов снизу вверх')
    unchanged_count = 0

    while True:
        chat_list_element = driver.find_elements(By.CSS_SELECTOR, 'div.chat-list div')[1]
        current_chats = chat_list_element.find_elements(By.CSS_SELECTOR,
                                                        'div.ListItem.Chat.chat-item-clickable.private')

        if current_chats == previous_chats:
            unchanged_count += 1
            driver.execute_script(
                "console.log(`Текущий список чатов идентичен предыдущему. unchanged_count = ${arguments[0]}`);",
                unchanged_count)
        else:
            unchanged_count = 0
            for chat in current_chats:
                try:
                    chat_id = chat.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                except StaleElementReferenceException:
                    driver.execute_script(
                        "console.log('При парсинге идентификатора произошла ошибка StaleElementReferenceException');")
                    logger.exception('StaleElementReferenceException occurred!')
                    continue
                except Exception as E:
                    driver.execute_script(
                        "console.log('При парсинге идентификатора произошла ошибка');")
                    logger.exception(E)
                    continue
                chat_id = int(chat_id.replace('https://web.telegram.org/a/#', ''))
                chat_list.add(chat_id)
        if unchanged_count >= 1:
            driver.execute_script("arguments[0].scrollBy(0, 200);", scrollable_container)
            driver.execute_script("arguments[0].scrollBy(0, -400);", scrollable_container)
            time.sleep(1)
        if unchanged_count >= 5:
            driver.execute_script(
                "console.log('Сбор чатов закончен');")
            break
        previous_chats = current_chats

        driver.execute_script("arguments[0].scrollBy(0, -2000);", scrollable_container)
        time.sleep(1)

    logger.info(f'Parsed chat list: {chat_list}')
    logger.info(f'Count of parsed chats: {len(chat_list)}')
    driver.execute_script("console.log('Кол-во собранных чатов', arguments[0]);", len(chat_list))
    return chat_list


def extract_chats_deep(driver):
    chat_list = set()
    unchanged_count = 0

    driver.execute_script("console.log('Вызван метод глубокого сбора списка чатов');")
    driver.execute_script("console.log('Поиск scrollable_container - div.chat-list');")

    scrollable_container = driver.find_element(By.CSS_SELECTOR, 'div.chat-list')

    previous_chats = []

    driver.execute_script("console.log('scrollable_container найден');")
    driver.execute_script("console.log('Запущен глубокий сбор списка чатов');")

    # scroll_bottom(driver, scrollable_container)
    driver.execute_script("console.log('Сбор чатов сверху вниз');")
    logger.info('Сбор чатов сверху вниз')

    while True:
        chat_list_element = driver.find_elements(By.CSS_SELECTOR, 'div.chat-list div')[1]
        current_chats = chat_list_element.find_elements(By.CSS_SELECTOR,
                                                        'div.ListItem.Chat.chat-item-clickable.private')

        if current_chats == previous_chats:
            unchanged_count += 1
            driver.execute_script(
                "console.log(`Текущий список чатов идентичен предыдущему. unchanged_count = ${arguments[0]}`);",
                unchanged_count)
        else:
            unchanged_count = 0
            for chat in current_chats:
                try:
                    chat_id = chat.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                except StaleElementReferenceException:
                    driver.execute_script(
                        "console.log('При парсинге идентификатора произошла ошибка StaleElementReferenceException');")
                    logger.exception('StaleElementReferenceException occurred!')
                    continue
                except Exception as E:
                    driver.execute_script(
                        "console.log('При парсинге идентификатора произошла ошибка');")
                    logger.exception(E)
                    continue
                chat_id = int(chat_id.replace('https://web.telegram.org/a/#', ''))
                chat_list.add(chat_id)
        if unchanged_count >= 1:
            driver.execute_script("arguments[0].scrollBy(0, -100);", scrollable_container)
            driver.execute_script("arguments[0].scrollBy(0, 300);", scrollable_container)
            driver.execute_script("arguments[0].scrollBy(0, -100);", scrollable_container)
            driver.execute_script("arguments[0].scrollBy(0, 300);", scrollable_container)
            time.sleep(1)
        if unchanged_count >= 5:
            driver.execute_script(
                "console.log('Первый этап глубокого сбора чатов закончен. Приступаю ко второму этапу..');")
            break
        previous_chats = current_chats

        driver.execute_script("arguments[0].scrollBy(0, 500);", scrollable_container)
        time.sleep(0.5)

    driver.execute_script("console.log('Сбор чатов снизу вверх');")
    logger.info('Сбор чатов снизу вверх')
    unchanged_count = 0

    while True:
        chat_list_element = driver.find_elements(By.CSS_SELECTOR, 'div.chat-list div')[1]
        current_chats = chat_list_element.find_elements(By.CSS_SELECTOR,
                                                        'div.ListItem.Chat.chat-item-clickable.private')

        if current_chats == previous_chats:
            unchanged_count += 1
            driver.execute_script(
                "console.log(`Текущий список чатов идентичен предыдущему. unchanged_count = ${arguments[0]}`);",
                unchanged_count)
        else:
            unchanged_count = 0
            for chat in current_chats:
                try:
                    chat_id = chat.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                except StaleElementReferenceException:
                    driver.execute_script(
                        "console.log('При парсинге идентификатора произошла ошибка StaleElementReferenceException');")
                    logger.exception('StaleElementReferenceException occurred!')
                    continue
                except Exception as E:
                    driver.execute_script(
                        "console.log('При парсинге идентификатора произошла ошибка');")
                    logger.exception(E)
                    continue
                chat_id = int(chat_id.replace('https://web.telegram.org/a/#', ''))
                chat_list.add(chat_id)
        if unchanged_count >= 1:
            driver.execute_script("arguments[0].scrollBy(0, 100);", scrollable_container)
            driver.execute_script("arguments[0].scrollBy(0, -300);", scrollable_container)
            driver.execute_script("arguments[0].scrollBy(0, 100);", scrollable_container)
            driver.execute_script("arguments[0].scrollBy(0, -300);", scrollable_container)
            time.sleep(1)
        if unchanged_count >= 5:
            driver.execute_script(
                "console.log('Глубокий сбор чатов закончен');")
            break
        previous_chats = current_chats

        driver.execute_script("arguments[0].scrollBy(0, -1000);", scrollable_container)
        time.sleep(1)

    logger.info(f'Parsed chat list: {chat_list}')
    logger.info(f'Count of parsed chats: {len(chat_list)}')
    driver.execute_script("console.log('Кол-во собранных чатов', arguments[0]);", len(chat_list))
    return chat_list


def back_top(driver, scrollable_container, shift):
    attempts = 0
    last_first_visible_chat = None

    while shift != 0:
        driver.execute_script("arguments[0].scrollBy(0, -2000);", scrollable_container)
        time.sleep(0.5)

        try:
            chat_list_element = driver.find_elements(By.CSS_SELECTOR, 'div.chat-list div')[1]
            current_chats = chat_list_element.find_elements(By.CSS_SELECTOR, 'div.ListItem.Chat')
            first_visible_chat = current_chats[0]
            style_attr = first_visible_chat.get_attribute('style')
            shift = int(style_attr.replace('top: ', '').replace('px;', '')) if style_attr else 100

            if last_first_visible_chat == first_visible_chat:
                attempts += 1
                time.sleep(0.3)
            else:
                attempts = 0

            last_first_visible_chat = first_visible_chat

            if attempts >= 5:
                logger.info("Остановка скроллинга")
                driver.execute_script("console.log('Список диалогов не смог обновиться, выход из скроллинга');")
                break

        except Exception as e:
            logger.exception(f"Произошла ошибка: {e}")
            driver.execute_script("console.log('При скроллинге произошла непредвиденная ошибка', argument[0]);", e)
            break


def scroll_bottom(driver, scrollable_container):
    attempts = 0
    previous_chats = None

    while True:
        driver.execute_script("arguments[0].scrollBy(0, 2000);", scrollable_container)
        time.sleep(0.5)

        try:
            chat_list_element = driver.find_elements(By.CSS_SELECTOR, 'div.chat-list div')[1]
            current_chats = chat_list_element.find_elements(By.CSS_SELECTOR, 'div.ListItem.Chat')

            if previous_chats == current_chats:
                attempts += 1
                time.sleep(0.3)
            else:
                attempts = 0

            previous_chats = current_chats

            if attempts >= 1:
                driver.execute_script("arguments[0].scrollBy(0, -200);", scrollable_container)
                driver.execute_script("arguments[0].scrollBy(0, 400);", scrollable_container)
                time.sleep(1)

            if attempts >= 5:
                logger.info("Остановка скроллинга")
                driver.execute_script("console.log('Список диалогов не смог обновиться, выход из скроллинга');")
                break

        except Exception as e:
            logger.exception(f"Произошла ошибка: {e}")
            driver.execute_script("console.log('При скроллинге произошла непредвиденная ошибка', argument[0]);", e)
            break


def scan_new_chats(driver, chat_list, messages, file_path):
    previous_chats = []
    driver.execute_script("console.log('Вызван метод поиска новых чатов');")

    scrollable_container = driver.find_element(By.CSS_SELECTOR, 'div.chat-list')
    counter = 0

    while True:
        logger.info('scanning new chats..')
        chat_list_element = driver.find_elements(By.CSS_SELECTOR, 'div.chat-list div')[1]
        current_chats = chat_list_element.find_elements(By.CSS_SELECTOR,
                                                        'div.ListItem.Chat.chat-item-clickable.private')

        if current_chats != previous_chats:
            for chat in current_chats:
                try:
                    chat_id = chat.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                except StaleElementReferenceException:
                    logger.exception('StaleElementReferenceException occurred!')
                    continue
                except NoSuchElementException:
                    logger.exception('NoSuchElementException occurred!')
                    continue
                chat_id = int(chat_id.replace('https://web.telegram.org/a/#', ''))
                if chat_id not in chat_list:
                    logger.info(f"new chat {chat_id} has been found")
                    driver.execute_script(f"console.log('Обнаружен новый чат: {chat_id}');")
                    driver.execute_script("console.log('Отправка сообщения');")
                    send_message(driver, chat, chat_id, messages)
                    chat_list.add(chat_id)
                    to_saved_messages(driver)
                    save_chat_list_to_file(chat_list, file_path)
                    logger.info('Saved updated chat list to file')
                else:
                    logger.info(f'chat with {chat_id} already in chat_list')

        previous_chats = current_chats
        counter += 1
        if counter == 5:
            driver.execute_script("arguments[0].scrollBy(0, 200);", scrollable_container)
            driver.execute_script("arguments[0].scrollBy(0, -200);", scrollable_container)
            counter = 0
        time.sleep(0.3)


def send_message(driver, chat, chat_id, messages):
    chat.click()
    time.sleep(0.5)

    own_messages = driver.find_elements(By.CSS_SELECTOR, 'div.Message.own')
    if not own_messages:
        try:
            input_field = driver.find_element(By.ID, 'editable-message-text')
        except NoSuchElementException:
            chat.click()
            time.sleep(0.3)
            input_field = driver.find_element(By.ID, 'editable-message-text')

        driver.execute_script("arguments[0].click();", input_field)
        driver.execute_script(f'arguments[0].innerText = arguments[1];', input_field, messages['first_message'])
        driver.execute_script("var event = new Event('input', { 'bubbles': true }); arguments[0].dispatchEvent(event);",
                              input_field)

        time.sleep(0.1)
        send_button = driver.find_element(By.CSS_SELECTOR, 'button.Button.send')

        # time.sleep(0.1)
        send_button.click()
        driver.execute_script("console.log('Сообщение отправлено');")

        time.sleep(0.2)

        driver.execute_script("arguments[0].click();", input_field)
        driver.execute_script(f'arguments[0].innerText = arguments[1];', input_field, messages['second_message'])
        driver.execute_script("var event = new Event('input', { 'bubbles': true }); arguments[0].dispatchEvent(event);",
                              input_field)

        time.sleep(0.5)
    else:
        driver.execute_script(
            "console.log(`Ложное срабатывание на пользователе ${arguments[0]}. "
            "Он не был обнаружен при поиске, рекомендуется повторно провести глубокое сканирование чатов`);",
            chat_id)
        logger.warning(f'Ложное срабатывание на пользователе {chat_id}. '
                       f'Он не был обнаружен при поиске, рекомендуется повторно провести глубокое сканирование чатов')


def to_saved_messages(driver):
    try:
        saved_messages_element = driver.find_element(By.CSS_SELECTOR, ".ListItem.Chat:has(div.saved-messages)")
        saved_messages_element.click()
    except Exception as E:
        logger.exception(E)


def main(use_tokens: bool, deep_search: bool):
    logger.info('App startup')

    try:
        with open("first_message.txt", "r", encoding="utf-8") as file:
            first_message = file.read()

        with open("second_message.txt", "r", encoding="utf-8") as file:
            second_message = file.read()
    except FileNotFoundError:
        logger.exception('Files loaded with error! Using dummy messages')
        first_message = 'first_message'
        second_message = 'second_message'
    else:
        logger.info('Files successfully loaded')

    messages = {
        'first_message': first_message,
        'second_message': second_message,
    }

    logger.info('Driver starting')
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()

    try:
        logger.info('Authorization process started. You have 60 seconds to authorize in telegram')
        authorization(driver, use_tokens)
        logger.info('Successful authorization')

        # Загрузка chat_list из файла
        file_path = 'chat_list.txt'
        chat_list = load_chat_list_from_file(file_path)
        logger.info('Loaded chat list from file')

        if deep_search:
            logger.info('Deep chat extracting process started')
            new_chat_list = extract_chats_deep(driver)
        else:
            logger.info('Simple chat extracting process started')
            new_chat_list = extract_chats(driver)

        logger.info('Successful extracting')

        # Объединение сетов
        chat_list.update(new_chat_list)
        logger.info('Updated chat list')

        # Сохранение chat_list в файл
        save_chat_list_to_file(chat_list, file_path)
        logger.info('Saved updated chat list to file')

        logger.info('Scanning process started')
        scan_new_chats(driver, chat_list, messages, file_path)

    except Exception as E:
        logger.exception(E)
    finally:
        driver.quit()


def set_item(driver, key, value):
    driver.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", key, value)


if __name__ == '__main__':
    deep_search = input('Желаете провести глубокий анализ чатов?(y/n)').lower()
    yes_variants = ['y', 'yes', 'да', 'д']
    deep_search = deep_search in yes_variants
    use_tokens = False
    main(use_tokens, deep_search)
