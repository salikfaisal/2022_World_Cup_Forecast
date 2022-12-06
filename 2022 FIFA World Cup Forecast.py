import sys
import random
import statistics
from bs4 import BeautifulSoup
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# finds the local file for your computer for the webdriver
# this is commented out because it is not needed after one run and is different for every user
# sys.path.append('C:\\Users\\ppp\\Selenium\\chromedriver_win32\\chromedriver.exe')

# gets the website where the elo ratings are located
driver.get('http://www.eloratings.net/')
# waits 10 seconds for the website to load
driver.implicitly_wait(10)

# uses XPath to scrape data
odd_ranked_teams = driver.find_elements(By.XPATH,
                                        "//div[@id='main']/div[@id='maindiv']/div[@id='maintable_World']/div[@class='slick-viewport']/div[@class='grid-canvas']/div[@class='ui-widget-content slick-row even']")
even_ranked_teams = driver.find_elements(By.XPATH,
                                         "//div[@id='main']/div[@id='maindiv']/div[@id='maintable_World']/div[@class='slick-viewport']/div[@class='grid-canvas']/div[@class='ui-widget-content slick-row odd']")
# Translates HTML to text and stores national elo ratings into a dictionary
team_elo_ratings = {}
for team in odd_ranked_teams:
    widget_content = team.text.split()
    country_name = ''
    for column_num, column in enumerate(widget_content):
        if column_num > 0 and column.isnumeric():
            team_rating = int(column)
            words_in_country_name = widget_content[1:column_num]
            country_name = ' '.join(words_in_country_name)
            team_elo_ratings.update({country_name: team_rating})
            break
for team in even_ranked_teams:
    widget_content = team.text.split()
    country_name = ''
    for column_num, column in enumerate(widget_content):
        if column_num > 0 and column.isnumeric():
            team_rating = int(column)
            words_in_country_name = widget_content[1:column_num]
            country_name = ' '.join(words_in_country_name)
            team_elo_ratings.update({country_name: team_rating})
            break
driver.quit()

# gets SPI ratings from ESPN/FiveThirtyEight
url = 'https://projects.fivethirtyeight.com/soccer-api/international/spi_global_rankings_intl.csv'
spi_data = requests.get(url).text.split(',')[6:]
spi_dict = {}

# changes SPi names to elo names if conflicting
spi_to_elo_change = {'USA': 'United States', 'Bosnia and Herzegovina': 'Bosnia/Herzegovina',
                     'United Arab Emirates': 'UAE', 'Swaziland': 'Eswatini', 'Antigua and Barbuda': 'Antigua & Barbuda',
                     'Sao Tome and Principe': 'São Tomé & Príncipe',
                     'St. Vincent and the Grenadines': 'St Vincent/Gren', 'Chinese Taipei': 'Taiwan',
                     'Timor-Leste': 'East Timor', 'Czech Republic': 'Czechia', 'Rep of Ireland': 'Ireland',
                     'Cape Verde Islands': 'Cape Verde', 'China PR': 'China', 'Congo DR': 'DR Congo',
                     'Curacao': 'Curaçao', 'Central African Republic': 'Central African Rep',
                     'St. Kitts and Nevis': 'Saint Kitts and Nevis', 'St. Lucia': 'Saint Lucia',
                     'St. Martin': 'Saint Martin', 'Turks and Caicos Islands': 'Turks and Caicos', 'Macau': 'Macao'
                     }
for item_num, item in enumerate(spi_data):
    if item_num % 5 == 0:
        rating = float(spi_data[item_num + 4].split()[0])
        elo_adjusted_rating = 1000 + 10 * rating
        if item in spi_to_elo_change:
            item = spi_to_elo_change[item]
        spi_dict.update({item: elo_adjusted_rating})

