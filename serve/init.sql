CREATE TABLE IF NOT EXISTS Channel (
    channel_id VARCHAR(50) PRIMARY KEY,
    channel_name VARCHAR(255) NOT NULL,
    total_videos INT DEFAULT 0,
    subscribers INT DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS Videos (
    video_id VARCHAR(50) PRIMARY KEY,
    channel_id VARCHAR(50) REFERENCES Channel(channel_id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    published_at TIMESTAMP NOT NULL,
    duration INT NOT NULL,
    view_count INT DEFAULT 0,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    type VARCHAR(10) CHECK (type IN ('Short', 'Long'))
);

CREATE TABLE IF NOT EXISTS Metrics (
    metrics_id SERIAL PRIMARY KEY,
    channel_id VARCHAR(50) REFERENCES Channel(channel_id) ON DELETE CASCADE,
    calculation_date TIMESTAMP NOT NULL DEFAULT NOW(),
    median_viewership INT DEFAULT 0,
    upload_frequency VARCHAR(20),
    short_videos_count INT DEFAULT 0,
    long_videos_count INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS Video_Stats (
    stat_id SERIAL PRIMARY KEY,
    video_id VARCHAR(50) REFERENCES Videos(video_id) ON DELETE CASCADE,
    date_checked TIMESTAMP NOT NULL DEFAULT NOW(),
    view_count INT DEFAULT 0,
    likes INT DEFAULT 0,
    comments INT DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_channel_id ON Videos (channel_id);
CREATE INDEX IF NOT EXISTS idx_published_at ON Videos (published_at);
