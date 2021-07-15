import time
import atexit
import pickle
import requests
import bs4.element
from os import path
from Flat import Flat
from bs4 import BeautifulSoup
from random import randint, random

LAST_DISTRICT_NUMBER = 740
AVITO_URL = 'https://www.avito.ru'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' \
             'AppleWebKit/537.36 (KHTML, like Gecko) ' \
             'Chrome/91.0.4472.106 ' \
             'YaBrowser/21.6.0.616 ' \
             'Yowser/2.5 Safari/537.36'

flat_list = []
main_page_second_parse = []
offers_page_second_parse = []

start_district_number = 616
start_page_number = 1
start_id = 0

district_name = ''

headers = {'user-agent': USER_AGENT}


def parse_avito(first_id=0):
    global start_district_number, start_id

    start_id = first_id

    # Если программа запускается не в первый раз, то продолжить
    # с места остановки после прошлого запуска
    check_last_position()

    # range(start_district_number, LAST_DISTRICT_NUMBER + 1)
    # Перебор всех страниц с объявлениями рядом с различными станциями метро
    for i in range(616, 617):
        parse_district(i)
        start_district_number = i
        # Ожидание
        time.sleep(randint(-10, 10) + 300)

    # В случае ошибки доступа повторная попытка обработки данных страниц
    # (пока все не будут обработаны)
    while len(main_page_second_parse) != 0:
        parse_district(main_page_second_parse[0])
        main_page_second_parse.pop(0)
        # Ожидание
        time.sleep(randint(-10, 10) + 300)


def parse_district(district_number):
    global district_name

    url = f'https://www.avito.ru/moskva/kvartiry/prodam-ASgBAgICAUSSA8YQ'
    params = {'district': f'{district_number}', 'p': '1', 's': '1'}
    html = get_html(url, params)

    # Ожидание
    time.sleep(random() * 5 + 10)

    if html is not None:
        pages_amount = get_pages_amount(html)
        district_name = get_district_name(html)
        if pages_amount != 0:
            parse_district_pages(district_number, pages_amount, html)
        else:
            main_page_second_parse.append(district_number)
            # Ожидание (скорее всего вместо нужной страницы получена капча)
            time.sleep(randint(-10, 10) + 120)


def get_pages_amount(html):
    # Поиск div-обертки полосы прокрутки страниц
    pages_div = html.find('div', class_='pagination-root-2oCjZ')

    # В случае ошибки разбора страницы возврат 0
    if pages_div is None:
        print('Warning! Can\'t find pagination button!')
        return 0

    # Выделение номера последней страницы
    last_page = pages_div.find_all('span', class_='pagination-item-1WyVp')
    last_page_number = last_page[len(last_page) - 2].contents[0]

    return last_page_number


def get_district_name(html):
    # Поиск заголовка с названием района
    district_h = html.find('h1', class_='page-title-text-WxwN3 page-title-inline-2v2CW')

    # В случае ошибки разбора страницы возврат пустой строки
    if district_h is None:
        print('Warning! Can\'t find district name!')
        return ''

    # Выделение названия самого района
    district_phrase_split = district_h.text.split(' ')
    return district_phrase_split[len(district_phrase_split) - 1]


def parse_district_pages(district_number, pages_amount, first_page):
    global start_page_number

    if start_page_number == 1:
        parse_offers_page(district_number, 1, first_page)
    else:
        parse_offers_page(district_number, start_page_number)

    # range(start_page_number + 1, pages_amount + 1)
    for i in range(2, 2):
        parse_offers_page(district_number, i)
        start_page_number = i
        # Ожидание
        time.sleep(randint(-10, 10) + 60)

    while len(offers_page_second_parse) != 0:
        parse_offers_page(district_number, offers_page_second_parse[0])
        offers_page_second_parse[0].pop()
        # Ожидание
        time.sleep(randint(-10, 10) + 60)


def parse_offers_page(district_number, current_page, html=None):
    # Если это не первая страница или первая страница не передается,
    # тогда идет запрос, иначе обработка уже полученной страницы
    if current_page != 1 or html is None:
        url = f'https://www.avito.ru/moskva/kvartiry/prodam-ASgBAgICAUSSA8YQ'
        params = {'district': f'{district_number}', 'p': f'{current_page}', 's': '1'}
        html = get_html(url, params)

    # Если полученная страница не пуста, то поиск объявлений на ней,
    # иначе добавление страницы в очередь на повторный разбор
    if html is not None:
        offers = html.find_all('div', {'data-marker': 'item'})
        if len(offers) != 0:
            parse_offers_list(offers)
    else:
        print(f'Warning! Offers page is empty!')
        offers_page_second_parse.append(current_page)
        # Ожидание (скорее всего вместо нужной страницы получена капча)
        time.sleep(randint(-10, 10) + 60)


