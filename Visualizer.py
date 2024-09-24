import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO
import chess.pgn

# Load CSV containing mapping of ECO to opening names
@st.cache_data
def load_openings(): 
    openings = pd.read_csv('Chess_Openings.csv')  # Ensure the correct path to the CSV
    openings = openings[openings['ECO'] != openings['name']]
    return openings.drop_duplicates(subset='ECO', keep='first')  # Keep the first entry for each ECO

openings_df = load_openings()

# Fetch games for a user in PGN format, limit to a max of 500 games
def fetch_games(username, num_games=500):
    url = f'https://lichess.org/api/games/user/{username}?max={num_games}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    return None

# Extract and parse the opening from the PGN games
def parse_openings_from_pgn(pgn_data, openings_df):
    openings_count = {}
    
    # Parse PGN using chess.pgn library
    pgn_io = StringIO(pgn_data)
    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break
        opening_eco = game.headers.get("ECO", "")
        opening_name = openings_df[openings_df['ECO'] == opening_eco]['name'].values
        if opening_name.size > 0:
            opening_name = opening_name[0]
            if opening_name in openings_count:
                openings_count[opening_name] += 1
            else:
                openings_count[opening_name] = 1
                
    return openings_count

# Fetch user stats for a specific time format
def fetch_user_stats(username, game_format):
    url = f'https://lichess.org/api/user/{username}/perf/{game_format}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["stat"]  # Return stats JSON data
    return None

# Fetch player rating data
def fetch_rating_history(username):
    url = f'https://lichess.org/api/user/{username}/rating-history'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

# Streamlit App
st.title("Lichess Player Analysis Dashboard")

username = st.text_input("Enter Lichess Username:")

if username:
    # Fetch player's games data and display slider to select number of games
    max_games = 60
    pgn_data = fetch_games(username, max_games)

    if pgn_data:
        st.header("Select Number of Games to analyze")
        num_games = st.slider("Number of games", 0, max_games, 50)  # Default to 50 games
        
        # Parse openings from PGN data
        openings_count = parse_openings_from_pgn(pgn_data, openings_df)

        # Display most played openings as a bar chart
        st.header(f"Most Played Openings in the last {num_games} games")
        if openings_count:
            opening_df = pd.DataFrame(list(openings_count.items()), columns=['Opening', 'Count'])
            fig_openings = px.bar(opening_df.sort_values(by='Count', ascending=False), 
                                  x='Opening', y='Count', title="Most Played Openings")
            st.plotly_chart(fig_openings)
        else:
            st.write("No openings found.")

        # Fetch player rating history
        rating_history = fetch_rating_history(username)
        
        # Game formats and variants to display
        game_formats = ['bullet', 'blitz', 'rapid', 'classical', 'correspondence', 
        'ultraBullet', 'crazyhouse', 'antichess', 
        'horde', 'chess960', 'kingOfTheHill', 'threeCheck', 'racingKings'
        ]

        
        for game_format in game_formats:
            st.header(f"{game_format.capitalize()} Games")
            
            # Fetch user stats for the specific format/variant
            stats = fetch_user_stats(username, game_format)
    
            if stats:
                total_games = stats['count']['all']
                wins = stats['count']['win']
                losses = stats['count']['loss']
                draws = stats['count']['draw']
                
                win_loss_data = {
                    'Win': wins,
                    'Loss': losses,
                    'Draw': draws
                }
    
                # Pie chart for win/loss ratio
                with st.expander(f"Win/Loss/Draw Ratio in {game_format.capitalize()}"):
                    fig_white = px.pie(values=win_loss_data.values(), names=win_loss_data.keys(), 
                                       title=f"Win/Loss/Draw Ratio in {game_format.capitalize()}", hole=0.4)
                    fig_white.update_traces(textinfo='percent+label')
                    st.plotly_chart(fig_white)
    
                # Rating progression for the format/variant
                if rating_history:
                    for rating in rating_history:
                        if rating['name'] == game_format.capitalize() and rating['points']:
                            dates = [point[0] for point in rating['points']]
                            ratings = [point[3] for point in rating['points']]
                            with st.expander(f"Rating Progression in {game_format.capitalize()}"):
                                fig_rating = go.Figure(data=[go.Scatter(x=dates, y=ratings, mode='lines+markers')])
                                fig_rating.update_layout(title=f"Rating Progression in {game_format.capitalize()}", xaxis_title='Date', yaxis_title='Rating')
                                st.plotly_chart(fig_rating)
                else:
                    st.write(f"No rating data available for {game_format.capitalize()}.")
            else:
                st.write(f"Error fetching {game_format.capitalize()} statistics for {username}.")
    else:
        st.write(f"Error fetching games for {username}.")
