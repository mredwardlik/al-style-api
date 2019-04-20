import csv, os, requests, json, configparser, sys, ast, time, re, multiprocessing, urllib.request
from random import choice
'''------------------------------------------------'''
sys.getdefaultencoding()
config = configparser.ConfigParser()
dir_path = os.path.dirname(os.path.realpath(__file__))
conf_path = '{}{}'.format(dir_path, '\conf.ini')
params = {}
punctuation = r"""!][?'"#*\|/+.%@&`~}{:$<>^"""
'''------------------------------------------------'''
def getFileOption(section, option, mydefault):
	global config
	if (os.path.exists(conf_path) and os.path.isfile(conf_path)):
		config.read(conf_path)
		_typevalue = type(mydefault)
		if (config.has_option(section, option) and not(config.get(section, option) == '')):
			if (_typevalue == list) or (_typevalue == int) or (_typevalue == bool):
				return ast.literal_eval(config.get(section, option))
			else:
				return config.get(section, option)
		else:
			return mydefault
	else:
		f = open("conf.ini","w+")
		f.write("[Main]\nurl: https://order.al-style.kz/api/\naccess_token: YOUR_ACCESS_TOKEN\n\n[Columns]\ncolumns_element: ['article', 'name', 'full_name', 'category', 'sort', 'price1', 'price2', 'quantity', 'isnew', 'ishit', 'ispromo']\ncolumns_categories: ['id', 'name', 'left', 'right', 'level', 'elements']\ncolumns_element_info: ['article', 'name', 'full_name', 'category', 'sort', 'price1', 'price2', 'quantity', 'isnew', 'ishit', 'ispromo']\ncolumns_images: ['article', 'images']\n\n[Speed]\npool: 5\nsleep: 0\n\n[Check]\ncheck_result: False\n\n[Encoding]\nencode = UTF-8")
		f.close()
		input('Файл конфигураций был создан. Перезапустите программу!')
		sys.exit('Closing..')
'''------------------------------------------------'''
try:
	url = getFileOption('Main', 'url', 'https://order.al-style.kz/api/')
	access_token = getFileOption('Main', 'access_token', 'YOUR_ACCESS_TOKEN')
	columnsElements = getFileOption('Columns', 'columns_element', ['article', 'name', 'full_name', 'category', 'sort', 'price1', 'price2', 'quantity', 'isnew', 'ishit', 'ispromo'])
	columnsCategories = getFileOption('Columns', 'columns_categories', ['id', 'name', 'left', 'right', 'level', 'elements'])
	columnsElementInfo = getFileOption('Columns','columns_element_info', ['article', 'name', 'full_name', 'category', 'sort', 'price1', 'price2', 'quantity', 'isnew', 'ishit', 'ispromo'])
	columnsImages = getFileOption('Columns', 'columns_images', ['article', 'image'])
	pool_num = getFileOption('Speed', 'pool', 5)
	num_sleep = getFileOption('Speed', 'sleep', 0)
	check_result = getFileOption('Check', 'check_result', False)
	file_encode = getFileOption('Encoding', 'encode', 'UTF-8')
except SyntaxError:
	input('Ошибка синтаксиса в файле конфигураций conf.ini')
	sys.exit('Closing..')
except ValueError:
	input('Ошибка синтаксиса в файле конфигураций conf.ini')
	sys.exit('Closing..')
'''------------------------------------------------'''
def get_HTML(address):
	html = requests.get(address)
	if html.status_code == 200:
		return json.loads(html.text)
	else:
		return []

def get_address(method):
	global url, access_token, params
	address = '{}{}{}{}{}'.format(url, method, '?access-token=', access_token, '&')
	if bool(params):
		for key in params:
			address = '{}{}{}{}{}'.format(address, key, '=', params[key], '&')
	address = address[:-1]
	return address
'''------------------------------------------------'''
def ClearConsole(): 
    if os.name == 'nt': 
        _ = os.system('cls') 
    else: 
        _ = os.system('clear')

def getDate():
	global params
	params = {}
	method = 'date'
	return(get_HTML(get_address(method)))

