import iso639

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
        if iso639.Language.match('lang') == requested_lang:
            return True
    return False
