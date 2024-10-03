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


def get_channelId_from_name(channel_name):
    try:
        # If the name starts with @, treat it as a handle
        if channel_name.startswith('@'):
            request = youtube.search().list(
                part="snippet",
                q=channel_name,
                type="channel",
                maxResults=1
            )
            response = request.execute()
            if 'items' in response and len(response['items']) > 0:
                return response['items'][0]['snippet']['channelId']
        else:
            # Old style username lookup
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


def get_channel_summary(channel_id):
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT
            c.channel_name,
            COUNT(v.video_id) AS total_videos,
            SUM(v.view_count) AS total_views,
            SUM(v.likes) AS total_likes
        FROM
            Channel c
        JOIN
            Videos v ON c.channel_id = v.channel_id
        WHERE
            c.channel_id = %s
        GROUP BY
            c.channel_name;
    """

    cur.execute(query, (channel_id,))
    summary = cur.fetchone()
    cur.close()
    conn.close()

    if summary:
        return {
            'channel_name': summary[0],
            'total_videos': summary[1],
            'total_views': summary[2],
            'total_likes': summary[3]
        }
    return None


def get_popular_videos(min_views):
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT
            v.video_id,
            v.title,
            v.view_count,
            v.likes,
            c.channel_name
        FROM
            Videos v
        JOIN
            Channel c ON v.channel_id = c.channel_id
        WHERE
            v.view_count > %s
        ORDER BY
            v.view_count DESC;
    """

    cur.execute(query, (min_views,))
    videos = cur.fetchall()
    cur.close()
    conn.close()

    return [{'video_id': row[0], 'title': row[1], 'view_count': row[2], 'likes': row[3], 'channel_name': row[4]} for row in videos]


def get_video_performance(video_id):
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT
            v.title,
            vs.date_checked,
            vs.view_count,
            vs.likes,
            vs.comments
        FROM
            Video_Stats vs
        JOIN
            Videos v ON vs.video_id = v.video_id
        WHERE
            v.video_id = %s
        ORDER BY
            vs.date_checked ASC;
    """

    cur.execute(query, (video_id,))
    performance = cur.fetchall()
    cur.close()
    conn.close()

    return [{'title': row[0], 'date_checked': row[1], 'view_count': row[2], 'likes': row[3], 'comments': row[4]} for row in performance]


@app.route('/api/channels', methods=['POST'])
def add_channel():
    data = request.json

    if 'channelName' not in data:
        return jsonify({'error': 'channelName is required'}), 400


    channel_id = get_channelId_from_name(data['channelName'])
    if not channel_id:
        return jsonify({'error': 'Channel not found'}), 404


    channel_data = fetch_channel_data(channel_id)

    if 'items' not in channel_data or not channel_data['items']:
        return jsonify({'error': 'Channel not found'}), 404

    channel_info = channel_data['items'][0]

    try:
        conn = get_db_connection()
        cur = conn.cursor()


        cur.execute(
            sql.SQL("INSERT INTO Channel (channel_id, channel_name, total_videos, subscribers) VALUES (%s, %s, %s, %s) ON CONFLICT (channel_id) DO NOTHING;"),
            (
                channel_id,
                channel_info['snippet']['title'],
                int(channel_info['statistics'].get('videoCount', 0)),
                int(channel_info['statistics'].get('subscriberCount', 0))
            )
        )


        video_items = fetch_latest_videos(channel_id)
        video_ids = [video['id']['videoId'] for video in video_items]

        videos = fetch_video_statistics(video_ids)


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



@app.route('/api/channels/<channel_identifier>/summary', methods=['GET'])
def get_channel_summary_route(channel_identifier):
    try:
        if len(channel_identifier) == 24:
            channel_id = channel_identifier
        else:
            channel_id = get_channelId_from_name(channel_identifier)

        if not channel_id:
            return jsonify({'error': 'Channel not found'}), 404

        summary = get_channel_summary(channel_id)
        if summary:
            return jsonify(summary), 200
        else:
            return jsonify({'error': 'Channel not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/videos/popular', methods=['GET'])
def get_popular_videos_route():
    min_views = request.args.get('min_views', default=10000, type=int)
    try:
        popular_videos = get_popular_videos(min_views)
        return jsonify(popular_videos), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/videos/<video_id>/performance', methods=['GET'])
def get_video_performance_route(video_id):
    try:
        performance_data = get_video_performance(video_id)
        if performance_data:
            return jsonify(performance_data), 200
        else:
            return jsonify({'error': 'Video not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    initialize_db()
    app.run(debug=True)