def parse_offers_list(offers):
    for offer in offers:
        # Поиск div-обертки названия-ссылки объявления
        offer_div = offer.find('div', class_='iva-item-titleStep-2bjuh')
        if offer_div is None:
            continue

        # Выделение a с ссылкой на объявление
        offer_a = offer_div.find('a')
        if offer_a is None:
            continue

        # Выделение ссылки
        offer_url_part = offer_a['href']
        parse_offer(AVITO_URL + offer_url_part)

        # Ожидание между обработкой объявлений
        time.sleep(randint(-5, 5) + 15)

    # Запись всех квартир со страницы в файл
    with open('avito.pickle', 'ab+') as buff:
        for f in flat_list:
            pickle.dump(f, buff)
        flat_list.clear()

    # Сохранение состояния
    save_last_position()


def parse_offer(offer_url):
    global start_id

    # Открытие страницы объявления
    html = get_html(offer_url, {})
    if html is None:
        print(f'Error! Offer url ({offer_url}) is incorrect!')
        return

    flat = Flat()

    # Заполнение объекта с информацией о квартире
    get_flat_info(html, flat)

    # Заполнение названия района в объекте квартиры
    flat.district = district_name

    # Заполнение индивидуального номера квартиры
    flat.id = start_id
    start_id += 1

    # Заполнение ссылки на квартиру
    flat.url = offer_url

    # Добавление квартиры в список квартир
    flat_list.append(flat)

    # Запись квартиры в буферный файл
    # with open('avito.json', 'a+', encoding='utf-8') as f:
    #    print(flat, file=f)

    # Вывод на экран (для отладки)
    print(flat)


def get_flat_info(html, flat):
    get_price(html, flat)
    get_address(html, flat)
    get_floor_rooms_square(html, flat)


def get_floor_rooms_square(html, flat):
    # Выделение списка с параметрами квартиры
    info_ul = html.find('ul', class_='item-params-list')

    # Перебор параметров с поиском в них информации об этаже,
    # количестве комнат и общей площади квартиры
    for parameter in info_ul.children:
        if type(parameter) != bs4.element.NavigableString:
            key = parameter.contents[1].text.strip()
            value = parameter.contents[2].strip()
            if key == 'Этаж:':
                flat.floor = int(value.split(' ')[0])
            if key == 'Количество комнат:':
                if value == 'студия' or value == 'своб. планировка':
                    value = '1'
                flat.rooms = value
            if key == 'Общая площадь:':
                flat.square = float(value.split('\xa0')[0])


def get_price(html, flat):
    # Поиск span с ценой
    price_span = html.find('span', class_='js-item-price')

    # Выделение стоимости квартиры из него
    flat.price = int(price_span.text.replace('\xa0', ''))


def get_address(html, flat):
    # Поиск span с адресом квартиры
    address = html.find('span', class_='item-address__string').text

    # Разбиение адреса на слова по запятой
    address_split = address.split(',')

    # Удаление города из адреса
    if address_split[0].strip() == "Москва":
        address_split.pop(0)

    # Заполнение улицы
    flat.street = address_split[0].strip()

    # Добавление номера дома, номера строения и т.д.
    for i in range(1, len(address_split)):
        flat.house += address_split[i].strip()
        if i != len(address_split) - 1:
            flat.house += ', '

    # Выделение ближайшей к квартире станции метро
    flat.metro = html.find('span', class_='item-address-georeferences-item__content').text.strip()


# Получение html-страницы
def get_html(url, params):
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        print(f'Error! HTTP status code: {response.status_code}')
        if response.status_code == 429:
            save_last_position()
            exit()
        return None
    return BeautifulSoup(response.text, 'lxml')


# Восстановление последнего состояния после прошлого запуска программы
def check_last_position():
    global start_district_number, start_page_number, start_id
    if path.exists('last_position.txt') and path.exists('avito.pickle'):
        with open('last_position.txt', 'r', encoding='utf-8') as lp:
            start_district_number = int(lp.readline().strip())
            start_page_number = int(lp.readline().strip())
            start_id = int(lp.readline().strip())
            # for _ in range(start_id):
            #    f = pickle.load(avito)
            #    print(f)


# Сохранение состояния в случае завершения работы программы
@atexit.register
def save_last_position():
    start_district_number_old = 0
    start_page_number_old = 0
    start_id_old = 0
    if path.exists('last_position.txt'):
        with open('last_position.txt', 'r', encoding='utf-8') as lp:
            start_district_number_old = int(lp.readline().strip())
            start_page_number_old = int(lp.readline().strip())
            start_id_old = int(lp.readline().strip())
    with open('last_position.txt', 'w+', encoding='utf-8') as lp:
        lp.write(f'{max(start_district_number_old, start_district_number)}\n'
                 f'{max(start_page_number_old, start_page_number)}\n'
                 f'{max(start_id_old, start_id)}')


if __name__ == '__main__':
    parse_avito()
