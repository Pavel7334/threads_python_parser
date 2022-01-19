import concurrent.futures
import os
import shutil
from typing import IO

import requests
import logging

from threads_parser.utils import timer

logger = logging.getLogger(__name__)


class Album:
    def __init__(self, id_: int, title: str):
        self.id = id_
        self.title = title.replace(' ', '_')

    def __str__(self) -> str:
        return f'{self.title}'


class Photo(Album):
    def __init__(
        self, album_id: int, id_: int, title: str, url: str, file: IO = None
    ):
        self.album_id = album_id
        self.url = url
        self.file = file
        super().__init__(id_, title)

    def __str__(self) -> str:
        return f'{self.title}'


class Parser:
    @staticmethod
    def _get_response(url: str) -> requests.Response:
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            logger.error(e)

    def get_json_by_url(self, url: str) -> dict:
        return self._get_response(url).json()

    def get_file_by_url(self, url: str) -> IO:
        return self._get_response(url).raw


class PhotoSaver:
    @staticmethod
    def _make_directory(path: str):
        if not os.path.exists(path):
            os.mkdir(path)

    def save_photo(self, album: Album, photo: Photo):
        self._make_directory(str(album))
        format_ = photo.file.headers['content-type'].split('/')[-1]
        with open(f'{os.path.join(str(album), str(photo))}.{format_}', 'wb') as file:
            shutil.copyfileobj(photo.file, file)
        # logger.info(f' {photo}.{format_} успешно сохраненно')


@timer
def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as worker:
        p = Parser()
        photos = worker.submit(p.get_json_by_url, 'https://jsonplaceholder.typicode.com/photos/')
        albums = worker.submit(p.get_json_by_url, 'https://jsonplaceholder.typicode.com/albums/')

        albums_dict = {
            album['id']: Album(id_=album['id'], title=album['title']) for album in albums.result()
        }

        ps = PhotoSaver()
        for photo in photos.result():
            worker.submit(ps.save_photo,
                          albums_dict[photo['albumId']],
                          Photo(
                              title=photo['title'],
                              id_=photo['id'],
                              album_id=photo['albumId'],
                              url=photo['url'],
                              file=p.get_file_by_url(photo['url']),
                          ),
                          )


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()


