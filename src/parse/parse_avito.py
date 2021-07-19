import time
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


def parse_avito():
    """
    Управляет обработкой всех объявлений о продаже недвижимости в Москве.

    :return:
    """
    global start_district_number, start_id, start_page_number

    # Если программа запускается не в первый раз, то продолжить
    # с места остановки после прошлого запуска
    load_last_position()

    # Перебор всех страниц с объявлениями рядом с различными станциями метро
    for i in range(start_district_number, LAST_DISTRICT_NUMBER + 1):
        start_district_number = i
        parse_district(i)
        start_page_number = 0
        save_last_position()
        start_page_number = 1
        # Ожидание
        if i != LAST_DISTRICT_NUMBER:
            time.sleep(randint(-10, 10) + 120)

    # В случае ошибки доступа повторная попытка обработки данных страниц
    # (пока все не будут обработаны)
    while len(main_page_second_parse) != 0:
        parse_district(main_page_second_parse[0])
        main_page_second_parse.pop(0)
        start_page_number = 1
        # Ожидание
        if len(main_page_second_parse) != 0:
            time.sleep(randint(-10, 10) + 180)


def parse_district(district_number):
    """
    Управляет обработкой страниц предложений для определенного района.

    :param district_number: номер района для обработки
    :type district_number: int
    :return:
    """
    global start_page_number

    url = f'https://www.avito.ru/moskva/kvartiry/prodam-ASgBAgICAUSSA8YQ'
    params = {'district': f'{district_number}', 'p': '1', 's': '1'}
    html = get_html(url, params)

    if html is not None:
        pages_amount = get_pages_amount(html)
        if pages_amount != 0:
            set_district_name(html)
            parse_district_pages(district_number, pages_amount, html)
        else:
            main_page_second_parse.append(district_number)
            # Ожидание (скорее всего вместо нужной страницы получена капча)
            time.sleep(randint(-10, 10) + 60)

    # Ожидание
    time.sleep(random() * 5 + 10)


def get_pages_amount(html):
    """
    Возвращает количество страниц предложений для данного района.

    :param html: первая страница предложений
    :type html: BeautifulSoup
    :return: количество страниц предложений
    :rtype: int
    """
    # Поиск div-обертки полосы прокрутки страниц
    pages_div = html.find('div', class_='pagination-root-2oCjZ')

    # В случае ошибки разбора страницы возврат 0
    if pages_div is None:
        print('Warning! Can\'t find pagination button!')
        return 0

    # Выделение номера последней страницы
    last_page = pages_div.find_all('span', class_='pagination-item-1WyVp')
    last_page_number = int(last_page[len(last_page) - 2].contents[0].strip())

    return last_page_number


def set_district_name(html):
    """
    Выделяет название района со страницы предложений и записывает его в district_name.

    Внимание! Изменяет значение глобальной переменной district_name.

    :param html: страница предложений
    :type html: BeautifulSoup
    :return:
    """
    global district_name

    # Поиск заголовка с названием района
    district_h = html.find('h1', class_='page-title-text-WxwN3 page-title-inline-2v2CW')

    # В случае ошибки разбора страницы возврат пустой строки
    if district_h is None:
        print('Warning! Can\'t find district name!')
        return ''

    # Выделение названия самого района
    district_phrase_split = district_h.text.split(' ')
    district_name = district_phrase_split[len(district_phrase_split) - 1]


def parse_district_pages(district_number, pages_amount, first_page):
    """
    Проходит по всем страницам предложений для одного района, вызывает parse_offers_page для каждой из них.

    :param district_number: номер района
    :type district_number: int
    :param pages_amount: количество страниц предложений для данного района
    :type pages_amount: int
    :param first_page: первая страница предложений, загруженная ранее
    :type first_page: BeautifulSoup
    :return:
    """
    global start_page_number

    if start_page_number == 1:
        parse_offers_page(district_number, 1, first_page)
    elif start_page_number <= pages_amount:
        parse_offers_page(district_number, start_page_number)

    for i in range(start_page_number + 1, pages_amount + 1):
        start_page_number = i
        parse_offers_page(district_number, i)
        # Ожидание
        if i != pages_amount:
            time.sleep(randint(-5, 5) + 30)

    while len(offers_page_second_parse) != 0:
        parse_offers_page(district_number, offers_page_second_parse[0])
        offers_page_second_parse[0].pop()
        # Ожидание
        if len(offers_page_second_parse) != 0:
            time.sleep(randint(-5, 5) + 30)


