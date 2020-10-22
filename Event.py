import os
import re

import pandas as pd
import numpy as np

from datetime import datetime, date
from itertools import combinations, product


from os import listdir
from os.path import isfile, join

import json
import csv
import urllib.request as urllib2
from bs4 import BeautifulSoup


class Event:
    DK_MAX_SALARY = 50000
    FIGHTERS_TO_PICK = 6
    FIGHTERS_OUT = []
    NO_PICKING_BOTH = True
    MIN_POINTS = 510
    RECURSIVENESS = 1  # NUMBER OF FIGHTS TO PICK ALL POSSIBLE COMBOS
    NEWCOMER_POINTS = 25
    PICK_EVERY_WAY = 2

    def __init__(self, event_webpage_dk: str = '',
                 event_webpage_ufcstats: str = '',
                 bloodyelbow_webpage: str = '',
                 bloodyelbow_loc: str = '',
                 sherdog_webpage: str = '',
                 sherdog_loc: str = '',
                 odds_webpage: str = '',
                 UFCStats_loc: str = '',
                 dk_csv_path: str = '',
                 override_stats: dict = {},
                 forced_matchups: list = []):

        self.event_webpage_dk = event_webpage_dk
        self.event_webpage_ufcstats = event_webpage_ufcstats
        self.UFCStats_loc = UFCStats_loc
        self.UFCStats_dict = {}
        self.dk_csv_path = dk_csv_path
        self.bloodyelbow_webpage = bloodyelbow_webpage
        self.bloodyelbow_loc = bloodyelbow_loc
        self.staffpicks_dict = {}
        self.override_stats = override_stats
        self.fighter_names = []
        self.fights_on_ticket = 0
        self.forced_matchups = forced_matchups
        self.sherdog_webpage = sherdog_webpage
        self.sherdog_loc = sherdog_loc
        self.odds_webpage = odds_webpage
        # self.event_name = event_name
        # self.location = location                # find info on weather, altitude, commission, other factors...
        self.dk_salaries = self.load_dk_csv()  # DataFrame

        # if not os.path.exists(self.UFCStats_loc):
        #     os.makedirs(self.UFCStats_loc)
        #
        # if not os.path.exists(self.UFCStats_loc + '/matchups'):
        #     os.makedirs(self.UFCStats_loc + '/matchups')
        #     self.scrape_ufcstats()

        self.combine_ufcstats()

        if not os.path.exists(self.sherdog_loc):
            os.makedirs(self.sherdog_loc)
            self.scrape_sherdog()

        self.combine_sherdog()
        # self.load_staffpicks()
        # self.process_staffpicks()

        if not os.path.exists(self.UFCStats_loc + '/odds'):
            os.makedirs(self.UFCStats_loc + '/odds')
            self.getOdds(self.odds_webpage)

        if not os.path.exists(self.UFCStats_loc + '/picks'):
            os.makedirs(self.UFCStats_loc + '/picks')

        self.dk_odds = self.load_and_process_odds()
        # print(self.dk_odds)

        self.add_dk_info()
        # self.scrape_bloodyelbow_staffpicks()
        self.stat_override()

        self.add_fight_history()

        if not os.path.exists(self.UFCStats_loc + '/fighters'):
            os.makedirs(self.UFCStats_loc + '/fighters')
            for vs in self.UFCStats_dict.keys():
                for f in self.UFCStats_dict[vs].keys():
                    self.getStats(self.UFCStats_dict[vs][f]['UFCStats_Link'])

            # self.getStats(f)
        # self.brute_force_dk_salary_picks(2000)
        self.pick_n_everyway(self.PICK_EVERY_WAY - len(self.forced_matchups), self.forced_matchups)
        self.greedy_pick([])

    def stat_override(self):
        for fighter in list(self.override_stats.keys()):
            matchups = list(self.UFCStats_dict.keys())
            for matchup in matchups:
                if fighter in matchup:
                    print(fighter)
                    self.UFCStats_dict[matchup][fighter]['AvgPointsPerGame'] = self.override_stats[fighter]
                    self.UFCStats_dict[matchup][fighter]['WeightedAvgPoints'] = self.override_stats[fighter]*self.UFCStats_dict[matchup][fighter]['odds']

    def fix_dk_csv(self):

        # open your csv and read as a text string
        with open(self.dk_csv_path, 'r') as f:
            my_csv_text = f.read()

        find_str = 'Position,Name \+ ID,Name,ID,Roster Position,Salary,Game Info,TeamAbbrev,AvgPointsPerGame'
        replace_str = 'Position,NameID,Name,ID,RosterPosition,Salary,GameInfo,TeamAbbrev,AvgPointsPerGame'

        # substitute
        new_csv_str = re.sub(find_str, replace_str, my_csv_text)

        # open new file and save
        # new_csv_path = './my_new_csv.csv'  # or whatever path and name you want
        with open(self.dk_csv_path, 'w') as f:
            f.write(new_csv_str)

    # load the salary data from the .csv passed into object
    def load_dk_csv(self):
        self.fix_dk_csv()
        dk_sal = pd.read_csv(self.dk_csv_path, index_col=3)
        dk_sal = dk_sal.drop(dk_sal[dk_sal.GameInfo == "Cancelled"].index)
        dk_sal['LastName'] = dk_sal['Name'].apply(lambda x: x.split(' ', 1)[1])
        dk_sal['Fighter1'] = dk_sal['GameInfo'].apply(lambda x: x.split('@')[0])
        dk_sal['Fighter2'] = dk_sal['GameInfo'].apply(lambda x: x.split('@')[1][0:-22])
        dk_sal['Opponent'] = np.where(dk_sal['LastName'] == dk_sal['Fighter1'],
                                      dk_sal['Fighter2'], dk_sal['Fighter1'])
        # # Need to check for possible misidentifications.
        # self.fights_on_ticket = int(len(dk_sal.index) / 2)
        # self.melt_dk = pd.melt(dk_sal, id_vars=["Name"], value_vars=['Opponent','Salary','AvgPointsPerGame'])
        return dk_sal

    def combine_ufcstats(self):
        dir_name = os.getcwd() + '/' + self.UFCStats_loc + '/matchups'
        # Load and combine dictionaries
        self.fights_on_ticket = int(len(os.listdir(dir_name)))
        for filename in os.listdir(dir_name):
            with open(os.path.join(dir_name, filename)) as f:  # open in readonly mode
                matchup_dict = json.load(f)
                matchup_dict = self.clean_ufcstats(matchup_dict)
                self.UFCStats_dict.update(matchup_dict)

    def combine_sherdog(self):
        dir_name = os.getcwd() + '/' + self.sherdog_loc
        # Load and combine dictionaries
        # self.fights_on_ticket = int(len(os.listdir(dir_name)))
        # print(self.fights_on_ticket)
        for filename in os.listdir(dir_name):
            # print(filename)
            # amateur record causing issues with chronology
            with open(os.path.join(dir_name, filename)) as f:  # open in readonly mode
                # print(f.read())
                matchup_dict = json.load(f)
                # matchup_dict = self.clean_ufcstats(matchup_dict)
                # # print(matchup_dict)
                # self.UFCStats_dict.update(matchup_dict)

    def add_dk_info(self):
        odds_names = list(self.dk_odds.keys())
        odds_last_names = [n.split()[-1] for n in odds_names]
        odds_first_names = [n.split()[0] for n in odds_names]
        # print(odds_last_names)
        vs = list(self.UFCStats_dict.keys())
        for index, row in self.dk_salaries.iterrows():
            for fight in vs:
                if fight.find(row['Name']) != -1:
                    fighters = self.UFCStats_dict[fight]
                    if row['Name'] in list(fighters.keys()):
                        name = row['Name'].split()
                        first_name = name[0]
                        last_name = name[-1]
                        if last_name in odds_last_names:
                            # print(row['Name'])
                            substr = last_name
                        elif first_name in odds_first_names:
                            # print(row['Name'])
                            substr = first_name
                        else:
                            print('missing: ' + row['Name'])
                            substr = ''

                        temp = fighters[row['Name']]
                        if substr:
                            for name in odds_names:
                                if substr in name:
                                    # print(name, self.dk_odds[name])
                                    temp['odds'] = self.dk_odds[name]
                                    temp['WeightedAvgPoints'] = row['AvgPointsPerGame'] * self.dk_odds[name]
                                    break

                        temp['Salary'] = row['Salary']
                        temp['AvgPointsPerGame'] = row['AvgPointsPerGame']
                        fighters[row['Name']] = temp
                        self.UFCStats_dict[fight] = fighters
                        # print(self.UFCStats_dict[fight])
                    else:
                        print("error for fighter: ", row['Name'])

                    break

            # print(row['Name'], row['Salary'])

    def scrape_ufcstats(self):
        if self.event_webpage_ufcstats:
            process = CrawlerProcess()
            process.crawl(UFCStatsSpider, domain=[self.event_webpage_ufcstats], name=self.UFCStats_loc)
            process.start()

    def scrape_sherdog(self):
        if self.sherdog_webpage:
            process = CrawlerProcess()
            process.crawl(SherdogSpider, domain=[self.sherdog_webpage], name=self.sherdog_loc)
            process.start()

    def scrape_bloodyelbow_staffpicks(self):
        # if no staff picks a fighter, than opp is good pick?
        if self.bloodyelbow_webpage:
            process = CrawlerProcess()
            process.crawl(BloodyElbowSpider, domain=[self.bloodyelbow_webpage])
            process.start()

    def load_staffpicks(self):
        dir_name = os.getcwd() + '/' + self.bloodyelbow_loc
        # Load and combine dictionaries
        for filename in os.listdir(dir_name):
            # print(filename)
            with open(os.path.join(dir_name, filename)) as f:  # open in readonly mode
                # print(f.read())
                self.staffpicks_dict = json.load(f)  # print(matchup_dict)

    def process_staffpicks(self):
        names_staffpicks = list(self.staffpicks_dict.keys())
        for name in self.FIGHTERS_OUT:
            names_staffpicks.remove(name)
        names_staffpicks_copy = names_staffpicks

        new_dict = {}
        # print(names_staffpicks)
        # print(self.fighter_names)
        for name in names_staffpicks:
            for fullname in self.fighter_names:
                if name in fullname:
                    # print(name,fullname)
                    new_dict[fullname] = self.staffpicks_dict[name]
                    names_staffpicks_copy.remove(name)
                    break
                else:
                    print(name, fullname)
        # print(names_staffpicks_copy)
        # print(new_dict.keys())

    def add_staffpicks(self):
        pass

    def add_fight_history(self):
        # print(self.UFCStats_dict.keys())
        for match in list(self.UFCStats_dict.keys()):
            for fighter in list(self.UFCStats_dict[match].keys()):
                dir_name = self.sherdog_loc
                filename = fighter + '.txt'
                onlyfiles = [f for f in listdir(dir_name) if isfile(join(dir_name, f))]
                try:
                    with open(os.path.join(dir_name, filename)) as f:  # open in readonly mode
                        pass
                        # print(f.read())
                        # matchup_dict = jsonn.load(f)
                        # matchup_dict = self.clean_ufcstats(matchup_dict)
                        # # print(matchup_dict)
                        # self.UFCStats_dict.update(matchup_dict)
                except FileNotFoundError:
                    # Can't find fighter by full name, try fist than last for match.
                    # Need to watch for common names!!! Need a catch for this!!!
                    print(fighter)
                    print('Looking...')
                    for file in onlyfiles:
                        name = fighter.split()
                        firstname = name[0]
                        lastname = name[-1]
                        lastname = lastname.split('-')[-1]
                        if lastname in file:
                            print('FOUND')
                            break
                        elif firstname in file:
                            print('FOUND')
                            break

    def clean_ufcstats(self, matchup_dict, fighters=None):
        vs = list(matchup_dict.keys())
        # print(vs)
        fighters = matchup_dict[vs[0]]
        # print(matchup_dict)
        fighter_keys = list(fighters.keys())
        # print(fighter_keys)
        fighter_1_name = fighter_keys[0]
        fighter_1_info = fighters[fighter_1_name]

        fighter_2_name = fighter_keys[1]
        fighter_2_info = fighters[fighter_2_name]

        fighter_1_info['Wins'], fighter_1_info['Losses'], fighter_1_info['Draws'], fighter_1_info['NC'] = \
            self.process_mma_record(fighter_1_info['Wins/Losses/Draws'])
        del fighter_1_info['Wins/Losses/Draws']
        fighter_2_info['Wins'], fighter_2_info['Losses'], fighter_2_info['Draws'], fighter_2_info['NC'] = \
            self.process_mma_record(fighter_2_info['Wins/Losses/Draws'])
        del fighter_2_info['Wins/Losses/Draws']

        fighter_1_info['Average Fight Time'], fighter_1_info['Newcomer'], fighter_1_info['Age'] = \
            self.process_time_data(fighter_1_info['Average Fight Time'], fighter_1_info['DOB'])
        fighter_2_info['Average Fight Time'], fighter_2_info['Newcomer'], fighter_2_info['Age'] = \
            self.process_time_data(fighter_2_info['Average Fight Time'], fighter_2_info['DOB'])

        fighter_1_info['Height'] = self.process_height(fighter_1_info['Height'])
        fighter_1_info['Weight'] = self.process_weight(fighter_1_info['Weight'])
        fighter_1_info['Reach'] = self.process_reach(fighter_1_info['Reach'])
        fighter_1_info['Striking Accuracy'], fighter_1_info['Defense'], \
        fighter_1_info['Takedown Accuracy'], fighter_1_info['Takedown Defense'] = \
            self.process_percentage(fighter_1_info['Striking Accuracy'], fighter_1_info['Defense'],
                                    fighter_1_info['Takedown Accuracy'], fighter_1_info['Takedown Defense'])
        fighter_1_info['Strikes Landed per Min. (SLpM)'], fighter_1_info['Strikes Absorbed per Min. (SApM)'], \
        fighter_1_info['Takedowns Average/15 min.'], fighter_1_info['Submission Average/15 min.'] = \
            self.process_str_to_float(fighter_1_info['Strikes Landed per Min. (SLpM)'],
                                      fighter_1_info['Strikes Absorbed per Min. (SApM)'],
                                      fighter_1_info['Takedowns Average/15 min.'],
                                      fighter_1_info['Submission Average/15 min.'])
        fighter_1_info['Recent Wins'] = self.process_recent_ufc_record(fighter_1_info['Recent Fights'])

        fighter_2_info['Height'] = self.process_height(fighter_2_info['Height'])
        fighter_2_info['Weight'] = self.process_weight(fighter_2_info['Weight'])
        fighter_2_info['Reach'] = self.process_reach(fighter_2_info['Reach'])
        fighter_2_info['Striking Accuracy'], fighter_2_info['Defense'], \
        fighter_2_info['Takedown Accuracy'], fighter_2_info['Takedown Defense'] = \
            self.process_percentage(fighter_2_info['Striking Accuracy'], fighter_2_info['Defense'],
                                    fighter_2_info['Takedown Accuracy'], fighter_2_info['Takedown Defense'])
        fighter_2_info['Strikes Landed per Min. (SLpM)'], fighter_2_info['Strikes Absorbed per Min. (SApM)'], \
        fighter_2_info['Takedowns Average/15 min.'], fighter_2_info['Submission Average/15 min.'] = \
            self.process_str_to_float(fighter_2_info['Strikes Landed per Min. (SLpM)'],
                                      fighter_2_info['Strikes Absorbed per Min. (SApM)'],
                                      fighter_2_info['Takedowns Average/15 min.'],
                                      fighter_2_info['Submission Average/15 min.'])
        fighter_2_info['Recent Wins'] = self.process_recent_ufc_record(fighter_2_info['Recent Fights'])
        self.fighter_names.append(fighter_1_name)
        self.fighter_names.append(fighter_2_name)

        return {vs[0]: {fighter_1_name: fighter_1_info, fighter_2_name: fighter_2_info}}

    def process_recent_ufc_record(self, record_list):
        """Convert 'W' to True, all else to false. That is, a fight won is recorded a True"""
        record = []
        for fight in record_list:
            if fight[0] == 'W':
                record.append(True)
            else:
                record.append(False)
        return record

    def process_str_to_float(self, SLpM, SApM, takedown_avg, sub_avg):
        """Convert strings to floats"""
        return float(SLpM), float(SApM), float(takedown_avg), float(sub_avg)

    def process_percentage(self, strike_acc, strike_def, takedown_acc, takedown_def):
        """Convert string to percentages"""
        return float(strike_acc.rstrip("%")) / 100, float(strike_def.rstrip("%")) / 100, \
               float(takedown_def.rstrip("%")) / 100, float(takedown_acc.rstrip("%")) / 100

    def process_reach(self, reach):
        if reach == '--':
            w = 0
        else:
            w = int(reach.rstrip('\"'))
        return w

    def process_height(self, height):
        h = height.split()
        inch = h[1].rstrip('\"')
        return int(h[0][0]) * 12 + int(inch)

    def process_weight(self, weight):
        w = weight.split()
        return int(w[0])

    def process_time_data(self, avg_ftime, dob):
        aft_secs = -1  # distinguish as missing data
        newcomer = False
        if avg_ftime:
            try:
                aft = datetime.strptime(avg_ftime, '%M:%S')
                aft_secs = aft.minute * 60 + aft.second
            except ValueError:
                aft = datetime.strptime(avg_ftime, ':%S')
                aft_secs = aft.second
        else:
            newcomer = True  # assume no avg fight time means this is UFC debut

        born = datetime.strptime(dob, '%b %d, %Y')
        today = date.today()
        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return aft_secs, newcomer, age

    def process_mma_record(self, f1):
        f1w, f1l, f1d, f1nc = (0, 0, 0, 0)
        f1s = f1.split()
        record = f1s[0].split('-')
        f1w, f1l, f1d = tuple(map(lambda x: int(x), record))
        if len(f1s) > 1:
            nc = f1s[1]
            # assume less than 10 no contests
            f1nc = int(nc[1])

        return f1w, f1l, f1d, f1nc

    def brute_force_dk_salary_picks(self, max_remaining_salary=1000):
        brute_force_picks = []
        brute_force_points = []
        df_brute_force = pd.DataFrame()
        comb = list(combinations(range(2 * self.fights_on_ticket), self.FIGHTERS_TO_PICK))
        matchups = list(self.UFCStats_dict.keys())
        for i in comb:
            # print(i)
            temp_picks = []
            temp_salary = self.DK_MAX_SALARY
            TotalAvgPointsPerGame = 0
            for pick in i:
                match = self.UFCStats_dict[matchups[pick // 2]]
                fighters = list(match.keys())
                fighter = fighters[pick % 2]
                info = match[fighter]
                # print(fighter, info)

                if (info['Opponent'] in temp_picks) and self.NO_PICKING_BOTH:
                    break
                else:
                    temp_picks.append(fighter)
                    temp_salary -= info['Salary']
                    if info['Newcomer']:
                        print('Newcomer')
                        TotalAvgPointsPerGame += self.NEWCOMER_POINTS
                    else:
                        TotalAvgPointsPerGame += info['AvgPointsPerGame']
                if temp_salary < 0:
                    break
            if 0 <= temp_salary <= max_remaining_salary:
                if len(temp_picks) == self.FIGHTERS_TO_PICK:
                    # print(temp_salary, temp_picks)
                    brute_force_picks.append(temp_picks)
                    brute_force_points.append(TotalAvgPointsPerGame)
                # need to deal with newcomers...no stats to use...get something from sherdog or staff picks???
                # how to detect 5 round fight?
                # need a manual override to force a pick
        df_brute_force["TotalAvgPointsPerGame"] = brute_force_points
        df_brute_force["Index"] = range(len(brute_force_points))

        brute_force_picks = np.array(brute_force_picks)
        print(brute_force_picks)
        print(df_brute_force)
        # itemgetter(list(df_brute_force[df_brute_force.TotalAvgPointsPerGame > 420].index))(brute_force_picks)
        print(brute_force_picks[list(df_brute_force[df_brute_force.TotalAvgPointsPerGame >= self.MIN_POINTS].index)])
        print(df_brute_force[df_brute_force.TotalAvgPointsPerGame >= self.MIN_POINTS])
        # print(len(brute_force_picks[list(df_brute_force[df_brute_force.TotalAvgPointsPerGame > 445].index)]))

    def pick_n_everyway(self, n, forced_matchups=[]):
        comb = list(combinations(range(self.fights_on_ticket), n))
        matchups = list(self.UFCStats_dict.keys())
        best = []
        best_comb = []
        opt_n_everyway = 0
        for i in comb:
            temp_picks = []
            TotalAvgPointsPerGame = 0
            for pick in i:
                match = self.UFCStats_dict[matchups[pick]]
                fighters = list(match.keys())
                # print(matchups[pick])
                fighter1 = fighters[0]
                fighter2 = fighters[1]
                # tot_points = match[fighter1]['AvgPointsPerGame'] + match[fighter2]['AvgPointsPerGame']
                tot_points = match[fighter1]['WeightedAvgPoints'] + match[fighter2]['WeightedAvgPoints']
                TotalAvgPointsPerGame += tot_points
                temp_picks.append(matchups[pick])
            if TotalAvgPointsPerGame > opt_n_everyway:
                best = temp_picks
                best_comb = comb
                # print(TotalAvgPointsPerGame, best)
                opt_n_everyway = TotalAvgPointsPerGame

        opt_picks = forced_matchups + best
        print(opt_picks)
        opt_pick_count = len(opt_picks)
        remaining_fight_count = self.FIGHTERS_TO_PICK - opt_pick_count
        remaining_matchups = []
        for remaining in list(self.UFCStats_dict.keys()):
            if remaining not in opt_picks:
                remaining_matchups.append(remaining)
        print(remaining_matchups)

        pick_binary = list(product([0, 1], repeat=opt_pick_count))
        print(pick_binary)
        for pick in pick_binary:
            # print(pick)
            total_salary = self.DK_MAX_SALARY
            fighter_picks = []
            for match_loc, fighter_loc in enumerate(pick):
                # print(match_loc, fighter_loc)
                matchup_dicts = self.UFCStats_dict[opt_picks[match_loc]]
                fighters = list(matchup_dicts.keys())
                total_salary -= matchup_dicts[fighters[fighter_loc]]['Salary']
                fighter_picks.append(fighters[fighter_loc])
            # print(total_salary)
            comb = list(combinations(range(2 * (self.fights_on_ticket - opt_pick_count)), remaining_fight_count))
            best_points = 0
            best_pick = []
            for c in comb:
                temp_salary = total_salary
                temp_picks = []
                TotalAvgPointsPerGame = 0
                for p in c:
                    match = self.UFCStats_dict[remaining_matchups[p // 2]]
                    fighters = list(match.keys())
                    fighter = fighters[p % 2]
                    info = match[fighter]
                    # print(fighter, info)

                    if (info['Opponent'] in temp_picks) and self.NO_PICKING_BOTH:
                        break
                    else:
                        # print(fighter,info['WeightedAvgPoints'])
                        temp_picks.append(fighter)
                        temp_salary -= info['Salary']
                        TotalAvgPointsPerGame += info['WeightedAvgPoints']
                        # if info['Newcomer'] and info['WeightedAvgPoints']==0:
                        #     # print('Newcomer')
                        #     TotalAvgPointsPerGame += self.NEWCOMER_POINTS
                        # else:
                        #     # TotalAvgPointsPerGame += info['AvgPointsPerGame']
                        #     TotalAvgPointsPerGame += info['WeightedAvgPoints']
                # if len(fighter_picks + temp_picks)==6:
                #     print(temp_salary,TotalAvgPointsPerGame,temp_picks)
                if TotalAvgPointsPerGame > best_points and temp_salary >= 0 and len(fighter_picks + temp_picks) == 6:
                    best_points = TotalAvgPointsPerGame
                    best_pick = temp_picks

            print(fighter_picks + best_pick)

    def greedy_pick(self, forced_picks=[]):
        matchups = list(self.UFCStats_dict.keys())
        total_salary = self.DK_MAX_SALARY

        comb = list(combinations(range(2 * self.fights_on_ticket), 6))
        best_points = 0
        best_pick = []
        for c in comb:
            temp_salary = total_salary
            temp_picks = []
            TotalAvgPointsPerGame = 0
            for p in c:
                match = self.UFCStats_dict[matchups[p // 2]]
                fighters = list(match.keys())
                fighter = fighters[p % 2]
                info = match[fighter]
                # print(fighter, info)

                if (info['Opponent'] in temp_picks) and self.NO_PICKING_BOTH:
                    break
                else:
                    temp_picks.append(fighter)
                    temp_salary -= info['Salary']
                    if info['Newcomer']:
                        # print('Newcomer')
                        TotalAvgPointsPerGame += self.NEWCOMER_POINTS
                    else:
                        # TotalAvgPointsPerGame += info['AvgPointsPerGame']
                        TotalAvgPointsPerGame += info['WeightedAvgPoints']

            if TotalAvgPointsPerGame > best_points and temp_salary >= 0 and len(temp_picks) == 6:
                best_points = TotalAvgPointsPerGame
                best_pick = temp_picks

        print(best_pick)
        file = open(self.UFCStats_loc + '/picks/greedy_pick.csv', 'w+', newline='')

        with file:
            write = csv.writer(file)
            write.writerows([best_pick])

    def getWebPage(self, url):
        page = urllib2.urlopen(url)
        soup = BeautifulSoup(page, 'html.parser')
        return soup

    def getStats(self, url):
        soup = self.getWebPage(url)

        stats = {}

        name = str(soup.h2.span.string).strip()
        stats["Name"] = name
        nick = str(soup.p.string).strip()
        stats["Nick"] = nick

        ulList = soup.find_all('ul')

        for ul in ulList:  # accessing each individual ul tag in ulList
            for li in ul.find_all('li'):  # iterating through each li tag in each ul tag
                if li.i and (str(
                        li.i.string).strip() != ""):  # Since and short circuits wont run into error of prevLi.i not existing and trying to get a string from it.
                    statName = str(li.i.string).strip()
                    statNum = str(li.contents[
                                      2]).strip()  # If there is a statName inside the i tag there is always an associated statNum outside the i tag but in the li tag
                    stats[statName] = statNum

        tableList = soup.find_all('table')
        pList = tableList[0].find_all('p')
        info = []
        for p in pList:  # accessing each individual ul tag in ulList
            # a_all = p.find_all('a')
            info.append(p.text.strip())
            # if a_all:
            #     info.append(a_all[0].text.strip())
        # print(info)
        stats['UFC_Record'] = {}
        while info:
            temp_info = info.pop(0)
            if temp_info == 'next':
                # print(temp_info)
                f1 = info.pop(0)
                f2 = info.pop(0)
                info.pop(0)
                event = info.pop(0)
                date = info.pop(0)
                stats['Upcoming'] = {'Date': date, 'Event': event, 'Opponent': f2, 'Outcome': temp_info}
            else:
                # print(info)
                f1 = info.pop(0)
                f2 = info.pop(0)
                f1_str = int(info.pop(0))
                f2_str = int(info.pop(0))
                f1_td = int(info.pop(0))
                f2_td = int(info.pop(0))
                f1_sub = int(info.pop(0))
                f2_sub = int(info.pop(0))
                f1_pass = int(info.pop(0))
                f2_pass = int(info.pop(0))

                event = info.pop(0)
                date = info.pop(0)
                method = info.pop(0)
                method_detail = info.pop(0)
                round = info.pop(0)
                time = info.pop(0)

                stats['UFC_Record'][date] = {'Event': event, 'Opponent': f2,
                                             'STR_Opp': f2_str, 'STR': f1_str,
                                             'TD_Opp': f2_td, 'TD': f1_td,
                                             'SUB_Opp': f2_sub, 'SUB': f1_sub,
                                             'PASS_Opp': f2_pass, 'PASS': f1_pass,
                                             'Outcome': temp_info, 'Method': method, 'Method_Detail': method_detail,
                                             'Round': round, 'Time': time}
                # print(stats['UFC_Record'].keys())

        # print(stats.keys())
        # statDictionary = {stat[0]: stat[1] for stat in stats}  # creating python dictionary from list of data
        # create json object from python dictionary

        filename = self.UFCStats_loc + '/fighters/' + name + '.txt'

        jsonStats = json.dumps(stats, indent=4)
        # print(filename)
        with open(filename, 'w') as outfile:
            outfile.write(jsonStats)
        # return jsonStats

    def getOdds(self, url):
        soup = self.getWebPage(url)
        spanList = soup.find_all('span')
        names = []
        odds = []
        names_odds = {}
        prev_line = ''
        for ul in spanList:  # accessing each individual ul tag in ulList
            if ul.text:
                if ul.text[0] == '-' or ul.text[0] == '+':
                    names.append(prev_line)
                    odds.append(ul.text)
            prev_line = ul.text

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
        jsonStats = json.dumps(names_odds, indent=4)
        filename = self.UFCStats_loc + '/odds/raw_dk_odds.txt'
        with open(filename, 'w') as outfile:
            outfile.write(jsonStats)

    def load_and_process_odds(self):
        filename = self.UFCStats_loc + '/odds/raw_dk_odds.txt'
        with open(filename) as f:  # open in readonly mode
            # print(f.read())
            dk_odds = json.load(f)  # print(matchup_dict)
        # what if missing odds?
        # for name in list(dk_odds.keys()):
        #     print(name,dk_odds[name])
        return dk_odds


if __name__ == '__main__':
    event_webpage = "https://www.draftkings.com/draft/contest/90790409"
    test_1 = Event(event_webpage, 'DK_Salaries/DKSalaries_UFC_full_card_20200905.csv')
    print(test_1.dk_salaries.loc[list((0, 2, 3))])
