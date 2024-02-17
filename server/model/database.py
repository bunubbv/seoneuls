from databases import Database
from tools.path import *
from .logger import *
import sqlalchemy
import asyncio

db_url = get_path('data', 'tamaya.db', is_rel=False, is_str=False)
DATABASE_URL = "sqlite:///" + db_url.as_posix()

metadata = sqlalchemy.MetaData()
music = sqlalchemy.Table(
    "music",
    metadata,
    sqlalchemy.Column("album", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("albumid", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("albumsort", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("albumartist", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("albumartistsort", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("artist", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("artistid", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("artistsort", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("barcode", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("bitrate", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("bpm", sqlalchemy.Integer, nullable=False),
    # sqlalchemy.Column("catalognumber", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("channels", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("comment", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("compilation", sqlalchemy.Boolean(False), nullable=False),
    sqlalchemy.Column("composer", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("composersort", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("conductor", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("contentgroup", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("copyright", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("createdate", sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column("date", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("description", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("discnumber", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("disctotal", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("duration", sqlalchemy.REAL, nullable=False),
    sqlalchemy.Column("genre", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("grouping", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("id", sqlalchemy.String(''), nullable=False, primary_key=True),
    # sqlalchemy.Column("involved_people", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("image_id", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("isrc", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("label", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("language", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("lyricist", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("lyrics", sqlalchemy.JSON, nullable=False),
    sqlalchemy.Column("mime", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("mix_artist", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("musicbrainz_albumartistid", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("musicbrainz_albumid", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("musicbrainz_albumtype", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("musicbrainz_artistid", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("musicbrainz_discid", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("musicbrainz_originalalbumid", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("musicbrainz_originalartistid", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("musicbrainz_releasegroupid", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("musicbrainz_releasetrackid", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("musicbrainz_trackid", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("orignalalbum", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("orignalartist", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("orignallyricist", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("orignalyear", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("path", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("publisher", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("releasetype", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("releasetime", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("samplerate", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("script", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("setsubtitle", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("size", sqlalchemy.Integer, nullable=False),
    # sqlalchemy.Column("subtitle", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("title", sqlalchemy.String(''), nullable=False),
    # sqlalchemy.Column("titlesort", sqlalchemy.String(''), nullable=False),
    sqlalchemy.Column("tracknumber", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("tracktotal", sqlalchemy.Integer, nullable=False),
    sqlalchemy.Column("year", sqlalchemy.Integer, nullable=False),
)

if not db_url.exists():
    engine = sqlalchemy.create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}
    )
    metadata.create_all(engine)
    database = Database(DATABASE_URL)
    logs.debug("Creating new database...")
else:
    database = Database(DATABASE_URL)
    logs.debug("Initializing database...")

async def connect_database():
    await database.connect()
    logs.debug("Connected to database successfully.")

async def disconnect_database():
    await database.disconnect()

async def get_abs_path_from_id(value: str) -> Path:
    query = music.select().with_only_columns([music.c.path]).where(music.c.id == value)
    result = await database.fetch_one(query)

    if result is not None:
        path = get_path(result.path, is_rel=False, is_str=False)
        return path
    else:
        logs.error("Failed to load: ID not found in database.")
        return None