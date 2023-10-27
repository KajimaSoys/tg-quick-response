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

            with open("files/tokens.json", "w") as f:
                json.dump(tokens, f)
    else:
        driver.get("https://web.telegram.org/a/")
        time.sleep(60)


def extract_chats(driver):
    chat_list = set()
    unchanged_count = 0

    driver.execute_script("console.log('Вызван метод сбор списка чатов');")
    driver.execute_script("console.log('Поиск scrollable_container - div.chat-list');")

    scrollable_container = driver.find_element(By.CSS_SELECTOR, 'div.chat-list')
    driver.execute_script("arguments[0].scrollBy(0, -20000);", scrollable_container)

    previous_chats = []

    driver.execute_script("console.log('scrollable_container найден');")
    driver.execute_script("console.log('Запущен сбор списка чатов');")

    while True:
        chat_list_element = driver.find_elements(By.CSS_SELECTOR, 'div.chat-list div')[1]
        current_chats = chat_list_element.find_elements(By.CSS_SELECTOR,
                                                        'div.ListItem.Chat.chat-item-clickable.private')

        if current_chats == previous_chats:
            unchanged_count += 1
            driver.execute_script("console.log(`Текущий список чатов идентичен предыдущему. unchanged_count = ${arguments[0]}`);", unchanged_count)
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
            first_visible_chat = current_chats[0]
            shift = int(first_visible_chat.get_attribute('style').replace('top: ', '').replace('px;', ''))
            driver.execute_script(
                "console.log('Сбор чатов закончен, возврат к началу диалогов');")
            back_top(driver, scrollable_container, shift)
            break
        previous_chats = current_chats

        driver.execute_script("arguments[0].scrollBy(0, 2000);", scrollable_container)
        time.sleep(1)

    logger.info(f'Parsed chat list: {chat_list}')
    logger.info(f'Count of parsed chats: {len(chat_list)}')
    driver.execute_script("console.log('Сбор чатов окончен');")
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


def scan_new_chats(driver, chat_list, messages):
    previous_chats = []
    driver.execute_script("console.log('Вызван метод поиска новых чатов');")

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
                    logger.info("new_chat!")
                    driver.execute_script(f"console.log('Обнаружен новый чат: {chat_id}');")
                    driver.execute_script("console.log('Отправка сообщения');")
                    send_message(driver, chat, messages)
                    chat_list.add(chat_id)
                    to_saved_messages(driver)
                else:
                    logger.info(f'chat with {chat_id} already in chat_list')

        previous_chats = current_chats
        time.sleep(0.5)


def send_message(driver, chat, messages):
    chat.click()
    time.sleep(0.5)
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

    time.sleep(0.2)
    send_button.click()
    driver.execute_script("console.log('Сообщение отправлено');")

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
        logger.exception(E)


