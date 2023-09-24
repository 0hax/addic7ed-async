import argparse
import asyncio
import pprint
import os
from aiohttp_client_cache import CachedSession, FileBackend
from .addic7ed import Addic7ed
from .helpers import lang_in_list, get_sub_lang_from_file
from datetime import timedelta
from guessit import guessit


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', '-l',
                        help='language used to download subtitles',
                        choices=['Arabic',
                                 'Catala',
                                 'English',
                                 'Euskera',
                                 'French',
                                 'Galician',
                                 'German',
                                 'Greek',
                                 'Hungarian',
                                 'Italian',
                                 'Persian',
                                 'Polish',
                                 'Portuguese',
                                 'Romanian',
                                 'Russian',
                                 'Spanish',
                                 'Swedish',
                                 ])
    parser.add_argument(
            '--check-embedded-subtitles', '-c',
            help='check if language is already embedded in the file',
            action='store_true',
            default=False)
    parser.add_argument(
            '--force', '-f',
            help='override existing subtitles',
            default=False)
    parser.add_argument('tvshows', nargs='+')

    return parser.parse_args()

async def download_one_subtitle(args, session, tvshow):
    if args.check_embedded_subtitles:
        embedded_langs = await get_sub_lang_from_file(tvshow)
        print(
            'Available subtitle languages embedded in the file:\n {}'.
            format(pprint.pformat(embedded_langs))
        )
        if await lang_in_list(embedded_langs, args.language):
            print(f'{args.language} Subtitle already embedded in {tvshow}')
            return

    # TODO check if subtitle is synced using some lib
    # TODO support saving multiple subtitles languages .fr.srt ?
    addicted = Addic7ed(session)
    guess = guessit(tvshow)
    srt_file = os.path.splitext(tvshow)[0] + '.srt'
    if os.path.exists(srt_file) and not args.force:
        print(f"Local subtitle already present for {tvshow} at {srt_file}")
        return
    # TODO handle when prefered_version is not found.
    #  Add a way to override it?
    subtitle = await addicted.download_subtitle(
                    guess['title'], guess['season'], guess['episode'],
                    language=args.language,
                    prefered_version=guess['release_group']
              )
    if not subtitle:
        return
    print(f'Subtitle downloaded for {tvshow}')
    with open(srt_file, 'wb') as f:
        f.write(subtitle)


async def download_subtitles(args, session):
    # Create a task for each tvshow
    await asyncio.gather(
        *[asyncio.create_task(download_one_subtitle(args, session, tvshow))
          for tvshow in args.tvshows]
    )


async def main():
    args = parse_args()
    cache = FileBackend(cache_name='.addic7ed_cache',
                        expire_after=timedelta(days=1))
    async with CachedSession(cache=cache) as session:
        try:
            await download_subtitles(args, session)
        finally:
            # Make sure the cache is closed, otherwise a deadlock happens.
            # TODO change this to autoclose=True once available
            await cache.close()


def sync_main():
    asyncio.run(main())


if __name__ == "__main__":
    sync_main()