# combines SPI and world elo ratings
for team, elo_rating in team_elo_ratings.items():
    if team in ['Northern Cyprus', 'Kurdistan', 'Réunion', 'Saint Barthélemy', 'Wallis and Futuna', 'Vatican',
                'Falkland Islands', 'Eastern Samoa', 'Palau', 'Mayotte', 'Somaliland', 'Western Sahara', 'Greenland',
                'Monaco', 'Chagos Islands', 'St Pierre & Miquelon', 'Tibet', 'FS Micronesia', 'Kiribati',
                'Northern Marianas', 'Niue']:
        continue
        # this is because there is no SPI rating for these countries, and they are not officially FIFA members
    spi_elo = spi_dict[team]
    new_rating = (elo_rating + spi_elo) / 2
    team_elo_ratings.update({team: new_rating})

# This updates Qatar's elo rating to reflect its home advantage
qatar_original_elo = team_elo_ratings['Qatar']
team_elo_ratings.update({'Qatar': qatar_original_elo + 100})


# this function returns a simulation of the results of a game given the elo ratings of the two teams
def match_result(team_1_elo, team_2_elo):
    # uses the elo formula to get the two-outcome win probability
    team_1_wl = 1 / (10 ** ((team_2_elo - team_1_elo) / 400) + 1)
    # gets the average goal difference expected between the two sides
    # if two sides have an equal rating the probabilities are: 35% Team 1 win, 30% draw, 35% Team 2 win
    team_1_margin_mean = statistics.NormalDist(0, 1.3).inv_cdf(team_1_wl)
    # the goal difference as a result of a random simulation
    team_1_margin = round(statistics.NormalDist(team_1_margin_mean, 1.3).inv_cdf(random.random()))
    # the goal probability distribution from 1826 matches in the 2020-21 season in Europe's top 5 leagues
    goal_prob = [0.25985761226725085, 0.3417305585980285, 0.22343921139101863, 0.1119934282584885, 0.0443592552026287,
                 0.014786418400876232, 0.0024644030668127055, 0.0008214676889375684, 0.0002738225629791895,
                 0.0002738225629791895]
    gp_list = []
    if abs(team_1_margin) > 9:
        winning_goal_count = abs(team_1_margin)
        losing_goal_count = 0
    else:
        gp_list = goal_prob[abs(team_1_margin):]
        total = sum(gp_list)
        cum = 0
        for goal_count, goal_probability in enumerate(gp_list):
            gp_list[goal_count] = goal_probability / total
        goal_result = random.random()
        for gc, gp in enumerate(gp_list):
            cum += gp
            if goal_result < cum:
                winning_goal_count = gc + abs(team_1_margin)
                winning_goal_count = gc + abs(team_1_margin)
                losing_goal_count = winning_goal_count - abs(team_1_margin)
                break
    if team_1_margin >= 0:
        home_goals = winning_goal_count
        away_goals = home_goals - team_1_margin
    else:
        away_goals = winning_goal_count
        home_goals = away_goals + team_1_margin
    return [home_goals, away_goals]


# World Cup groups initialized
groups = [['Qatar', 'Ecuador', 'Senegal', 'Netherlands'], ['England', 'Iran', 'United States', 'Wales'],
          ['Argentina', 'Saudi Arabia', 'Mexico', 'Poland'], ['France', 'Australia', 'Denmark', 'Tunisia'],
          ['Spain', 'Costa Rica', 'Germany', 'Japan'], ['Belgium', 'Canada', 'Morocco', 'Croatia'],
          ['Brazil', 'Serbia', 'Switzerland', 'Cameroon'], ['Portugal', 'Ghana', 'Uruguay', 'South Korea']]
wc_summary = []
group_summary = {}
for group_number, group in enumerate(groups):
    for team in group:
        wc_summary.append([team, 0, 0, 0, 0, 0, chr(65 + group_number)])
        group_summary.update({team: [0, 0, 0, 0, 0, 0, chr(65 + group_number)]})


