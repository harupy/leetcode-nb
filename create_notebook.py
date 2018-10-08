import re
import csv
import pandas as pd
import sys
import os
import nbformat
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options


driver = webdriver.Chrome()


def print_error(e):
	exc_type, exc_obj, exc_tb = sys.exc_info()
	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	print(exc_type, fname, exc_tb.tb_lineno, e)


def create_new_notebook(fpath):
	nb = nbformat.read('base.ipynb', 4)
	with open(fpath, 'w') as f:
		nbformat.write(nb, f)


def update_notebook(fpath, problem, sol):
	nb = nbformat.read(fpath, 4)
	nb['cells'].insert(-1, nbformat.v4.new_markdown_cell(problem))
	nb['cells'].insert(-1, nbformat.v4.new_code_cell(sol + '\n\nhide_toggle("Toggle the solution")'))
	nb['cells'].insert(-1, nbformat.v4.new_code_cell('# Your solution'))
	with open(fpath, 'w') as f:
		nbformat.write(nb, f)


def scrape_problems():
	top_url = 'https://leetcode.com'
	driver.get(top_url + '/problemset/all')
	WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'select.form-control')))
	Select(driver.find_element_by_css_selector('select.form-control')).select_by_visible_text('all')
	soup = BeautifulSoup(driver.page_source, 'lxml')
	table = soup.find('div', {'class': 'question-list-table'})
	header = [x.text.lower() for x in table.select('thead th')[1:-1]] + ['problem_url', 'locked']
	title_idx = header.index('title')
	solution_idx = header.index('solution')

	rows = []
	with open('prolems.csv', 'w', newline='') as f:
		writer = csv.writer(f, delimiter=',')
		writer.writerow(header)
		for tr in table.select('tbody tr')[:-1]:
			row = []
			for i, td in enumerate(tr.find_all('td')[1:-1]):
				if i == solution_idx:
					if td.find_all('a'):
						row.append(top_url + td.find('a')['href'])
					else:
						row.append('')
				else:
					row.append(td.text.strip())
					if i == title_idx:
						url = top_url + td.find('a')['href']
						if not url.endswith('/description'): url += '/description'
						locked = len(td.find_all('i', {'class': 'fa-lock'}))
			row.extend([url, locked])
			rows.append(row)
			writer.writerow(row)
	return pd.DataFrame(rows, columns=header)


def scrape_description(url):
	driver.get(url)
	try:
		class_regex = r'^question-description'
		WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CLASS_NAME, 'question-content')))
	except Exception as e:
		class_regex = r'content-wrapper'
	soup = BeautifulSoup(driver.page_source, 'lxml')
	desc = soup.find('div', {'class': re.compile(class_regex)}).find('div').decode_contents()
	return desc


def format_description(desc):
	return desc.replace('<pre>', '<div class="example">').replace('</pre>', '</div>').replace('\n</div>', '</div>')


def scrape_solution(title='two-sum'):
	url = 'https://raw.githubusercontent.com/kamyu104/LeetCode/master/Python/{}.py'.format(title)
	try:
		r = requests.get(url)
		return r.text if r.status_code == 200 else ''
	except requests.exceptions.RequestException as e:
		print_error(e)
		return ''


def format_solution(sol):
	regex = r'(?m)^# *((?!(Time:|Space:)).)*$\n?'
	return re.sub(regex, '', sol).replace('from __future__ import print_function\n', '')


def main():
	difficulty = 'Easy'
	fpath = 'leetcode_{}.ipynb'.format(difficulty.lower())
	create_new_notebook(fpath)
	try:
		df = scrape_problems()
		df = df[df['difficulty'] == difficulty]
		cols = ['title', 'problem_url', 'difficulty', 'locked']
		for index, (title, problem_url, difficulty, locked) in df[cols].iterrows():
			if index + 1 > 100: break
			if locked: continue
			desc = scrape_description(problem_url)
			desc = format_description(desc)
			sol = scrape_solution(title.lower().replace(' ', '-'))
			sol = format_solution(sol)
			problem = '\n'.join([
				'---\n'
				'## [{}. {} ({})]({})'.format(index + 1, title, difficulty.capitalize(), problem_url),
				desc,
			])
			update_notebook(fpath, problem, sol)
			print(index, title, problem_url)
	except Exception as e:
		print_error(e)
	finally:
		driver.quit()


if __name__ == '__main__':
	main()
