import json
import re
import csv

import urllib.request as urllib2

from bs4 import BeautifulSoup
from datetime import timezone
from dateutil import parser
from os import path
from decimal import Decimal

contest = 'https://www.draftkings.com/draft/contest/94236810'

def get_dk_payout(contest_url):
    """Retrieve html and save if not already done. Parse html and return"""
    contest_id = contest_url.split('/')[-1]
    save_loc = "DraftKings/Contest_HTML/contest_" + str(contest_id) + ".html"
    if not path.exists(save_loc):
        print('Scraping DK Site')
        urllib2.urlretrieve(contest_url, save_loc)

    return BeautifulSoup(open(save_loc), 'html.parser')

soup_dk = get_dk_payout(contest)

payout_text = soup_dk.find(string=re.compile("window.mvcVars.contests"))
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
    payout_list.append([d['minPosition'], d['maxPosition'],Decimal(re.sub(r'[^\d.]', '',d['tierPayoutDescriptions']['Cash']))])

payout_list[1].append(entry_fee)
print(payout_list)
date_UTC = parser.isoparse(date)
date_my_timezone = date_UTC.replace(tzinfo=timezone.utc).astimezone(tz=None)
date_str = str(date_my_timezone.year) + str(date_my_timezone.month) + str(date_my_timezone.day)

salary_csv_loc = 'DraftKings/Salary_CSV/DKSalaries_UFC_full_card_' + date_str + '.csv'
payout_csv_loc = 'DraftKings/Payout_CSV/DKPayout_UFC_full_card_' + date_str + '.csv'

if not path.exists(salary_csv_loc):
    print('Beginning file download with urllib2...')
    url = 'https://www.draftkings.com/lineup/getavailableplayerscsv?contestTypeId=' + str(contestTypeId) + \
          '&draftGroupId=' + str(draftGroupId)
    urllib2.urlretrieve(url, salary_csv_loc)


if not path.exists(payout_csv_loc):
    with open(payout_csv_loc, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(payout_list)