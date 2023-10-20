import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException

import traceback
import time
import json

options = webdriver.ChromeOptions()
options.add_argument(
    '--user-agent=""Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5810.200 Safari/537.36""')


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
            print('File not found, please authorize in telegram, you have 60 seconds')
            driver.get("https://web.telegram.org/a/")
            time.sleep(60)
            tokens = driver.execute_script(
                "var tokens = {};\
                for (var i = 0; i < localStorage.length; i++){\
                    tokens[localStorage.key(i)] = localStorage.getItem(localStorage.key(i));\
                    };\
                return tokens;"
            )

            with open("files/tokens.json", "w") as f:
                json.dump(tokens, f)
    else:
        driver.get("https://web.telegram.org/a/")
        time.sleep(60)


def extract_chats(driver):
    chat_list = set()
    unchanged_count = 0

    scrollable_container = driver.find_element(By.CSS_SELECTOR, 'div.chat-list')
    driver.execute_script("arguments[0].scrollBy(0, -20000);", scrollable_container)

    previous_chats = []

    while True:
        chat_list_element = driver.find_elements(By.CSS_SELECTOR, 'div.chat-list div')[1]
        current_chats = chat_list_element.find_elements(By.CSS_SELECTOR,
                                                        'div.ListItem.Chat.chat-item-clickable.private')

        if current_chats == previous_chats:
            unchanged_count += 1
        else:
            unchanged_count = 0
            for chat in current_chats:
                try:
                    chat_id = chat.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                except StaleElementReferenceException:
                    print('StaleElementReferenceException occurred!')
                    continue
                chat_id = int(chat_id.replace('https://web.telegram.org/a/#', ''))
                chat_list.add(chat_id)
        if unchanged_count >= 1:
            driver.execute_script("arguments[0].scrollBy(0, -200);", scrollable_container)
            driver.execute_script("arguments[0].scrollBy(0, 400);", scrollable_container)
            time.sleep(1)
        if unchanged_count >= 3:
            first_visible_chat = current_chats[0]
            shift = int(first_visible_chat.get_attribute('style').replace('top: ', '').replace('px;', ''))
            back_top(driver, scrollable_container, shift)
            break
        previous_chats = current_chats

        driver.execute_script("arguments[0].scrollBy(0, 2000);", scrollable_container)
        time.sleep(1)

    print(f'Parsed chat list: {chat_list}')
    print(f'Count of parsed chats: {len(chat_list)}')
    return chat_list


def back_top(driver, scrollable_container, shift):
    while shift != 0:
        driver.execute_script("arguments[0].scrollBy(0, -2000);", scrollable_container)
        time.sleep(0.5)

        chat_list_element = driver.find_elements(By.CSS_SELECTOR, 'div.chat-list div')[1]
        current_chats = chat_list_element.find_elements(By.CSS_SELECTOR, 'div.ListItem.Chat')

        first_visible_chat = current_chats[0]
        shift = int(first_visible_chat.get_attribute('style').replace('top: ', '').replace('px;', ''))


def scan_new_chats(driver, chat_list, messages):
    previous_chats = []

    while True:
        print('scanning new chats..')
        chat_list_element = driver.find_elements(By.CSS_SELECTOR, 'div.chat-list div')[1]
        current_chats = chat_list_element.find_elements(By.CSS_SELECTOR,
                                                        'div.ListItem.Chat.chat-item-clickable.private')

        if current_chats != previous_chats:
            for chat in current_chats:
                try:
                    chat_id = chat.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
                except StaleElementReferenceException:
                    print('StaleElementReferenceException occurred!')
                    continue
                except NoSuchElementException:
                    print('NoSuchElementException occurred!')
                    continue
                chat_id = int(chat_id.replace('https://web.telegram.org/a/#', ''))
                if chat_id not in chat_list:
                    print("new_chat!")
                    send_message(driver, chat, messages)
                    chat_list.add(chat_id)
                    to_saved_messages(driver)
                else:
                    print(f'chat with {chat_id} already in chat_list')

        previous_chats = current_chats
        time.sleep(0.5)


def send_message(driver, chat, messages):
    chat.click()
    time.sleep(0.5)
    input_field = driver.find_element(By.ID, 'editable-message-text')

    driver.execute_script("arguments[0].click();", input_field)
    driver.execute_script(f'arguments[0].innerText = arguments[1];', input_field, messages['first_message'])
    driver.execute_script("var event = new Event('input', { 'bubbles': true }); arguments[0].dispatchEvent(event);",
                          input_field)

    time.sleep(0.1)
    send_button = driver.find_element(By.CSS_SELECTOR, 'button.Button.send')

    time.sleep(0.2)
    send_button.click()

    time.sleep(0.5)

    driver.execute_script("arguments[0].click();", input_field)
    for char in messages['second_message']:
        driver.execute_script(f"arguments[0].innerText += '{char}';", input_field)
        driver.execute_script("var event = new Event('input', { 'bubbles': true }); arguments[0].dispatchEvent(event);",
                              input_field)
        time.sleep(0.1)

    time.sleep(0.5)


def to_saved_messages(driver):
    try:
        saved_messages_element = driver.find_element(By.CSS_SELECTOR, ".ListItem.Chat:has(div.saved-messages)")
        saved_messages_element.click()
    except Exception as E:
        print(traceback.format_exc())


def main(use_tokens):
    with open("first_message.txt", "r", encoding="utf-8") as file:
        first_message = file.read()

    with open("second_message.txt", "r", encoding="utf-8") as file:
        second_message = file.read()

    messages = {
        'first_message': first_message,
        'second_message': second_message,
    }

    driver = webdriver.Chrome(options=options)
    driver.maximize_window()

    try:
        authorization(driver, use_tokens)

        chat_list = extract_chats(driver)

        scan_new_chats(driver, chat_list, messages)

        time.sleep(300)
    except Exception as E:
        print(traceback.format_exc())
    finally:
        driver.quit()


def set_item(driver, key, value):
    driver.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", key, value)


if __name__ == '__main__':
    use_tokens = False
    main(use_tokens)