# A class for functions used for the Group Stage
class group_stage:
    def __init__(self, group):
        self.group = group

    # This function returns a list of all the Group State matches already completed
    def matches_completed(self):
        matches_completed = [['Qatar', 'Ecuador', 0, 2], ['Senegal', 'Netherlands', 0, 2], ['England', 'Iran', 6, 2],
                             ['United States', 'Wales', 1, 1], ['Argentina', 'Saudi Arabia', 1, 2],
                             ['Denmark', 'Tunisia', 0, 0], ['Mexico', 'Poland', 0, 0], ['France', 'Australia', 4, 1],
                             ['Morocco', 'Croatia', 0, 0], ['Germany', 'Japan', 1, 2], ['Spain', 'Costa Rica', 7, 0],
                             ['Belgium', 'Canada', 1, 0], ['Switzerland', 'Cameroon', 1, 0],
                             ['Uruguay', 'South Korea', 0, 0], ['Portugal', 'Ghana', 3, 2], ['Brazil', 'Serbia', 2, 0],
                             ['Wales', 'Iran', 0, 2], ['Qatar', 'Senegal', 1, 3], ['Netherlands', 'Ecuador', 1, 1],
                             ['England', 'United States', 0, 0], ['Tunisia', 'Australia', 0, 1],
                             ['Poland', 'Saudi Arabia', 2, 0], ['France', 'Denmark', 2, 1],
                             ['Argentina', 'Mexico', 2, 0], ['Japan', 'Costa Rica', 0, 1], ['Belgium', 'Morocco', 0, 2],
                             ['Croatia', 'Canada', 4, 1], ['Spain', 'Germany', 1, 1], ['Cameroon', 'Serbia', 3, 3],
                             ['South Korea', 'Ghana', 2, 3], ['Brazil', 'Switzerland', 1, 0],
                             ['Portugal', 'Uruguay', 2, 0], ['Ecuador', 'Senegal', 1, 2],
                             ['Netherlands', 'Qatar', 2, 0], ['Iran', 'United States', 0, 1],
                             ['Wales', 'England', 0, 3], ['Tunisia', 'France', 1, 0], ['Australia', 'Denmark', 1, 0],
                             ['Poland', 'Argentina', 0, 2], ['Saudi Arabia', 'Mexico', 1, 2],
                             ['Croatia', 'Belgium', 0, 0], ['Canada', 'Morocco', 1, 2], ['Japan', 'Spain', 2, 1],
                             ['Costa Rica', 'Germany', 2, 4], ['Cameroon', 'Brazil', 1, 0],
                             ['Serbia', 'Switzerland', 2, 3], ['Ghana', 'Uruguay', 0, 2],
                             ['South Korea', 'Portugal', 2, 1]
                             ]

        return matches_completed

    # This function returns the various matchups within a particular group
    def group_matches(self):
        matches = []
        for team_1_pos, team_1 in enumerate(self.group):
            for team_2_pos, team_2 in enumerate(self.group):
                if team_1_pos < team_2_pos:
                    matches.append([team_1, team_2])
        return matches

    # This function returns the elo ratings for each team in a Group Stage match
    def match_ratings(self):
        matches = self.group_matches()
        ratings = []
        for match in matches:
            rating = []
            for team_number, team in enumerate(match):
                rating.append(team_elo_ratings[team])
            ratings.append(rating)
        return ratings

    # This function returns a final simulated group
    def group_simulation(self):
        table = {}
        group_ratings = self.match_ratings()
        matches_completed = self.matches_completed()
        for team in self.group:
            table.update({team: [0, 0, 0, 0]})
        match_results = []
        for match_number, match in enumerate(self.group_matches()):
            simulation_needed = True
            rating = group_ratings[match_number]
            team_1_standings = table[match[0]]
            team_2_standings = table[match[1]]
            for finished_match in matches_completed:
                # This checks to see if the match has already been played
                if match[0] in finished_match and match[1] in finished_match:
                    simulation_needed = False
                    if match[0] == finished_match[0]:
                        result = finished_match[2:]
                    else:
                        result = [finished_match[3], finished_match[2]]
                    break
            # This simulates the match if it has not been played yet
            if simulation_needed:
                result = match_result(rating[0], rating[1])
            match_results.append(result)
            # This updates the standings to reflect the match
            if result[0] > result[1]:
                team_1_standings[0] = team_1_standings[0] + 3
            elif result[0] == result[1]:
                team_1_standings[0] = team_1_standings[0] + 1
                team_2_standings[0] = team_2_standings[0] + 1
            else:
                team_2_standings[0] = team_2_standings[0] + 3
            team_1_standings[1] += result[0]
            team_2_standings[1] += result[1]
            team_1_standings[2] += result[1]
            team_2_standings[2] += result[0]
            team_1_standings[3] = team_1_standings[1] - team_1_standings[2]
            team_2_standings[3] = team_2_standings[1] - team_2_standings[2]
            table[match[0]] = team_1_standings
            table[match[1]] = team_2_standings
        standings = []
        for team in table:
            standing = [team]
            standing.extend(table[team])
            standings.append(standing)
        standings = sorted(standings, key=lambda data: (data[1], data[4], data[2]), reverse=True)
        return standings


