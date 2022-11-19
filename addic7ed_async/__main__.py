import argparse
import asyncio
import os
import re
from aiohttp_client_cache import CachedSession, FileBackend
from addic7ed import Addic7ed
from datetime import timedelta
from guessit import guessit


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', '-l', default='en',
                        help='language used to download subtitles')
    parser.add_argument('--check-embedded-subtitles', '-c',
                        help='check if language is already embedded in the file',
                        default=True)
    parser.add_argument('tvshows', nargs='+')
    return parser.parse_args()


async def get_sub_lang_from_file(tvshow):
    try:
        import ffmpeg
    except ImportError:
        return []
    streams = ffmpeg.probe(tvshow)['streams']
    languages = list()
    for stream in streams:
        if stream['codec_name'] != 'subrip':
            continue
        if not stream.get('tags'):
            continue
        languages.append(stream['tags']['language'])
    return languages


async def embedded_langs_match(embedded_langs, requested_lang):
    for lang in embedded_langs:
        # Usually 2 first letters are enough to match against ISO
        # 3166-2 standards.
        if re.match(r"{}?".format(requested_lang[0:2]),
                    lang, re.IGNORECASE):
            return True
    return False


async def main():
    args = parse_args()
    # TODO Add flush cache option and recommend it in case of exception
    # 1 day for clearing is ok.
    cache = FileBackend(cache_name='.addic7ed_cache',
                        expire_after=timedelta(days=1))
    async with CachedSession(cache=cache) as session:
        for tvshow in args.tvshows:
            if args.check_embedded_subtitles:
                embedded_langs = await get_sub_lang_from_file(tvshow)
                if await embedded_langs_match(embedded_langs, args.language):
                    print(f'{args.language} Subtitle already present in {tvshow}')
                    continue

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
