"""Text helpers: unicode safety, title cleaning, preferred-title selection, dates and fuzzy comparison."""
import re
import time
import traceback
from datetime import datetime

from unidecode import unidecode

import settings

XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def safe_unicode(value, encoding="utf-8"):
    """Always return unicode (or None). Never raises on non-ASCII input."""
    if value is None:
        return None
    if isinstance(value, unicode):
        return value
    if isinstance(value, str):
        return value.decode(encoding, "replace")
    try:
        return unicode(value)
    except Exception:
        return str(value).decode(encoding, "replace")


def clean_text(value):
    """Unicode text with surrounding whitespace removed, runs of spaces made single (TVDB has a few titles with double
       spaces) and backticks replaced (titles, names)."""
    value = safe_unicode(value)
    if value is None:
        return None
    return re.sub(u" {2,}", u" ", value.replace(u"`", u"'")).strip()


def clean_title(title, filter_words=False):
    """Lower-case ASCII form of a title used for matching: accents transliterated, punctuation removed."""
    if not title:
        return ""
    title = safe_unicode(title).lower()
    if filter_words:
        title = re.sub(settings.FILTER_REGEX, "", title)
    title = re.sub(r"\[(tvdb\d?|anidb\d?).*\]", "", title)
    title = unidecode(title)                       # Transliterate first so accented letters survive the filter below
    title = re.sub(r"[^A-Za-z0-9 ]+", " ", title)
    title = re.sub(r"[ ]+", " ", title)
    return str(title.strip())


def is_digits(value):
    return value is not None and str(value).isdigit()


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def exception_text():
    return traceback.format_exc().strip().replace("\n", " | ")


def element_text(element, xpath, default=None):
    """Text of the first node matching xpath under element, or default ("" if not given)."""
    if element is not None:
        found = element.xpath(xpath)
        if found and found[0].text:
            return found[0].text
    return "" if default is None else default


def when_text(epoch):
    """A future time for the log, with its date: "2026-11-08 01:14:59" (a bare "01:14:59" left it unclear which day)."""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epoch))


def parse_date(value):
    """AniDB/TVDB dates can be 'YYYY-MM-DD', 'YYYY-MM' or 'YYYY'. Returns a date or None."""
    value = (value or "").strip()
    for date_format, length in (("%Y-%m-%d", 10), ("%Y-%m", 7), ("%Y", 4)):
        try:
            return datetime.strptime(value[:length], date_format).date()
        except ValueError:
            pass
    return None


def title_rank(lang, is_main, languages):
    """Position of a title's language in a language priority list; AniDB's main title also counts as "main". Unlisted = last."""
    ranks = []
    if lang in languages:
        ranks.append(languages.index(lang))
    if is_main and "main" in languages:
        ranks.append(languages.index("main"))
    return sorted(ranks)[0] if ranks else len(languages)


def preferred_title_info(titles, languages=None):
    """(title, language, is_main) best matching the series title languages and title-type priority, or (None, None, False)."""
    languages = languages or settings.SERIES_LANGUAGE_PRIORITY
    titles = [x for x in titles if x.text]
    if not titles:
        return None, None, False
    # Order: main/official titles before synonyms and short titles, then the language order, then the title type
    # (ranked in that order, not added together, so an English official title isn't tied with the main romaji title).
    ranked = []
    for title in titles:
        lang, title_type = title.get(XML_LANG), title.get("type")
        rank = title_rank(lang, title_type == "main", languages)
        if rank < len(languages) and title_type in settings.SERIES_TYPE_PRIORITY:
            type_rank = settings.SERIES_TYPE_PRIORITY.index(title_type)
            ranked.append((0 if title_type in ("main", "official") else 1, rank, type_rank, title))
    if ranked:
        best = sorted(ranked, key=lambda r: (r[0], r[1], r[2]))[0][3]
    else:
        main = [x for x in titles if x.get("type") == "main"]
        best = main[0] if main else titles[0]
    return safe_unicode(best.text), best.get(XML_LANG), best.get("type") == "main"


def preferred_title(titles):
    """Title matching the user's language and title-type priority. Returns unicode, or None if there are no titles."""
    return preferred_title_info(titles)[0]


