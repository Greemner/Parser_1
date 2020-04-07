import re
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import time
from selenium.webdriver.common.keys import Keys
import numpy as np
import matplotlib.pyplot as plt


URL = 'http://astrakhan.zakazrf.ru/DeliveryRequest'
LINKS = {}
PRODUCTS_DICT = {}
HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
                         ' Chrome/80.0.3987.149 Safari/537.36', 'accept': '*/*'}

LIMIT = 1000
ITEMS_FOUND = 0
ITEMS_LIST = []


def value_error_check(string):
    flag = 0
    value = None
    while flag == 0:
        try:
            value = int(input(string))
        except ValueError:
            print('Введите корректное число')
        else:
            flag = 1
    return value


# Поиск минимальной цены и даты для позиции
def find_price_date(link, item):
    global ITEMS_FOUND, PRODUCTS_DICT
    html_page = requests.get(link, headers=HEADERS)
    html_text = html_page.text
    soup = BeautifulSoup(html_text, "html.parser")
    table = soup.find('table', class_='grid-table-view')
    table_str = str(table).split('</tr>')
    price_list = []
    dates = []
    table_dates = table.find_all('img', class_='row_error_icon')

    for row in range(1, len(table_str) - 1):
        # Поиск дат
        date = table_dates[row-1].find_parent().get_text()
        dates.append(date.split(' ')[0])

        # Поиск цен
        participant = list(table_str[row].split('</td>'))
        price_list.append(float(participant[2].split('>')[1].replace(',', '.')))

    PRODUCTS_DICT[item]['Price'].append(round(min(price_list), 2))
    PRODUCTS_DICT[item]['Date'].append(dates[0][:5])
    ITEMS_FOUND += 1
    for product in list(PRODUCTS_DICT.keys()):
        print('  ', product, ': ', len(PRODUCTS_DICT[product]['Price']), sep='', end=' ')
    print()
    return 0


# Создание словаря со всеми записями
def create_product_dict():
    global PRODUCTS_DICT
    for item in range(len(ITEMS_LIST)):
        PRODUCTS_DICT[ITEMS_LIST[item]] = dict(Price=[], Date=[], Link=[])
    return 0


# Поиск ссылок для каждой позиции
def product_link(table):
    global PRODUCTS_DICT
    product_table = str(table.find_all('tr', style="background-color: #6ab898;")).split('</tr>')
    item_list = {}
    base_link = 'http://astrakhan.zakazrf.ru/DeliveryRequest/'
    href = r'id/\d{6}'

    for row in range(len(product_table)):
        for item in ITEMS_LIST:
            if item in product_table[row]:
                item_id = re.findall(href, product_table[row])[0]
                link = base_link + item_id
                PRODUCTS_DICT[item]['Link'].append(link)
                item_list[link] = item
                break

    return item_list


# Парсинг
def parse(num=1000000, stop_link=''):
    global ITEMS_FOUND
    driver = webdriver.Chrome()
    driver.get(URL)
    create_product_dict()

    # Выбрать завершенные
    button_bar = driver.find_element_by_class_name("tab-pages-bar")
    buttons = button_bar.find_elements_by_tag_name("button")
    completed = buttons[5]
    completed.click()
    time.sleep(1)

    # Парсинг страниц
    page = 1
    while ITEMS_FOUND < num and page < LIMIT:
        page_input = driver.find_element_by_xpath('/html/body/div[1]/div[3]/div/form/div/input[11]')
        for i in range(4):
            page_input.send_keys(Keys.BACK_SPACE)
        page_input.send_keys(str(page))
        page_input.send_keys(Keys.ENTER)
        time.sleep(1.5)
        completed_page_html = driver.page_source
        soup = BeautifulSoup(completed_page_html, "html.parser")
        completed_table = soup.find('table', class_='reporttable')
        links_on_page = product_link(completed_table)  # Ссылки на нужный товар
        links = list(links_on_page.keys())
        items = list(links_on_page.values())
        for i in range(len(links_on_page)):
            if links[i].split('/')[-1] != stop_link.split('/')[-1].split('\n')[0]:
                find_price_date(links[i], items[i])  # Поиск цены и даты для каждой ссылки
            else:
                driver.quit()
                return 1

        page += 1

    driver.quit()
    return 0