def parse_offers_page(district_number, current_page, html=None):
    """
    Выделяет со страницы предложений список объявлений и вызывает parse_offers_list для него.

    :param district_number: номер района
    :type district_number: int
    :param current_page: номер страницы предложений
    :type current_page: int
    :param html: страница для обработки, defaults to None
    :type html: BeautifulSoup, optional
    :return:
    """
    # Если это не первая страница или первая страница не передается,
    # тогда идет запрос, иначе обработка уже полученной страницы
    if current_page != 1 or html is None:
        url = f'https://www.avito.ru/moskva/kvartiry/prodam-ASgBAgICAUSSA8YQ'
        params = {'district': f'{district_number}', 'p': f'{current_page}', 's': '1'}
        html = get_html(url, params)

    # Если полученная страница не пуста, то поиск объявлений на ней,
    # иначе добавление страницы в очередь на повторный разбор
    if html is not None:
        delete_vip_blocks(html)
        offers = html.find_all('div', {'data-marker': 'item'})
        if len(offers) != 0:
            parse_offers_list(offers)
        else:
            print(f'Warning! Can\'t find offers on page!')
            offers_page_second_parse.append(current_page)
    else:
        print(f'Warning! Offers page is empty!')
        offers_page_second_parse.append(current_page)
        # Ожидание (скорее всего вместо нужной страницы получена капча)
        time.sleep(randint(-10, 10) + 60)


def delete_vip_blocks(html):
    """
    Находит и удаляет VIP-предложения со страницы предложений.

    :param html: страница предложений
    :type html: BeautifulSoup
    :return:
    """
    add_block = html.find('div', class_='items-vip-1naL1')

    if add_block is None:
        return

    add_block.decompose()


def parse_offers_list(offers):
    """
    Обрабатывает список объявлений на одной странице предложений и вызывает сохранение состояния после обработки.

    :param offers: список объявлений с одной страницы
    :type offers: list
    :return:
    """

    # Для подсчета количества обработанных квартир
    first_id = start_id

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
        time.sleep(randint(-5, 5) + 10)

    print(f'Обработано(-а) {start_id - first_id} квартир(-а/-ы).')

    # Сохранение состояния
    save_last_position()
    save_flats_list()


def parse_offer(offer_url):
    """
    Парсит страницу объявления и добавляет объект flat в список квартир.

    :param offer_url: ссылка на страницу объявления
    :type offer_url: str
    :return:
    """
    global start_id

    # Открытие страницы объявления
    html = get_html(offer_url, {})
    if html is None:
        print(f'Error! Offer url ({offer_url}) is incorrect!')
        return

    flat = Flat()

    # Заполнение объекта с информацией о квартире
    if set_flat_info(html, flat):

        # Заполнение названия района в объекте квартиры
        flat.district = district_name

        # Заполнение индивидуального номера квартиры
        flat.id = start_id
        start_id += 1

        # Заполнение ссылки на квартиру
        flat.url = offer_url

        # Добавление квартиры в список квартир
        flat_list.append(flat)

        # Вывод на экран (для отладки)
        print(flat)
    else:
        print(f'Error! Offer ({offer_url}) has not enough info!')


def set_flat_info(html, flat):
    """
    Определяет и устанавливает в объекте flat информацию о квартире по странице объявления html.

    :param html: страница объявления
    :type html: BeautifulSoup
    :param flat: объект квартры
    :type flat: Flat
    :return: удачно ли выполнены поиск и выделение информации о квартире
    :rtype: bool
    """
    return set_price(html, flat) and set_address(html, flat) and set_floor_rooms_square(html, flat)


def set_floor_rooms_square(html, flat):
    """
    Определяет и устанавливает в объекте flat этаж, количество комнат и площадь квартиры по странице объявления html.

    :param html: страница объявления
    :type html: BeautifulSoup
    :param flat: объект квартры
    :type flat: Flat
    :return: удачно ли выполнены поиск и выделение этажа, комнатности и квадратуры
    :rtype: bool
    """
    # Выделение списка с параметрами квартиры
    info_ul = html.find('ul', class_='item-params-list')

    if info_ul is None:
        return False

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

    return True