def preferred_title_any_type_info(titles, languages=None):
    """(title, language) best matching a language priority (default: the episode title languages), ignoring title type."""
    languages = languages or settings.EPISODE_LANGUAGE_PRIORITY
    titles = [x for x in titles if x.text]
    if not titles:
        return None, None
    ranked = [(languages.index(x.get(XML_LANG)), x) for x in titles if x.get(XML_LANG) in languages]
    best = sorted(ranked, key=lambda r: r[0])[0][1] if ranked else titles[0]
    return safe_unicode(best.text), best.get(XML_LANG)


def strip_html(text):
    """AniList descriptions: <br> to newlines, other tags removed, common entities decoded."""
    if not text:
        return text
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    for entity, char in (("&amp;", "&"), ("&quot;", '"'), ("&#039;", "'"), ("&apos;", "'"), ("&lt;", "<"), ("&gt;", ">"), ("&mdash;", u"\u2014"), ("&ndash;", u"\u2013")):
        text = text.replace(entity, char)
    return text


def clean_summary(text):
    """Source notes and markup removed from a description (AniDB and AniList; rules based on HAMA's summary_sanitizer):
       AniDB links 'http://anidb.net/ch123 [Name]' and 'https://anidb.net/character/123 [Name]' become 'Name'; lines starting
       with '* ', '-- ' or '~ ' are dropped; everything after a 'Source:', 'Note:' or 'Summary:' line, or '(Source: ...)', is cut."""
    if not text:
        return None
    text = safe_unicode(text).replace("`", "'").replace("\r\n", "\n")
    text = re.sub(r"https?://anidb\.net/[a-z]{1,2}[0-9]+ \[(.+?)\]", r"\1", text)
    text = re.sub(r"https?://anidb\.net/[a-z]+/[0-9]+ \[(.+?)\]", r"\1", text)
    text = re.sub(r"(?m)^(\*|--|~) .*$", "", text)
    text = re.sub(r"(?s)\n\s*\(?(Source|Note|Summary)s?:.*$", "", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = text.strip(" \n")
    return text or None


def similarity(first, second):
    """1.0 for identical strings, falling towards 0.0 with Levenshtein distance."""
    first, second = safe_unicode(first) or u"", safe_unicode(second) or u""
    longest = float(max(len(first), len(second)))
    if not longest:
        return 1.0
    return float(1 - (Util.LevenshteinDistance(first, second) / longest))


# ISO 639-2 (TVDB v4, e.g. "eng") -> ISO 639-1 (Plex and TVDB v1, e.g. "en") for the languages Plex offers this agent
LANGUAGE_CODES = {"eng": "en", "jpn": "ja", "fra": "fr", "fre": "fr", "zho": "zh", "chi": "zh", "swe": "sv", "nor": "no", "dan": "da", "fin": "fi",
                  "nld": "nl", "dut": "nl", "deu": "de", "ger": "de", "ita": "it", "spa": "es", "pol": "pl", "hun": "hu", "ell": "el", "gre": "el",
                  "tur": "tr", "rus": "ru", "heb": "he", "por": "pt", "ces": "cs", "cze": "cs", "kor": "ko", "slv": "sl", "hrv": "hr"}


def short_language(code):
    """'eng' or 'en' -> 'en'; empty or unknown codes are returned lower-cased (empty = no language, e.g. textless art)."""
    code = (code or "").strip().lower()
    return LANGUAGE_CODES.get(code, code)


# ISO 3166-1 alpha-3 (TVDB v4 originalCountry) -> the country names AniDB uses
COUNTRY_NAMES = {"jpn": "Japan", "kor": "South Korea", "chn": "China", "twn": "Taiwan", "hkg": "Hong Kong", "usa": "United States", "can": "Canada",
                 "gbr": "United Kingdom", "fra": "France", "deu": "Germany", "ita": "Italy", "esp": "Spain", "aus": "Australia", "rus": "Russia",
                 "tha": "Thailand", "phl": "Philippines", "ind": "India", "bra": "Brazil", "mex": "Mexico", "nld": "Netherlands", "swe": "Sweden"}


def country_name(code):
    return COUNTRY_NAMES.get((code or "").strip().lower())


def anidb_language(code):
    """TVDB's 'eng' / Plex's 'en' -> AniDB's code ("en"), so TVDB titles can be ranked with the AniDB title language settings."""
    return short_language(code) or None
