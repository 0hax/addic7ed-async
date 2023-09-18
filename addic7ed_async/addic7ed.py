from bs4 import BeautifulSoup
from collections import namedtuple
from typing import List
import os
import pprint
import re

# TODO this somewhere else.
# async lru
# https://github.com/aio-libs/async-lru
# https://github.com/requests-cache/aiohttp-client-cache
# https://github.com/pydanny/cached-property
# https://github.com/youknowone/ring/
# 
# loguru for logging



Addic7edShow = namedtuple('Addic7edShow', ['name', 'id'])
Addic7edEpisode = namedtuple('Addic7edEpisode', ['number', 'name'])
Addic7edSubtitle = namedtuple('Addic7edSubtitle', ['version',
                                                   'language',
                                                   'download'])

ADDIC7ED_URL = 'https://www.addic7ed.com/'


class Addic7ed(object):
    def __init__(self, session):
        self._url = ADDIC7ED_URL
        self._session = session

    async def get_main_page(self):
        response = await self._session.get(self._url)
        return await response.text()

    async def get_all_possible_languages(self):
        """
        Get all available subtitle languages used on addict7ed.
        It's not 100% correct as it's retrieving the list of languages of the
        website itself. But it doesn't look too far from the available
        languages for subtitles.
        """
        data = await self.get_main_page()
        soup = BeautifulSoup(data, 'html5lib')
        langs = soup.find(id='comboLang')
        return [lang.string for lang in langs]

    async def get_all_shows(self) -> List[Addic7edShow]:
        """
        Get all available TVShows for which there is subtitles.
        """
        data = await self.get_main_page()
        soup = BeautifulSoup(data, 'html5lib')
        qsShow = soup.find(id='qsShow')
        options = qsShow.find_all('option')
        shows = [Addic7edShow(option.string, option['value'])
                 for option in options]
        return shows

    async def get_show_from_name(self, name) -> Addic7edShow:
        """
        Given a show name, return an Addic7edShow namedtuple corresponding to
        the matching show.
        """
        shows = await self.get_all_shows()
        # First pass with an exact match minus special characters.
        for show in shows:
            # Remove any weird character like ' in "The Handmaid's Tale"
            if re.match(f'^{name}$',
                        re.sub(r'[^A-Za-z0-9 ]', '', show.name),
                        re.IGNORECASE):
                return show

        # Second pass with a loose match minus special characters.
        for show in shows:
            # Remove any weird character like ' in "The Handmaid's Tale"
            if re.match(f'.*{name}.*',
                        re.sub(r'[^A-Za-z0-9 ]', '', show.name),
                        re.IGNORECASE):
                return show

        # TODO retry without cache?
        # flush_cache('addict7ed.html')
        raise Exception(f'Show {name} not found')


    # TODO add show_id in cache request
    async def get_seasons_page(self, show):
        season_url = os.path.join(self._url,
                                  f'ajax_getSeasons.php?showID={show.id}')
        response = await self._session.get(season_url)
        return await response.text()

    async def list_seasons(self, show):
        # <select id="qsiSeason" name="qsiSeason" onchange="seasonChange(6265,-1);">
        #  <option value="0">
        #   Season
        #  </option>
        #  <option>
        #   1
        #  </option>
        #  <option>
        #   2
        #  </option>
        # </select>

        data = await self.get_seasons_page(show)
        season = BeautifulSoup(data, 'html5lib')
        qsiSeason = season.find(id='qsiSeason')
        options = qsiSeason.find_all('option')
        seasons = [int(option.string) for option in options
                   if option.string != 'Season']
        return seasons

    # TODO add season and show id in cache request
    async def get_episodes_page(self, show, season):
        episode_url = \
            os.path.join(
                self._url,
                f'ajax_getEpisodes.php?showID={show.id}&season={season}'
            )
        response = await self._session.get(episode_url)
        return await response.text()

    async def list_episodes(self, show, season):
        data = await self.get_episodes_page(show, season)
        episodes = BeautifulSoup(data, 'html5lib')
        qsiEp = episodes.find(id='qsiEp')
        options = qsiEp.find_all('option')

        # Strip unwanted stuff:
        # <option value="0">[Select an episode]</option> <--
        # <option value="6265-5x1">1. Morning</option>
        # <option value="6265-5x2">2. Ballet</option>
        # <option value="6265-5x3">3. Border</option>
        # <option value="6265-5x4">4. Dear Offred</option>
        # <option value="6265-5x5">5. Fairytale</option>
        # <option value="6265-5x6">6. Together</option>

        raw_episodes = [option.string for option in options
                        if option['value'] != '0']

        # Make it a tuple with episode number and title.
        episodes = list()
        for episode in raw_episodes:
            match = re.match(r'([0-9]+)\. (.*)', episode.string)
            if not match:
                raise Exception("Invalid format")
            episodes.append(
                Addic7edEpisode(
                    int(match.group(1)),
                    match.group(2))
            )
        return episodes

    async def find_episode(self, show, season, number):
        episodes = await self.list_episodes(show, season)
        for episode in episodes:
            if episode.number == number:
                return episode
        raise Exception("No subtitles available for this episode.")

    async def get_subtitles_page(self, show, season, episode):
        # Replace ' ' by '_'
        subtitles_url = os.path.join(
            self._url, 'serie',
            show.name.replace(' ', '_'),
            str(season),
            str(episode.number),
            episode.name.replace(' ', '_')
        )
        response = await self._session.get(subtitles_url)
        return await response.text()

    async def list_subtitles(self, show: Addic7edShow,
                             season: int,
                             episode: Addic7edEpisode):
        data = await self.get_subtitles_page(show, season, episode)
        soup = BeautifulSoup(data, 'html5lib')
        sub_cells = soup.find_all(
            'table',
            {'width': '100%', 'border': '0', 'align': 'center', 'class': 'tabel95'}
        )
        subtitles = list()
        for sub_cell in sub_cells:
            version_row = sub_cell.find('td', {'class': 'NewsTitle'})
            version = re.match('Version (.*?),', version_row.text).group(1)

            language_row = sub_cell.find('td', {'class': 'language'})
            language = language_row.text.strip()

            dl = sub_cell.find('a', {'class': 'buttonDownload'})
            dl_link = dl['href']
            subtitles.append(Addic7edSubtitle(version, language, dl_link))
        return subtitles

    # TODO Cache this obviously
    async def get_subtitle(self, subtitle):
        download_url = os.path.join(self._url, subtitle.download.lstrip('/'))
        headers = {'Referer': download_url,
                   'User-Agent': 'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.1.3)'}
        response = await self._session.get(download_url, headers=headers)
        return await response.read()

    async def download_subtitle(self, show_name: str, season_number: int,
                                episode_number: int, language='French',
                                prefered_version=None):
        show = await self.get_show_from_name(show_name)
        episode = await self.find_episode(show, season_number, episode_number)
        subtitles = await self.list_subtitles(show, season_number, episode)
        matching_subtitle = None
        for subtitle in subtitles:
            if subtitle.language != language:
                continue
            if prefered_version and \
               prefered_version not in subtitle.version:
                continue
            matching_subtitle = subtitle
            break
        if not matching_subtitle:
            print("""Can't find matching subtitle for {} S{:02d}E{:02d}
Availables:\n
{}
""".format(show_name, season_number, episode_number, pprint.pformat(subtitles))
            )
            return None
        return await self.get_subtitle(subtitle)
