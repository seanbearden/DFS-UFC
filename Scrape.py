import os
from urllib.request import urlopen, urlretrieve, Request
from bs4 import BeautifulSoup
from decimal import Decimal
import json
import csv
import re


def get_soup(url):
    """Get html from url and return as BeautifulSoup"""
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
                 sherdog_event_url: str = '',
                 dk_odds_url: str = '',
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
        self.salary_csv_loc = 'DraftKings/Salary_CSV/DKSalaries_' + card_id + '.csv'
        self.payout_csv_loc = 'DraftKings/Payout_CSV/DKPayout_' + card_id + '.csv'
        self.odds_json_loc = 'DraftKings/Odds_JSON/DKOdds_' + card_id + '.json'
        self.salary_csv_loc = 'DraftKings/Salary_CSV/DKSalaries_' + card_id + '.csv'
        self.payout_csv_loc = 'DraftKings/Payout_CSV/DKPayout_' + card_id + '.csv'

        self.bloodyelbow_url = bloodyelbow_url

        self.dk_odds_url = dk_odds_url

        self.ufcstats_fighter_links = {}

        self.scrape_ufcstats()
        self.scrape_sherdog()
        self.scrape_dk_event()
        self.scrape_dk_odds()

    def scrape_dk_odds(self):
        """Get odds from DK and remove vig. SAve to JSON file."""
        # Odds currently contains fighter odds from multiple events.
        if self.dk_odds_url and not os.path.exists(self.odds_json_loc):
            print("Scraping DK Odds")
            soup = get_soup(self.dk_odds_url)
            span_list = soup.find_all('span')
            names = []
            odds = []
            names_odds = {}
            prev_line = ''
            for ul in span_list:  # accessing each individual ul tag in ulList
                if ul.text:
                    if ul.text[0] == '-' or ul.text[0] == '+':
                        names.append(prev_line)
                        odds.append(ul.text)
                prev_line = ul.text
            # Remove the vig.
            for i in range(len(names) // 2):
                f1 = names[2 * i]
                f2 = names[2 * i + 1]
                o1 = int(odds[2 * i])
                o2 = int(odds[2 * i + 1])
                # print(f1,f2,o1,o2)
                if o1 < 0 and o2 < 0:
                    o1 = -o1 / (-o1 + 100)
                    o2 = -o2 / (-o2 + 100)
                elif o1 < 0:
                    o1 = -o1 / (-o1 + 100)
                    o2 = 100 / (o2 + 100)
                else:
                    o1 = 100 / (o1 + 100)
                    o2 = -o2 / (-o2 + 100)
                total = o1 + o2
                o1 = o1 / total
                o2 = o2 / total
                names_odds[f1] = o1
                names_odds[f2] = o2

            json_stats = json.dumps(names_odds, indent=4)
            with open(self.odds_json_loc, 'w') as outfile:
                outfile.write(json_stats)
        else:
            print("Already Scraped DK odds...")

    def scrape_dk_event(self):
        """Scrape data from DK event. Get payout structure and salary info."""
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

            # date = info_dict['draftGroup']['minStartTime']
            payout_dicts = payout_dicts_and_more['contestDetail']['payoutSummary']
            entry_fee = payout_dicts_and_more['contestDetail']['entryFee']
            payout_list = [['minPosition', 'maxPosition', 'Cash', 'entryFee']]

            for d in payout_dicts:
                payout_list.append([d['minPosition'], d['maxPosition'],
                                    Decimal(re.sub(r'[^\d.]', '', d['tierPayoutDescriptions']['Cash']))])

            payout_list[1].append(entry_fee)
            # date_UTC = parser.isoparse(date)
            # date_my_timezone = date_UTC.replace(tzinfo=timezone.utc).astimezone(tz=None)
            # date_str = str(date_my_timezone.year) + str(date_my_timezone.month) + str(date_my_timezone.day)

            # need option to force download in case fighters drop out of event.
            if not os.path.exists(self.salary_csv_loc):
                print('Beginning DK Salary CSV download..')
                url = 'https://www.draftkings.com/lineup/getavailableplayerscsv?contestTypeId=' + str(contestTypeId) + \
                      '&draftGroupId=' + str(draftGroupId)
                urlretrieve(url, self.salary_csv_loc)
                self.fix_dk_salary_csv()

            if not os.path.exists(self.payout_csv_loc):
                with open(self.payout_csv_loc, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerows(payout_list)

    def fix_dk_salary_csv(self):
        """Fix column labels in DK salary csv."""
        with open(self.salary_csv_loc, 'r') as f:
            my_csv_text = f.read()
        find_str = 'Position,Name \+ ID,Name,ID,Roster Position,Salary,Game Info,TeamAbbrev,AvgPointsPerGame'
        replace_str = 'Position,NameID,Name,ID,RosterPosition,Salary,GameInfo,TeamAbbrev,AvgPointsPerGame'
        # substitute
        new_csv_str = re.sub(find_str, replace_str, my_csv_text)

        # open new file and save
        # new_csv_path = './my_new_csv.csv'  # or whatever path and name you want
        with open(self.salary_csv_loc, 'w') as f:
            f.write(new_csv_str)

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
        filename = self.sherdog_event_loc + '/' + fighter_name + '.json'
        json_object = json.dumps(fighter_dict, indent=4)
        with open(filename, 'w') as outfile:
            outfile.write(json_object)

    def combine_ufcstats(self):
        dir_name = self.ufcstats_event_loc + '/matchups'
        # Load and combine dictionaries
        # self.fights_on_ticket = int(len(os.listdir(dir_name)))
        for filename in os.listdir(dir_name):
            with open(os.path.join(dir_name, filename)) as f:  # open in readonly mode
                matchup_dict = json.load(f)
                matchup_dict = self.clean_ufcstats(matchup_dict)
                self.UFCStats_dict.update(matchup_dict)

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
                if not os.path.exists(self.ufcstats_event_loc + '/fighters'):
                    os.makedirs(self.ufcstats_event_loc + '/fighters')
                for f in self.ufcstats_fighter_links.keys():
                    self.get_fighter_history_ufcstats(self.ufcstats_fighter_links[f])
            else:
                print('Already Scraped UFCStats.com...')

    def get_fighter_history_ufcstats(self, url):
        soup = get_soup(url)
        stats = {}

        name = str(soup.h2.span.string).strip()
        stats["Name"] = name
        nick = str(soup.p.string).strip()
        stats["Nick"] = nick

        ulList = soup.find_all('ul')

        for ul in ulList:  # accessing each individual ul tag in ulList
            for li in ul.find_all('li'):  # iterating through each li tag in each ul tag
                if li.i and (str(
                        li.i.string).strip() != ""):  # Since and short circuits wont run into error of prevLi.i not
                    # existing and trying to get a string from it.
                    statName = str(li.i.string).strip()
                    statNum = str(li.contents[2]).strip()  # If there is a statName inside the i tag there is always
                    # an associated statNum outside the i tag but in the li tag
                    stats[statName] = statNum

        tableList = soup.find_all('table')
        pList = tableList[0].find_all('p')
        info = []
        for p in pList:  # accessing each individual ul tag in ulList
            info.append(p.text.strip())
        stats['UFC_Record'] = {}
        while info:
            temp_info = info.pop(0)
            if temp_info == 'next':
                f1 = info.pop(0)
                f2 = info.pop(0)
                info.pop(0)
                event = info.pop(0)
                date = info.pop(0)
                stats['Upcoming'] = {'Date': date, 'Event': event, 'Opponent': f2, 'Outcome': temp_info}
            else:
                f1 = info.pop(0)
                f2 = info.pop(0)
                f1_str = info.pop(0)
                f2_str = info.pop(0)
                f1_td = info.pop(0)
                f2_td = info.pop(0)
                f1_sub = info.pop(0)
                f2_sub = info.pop(0)
                f1_pass = info.pop(0)
                f2_pass = info.pop(0)

                event = info.pop(0)
                date = info.pop(0)
                method = info.pop(0)
                method_detail = info.pop(0)
                max_round = info.pop(0)
                time = info.pop(0)

                stats['UFC_Record'][date] = {'Event': event, 'Opponent': f2,
                                             'STR_Opp': f2_str, 'STR': f1_str,
                                             'TD_Opp': f2_td, 'TD': f1_td,
                                             'SUB_Opp': f2_sub, 'SUB': f1_sub,
                                             'PASS_Opp': f2_pass, 'PASS': f1_pass,
                                             'Outcome': temp_info, 'Method': method, 'Method_Detail': method_detail,
                                             'Round': max_round, 'Time': time}

        # create json object from python dictionary
        filename = self.ufcstats_event_loc + '/fighters/' + name + '.json'

        json_stats = json.dumps(stats, indent=4)
        with open(filename, 'w') as outfile:
            outfile.write(json_stats)

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

        self.ufcstats_fighter_links[fighter_names[0]] = fighter_links[0]['href']
        self.ufcstats_fighter_links[fighter_names[1]] = fighter_links[1]['href']

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

        filename = self.ufcstats_event_loc + '/matchups/' + vs + '.json'

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
                     'dk_odds_url': 'https://sportsbook.draftkings.com/leagues/mma/2162?category=fight-lines&subcategory=moneyline',
                     'card_id': 'UFC_full_card_20201024'}
    Scrape(**scrape_kwargs)
