import argparse
import asyncio
import iso639
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
                        help='language used to download subtitles')
    parser.add_argument(
            '--check-embedded-subtitles', '-c',
            help='check if language is already embedded in the file',
            action='store_true',
            default=False)
    parser.add_argument(
            '--force', '-f',
            help='override existing subtitles',
            action='store_true',
            default=False)
    parser.add_argument(
        '--ignore-release-group', '-i',
        help='ignore release group when downloading subtitles (subtitles may not be in sync)',
        action='store_true',
        default=False)
    parser.add_argument('tvshows', nargs='+')

    args = parser.parse_args()
    # Convert language to Language object.
    args.language = iso639.Language.match(args.language)
    return args


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
    guess = guessit(tvshow)
    for field in ['title', 'season', 'episode']:
        if not guess.get(field):
            raise Exception(f'Cant retrieve {field} from {tvshow}')

    if not guess.get('release_group'):
        if not args.ignore_release_group:
            raise Exception(f'Cant retrieve release group for {tvshow}')
        else:
            print('Missing release group but ignoring thanks to --ignore-release-group')

    addicted = Addic7ed(session)
    # TODO handle when release_group is not found.
    #  Add a way to override it?
    subtitle = await addicted.download_subtitle(
        guess['title'], guess['season'], guess['episode'],
        language=args.language,
        release_group=None if args.ignore_release_group else guess.get('release_group')
    )
    if not subtitle:
        raise Exception(f'No subtitle found for {tvshow}')

    print(f'Subtitle downloaded for {tvshow}')
    srt_file = os.path.splitext(tvshow)[0] + '.srt'
    with open(srt_file, 'wb') as f:
        f.write(subtitle)


async def download_subtitles(args, session):
    tasks = []
    for tvshow in args.tvshows:
        srt_file = os.path.splitext(tvshow)[0] + '.srt'
        if os.path.exists(srt_file) and not args.force:
            print(f"Local subtitle already present for {tvshow} at {srt_file}")
            continue
        tasks.append(asyncio.create_task(download_one_subtitle(args, session, tvshow)))

    # Create a task for each tvshow
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if result:
            print(result)

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
