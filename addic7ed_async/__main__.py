import argparse
import asyncio
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


async def main():
    args = parse_args()
    async with ClientSession() as session:
        for tvshow in args.tvshows:
            # TODO check if the mkv file already has fr subtitles.
            addicted = Addic7ed(session)
            guess = guessit(tvshow)
            # TODO check if srtfile exists already, add -f option?
            subtitle = await addicted.download_subtitle(
                            guess['title'], guess['season'], guess['episode'],
                            language=args.language,
                            prefered_version=guess['release_group']
                      )
            with open(os.path.splitext(tvshow)[0] + '.srt', 'w') as f:
                f.write(subtitle)

if __name__ == "__main__":
    asyncio.run(main())
