from core.convert_tools import *
from core.extract_tags import *
from infra.convert_image import *
from infra.database import *
from infra.path_handler import *
from infra.setup_logger import *
import aiofiles

class TracksService:
    def __init__(self, path: str):
        self.path = path

    async def stream(self, range):  
        track_info = await self.info(self.path)
        real_path = get_path(self.path)

        if track_info:
            track_mime = track_info['mime']
            track_size = track_info['size']
            track_chunk = int(track_size * 0.25)

            if range:
                track_range = range.replace("bytes=", "").split("-")
                track_start = int(track_range[0])
                track_end = int(track_range[1]) if track_range[1] else track_start + track_chunk
            else:
                track_start = 0
                track_end = track_start + track_chunk
            track_end = min(track_end, track_size - 1)

            async with aiofiles.open(real_path, mode="rb") as track_file:
                await track_file.seek(track_start)
                data = await track_file.read(track_end - track_start + 1)
                headers = {
                    'Content-Range': f'bytes {track_start}-{track_end}/{track_size}',
                    'Accept-Ranges': 'bytes',
                    'Content-Length': str(track_end - track_start + 1),
                    'Content-Type': track_mime
                }

                return data, headers
        else:
            raise LookupError('Failed to lookup the tags data.')

    async def create(self):
        list_tags = [column.name for column in tracks.columns]
        tags = ExtractTags(self.path)
        self.track_tags = await tags.extract_tags(list_tags)

        if not self.track_tags:
            logs.debug("Failed to read tags. Is it a valid file?")
            return False
        
        try:
            await db.execute(tracks.insert().values(self.track_tags))
            return True
        
        except ValueError as error:
            logs.error("Failed to insert data into the database. %s", error)
            return False

    async def remove(self):
        try:
            await db.execute(tracks.delete().where(tracks.c.path == self.path))
        except:
            logs.error("Failed to remove track.")
            return False

    @staticmethod
    async def list(num: int) -> list:
        track_tags = []
        tags_select = await db.fetch_all(
            tracks.select().with_only_columns(
                [
                    tracks.c.title,
                    tracks.c.artist,
                    tracks.c.album,
                    tracks.c.year,
                    tracks.c.id,
                    tracks.c.albumid,
                    tracks.c.artistid
                ]
            ).order_by(
                tracks.c.album.desc(),
                tracks.c.tracknumber.asc()
            ).limit(num)
        )

        if tags_select: [track_tags.append(dict(tag)) for tag in tags_select]

        return track_tags

    @staticmethod
    async def info(path: str) -> dict:
        print(path)
        id = get_hash_str(path)
        print(id)
        track_info = {}

        track_data = await db.fetch_all(tracks.select().where(tracks.c.id == id))
        for data in track_data:
            track_info = dict(data)
            print(track_data)

        try:
            track_data = await db.fetch_all(tracks.select().where(tracks.c.id == id))
            for data in track_data: track_info = dict(data)
        except:
            logs.error("Failed to load the track information.")

        print(track_info)

        return track_info