def set_price(html, flat):
    """
    Определяет и устанавливает в объекте flat цену квартиры по странице объявления html.

    :param html: страница объявления
    :type html: BeautifulSoup
    :param flat: объект квартры
    :type flat: Flat
    :return: удачно ли выполнены поиск и выделение цены
    :rtype: bool
    """
    # Поиск span с ценой
    price_span = html.find('span', class_='js-item-price')

    if price_span is None:
        return False

    # Выделение стоимости квартиры из него
    flat.price = int(price_span.text.replace('\xa0', ''))

    return True


def set_address(html, flat):
    """
    Определяет и устанавливает в объекте flat адрес квартиры по странице объявления html.

    :param html: страница объявления
    :type html: BeautifulSoup
    :param flat: объект квартры
    :type flat: Flat
    :return: удачно ли выполнены поиск и выделение адреса
    :rtype: bool
    """
    # Поиск span с адресом квартиры
    address = html.find('span', class_='item-address__string').text

    if address is None:
        return False

    # Разбиение адреса на слова по запятой
    address_split = address.split(',')

    # Удаление города из адреса
    if address_split[0].strip() == "Москва":
        address_split.pop(0)

    if len(address_split) == 0:
        return False

    # Заполнение улицы
    flat.street = address_split[0].strip()

    # Добавление номера дома, номера строения и т.д.
    for i in range(1, len(address_split)):
        flat.house += address_split[i].strip()
        if i != len(address_split) - 1:
            flat.house += ', '

    # Выделение ближайшей к квартире станции метро
    flat.metro = html.find('span', class_='item-address-georeferences-item__content').text.strip()

    return True


# Получение html-страницы
def get_html(url, params):
    """
    Возвращает страницу, находяющуся по переданному адресу.

    :param url: адрес страницы запроса
    :type url: str
    :param params: параметры запроса
    :type params: dict
    :return: объект BeautifulSoup страницы
    :rtype: BeautifulSoup|None
    """
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        print(f'Error! HTTP status code: {response.status_code}')
        if response.status_code == 429:
            exit()
        return None
    return BeautifulSoup(response.text, 'lxml')


# Восстановление последнего состояния после прошлого запуска программы
def load_last_position():
    """
    Загружает состояние парсера, если оно было сохранено ранее.

    Внимание! Изменяет значения глобальных переменных
    start_district_number, start_page_number и start_id.

    :return:
    """
    global start_district_number, start_page_number, start_id
    if path.exists('last_position.txt') and path.exists('avito.pickle'):
        with open('last_position.txt', 'r', encoding='utf-8') as lp:
            start_district_number = int(lp.readline().strip())
            start_page_number = int(lp.readline().strip()) + 1
            start_id = int(lp.readline().strip())
            print(f'Last position loaded.\n'
                  f'District: {start_district_number - 615};\n'
                  f'Page: {start_page_number};\n'
                  f'Last ID: {start_id}.')
    else:
        print(f'Nothing to load.')


# Сохранение состояния
def save_last_position():
    """
    Сохраняет состояние парсера на данный момент.

    Предусматривает случай первого и повторного обхода районов.
    Сохраняет номера района, страницы предложений внутри района
    и последний id квартиры.

    :return:
    """
    start_district_number_old = 0
    start_page_number_old = 0
    start_id_old = 0
    if path.exists('last_position.txt'):
        with open('last_position.txt', 'r', encoding='utf-8') as lp:
            start_district_number_old = int(lp.readline().strip())
            start_page_number_old = int(lp.readline().strip())
            start_id_old = int(lp.readline().strip())

    print(f'\nLast position saved.')

    with open('last_position.txt', 'w+', encoding='utf-8') as lp:
        if start_district_number_old > start_district_number:
            lp.write(f'{start_district_number_old}\n'
                     f'{start_page_number_old}\n')

            print(f'District: {start_district_number_old};\n'
                  f'Page: {start_page_number_old};')

        else:
            lp.write(f'{start_district_number}\n'
                     f'{start_page_number}\n')

            print(f'District: {start_district_number};\n'
                  f'Page: {start_page_number};')

        lp.write(f'{max(start_id_old, start_id)}')

        print(f'Last ID: {max(start_id_old, start_id)}.\n')


def save_flats_list():
    """
    Дополняет список квартир теми, что были разобраны на данный момент.

    :return:
    """
    with open('avito.pickle', 'ab+') as buff:
        for f in flat_list:
            pickle.dump(f, buff)
        flat_list.clear()

    print('Flats list saved.')


if __name__ == '__main__':
    parse_avito()
