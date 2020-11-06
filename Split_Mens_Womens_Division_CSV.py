# Issue with catchweight bouts...no identification as womens or mens.
import json
import pandas as pd
from os import listdir, getcwd
from os.path import isfile, join

path_all_events = getcwd() + '/UFCStats_Dicts/All_Events/'
path_processed_events = getcwd() + '/UFCStats_Dicts/Processed/'
processed_men_filename = 'All_Mens_Fights.csv'
processed_women_filename = 'All_Womens_Fights.csv'
only_files = [f for f in listdir(path_all_events) if isfile(join(path_all_events, f)) and not f.startswith('.')]

m_event_name = []
m_event_date = []
m_bout_type = []
m_weight_class = []
m_bonus_type = []
m_bonus = []
m_title = []
m_method = []
m_position_on_card = []
m_round_seen = []
m_round_time = []
m_round_format = []
m_fighter_1_name = []
m_fighter_2_name = []
m_fighter_1_outcome = []
m_fighter_2_outcome = []
m_sex = []

w_event_name = []
w_event_date = []
w_bout_type = []
w_weight_class = []
w_bonus_type = []
w_bonus = []
w_title = []
w_method = []
w_position_on_card = []
w_round_seen = []
w_round_time = []
w_round_format = []
w_fighter_1_name = []
w_fighter_2_name = []
w_fighter_1_outcome = []
w_fighter_2_outcome = []
w_sex = []

catchweight_paths = []
catchweight_fighter_1 = []
catchweight_fighter_2 = []


def find_weight_class(wc_str):
    """Determine the weight class of a fight by finding substring.
    Args:
        wc_str (str)

    Return:
        str
    Notes:
        If the weight class cannot be determined, the output will be 'UNKNOWN'.
    """

    wcs = ['Strawweight', 'Flyweight', 'Bantamweight', 'Featherweight', 'Lightweight', 'Welterweight', 'Middleweight',
           'Light Heavyweight', 'Heavyweight', 'Open Weight', 'Tournament', 'Superfight']
    for wc in wcs:
        if wc_str.find(wc) >= 0:
            return wc
    return 'UNKNOWN'


for event_path in only_files:
    with open(join(path_all_events, event_path)) as json_file:
        data = json.load(json_file)
        n_fights = data['FightCount']
        for fight_idx in range(1, n_fights + 1):
            fight_idx_str = str(fight_idx)
            if data[fight_idx_str]['WeightClass'].lower().find('catch weight') >= 0:
                catchweight_paths.append(event_path)
                catchweight_fighter_1.append(data[fight_idx_str]['Fighter_1']['Name'])
                catchweight_fighter_2.append(data[fight_idx_str]['Fighter_2']['Name'])
            elif data[fight_idx_str]['WeightClass'].lower().find('women') >= 0:
                w_position_on_card.append(fight_idx_str + ' of ' + str(n_fights))
                w_event_name.append(data['EventName'])
                w_event_date.append(data['EventDate'])
                w_bout_type.append(data[fight_idx_str]['WeightClass'])
                w_weight_class.append(find_weight_class(data[fight_idx_str]['WeightClass']))
                w_sex.append('F')
                w_bonus.append(data[fight_idx_str]['Bonus'])
                w_bonus_type.append(data[fight_idx_str]['BonusType'])
                w_title.append(data[fight_idx_str]['TitleFight'])
                w_method.append(data[fight_idx_str]['Method'])
                w_round_seen.append(data[fight_idx_str]['Round'])
                w_round_time.append(data[fight_idx_str]['RoundTime'])
                w_round_format.append(data[fight_idx_str]['RoundFormat'])
                w_fighter_1_name.append(data[fight_idx_str]['Fighter_1']['Name'])
                w_fighter_1_outcome.append(data[fight_idx_str]['Fighter_1']['Outcome'])
                w_fighter_2_name.append(data[fight_idx_str]['Fighter_2']['Name'])
                w_fighter_2_outcome.append(data[fight_idx_str]['Fighter_2']['Outcome'])
            else:
                m_position_on_card.append(fight_idx_str + ' of ' + str(n_fights))
                m_event_name.append(data['EventName'])
                m_event_date.append(data['EventDate'])
                m_bout_type.append(data[fight_idx_str]['WeightClass'])
                m_weight_class.append(find_weight_class(data[fight_idx_str]['WeightClass']))
                m_sex.append('M')
                m_bonus.append(data[fight_idx_str]['Bonus'])
                m_bonus_type.append(data[fight_idx_str]['BonusType'])
                m_title.append(data[fight_idx_str]['TitleFight'])
                m_method.append(data[fight_idx_str]['Method'])
                m_round_seen.append(data[fight_idx_str]['Round'])
                m_round_time.append(data[fight_idx_str]['RoundTime'])
                m_round_format.append(data[fight_idx_str]['RoundFormat'])
                m_fighter_1_name.append(data[fight_idx_str]['Fighter_1']['Name'])
                m_fighter_1_outcome.append(data[fight_idx_str]['Fighter_1']['Outcome'])
                m_fighter_2_name.append(data[fight_idx_str]['Fighter_2']['Name'])
                m_fighter_2_outcome.append(data[fight_idx_str]['Fighter_2']['Outcome'])

women_names = set(w_fighter_1_name + w_fighter_2_name)
men_names = set(m_fighter_1_name + m_fighter_2_name)