# A class for functions used during the knockout stage
class knockout_stage:
    # This sets the matchups for the knockout stage based on the results of the Group Stage
    def __init__(self, group_winners, group_runners_up):
        round_of_16_matchups = [[0, 1], [2, 3], [4, 5], [6, 7], [1, 0], [3, 2], [5, 4], [7, 6]]
        for match_number, match in enumerate(round_of_16_matchups):
            matchup = [group_winners[match[0]], group_runner_ups[match[1]]]
            round_of_16_matchups[match_number] = matchup
        self.round_of_16_matchups = round_of_16_matchups

    # This returns the nations that advanced to the quarterfinals through simulations or returns the actual quarterfinalists 
    # if the matches have been completed
    def round_of_16(self):
        r16_matchups = self.round_of_16_matchups
        quarterfinalists = ['Netherlands', 'Argentina', 'Croatia', 'Brazil', 'England', 'France', 'Morocco', 'Portugal']
        # # The quarterfinalists have already been determined
        # for match in r16_matchups:
        #     team_1_elo = team_elo_ratings[match[0]]
        #     team_2_elo = team_elo_ratings[match[1]]
        #     result = match_result(team_1_elo, team_2_elo)
        #     if result[0] > result[1]:
        #         quarterfinalists.append(match[0])
        #     elif result[0] < result[1]:
        #         quarterfinalists.append(match[1])
        #     else:
        #         quarterfinalists.append(match[random.randrange(0, 2)])
        return quarterfinalists

    # This returns the nations that advanced to the quarterfinals and semifinals through simulations or returns the actual 
    # quarterfinalists add semifinalists if the matches have been completed
    def quarterfinals(self):
        quarterfinalists = self.round_of_16()
        semifinalists = []
        qf_matches = []
        qf_match = []
        for team in quarterfinalists:
            qf_match.append(team)
            if len(qf_match) == 2:
                qf_matches.append(qf_match)
                qf_match = []
        for match in qf_matches:
            team_1_elo = team_elo_ratings[match[0]]
            team_2_elo = team_elo_ratings[match[1]]
            result = match_result(team_1_elo, team_2_elo)
            if result[0] > result[1]:
                semifinalists.append(match[0])
            elif result[0] < result[1]:
                semifinalists.append(match[1])
            else:
                semifinalists.append(match[random.randrange(0, 2)])
        return quarterfinalists, semifinalists

    # This returns the nations that advanced to the quarterfinals, semifinals, and final through simulations or returns the actual 
    # quarterfinalists, semifinalists, and finalists if the matches have been completed
    def semifinals(self):
        quarterfinalists, semifinalists = self.quarterfinals()
        finalists = []
        sf_matches = []
        sf_match = []
        for team in semifinalists:
            sf_match.append(team)
            if len(sf_match) == 2:
                sf_matches.append(sf_match)
                sf_match = []
        for match in sf_matches:
            team_1_elo = team_elo_ratings[match[0]]
            team_2_elo = team_elo_ratings[match[1]]
            result = match_result(team_1_elo, team_2_elo)
            if result[0] > result[1]:
                finalists.append(match[0])
            elif result[0] < result[1]:
                finalists.append(match[1])
            else:
                finalists.append(match[random.randrange(0, 2)])
        return quarterfinalists, semifinalists, finalists

    # This returns the nations that advanced to the quarterfinals, semifinals, final, and champion through simulations
    # or returns the actual quarterfinalists, semifinalists, finalists and champions if the matches have been completed
    def world_cup_final(self):
        quarterfinalists, semifinalists, finalists = self.semifinals()
        team_1_elo = team_elo_ratings[finalists[0]]
        team_2_elo = team_elo_ratings[finalists[1]]
        result = match_result(team_1_elo, team_2_elo)
        if result[0] > result[1]:
            champion = finalists[0]
        elif result[0] < result[1]:
            champion = finalists[1]
        else:
            champion = finalists[random.randrange(0, 2)]
        return quarterfinalists, semifinalists, finalists, champion


