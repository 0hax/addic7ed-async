import argparse
import asyncio
import ffmpeg
import os
from aiohttp import ClientSession
from addic7ed import Addic7ed
from guessit import guessit


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', '-l', default='en',
                        help='language used to download subtitles')
    parser.add_argument('tvshows', nargs='+')
    return parser.parse_args()


async def get_available_subtitles_from_file(tvshow):
    streams = ffmpeg.probe(tvshow)['streams']
    languages = list()
    for stream in streams:
        if stream['codec_name'] != 'subrip':
            continue
        languages.append(stream['tags']['language'])
    return languages


async def main():
    args = parse_args()
    async with ClientSession() as session:
        for tvshow in args.tvshows:
            available_subtitles = await get_available_subtitles_from_file(tvshow)
            if args.language in available_subtitles:
                print('subtitle already present')
                continue
            # TODO check if the mkv file already has fr subtitles.
            addicted = Addic7ed(session)
            guess = guessit(tvshow)
            # TODO check if srtfile exists already, add -f option?
            subtitle = await addicted.download_subtitle(
                            guess['title'], guess['season'], guess['episode'],
                            language=args.language,
                            prefered_version=guess['release_group']
                      )
            with open(os.path.splitext(tvshow)[0] + '.srt', 'wb') as f:
                f.write(subtitle)

if __name__ == "__main__":
    asyncio.run(main())
