import aiofiles
import asyncio

from core.models import *
from infra.config import *
from infra.loggings import *
from infra.database import *
from tools.convert_value import *
from tools.path_handler import *
from tools.save_artwork import *
from tools.tags_handler import *

semaphore = asyncio.Semaphore(5)

class Library:
    @staticmethod
    async def stream(hash: str, range: str) -> tuple[bytes, dict[str, any]] | None:
        
        path = await hash_to_track(hash)
        track_info = await Library.get_track_info(hash)
        if not track_info: return

        track_mime = track_info['mime']
        track_size = track_info['size']
        track_chunk = int(track_size * 0.25)
        real_path = get_path(path)

        if range:
            track_range = range.replace("bytes=", "").split("-")
            track_start = int(track_range[0])
            track_end = int(track_range[1]) if track_range[1] else track_start + track_chunk
        else:
            track_start = 0
            track_end = track_start + track_chunk

        logs.debug("Streaming \"%s\" (%s-%s)", track_info['title'], track_start, track_end)
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


    @staticmethod
    async def get_artwork(hash: str, type: int) -> Path | None:
        if type == 0:
            for orig_artwork in conf.IMAGES_DIR.glob(f"{hash}_orig*"):
                if orig_artwork.is_file(): return orig_artwork
        elif type in conf.IMG_SIZE:
            artwork_thumb = conf.IMG_DIR / f"{hash}_{type}.{conf.IMG_TYPE}"
            return artwork_thumb if artwork_thumb .is_file() else None
        else:
            return None


    @staticmethod
    async def get_track_list(page: int, item: int) -> list[dict]:
        return await Library._get_track_list(page - 1, item)


    @staticmethod
    async def get_track_info(hash: str) -> tuple[list[dict], dict]:
        return await Library._get_track_info(hash)


    @staticmethod
    async def _get_track_list(page: int, item: int) -> list[dict]:
        try:
            async with session() as conn:
                db_query = (
                    select(
                        Tracks.title,
                        Tracks.album,
                        Tracks.artist,
                        Tracks.albumartist,
                        Tracks.hash,
                        Tracks.albumhash,
                    )
                    .order_by(Tracks.title.asc())
                    .offset(page)
                    .limit(item)
                )

                db_result = await conn.execute(db_query)
                track_list = [dict(row) for row in db_result.mappings().all()]

                return track_list
            
        except OperationalError as error:
            logs.error("Failed to load track list, %s", error)
            raise error


    @staticmethod
    async def _get_track_info(hash: str) -> dict:
        try:
            path = await hash_to_track(hash)
            async with session() as conn:
                db_query = (
                    select(Tracks.__table__)
                    .where(Tracks.path == path)
                )

                db_result = await conn.execute(db_query)
                track_info = dict(db_result.mappings().first())

                return track_info
            
        except OperationalError as error:
            logs.error("Failed to load track info, %s", error)
            raise error
        

    @staticmethod
    async def get_album_list(page: int, item: int) -> list[dict]:
        return await Library._get_album_list(page - 1, item)


    @staticmethod
    async def get_album_info(hash: str) -> tuple[list[dict], dict]:
        return await Library._get_album_info(hash)


    @staticmethod
    async def _get_album_list(page: int, item: int) -> list[dict]:
        try:
            async with session() as conn:
                db_query = (
                    select(Albums.__table__)
                    .order_by(Albums.album.asc())
                    .offset(page)
                    .limit(item)
                )

                db_result = await conn.execute(db_query)
                album_list = [dict(row) for row in db_result.mappings().all()]
                
                return album_list
            
        except OperationalError as error:
            logs.error("Failed to load album list, %s", error)
            raise error


    @staticmethod
    async def _get_album_info(hash: str) -> dict:
        try:
            async with session() as conn:
                album_query = select(Albums.__table__).where(Albums.albumhash == hash)
                album_result = await conn.execute(album_query)
                album_info = album_result.mappings().first()

                if album_info:
                    album_info = dict(album_info)
                    track_query = (
                        select(
                            Tracks.title,
                            Tracks.artist,
                            Tracks.duration,
                            Tracks.track,
                            Tracks.hash,
                            Tracks.albumhash,
                            Tracks.artisthash,
                        )
                        .order_by(Tracks.track.asc())
                        .where(Tracks.albumhash == hash)
                    )

                    track_result = await conn.execute(track_query)
                    album_info['tracks'] = [dict(track) for track in track_result.mappings().all()]

                    return album_info
                
                else:
                    return {}
                
        except OperationalError as error:
            logs.error("Failed to load album info, %s", error)
            raise error
        

    @staticmethod
    async def get_artist_list(page: int, item: int) -> list[dict]:
        return await Library._get_artist_list(page - 1, item)


    @staticmethod
    async def get_artist_info(hash: str) -> tuple[list[dict], dict]:
        pass


    @staticmethod
    async def _get_artist_list(page: int, item: int) -> list[dict]:
        try:
            async with session() as conn:
                db_query = (
                    select(Artists.__table__)
                    .order_by(Artists.artist.asc())
                    .offset(page)
                    .limit(item)
                )

                db_result = await conn.execute(db_query)
                artist_list = [dict(row) for row in db_result.mappings().all()]
                
                return artist_list
            
        except OperationalError as error:
            logs.error("Failed to load artist list, %s", error)
            raise error



