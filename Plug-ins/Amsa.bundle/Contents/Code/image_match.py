"""Duplicate artwork from different sites (setting "Images: Duplicate artwork").

AniDB's poster, AniList's cover and TVDB's poster are often the same picture, each site storing its own copy (different
address, size and compression), so they can't be told apart by address or file contents. Here each image gets a
fingerprint of what it looks like: Plex's own image resizer (/photo/:/transcode on the local server) shrinks it, and
the small picture is reduced to 9 x 8 grey levels whose left-to-right differences give 64 bits (a "difference hash"),
plus an 8 x 8 map of where its sharp edges are. Two images are the same artwork when their hashes differ in at most
THRESHOLD bits AND their edge maps differ by at most EDGE_LIMIT in every region: titles and logos are small but full of
edges, so a textless poster and the same poster with a title are told apart (the hash alone can't see text).

What is done with the images of a list is in image_choice.py (duplicates, blanks, text, languages) and image_sets.py
(poster sets). Fingerprints are cached in Cache/Fingerprints and kept for good (slow to work out); one that isn't cached yet is worked out in the background
(or straight away in "Wait for fresh data" mode), and the show refreshed.
Plex is asked for a small PNG, decoded here in plain Python with only the built-ins Plex's sandbox offers (no bytearray,
bytes or bin); anything else is treated as a failure, as a JPEG would only give a grey, low-detail fingerprint.

Each fingerprint also keeps a 24 x 36 colour grid of the picture, used for:
  * duplicates: the middle third must match too (MIDDLE_LIMIT). A designed set of season posters shares its logo, frame and
    background, so its members can have near-identical hashes; only the middle (a different character) tells them apart;
  * blank and placeholder images (is_blank);
  * which of two versions of the same artwork has more text (text_side), and poster sets by layout (image_sets.py).
"""
import json
import re
import time
import zlib

import downloader
import textutil

FOLDER = "Fingerprints"
THRESHOLD = 10                    # Bits of 64 that may differ (re-encoding and resizing change a few; other artwork ~32)
EDGE_LIMIT = 0.8                  # Largest regional edge difference (in average-edge units) for the same artwork. Real copies
                                  # from different sites: 0.1-0.5; a poster with and without its logo: 1.1-2.1 (live logs)
RETRY_FAILED = 7 * 86400          # An image Plex couldn't resize is tried again after a week
NO_ANSWER = {}                    # Image -> times Plex didn't answer for it (not recorded as failed: Plex may be busy or restarting)
NO_ANSWER_MOST = 3                # ... until this many: then it's recorded as failed (Plex answers others, just not this one)
SLOW = 1.0                        # A fingerprint taking longer is logged with its details (size, Plex's answer, reading)
SIZE = 128                        # Plex makes the shorter side this long: enough detail, little work
GRID_WIDTH, GRID_HEIGHT = 24, 36  # Colour grid kept with each fingerprint (any image is squeezed to this shape)
MIDDLE_TOP, MIDDLE_BOTTOM = 10, 25   # Grid rows of the middle third
MIDDLE_LIMIT = 12                 # Largest average grey difference in the middle third for duplicates. Real copies: 0.4-5.3;
                                  # members of one poster set: 19.8 or more (151 real posters, 8 sets)
ALIKE_BITS = 14                   # Hash bits for "same artwork, maybe different text"
TEXT_PEAK, TEXT_RATIO = 30, 1.5   # text_side: the extra-edge peak must be this high and this much above the other's
SAME_ART_MIDDLE = 0.42            # text_side: the middles must match this well (layout score), so posters of one set (same
                                  # frame, different character) aren't compared for text
PARSED = {}                       # Image key -> parsed cache entry (hex parsed once, while it's in use)
PARSED_MOST = 4000                # Parsed entries kept in memory (about 20 KB each); emptied when more
SHARDS_MOST = 32                  # Shared files kept in memory (of 256); clean ones are let go when more are loaded
BLANK_SPREAD, BLANK_SHARE = 10, 0.97   # is_blank: this share of the picture within this many grey levels of its middle level
SHARDS = {}                       # Shared file name -> {image key: "<hash>:<edges>:<grid>:2" or "failed <time> 2"} (2: the entry format)
DIRTY = {}                        # Shared files changed since saved (new fingerprints): saved by fingerprints_flush within
                                  # FLUSH_EVERY, so a busy queue doesn't rewrite them each time
FLUSH = {"scheduled": False}
FLUSH_EVERY = 60                  # Seconds before changed shared files are saved

