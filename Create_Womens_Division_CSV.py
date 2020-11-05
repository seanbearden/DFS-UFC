import json
import pandas as pd
from os import listdir, getcwd
from os.path import isfile, join

path_all_events = getcwd() + '/UFCStats_Dicts/All_Events/'
path_processed_events = getcwd() + '/UFCStats_Dicts/Processed/'
processed_filename = 'All_Womens_Fights.csv'
only_files = [f for f in listdir(path_all_events) if isfile(join(path_all_events, f)) and not f.startswith('.')]

event_name = []
event_date = []
weight_class = []
bonus_type = []
bonus = []
title = []
method = []
position_on_card = []
round_seen = []
round_time = []
round_format = []
fighter_1_name = []
fighter_2_name = []
fighter_1_outcome = []
fighter_2_outcome = []

for event_path in only_files:
    with open(join(path_all_events, event_path)) as json_file:
        data = json.load(json_file)
        n_fights = data['FightCount']
        for fight_idx in range(1, n_fights + 1):
            fight_idx_str = str(fight_idx)
            if data[fight_idx_str]['WeightClass'].lower().find('women') >= 0:
                position_on_card.append(fight_idx_str + ' of ' + str(n_fights))
                event_name.append(data['EventName'])
                event_date.append(data['EventDate'])
                weight_class.append(data[fight_idx_str]['WeightClass'])
                bonus.append(data[fight_idx_str]['Bonus'])
                bonus_type.append(data[fight_idx_str]['BonusType'])
                title.append(data[fight_idx_str]['TitleFight'])
                method.append(data[fight_idx_str]['Method'])
                round_seen.append(data[fight_idx_str]['Round'])
                round_time.append(data[fight_idx_str]['RoundTime'])
                round_format.append(data[fight_idx_str]['RoundFormat'])
                fighter_1_name.append(data[fight_idx_str]['Fighter_1']['Name'])
                fighter_1_outcome.append(data[fight_idx_str]['Fighter_1']['Outcome'])
                fighter_2_name.append(data[fight_idx_str]['Fighter_2']['Name'])
                fighter_2_outcome.append(data[fight_idx_str]['Fighter_2']['Outcome'])

d = {'EventName': event_name,
     'EventDate': event_date,
     'WeightClass': weight_class,
     'Bonus': bonus,
     'BonusType': bonus_type,
     'TitleFight': title,
     'Method': method,
     'Round': round_seen,
     'RoundTime': round_time,
     'RoundFormat': round_format,
     'FighterName1': fighter_1_name,
     'FighterName2': fighter_2_name,
     'FighterOutcome1': fighter_1_outcome,
     'FighterOutcome2': fighter_2_outcome,
     'CardPosition': position_on_card}

df = pd.DataFrame(data=d)

df['EventDate'] = pd.to_datetime(df['EventDate'])
df.sort_values(by='EventDate', inplace=True)
df['WeightClass'] = df['WeightClass'].str.replace('UFC Women\'s Bantamweight Title Bout', 'Women\'s Bantamweight Bout')
df['WeightClass'] = df['WeightClass'].str.replace('UFC Women\'s Strawweight Title Bout', 'Women\'s Strawweight Bout')
df['WeightClass'] = df['WeightClass'].str.replace('UFC Women\'s Flyweight Title Bout', 'Women\'s Flyweight Bout')
df['WeightClass'] = df['WeightClass'].str.replace('UFC Women\'s Featherweight Title Bout', 'Women\'s Featherweight Bout')
df['WeightClass'] = df['WeightClass'].str.replace('Ultimate Fighter 18 Women\'s Bantamweight Tournament Title Bout', 'Women\'s Bantamweight Bout')
df['WeightClass'] = df['WeightClass'].str.replace('Ultimate Fighter 23 Women\'s Strawweight Tournament Title Bout', 'Women\'s Strawweight Bout')
df['WeightClass'] = df['WeightClass'].str.replace('Ultimate Fighter 28 Women\'s Featherweight Tournament Title Bout', 'Women\'s Featherweight Bout')

df.to_csv(join(path_processed_events, processed_filename), index=False)