class LibraryTask:
    def __init__(self, path: str) -> None:
        self.path = path
        self.tags = {}
        

    async def create_track(self) -> None:
        self.tags = await extract_tags(self.path)

        async with semaphore:
            async with session() as conn:
                try:
                    logs.debug("Inserting \"%s\"", self.tags.get('title'))
                    await LibraryRepo.insert_track(conn, self.tags)
                    await conn.commit()

                except Exception as error:
                    logs.error("LibraryTask: Failed to create track: %s", error)
                    await conn.rollback()


    async def remove_track(self) -> None:
        async with semaphore:
            async with session() as conn:
                try:
                    logs.debug("Removing \"%s\"", self.path)
                    await LibraryRepo.delete_track(conn, self.path)
                    await conn.commit()

                except Exception as error:
                    logs.error("LibraryTask: Failed to remove track: %s", error)
                    await conn.rollback()


    @staticmethod
    async def create_artwork(hash: str) -> None:
        try:
            async with session() as conn:
                query = select(Tracks.path).where(Tracks.albumhash == hash)
                result = await conn.execute(query)

                data = result.mappings().first()
                if data: data = dict(data)

                artwork = await extract_artwork(data.get('path'))
                if artwork:
                    await save_artwork(artwork, hash)
                else:
                    logs.debug("Failed to extract artwork.")
                    
        except Exception as error:
            logs.error('error %s', error)


    @staticmethod
    async def remove_artwork(hash: str) -> None:
        pass



class LibraryScan:
    def __init__(self) -> None:
        pass

    
    @staticmethod
    async def perform_albums() -> None:
        async with session() as conn:
            try:
                db_query = (
                    select(
                        Tracks.album,
                        Tracks.albumartist,
                        Tracks.tracktotal,
                        Tracks.disctotal,
                        Tracks.year,
                        func.sum(Tracks.duration).label('totalduration'),
                        func.sum(Tracks.size).label('totalsize'),
                    )
                    .group_by(
                        Tracks.album,
                        Tracks.albumartist,
                        Tracks.tracktotal,
                    )
                )

                db_result = await conn.execute(db_query)
                albums_data = db_result.all()

                for alb in albums_data:
                    albumhash = get_hash_str(
                        f'{alb.album}-{alb.albumartist}-{alb.tracktotal}-{alb.year}'
                    )
                    albumartisthash = get_hash_str(alb.albumartist)

                    update_track = (
                        update(Tracks)
                        .where(
                            Tracks.album == alb.album,
                            Tracks.albumartist == alb.albumartist,
                            Tracks.tracktotal == alb.tracktotal,
                        )
                        .values(albumhash=albumhash)
                        .execution_options(synchronize_session='fetch')
                    )

                    album_data = {
                        'album': alb.album,
                        'albumartist': alb.albumartist,
                        'albumartisthash': albumartisthash,
                        'albumhash': albumhash,
                        'durationtotals': alb.totalduration,
                        'sizetotals': alb.totalsize,
                        'tracktotals': alb.tracktotal,
                        'disctotals': alb.disctotal,
                        'year': alb.year,
                    }

                    await conn.execute(update_track)
                    await LibraryRepo.insert_album(conn, album_data)

                await conn.commit()

            except Exception as error:
                logs.error("Failed to perform albums, %s", error)
                await conn.rollback()

    
        async with session() as conn:
            try:
                albums_query = select(Albums.albumhash)
                result = await conn.execute(albums_query)
                album_hash = {row.albumhash for row in result}

                tracks_query = select(Tracks.albumhash).distinct()
                result = await conn.execute(tracks_query)
                track_hash = {row.albumhash for row in result}

                find = album_hash - track_hash # 중복 없애고 set으로 차집합 연산

                for albumhash in find:
                    logs.debug("Removing Album %s", albumhash)
                    await LibraryRepo.delete_album(conn, albumhash)

                await conn.commit()

            except Exception as error:
                logs.error("Failed to fetch untracked albums, %s", error)
                await conn.rollback()


    @staticmethod
    async def perform_artists() -> None:
        pass



class LibraryRepo:
    @staticmethod
    async def insert_track(conn: AsyncSession, tags: dict) -> bool:
        try:
            await conn.execute(
                insert(Tracks).values(**tags)
            )
            return True
        
        except OperationalError as error:
            logs.error("LibraryRepo: Failed to insert track, %s", error)
            raise


    @staticmethod
    async def insert_album(conn: AsyncSession, tags: dict) -> bool:
        try:
            await conn.execute(
                Insert(Albums).values(**tags)
                .on_conflict_do_nothing()
            )
            return True
        
        except OperationalError as error:
            logs.error("LibraryRepo: Failed to insert album, %s", error)
            raise


    @staticmethod
    async def delete_track(conn: AsyncSession, path: str) -> bool:
        try:
            await conn.execute(
                delete(Tracks).where(Tracks.path == path)
            )
            return True
        
        except OperationalError as error:
            logs.error("LibraryRepo: Failed to delete track, %s", error)
            raise


    @staticmethod
    async def delete_album(conn: AsyncSession, hash: str) -> bool:
        try:
            await conn.execute(
                delete(Albums).where(Albums.albumhash == hash)
            )
            return True
        
        except OperationalError as error:
            logs.error("LibraryRepo: Failed to delete album, %s", error)
            raise