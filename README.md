# Plex Anime Multi Source Agent (AMSA)
A Plex anime agent that combines metadata from AniDB, TheTVDB, AniList and more.

AMSA gives your anime library the standard Plex experience, with richer data than Plex's own agents can provide. It gathers metadata from several sites and combines the best of each: titles in your language, proper season names and summaries, ratings that make sense, full cast lists, and artwork for every show and season.

AMSA comes with its own scanner, the **AMSA Series Scanner**, which recognises anime file naming and sorts specials, openings and endings into their own places.

*Looking for ultimate control over your library, built around AniDB's data? [HAMA](https://github.com/ZeroQI/Hama.bundle) is made for exactly that. The two agents serve different audiences and share good ideas.*



Metadata sources
================
AMSA uses metadata from the following sources. Each can be turned off or reordered in the settings, and sites that aren't needed are never contacted.
- **AniDB:** titles, summaries, ratings, tags, cast, staff, posters, related anime
- **TheTVDB:** season and episode numbering, episode titles and summaries, writers and directors, posters, backgrounds, banners, episode thumbnails, official content ratings
- **AniList:** titles, summaries, ratings, genres, cast with English voice actors, posters
- **MyAnimeList and Kitsu:** episode titles, summaries and air dates the main sources are missing
- **AnimeThemes:** song names for openings and endings
- **Plex:** theme songs
- **Anime-Lists and the anime-offline-database:** matching shows between the sites



Installation
============
1. Get the latest release zip from https://github.com/Dingmatt/AMSA/releases.
2. Place `Amsa.bundle` in your Plex Media Server's `Plug-ins` folder, replacing any older copy.
3. Copy `AMSA Series Scanner.py` into Plex's `Scanners/Series` folder (create the folders if they don't exist).
4. Restart Plex Media Server.
5. Create a new TV Shows library, or edit an existing one.
6. In the library's advanced settings, set the scanner to **AMSA Series Scanner** and the agent to **Anime Multi Source Agent**.
7. Open AMSA's settings from the Agents section of your Plex server's settings and check them. The [settings guide](SETTINGS.md) explains every option; a copy is also in `Amsa.bundle/Contents`.

Upgrading from an older AMSA: replace the whole `Contents` folder in `Plug-ins/Amsa.bundle` and restart Plex. Settings saved by older versions are converted automatically about a minute after Plex starts.



Usage
=====
AMSA works like any regular Plex library. Name your folders and files as you would for any TV show:

      /Anime Shows
         /Show Name
            /Season 1
               Show Name - S01E01 - First Episode.mkv
               Show Name - S01E02 - Second Episode.mkv
            /Season 2
               Show Name - S02E01.mkv
            /Specials
               Show Name - S00E01 - Special.mkv
               Show Name - OP1.mkv
               Show Name - NCED2.mkv
               Show Name - PV1.mkv
         /Long Running Show
            Long Running Show - 001.mkv
            Long Running Show - 1002.mkv

