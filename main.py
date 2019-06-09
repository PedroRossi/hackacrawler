import os
import re
import threading
from urllib.parse import parse_qs

import click
import requests
from bs4 import BeautifulSoup

lock = threading.Lock()

def req(query):
    base_url = 'https://www.google.com/search'
    params = {'q': query}
    r = requests.get(base_url, params=params)
    return r.text

def next_req(url):
    base_url = 'https://www.google.com'
    r = requests.get(base_url + url)
    return r.text

def extract_pdf_links_from_page(soup):
    return [
        parse_qs(x['href'][5:])['q'][0] for x in soup.find_all('a')
        if x.find('div', string=re.compile('\[PDF\]'))
    ]

def search(f_term, s_term, depth, outpath):
    q = f_term + '+' + s_term
    html_doc = req(q)
    soup = BeautifulSoup(html_doc, 'html.parser') 
    for i in range(depth):
        curr_links = extract_pdf_links_from_page(soup)
        curr_links = list(set(curr_links))
        for l in curr_links:
            r = requests.get(l)
            if r.ok:
                name = 'aux.pdf'
                if 'Content-Disposition' in r.headers:
                    name = r.headers['Content-Disposition']
                    name = name[name.rfind('filename=')+10:len(name)-1]
                else:
                    name = l[l.rfind('/')+1:]
                if not name.endswith('.pdf'):
                    name += '.pdf'
                print(name)
                path = './out/' + name
                count = 1
                lock.acquire()
                while os.path.exists(path):
                    path = './out/' + str(count) + '_' + name
                with open(path, 'wb') as f:
                    f.write(r.content)
                lock.release()
        next_page = soup.find('a', attrs={'aria-label': 'Próxima página'})
        if next_page:
            html_doc = next_req(next_page['href'])
            soup = BeautifulSoup(html_doc, 'html.parser')
        else:
            break

@click.command()
@click.option('--first-terms', '-st', default='hackathon', help='Lista de primeiros termos da busca divididos por , (Ex.: hackathon,hackaday)')
@click.option('--second-terms', '-ft', default='edital,regulamento', help='Lista de primeiros termos da busca divididos por , (Ex.: edital,regulamento)')
@click.option('--depth', '-dt', default=20, help='Profundidade da busca em número de pags do Google, 20 por padrão')
@click.option('--outpath', '-o', default='./out/', help='Caminho para baixar os pdfs da busca')
def main(first_terms, second_terms, depth, outpath):
    fts = first_terms.split(',')
    sts = second_terms.split(',')
    for f_term in fts:
        for s_term in sts:
            # do this in a different thread
            print('searching with ', f_term, ' and ', s_term)
            search(f_term, s_term, depth, outpath)

if __name__ == '__main__':
    main()