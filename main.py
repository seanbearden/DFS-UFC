from Event import Event
from Scrape import Scrape

card_id = 'UFC_full_card_20201024'
scrape_kwargs = {'ufcstats_event_url': 'http://ufcstats.com/event-details/c3c38c86f5ab9b5c',
                 'sherdog_event_url': 'https://www.sherdog.com/events/UFC-254-Nurmagomedov-vs-Gaethje-87041',
                 'dk_event_url': 'https://www.draftkings.com/draft/contest/93995953',
                 'dk_odds_url': 'https://sportsbook.draftkings.com/leagues/mma/2162?category=fight-lines&subcategory=moneyline',
                 'card_id': card_id}
Scrape(**scrape_kwargs)


override_stats = {}#{'Tagir Ulanbekov': 90,'Edson Barboza':80,'Youssef Zalal':40,'Bruno Silva':0}
forced_matchups = []#['Marlon Moraes vs. Cory Sandhagen','Edson Barboza vs. Makwan Amirkhani']

event_kwargs = {'card_id': card_id,
                'forced_matchups': [],
                'override_stats': {}}
event = Event(**event_kwargs)