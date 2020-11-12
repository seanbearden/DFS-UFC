from Event import Event
from Scrape import Scrape

card_id = 'UFC_full_card_20201114'
# change Scrape to automatically detect next event at UFCStats.com.
# can this be done for Sherdog.com?
# dk_odds_url does not seem to change between events. Utilize that...
scrape_kwargs = {'ufcstats_event_url': 'http://ufcstats.com/event-details/3bc27ec15facbcf3',
                 'sherdog_event_url': 'https://www.sherdog.com/events/UFC-Fight-Night-182-Felder-vs-Dos-Anjos-87393',
                 'dk_event_url': 'https://www.draftkings.com/draft/contest/96166762',
                 'dk_odds_url': 'https://sportsbook.draftkings.com/leagues/mma/2162?category=fight-lines&subcategory=moneyline',
                 'card_id': card_id,
                 'rescrape_dk': False}
Scrape(**scrape_kwargs)


override_stats = {}
forced_matchups = []

event_kwargs = {'card_id': card_id,
                'forced_matchups': [],
                'override_stats': {}}
event = Event(**event_kwargs)