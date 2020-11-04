import json
import csv
import os

import pandas as pd
import numpy as np

from datetime import datetime, date
from itertools import combinations, product
from os import listdir
from os.path import isfile, join


def process_mma_record(f1):
    f1w, f1l, f1d, f1nc = (0, 0, 0, 0)
    f1s = f1.split()
    record = f1s[0].split('-')
    f1w, f1l, f1d = tuple(map(lambda x: int(x), record))
    if len(f1s) > 1:
        nc = f1s[1]
        # assume less than 10 no contests
        f1nc = int(nc[1])

    return f1w, f1l, f1d, f1nc


def process_time_data(avg_ftime, dob):
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


def process_weight(weight):
    w = weight.split()
    return int(w[0])


def process_height(height):
    h = height.split()
    inch = h[1].rstrip('\"')
    return int(h[0][0]) * 12 + int(inch)


def process_reach(reach):
    if reach == '--':
        w = 0
    else:
        w = int(reach.rstrip('\"'))
    return w


def process_percentage(strike_acc, strike_def, takedown_acc, takedown_def):
    """Convert string to percentages"""
    return float(strike_acc.rstrip("%")) / 100, float(strike_def.rstrip("%")) / 100, \
           float(takedown_def.rstrip("%")) / 100, float(takedown_acc.rstrip("%")) / 100


def process_str_to_float(SLpM, SApM, takedown_avg, sub_avg):
    """Convert strings to floats"""
    return float(SLpM), float(SApM), float(takedown_avg), float(sub_avg)


def process_recent_ufc_record(record_list):
    """Convert 'W' to True, all else to false. That is, a fight won is recorded a True"""
    record = []
    for fight in record_list:
        if fight[0] == 'W':
            record.append(True)
        else:
            record.append(False)
    return record


