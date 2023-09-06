import re


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


async def lang_in_list(embedded_langs, requested_lang):
    for lang in embedded_langs:
        # Usually 2 first letters are enough to match against ISO
        # 3166-2 standards.
        if re.match(r"{}?".format(requested_lang[0:2]),
                    lang, re.IGNORECASE):
            return True
    return False
