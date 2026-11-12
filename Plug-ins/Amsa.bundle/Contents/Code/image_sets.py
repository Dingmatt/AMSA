"""Season poster sets by layout (setting "Images: Season posters from matching sets").

A designed set of season posters (one fan's DVD-style covers, a site's "Season 1..20" series) keeps its layout and changes
the picture: the same logo, title bar, frame or fade in the same places, a different character in the middle. TVDB only
says when each poster was uploaded (metadata_writer.mark_poster_sets guesses sets from that); this finds sets by looking,
across all sites, from the 24 x 36 colour grid kept with each image's fingerprint (image_match).

Two posters are compared in three bands: the top 30%, the bottom 30% and the middle. In each band, the share of
"detail" cells (a sharp change to the next cell) that are detail in both posters with nearly the same colour, allowing a
shift of one cell. Posters of one set match in the top and bottom bands (their average) and differ in the middle; the
same picture with different text is left to the duplicate check (image_match.same_artwork).

Posters are grouped by average linkage: a group only takes in a poster that matches its members on average (one
similar logo isn't enough), until no two groups match by SET_LIMIT. On 151 real posters (8 sets from 3 shows, 31
others), every set came out whole or split in two, none merged with another, and one unrelated pair was grouped.
"""
import image_match

DETAIL = 25                 # Grey difference to the next cell that makes a cell "detail"
CLOSE = 24                  # Largest colour difference (any of red, green, blue) for two detail cells to match
TOP_END = 10                # Bands, in grid rows (of 36): top 0-9, bottom 25-35, middle 10-24 (30% / 70%, as tested)
BOTTOM_START = 25
MIDDLE_DIFFERS = 0.25       # A set's members differ in the middle: a middle match this good means the same picture
SET_LIMIT = 0.14            # Average top/bottom match for one set. Real posters: 0.13-0.14 got every set right; lower
                            # merged sets (0.12), higher only split them (0.15+), the safe way to fail
QUICK_SKIP = 0.04           # Below this, the middle isn't compared (it can't matter)
PREPARED = {}               # id(grid) -> (grid, prepared data), reused within a run


def prepared(grid):
    """Grey levels, detail cells and, per row, where the detail cells are, for band_score."""
    key = id(grid)
    found = PREPARED.get(key)
    if found is not None and found[0] is grid:
        return found[1]
    width, height = image_match.GRID_WIDTH, image_match.GRID_HEIGHT
    grey = image_match.grid_grey(grid)
    detail = []
    points = []
    counts = []
    for y in range(height):
        row_points = []
        row_counts = [0]
        for x in range(width):
            index = y * width + x
            here = grey[index]
            strong = (x < width - 1 and abs(grey[index + 1] - here) >= DETAIL) or (y < height - 1 and abs(grey[index + width] - here) >= DETAIL)
            detail.append(strong)
            if strong:
                row_points.append(x)
            row_counts.append(row_counts[-1] + (1 if strong else 0))
        points.append(row_points)
        counts.append(row_counts)
    data = {"grid": grid, "detail": detail, "points": points, "counts": counts}
    if len(PREPARED) > 4000:
        PREPARED.clear()
    PREPARED[key] = (grid, data)
    return data


def band_score(one, two, top, bottom):
    """Share of detail cells in rows top..bottom-1 that match (detail in both, nearly the same colour), best of the shifts
       by up to one cell; 0-1. one, two: prepared() data."""
    width, height = image_match.GRID_WIDTH, image_match.GRID_HEIGHT
    grid_one, grid_two = one["grid"], two["grid"]
    detail_two = two["detail"]
    best = 0.0
    for shift_y in (-1, 0, 1):
        first_row, last_row = max(top, top + shift_y, 0), min(bottom, bottom + shift_y, height)
        for shift_x in (-1, 0, 1):
            first_column, last_column = max(0, shift_x), min(width, width + shift_x)
            count_one = 0
            count_two = 0
            both = 0
            for y in range(first_row, last_row):
                y_two = y - shift_y
                counts_one, counts_two = one["counts"][y], two["counts"][y_two]
                count_one += counts_one[last_column] - counts_one[first_column]
                count_two += counts_two[last_column - shift_x] - counts_two[first_column - shift_x]
                for x in one["points"][y]:
                    if x < first_column or x >= last_column:
                        continue
                    cell_two = y_two * width + x - shift_x
                    if not detail_two[cell_two]:
                        continue
                    a = (y * width + x) * 3
                    b = cell_two * 3
                    if abs(grid_one[a] - grid_two[b]) <= CLOSE and abs(grid_one[a + 1] - grid_two[b + 1]) <= CLOSE and abs(grid_one[a + 2] - grid_two[b + 2]) <= CLOSE:
                        both += 1
            most = max(count_one, count_two)
            if most < 4:
                continue
            best = max(best, float(both) / most)
    return best


def pair_score(one, two):
    """How much two posters look like one set: the average of their top and bottom band matches, or 0 when their middles
       match too (the same picture, not a set). one, two: prepared() data."""
    score = (band_score(one, two, 0, TOP_END) + band_score(one, two, BOTTOM_START, image_match.GRID_HEIGHT)) / 2.0
    if score < QUICK_SKIP:
        return score
    if band_score(one, two, TOP_END, BOTTOM_START) >= MIDDLE_DIFFERS:
        return 0.0
    return score


def find_sets(items):
    """items: [(anything, (hash, edge map, colour grid))] with colour grids. Returns the sets found: lists of the items'
       first parts (2 or more each), by average linkage at SET_LIMIT. Pairs that are the same artwork (hash within
       image_match.ALIKE_BITS) aren't compared: that's for the duplicate check."""
    usable = [item for item in items if item[1] is not None and item[1][2] is not None]
    count = len(usable)
    if count < 2:
        return []
    data = [prepared(item[1][2]) for item in usable]
    sums = [[0.0] * count for index in range(count)]
    pairs = [[0] * count for index in range(count)]
    for first in range(count):
        for second in range(first + 1, count):
            if image_match.distance(usable[first][1][0], usable[second][1][0]) <= image_match.ALIKE_BITS:
                continue
            score = pair_score(data[first], data[second])
            sums[first][second] = score
            sums[second][first] = score
            pairs[first][second] = 1
            pairs[second][first] = 1
    members = [[index] for index in range(count)]
    alive = list(range(count))
    while True:
        best = None
        for position in range(len(alive)):
            first = alive[position]
            for second in alive[position + 1:]:
                if not pairs[first][second]:
                    continue
                average = sums[first][second] / pairs[first][second]
                if average >= SET_LIMIT and (best is None or average > best[0]):
                    best = (average, first, second)
        if best is None:
            break
        keep, gone = best[1], best[2]
        members[keep] = members[keep] + members[gone]
        for other in alive:
            if other == keep or other == gone:
                continue
            total = sums[keep][other] + sums[gone][other]
            number = pairs[keep][other] + pairs[gone][other]
            sums[keep][other] = total
            sums[other][keep] = total
            pairs[keep][other] = number
            pairs[other][keep] = number
        alive = [index for index in alive if index != gone]
    return [[usable[index][0] for index in sorted(members[group])] for group in alive if len(members[group]) > 1]
