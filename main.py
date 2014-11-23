#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function


from bs4 import BeautifulSoup
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from couchpotato.core.media.movie.providers.base import MovieProvider

import re
import time
import traceback

import requests


log = CPLog(__name__)


class T411(TorrentProvider, MovieProvider):

    urls = {
        'test' : 'https://www.t411.me/',
        'login' : 'http://www.t411.me/users/login/',
        'login_check': 'https://www.t411.me/',
        'detail' : 'https://www.t411.me/torrents/?id={}',
        'search' : 'http://www.t411.me/torrents/search/?search={title}&cat={category}&subcat={subcategory}&term%5B17%5D%5B%5D={language}&submit=Recherche&order=seeders&type=desc',
        'download' : 'https://www.t411.me/torrents/download/?id={}',
    }

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    categories = {
        'movies': 210,
    }
    subcategories = {
        'film': 631
    }
    languages = {
        'french': 541
    }

    session = requests.Session()


    def _searchOnTitle(self, title, movie, quality, results):
        log.debug('Searching T411 for {}'.format(title))
        url = self.urls['search'].format(**{
            'title': title,
            'category': self.categories['movies'],
            'subcategory': self.subcategories['film'],
            'language': self.languages['french']
        })
        data = self.session.get(url).text

        log.debug('Received data from T411')
        if data:
            log.debug('Data is valid from T411')

            html = BeautifulSoup(data)
            try:
                content = html.find('div', attrs={'class', 'content'})
                result_table = content.find('table')
                if not result_table:
                    log.debug('No results from T411')
                    return

                torrents = result_table.find_all('tr')
                for torrent in torrents[1:]:
                    try:
                        columns = torrent.find_all('td')
                        release_name = columns[1].find('a')['title']
                        link = columns[2].find('a')['href']
                        match = re.search('(?P<torrent_id>[0-9]+)', link)
                        torrent_id = match.groupdict()['torrent_id'] if match else None
                        results.append({
                            'id': torrent_id,
                            'name': release_name,
                            'seeders': columns[7].text,
                            'leechers': columns[8].text,
                            'url': self.urls['download'].format(torrent_id),
                            'detail_url': 'http:{}'.format(columns[1].find('a')['href']),
                            'size': self.parseSize(columns[5].text)
                        })
                    except:
                        continue
            except:
                log.error('Failed to parse T411: %s' % (traceback.format_exc()))

    def loginDownload(self, url = '', nzb_id = ''):
        try:
            response = self.session.get(url)
            return response.content
        except:
            log.error('Failed getting release from %s: %s', (self.getName(), traceback.format_exc()))
        return 'try_next'

    def login(self):
        # Check if we are still logged in every hour
        now = time.time()
        if self.last_login_check and self.last_login_check < (now - 3600):
            try:
                output = self.session.get(self.urls['login_check'])
                if self.loginCheckSuccess(output):
                    self.last_login_check = now
                    return True
            except: pass
            self.last_login_check = None

        if self.last_login_check:
            return True

        try:
            response = self.session.post(self.urls['login'], data=self.getLoginParams())
            output = response.text
            if self.loginSuccess(output):
                self.last_login_check = now
                return True
            error = 'unknown'
        except:
            error = traceback.format_exc()

        self.last_login_check = None
        log.error('Failed to login %s: %s', (self.getName(), error))
        return False

    def getLoginParams(self):
        log.debug('Getting login params for T411')
        return {
            'login': self.conf('username'),
            'password': self.conf('password')
        }

    def loginSuccess(self, output):
        verdict = '/users/logout/' in output.lower()
        log.debug('Checking login success for T411: {}'.format(verdict))
        return verdict

    loginCheckSuccess = loginSuccess
