import aiohttp
import logging
from bs4 import BeautifulSoup
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class HackathonScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.previous_hackathons = set()

    async def fetch_page(self, url):
        """Fetches page content from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.error(f"Failed to fetch {url}: Status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            return None

    async def scrape_hackerearth(self):
        """Scrapes hackathons from HackerEarth"""
        url = "https://www.hackerearth.com/challenges/hackathon/"
        content = await self.fetch_page(url)
        if not content:
            return []

        hackathons = []
        try:
            soup = BeautifulSoup(content, 'html.parser')
            challenge_cards = soup.find_all('div', class_='challenge-card-modern')

            for card in challenge_cards:
                title = card.find('span', class_='challenge-name')
                date = card.find('div', class_='challenge-date')
                link = card.find('a', class_='challenge-card-wrapper')

                if title and date and link:
                    hackathons.append({
                        'title': title.text.strip(),
                        'date': date.text.strip(),
                        'link': f"https://www.hackerearth.com{link['href']}",
                        'platform': 'HackerEarth',
                        'id': f"he_{title.text.strip()}_{date.text.strip()}"
                    })
        except Exception as e:
            logger.error(f"Error parsing HackerEarth: {str(e)}")

        return hackathons

    async def scrape_codechef(self):
        """Scrapes hackathons from CodeChef"""
        url = "https://www.codechef.com/contests"
        content = await self.fetch_page(url)
        if not content:
            return []

        hackathons = []
        try:
            soup = BeautifulSoup(content, 'html.parser')
            contest_tables = soup.find_all('table', class_='dataTable')

            for table in contest_tables:
                rows = table.find_all('tr')[1:]  # Skip header row
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        title = cols[1].text.strip()
                        date = cols[2].text.strip()
                        hackathons.append({
                            'title': title,
                            'date': date,
                            'link': f"https://www.codechef.com{cols[1].find('a')['href']}",
                            'platform': 'CodeChef',
                            'id': f"cc_{title}_{date}"
                        })
        except Exception as e:
            logger.error(f"Error parsing CodeChef: {str(e)}")

        return hackathons

    async def scrape_leetcode(self):
        """Scrapes contests from LeetCode"""
        url = "https://leetcode.com/contest/"
        content = await self.fetch_page(url)
        if not content:
            return []

        hackathons = []
        try:
            soup = BeautifulSoup(content, 'html.parser')
            contest_cards = soup.find_all('div', class_='contest-card')

            for card in contest_cards:
                title = card.find('div', class_='contest-title')
                date = card.find('div', class_='contest-time')
                link = card.find('a')

                if title and date and link:
                    hackathons.append({
                        'title': title.text.strip(),
                        'date': date.text.strip(),
                        'link': f"https://leetcode.com{link['href']}",
                        'platform': 'LeetCode',
                        'id': f"lc_{title.text.strip()}_{date.text.strip()}"
                    })
        except Exception as e:
            logger.error(f"Error parsing LeetCode: {str(e)}")

        return hackathons

    async def get_all_hackathons(self):
        """Fetches hackathons from all sources and detects new ones"""
        tasks = [
            self.scrape_hackerearth(),
            self.scrape_codechef(),
            self.scrape_leetcode()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_hackathons = []
        for result in results:
            if isinstance(result, list):
                all_hackathons.extend(result)
            else:
                logger.error(f"Error fetching hackathons: {str(result)}")

        # Detect new hackathons
        current_hackathon_ids = {h['id'] for h in all_hackathons}
        new_hackathons = [h for h in all_hackathons if h['id'] not in self.previous_hackathons]
        self.previous_hackathons = current_hackathon_ids

        return all_hackathons, new_hackathons