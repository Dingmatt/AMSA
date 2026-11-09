# -*- coding: utf-8 -*-
"""AMSA Series Scanner - a lean, offline anime series scanner for the AMSA metadata agent.

It reports what AMSA reads (show name with optional forced id and folder year, season and episode
numbers in Plex/TVDB style, the file parts) and nothing else. Folder and file names written for
Absolute Series Scanner (ASS) work too.

  * no network access: everything is worked out from the folder and file names;
  * every regular expression is compiled once at import;
  * one log line per file, no per-character logging.

Folder layout (standard Plex):  <library>/<Show [anidb-123]>/<Season 01 | Specials>/<files>
Episode numbers: SxxEyy, 1x01, "Show - 05", E05, #05, 01-02 (multi-episode), 12.5 (special),
specials SP1 / S1 / Special 1 / OAD 1 -> S00E01, openings OP1 / NCOP1 -> S00E101,
endings ED1 / NCED1 -> S00E151, trailers / PV / CM -> S00E201, others -> S00E401,
unrecognised files -> S00E501 and up.

Runs on Plex's Python 2.7 and on Python 3 (used by the command-line test harness).
"""
import os
import re
import sys
import fnmatch
import inspect
import logging
import logging.handlers

VERSION = "1.0.0"
LOG_NAME = "Plex Media Scanner (AMSA Series Scanner).log"

PY2 = sys.version_info[0] == 2
if PY2:
    TEXT = unicode  # noqa: F821 - Python 2 only
else:
    TEXT = str

try:
    import Media                                     # Plex Media Server scanner module
except ImportError:
    Media = None
try:
    import Stack                                     # Plex: stacks cd1/cd2, part1/part2 files
except ImportError:
    Stack = None


