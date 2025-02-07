import tkinter as tk
from tkinter import ttk
import webbrowser
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pyautogui
import time
import random

# YouTube Data API key
API_KEY = 'get your own api key'

def fetch_playlist():
    # Set up Chrome options for headless browsing
    chrome_options = Options()
    # Auto select webdriver instead of pathing 
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Open the webpage
    print("Opening the webpage")
    url = "https://feelthemusi.com/playlist/z1enh9"
    driver.get(url)

    try:
        # Use WebDriverWait to wait until the track elements are present (better alternative to sleep)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'track')))

        # Get the page source after JavaScript has run and elements are present
        html = driver.page_source
        print("Webpage accessed")

    except Exception as e:
        print(f"An error occurred while waiting for the elements: {e}")
        driver.quit()
        return []

    # Parse the page source with BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    songs = []
    try:
        # iterate through song list for every element designated as class 'track'
        for track in soup.find_all('a', class_='track'):
            link = track.get('href', None)
            if not link:
                continue
            # Iterate through looking for div followed by video_title to pull video title
            title_div = track.find('div', class_='video_title')
            # Strips text from html to print title
            title = title_div.text.strip() if title_div else "Unknown Title"
            # Iterate through looking for div followed by video_artist to pull video title
            artist_div = track.find('div', class_='video_artist')
            # Strips text from html to print artist
            artist = artist_div.text.strip() if artist_div else "Unknown Artist"
            # Iterate through looking for div followed by icon to pull image url
            icon_div = track.find('div', class_='icon')
            image_url = None
            if icon_div and 'style' in icon_div.attrs:
                style_attr = icon_div['style']
                start = style_attr.find("url('") + len("url('")
                end = style_attr.find("')", start)
                image_url = style_attr[start:end] if start != -1 and end != -1 else None
            songs.append((title, artist, link, image_url))
    except AttributeError as e:
        print(f"Error parsing the page: {e}")
    
    if not songs:
        print("No songs found on the page.")
    else:
        print(f"Successfully fetched {len(songs)} songs.")
    
    return songs

def get_video_duration(video_id):
    """Fetch video duration using the YouTube Data API."""
    url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={API_KEY}&part=contentDetails"
    response = requests.get(url)
    data = response.json()

    if 'items' in data and len(data['items']) > 0:
        duration_iso = data['items'][0]['contentDetails']['duration']
        return iso_duration_to_seconds(duration_iso)
    else:
        print(f"Video with ID {video_id} not found.")
        return None

def iso_duration_to_seconds(duration):
    """Convert ISO 8601 duration to seconds."""
    hours = minutes = seconds = 0

    if 'H' in duration:
        hours = int(duration.split('H')[0].replace('PT', ''))
        duration = duration.split('H')[1]
    if 'M' in duration:
        minutes = int(duration.split('M')[0].replace('PT', ''))
        duration = duration.split('M')[1]
    if 'S' in duration:
        seconds = int(duration.replace('S', ''))

    total_seconds = hours * 3600 + minutes * 60 + seconds
    return total_seconds

def is_video_paused(driver):
    """Check if the YouTube video is paused using JavaScript."""
    script = """
    var video = document.querySelector('video');
    return video ? video.paused : true;
    """
    return driver.execute_script(script)

class PlaylistApp:
    def __init__(self, root, playlist):
        self.root = root
        self.root.configure(bg="#1f1f1f")
        self.frame = tk.Frame(root, bg="#1f1f1f")
        self.frame.pack(fill="both", expand=True)
        self.root.title("Music Playlist")
        
        # Header for the app
        self.header = tk.Label(self.frame, text="Musi.py", fg="orange", bg="#1f1f1f", font=("Helvetica", 16, "bold"))
        self.header.pack(pady=10)
        
        self.playlist = playlist
        self.current_song_index = 0

        # Set up Selenium ChromeDriver for controlling the browser
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

        # Create a canvas for the scrollable playlist
        self.canvas = tk.Canvas(self.frame, bg="#1f1f1f", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#1f1f1f")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Display the songs in the playlist
        for idx, (title, artist, url, img_url) in enumerate(self.playlist):
            self.create_song_row(idx, title, artist, url)

        # Buttons for play, shuffle, and quit
        self.play_button = tk.Button(root, text="Play Selected Song", command=self.play_selected_song, bg="#1f1f1f", fg="orange", bd=2, relief="solid", highlightbackground="lightgrey")
        self.play_button.pack(pady=5)

        self.shuffle_button = tk.Button(root, text="Shuffle Play", command=self.shuffle_and_play, bg="#1f1f1f", fg="orange", bd=2, relief="solid", highlightbackground="lightgrey")
        self.shuffle_button.pack(pady=5)

        self.quit_button = tk.Button(root, text="Quit", command=self.quit_app, bg="#1f1f1f", fg="orange", bd=2, relief="solid", highlightbackground="lightgrey")
        self.quit_button.pack(pady=5)

    def create_song_row(self, idx, title, artist, url):
        """Create a row for each song with title and artist and make it clickable."""
        row_frame = tk.Frame(self.scrollable_frame, bg="#1f1f1f", pady=5)
        song_label = tk.Label(row_frame, text=f"{title}\n{artist}", fg="orange", bg="#1f1f1f", font=("Helvetica", 8, "bold"), anchor="w", justify="left")
        song_label.pack(side="left", padx=10, fill="both", expand=True)

        # Bind the label to the click event to open the URL
        song_label.bind("<Button-1>", lambda e, link=url: self.play_song(link))

        row_frame.pack(fill="x", padx=5)

    def play_song(self, url):
        """Play the song in Selenium, fetch the video duration, and manage the browser tab."""
        video_id = url.split('v=')[1]
        duration = get_video_duration(video_id)
        if not duration:
            print("Unable to get video duration.")
            return
        
        # Open the YouTube video in a new tab
        self.driver.execute_script("window.open('{}', '_blank');".format(url))
        self.driver.switch_to.window(self.driver.window_handles[-1])

        # Add a delay to allow the video to load
        time.sleep(5)

        # Simulate pressing the spacebar to start the video
        pyautogui.press('space')

        elapsed_time = 0
        check_interval = 1

        # Monitor video playback
        while elapsed_time < duration:
            if not is_video_paused(self.driver):
                elapsed_time += check_interval
            time.sleep(check_interval)

        # Once the video finishes, close the tab and switch back
        self.driver.close()
        self.driver.switch_to.window(self.driver.window_handles[0])

    def play_selected_song(self):
        """Play the currently selected song."""
        if self.playlist:
            song = self.playlist[self.current_song_index]
            self.play_song(song[2])

    def shuffle_and_play(self):
        """Shuffle and play a random song."""
        random_song = random.choice(self.playlist)
        self.play_song(random_song[2])

    def quit_app(self):
        """Quit the app and close the Selenium browser."""
        self.driver.quit()
        self.root.quit()

# Initialize the GUI application
root = tk.Tk()

# Fetch the playlist data
playlist = fetch_playlist()

# Start the app with the playlist data
app = PlaylistApp(root, playlist)

# Start the GUI event loop
root.mainloop()