def getCategories(id_from, id_to):
	global params
	answer = []; params = {}; a = None;
	method = 'categories'
	for id_n in range(id_from, id_to):
		params['id']= str(id_n)
		a = get_HTML(get_address(method))
		if not(len(a) == 0):
			answer.append(a[0])
		else:
			answer.append({'id': 'None', 'name': 'None', 'left': 'None', 'right': 'None', 'level': 'None', 'elements': 'None'})
	return answer

def getCategorie(id_n):
	global num_sleep, params
	time.sleep(num_sleep)
	answer = []; params = {}; a = None;
	method = 'categories'
	params['id']= str(id_n)
	a = get_HTML(get_address(method))
	if not(len(a) == 0):
		answer.append(a[0])
	else:
		answer.append({'id': 'None', 'name': 'None', 'left': 'None', 'right': 'None', 'level': 'None', 'elements': 'None'})
	return answer[0]
           
def getElements(category_from, category_to, limit=100, offset=0, additional_fields=''):
	global params
	params = {}; method = 'elements';
	params['category'] = str(",".join(tuple(str(category_from+x) for x in range(category_to-category_from))))
	params['limit'] = str(limit)
	params['offset'] = str(offset)
	if additional_fields != '':
		params['additional_fields'] = str(additional_fields)
	return (get_HTML(get_address(method)))

def getElementInfo(article, additional_fields=''):
	global params
	params = {}; method = 'element-info';
	if article == '':
		article = 0
	params['article'] = str(article)
	if additional_fields != '':
		params['additional_fields'] = str(additional_fields)
	return (get_HTML(get_address(method)))

def getImages(article, thumbs=1):
	global params
	answer = []; params = {}; method = 'images';
	params['article'] = str(article)
	params['thumbs'] = str(thumbs)
	imageList = get_HTML(get_address(method))
	for key,value in imageList.items():
		i = 1;
		for a in value:
			answer.append([f'{key}({i})', a])
			i += 1
	return answer

def getQuantity(article):
	global params
	params = {}; method = 'quantity';
	params['article'] = str(article)
	return (get_HTML(get_address(method)))

def getArticle(category_from, category_to, limit=100, offset=0, additional_fields=''):
	elements = getElements(category_from, category_to, limit, offset, additional_fields)
	if not(elements == []):
		strin = ''
		for i in elements:
			strin = '{},{}'.format(i['article'], strin)
		strin = strin[:-1]
		return strin
	else:
		return []
'''------------------------------------------------'''
def DownloadImages(data, FilePath=''):
	global dir_path, punctuation
	if FilePath == '':
		FilePath = 'images'
	FilePath = ''.join( c for c in FilePath if c not in punctuation)
	if FilePath == '':
		FilePath = 'images'
	if not(os.path.exists(FilePath) and os.path.isdir(FilePath)):
		os.makedirs(FilePath)
	for i in data:
		full_path = '{}/{}.jpg'.format(FilePath, i[0])
		urllib.request.urlretrieve(i[1], full_path)
	print('------------')
	print('Скачано!')

def insertInFile(data, columns=None, FileName='', spec=False):
	global file_encode, punctuation
	if FileName == '':
		FileName = 'test'
	FileName = ''.join( c for c in FileName if c not in punctuation)
	if FileName == '':
		FileName = 'test'
	with open(f'{FileName}.csv', mode='a', newline='', encoding=file_encode) as csv_file:
		writer = csv.writer(csv_file, delimiter=';')
		if not(columns==None) and (type(columns) is list) and (os.stat(f'{FileName}.csv').st_size == 0):
			writer.writerow(columns)
		if not(spec):
			for v in data:
				writer.writerow(list(v.values()))
		else:
			for v in data:
				writer.writerow(v)
	print('Записано!')