def main(use_tokens):
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

        logger.info('Extracting chats process started')
        chat_list = extract_chats(driver)
        logger.info('Successful extracting')

        # chat_list = {6347319297, 7756580, 94230536, 1805340682, 988323861, 1321066523, 764010526, 519227426, 227924018,
        #              219076670, 43860031, 663953474, 1462114374, 1185216597, 1343701078, 6292815965, 1694763124,
        #              270796923, 540219515, 480180347, 330209410, 93372553, 278339724, 1945114776, 889710746, 146946204,
        #              426987701, 6060050625, 340238545, 554303698, 6080561376, 405903591, 2032367848, 737487087,
        #              136210706, 1296935190, 1646954785, 1499636014, 956234031, 5319426367, 521642305, 1165658446,
        #              166035794, 1048756563, 120215903, 592314723, 1179978083, 1137191268, 890503535, 5474576753,
        #              5641808243, 1908126078, 6063135108, 1301221766, 527581578, 460693903, 169642392, 608111005,
        #              1529708960, 322040227, 345555366, 1093212591, 253465013, 862472633, 766185919, 5478668734,
        #              1354387907, 437109196, 29612493, 1412622808, 976294365, 1286961638, 5213104624, 1495560690,
        #              364591612, 6200945150, 552817165, 357384719, 697319963, 2146333212, 1360790056, 1508495914,
        #              709286445, 622365233, 979147314, 5254949431, 209859129, 100203067, 1802183238, 780726859,
        #              301027918, 1702732380, 997810796, 377651836, 457636477, 851540611, 1082247813, 317813382,
        #              756339335, 1294725778, 2039884436, 276333210, 1462756005, 1159289518, 863269554, 1062326967,
        #              436585153, 5606503115, 1062333136, 6297651923, 64355031, 713732828, 1938600670, 980634335,
        #              872383202, 118377187, 123833070, 1728189169, 127226626, 6682309378, 947030789, 454611720,
        #              431291144, 343196428, 44331798, 1293527834, 969157403, 975139613, 840289063, 777000, 218966827,
        #              746701617, 870173494, 892412734, 409158474, 365110093, 1140362062, 630426447, 84804429, 1296962394,
        #              886412126, 956865383, 2043337578, 933823343, 177662837, 96217975, 2057436034, 1049985923,
        #              1018020740, 1820853122, 2120020871, 845601686, 5637675929, 804778910, 911690657, 1010486185,
        #              515085230, 272606127, 429000, 924144590, 6324237269, 387574746, 5111016414, 285400032, 5225667554,
        #              903273452, 295943148, 122997754, 1606620155, 5956854784, 1250255874, 740004884, 1419828244,
        #              1936559133, 953799712, 515081261, 297104432, 1069222963, 1305697334, 1544995898, 1582879805,
        #              381764678, 586185799, 956068948, 1495688290, 1056683107, 887301218, 803669093, 1181537387,
        #              779381885, 1309205635, 74376339, 1007058073, 1631638686, 260850852, 1080796329, 407076013,
        #              808791216, 617909425, 1279671474, 492534968, 2113381568, 1135113408, 948616385, 283927755,
        #              452420823, 262671582, 893936863, 1089219811, 414977260, 1471886575, 287667440, 805526774,
        #              436204792, 613780729, 1778433289, 767079691, 1186270476, 404270356, 788880662, 119588126,
        #              1027200287, 1976861987, 477226275, 594101550, 247743791, 403273026, 1946527042, 643134786,
        #              416159046, 5365579082, 817356109, 6116539729, 388433235, 929361247, 992920935, 2114614635,
        #              843562369, 1823448466, 1633914258, 1798389140, 6107256222, 882742704, 5315438005, 1931261368,
        #              1033921975, 277153210, 398255543, 5731954117, 234634696, 1989189068, 6038736331, 860118478,
        #              1059313102, 317711825, 486972885, 369124823, 275799522, 107965924, 532147687, 794652151,
        #              2094071296, 721823234, 1548232202, 1094053394, 5866135057, 1050320403, 500057623, 855447066,
        #              730066459, 5142101530, 1275788834, 94889508, 1098974757, 5863974446, 440243761, 51590712,
        #              5363226166, 815668795, 675591747, 248583760, 564932185, 977536601, 187119208, 1567454829,
        #              2130656887, 1203158660, 1289703049, 1043897994, 1271266957, 465747598, 6119341719, 1924570777,
        #              294948507, 206788257, 5453246113, 5200465578, 322016942, 5736179384, 233625279, 487435972,
        #              359067337, 741344970, 468481747, 1340628696, 507784923, 872570593, 914632419, 717276900, 755465957,
        #              985992939, 6452369139, 1326417657, 1637619452, 856121098, 690536205, 753463057, 1475491603,
        #              6071715603, 5854170911, 926400294, 409298736, 787064627, 198807352, 1630705481, 877068107,
        #              5843066707, 5660763995, 682534755, 252637046, 875272062, 514568078, 1096845207, 654626713,
        #              330276767, 285183907, 52504489, 258709420, 330862514, 404979644, 1571977151, 1287309259,
        #              1344135117, 424863695, 535373776, 678774743, 395681770, 846358510, 863621114}

        logger.info('Scanning process started')
        scan_new_chats(driver, chat_list, messages)

    except Exception as E:
        logger.exception(E)
    finally:
        driver.quit()


def set_item(driver, key, value):
    driver.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", key, value)


if __name__ == '__main__':
    use_tokens = False
    main(use_tokens)
