from Event import Event
from Scrape import Scrape

card_id = 'UFC_full_card_20201107'
# change Scrape to automatically detect next event at UFCStats.com.
# can this be done for Sherdog.com?
# dk_odds_url does not seem to change between events. Utilize that...
scrape_kwargs = {'ufcstats_event_url': 'http://ufcstats.com/event-details/41dca66f9dadfc86',
                 'sherdog_event_url': 'https://www.sherdog.com/events/UFC-on-ESPN-17-Santos-vs-Teixeira-87362',
                 'dk_event_url': 'https://www.draftkings.com/draft/contest/95695151',
                 'dk_odds_url': 'https://sportsbook.draftkings.com/leagues/mma/2162?category=fight-lines&subcategory=moneyline',
                 'card_id': card_id}
Scrape(**scrape_kwargs)


override_stats = {}
forced_matchups = []

event_kwargs = {'card_id': card_id,
                'forced_matchups': [],
                'override_stats': {}}
event = Event(**event_kwargs)