try:
    import struct                 # Bytes to numbers in one step, where Plex's sandbox offers it (else via hex text)
except Exception:
    struct = None

try:
    import threading
    LOCK = threading.Lock()
    READING = threading.Lock()
except ImportError:
    LOCK = Thread.Lock()
    READING = Thread.Lock()
# READING: one image read at a time, whichever thread asks (an update and the background queue). Reading is plain
# Python, and two threads doing it at once take turns badly in Plex's Python 2 (live logs: 0.27s alone, 1.5s side by
# side), so the second one waits instead.


# Fingerprints #########################################################################################################
def file_name(url):
    """Key for an image address (two CRCs: no hashlib needed); its first two characters pick the shared file."""
    text = textutil.safe_unicode(url).encode("utf-8")
    return "%08x%08x" % (zlib.crc32(text) & 0xffffffff, zlib.crc32(text[::-1]) & 0xffffffff)


def shard(key):
    """The shared file holding this key, loaded from the cache when needed (call with LOCK held). At most SHARDS_MOST stay
       in memory: when more are needed, the ones with nothing to save are let go (read again if needed)."""
    name = "%s.json" % (key[:2])
    if name not in SHARDS:
        if len(SHARDS) >= SHARDS_MOST:
            for other in list(SHARDS.keys()):
                if other not in DIRTY:
                    del SHARDS[other]
        try:
            text = downloader.load_stale(name, FOLDER, True)
            SHARDS[name] = json.loads(text) if text else {}
        except Exception:
            SHARDS[name] = {}
    return name, SHARDS[name]


def cached(url):
    """((hash, edge map, colour grid) or None, known): known is False if it has to be worked out (never tried, or Plex
       couldn't resize it over RETRY_FAILED ago)."""
    key = file_name(url)
    LOCK.acquire()
    try:
        if key in PARSED:
            return PARSED[key]
        entry = shard(key)[1].get(key)
    finally:
        LOCK.release()
    if not entry:
        return None, False
    if re.match(r"^[0-9a-f]{16}:[0-9a-f]{128}:[0-9a-f]{%d}(:2)?$" % (GRID_WIDTH * GRID_HEIGHT * 6), entry):
        found = (parse_entry(entry), True)
        LOCK.acquire()
        try:
            if len(PARSED) >= PARSED_MOST:
                PARSED.clear()
            PARSED[key] = found
        finally:
            LOCK.release()
        return found
    failed = re.match(r"^failed (\d+)( 2)?$", entry)
    return None, bool(failed) and time.time() - int(failed.group(1)) < RETRY_FAILED


def changed(name):
    """A shared file has something to save (call with LOCK held): saved by fingerprints_flush within FLUSH_EVERY."""
    DIRTY[name] = True
    if not FLUSH["scheduled"]:
        FLUSH["scheduled"] = True
        try:
            Thread.CreateTimer(FLUSH_EVERY, fingerprints_flush)
        except Exception:
            import threading
            timer = threading.Timer(FLUSH_EVERY, fingerprints_flush)
            timer.daemon = True
            timer.start()


def fingerprints_flush():
    """Save the shared files that changed (named for Plex's log)."""
    LOCK.acquire()
    try:
        FLUSH["scheduled"] = False
        for name in list(DIRTY.keys()):
            try:
                downloader.save_file(json.dumps(SHARDS[name], sort_keys=True), name, FOLDER)
            except Exception as e:
                Log.Debug("Images - Couldn't save %s: %s" % (name, e))
        DIRTY.clear()
    finally:
        LOCK.release()


def parse_entry(entry):
    parts = entry.split(":")
    return (int(parts[0], 16), hex_numbers(parts[1]), hex_numbers(parts[2]))


def hex_numbers(text):
    """Hex text as a list of numbers 0-255, decoded in one step where possible (a fingerprint has 2,656 of them)."""
    try:
        raw = text.decode("hex")                        # Plex: Python 2 str
    except (AttributeError, LookupError, TypeError):
        try:
            raw = b"".fromhex(text)                     # Python 3 (tests)
        except Exception:
            return [int(text[index:index + 2], 16) for index in range(0, len(text), 2)]
    return numbers_of(raw)