# Logging ##################################################################################################################
def make_logger():
    logger = logging.getLogger("amsa_series_scanner")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    log_dir = os.environ.get("AMSA_SCANNER_LOG_DIR")
    if not log_dir:
        try:
            here = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
            log_dir = os.path.abspath(os.path.join(here, "..", "..", "Logs"))   # Scanners/Series -> <Plex data>/Logs
        except Exception:
            log_dir = ""
    try:
        if log_dir and os.path.isdir(log_dir):
            handler = logging.handlers.RotatingFileHandler(os.path.join(log_dir, LOG_NAME), maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S"))
            logger.addHandler(handler)
    except Exception:
        pass
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


Log = make_logger()


# Text helpers ##############################################################################################################
def to_text(value):
    """Unicode version of a path or name (Plex passes UTF-8 byte strings on Python 2)."""
    if value is None:
        return u""
    if isinstance(value, TEXT):
        return value
    for encoding in ("utf-8", sys.getfilesystemencoding() or "utf-8"):
        try:
            return value.decode(encoding)
        except Exception:
            pass
    return value.decode("latin-1", "replace")


def to_plex(value):
    """Plex's Media.Episode expects UTF-8 byte strings on Python 2."""
    if PY2 and isinstance(value, TEXT):
        return value.encode("utf-8")
    return value


def rx(pattern):
    return re.compile(pattern, re.IGNORECASE | re.UNICODE)


# Files and folders to skip #################################################################################################
VIDEO_EXTS = set("3g2 3gp asf asx avc avi avs bin bivx divx dv dvr-ms evo fli flv ifo img iso m2t m2ts m2v m4v mkv mov mp4 "
                 "mpeg mpg mts nrg nsv nuv ogm ogv pva qt rm rmvb sdp strm svq3 swf tp trp ts ty vdr viv vp3 webm wmv wpl wtv "
                 "xsp xvid".split())
# Folder basenames (whole name, case-insensitive). Plex's local-extras folders are skipped so their files don't become episodes.
IGNORE_DIR_RX = rx(r"^(?:[._].*|@Recycle|@eaDir|@Recently-Snapshot|lost\+found|\$Recycle\.Bin|System Volume Information|Temporary Items|"
                   r"Network Trash Folder|Extras?|Samples?|Bonus|.*bonus disc.*|Trailers?|.*_UNPACK_.*|.*_FAILED_.*|Misc|Audio|Subs?|"
                   r"Subtitles?|Fonts?|Scans?|.*Special Features|Featurettes?|Behind The Scenes|Deleted Scenes|Interviews|Scenes|"
                   r"Shorts|Plex Versions|Optimized for .*)$")
IGNORE_FILE_RX = rx(r"(?:^|[ _.\-])sample(?:[ _.\-]|$)|[ _.\-]recap$|^\._|^_|^(?:OST|soundtrack)\b")

# Sub-folders of a series folder
SPECIALS_FOLDER_RX = rx(u"^(?:specials?|speciali|sps?|ovas?|oads?|oavs?|映像特典)$")
SEASON_FOLDER_RX = [
    rx(r"^(?:.*?[ ._\-])?(?:season|series|saison|temporada|stagione|staffel|book|s)[ ._\-]*(?P<season>\d{1,4})(?:[ ._\-].*)?$"),
    rx(r"^(?:.*?[ ._\-])?(?P<season>\d{1,2})(?:st|nd|rd|th)[ ._\-]*season(?:[ ._\-].*)?$"),
    rx(r"^(?P<season>\d{1,2})a? stagione.*$"),
]
TRANSPARENT_FOLDER_RX = rx(r"^(?:saga|(?:story )?ar[ck]|cour|part|disc|disk|dvd|cd|vol(?:ume)?|bdmv|stream|video_ts)\b.*$")

# Forced ids. AMSA reads "[anidb-123]" / "[tvdb-456]" from the show name; ASS-style id files are supported too.
FORCED_ID_RX = rx(r"[\[\{](?P<source>anidb[2-4]?|tvdb[2-6]?|tmdb|tsdb|imdb|mal)-(?P<id>(?:tt)?\d{1,8})(?P<offset>-[^\]\}]*)?[\]\}]")
OFFSET_RX = rx(r"^-(?:s(?P<season>\d{1,3}))?(?:e(?P<episode>-?\d{1,4}))?$")             # [tvdb-123-s2] / [tvdb-123-e13] / [tvdb-123-s2e13]
ID_FILES = ["anidb.id", "anidb2.id", "anidb3.id", "anidb4.id", "tvdb.id", "tvdb2.id", "tvdb3.id", "tvdb4.id", "tvdb5.id",
            "tmdb.id", "tsdb.id", "imdb.id", "mal.id"]


# Name cleaning #############################################################################################################
# Release tags removed as whole phrases (before dots/underscores become spaces), longest first
JUNK_PHRASES = [
    "x264-FMD Release", "x264-h65", "x264-mSD", "x264-BAJSKORV", "x264-MgB", "x264-SYS", "x264-FQM", "x264-ASAP", "x264-QCF", "x264-W4F",
    "x264-AAC", "x264-2hd", "x264-batv", "x264-EXCELLENCE", "x264-KILLERS", "x264-LOL", "x264-SnowDoN", "x264-xRed", "x264-RedBlade",
    "x264-CTR", "x265-NTb", "H.264-iT00NZ", "H.264.iT00NZ", "H264-PublicHD", "H.264-BS", "H_264_iT00NZ", "H.264_AAC", "REAL.HDTV",
    "WEB.DL", "WEB_DL", "WEB-DL", "WEBDL", "DCU.WEB-DL", "NF.WEBRip.by.AKTEP", "www.crazy-torrent.com", "minitheatre.org",
    "XviD-2HD", "XviD-AFG", "xvid-aldi", "xvid-asap", "XviD-AXED", "XviD-BiA-mOt", "xvid-fqm", "xvid-futv", "xvid-killer", "XviD-LMAO",
    "xvid-pfa", "xvid-saints", "XviD-T00NG0D", "XViD-ViCKY", "XviD-BiA", "XVID-FHW", "PROPER-LOL", "REPACK-LOL", "HDTV-AFG", "HDTV-LMAO",
    "hdtv-lol", "HDTV-RIP", "OAR XviD-BiA-mOt", "OAR HDTV-BiA-mOt", "mthd bd dual", "Dual Audio", "Dual.Audio", "Tri.Audio",
    "BD 10-bit", "BD 1080p", "BD 960p", "BD 720p", "BD_720p", "TV 720p", "DVD 480p", "DVD 476p", "DVD 432p", "DVD 336p", "1080p.BluRay",
    "1080p-Hi10p", "Blu-Ray", "SD TV", "SD DVD", "HD TV", "dvd-jap", "AC3.5.1", "AC3-5.1", "AAC2.0", "AAC.2.0", "AAC2_0", "DD2.0", "DD2.1",
    "DD5.1", "DD5_1", "DDP5.1", "DDP2.0", "FLAC5.1", "FLAC2.0", "Opus 2.0", "Opus 5.1", "Opus 7.1", "5.1ch", "7.1ch", "dub.sub_ja+.ru+",
    "dub.sub_en.ja", "VO.ENG.Subs", "2xDVO.MVO", "2xRus.Eng", "YUV420P10", "10Bits-WKN", "Zone-Telechargement.Ws", "Zone-Telechargement",
    "AniLibria.TV", "AI-Raws", "philosophy-raws", "VCB-S", "Despair-Paradise", "- copy", "H.264", "H.265", "H 264", "H 265", "DD+5.1",
    "DDP 5.1", "AAC 2.0", "FLAC 2.0", "Hi10P", "Hi-10P",
]
JUNK_PHRASES_RX = rx(u"(?<![^\\W_])(?:%s)(?![^\\W_])" % u"|".join([re.escape(x) for x in sorted(JUNK_PHRASES, key=len, reverse=True)]))
# Release tags removed as whole words (after cleaning), lower case
JUNK_WORDS = set((
    "x264 x265 h264 h265 hevc avc xvid divx divx5 divx51 dxva 8bit 8-bit 10bit 10-bit 10bits hi10 hi10p crf24 hdr hdr10 sdr "
    "480p 576p 720p 1080p 1080i 2160p 4k uhd 24fps 25fps ntsc pal ntsc-u ntsc-j "
    "mp3 ogg vorbis aac aac2 eac3 ac3 ac-3 dts dts-hd truehd thd flac opus qaac pcm lpcm 5.1 7.1 "
    "dual-audio multi multisubs multi-subs dubbed dub subbed subs sub engsub eng jap jpn rus vostfr "
    "uncensored uncen unc censored cen remastered remux repack proper rerip reenc internal "
    "bluray blu-ray bdrip bdremux brrip bdrc bd bdmv hdrip hddvd hddvdrip dvdrip dvdremux dvd dvd5 dvd9 r1 r2 r3 r5 "
    "webrip web-rip web-dl webdl web hdtv hdtvrip pdtv dsr dsrip tvrip dvb hdtv-rip "
    "cd1 cd2 cd3 cd4 nfo nfofix mkv mp4 avi hq creditless "
    "horriblesubs subsplease erai-raws commie coalgirls doremi fff hatsuyuki shimeji rizlim subtidal anxious-he "
    "darkdream exileddestiny exiled-destiny ocz 3xr newstudio exkinoray ntb wkn dragonmax mawen1250 casstudio the0x539"
).split())
BRACKET_RX = re.compile(u"\\[([^\\[\\]]*)\\]|\\{([^{}]*)\\}|【([^【】]*)】", re.UNICODE)
PAREN_RX = re.compile(r"\(([^()]*)\)", re.UNICODE)
KEEP_BRACKET_RX = rx(r"^\s*(?:\d{1,4}(?:\.\d)?(?:v\d)?|(?:ep?|sp|op|ed|ncop|nced|oad|oav)\s?\d{1,3}[a-z]?(?:v\d)?|s\d{1,4}\s?e\d{1,4}.*)\s*$")
KEEP_PAREN_RX = rx(r"^\s*(?:\d{1,3}(?:\.\d)?(?:v\d)?|s\d{1,4}\s?e\d{1,4}.*)\s*$")        # "(05)" stays, "(2009)" goes
JAPANESE_EPISODE_RX = re.compile(u"第?(\\d{1,4})[話话集]", re.UNICODE)       # 第01話 / 01话 / 01集
DOT_RX = re.compile(r"(?<!\d)\.|\.(?!\d)")                                                     # dots, except in "12.5"
CRC_RX = re.compile(r"(?<![0-9A-Za-z])[0-9A-Fa-f]{8}(?![0-9A-Za-z])")
RESOLUTION_RX = rx(u"(?<!\\d)\\d{3,4} ?[x×] ?\\d{3,4}(?!\\d)|(?<![0-9a-z])\\d{3,4}[pi](?![0-9a-z])")
FILTER_CHARS_RX = re.compile(u"[\\\\/:*?<>|;　：]")
SPACES_RX = re.compile(r"\s+", re.UNICODE)
WORDS_ONLY_RX = re.compile(r"[\W_]+", re.UNICODE)


def keep_bracket(match):
    inner = match.group(1) if match.group(1) is not None else (match.group(2) if match.group(2) is not None else match.group(3))
    return u" %s " % inner if KEEP_BRACKET_RX.match(inner or u"") else u" "


def keep_paren(match):
    inner = match.group(1)
    return u" %s " % inner if KEEP_PAREN_RX.match(inner) else u" "


def normalise(name):
    """Filename or folder name -> words without release tags, brackets, CRCs or resolutions (case kept)."""
    text = to_text(name)
    text = JAPANESE_EPISODE_RX.sub(u" \\1 ", text)
    text = BRACKET_RX.sub(keep_bracket, text)
    previous = None
    while previous != text:                           # nested parentheses
        previous, text = text, PAREN_RX.sub(keep_paren, text)
    text = text.replace(u"(", u" ").replace(u")", u" ")
    text = JUNK_PHRASES_RX.sub(u" ", text)
    text = text.replace(u"_", u" ")
    text = DOT_RX.sub(u" ", text)
    text = FILTER_CHARS_RX.sub(u" ", text)
    text = CRC_RX.sub(u" ", text)
    text = RESOLUTION_RX.sub(u" ", text)
    return u" ".join([word for word in text.split() if word.lower() not in JUNK_WORDS])


def simplified(text):
    """Lower case, punctuation removed - for comparing a filename with the show name."""
    return SPACES_RX.sub(u" ", WORDS_ONLY_RX.sub(u" ", text.lower())).strip()


def forced_id(folder):
    """('[tvdb-123]', season offset, episode offset) from a folder name; ASS-style offsets: -s2 = file season 1 is season 2,
       -e13 = file episode 1 is episode 13. The offset is applied here, so AMSA always receives a plain [source-id]."""
    match = FORCED_ID_RX.search(to_text(folder))
    if not match:
        return u"", 0, 0
    season_offset, episode_offset = 0, 0
    offset = OFFSET_RX.match(match.group("offset") or u"")
    if offset:
        if offset.group("season"):
            season_offset = int(offset.group("season")) - 1
        if offset.group("episode"):
            episode_offset = int(offset.group("episode")) - (1 if int(offset.group("episode")) > 0 else 0)
    return u"[%s-%s]" % (match.group("source").lower(), match.group("id")), season_offset, episode_offset


def display_show(folder):
    """Show name passed to Plex/AMSA: folder name without release tags, keeping '(2009)' and a forced id tag."""
    text = to_text(folder)
    tag = forced_id(text)[0]
    text = FORCED_ID_RX.sub(u" ", text)
    text = BRACKET_RX.sub(u" ", text)
    text = text.replace(u"_", u" ")
    if u" " not in text.strip() and text.count(u".") > 1:
        text = DOT_RX.sub(u" ", text)
    text = FILTER_CHARS_RX.sub(u" ", text)
    text = SPACES_RX.sub(u" ", text).strip(u" -")
    for article in (u"The", u"A"):
        if text.endswith(u", " + article):
            text = article + u" " + text[:-len(article) - 2]
    return (text + u" " + tag).strip() if tag else text


# Episode detection #########################################################################################################
SXXEYY_RX = rx(r"(?:^|(?<=[\s\-]))s(?P<season>\d{1,4})[ .\-]?ep?(?P<ep>\d{1,4})(?:(?:-|-?ep?|[ .]ep?)(?P<ep2>\d{1,4}))?(?!\d)")
NXNN_RX = rx(r"(?:^|(?<=[\s\-]))(?P<season>\d{1,2})x(?P<ep>\d{1,4})(?:[\-x](?P<ep2>\d{1,4}))?(?!\d)")
ORDINAL_SEASON_RX = rx(r"(?:^|\s)(?P<season>\d{1,2})(?:st|nd|rd|th)\s+season(?=\s|$)")
NUMBER_RX = re.compile(r"^(?P<ep>\d{1,4})(?:-(?P<ep2>\d{1,4}))?$")
DECIMAL_RX = re.compile(r"^(?P<ep>\d{1,3})\.(?P<part>\d{1,2})$")
PREFIXED_RX = rx(r"^(?:ep|e|episode|act|#)(?P<ep>\d{1,4})(?:-(?:ep?)?(?P<ep2>\d{1,4}))?$")
SEASON_TOKEN_RX = rx(r"^s(?P<n>\d{1,3})$")
VERSION_RX = rx(r"(?<=\d)v\d$")
SPECIAL_RX = rx(r"^(?P<kind>sp|special|specials|oad|oav|ncop|op|opening|nced|ed|ending|pv|promo|trailer|cm|preview|others?|o|t)"
                r"(?P<n>\d{1,3})?(?P<letter>[a-z])?$")
# Kind -> (first episode number in season 0, needs a number, rule name)
SPECIAL_KINDS = {"sp": (0, True, "special"), "special": (0, True, "special"), "specials": (0, True, "special"), "oad": (0, True, "special"),
                 "oav": (0, True, "special"), "op": (100, False, "opening"), "ncop": (100, False, "opening"), "opening": (100, False, "opening"),
                 "ed": (150, False, "ending"), "nced": (150, False, "ending"), "ending": (150, False, "ending"), "pv": (200, False, "trailer"),
                 "promo": (200, False, "trailer"), "trailer": (200, False, "trailer"), "cm": (200, False, "trailer"), "preview": (200, False, "trailer"),
                 "t": (200, True, "trailer"), "o": (400, True, "other"), "other": (400, False, "other"), "others": (400, False, "other")}
MOVIE_WORDS_RX = rx(r"\b(?:movie|gekijouban|the movie|film)\b")
UNKNOWN_START = 500


class Parsed(object):
    def __init__(self, season, episode, episode2=None, rule="", title=u"", show=u""):
        self.season = season
        self.episode = episode
        self.episode2 = episode2 if episode2 and episode2 > episode else episode
        self.rule = rule
        self.title = title
        self.show = show


WORD_RX = re.compile(r"\S+", re.UNICODE)


def strip_show(text, show_simple):
    """Remove the show name from the start of a normalised filename (punctuation-insensitive, e.g. 'Steins Gate 0' / 'Steins;Gate 0')."""
    if not show_simple:
        return text
    size = len(show_simple)
    if text.lower().startswith(show_simple) and (len(text) == size or not text[size].isalnum()):
        return text[size:].strip(u" -")
    limit = 2 * len(show_simple.split()) + 2
    for count, match in enumerate(WORD_RX.finditer(text)):
        if count >= limit:
            break
        if simplified(text[:match.end()]) == show_simple:
            return text[match.end():].strip(u" -")
    return text


def episode_title(tokens):
    title = u" ".join([t for t in tokens if t != u"-"]).strip(u" -")
    if title and (title == title.lower() or title == title.upper()):
        title = title.title()
    return title


def special_slot(kind, number, letter, letters):
    """Season-0 episode for OP/ED/SP/...; OP2a/OP2b get consecutive slots like ASS (101, 102a->102, 102b->103, 103->104)."""
    base, needs_number, rule = SPECIAL_KINDS[kind]
    offset = ord(letter) - ord("a") if letter else 0
    group = letters.get(base, {})
    offset = offset + len([1 for n in group if n < number for x in range(group[n])])
    return base + number + offset, rule


class Folder(object):
    """Per-call context: the files of one folder."""

    def __init__(self, show_name, folder_season, names):
        self.show_simple = simplified(normalise(show_name.split(u"[")[0])) if show_name else u""
        self.folder_season = folder_season
        self.show_numbers = set([w for w in self.show_simple.split() if w.isdigit()])
        self.rests = [strip_show(normalise(name), self.show_simple) for name in names]
        counts = {}
        for rest in self.rests:
            for word in set([w.strip(u"-") for w in rest.split()]):
                if word.isdigit():
                    counts[word] = counts.get(word, 0) + 1
        self.common = set([w for w in counts if counts[w] == len(names)]) if len(names) >= 3 else set()
        # Letter versions per special kind (OP2a, OP2b) for consecutive numbering
        self.letters = {}
        for rest in self.rests:
            for word in rest.split():
                match = SPECIAL_RX.match(VERSION_RX.sub(u"", word.strip(u"-")))
                if match and match.group("letter") and match.group("n"):
                    base = SPECIAL_KINDS[match.group("kind").lower()][0]
                    number, index = int(match.group("n")), ord(match.group("letter").lower()) - ord("a")
                    group = self.letters.setdefault(base, {})
                    group[number] = max(group.get(number, 0), index)
        self.unknown = UNKNOWN_START


def parse(rest, folder, at_root=False):
    """Season/episode for one normalised filename (show name already removed). None if nothing was found."""
    default_season = folder.folder_season if folder.folder_season is not None else 1

    for regex, rule in ((SXXEYY_RX, "SxxEyy"), (NXNN_RX, "NxNN")):
        match = regex.search(rest)
        if match:
            ep2 = int(match.group("ep2")) if match.group("ep2") else None
            return Parsed(int(match.group("season")), int(match.group("ep")), ep2, rule,
                          episode_title(rest[match.end():].split()), rest[:match.start()].strip(u" -"))

    season = default_season
    match = ORDINAL_SEASON_RX.search(rest)
    if match:
        season = int(match.group("season"))
        rest = (rest[:match.start()] + u" " + rest[match.end():]).strip()

    tokens = [t for t in SPACES_RX.split(rest) if t]
    candidates = []                                   # (strong, after_dash, index, Parsed)
    skip = set()
    for index, token in enumerate(tokens):
        if index in skip:
            continue
        word = VERSION_RX.sub(u"", token.strip(u"-~,.:!'\"").lower())
        if not word:
            continue
        after_dash = index > 0 and tokens[index - 1] in (u"-", u"~", u"–", u"—")
        following = [i for i in range(index + 1, len(tokens)) if tokens[i] not in (u"-", u"~")]
        next_index = following[0] if following else None
        next_word = VERSION_RX.sub(u"", tokens[next_index].strip(u"-").lower()) if next_index is not None else u""
        title_from = index + 1

        # "Season 2 05" / "S2 - 05": season marker followed by a number; "S2" alone is special 2 (AniDB style)
        if word in (u"season", u"saison", u"series") and next_word.isdigit() and len(next_word) <= 2:
            season = int(next_word)
            skip.add(next_index)
            continue
        match = SEASON_TOKEN_RX.match(word)
        if match:
            if NUMBER_RX.match(next_word) or PREFIXED_RX.match(next_word):
                season = int(match.group("n"))
                continue
            candidates.append((True, after_dash, index, Parsed(0, int(match.group("n")), None, "special", episode_title(tokens[title_from:]))))
            continue

        match = SPECIAL_RX.match(word)
        if match:
            kind = match.group("kind").lower()
            base, needs_number, rule = SPECIAL_KINDS[kind]
            number = match.group("n")
            if not number and next_word.isdigit() and len(next_word) <= 3 and kind not in (u"o", u"t"):
                number, title_from = next_word, next_index + 1
            if number or not needs_number:
                if kind in (u"special", u"specials", u"other", u"others", u"preview") and not number and index > 0:
                    pass                              # a plain word in a title, not a marker
                else:
                    slot, rule = special_slot(kind, int(number or 1), (match.group("letter") or u"").lower(), folder.letters)
                    if base == 0:
                        slot = int(number)
                    candidates.append((True, after_dash, index, Parsed(0, slot, None, rule, episode_title(tokens[title_from:]))))
                    continue

        match = DECIMAL_RX.match(word)
        if match:
            candidates.append((True, after_dash, index, Parsed(0, int(match.group("ep")), None, "decimal special", u"Special " + word)))
            continue

        match = NUMBER_RX.match(word) or PREFIXED_RX.match(word)
        if match:
            value = match.group("ep")
            strong = value not in folder.common and value not in folder.show_numbers
            if len(value) == 4 and 1930 <= int(value) <= 2039:
                strong = False                        # probably a year
            ep2 = int(match.group("ep2")) if match.group("ep2") else None
            candidates.append((strong, after_dash, index, Parsed(season, int(value), ep2, "number", episode_title(tokens[title_from:]))))

    if not candidates:
        return None
    # Prefer: not a show/common number or a year, then a number right after " - ", then the left-most one
    candidates.sort(key=lambda c: (0 if c[0] else 1, 0 if c[1] else 1, c[2]))
    best = candidates[0]
    result = best[3]
    result.show = u" ".join(tokens[:best[2]]).strip(u" -")
    return result


def parse_file(name, folder, at_root, single_file):
    rest = strip_show(normalise(name), folder.show_simple) if not at_root else normalise(name)
    result = parse(rest, folder, at_root)
    if single_file and (result is None or MOVIE_WORDS_RX.search(rest + u" " + folder.show_simple)):
        return Parsed(folder.folder_season if folder.folder_season is not None else 1, 1, None, "single file", u"", rest)
    if result is None and at_root:
        return Parsed(1, 1, None, "root file", u"", rest)
    if result is None:
        folder.unknown = folder.unknown + 1
        return Parsed(0, folder.unknown, None, "unknown", episode_title(rest.split(u" - ")[-1:]), rest)
    return result


# Folder analysis ###########################################################################################################
PLEXIGNORE_CACHE = {}
ID_CACHE = {}


def split_path(path):
    return [part for part in re.split(r"[\\/]", path or "") if part]


def plexignore_patterns(directory):
    """Patterns from <directory>/.plexignore (cached per scanner process)."""
    if directory not in PLEXIGNORE_CACHE:
        patterns = []
        try:
            filename = os.path.join(directory, ".plexignore")
            if os.path.isfile(filename):
                handle = open(filename, "rb")
                try:
                    for line in to_text(handle.read()).splitlines():
                        line = line.strip()
                        if line and not line.startswith(u"#"):
                            patterns.append(line.replace(u"\\", u"/"))
                finally:
                    handle.close()
        except Exception as e:
            Log.info("Reading .plexignore in '%s' failed: %s" % (to_text(directory), e))
        PLEXIGNORE_CACHE[directory] = patterns
    return PLEXIGNORE_CACHE[directory]


def ignored_by_plexignore(root, parts, name):
    """True if a .plexignore in the library root or a folder above matches this file or folder name.
       Patterns with a '/' are relative to the .plexignore's folder; others match the name anywhere below it."""
    if not root:
        return False
    name = to_text(name)
    for depth in range(len(parts) + 1):
        directory = os.path.join(root, *parts[:depth]) if depth else root
        relative = u"/".join([to_text(p) for p in parts[depth:]] + [name]).lower()
        for pattern in plexignore_patterns(directory):
            pattern = pattern.lower().rstrip(u"/")
            if u"/" in pattern:
                if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(relative, pattern + u"/*"):
                    return True
            elif fnmatch.fnmatch(name.lower(), pattern):
                return True
    return False


def forced_id_from_file(root, show_folder):
    """'[anidb-123]' from an ASS-style id file in the series folder (cached)."""
    key = (root, show_folder)
    if key not in ID_CACHE:
        ID_CACHE[key] = u""
        if root:
            for filename in ID_FILES:
                full = os.path.join(root, show_folder, filename)
                try:
                    if os.path.isfile(full):
                        handle = open(full, "rb")
                        try:
                            value = to_text(handle.read()).strip()
                        finally:
                            handle.close()
                        if value:
                            ID_CACHE[key] = u"[%s-%s]" % (filename[:-3], value)
                            break
                except Exception as e:
                    Log.info("Reading '%s' failed: %s" % (to_text(full), e))
    return ID_CACHE[key]


def folder_info(parts):
    """(show folder, season number or None, disc folder name or None) for a path relative to the library root."""
    season, disc_name = None, None
    for index, part in enumerate(parts[1:]):
        name = to_text(part)
        clean = SPACES_RX.sub(u" ", BRACKET_RX.sub(u" ", name).replace(u"_", u" ").replace(u".", u" ")).strip()
        if SPECIALS_FOLDER_RX.match(clean):
            season = 0
            continue
        for regex in SEASON_FOLDER_RX:
            match = regex.match(clean)
            if match:
                season = int(match.group("season"))
                break
        else:
            if name.lower() in (u"bdmv", u"stream", u"video_ts"):
                if disc_name is None:
                    disc_name = to_text(parts[index]) if index > 0 else None
            elif not TRANSPARENT_FOLDER_RX.match(clean):
                Log.info("Sub-folder '%s' is not a season folder; its files are added to '%s'" % (name, to_text(parts[0])))
    return parts[0], season, disc_name


def dvd_parts(file_path):
    """VIDEO_TS.IFO -> the title-set VOB files."""
    directory = os.path.dirname(file_path)
    try:
        items = sorted([item for item in os.listdir(directory) if item.upper().startswith("VTS_01_") and item.upper().endswith(".VOB")
                        and item.upper() != "VTS_01_0.VOB"])
        return [os.path.join(directory, item) for item in items] or [file_path]
    except Exception:
        return [file_path]


# Plex entry point ##########################################################################################################
def add_episode(media_list, show, parsed, parts):
    for number in range(parsed.episode, parsed.episode2 + 1):
        if Media is None:
            episode = {"show": show, "season": parsed.season, "episode": number, "title": parsed.title, "parts": list(parts)}
            media_list.append(episode)
            continue
        episode = Media.Episode(to_plex(show), parsed.season, number, to_plex(parsed.title), None)
        if parsed.episode2 > parsed.episode:
            episode.display_offset = (number - parsed.episode) * 100 // (parsed.episode2 - parsed.episode + 1)
        for part in parts:
            episode.parts.append(part)
        media_list.append(episode)


def Scan(path, files, mediaList, subdirs, language=None, root=None, **kwargs):
    """Called by Plex for the library root and every folder below it."""
    parts = split_path(path)

    for subdir in list(subdirs or []):
        name = os.path.basename(subdir.rstrip("/\\"))
        if IGNORE_DIR_RX.match(to_text(name)) or ignored_by_plexignore(root, parts, name):
            subdirs.remove(subdir)

    kept = []
    for file_path in files or []:
        name = os.path.basename(file_path)
        stem, ext = os.path.splitext(to_text(name))
        ext = ext[1:].lower()
        if ext not in VIDEO_EXTS or IGNORE_FILE_RX.search(stem):
            continue
        if ext == "ifo" and stem.upper() != "VIDEO_TS":
            continue
        if ignored_by_plexignore(root, parts, name):
            continue
        kept.append(file_path)
    files[:] = kept
    if not files:
        return

    files.sort(key=lambda f: [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", to_text(os.path.basename(f)))])
    at_root = not parts
    season_offset, episode_offset = 0, 0
    if at_root:
        show_name, folder_season, disc_name = u"", None, None
    else:
        show_folder, folder_season, disc_name = folder_info(parts)
        show_name = display_show(show_folder)
        tag, season_offset, episode_offset = forced_id(show_folder)
        if not FORCED_ID_RX.search(show_name):
            tag = forced_id_from_file(root, show_folder)
            if tag:
                show_name = show_name + u" " + tag

    names = []
    for file_path in files:
        stem = os.path.splitext(to_text(os.path.basename(file_path)))[0]
        names.append(to_text(disc_name) if disc_name else stem)
    folder = Folder(show_name, folder_season, names)
    Log.info("Scan '%s' - show '%s', season folder: %s, %d files" % (to_text(path), show_name, folder_season, len(files)))

    for file_path, name in zip(files, names):
        try:
            parsed = parse_file(name, folder, at_root, len(files) == 1 and not at_root)
            if parsed.season > 0 and (season_offset or episode_offset):
                parsed.season = parsed.season + season_offset
                parsed.episode, parsed.episode2 = parsed.episode + episode_offset, parsed.episode2 + episode_offset
            show = show_name
            if at_root:
                show = display_show(parsed.show or name) or u"No title"
            parts_list = dvd_parts(file_path) if os.path.basename(file_path).upper() == "VIDEO_TS.IFO" else [file_path]
            add_episode(mediaList, show, parsed, parts_list)
            Log.info("  S%02dE%03d%s  %-16s %s" % (parsed.season, parsed.episode, "-E%03d" % parsed.episode2 if parsed.episode2 > parsed.episode else "     ",
                                                 parsed.rule, to_text(os.path.basename(file_path))))
        except Exception as e:
            Log.info("  Failed on '%s': %s" % (to_text(file_path), e))

    if Stack is not None:
        try:
            Stack.Scan(path, files, mediaList, subdirs)
        except Exception as e:
            Log.info("Stack.Scan failed: %s" % e)


if __name__ == "__main__":                            # python "AMSA Series Scanner.py" "<library root>/<show folder>"
    target = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    library_root = os.path.dirname(target)
    results = []
    for directory, dirnames, filenames in os.walk(target):
        subdirs = [os.path.join(directory, d) for d in sorted(dirnames)]
        Scan(os.path.relpath(directory, library_root), [os.path.join(directory, f) for f in filenames], results, subdirs, root=library_root)
        dirnames[:] = [os.path.basename(d) for d in subdirs]          # Scan removed ignored folders
    for entry in results:
        print("%s  S%02dE%03d  %s" % (entry["show"], entry["season"], entry["episode"], os.path.basename(entry["parts"][0])))