# Создание txt файлов
def import_to_txt(item):
    global PRODUCTS_DICT
    file_name = item + '.txt'
    data_txt = open(file_name, 'w')
    PRODUCTS_DICT[item]['Price'].reverse()
    PRODUCTS_DICT[item]['Date'].reverse()
    PRODUCTS_DICT[item]['Link'].reverse()
    price = PRODUCTS_DICT[item]['Price']
    date = PRODUCTS_DICT[item]['Date']
    links = PRODUCTS_DICT[item]['Link']
    for i in range(len(PRODUCTS_DICT[item]['Price'])):
        data_txt.write("{:s}\t{:s}\t{:s}\n".format(str(price[i]), date[i], links[i]))
    data_txt.close()
    return 0


# Обновление данных по позициям
def update():
    flag_open = 0
    file_name = None
    data_txt = None
    while flag_open == 0:
        try:
            file_name = input('Имя файла (Продукт.txt)\t')
            print('--------------------------------------------------------------------------')
            data_txt = open(file_name, 'r+')
        except IOError:
            print('Введите корректное имя файла')
        else:
            flag_open = 1
    item = file_name.split('.')[0]
    ITEMS_LIST.append(item)
    lines = data_txt.readlines()
    last_link = lines[-1].split('\t')[2]
    parse(stop_link=last_link)
    price = PRODUCTS_DICT[item]['Price']
    date = PRODUCTS_DICT[item]['Date']
    links = PRODUCTS_DICT[item]['Link']
    price.reverse()
    date.reverse()
    links.reverse()
    new_len = len(price)
    if new_len != 0:
        print('Найдено', new_len, 'новых записей по данному товару')
        print('--------------------------------------------------------------------------')
        for i in range(new_len):
            data_txt.write("{:s}\t{:s}\t{:s}\n".format(str(price[i]), date[i], links[i]))
    else:
        print('Никаких новых записей')
        print('--------------------------------------------------------------------------')

    data_txt.close()
    return 0


# Загрузка данных для одного продукта
def download():
    global ITEMS_LIST
    item = input('Введите продукт\t')
    ITEMS_LIST.append(item)
    req = 'Введите количество элементов для поиска\t'
    number = value_error_check(req)
    print('--------------------------------------------------------------------------')
    parse(num=number)
    import_to_txt(item)
    print('Файл создан!')
    plt.plot(PRODUCTS_DICT[item]['Date'], PRODUCTS_DICT[item]['Price'])
    plt.show()
    return 0


# Создание графика из файла
def draw():
    flag_open = 0
    file_name = None
    data_txt = None
    price = []
    date = []
    while flag_open == 0:
        try:
            file_name = input('Имя файла (Продукт.txt)\t')
            data_txt = open(file_name, 'r')
        except IOError:
            print('Введите корректное имя файла')
        else:
            flag_open = 1

    req = 'По скольким последним позициям построить график? (0 - всем записям в файле)\t'
    elements = value_error_check(req)
    print('--------------------------------------------------------------------------')
    lines = data_txt.readlines()
    el_lim = None
    if elements == 0:
        el_lim = 0
    else:
        el_lim = len(lines) - elements
    for line in range(el_lim, len(lines)):
        line_list = lines[line].split('\t')
        price.append(float(line_list[0]))
        date.append(line_list[1])
    plt.plot(date, price)
    plt.show()
    return 0


# Загрузка данных для нескольких продуктов
def group():
    global ITEMS_LIST, LIMIT
    req1 = 'Сколько продуктов Вы хотите найти?\t'
    items_len = value_error_check(req1)
    for i in range(items_len):
        print('\t', i + 1, 'продукт', end=' ')
        ITEMS_LIST.append(input('- '))

    req2 = 'Сколько страниц просмотреть?\t'
    LIMIT = value_error_check(req2)
    print('--------------------------------------------------------------------------')
    parse()
    for item in ITEMS_LIST:
        import_to_txt(item)
        plt.plot(PRODUCTS_DICT[item]['Date'], PRODUCTS_DICT[item]['Price'])
        plt.gcf().canvas.set_window_title(item)
        plt.show()
    print('Файлы созданы!')
    return 0


def main():
    flag_mode = 0
    mode = None
    print('--------------------------------------------------------------------------')
    print('Выберите режим\n\t1 - основной режим\n\t2 - обновить данные\n\t3 - график из файла'
          '\n\t4 - группа продуктов')
    req = 'Режим\t'
    mode = value_error_check(req)
    if mode == 1:
        download()
    elif mode == 2:
        update()
    elif mode == 3:
        draw()
    else:
        group()
    return 0


print('\n\n')
main()
answer = 2
while answer == 2:
    print('Закончить или продолжить?\n\t1 - закончить и выключить программу\n\t2 - продолжить сеанс')
    req = 'Выбор\t'
    answer = value_error_check(req)
    if answer == 2:
        PRODUCTS_DICT.clear()
        main()
