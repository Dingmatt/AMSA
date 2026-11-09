# AMSA settings guide

Plex's settings page for legacy agents shows only a label and a list of options, with no tooltips, so this page explains each setting. Settings are listed in the order they appear in Plex. Recommended options are marked "(recommended)" in Plex.

Source lists ("AniDB > AniList > TVDB"): AMSA takes the value from the first source that has one, reading left to right. Sources not in the list are never used for that field, and "Off" leaves the field empty.

## Titles
- **Show title from:** sources for the show's title.
- **Show title language 1 / 2 / 3:** preferred languages for the show's title, in order. "main" is AniDB's main title, and "x-jat" is romaji.
- **Original title language:** language of Plex's "original title" field, taken from AniDB or AniList.
- **Use TVDB's title over its aliases:** when the title AMSA picked is one of TVDB's alternative names for the series, use TVDB's own series title instead. "Shows with several AniDB entries" applies this to shows whose seasons are separate AniDB entries only, so a single-entry show keeps its AniDB title.
- **Episode title from:** sources for episode titles.
- **Episode title language 1 / 2:** preferred languages for episode titles, in order.
- **Pick by language first, then source:** on (the default), a title in a preferred language beats the source order, so TVDB's English episode title wins over AniDB's romaji one. Off, the source order wins and language only decides within a source.

## Show
- **Summary, Air date, Rating, Studio, Episode length, Countries, Genres, Tags from:** sources for each field.
- **Combine ratings:** how the show's 1–10 rating is made when several sources in "Rating from" have one.
  - *Weighted by votes:* an average where each source counts by how many votes its rating is from, votes ÷ (votes + 100). A rating from 12 votes counts 0.11, from 100 votes 0.5, from thousands about 1, so a handful of votes on one site can't outweigh a big crowd on another. A source without a vote count counts fully.
  - *Average of the sources:* a plain average.
  - *First source only:* the first source in "Rating from" that has a rating.