def remember(url, value):
    """Keep a fingerprint, or that Plex couldn't make one (tried again after RETRY_FAILED); saved within FLUSH_EVERY."""
    key = file_name(url)
    LOCK.acquire()
    try:
        name, entries = shard(key)
        if value is not None:
            entries[key] = "%016x:%s:%s:2" % (value[0], "".join(["%02x" % (cell) for cell in value[1]]), "".join(["%02x" % (cell) for cell in value[2]]))
            if len(PARSED) >= PARSED_MOST:
                PARSED.clear()
            PARSED[key] = (value, True)
        else:
            entries[key] = "failed %d 2" % (int(time.time()))
            if key in PARSED:
                del PARSED[key]
        changed(name)
    except Exception as e:
        Log.Debug("Images - Couldn't save a fingerprint: %s" % (e))
    finally:
        LOCK.release()


def work_out(url):
    """(hash, edge map, colour grid) of one image through Plex's resizer, saved to the cache; None if Plex couldn't resize it
       or the answer can't be read."""
    import season_editor
    value = None
    try:
        path = "/photo/:/transcode?width=%s&height=%s&minSize=1&upscale=1&format=png&url=%s" % (SIZE, SIZE, season_editor.quote(url))
        started = time.time()
        data = season_editor.plex_request(path)
        answered = time.time()
        READING.acquire()
        try:
            reading = time.time()
            value = describe_pixels(data)
        finally:
            READING.release()
        took = time.time() - started
        Log.Debug("Images - Fingerprint %016x for '%s' (%.2fs%s)" % (value[0], url, took, (": slow, Plex answered %s (row filters %s), %s KB in %.2fs, waited %.2fs for another read, read in %.2fs"
                  % (size_of(data), filters_of(data), len(data) // 1024, answered - started, reading - answered, time.time() - reading)) if took > SLOW else ""))
    except Exception as e:
        import anidb_retry
        if anidb_retry.plex_unreachable(e):
            NO_ANSWER[url] = NO_ANSWER.get(url, 0) + 1
            if NO_ANSWER[url] < NO_ANSWER_MOST:
                anidb_retry.plex_down()                    # Plex itself didn't answer: nothing recorded, tried again later
                Log.Debug("Images - Plex didn't answer for '%s' (%s): tried again later" % (url, e))
                return None
        Log.Debug("Images - Couldn't fingerprint '%s' through Plex's resizer: %s" % (url, e))
    if url in NO_ANSWER:
        del NO_ANSWER[url]
    remember(url, value)
    return value


def describe_pixels(data):
    """(hash, edge map, colour grid) of PNG bytes."""
    pixels, planes = decode(data)
    return (fingerprint(pixels), edge_map(pixels), colour_grid(planes))


def colour_grid(planes):
    """24 x 36 colour grid, as one list: red, green, blue of each cell, row by row (area averages)."""
    shrunk = [shrink(plane, GRID_WIDTH, GRID_HEIGHT) for plane in planes]
    grid = []
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            for plane in shrunk:
                grid.append(min(255, max(0, int(round(plane[y][x])))))
    return grid


def grid_grey(grid):
    """The colour grid as grey levels (one per cell)."""
    return [(grid[index] * 299 + grid[index + 1] * 587 + grid[index + 2] * 114) // 1000 for index in range(0, len(grid), 3)]


def middle_difference(one, two):
    """Average grey difference of two colour grids' middle thirds (0-255)."""
    grey_one, grey_two = grid_grey(one), grid_grey(two)
    total = 0
    count = 0
    for index in range(MIDDLE_TOP * GRID_WIDTH, MIDDLE_BOTTOM * GRID_WIDTH):
        total += abs(grey_one[index] - grey_two[index])
        count += 1
    return float(total) / (count or 1)


def is_blank(grid):
    """A blank or placeholder image: nearly all of it one shade (an all-black episode image, a grey 'no image' card).
       Real artwork, even a logo on black, has more variety (tested on 151 posters and backgrounds)."""
    if not grid:
        return False
    levels = sorted(grid_grey(grid))
    middle = levels[len(levels) // 2]
    close = len([level for level in levels if abs(level - middle) <= BLANK_SPREAD])
    return close >= BLANK_SHARE * len(levels)


def text_side(one, two):
    """For two versions of the same artwork (hash within ALIKE_BITS): 1 if the first clearly has more text (titles and logos
       add sharp edges in one area), 2 if the second has, 0 if it can't be told (tested on 31 real pairs: no wrong answers).
       one, two: (hash, edge map, colour grid) values."""
    if one[2] is None or two[2] is None:
        return 0
    import image_sets
    if image_sets.band_score(image_sets.prepared(one[2]), image_sets.prepared(two[2]), MIDDLE_TOP, MIDDLE_BOTTOM) < SAME_ART_MIDDLE:
        return 0                                  # Middles differ: another picture in the same frame (a poster set), not text
    peak_one = 0
    peak_two = 0
    for index in range(64):
        difference = one[1][index] - two[1][index]
        peak_one = max(peak_one, difference)
        peak_two = max(peak_two, -difference)
    if peak_one >= TEXT_PEAK and peak_one >= TEXT_RATIO * peak_two:
        return 1
    if peak_two >= TEXT_PEAK and peak_two >= TEXT_RATIO * peak_one:
        return 2
    return 0


def same_artwork(one, two):
    """"duplicate" (same picture: hash, edges and middle all match), "alike" (same artwork, different text or logo, or no
       colour grid yet to be sure) or None."""
    gap = distance(one[0], two[0])
    if gap > ALIKE_BITS:
        return None
    if gap <= THRESHOLD and edge_gap(one[1], two[1]) <= EDGE_LIMIT:
        if one[2] is not None and two[2] is not None and middle_difference(one[2], two[2]) <= MIDDLE_LIMIT:
            return "duplicate"
    return "alike"


def distance(one, two):
    """Bits that differ (counted here: Plex's sandbox only offers some built-ins)."""
    rest = one ^ two
    count = 0
    while rest:
        rest = rest & (rest - 1)
        count += 1
    return count


def fingerprint(pixels):
    """64-bit difference hash of a grey image (rows of numbers): shrunk to 9 x 8, each bit = left brighter than right."""
    small = shrink(pixels, 9, 8)
    value = 0
    for row in range(8):
        for column in range(8):
            value = (value << 1) | (1 if small[row][column] > small[row][column + 1] else 0)
    return value


def edge_map(pixels):
    """Where the picture's sharp edges are: edge strength (differences to the right and below) averaged over 8 x 8
       regions, scaled so the average region is 32 (0-255)."""
    height = len(pixels)
    width = len(pixels[0]) if height else 0
    if height < 2 or width < 2:
        return [32] * 64
    strength = []
    above = pixels[0]
    for below in pixels[1:]:
        strength.append(list(map(lambda here, right, down: abs(right - here) + abs(down - here), above[:-1], above[1:], below[:-1])))
        above = below
    regions = shrink(strength, 8, 8)
    total = 0.0
    for region_row in regions:
        for value in region_row:
            total += value
    average = total / 64 or 1.0
    cells = []
    for region_row in regions:
        for value in region_row:
            cells.append(min(255, int(round(value / average * 32))))
    return cells


def edge_gap(one, two):
    """Largest regional difference between two edge maps, in average-edge units (copies: under ~1.4; a title added: 4+)."""
    largest = 0
    for index in range(64):
        largest = max(largest, abs(one[index] - two[index]))
    return largest / 32.0


def shrink(pixels, width, height):
    """Area average to width x height, weighting source pixels by how much of each target cell they cover."""
    source_height = len(pixels)
    source_width = len(pixels[0]) if source_height else 0
    if not source_width:
        raise ValueError("empty image")
    columns = []
    for left, right, weights in spans(source_width, width):
        # A cell's middle pixels all have the same weight (1 / scale): only its first and last can differ
        columns.append((left, right, weights[0], weights[1] if len(weights) > 2 else 0.0, weights[-1], len(weights)))
    result = []
    for top, bottom, row_weights in spans(source_height, height):
        line = []
        keep = line.append
        rows = list(map(lambda one, two: (one, two), pixels[top:bottom], row_weights))   # list: walked once per column
        for left, right, first_weight, middle_weight, last_weight, count in columns:
            total = 0.0
            for values, weight_y in rows:
                cells = values[left:right]
                total += cells[0] * weight_y * first_weight
                if count > 2:
                    for value in cells[1:-1]:
                        total += value * weight_y * middle_weight
                if count > 1:
                    total += cells[-1] * weight_y * last_weight
            keep(total)
        result.append(line)
    return result


def spans(source, target):
    """For each target cell: (first, last + 1, weights) of the source cells it covers, weights summing to 1."""
    found = []
    scale = float(source) / target
    for index in range(target):
        start, end = index * scale, (index + 1) * scale
        first = int(start)
        last = min(source, int(end) + (0 if end == int(end) else 1))
        weights = []
        for cell in range(first, last):
            weights.append((min(end, cell + 1) - max(start, cell)) / scale)
        found.append((first, last, weights))
    return found


# Decoding #############################################################################################################
PNG_SIGNATURE = [137, 80, 78, 71, 13, 10, 26, 10]


def size_of(raw):
    """"PNG width x height, colour type" (from its header), else "not a PNG"."""
    head = numbers_of(raw[:26])
    if head[:8] != PNG_SIGNATURE:
        return "not a PNG"
    kind = {0: "grey", 2: "RGB", 3: "palette", 4: "grey and alpha", 6: "RGBA"}.get(head[25] if len(head) > 25 else None, "?")
    return "PNG %sx%s %s" % (number(head, 16, 4), number(head, 20, 4), kind)


def filters_of(raw):
    """For the log, of a slow image: how many rows use each PNG filter ("none 2, sub 10, paeth 116"), or "?"."""
    try:
        data = numbers_of(raw)
        position = 8
        width = channels = None
        compressed = []
        while position + 8 <= len(data):
            length = number(data, position, 4)
            kind = data[position + 4:position + 8]
            if kind == PNG_IHDR:
                width = number(data, position + 8, 4)
                channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(data[position + 17], 1)
            elif kind == PNG_IDAT:
                compressed.append(raw[position + 8:position + 8 + length])
            position += 12 + length
        pixels = numbers_of(zlib.decompress(raw[0:0].join(compressed)))
        stride = width * channels + 1
        counts = {}
        for start in range(0, len(pixels), stride):
            counts[pixels[start]] = counts.get(pixels[start], 0) + 1
        names = {0: "none", 1: "sub", 2: "up", 3: "average", 4: "paeth"}
        return ", ".join(["%s %s" % (names.get(kind, kind), counts[kind]) for kind in sorted(counts)])
    except Exception:
        return "?"


def numbers_of(raw):
    """Bytes as a list of numbers 0-255, using only what Plex's sandbox allows (no bytearray or ord): with struct where
       offered, else via hex text."""
    if struct is not None:
        try:
            return list(struct.unpack("%dB" % (len(raw)), raw))
        except Exception:
            pass
    try:
        text = raw.encode("hex")                        # Plex: Python 2 str
    except (AttributeError, LookupError):
        text = raw.hex()                                # Python 3 bytes (tests)
    return [int(text[index:index + 2], 16) for index in range(0, len(text), 2)]


def grey(raw):
    """Grey image (rows of numbers) from PNG bytes."""
    return decode(raw)[0]


def decode(raw):
    """(grey rows, [red rows, green rows, blue rows]) from PNG bytes; anything else raises ValueError."""
    if not raw:
        raise ValueError("empty answer")
    data = numbers_of(raw)
    if data[:8] == PNG_SIGNATURE:
        return png_planes(raw, data)
    raise ValueError("not a PNG (%s bytes%s)" % (len(data), ", a JPEG" if data[:2] == [255, 216] else ""))


def number(data, start, length):
    value = 0
    for index in range(start, start + length):
        value = (value << 8) | data[index]
    return value


PNG_IHDR, PNG_PLTE, PNG_IDAT, PNG_IEND = [73, 72, 68, 82], [80, 76, 84, 69], [73, 68, 65, 84], [73, 69, 78, 68]


def png_planes(raw, data):
    """8-bit PNG (grey, RGB, palette, with or without alpha; not interlaced) as (grey rows, [red, green, blue rows]).
       raw: the bytes, data: as numbers."""
    position = 8
    width = height = depth = colour = interlace = None
    palette = None
    compressed = []
    while position + 8 <= len(data):
        length = number(data, position, 4)
        kind = data[position + 4:position + 8]
        body = data[position + 8:position + 8 + length]
        if kind == PNG_IHDR:
            width, height = number(body, 0, 4), number(body, 4, 4)
            depth, colour, interlace = body[8], body[9], body[12]
        elif kind == PNG_PLTE:
            palette = body
        elif kind == PNG_IDAT:
            compressed.append(raw[position + 8:position + 8 + length])
        elif kind == PNG_IEND:
            break
        position += 12 + length
    if not width or depth != 8 or interlace:
        raise ValueError("unsupported PNG (depth %s, interlace %s)" % (depth, interlace))
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(colour)
    if channels is None or (colour == 3 and palette is None):
        raise ValueError("unsupported PNG colour type %s" % (colour))
    pixels = numbers_of(zlib.decompress(raw[0:0].join(compressed)))
    stride = width * channels
    previous = [0] * stride
    rows = []
    reds = []
    greens = []
    blues = []
    position = 0
    for row in range(height):
        kind = pixels[position]
        line = unfilter(kind, pixels[position + 1:position + 1 + stride], previous, channels)
        position += 1 + stride
        red, green, blue = colour_rows(line, width, channels, colour, palette)
        reds.append(red)
        greens.append(green)
        blues.append(blue)
        rows.append(list(map(lambda r, g, b: (r * 299 + g * 587 + b * 114) // 1000, red, green, blue)))
        previous = line
    return rows, [reds, greens, blues]


def unfilter(kind, line, previous, channels):
    """One PNG row with its filter undone, as a new list. Written for Plex's sandbox, where every list[index] and every
       attribute is a checked call: rows are walked with for-loops and map, and the previous pixel is carried in
       variables instead of looked up."""
    if kind == 0:
        return line
    if kind == 2:                                                          # Up
        return list(map(lambda value, up: (value + up) & 255, line, previous))
    out = []
    push = out.append                                                      # Looked up once
    if kind == 3:                                                          # Average
        for value, up in map(lambda one, two: (one, two), line[:channels], previous[:channels]):
            push((value + up // 2) & 255)
        place = 0
        for value, up in map(lambda one, two: (one, two), line[channels:], previous[channels:]):
            push((value + (out[place] + up) // 2) & 255)
            place += 1
        return out
    if kind == 1:                                                          # Sub: add the pixel to the left
        out.extend(line[:channels])
        rest = map(lambda value: (value, 0, 0), line[channels:])
        paeth = False
    else:                                                                  # Paeth
        for value, up in map(lambda one, two: (one, two), line[:channels], previous[:channels]):
            push((value + up) & 255)
        # Equal lengths: Plex's Python 2 map() pads a shorter list with None (Python 3 stops at the shortest)
        rest = map(lambda one, two, three: (one, two, three), line[channels:], previous[channels:], previous[:-channels])
        paeth = True
    if channels in (1, 2, 3, 4):
        first = out[0]
        second = out[1] if channels > 1 else 0
        third = out[2] if channels > 2 else 0
        fourth = out[3] if channels > 3 else 0
        for value, up, corner in rest:
            left = first
            if paeth:                                                      # paeth_pick, written out (no call)
                to_left = up - corner if up >= corner else corner - up
                to_up = left - corner if left >= corner else corner - left
                both = left + up - corner - corner
                to_corner = both if both >= 0 else -both
                if not (to_left <= to_up and to_left <= to_corner):
                    left = up if to_up <= to_corner else corner
            new = (value + left) & 255
            push(new)
            if channels == 4:
                first, second, third, fourth = second, third, fourth, new
            elif channels == 3:
                first, second, third = second, third, new
            elif channels == 2:
                first, second = second, new
            else:
                first = new
        return out
    place = 0
    for value, up, corner in rest:
        left = out[place]
        new = (value + (paeth_pick(left, up, corner) if paeth else left)) & 255
        push(new)
        place += 1
    return out


def paeth_pick(left, up, corner):
    """PNG's Paeth predictor: whichever of left, up and corner is closest to left + up - corner (abs() avoided)."""
    to_left = up - corner if up >= corner else corner - up
    to_up = left - corner if left >= corner else corner - left
    both = left + up - corner - corner
    to_corner = both if both >= 0 else -both
    if to_left <= to_up and to_left <= to_corner:
        return left
    return up if to_up <= to_corner else corner


def colour_rows(line, width, channels, colour, palette):
    """(reds, greens, blues) of one unfiltered row: by slices (one step each), or through the palette."""
    if colour == 3:
        reds_table, greens_table, blues_table = palette[0::3], palette[1::3], palette[2::3]
        entries = line[:width]
        return ([reds_table[entry] for entry in entries], [greens_table[entry] for entry in entries],
                [blues_table[entry] for entry in entries])
    if channels >= 3:
        return line[0:width * channels:channels], line[1:width * channels:channels], line[2:width * channels:channels]
    grey = line[0:width * channels:channels]
    return grey, grey, grey


def background_task(url):
    """A "print|<url>" task from the background "Files" lane: True if a fingerprint was worked out (the show is refreshed)."""
    import image_choice
    if not image_choice.wanted():
        return False
    value, known = cached(url)
    if known:
        return False
    import anidb_retry
    value = work_out(url)
    if value is None and not anidb_retry.plex_answering():
        return "wait"                                      # Plex didn't answer: the task is kept (background_refresh)
    return value is not None
