import os
import psycopg2
from psycopg2 import sql
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from googleapiclient.discovery import build
import isodate

app = Flask(__name__)
CORS(app)

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
# DATABASE_URL = r"postgresql://postgres:postgres@db:5432/postgres"
API_KEY = os.getenv('GAPI_KEY')
youtube = build('youtube', 'v3', developerKey=API_KEY)


# Updated to use googleapiclient for API calls
def get_channelId_from_name(channel_name):
    try:
        # Using the YouTube Data API to fetch channel ID by username
        request = youtube.channels().list(
            part="id",
            forUsername=channel_name
        )
        response = request.execute()
        if 'items' in response and len(response['items']) > 0:
            return response['items'][0]['id']
        return None
    except Exception as e:
        print(f"Error fetching channel ID: {e}")
        return None


def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def initialize_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name = 'channel'
        );
    """)

    exists = cur.fetchone()[0]

    if not exists:
        with open('init.sql', 'r') as f:
            init_script = f.read()
            cur.execute(init_script)
            conn.commit()

    cur.close()
    conn.close()


def fetch_channel_data(channel_id):
    request = youtube.channels().list(
        part='statistics,snippet',
        id=channel_id
    )
    response = request.execute()
    return response


def fetch_latest_videos(channel_id):
    request = youtube.search().list(
        part='snippet',
        channelId=channel_id,
        maxResults=10,
        order='date',
        type='video'
    )
    response = request.execute()
    return response['items']


def fetch_video_statistics(video_ids):
    request = youtube.videos().list(
        part='statistics,contentDetails',
        id=','.join(video_ids)
    )
    response = request.execute()
    return response['items']


def calculate_metrics(videos):
    view_counts = [int(video['statistics']['viewCount'])
                   for video in videos if 'viewCount' in video['statistics']]
    if not view_counts:
        median_viewership = 0
    else:
        sorted_views = sorted(view_counts)
        mid = len(sorted_views) // 2
        median_viewership = (sorted_views[mid] if len(sorted_views) % 2 == 1 else (
            sorted_views[mid - 1] + sorted_views[mid]) // 2)

    short_videos_count = sum(1 for video in videos if isodate.parse_duration(
        video['contentDetails']['duration']).total_seconds() <= 60)
    long_videos_count = len(videos) - short_videos_count
    upload_frequency = len(videos)

    return {
        'median_viewership': median_viewership,
        'short_videos_count': short_videos_count,
        'long_videos_count': long_videos_count,
        'upload_frequency': upload_frequency
    }


@app.route('/api/channels', methods=['POST'])
def add_channel():
    data = request.json

    if 'channelName' not in data:
        return jsonify({'error': 'channelName is required'}), 400

    # Step 1: Get Channel ID from the channelName
    channel_id = get_channelId_from_name(data['channelName'])
    if not channel_id:
        return jsonify({'error': 'Channel not found'}), 404

    # Step 2: Fetch Channel Data using the channel ID
    channel_data = fetch_channel_data(channel_id)

    if 'items' not in channel_data or not channel_data['items']:
        return jsonify({'error': 'Channel not found'}), 404

    channel_info = channel_data['items'][0]

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Step 3: Insert the channel information into the database
        cur.execute(
            sql.SQL("INSERT INTO Channel (channel_id, channel_name, total_videos, subscribers) VALUES (%s, %s, %s, %s) ON CONFLICT (channel_id) DO NOTHING;"),
            (
                channel_id,
                channel_info['snippet']['title'],
                int(channel_info['statistics'].get('videoCount', 0)),
                int(channel_info['statistics'].get('subscriberCount', 0))
            )
        )

        # Step 4: Fetch and process the latest videos
        video_items = fetch_latest_videos(channel_id)
        video_ids = [video['id']['videoId'] for video in video_items]

        videos = fetch_video_statistics(video_ids)

        # Step 5: Insert video data into the database
        for video in videos:
            video_id = video['id']
            title = next(v['snippet']['title']
                         for v in video_items if v['id']['videoId'] == video_id)
            published_at = next(v['snippet']['publishedAt']
                                for v in video_items if v['id']['videoId'] == video_id)
            duration_iso = video['contentDetails']['duration']
            duration_seconds = int(isodate.parse_duration(
                duration_iso).total_seconds())
            view_count = int(video['statistics'].get('viewCount', 0))
            likes = int(video['statistics'].get('likeCount', 0))
            comments = int(video['statistics'].get('commentCount', 0))

            cur.execute(
                sql.SQL("INSERT INTO Videos (video_id, channel_id, title, published_at, duration, view_count, likes, comments, type) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);"),
                (
                    video_id, channel_id, title, published_at, duration_seconds, view_count, likes, comments, 'Long' if duration_seconds > 60 else 'Short'
                )
            )

        # Step 6: Calculate and store metrics
        metrics = calculate_metrics(videos)

        cur.execute(
            sql.SQL("INSERT INTO Metrics (channel_id, median_viewership, upload_frequency, short_videos_count, long_videos_count) VALUES (%s, %s, %s, %s, %s);"),
            (
                channel_id,
                metrics['median_viewership'],
                metrics['upload_frequency'],
                metrics['short_videos_count'],
                metrics['long_videos_count']
            )
        )

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'name': channel_info['snippet']['title']}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    initialize_db()
    app.run(debug=True)