- **Minimum AniDB tag weight:** AniDB tags below this weight (how strongly AniDB's users agree a tag applies) aren't used as genres or tags.
- **Related anime collections:** Plex collections of related anime (sequels, prequels, side stories) from AniDB.
- **Dubbed / Subbed collections:** the "English Dubbed" and "English Subbed" collections, built from the audio and subtitle tracks Plex has seen in your files.
  - *Leave out explicit shows (18+):* shows rated 18+ or X, or flagged adult by AniDB or AniList, aren't added.
  - *Leave out explicit and mature shows (17+):* also leaves out TV-MA and R.

## Content rating
- **From:** sources for the content rating (TV-14 and so on).
- **When sources disagree:** *Official rating first* prefers an official rating, such as TVDB's, over AniDB's estimate from its tags. *Strictest of all sources* takes the highest age, and *Source order* takes the first source.
- **Country:** the country whose ratings Plex shows.
  - If TVDB has that country's official rating, it's used.
  - Otherwise the rating is converted by age to the nearest one there, shown as for example `gb/15`.
  - A US TV-MA show is 17+. Countries with no 17 rating get their lower option (UK 15) when TVDB's Japanese rating or AniDB's tags say there's no strong content, and their top option (18) otherwise.

## Cast
- **From:** sources for the cast list.
- **Voice actors:** *Japanese* uses AniDB, then TVDB or AniList. *English (else Japanese)* uses AniList's English cast, or the Japanese cast if a show has no English one listed. *Both (labelled)* lists both, each marked with its language.
- **Photos:** the picture shown for each cast entry. *Character (else voice actor)* uses the character's picture where there is one.

## Images
- **Posters, backgrounds, banners from:** sources for show and season artwork.
- **Prefer library language, then textless:** images in your library's language come first, then images without text, then the rest. Within that, the source order applies.
- **Prefer matching season poster sets:** season posters from one designed set come first where possible. A set is guessed from TVDB uploads with the same language and text flag made in one batch.
- **Most images per type:** how many posters, backgrounds, banners and season posters (per season) AMSA offers Plex, best first.
- **Theme music from:** theme songs; only Plex's theme service provides these.

## Seasons
Plex ignores season titles and summaries sent by a legacy agent, so AMSA writes them through Plex's own edit API about 30 seconds after each update. A title or summary you typed yourself is never overwritten.
- **Season titles:** *Season 2: Name of Season* puts the number and the name in the season's title. *Name of Season* uses the name only. *Off* leaves Plex's own title ("Season 2").
- **Start the summary with the season's name:** puts the season's name on the first line of its summary. It's separate from the title, so it works with any title choice, including *Off*.
- **Names and summaries from:** sources for season names and summaries. AniDB and AniList use each season's own entry; TVDB uses its season text.
- **Seasons made of several AniDB entries:** a TVDB season can hold several AniDB entries, such as a split cour or a long season released in parts. The season is always named after the entry it starts with.
  - *Combine their summaries:* the first entry's summary, then each later part's under its own name and episodes, e.g. "The Separation (episodes 27–40)".
  - *First entry's summary only:* just the first part's.
- **If a season repeats the show's summary:** this happens when a show is matched to its first AniDB entry, which describes both the show and season 1.
  - *Show uses TVDB's summary:* the show takes TVDB's series overview, and the season keeps its own.
  - *Season uses TVDB's summary:* the season takes TVDB's season overview, if TVDB has one.
  - *Leave both:* nothing changes.

## Episodes
- **Summary, Air date, Rating, Absolute number from:** sources for each field.
- **"… > fallback"** (Title, Summary and Air date): the fallback setting's sources follow the ones listed. *AniDB only* / *TVDB only* use that source alone, with no fallback, and *Off* leaves the field empty.
- **Writers / Directors from:** TVDB gives them per episode; AniDB gives the season's staff.
- **Producers from:** AniDB's series composition credit for the season.
- **Thumbnails from:** episode images; only TVDB provides these.
- **Fallback for missing titles, summaries, dates:** a second tier after the episode sources. Where they leave an episode without a title in your language, a summary or an air date, AMSA asks MyAnimeList and Kitsu, in the order chosen here. MyAnimeList has episode titles and air dates; Kitsu also has summaries, so "MyAnimeList only" fills no summaries. *Off* contacts neither.
- **Song names for opening/ending specials:** opening and ending specials are named after their song and artist, from AnimeThemes.

## Matching
- **Check the aired year with AniDB:** when matching a show, AMSA checks the candidates' aired year with AniDB.
- **Use TVDB (year check, title search):** also uses TVDB to check the year, and to search by title when AniDB has no exact match.
- **Use anime-offline-database (60 MB weekly):** a dataset of extra titles, AniList ids and airing status, downloaded once a week.

## AniDB
AniDB bans clients that ask too often. These limits apply to every AniDB request AMSA makes.
- **Time between requests:** at least this long between requests. AniDB allows one every 2 seconds and suggests 4 over time.
- **Most requests per hour / Most requests per day:** rolling limits. Downloads nobody is waiting for (the background refresh and the retry queue) are spread evenly over the hour, for example 36 seconds apart at 100 an hour. When a limit is reached, cached data is used and the download is queued for later.

## Refreshing
- **Refresh Metadata mode:**
  - *Cached first, update in background:* a refresh writes the show from the cache at once, then downloads fresh copies in the background. The show is refreshed again only if something changed.
  - Episode thumbnails, writers and directors not cached yet, and TVDB data over 2 days old, are also downloaded after the update.
  - *Wait for fresh data:* the downloads happen during the update.
- **Skip sources downloaded within:** Refresh Metadata leaves a source alone if its copy is newer than this. Use 10 minutes while testing and 24 hours normally. AniDB also keeps its own minimum: 24 hours for airing shows, 7 days for finished ones.
- **Refresh airing shows daily:** asks Plex once a day to refresh shows that are airing or ended in the last 30 days.

## Maintenance
- **Reset all settings on save:** resets every AMSA setting to its default when you save the page. Restart Plex Media Server afterwards.
