# Plex Anime Multi Source Agent (AMSA)
A Plex anime agent using TVDB and AniDB data


Amsa is an anime oriented Plex agent which has been designed to gather metadata from multiple sources in order to present you with the richest Plex experience available, it has been designed to allow you to store your shows in either the AniDB or TVDB standard whilst still benefiting form the input from both sites. 

*TVDB standard is advised during the alpha period as the AniDB standard is still in testing*

The Amsa was based on Atomicstrawberry & ZeroQI's Hama (https://github.com/ZeroQI/Hama.bundle) and currently uses a custom version of the Absolute Series Scanner (https://github.com/ZeroQI/Absolute-Series-Scanner).
    
    
    
Metadata source
===============
Amsa uses metadate from the following sources:
- AniDB (Posters, Series Info, Ratings & Tags)
- TVDB (Posters, Background, Banner, Series Info, Episode Info)
- Plex (Themes Songs)



Installation
============
1. Get the latest source zip in github release for Amsa https://github.com/Dingmatt/AMSA/releases.
2. Place the content of the zip into your Plex Media Server directory
3. Create a new library 
4. Set its scanner to "Absolute Series Scanner"
5. Set its agent to "Anime Multi Source Agent"
6. Access the Amsa settings from your server library admin tab



Usage
=====
Asma in conjunction with the Absolute Series Scanner will work in the same way as any regular Plex library, the main difference is where the metadata is gathered from and that it will also list any additional media you have stored alongside your series episodes.

To use this feature simply place any additional content in the series "Specials" folder with a high episode number (see example below), opening and endings are handled separately as long as you label them with either the "OP", "ED" or the no credit (NC) equivalents.

Example:
  /Anime Shows

     /Akame ga Kill!

        /Season 1

           Akame ga Kill! - S01E01 - Kill the Darkness.mkv 

        /Specials

           Akame ga Kill! - OP.mkv   

           Akame ga Kill! - OP2.mkv 

           Akame ga Kill! - ED1.mkv 

           Akame ga Kill! - NCED2.mkv  

           Akame ga Kill! - S00E50 - Parody.mkv 



Troubleshooting:
================
If files and series are showing in Plex GUI the scanner did its job
If files that are showing correctly but do not have all metadata updating, its the agent thats at fault.
If the files and series have their titles / descriptions but the posters are missing then check that all the data folders are present and the agent is where it should be.

Please ensure you have the latest version of Amsa before reporting any issues, to do this please follow these steps:

1. Delete the library
2. Stop Plex
3. Update to the latest Amsa from github
4. Start Plex
5. Re-create the library

If that fails to work then please include all of the following logs when submitting your issue (location: https://support.plex.tv/hc/en-us/articles/200250417-Plex-Media-Server-Log-Files):
- [...]/Plex Media Server/Logs/PMS Plugin Logs/com.plexapp.agents.amsa.log (Agent logs)
- [...]/Plex Media Server/Logs/PMS Plugin Logs/com.plexapp.system.log (show why the agent cannot launch)
- [...]/Plex Media Server/Logs/Plex Media Scanner (custom ASS) - Library_name.log (episodes info)
- [...]/Plex Media Server/Logs/Plex Media Scanner (custom ASS).log (episodes info IF library name log doesn't exist)
- [...]/Plex Media Server/Logs/Plex Media Scanner (custom ASS) filelist.log (library file list)
- Screen capture to illustrate if needed. Above logs are still mandatory
