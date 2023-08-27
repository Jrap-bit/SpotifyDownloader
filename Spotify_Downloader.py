import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from tkinter import filedialog
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from pytube import YouTube
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_audio
import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import re

load_dotenv()

scope = os.getenv("SCOPE")
username = os.getenv("SPOTIFY_USERNAME")
client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")
api_key = os.getenv("YOUTUBE_API_KEY")
youtube_client = os.getenv("YOUTUBE_API_OAUTH_CLIENT_ID")
youtube_secret = os.getenv("YOUTUBE_API_OAUTH_CLIENT_SECRET")
youtube_scopes = ['https://www.googleapis.com/auth/youtube']

playlist_id_global = ""

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id,
                                               client_secret=client_secret,
                                               redirect_uri=redirect_uri,
                                               scope=scope,
                                               username=username))


def search_youtube_video(song_name, artist_name=None, album_name=None, skip_lyrics=False):
    query = f"{song_name}"

    if artist_name:
        query += f" {artist_name}"
    if album_name:
        query += f" {album_name}"

    if not skip_lyrics:
        pass
    else:
        query += " Song"

    print("Searching YouTube with query: {}".format(query))

    youtube = build("youtube", "v3", developerKey=api_key)

    search_response = youtube.search().list(
        q=query,
        part="id,snippet",
        maxResults=2,
    ).execute()

    video_info = []
    for search_result in search_response.get("items", []):
        if search_result["id"]["kind"] == "youtube#video":
            video_id = search_result["id"]["videoId"]
            video_title = search_result["snippet"]["title"]
            video_link = f"https://www.youtube.com/watch?v={video_id}"
            video_info.append({"title": video_title, "link": video_link})

    return video_info[:2]


def get_playlists():
    try:
        playlists = sp.user_playlists(username)
        playlist_listbox.delete(0, tk.END)

        for index, playlist in enumerate(playlists['items'], start=1):
            playlist_name = playlist['name']
            if playlist_name:
                playlist_listbox.insert(tk.END, f"{index}. {playlist_name}")

    except Exception as e:
        messagebox.showerror("Error", f"Error occurred: {e}")


def get_playlist_songs(event):
    global playlist_id_global
    selected_index = playlist_listbox.curselection()
    if selected_index:
        playlist_id_global = selected_index
        playlist_name = playlist_listbox.get(selected_index[0])
        playlist_id = get_playlist_id_by_name(playlist_name)
        if playlist_id:
            try:
                playlist = sp.playlist_items(playlist_id)
                song_listbox.delete(0, tk.END)

                for index, item in enumerate(playlist["items"], start=1):
                    track_name = item["track"]["name"]
                    if track_name:
                        song_listbox.insert(tk.END, f"{index}. {track_name}")

            except Exception as e:
                messagebox.showerror("Error", f"Error occurred: {e}")


def get_playlist_id_by_name(playlist_name):
    playlists = sp.user_playlists(username)
    for index, playlist in enumerate(playlists['items'], start=1):
        if playlist_name.startswith(f"{index}. "):
            return playlist['id']
    return None


def download_youtube_audio(url, output_folder):
    try:
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').first()
        if audio_stream:
            audio_stream.download(output_folder)
            downloaded_file_path = os.path.join(output_folder, audio_stream.default_filename)

            mp3_file_path = os.path.splitext(downloaded_file_path)[0] + '.mp3'
            ffmpeg_extract_audio(downloaded_file_path, mp3_file_path)

            os.remove(downloaded_file_path)

            print(f"Downloaded and converted: {yt.title}")
        else:
            print("No suitable audio stream found.")


    except Exception as e:

        print(f"Error occurred: {e}")


def download_song(selected_video_info):
    try:
        video_link = selected_video_info["link"]
        download_youtube_audio(video_link, download_folder)
        messagebox.showinfo("Success", "Downloaded successfully!")
    except Exception as e:
        print(f"Error occurred: {e}")