for i, event_path in enumerate(catchweight_paths):
    with open(join(path_all_events, event_path)) as json_file:
        data = json.load(json_file)
        n_fights = data['FightCount']
        # print(event_path, n_fights)
        w_name = [f for f in women_names if (f == catchweight_fighter_1[i]) or (f == catchweight_fighter_2[i])]
        for fight_idx in range(1, n_fights + 1):
            fight_idx_str = str(fight_idx)
            name_1 = data[fight_idx_str]['Fighter_1']['Name']
            name_2 = data[fight_idx_str]['Fighter_2']['Name']
            # must be careful to avoid other catch weight bouts at event.
            if (name_1 in w_name) or (name_2 in w_name):
                # print(w1_name, w2_name)
                w_position_on_card.append(fight_idx_str + ' of ' + str(n_fights))
                w_event_name.append(data['EventName'])
                w_event_date.append(data['EventDate'])
                w_bout_type.append("Women\'s " + data[fight_idx_str]['WeightClass'])
                w_weight_class.append("Catch Weight")
                w_sex.append('F')
                w_bonus.append(data[fight_idx_str]['Bonus'])
                w_bonus_type.append(data[fight_idx_str]['BonusType'])
                w_title.append(data[fight_idx_str]['TitleFight'])
                w_method.append(data[fight_idx_str]['Method'])
                w_round_seen.append(data[fight_idx_str]['Round'])
                w_round_time.append(data[fight_idx_str]['RoundTime'])
                w_round_format.append(data[fight_idx_str]['RoundFormat'])
                w_fighter_1_name.append(data[fight_idx_str]['Fighter_1']['Name'])
                w_fighter_1_outcome.append(data[fight_idx_str]['Fighter_1']['Outcome'])
                w_fighter_2_name.append(data[fight_idx_str]['Fighter_2']['Name'])
                w_fighter_2_outcome.append(data[fight_idx_str]['Fighter_2']['Outcome'])
                break
            elif data[fight_idx_str]['WeightClass'].lower().find('catch weight') >= 0:
                # Assuming male if not confirmed female.
                # This has to potential to misidentify women fighters as men if both fighters have not had UFC fights
                # that did not occur at catch weight. There is one case of men fighters where this happens:
                # Valiev vs. Jones
                m_position_on_card.append(fight_idx_str + ' of ' + str(n_fights))
                m_event_name.append(data['EventName'])
                m_event_date.append(data['EventDate'])
                m_bout_type.append(data[fight_idx_str]['WeightClass'])
                m_weight_class.append("Catch Weight")
                m_sex.append('M')
                m_bonus.append(data[fight_idx_str]['Bonus'])
                m_bonus_type.append(data[fight_idx_str]['BonusType'])
                m_title.append(data[fight_idx_str]['TitleFight'])
                m_method.append(data[fight_idx_str]['Method'])
                m_round_seen.append(data[fight_idx_str]['Round'])
                m_round_time.append(data[fight_idx_str]['RoundTime'])
                m_round_format.append(data[fight_idx_str]['RoundFormat'])
                m_fighter_1_name.append(data[fight_idx_str]['Fighter_1']['Name'])
                m_fighter_1_outcome.append(data[fight_idx_str]['Fighter_1']['Outcome'])
                m_fighter_2_name.append(data[fight_idx_str]['Fighter_2']['Name'])
                m_fighter_2_outcome.append(data[fight_idx_str]['Fighter_2']['Outcome'])
                break


d_w = {'EventName': w_event_name,
       'EventDate': w_event_date,
       'BoutType': w_bout_type,
       'WeightClass': w_weight_class,
       'Sex': w_sex,
       'Bonus': w_bonus,
       'BonusType': w_bonus_type,
       'TitleFight': w_title,
       'Method': w_method,
       'Round': w_round_seen,
       'RoundTime': w_round_time,
       'RoundFormat': w_round_format,
       'FighterName1': w_fighter_1_name,
       'FighterName2': w_fighter_2_name,
       'FighterOutcome1': w_fighter_1_outcome,
       'FighterOutcome2': w_fighter_2_outcome,
       'CardPosition': w_position_on_card}

d_m = {'EventName': m_event_name,
       'EventDate': m_event_date,
       'BoutType': m_bout_type,
       'WeightClass': m_weight_class,
       'Sex': m_sex,
       'Bonus': m_bonus,
       'BonusType': m_bonus_type,
       'TitleFight': m_title,
       'Method': m_method,
       'Round': m_round_seen,
       'RoundTime': m_round_time,
       'RoundFormat': m_round_format,
       'FighterName1': m_fighter_1_name,
       'FighterName2': m_fighter_2_name,
       'FighterOutcome1': m_fighter_1_outcome,
       'FighterOutcome2': m_fighter_2_outcome,
       'CardPosition': m_position_on_card}

df = pd.DataFrame(data=d_w)
df['EventDate'] = pd.to_datetime(df['EventDate'])
df.sort_values(by='EventDate', inplace=True)
df.to_csv(join(path_processed_events, processed_women_filename), index=False)

df = pd.DataFrame(data=d_m)
df['EventDate'] = pd.to_datetime(df['EventDate'])
df.sort_values(by='EventDate', inplace=True)
df.to_csv(join(path_processed_events, processed_men_filename), index=False)