'''------------------------------------------------'''
def main():
	global pool_num, columnsCategories, columnsElements, columnsElementInfo, columnsImages, check_result;
	cyc = True;
	while (cyc):
		none_command = False; columns = None; FileName = ''; result = [];
		print('----1.0v----')
		command = ((str(input('Введите команду: \n1.[date] \n2.[categories] \n3.[elements] \n4.[element-info]\n5.[images]\n6.[quantity]\n7.[article]*\n8.[clear]*\n------------\n'))).lower()).replace(' ', '')
		print('------------')

		if command == '260199':
			print('Author: Lik Eduard.')
			continue

		elif command == 'date' or command == '1':
			result = getDate()

		elif command == 'categories' or command == '2':
			if (pool_num == True) or (pool_num == False):
				pool_num = 1
			p = multiprocessing.Pool(pool_num)
			f_id = int(input('От: '))
			t_id = int(input('До: '))
			result = (p.map(getCategorie, [x for x in range(f_id, t_id)]))
			columns = columnsCategories
			p.close()
			p.join()

		elif command == 'elements' or command == '3':
			category_from = int(input('Категория(От): '))
			category_to = int(input('Категория(До): '))
			limit = int(input('Лимит(100): '))
			offset = int(input('Отступ(0): '))
			additional_fields = (str(input('Дополнительные поля(null): '))).replace(' ', '')
			result = getElements(category_from, category_to, limit, offset, additional_fields)
			columns = columnsElements

		elif command == 'element-info' or command == '4':
			article = (str(input('Артикль: '))).replace(' ', '')
			additional_fields = (str(input('Дополнительные поля(null): '))).replace(' ', '')
			result = getElementInfo(article, additional_fields)
			columns = columnsElementInfo

		elif command == 'images' or command == '5':
			article = (str(input('Артикль: '))).replace(' ', '')
			thumbs = int(input('Миниатюра(0): '))
			result = getImages(article, thumbs)
			columns = columnsImages

		elif command == 'quantity' or command == '6':
			article = (str(input('Артикль: '))).replace(' ', '')
			result = getQuantity(article)
			print('------------')

		elif command == 'article' or command == '7':
			category_from = int(input('Категория(От): '))
			category_to = int(input('Категория(До): '))
			limit = int(input('Лимит(100): '))
			offset = int(input('Отступ(0): '))
			additional_fields = (str(input('Дополнительные поля(null): '))).replace(' ', '')
			result = getArticle(category_from, category_to, limit, offset, additional_fields)
			print('------------')

		elif command == 'clear' or command == '8':
			ClearConsole()

		else:
			print('Такой команды нет.')
			none_command = True

		if (none_command) or (command == 'clear' or command == '8'):
			continue

		if (command == 'date' or command == '1') or (command == 'quantity' or command == '6') or (command == 'article' or command == '7'):
			if not(result == []):
				print(result)
			else:
				print('Получено! Результат пуст!')
			continue

		if (check_result):
			print('------------')
			if not(result == []):
				print(result)
			else:
				print('Получено! Результат пуст!')
				continue
		else:
			print('------------')
			if not(result == []):
				print('Получено!')
			else:
				print('Получено! Результат пуст!')
				continue

		print('------------')
		writeFile = ((str(input('Записать в файл?\n1.Да\n------------\n'))).lower()).replace(' ', '')
		if (writeFile == 'да' or writeFile == '1'):
			print('------------')
			FileName = (str(input("Имя файла(test): "))).replace(' ', '_')
			print('------------')
			if command == 'images' or command == '5':
				insertInFile(result, columns, FileName, True)
			else:
				insertInFile(result, columns, FileName, False)
		else:
			print('------------')
			print('Файл не записан!')

		if (command == 'images' or command == '5'):
			print('------------')
			downloadImage = ((str(input('Скачать фотографии?\n1.Да\n------------\n'))).lower()).replace(' ', '')
			if (downloadImage == 'да' or downloadImage == '1'):
				print('------------')
				FilePath = (str(input("Имя директории(images): "))).replace(' ', '_')
				DownloadImages(result, FilePath)
			else:
				print('------------')
				print('Фотографии не скачаны!')
'''------------------------------------------------'''
if __name__ == '__main__':
	multiprocessing.freeze_support()
	while(1):
		try:
			main()
		except AttributeError:
			print('------------')
			print('Получено! Результат пуст!')
		except ValueError:
			print('------------')
			print('Ошибка ввода данных!')
		except LookupError:
			print('conf.ini:[Encoding] Ошибка кодировки при создании файла!')
		except OverflowError:
			print('------------')
			print('conf.ini:[Speed] Значение sleep слишком большое!')
'''------------------------------------------------'''