def choose_download():
    global playlist_id_global
    selected_index = song_listbox.curselection()
    if selected_index:
        song_item = song_listbox.get(selected_index[0])
        song_name = song_item.split(". ", 1)[1]
        artist_name = None
        album_name = None

        selected_playlist_index = playlist_id_global
        if selected_playlist_index:
            selected_playlist = playlist_listbox.get(selected_playlist_index[0])
            playlist_id = get_playlist_id_by_name(selected_playlist)
            print(playlist_id)
            if playlist_id is None:
                playlist_id = playlist_id_global
            if playlist_id:
                playlist = sp.playlist_items(playlist_id)
                for item in playlist["items"]:
                    if item["track"]["name"] == song_name:
                        artist_name = item["track"]["artists"][0]["name"]
                        album_name = item["track"]["album"]["name"]
                        break

        video_info_list = search_youtube_video(song_name, artist_name, album_name)

        if video_info_list:
            if len(video_info_list) == 1:
                selected_video_info = video_info_list[0]
                download_song(selected_video_info)
            else:
                video_info_text = "Select a video to download:\n"
                for idx, video_info in enumerate(video_info_list, start=1):
                    video_info_text += f"{idx}. {video_info['title']}\n"

                video_info_label.config(text=video_info_text)

                download_button_frame.pack_forget()
                download_button_frame.pack(side=tk.TOP, pady=5, fill=tk.X)
                for btn in download_buttons:
                    btn.destroy()

                for idx, video_info in enumerate(video_info_list, start=1):
                    btn = tk.Button(download_button_frame, text=f"Download Option {idx}", font=("Helvetica", 20),
                                    command=lambda v=video_info: download_song(v))
                    btn.pack(side=tk.LEFT, padx=40)
                    download_buttons.append(btn)

                    video_info["song_name"] = song_name
                    video_info["artist_name"] = artist_name
                    video_info["album_name"] = album_name


def download_whole_playlist():
    global download_folder
    selected_playlist_index = playlist_listbox.curselection()
    if selected_playlist_index == ():
        selected_playlist_index = playlist_id_global
    if selected_playlist_index:
        selected_playlist = playlist_listbox.get(selected_playlist_index[0])
        playlist_id = get_playlist_id_by_name(selected_playlist)
        if playlist_id is None:
            playlist_id = playlist_id_global
        if playlist_id:
            try:
                playlist = sp.playlist_items(playlist_id)
                for item in playlist["items"]:
                    track_name = item["track"]["name"]
                    artist_name = item["track"]["artists"][0]["name"]
                    album_name = item["track"]["album"]["name"]
                    if track_name:
                        video_info_list = search_youtube_video(track_name, artist_name, album_name)
                        if video_info_list:
                            selected_video_info = video_info_list[0]
                            video_link = selected_video_info["link"]
                            try:
                                download_youtube_audio(video_link, download_folder)
                            except Exception as e:
                                print(f"Error occurred: {e}")
                messagebox.showinfo("Download", "Downloading the whole playlist")

            except Exception as e:
                print(f"Error occurred: {e}")


def create_youtube_playlist(playlist_title, playlist_description, credential):
    youtube = build("youtube", "v3", credentials=credential)

    request = youtube.playlists().insert(
        part="snippet",
        body={
            "snippet": {
                "title": playlist_title,
                "description": playlist_description,
            }
        }
    )
    response = request.execute()

    return response["id"]


def fetch_spotify_playlist(playlist_link):
    global playlist_id_global
    playlist_id = re.search(r'playlist\/(\w+)', playlist_link)
    if playlist_id:
        playlist_id = playlist_id.group(1)
        playlist_id_global = playlist_id
        playlist = sp.playlist_items(playlist_id)

        playlist_info = {
            "playlist": playlist,
            "songs_info": []
        }

        for item in playlist["items"]:
            track_name = item["track"]["name"]
            artist_name = item["track"]["artists"][0]["name"]
            album_name = item["track"]["album"]["name"]
            playlist_info["songs_info"].append({
                "track_name": track_name,
                "artist_name": artist_name,
                "album_name": album_name
            })

        return playlist_info

    else:
        return None


def display_playlist_details(playlist):
    song_listbox.delete(0, tk.END)

    for index, item in enumerate(playlist["items"], start=1):
        track_name = item["track"]["name"]
        artist_name = item["track"]["artists"][0]["name"]
        album_name = item["track"]["album"]["name"]
        if track_name:
            song_listbox.insert(tk.END, f"{index}. {track_name}")


def search_spotify_playlist():
    playlist_link = spotify_playlist_entry.get()
    playlist_info = fetch_spotify_playlist(playlist_link)
    if playlist_info:
        display_playlist_details(playlist_info["playlist"])