# Simulates the World Cup 10,000 times and stores the information
for simulation in range(10000):
    group_winners = []
    group_runner_ups = []
    # Simulates the Group Stage and stores data for each Group
    for group in groups:
        group_sim = group_stage(group)
        group_sim_results = group_sim.group_simulation()
        for position, team in enumerate(group_sim_results):
            summary_info = group_summary[team[0]]
            summary_info[0] += team[1]
            summary_info[1] += team[4]
            summary_info[position + 2] += 1
            group_summary.update({team[0]: summary_info})
            if position == 0:
                group_winners.append(team[0])
            elif position == 1:
                group_runner_ups.append(team[0])
    # Reports Group Stage Results to Knockout Stage
    ks_sim = knockout_stage(group_winners, group_runner_ups)
    # Simulates Knockout Stage
    quarterfinalists, semifinalists, finalists, champion = ks_sim.world_cup_final()
    # for the purposes of extracting a random simulation
    # if simulation == 0:
    #     print('Round of 16')
    #     for matchup in ks_sim.round_of_16_matchups:
    #         print(matchup[0], 'vs', matchup[1])
    #     print()
    #     print('Quarterfinals')
    #     matchup = []
    #     for team in quarterfinalists:
    #         if len(matchup) != 2:
    #             matchup.append(team)
    #         if len(matchup) == 2:
    #             print(matchup[0], 'vs', matchup[1])
    #             matchup = []
    #     print()
    #     print('Semifinals')
    #     matchup = []
    #     for team in semifinalists:
    #         if len(matchup) != 2:
    #             matchup.append(team)
    #         if len(matchup) == 2:
    #             print(matchup[0], 'vs', matchup[1])
    #             matchup = []
    #     print()
    #     print('World Cup Final')
    #     print(finalists[0], 'vs', finalists[1])
    #     print()
    #     print('World Cup Champions:', champion)
    # Stores the results of the Knockout Stage
    for team in wc_summary:
        if team[0] == champion:
            team[1] += 1
            team[2] += 1
            team[3] += 1
            team[4] += 1
            team[5] += 1
        elif team[0] in finalists:
            team[1] += 1
            team[2] += 1
            team[3] += 1
            team[4] += 1
        elif team[0] in semifinalists:
            team[1] += 1
            team[2] += 1
            team[3] += 1
        elif team[0] in quarterfinalists:
            team[1] += 1
            team[2] += 1
        elif team[0] in group_winners or team[0] in group_runner_ups:
            team[1] += 1

group_sim_summary = []
for team, data in group_summary.items():
    team_info = [team]
    team_info.extend(data)
    group_sim_summary.append(team_info)
group_sim_summary = sorted(group_sim_summary, key=lambda data: ((data[3] + data[4]), data[3], data[4], data[5]),
                           reverse=True)
