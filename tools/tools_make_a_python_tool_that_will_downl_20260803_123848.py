# This script allows users to download YouTube videos using yt-dlp.
import yt_dlp

def download_video(url, output_path='%(title)s.%(ext)s'):
    ydl_opts = {
        'outtmpl': output_path,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

if __name__ == "__main__":
    url = input("Enter the YouTube video URL: ")
    download_video(url)