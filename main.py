from Event import Event

card = 'UFC_full_card_20201017'
event_webpage_dk = ""
event_dk_salaries = "DraftKings/Salary_CSV/DKSalaries_"+card+".csv"
event_webpage_ufcstats = "http://ufcstats.com/event-details/d4f364dd076bb0e2"
UFCStats_loc = "UFCStats_Dicts/" + card
bloodyelbow_webpage = ""
bloodyelbow_loc = "BloodyElbow_StaffPicks"
sherdog_webpage = "https://www.sherdog.com/events/UFC-Fight-Night-180-Ortega-vs-Korean-Zombie-87277"
sherdog_loc = "Sherdog_Dicts/" + card
odds_webpage= 'https://sportsbook.draftkings.com/leagues/mma/2162?category=fight-lines&subcategory=moneyline'
override_stats = {}#{'Tagir Ulanbekov': 90,'Edson Barboza':80,'Youssef Zalal':40,'Bruno Silva':0}
forced_picks = []#['Marlon Moraes vs. Cory Sandhagen','Edson Barboza vs. Makwan Amirkhani']

event = Event(event_webpage_dk, event_webpage_ufcstats, UFCStats_loc, event_dk_salaries, "", bloodyelbow_loc, override_stats, forced_picks,
              sherdog_webpage, sherdog_loc,odds_webpage)