# github repo: https://github.com/johannbleza/statsify

import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Set default style for Streamlit
st.set_page_config(
    page_title="Statsify",
    page_icon="📉",
    layout="centered",
)

# Function to get Spotify client using OAuth
def get_spotify_client():
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=st.secrets['spotify']['client_id'], 
            client_secret=st.secrets['spotify']['client_secret'],
            redirect_uri=st.secrets['spotify']['redirect_uri'],
            scope="user-library-read user-top-read user-read-recently-played user-read-playback-state",
            show_dialog=True,
        )
    )

# Initialize Spotify client
sp = get_spotify_client()

# Function to get recently played tracks
def get_recently_played():
    return sp.current_user_recently_played(limit=50)

# Function to get user profile
def get_user_profile():
    return sp.current_user()

# Function to get top artists
def get_top_artists():
    return sp.current_user_top_artists(limit=50)

# Streamlit app title and description
st.title("📉 Statsify")
st.caption("A real-time dashboard for your Spotify account. Visualize and track your listening habits, top tracks, artists, and more!")

# Button to login with Spotify account
if st.button("Login with your Spotify account!"):
    if os.path.exists('.cache'):
        os.remove('.cache')
    st.rerun()

# Dashboard 
st.header("Dashboard")
try:
    user = get_user_profile()
except spotipy.exceptions.SpotifyException as e:
    st.error(f"Error fetching user profile data: No access to beta")
    st.stop()

# Get recently played tracks
recently_played = get_recently_played()
track = recently_played['items'][0]['track']

# User profile section
col1, col2 = st.columns([2, 3])
with col1:
    if user.get('images'):
        st.image(user['images'][0]['url'])
    else:
        st.image(f"https://placehold.co/400?text={user['display_name']}", )
with col2:
    st.subheader("User Profile 🎵")
    st.header(user['display_name'])
    st.caption(f"Last updated: {pd.to_datetime('now').strftime('%Y-%m-%d %H:%M:%S')}")
    if st.button("Refresh"): 
        sp = get_spotify_client()
        st.toast('Successfully refreshed!')
        user = get_user_profile()

# Current device section
now_playing = sp.current_playback()
if now_playing and now_playing['device']:
    device = now_playing['device']
    st.subheader("Current Device")
    col1, col2 = st.columns([1,1])
    with col1:
        st.write(f" 💻 {device['name']}  ")
    with col2:
        st.write(f"🔊 Volume: {device['volume_percent']}%")
else:
    st.subheader("Current Device")
    st.write("No device is currently active.")

# Now playing and next in queue section
play1, play2 = st.columns([1, 1])
with play1:
    if now_playing and now_playing['is_playing']:
        track = now_playing['item']
        st.subheader("Now Playing")
        col1, col2 = st.columns([1, 4])
        with col1:
            st.image(track['album']['images'][0]['url'])
        with col2:
            st.write(track['name'])
            st.caption(f"by {track['artists'][0]['name']}")
    else:
        st.subheader("Now Playing")
        st.write("No song is currently playing.")

with play2:
    st.subheader("Next in Queue")
    try:
        queue = sp.queue()
        if queue and queue['queue']:
            next_track = queue['queue'][0]
            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(next_track['album']['images'][0]['url'])
            with col2:
                st.write(next_track['name'])
                st.caption(f"by {next_track['artists'][0]['name']}")
        else:
            st.write("No songs in the queue.")
    except spotipy.exceptions.SpotifyException as e:
        st.write(f"Error fetching queue")

st.divider()

# Recent activity section
st.subheader("Recent Activity 📅")
st.caption("Listened minutes over a period of time.")

# Calculate durations and played times for recently played tracks
durations = [item['track']['duration_ms'] / 60000 for item in recently_played['items']]
played_times = [pd.to_datetime(item['played_at']) for item in recently_played['items']]

# Create DataFrame for recent activity
df = pd.DataFrame({'played_at': played_times, 'duration': durations})
df.set_index('played_at', inplace=True)

# Select time period for resampling
period = st.selectbox("Select time period", ["1H", "2H", "4H", "6H"], index=1)
listening_time = df['duration'].resample(period).sum()

# Display area chart for recent activity
st.area_chart(listening_time, y_label="Number of Minutes", x_label="Period")
col1, col2, col3 = st.columns([5, 1, 3])

# On repeat recently section
with col1:
    st.subheader("On Repeat 🔂")
    st.caption("Most played tracks recently.")
    tracks = [item['track']['name'] for item in recently_played['items']]
    track_counts = pd.Series(tracks).value_counts().head(10)
    st.bar_chart(track_counts, x_label="Tracks", y_label="Count")

    # Top genres section
    top_artists = get_top_artists()
    genres = [genre for artist in top_artists['items'] for genre in artist['genres']]
    genre_counts = pd.Series(genres).value_counts().head(5)

    st.subheader("Top Genres 🎶")
    st.caption("Your current taste in music.")
    fig, ax = plt.subplots()
    colors = ['#92C5F9', '#4394E5', '#0066CC', '#003366', '#004D99']
    ax.pie(genre_counts, labels=[label.title() for label in genre_counts.index], autopct='%1.2f%%', colors=colors, textprops={'color': "w"})
    fig.patch.set_alpha(0)
    st.pyplot(fig)

    # Current favorites section
    artist_names = [item['track']['artists'][0]['name'] for item in recently_played['items']]
    artist_counts = pd.Series(artist_names).value_counts().head(5)

    st.subheader("Current Favorites 🩵")
    st.caption("Top artists based on your recently played tracks.")
    fig, ax = plt.subplots()
    ax.pie(artist_counts, labels=[label.title() for label in artist_counts.index], autopct='%1.2f%%', colors=colors, textprops={'color': "w"})
    fig.patch.set_alpha(0)
    st.pyplot(fig)

# Recently played and top songs section
with col3:
    st.subheader("Recently Played")
    for item in recently_played['items'][:5]:
        track = item['track']
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image(track['album']['images'][0]['url'], use_container_width=100)
        with col2:
            st.write(track['name'])
            st.caption(f"{track['artists'][0]['name']}")

    st.subheader("Top Songs")
    top_tracks = sp.current_user_top_tracks(limit=5)
    for track in top_tracks['items']:
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image(track['album']['images'][0]['url'], use_container_width=True)
        with col2:
            st.write(track['name'])
            st.caption(track['artists'][0]['name'])

    st.subheader("Top Artists")
    for artist in top_artists['items'][:5]:
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image(artist['images'][0]['url'], use_container_width=True)
        with col2:
            st.write(artist['name'])

# Top artists by popularity section with adjustable limit
st.subheader("Top Artists by Popularity ⭐️")
limit = st.slider("Select the number of top artists to display", min_value=1, max_value=50, value=10)
st.caption(f"Your top {limit} artists based on popularity.")
artist_names = [artist['name'] for artist in top_artists['items'][:limit]]
popularity = [artist['popularity'] for artist in top_artists['items'][:limit]]
df_popularity = pd.DataFrame({'Artist': artist_names, 'Popularity': popularity})
df_popularity.set_index('Artist', inplace=True)
st.bar_chart(df_popularity, y_label="Popularity", x_label="Artists")

st.caption("Created by Johann.dev")