root = tk.Tk()
root.title("Spotify Playlist Downloader")
root.geometry("1500x900")


def authenticate_google():
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secrets.json',
        youtube_scopes
    )
    credentials = flow.run_local_server(port=0)
    return credentials


def create_youtube_playlist_from_spotify():
    selected_playlist_index = playlist_listbox.curselection()
    if selected_playlist_index == ():
        selected_playlist_index = playlist_id_global
    if selected_playlist_index:
        selected_playlist = playlist_listbox.get(selected_playlist_index[0])
        playlist_title = selected_playlist.split(". ", 1)[1]
        playlist_description = "Created by TuneLink"

        credentials = authenticate_google()
        youtube = build('youtube', 'v3', credentials=credentials)

        youtube_playlist_id = create_youtube_playlist(playlist_title, playlist_description, credentials)
        youtube_playlist_link = f"https://www.youtube.com/playlist?list={youtube_playlist_id}"

        selected_playlist_name = playlist_listbox.get(selected_playlist_index[0])
        selected_playlist_id = get_playlist_id_by_name(selected_playlist_name)
        if selected_playlist_id is None:
            selected_playlist_id = playlist_id_global
        if selected_playlist_id:
            selected_playlist = sp.playlist_items(selected_playlist_id)
            for item in selected_playlist["items"]:
                track_name = item["track"]["name"]
                artist_name = item["track"]["artists"][0]["name"]
                album_name = item["track"]["album"]["name"]

                if track_name:
                    video_info_list = search_youtube_video(track_name, artist_name, album_name, skip_lyrics=True)

                    if video_info_list:
                        selected_video_info = video_info_list[0]
                        video_id = selected_video_info["link"].split("v=")[1]
                        youtube.playlistItems().insert(
                            part="snippet",
                            body={
                                "snippet": {
                                    "playlistId": youtube_playlist_id,
                                    "resourceId": {
                                        "kind": "youtube#video",
                                        "videoId": video_id
                                    }
                                }
                            }
                        ).execute()

        messagebox.showinfo("YouTube Playlist Created", f"Your YouTube playlist has been created!\n"
                                                        f"Playlist Link: {youtube_playlist_link}")


playlist_listbox = tk.Listbox(root, font=("Helvetica", 15))
playlist_listbox.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=False)
playlist_listbox.config(height=90, width=40)

playlist_scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=playlist_listbox.yview)
playlist_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
playlist_listbox.config(yscrollcommand=playlist_scrollbar.set)

song_listbox = tk.Listbox(root, font=("Helvetica", 15))
song_listbox.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=False)
song_listbox.config(height=90, width=50)

song_scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=song_listbox.yview)
song_scrollbar.pack(side=tk.LEFT, fill=tk.Y)
song_listbox.config(yscrollcommand=song_scrollbar.set)

video_info_label = tk.Label(root, text="", font=("Helvetica", 15), justify="left")
video_info_label.pack(pady=20, padx=30)
video_info_label.config(wraplength=700, height=10)

spotify_playlist_entry = tk.Entry(root, font=("Helvetica", 15))
spotify_playlist_entry.pack(side=tk.TOP, padx=10, pady=10, fill=tk.X, expand=True)

search_playlist_button = tk.Button(root, text="Search Playlist", font=("Helvetica", 20), command=search_spotify_playlist)
search_playlist_button.pack(side=tk.TOP, padx=10, pady=10)

get_playlists_button = tk.Button(root, text="Get Playlists", font=("Helvetica", 20), command=get_playlists)
get_playlists_button.pack(pady=40)

playlist_listbox.bind("<<ListboxSelect>>", get_playlist_songs)

download_button_frame = tk.Frame(root)
download_button_frame.pack(side=tk.TOP, padx=40, pady=30, fill=tk.BOTH)
download_buttons = []

choose_download_button = tk.Button(root, text="Download This Song", font=("Helvetica", 20), command=choose_download)
choose_download_button.pack(pady=20)

download_whole_playlist_button = tk.Button(root, text="Download Whole Playlist", font=("Helvetica", 20), command=download_whole_playlist)
download_whole_playlist_button.pack(pady=40)

create_youtube_button = tk.Button(root, text="Create YouTube Playlist", font=("Helvetica", 20), command=create_youtube_playlist_from_spotify)
create_youtube_button.pack(pady=40)

download_folder = filedialog.askdirectory()

root.mainloop()
