import os
from urllib.request import urlopen, urlretrieve, Request
from bs4 import BeautifulSoup
from decimal import Decimal
from datetime import timezone
from dateutil import parser
import json
import csv
import re


def get_soup(url):
    request = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urlopen(request)
    url_req = response.read()
    soup = BeautifulSoup(url_req, 'html.parser')
    response.close()
    return soup


def get_and_save_soup(url, save_loc):
    """Retrieve html and save if not already done. Get html and return soup"""
    if not os.path.exists(save_loc):
        print('No html saved...scraping')
        urlretrieve(url, save_loc)
    return BeautifulSoup(open(save_loc), 'html.parser')


def get_attribute_list(link_soup, attr):
    return list(map(lambda line: line[attr], link_soup))


def get_text_list(link_soup):
    return list(map(lambda line: line.text, link_soup))


def get_text_and_split_lists(link_soup, total_pro_fights):
    temp_list = list(map(lambda line: line.get_text('|'), link_soup))
    outcomes = []
    refs = []
    for i in range(total_pro_fights):
        temp = temp_list[i].split('|')
        outcomes.append(temp[0])
        refs.append(temp[1])
    return outcomes, refs


class Scrape:
    SHERDOG_ROOT_URL = "https://sherdog.com"

    def __init__(self, dk_event_url: str = '',
                 ufcstats_event_url: str = '',
                 bloodyelbow_url: str = '',
                 bloodyelbow_loc: str = '',
                 sherdog_event_url: str = '',
                 odds_url: str = '',
                 dk_csv_path: str = '',
                 card_id: str = ''):

        self.card_id = card_id
        # scrape UFCStats.com
        self.ufcstats_event_url = ufcstats_event_url
        self.ufcstats_event_loc = 'UFCStats_Dicts/' + card_id
        # scrape Sherdog.com
        self.sherdog_event_url = sherdog_event_url
        self.sherdog_event_loc = 'Sherdog_Dicts/' + card_id
        # scrape DK event
        self.dk_event_url = dk_event_url
        self.dk_csv_path = dk_csv_path
        self.salary_csv_loc = 'DraftKings/Salary_CSV/DKSalaries_' + card_id + '.csv'
        self.payout_csv_loc = 'DraftKings/Payout_CSV/DKPayout_' + card_id + '.csv'

        self.bloodyelbow_url = bloodyelbow_url
        self.bloodyelbow_loc = bloodyelbow_loc

        self.odds_url = odds_url

        self.scrape_ufcstats()
        self.scrape_sherdog()
        self.scrape_dk_event()

    def scrape_dk_event(self):
        """Scrape data from DK event."""
        if self.dk_event_url:
            contest_id = self.dk_event_url.split('/')[-1]
            save_loc = "DraftKings/Contest_HTML/contest_" + str(contest_id) + ".html"
            soup = get_and_save_soup(self.dk_event_url, save_loc)

            payout_text = soup.find(string=re.compile("window.mvcVars.contests"))
            temp = payout_text.split("window.mvcVars.contests = ")[1]
            str_dict_split = temp.split(";")
            payout_str_dict = str_dict_split[0]
            info_str_dict = str_dict_split[1].split('window.mvcVars.draftgroups = ')[1]
            payout_dicts_and_more = json.loads(payout_str_dict)
            info_dict = json.loads(info_str_dict)
            draftGroupId = info_dict['draftGroup']['draftGroupId']
            contestTypeId = info_dict['draftGroup']['contestType']['contestTypeId']
            print(contestTypeId, draftGroupId)

            date = info_dict['draftGroup']['minStartTime']
            print(date)
            payout_dicts = payout_dicts_and_more['contestDetail']['payoutSummary']
            entry_fee = payout_dicts_and_more['contestDetail']['entryFee']
            payout_list = [['minPosition', 'maxPosition', 'Cash', 'entryFee']]

            for d in payout_dicts:
                payout_list.append([d['minPosition'], d['maxPosition'],
                                    Decimal(re.sub(r'[^\d.]', '', d['tierPayoutDescriptions']['Cash']))])

            payout_list[1].append(entry_fee)
            print(payout_list)
            date_UTC = parser.isoparse(date)
            date_my_timezone = date_UTC.replace(tzinfo=timezone.utc).astimezone(tz=None)
            date_str = str(date_my_timezone.year) + str(date_my_timezone.month) + str(date_my_timezone.day)

            salary_csv_loc = 'DraftKings/Salary_CSV/DKSalaries_' + self.card_id + '.csv'
            payout_csv_loc = 'DraftKings/Payout_CSV/DKPayout_' + self.card_id + '.csv'

            if not os.path.exists(salary_csv_loc):
                print('Beginning file download..')
                url = 'https://www.draftkings.com/lineup/getavailableplayerscsv?contestTypeId=' + str(contestTypeId) + \
                      '&draftGroupId=' + str(draftGroupId)
                urlretrieve(url, salary_csv_loc)

            if not os.path.exists(payout_csv_loc):
                with open(payout_csv_loc, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerows(payout_list)

    def scrape_sherdog(self):
        """Scrape data from Sherdog.com, creating directories for storage."""
        if self.sherdog_event_url:
            if not os.path.exists(self.sherdog_event_loc):
                os.makedirs(self.sherdog_event_loc)
                fighter_links = self.get_sherdog_links()
                for link in fighter_links:
                    # 'javascript:void();' means fighter has not been replaced yet in matchup
                    if link != 'javascript:void();':
                        self.parse_sherdog_fighters(self.SHERDOG_ROOT_URL + link)
                    else:
                        print("Fighter matchup not assigned at this time...")
            else:
                print('Already Scraped Sherdog.com...')

    def get_sherdog_links(self):
        """Return links for fighters webpages for those fighters participating in the event."""
        # 'javascript:void();' means fighter has not been replaced yet in matchup
        soup = get_soup(self.sherdog_event_url)
        fighter_links_main = soup.select("div.fighter > a[href]")
        fighter_links_main = get_attribute_list(fighter_links_main, 'href')
        fighter_links_right = soup.select("td.text_right.col_first-fighter a")
        fighter_links = fighter_links_main + get_attribute_list(fighter_links_right, 'href')
        fighter_links_left = soup.select("td.text_left a")
        fighter_links = fighter_links + get_attribute_list(fighter_links_left, 'href')
        return fighter_links

    def parse_sherdog_fighters(self, link):
        """Parse the html for each fighter who will fight at the event. Save it to JSON file."""
        soup = get_soup(link)
        fighter_name = soup.select(".fn")[0].text
        fighter_wins = int(soup.select("div:nth-child(1) > span.card > span.counter")[0].text)
        fighter_losses = int(soup.select("div.bio_graph.loser > span.card > span.counter")[0].text)
        # Scraping cannot differentiate between pro and amateur records...need to remove amateur record
        total_pro_fights = fighter_wins + fighter_losses
        fight_outcome = get_text_list(soup.select("tr.even > td:nth-of-type(1) > span, "
                                                  "tr.odd > td:nth-of-type(1) > span"))
        fight_opponent = get_text_list(soup.select("tr.even > td:nth-of-type(2), "
                                                   "tr.odd > td:nth-of-type(2)"))
        fight_event = get_text_list(soup.select("tr.even > td:nth-of-type(3) > a, "
                                                "tr.odd > td:nth-of-type(3) > a"))
        fight_date = get_text_list(soup.select("tr.even > td:nth-of-type(3) > span, "
                                               "tr.odd > td:nth-of-type(3) > span"))
        fight_outcome_method, fight_ref = get_text_and_split_lists(
            soup.select("tr.even > td:nth-of-type(4), "
                        "tr.odd > td:nth-of-type(4)"), total_pro_fights)
        fight_round = get_text_list(soup.select("tr.even > td:nth-of-type(5), "
                                                "tr.odd > td:nth-of-type(5)"))
        fight_round_time = get_text_list(soup.select("tr.even > td:nth-of-type(6), "
                                                     "tr.odd > td:nth-of-type(6)"))

        fighter_history = {}

        for idx in range(total_pro_fights):
            # datetime.strptime(fight_date[idx], '%b / %d / %Y')
            fighter_history[idx] = \
                {'opponent': fight_opponent[idx],
                 'event': fight_event[idx],
                 'result': fight_outcome[idx],
                 'how': fight_outcome_method[idx],
                 'round': fight_round[idx],
                 'round_time': fight_round_time[idx],
                 'ref': fight_ref[idx],
                 'date': fight_date[idx]}

        fighter_dict = {fighter_name: fighter_history}
        filename = self.sherdog_event_loc + '/' + fighter_name + '.txt'
        json_object = json.dumps(fighter_dict, indent=4)
        with open(filename, 'w') as outfile:
            outfile.write(json_object)

    def scrape_ufcstats(self):
        """Scrape data from UFCStats.com, creating directories for storage."""
        if self.ufcstats_event_url:
            if not os.path.exists(self.ufcstats_event_loc):
                os.makedirs(self.ufcstats_event_loc)
            if not os.path.exists(self.ufcstats_event_loc + '/matchups'):
                os.makedirs(self.ufcstats_event_loc + '/matchups')
                matchup_links = self.get_ufcstats_links()
                for link in matchup_links:
                    self.parse_ufcstats_matchup(link)
            else:
                print('Already Scraped UFCStats.com...')

    def get_ufcstats_links(self):
        """Retrieve html, parse html for matchup links, and return links"""
        soup = get_soup(self.ufcstats_event_url)

        matchup_links = soup.select("p.b-fight-details__table-text > a[data-link]")
        matchup_links = get_attribute_list(matchup_links, 'data-link')
        return matchup_links

    def parse_ufcstats_matchup(self, matchup_link):
        """Parse matchup html for fighter info. Save as json file."""
        soup = get_soup(matchup_link)

        fighter_links = soup.select("th.b-fight-details__table-col > a[href]")
        fighter_names = soup.select("h3.b-fight-details__person-name > a")
        # print(fighter_names[0].text)
        # time.sleep(1)
        fighter_names = list(map(lambda x: x.text.strip(), fighter_names))
        # print(fighter_names)
        # time.sleep(1)
        fighter_stats = soup.select("tbody.b-fight-details__table-body > tr.b-fight-details__table-row-preview ")

        fighter_0_dict = {'Opponent': fighter_names[1], 'UFCStats_Link': fighter_links[0]['href']}
        fighter_1_dict = {'Opponent': fighter_names[0], 'UFCStats_Link': fighter_links[1]['href']}
        recent_record_fighter_0 = []
        recent_record_fighter_1 = []

        for resp in fighter_stats:
            stats = resp.select("td > p")
            stats = list(map(lambda x: x.text.strip(), stats))
            if len(stats) == 3:
                fighter_0_dict[stats[0]] = stats[1]
                fighter_1_dict[stats[0]] = stats[2]
            elif len(stats) == 2:
                if stats[0].strip():
                    recent_record_fighter_0.append(stats[0])
                if stats[1].strip():
                    recent_record_fighter_1.append(stats[1])
        # matchup has two fighters, so each entry is a list of two dicts
        fighter_0_dict['Recent Fights'] = recent_record_fighter_0
        fighter_1_dict['Recent Fights'] = recent_record_fighter_1
        vs = fighter_names[0] + ' vs. ' + fighter_names[1]

        filename = self.ufcstats_event_loc + '/matchups/' + vs + '.txt'

        json_object = json.dumps({vs: {fighter_names[0]: fighter_0_dict, fighter_names[1]: fighter_1_dict}},
                                 indent=4)
        # print(filename)
        with open(filename, 'w') as outfile:
            outfile.write(json_object)


if __name__ == '__main__':
    card = 'UFC_full_card_20201024'
    scrape_kwargs = {'ufcstats_event_url': 'http://ufcstats.com/event-details/c3c38c86f5ab9b5c',
                     'sherdog_event_url': 'https://www.sherdog.com/events/UFC-254-Nurmagomedov-vs-Gaethje-87041',
                     'dk_event_url': 'https://www.draftkings.com/draft/contest/93995953',
                     'card_id': 'UFC_full_card_20201024'}
    Scrape(**scrape_kwargs)