- **Seasons** follow TheTVDB's numbering. AMSA maps each episode to its AniDB entry, so a season made of several AniDB entries, or one AniDB entry split across seasons, is handled for you.
- **Absolute numbering** ("Show - 105") works for long-running shows, with or without season folders.
- **Specials** go in a `Specials` folder or season 0. Openings (`OP1`, `NCOP1`), endings (`ED1`, `NCED1`) and trailers (`PV`, `CM`, `Trailer`) are recognised and placed after the specials, and openings and endings are named after their songs.
- **Forcing a match:** if a show matches the wrong entry, add its id to the folder name, e.g. `Show Name [anidb-1234]` or `Show Name [tvdb-56789]`. An `anidb.id` or `tvdb.id` file in the show's folder works too.
- **Search words in Fix Match:** add one of these to the search in Plex's Fix Match (anywhere, any case). It's taken out before searching, so the show is found as usual:
  - `unlock-images`, e.g. `Show Name unlock-images`: when you pick the match, the show's and its seasons' posters, backgrounds and banners are unlocked, so they follow AMSA's image settings again. Plex Web can't unlock a poster itself. A poster you pick afterwards is locked as usual. To unlock every show at once, use the setting *Maintenance: Unlock ALL images on save* (see the [settings guide](SETTINGS.md); it's irreversible).
  - `clear-cache`, e.g. `Show Name clear-cache`: clears Plex's download cache for AMSA. AMSA keeps its own cache and doesn't rely on Plex's, so this is rarely needed.

Refresh Metadata shows results straight away and finishes updating in the background.



Correcting how a show's episodes are mapped
============================================
AMSA matches AniDB's episodes to TheTVDB's seasons using the community [Anime-Lists](https://github.com/Anime-Lists/anime-lists) mapping, which it downloads and keeps up to date. If a show's episodes or specials land in the wrong place, you can override its entry locally:

1. Create a file named `anime-list-custom.xml` in AMSA's cache folder:
   `[...]/Plex Media Server/Plug-in Support/Data/com.plexapp.agents.amsa/DataItems/Cache/`
2. Copy the show's entry from [anime-list-master.xml](https://github.com/Anime-Lists/anime-lists/blob/master/anime-list-master.xml) (search for its AniDB id) and correct it. The format is the same:

       <?xml version="1.0" encoding="utf-8"?>
       <anime-list>
           <anime anidbid="1234" tvdbid="56789" defaulttvdbseason="1" episodeoffset="" tmdbid="" imdbid="">
               <name>Show Name</name>
               <mapping-list>
                   <mapping anidbseason="0" tvdbseason="0">;1-3;2-4;3-0;</mapping>
               </mapping-list>
           </anime>
       </anime-list>

   - `defaulttvdbseason`: the TheTVDB season the AniDB entry's episodes go into (`0` for specials, `a` for absolute numbering).
   - `episodeoffset`: added to AniDB's episode numbers, e.g. `12` when the entry starts at the season's 13th episode.
   - `mapping`: individual episodes, as `;AniDB-TVDB;` pairs. Here AniDB special 1 becomes TheTVDB special 3, special 2 becomes TheTVDB special 4, and `3-0` means AniDB special 3 has no TheTVDB equivalent, so it isn't placed.
3. Restart Plex Media Server, then refresh the show. The log confirms the file was read: `AnimeLists - Using 1 entries from anime-list-custom.xml; they replace the official entries for AniDB 1234`.

Each entry in your file replaces the official entry for that AniDB id completely, so later fixes to that show in the official list won't reach you while it's there. Keep the file to the shows you need, remove entries once the official list is fixed, and please report mistakes to [Anime-Lists](https://github.com/Anime-Lists/anime-lists/issues) so everyone gets the fix. If the file has an error, the log says so and the file is ignored.

The `anime-list-corrections.xml` file shipped with older versions of AMSA is no longer used, and today's official list already includes its fixes, so it can be deleted.



AniDB's request limits: please read
====================================
> **⚠ A new library won't get all of its AniDB data at once.** For a large library, expect it to take several days. That's deliberate.

**Why:** AniDB is run by volunteers and bans any server that asks for too much too quickly. A ban blocks all AniDB data for hours at first, and longer each time it happens. To keep your server safe, AMSA spaces out its AniDB requests and stops at a set number per hour and per day. When it reaches a limit, it uses what it has cached and queues the rest, downloading them automatically when the limits allow.

**What you'll see:** shows appear and update straight away, with data from TheTVDB, AniList and AniDB's cached copies. The AniDB-only details fill in show by show as the queue works through, and each show is refreshed in Plex automatically once its data arrives. The log says when each queued download is expected.

**How long the first download takes,** with the default limits (100 requests an hour, 500 a day). A show needs about 1.75 AniDB entries on average, one per sequel, season or OVA it includes:

| Library size | AniDB entries (approx.) | First full download |
|---|---|---|
| 50 shows | 90 | about 1 hour |
| 100 shows | 175 | about 2 hours |
| 250 shows | 440 | about 4–5 hours |
| 500 shows | 875 | about 1–2 days |
| 1,000 shows | 1,750 | about 3–4 days |
| 2,000 shows | 3,500 | about a week |

These are estimates; shows with many sequels and specials need more entries.

**After that, it's quick.** AMSA keeps its AniDB copies. A refresh only downloads entries again once they're out of date: daily for airing shows, and less often the longer ago a show ended (up to once a year). Adding a few new shows takes minutes, and a later full library refresh mostly uses the cache.

**Can it go faster?** You can raise the limits in AMSA's settings, up to 200 an hour and 1,000 a day, which roughly halves the times for large libraries. AniDB doesn't publish its exact limits, so higher settings risk a ban. The defaults are the safe choice.



Troubleshooting
===============
- If files and shows appear in Plex, the scanner did its job. If they appear but their metadata is missing or wrong, look at the agent.
- If episodes are missing or numbered wrongly, check the scanner's log: it has one line per file, saying how it was read.
- When AMSA starts, its log lists your settings, the sites each update will contact and in what order, and any problem with its folders (such as a folder Plex can't write to on a NAS), with what to fix.
- If AniDB data seems old, AniDB may be limiting requests. AMSA uses its cached copy and downloads a fresh one later; the log says when.
- If a show has duplicate or old images AMSA can't remove (the log says "Plex also holds images AMSA can't remove"), they come from another agent or an older match: Unmatch the show, run Settings → Troubleshooting → Clean Bundles in Plex, then Fix Match it again.
- If old poster picks keep a show or season from following your image settings, unlock them: `unlock-images` in a Fix Match search for one show, or *Maintenance: Unlock ALL images on save* for every show (irreversible: picks are replaced).
- Each update in the log starts with a line naming the show and its ids, e.g. `==== Update: 'Show Name' (AniDB 1234, TVDB 56789, AniList 101112) ====`, so you can find it quickly.
- For a show that's mapped or named wrongly, turn on *Maintenance: Generate debug bundles* and refresh it. Its bundle, `[...]/Data/com.plexapp.agents.amsa/DataItems/Cache/Bundles/<AniDB id>.bundle.xml`, shows how each episode was mapped and every site's values, and lists every site's id for the show and the folder in AMSA's cache that holds that site's data (its `<Ids>` section). Turn the setting off when you're done: saved bundles are then deleted.

Please make sure you have the latest version of AMSA before reporting an issue. If the problem persists, include the following logs ([where to find them](https://support.plex.tv/articles/200250417-plex-media-server-log-files/)):
- `[...]/Plex Media Server/Logs/PMS Plugin Logs/com.plexapp.agents.amsa.log` (the agent)
- `[...]/Plex Media Server/Logs/PMS Plugin Logs/com.plexapp.system.log` (shows why the agent couldn't start)
- `[...]/Plex Media Server/Logs/Plex Media Scanner (AMSA Series Scanner).log` (how each file was read)
- A screenshot, if it helps to show the problem. The logs are still needed.



Credits
=======
Evolved from [HAMA](https://github.com/ZeroQI/Hama.bundle) by Atomicstrawberry and ZeroQI. Data from [AniDB](https://anidb.net/), [TheTVDB](https://thetvdb.com/), [Anime-Lists](https://github.com/Anime-Lists/anime-lists), [AniList](https://anilist.co/), the [anime-offline-database](https://github.com/cedya77/anime-offline-database), [MyAnimeList](https://myanimelist.net/) via [Jikan](https://jikan.moe/), [Kitsu](https://kitsu.app/) and [AnimeThemes](https://animethemes.moe/). Metadata provided by TheTVDB. Please consider adding missing information or subscribing.

Includes [Unidecode](https://pypi.org/project/Unidecode/) by Tomaz Solc (GPL-2.0-or-later). AMSA is licensed under the GNU General Public License v3.0; see `LICENSE`.
