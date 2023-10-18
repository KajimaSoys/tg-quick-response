import traceback

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

options = webdriver.ChromeOptions()
options.add_argument(
    '--user-agent=""Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5810.200 Safari/537.36""')


def main(use_tokens):
    with open("message.txt", "r", encoding="utf-8") as file:
        welcome_message = file.read()

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 3)
    try:
        if use_tokens:
            try:
                with open("files/tokens.json", "r") as f:
                    tokens = json.load(f)

                driver.get("https://web.telegram.org/")

                for key, value in tokens.items():
                    set_item(driver, key, value)

                driver.refresh()
            except FileNotFoundError:
                print('File not found, please authorize in telegram, you have 60 seconds')
                driver.get("https://web.telegram.org/")
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
            driver.get("https://web.telegram.org/")
            time.sleep(60)
        time.sleep(300)
    except Exception as E:
        print(f"An error occurred:\n{E}")
    finally:
        driver.quit()


def set_item(driver, key, value):
    driver.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", key, value)


if __name__ == '__main__':
    use_tokens = True
    main(use_tokens)