group_sim_summary = sorted(group_sim_summary, key=lambda data: data[7])
wc_summary = sorted(wc_summary, key=lambda data: (data[5], data[4], data[3], data[2], data[1]), reverse=True)

line_format = '{pos:^4}|{team:^15}|{Pts:^15}|{GD:^15}|{KS:^10}|{First:^7}|{Second:^7}|{Third:^7}|{Fourth:^7}|'
group_format = '{group:^95}'

for team_number, team_stats in enumerate(group_sim_summary):
    if team_number % 4 == 0:
        print()
        group = 'Group ' + team_stats[7]
        print(group_format.format(group=group))
        print(line_format.format(pos='Pos', team='Team', Pts='Est. Points', GD='Est. GD', KS='Advance', First='1st',
                                 Second='2nd', Third='3rd', Fourth='4th'))
        print('-' * 96)
    position = team_number % 4 + 1
    team = team_stats[0]
    points = round(team_stats[1] / 10000, 2)
    gd = round(team_stats[2] / 10000, 2)
    advance = str(round((team_stats[3] + team_stats[4]) / 100)) + '%'
    first = str(round(team_stats[3] / 100)) + '%'
    second = str(round(team_stats[4] / 100)) + '%'
    third = str(round(team_stats[5] / 100)) + '%'
    fourth = str(round(team_stats[6] / 100)) + '%'
    print(line_format.format(pos=position, team=team, Pts=points, GD=gd, KS=advance, First=first, Second=second,
                             Third=third,
                             Fourth=fourth))

print()
print()
line_format = '{Pos:^4}|{team:^15}|{R16:^15}|{QF:^18}|{SF:^12}|{F:^10}|{W:^18}|'
wc_format = '{title:^99}'
print(wc_format.format(title='2022 FIFA World Cup Forecast'))
print()
print(line_format.format(Pos='Pos', team='Team', R16='Round of 16', QF='Quarterfinals', SF='Semifinals', F='Final',
                         W='Win World Cup'))
print('-' * 99)
for rank, team_stats in enumerate(wc_summary):
    team = team_stats[0]
    make_r16 = str(round(team_stats[1] / 100)) + '%'
    make_qf = str(round(team_stats[2] / 100)) + '%'
    make_sf = str(round(team_stats[3] / 100)) + '%'
    make_final = str(round(team_stats[4] / 100)) + '%'
    win_wc = str(round(team_stats[5] / 100)) + '%'
    print(line_format.format(Pos=rank + 1, team=team, R16=make_r16, QF=make_qf, SF=make_sf, F=make_final, W=win_wc))

# stores the data for the Group Stage in a Data Frame
for team_number, country in enumerate(group_sim_summary):
    new_country_data = [country[-1]]
    position = team_number % 4 + 1
    new_country_data.append(position)
    new_country_data.append(country[0])
    for data in country[1: -1]:
        new_country_data.append(data / 10000)
    advance = new_country_data[5] + new_country_data[6]
    new_country_data.insert(5, advance)
    group_sim_summary[team_number] = new_country_data

group_df = pd.DataFrame(group_sim_summary, columns=['Group', 'Group_Position', 'Team', 'Avg_Pts', 'Avg_GD',
                                                    'Advance', '1st', '2nd', '3rd', '4th'])

# stores the data for the Knockout Stage in a Data Frame
for team_number, country_data in enumerate(wc_summary):
    new_country_data = [team_number + 1, country_data[0], country_data[-1]]
    for data in country_data[1:-1]:
        new_country_data.append(data / 10000)
    wc_summary[team_number] = new_country_data

ks_df = pd.DataFrame(wc_summary, columns=['Rank', 'Team', 'Group', 'Make_R16', 'Make_QF', 'Make_SF', 'Make_Final',
                                          'Win_World_Cup'])


# exports Results to CSV files
group_df.to_csv("Group_Stage_Forecast_Results.csv", index=False, header=True)
ks_df.to_csv("Knockout_Stage_Forecast_Results.csv", index=False, header=True)
