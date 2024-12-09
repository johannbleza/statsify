import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import CacheHandler
import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
import matplotlib.pyplot as plt

class StreamlitCacheHandler(CacheHandler):
    """Custom cache handler that uses Streamlit's session state instead of files"""
    def __init__(self):
        super().__init__()

    def get_cached_token(self):
        """Get the cached token from Streamlit session state"""
        return st.session_state.get("spotify_token")

    def save_token_to_cache(self, token_info):
        """Save the token to Streamlit session state"""
        st.session_state["spotify_token"] = token_info

def clear_session_token():
    """Clear the token from Streamlit session state"""
    if "spotify_token" in st.session_state:
        del st.session_state["spotify_token"]
    if "authenticated" in st.session_state:
        del st.session_state["authenticated"]

def get_spotify_client():
    """Get Spotify client with custom cache handler"""
    cache_handler = StreamlitCacheHandler()
    load_dotenv()
    
    import socket
    try:
        import uvicorn
        uvicorn.config.MULTIPROCESS_BROKEN = True
    except ImportError:
        pass
    
    auth_manager = SpotifyOAuth(
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
        redirect_uri=os.getenv("REDIRECT_URI"),
        scope="user-library-read user-top-read user-read-recently-played user-read-playback-state",
        show_dialog=True,
        cache_handler=cache_handler
    )
    return spotipy.Spotify(auth_manager=auth_manager)

# Set custom theme configuration
st.set_page_config(
    page_title="Statsify",
    page_icon="📉",
    layout="centered",
)

# Add login/logout functionality
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


sp = get_spotify_client()

def get_recently_played():
    return sp.current_user_recently_played(limit=50)

def get_user_profile():
    return sp.current_user()

def get_top_artists():
    return sp.current_user_top_artists(limit=50)

st.title("📉 Statsify")
st.caption("A real-time dashboard for your Spotify account. Track your listening habits, top tracks, artists, and more!")


if st.button("Login with Spotify" if not st.session_state.authenticated else "Logout"):
    if st.session_state.authenticated:
        clear_session_token()
        st.success("Successfully logged out!")
        st.rerun()
    else:
        try:
            sp = get_spotify_client()
            user = sp.current_user()  # Test the connection
            st.session_state.authenticated = True
            st.success("Successfully logged in!")
            st.rerun()
        except Exception as e:
            st.error(f"Login failed: {str(e)}")
st.header("Dashboard")
try:
    user = get_user_profile()
except spotipy.exceptions.SpotifyException as e:
    st.error(f"Error fetching user profile data: No access to beta")
    st.stop()

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

durations = [item['track']['duration_ms'] / 60000 for item in recently_played['items']]
played_times = [pd.to_datetime(item['played_at']) for item in recently_played['items']]

df = pd.DataFrame({'played_at': played_times, 'duration': durations})
df.set_index('played_at', inplace=True)

period = st.selectbox("Select time period", ["1H", "2H", "4H", "6H"], index=0)
listening_time = df['duration'].resample(period).sum()

st.area_chart(listening_time, y_label="Number of Minutes", x_label="Period")
col1, col2, col3 = st.columns([5, 1, 3])

# On repeat recently section
with col1:
    st.subheader("On Repeat 🔂")
    st.caption("Most played tracks recently.")
    tracks = [item['track']['name'] for item in recently_played['items']]
    track_counts = pd.Series(tracks).value_counts().head(10)
    st.bar_chart(track_counts, x_label="Tracks", y_label="Count")

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

# Top artists by popularity section
st.subheader("Top Artists by Popularity ⭐️")
st.caption("Your top artists based on their popularity.")
artist_names = [artist['name'] for artist in top_artists['items']]
popularity = [artist['popularity'] for artist in top_artists['items']]
df_popularity = pd.DataFrame({'Artist': artist_names, 'Popularity': popularity})
df_popularity.set_index('Artist', inplace=True)
st.bar_chart(df_popularity, y_label="Popularity")

st.caption("Created by Johann.dev")
