import os
import re
import threading
from time import sleep
from urllib.parse import parse_qs

import click
import requests
from bs4 import BeautifulSoup

lock = threading.Lock()

def get(*args, **kwargs):
    sleep(2)
    kwargs['timeout'] = 1
    return requests.get(*args, **kwargs)

def req(query):
    base_url = 'https://www.google.com/search'
    params = {'q': query}
    r = get(base_url, params=params)
    return r.text

def next_req(url):
    base_url = 'https://www.google.com'
    r = get(base_url + url)
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
    for i in range(0, depth):
        curr_links = extract_pdf_links_from_page(soup)
        for l in curr_links:
            try:
                r = get(l)
                if r.ok:
                    name = 'aux.pdf'
                    if 'Content-Disposition' in r.headers:
                        name = r.headers['Content-Disposition']
                        name = name[name.rfind('filename=')+10:len(name)-1]
                    else:
                        name = l[l.rfind('/')+1:]
                    if not name.endswith('.pdf'):
                        name += '.pdf'
                    path = './out/' + name
                    count = 1
                    if os.path.exists(path):
                        continue
                    lock.acquire()
                    with open(path, 'wb') as f:
                        f.write(r.content)
                    lock.release()
            except Exception:
                pass
        next_page = soup.find('a', attrs={'aria-label': 'Próxima página'})
        if next_page:
            try:
                html_doc = next_req(next_page['href'])
                soup = BeautifulSoup(html_doc, 'html.parser')
            except Exception:
                break
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
    threads = []
    for f_term in fts:
        for s_term in sts:
            # do this in a different thread
            x = threading.Thread(target=search, args=(f_term, s_term, depth, outpath))
            threads.append(x)
    for t in threads:
        t.start()
    for t in threads:
        t.join()

if __name__ == '__main__':
    main()