class Event:
    DK_MAX_SALARY = 50000
    FIGHTERS_TO_PICK = 6
    FIGHTERS_OUT = []
    NO_PICKING_BOTH = True
    MIN_POINTS = 510
    RECURSIVENESS = 1  # NUMBER OF FIGHTS TO PICK ALL POSSIBLE COMBOS
    NEWCOMER_POINTS = 25
    PICK_EVERY_WAY = 2

    def __init__(self,
                 card_id: str = '',
                 override_stats: dict = {},
                 forced_matchups: list = []):

        self.override_stats = override_stats
        self.UFCStats_dict = {}

        self.fighter_names = []
        self.fights_on_ticket = 0
        self.forced_matchups = forced_matchups

        self.ufcstats_event_loc = 'UFCStats_Dicts/' + card_id
        self.sherdog_event_loc = 'Sherdog_Dicts/' + card_id
        self.salary_csv_loc = 'DraftKings/Salary_CSV/DKSalaries_' + card_id + '.csv'
        self.payout_csv_loc = 'DraftKings/Payout_CSV/DKPayout_' + card_id + '.csv'
        self.odds_json_loc = 'DraftKings/Odds_JSON/DKOdds_' + card_id + '.json'
        self.salary_csv_loc = 'DraftKings/Salary_CSV/DKSalaries_' + card_id + '.csv'
        self.payout_csv_loc = 'DraftKings/Payout_CSV/DKPayout_' + card_id + '.csv'

        if not os.path.exists(self.ufcstats_event_loc + '/picks'):
            os.makedirs(self.ufcstats_event_loc + '/picks')

        self.dk_salaries = self.load_dk_csv()  # DataFrame
        self.combine_ufcstats()
        # self.combine_sherdog()
        self.dk_odds = self.load_and_process_odds()
        self.add_dk_info()
        self.stat_override()
        self.add_fight_history()
        #
        # # self.brute_force_dk_salary_picks(2000)
        self.pick_n_everyway(self.PICK_EVERY_WAY - len(self.forced_matchups))
        self.greedy_pick()

    def assert_stats_dict(self):
        """Assert statements to catch errors in stats dictionaries..."""
        pass
    def combine_ufcstats(self):
        """Load and combine matchup info into """
        dir_name = self.ufcstats_event_loc  + '/matchups'
        # Load and combine dictionaries
        self.fights_on_ticket = int(len(os.listdir(dir_name)))
        for filename in os.listdir(dir_name):
            with open(os.path.join(dir_name, filename)) as f:  # open in readonly mode
                matchup_dict = json.load(f)
                matchup_dict = self.clean_ufcstats(matchup_dict)
                self.UFCStats_dict.update(matchup_dict)

    def clean_ufcstats(self, matchup_dict):
        vs = list(matchup_dict.keys())
        fighters = matchup_dict[vs[0]]
        fighter_keys = list(fighters.keys())
        fighter_1_name = fighter_keys[0]
        fighter_1_info = fighters[fighter_1_name]
        fighter_2_name = fighter_keys[1]
        fighter_2_info = fighters[fighter_2_name]

        fighter_1_info['Wins'], fighter_1_info['Losses'], fighter_1_info['Draws'], fighter_1_info['NC'] = \
            process_mma_record(fighter_1_info['Wins/Losses/Draws'])
        del fighter_1_info['Wins/Losses/Draws']
        fighter_2_info['Wins'], fighter_2_info['Losses'], fighter_2_info['Draws'], fighter_2_info['NC'] = \
            process_mma_record(fighter_2_info['Wins/Losses/Draws'])
        del fighter_2_info['Wins/Losses/Draws']

        fighter_1_info['Average Fight Time'], fighter_1_info['Newcomer'], fighter_1_info['Age'] = \
            process_time_data(fighter_1_info['Average Fight Time'], fighter_1_info['DOB'])
        fighter_2_info['Average Fight Time'], fighter_2_info['Newcomer'], fighter_2_info['Age'] = \
            process_time_data(fighter_2_info['Average Fight Time'], fighter_2_info['DOB'])

        fighter_1_info['Height'] = process_height(fighter_1_info['Height'])
        fighter_1_info['Weight'] = process_weight(fighter_1_info['Weight'])
        fighter_1_info['Reach'] = process_reach(fighter_1_info['Reach'])
        fighter_1_info['Striking Accuracy'], fighter_1_info['Defense'], \
        fighter_1_info['Takedown Accuracy'], fighter_1_info['Takedown Defense'] = \
            process_percentage(fighter_1_info['Striking Accuracy'], fighter_1_info['Defense'],
                                    fighter_1_info['Takedown Accuracy'], fighter_1_info['Takedown Defense'])
        fighter_1_info['Strikes Landed per Min. (SLpM)'], fighter_1_info['Strikes Absorbed per Min. (SApM)'], \
        fighter_1_info['Takedowns Average/15 min.'], fighter_1_info['Submission Average/15 min.'] = \
            process_str_to_float(fighter_1_info['Strikes Landed per Min. (SLpM)'],
                                      fighter_1_info['Strikes Absorbed per Min. (SApM)'],
                                      fighter_1_info['Takedowns Average/15 min.'],
                                      fighter_1_info['Submission Average/15 min.'])
        fighter_1_info['Recent Wins'] = process_recent_ufc_record(fighter_1_info['Recent Fights'])

        fighter_2_info['Height'] = process_height(fighter_2_info['Height'])
        fighter_2_info['Weight'] = process_weight(fighter_2_info['Weight'])
        fighter_2_info['Reach'] = process_reach(fighter_2_info['Reach'])
        fighter_2_info['Striking Accuracy'], fighter_2_info['Defense'], \
        fighter_2_info['Takedown Accuracy'], fighter_2_info['Takedown Defense'] = \
            process_percentage(fighter_2_info['Striking Accuracy'], fighter_2_info['Defense'],
                                    fighter_2_info['Takedown Accuracy'], fighter_2_info['Takedown Defense'])
        fighter_2_info['Strikes Landed per Min. (SLpM)'], fighter_2_info['Strikes Absorbed per Min. (SApM)'], \
        fighter_2_info['Takedowns Average/15 min.'], fighter_2_info['Submission Average/15 min.'] = \
            process_str_to_float(fighter_2_info['Strikes Landed per Min. (SLpM)'],
                                      fighter_2_info['Strikes Absorbed per Min. (SApM)'],
                                      fighter_2_info['Takedowns Average/15 min.'],
                                      fighter_2_info['Submission Average/15 min.'])
        fighter_2_info['Recent Wins'] = process_recent_ufc_record(fighter_2_info['Recent Fights'])
        self.fighter_names.append(fighter_1_name)
        self.fighter_names.append(fighter_2_name)

        return {vs[0]: {fighter_1_name: fighter_1_info, fighter_2_name: fighter_2_info}}

    def stat_override(self):
        for fighter in list(self.override_stats.keys()):
            matchups = list(self.UFCStats_dict.keys())
            for matchup in matchups:
                if fighter in matchup:
                    print(fighter)
                    self.UFCStats_dict[matchup][fighter]['AvgPointsPerGame'] = self.override_stats[fighter]
                    self.UFCStats_dict[matchup][fighter]['WeightedAvgPoints'] = \
                        self.override_stats[fighter] * self.UFCStats_dict[matchup][fighter]['odds']

    def load_dk_csv(self):
        """Load the salary data from the .csv, return as DataFrame"""
        dk_sal = pd.read_csv(self.salary_csv_loc, index_col=3)
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

    def combine_sherdog(self):
        """Load and combine dictionaries"""
        # dir_name = os.getcwd() + '/' + self.sherdog_event_loc
        #
        # self.fights_on_ticket = int(len(os.listdir(dir_name)))
        # print(self.fights_on_ticket)
        for filename in os.listdir(self.sherdog_event_loc):
            print(filename)
            with open(os.path.join(self.sherdog_event_loc, filename)) as f:  # open in readonly mode
                # print(f.read())
                matchup_dict = json.load(f)
                # print(matchup_dict)
                # matchup_dict = self.clean_ufcstats(matchup_dict)
                # # print(matchup_dict)
                # self.UFCStats_dict.update(matchup_dict)

    def add_dk_info(self):
        """Associate the names in dk_odds with dk_salaries"""
        odds_names = list(self.dk_odds.keys())
        odds_last_names = [n.split()[-1] for n in odds_names]
        odds_first_names = [n.split()[0] for n in odds_names]
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
                    else:
                        print("error for fighter: ", row['Name'])
                    break

    def add_fight_history(self):
        """"""
        for match in list(self.UFCStats_dict.keys()):
            for fighter in list(self.UFCStats_dict[match].keys()):
                dir_name = self.sherdog_event_loc
                filename = fighter + '.json'
                onlyfiles = [f for f in listdir(dir_name) if isfile(join(dir_name, f))]
                try:
                    with open(os.path.join(dir_name, filename)) as f:  # open in readonly mode
                        pass
                        # print(f.read())
                        # matchup_dict = json.load(f)
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

    def pick_n_everyway(self, n):
        comb = list(combinations(range(self.fights_on_ticket), n))
        matchups = list(self.UFCStats_dict.keys())
        best = []
        best_comb = []
        n_picks = []
        opt_n_everyway = 0
        for i in comb:
            temp_picks = []
            TotalAvgPointsPerGame = 0
            for pick in i:
                match = self.UFCStats_dict[matchups[pick]]
                fighters = list(match.keys())
                fighter1 = fighters[0]
                fighter2 = fighters[1]
                # tot_points = match[fighter1]['AvgPointsPerGame'] + match[fighter2]['AvgPointsPerGame']
                tot_points = match[fighter1]['WeightedAvgPoints'] + match[fighter2]['WeightedAvgPoints']
                TotalAvgPointsPerGame += tot_points
                temp_picks.append(matchups[pick])
            if TotalAvgPointsPerGame > opt_n_everyway:
                best = temp_picks
                best_comb = comb
                opt_n_everyway = TotalAvgPointsPerGame

        opt_picks = self.forced_matchups + best
        print(opt_picks)
        opt_pick_count = len(opt_picks)
        remaining_fight_count = self.FIGHTERS_TO_PICK - opt_pick_count
        remaining_matchups = []
        for remaining in list(self.UFCStats_dict.keys()):
            if remaining not in opt_picks:
                remaining_matchups.append(remaining)

        pick_binary = list(product([0, 1], repeat=opt_pick_count))
        for pick in pick_binary:
            total_salary = self.DK_MAX_SALARY
            fighter_picks = []
            for match_loc, fighter_loc in enumerate(pick):
                # print(match_loc, fighter_loc)
                matchup_dicts = self.UFCStats_dict[opt_picks[match_loc]]
                fighters = list(matchup_dicts.keys())
                total_salary -= matchup_dicts[fighters[fighter_loc]]['Salary']
                fighter_picks.append(fighters[fighter_loc])
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
            n_picks.append(fighter_picks + best_pick)
        file = open(self.ufcstats_event_loc + '/picks/pick_n_ways.csv', 'w+', newline='')
        with file:
            write = csv.writer(file)
            write.writerows(n_picks)

    def greedy_pick(self):
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
        file = open(self.ufcstats_event_loc + '/picks/greedy_pick.csv', 'w+', newline='')

        with file:
            write = csv.writer(file)
            write.writerows([best_pick])

    def load_and_process_odds(self):
        """Get the DK odds from CSV"""
        filename = self.odds_json_loc
        with open(filename) as f:  # open in readonly mode
            dk_odds = json.load(f)
        # what if missing odds?
        # for name in list(dk_odds.keys()):
        #     print(name,dk_odds[name])
        return dk_odds

    # def scrape_bloodyelbow_staffpicks(self):
    #     # if no staff picks a fighter, than opp is good pick?
    #     if self.bloodyelbow_webpage:
    #         process = CrawlerProcess()
    #         process.crawl(BloodyElbowSpider, domain=[self.bloodyelbow_webpage])
    #         process.start()

    # def load_staffpicks(self):
    #     dir_name = os.getcwd() + '/' + self.bloodyelbow_loc
    #     # Load and combine dictionaries
    #     for filename in os.listdir(dir_name):
    #         # print(filename)
    #         with open(os.path.join(dir_name, filename)) as f:  # open in readonly mode
    #             # print(f.read())
    #             self.staffpicks_dict = json.load(f)  # print(matchup_dict)
    #
    # def process_staffpicks(self):
    #     names_staffpicks = list(self.staffpicks_dict.keys())
    #     for name in self.FIGHTERS_OUT:
    #         names_staffpicks.remove(name)
    #     names_staffpicks_copy = names_staffpicks
    #
    #     new_dict = {}
    #     # print(names_staffpicks)
    #     # print(self.fighter_names)
    #     for name in names_staffpicks:
    #         for fullname in self.fighter_names:
    #             if name in fullname:
    #                 # print(name,fullname)
    #                 new_dict[fullname] = self.staffpicks_dict[name]
    #                 names_staffpicks_copy.remove(name)
    #                 break
    #             else:
    #                 print(name, fullname)
    #     # print(names_staffpicks_copy)
    #     # print(new_dict.keys())

    # def add_staffpicks(self):
    #     pass

if __name__ == '__main__':
    pass
