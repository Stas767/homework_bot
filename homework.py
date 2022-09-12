import logging
import os
import sys
import time

import requests
import telegram

from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
streamhandler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'
)
streamhandler.setFormatter(formatter)
logger.addHandler(streamhandler)


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Отправлено сообщение в телеграм: {message}')
    except Exception:
        logger.error('Сбой при отправке сообщения в Telegram')
        sys.exit()


def get_api_answer(current_timestamp):
    """Делает запрос к API. Возвращает ответ в типе данных Python."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == 200:
        logger.info(f'Эндпоинт доступен. Статус: {response.status_code}')
        return response.json()
    logger.error(
        f'Эндпоинт недоступен! Статус ответа: {response.status_code}'
    )
    sys.exit()


def check_response(response):
    """Проверяет ответ API на корректность."""
    if type(response) is not dict:
        raise TypeError(
            'response имеет тип не являющийся словарем'
        )
    expected_keys = {"homeworks": [], "current_date": 1634074965}
    if expected_keys.keys() != response.keys():
        logger.error('В ответе API нет ожидаемых ключей')
        sys.exit()
    while response['homeworks'] == []:
        logger.info('Домашней работы для проверки нет')
        time.sleep(RETRY_TIME)
    list_homework = response['homeworks']
    return list_homework[0]


def parse_status(homework):
    """Извлекает статус конкретной работы."""
    for key in 'homework_name', 'status':
        if key not in homework:
            raise KeyError(f'Отсутсвует ключ: {key}')

    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status not in HOMEWORK_STATUSES:
        raise TypeError('Такого статуса проверки нет!')

    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    return False


def main():
    """Основная логика работы бота."""
    if check_tokens():
        logger.info('Старт бота! Переменные доступны.')
    else:
        logger.critical('Переменные не доступны!')
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:

        try:
            response = get_api_answer(current_timestamp)
            list_homework = check_response(response)
            message = parse_status(list_homework)
            send_message(bot, message)
            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            time.sleep(RETRY_TIME)
        else:
            pass


if __name__ == '__main__':
    main()
