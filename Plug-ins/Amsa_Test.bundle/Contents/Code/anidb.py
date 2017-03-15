import constants, functions, lxml, copy, logging
from functions import XMLFromURL, GetElementText
from lxml import etree
from lxml.builder import E
from lxml.etree import Element, SubElement, Comment


def ParseNoFromSeason(season, episode):
    if season >= 1:
        return str(episode)
    elif season == 0:
        return "S" + str(episode)
        
def ParseNoFromType(type, episode):
    if type == 1:
        return str(episode)
    elif type == 2:
        return "S" + str(episode)
    elif type == 3:
        return "C" + str(episode)    
    elif type == 4:
        return "T" + str(episode) 
    elif type == 5:
        return "P" + str(episode) 
    elif type == 6:
        return "O" + str(episode) 
 
def ParseLocalNoFromType(type, episode, prefix = ""):
    if type == 1:
        return "S01E" + str(episode).zfill(2)
    elif type == 2:
        return "S00E" + str(episode).zfill(2) 
    elif type == 3 and prefix.lower() == "op":
        return "S00E" + str(episode)
    elif type == 3 and prefix.lower() == "ed":
        return "S00E" + str(episode) 
    elif type == 4:
        return "S00E" + str(episode) 
    elif type == 5:
        return "S00E" + str(episode) 
    elif type == 6:
        return "S00E" + str(episode) 

        
class AniDB(constants.Series):
    
    def __init__(self, id):
        logging.Log_Milestone("AniDB" + "_" + id)
        data = XMLFromURL(constants.ANIDB_HTTP_API_URL + id, id + ".xml", "AniDB\\" + id, CACHE_1HOUR * 24).xpath("""/anime""")[0]
        
        ##--------------------------------ID-----------------------------------##
        self.ID = id
        
        self.Type = GetElementText(data, "type")
        
        ##--------------------------------Title--------------------------------##
        if data.xpath("""./titles"""):
            self.Title = functions.GetPreferedTitle(data.xpath("""./titles/title""")).encode('utf-8').strip().translate(constants.ReplaceChars)
        
        ##--------------------------------Summary------------------------------##
        if GetElementText(data, "description"):  
            description = re.sub(r'(?m)^\*.*\n?', '',  GetElementText(data, "description").replace("`", "'")).strip()
            self.Summary = re.sub(r"http://anidb\.net/[a-z]{2}[0-9]+ \[(.+?)\]", r"\1", description)
            
        ##--------------------------------Originally_Available_At--------------##  
        if GetElementText(data, "startdate"):
            self.Originally_Available_At = GetElementText(data, "startdate")    

        ##--------------------------------Rating-------------------------------##    
        if GetElementText(data, "ratings/permanent") and GetElementText(data, "ratings/temporary"): 
            self.Rating = (float(GetElementText(data, "ratings/permanent")) + float(GetElementText(data, "ratings/temporary"))) / 2   
        elif GetElementText(data, "ratings/permanent"): 
            self.Rating = float(GetElementText(data, "ratings/permanent"))   
        elif GetElementText(data, "ratings/temporary"): 
            self.Rating = float(GetElementText(data, "ratings/temporary"))
            
        ##--------------------------------Studio-------------------------------##        
        for creator in data.xpath("""./creators/name[@type="Animation Work"]"""):
            self.Studio = creator.text 
        
        
        ##--------------------------------Countries----------------------------##   
        for setting in data.xpath("""./tags/tag/name[text()="setting"]/.."""):
            for place in data.xpath("""./tags/tag[@parentid="%s"]""" % (setting.get("id"))):
                for planet in data.xpath("""./tags/tag[@parentid="%s"]""" % (place.get("id"))):
                    for continent in data.xpath("""./tags/tag[@parentid="%s"]""" % (planet.get("id"))):
                        for country in data.xpath("""./tags/tag[@parentid="%s" and @weight>="%s"]/name""" % (continent.get("id"), constants.MINIMUM_WEIGHT)):
                            if self.Countries is None: self.Countries = []
                            self.Countries.append(country.text)
                    
        ##--------------------------------Duration-----------------------------##  
        for length in data.xpath("""./episodes/episode/epno[@type="1"]/.."""):
            if GetElementText(length, "length"): 
                if self.Duration is None: self.Duration = 0 
                self.Duration = self.Duration + int(GetElementText(length, "length"))
        
        ##--------------------------------Genres-------------------------------##         
        for element in data.xpath("""./tags/tag/name[text()="elements"]/.."""):
            for genre in data.xpath("""./tags/tag[@parentid="%s" and @weight>="%s"]/name""" % (element.get("id"), constants.MINIMUM_WEIGHT)):
                if self.Genres is None: self.Genres = []
                self.Genres.append(str(genre.text).title())        
        
        ##--------------------------------Tags---------------------------------## 
        for tag in data.xpath("""./tags/tag[@infobox="true"]/name"""):
            if self.Tags is None: self.Tags = []
            self.Tags.append(str(tag.text).title()) 
                
        ##--------------------------------Collections--------------------------## 
        for collection in data.xpath("""./relatedanime/anime[(@type="Prequel") or (@type="Sequel")]"""):
            if self.Collections is None: self.Collections = []
            self.Collections.append(collection.text)
                
        ##--------------------------------Content_Rating-----------------------## 
        for indicators in data.xpath("""./tags/tag/name[text()="content indicators"]/.."""):
            ratingInt = 0
            for tag in data.xpath("""./tags/tag[(@parentid="%s") and (@weight>="%s")]/name""" % (indicators.get("id"), constants.MINIMUM_WEIGHT)):
                if tag.text == "nudity": 1 if ratingInt < 1 else ratingInt
                elif tag.text == "sex": 2 if ratingInt < 2 else ratingInt
                elif tag.text == "violence": 2 if ratingInt < 2 else ratingInt
            if ratingInt == 0: self.Content_Rating = "PG-13"
            elif ratingInt == 1: self.Content_Rating = "R"
            elif ratingInt == 2: self.Content_Rating = "NC-17"
                    
        ##--------------------------------Writers------------------------------##
        for writer in data.xpath("""./creators/name[(@type="Original Work") or (@type="Script") or (@type="Screenplay")]"""):
            if self.Writers is None: self.Writers = []
            self.Writers.append(writer.text)
        
        ##--------------------------------Directors----------------------------##
        for director in data.xpath("""./creators/name[@type="Direction"]"""):
            if self.Directors is None: self.Directors = [] 
            self.Directors.append(director.text)   

        ##--------------------------------Producers----------------------------##
        for producer in data.xpath("""./creators/name[@type="Series Composition"]"""): 
            if self.Producers is None: self.Producers = [] 
            self.Producers.append(producer.text) 
                
        ##--------------------------------Roles--------------------------------##
        roles = etree.tostring(E.Roles(), pretty_print=True, xml_declaration=True, encoding="UTF-8")
        roles = XML.ElementFromString(roles)
        for role in data.xpath("""./characters/character/charactertype[text()="Character"]/.."""):
            character_name = ""
            seiyuu_name = ""
            seiyuu_pic = ""        
            if GetElementText(role, "name"):               
                character_name  = str(GetElementText(role, "name")) 
            if GetElementText(role, "seiyuu"):       
                seiyuu_name  = GetElementText(role, "seiyuu")
                seiyuu_pic = ""
                if role.find('seiyuu').get('picture'):
                    seiyuu_pic  = constants.ANIDB_PIC_BASE_URL + role.find('seiyuu').get('picture') 
            SubElement(roles, "Role", character_name = character_name, seiyuu_name = seiyuu_name, seiyuu_pic = seiyuu_pic)   
        if not roles is None: self.Roles = roles
        
        ##--------------------------------Images------------------------------##
        if GetElementText(data, "picture"): 
            season = etree.tostring(E.Images(), pretty_print=True, xml_declaration=True, encoding="UTF-8")
            season = XML.ElementFromString(season)
            bannerPath = GetElementText(data, "picture")
            mainUrl, thumbUrl, mainLocalPath, thumbLocalPath = functions.ParseImage(bannerPath, constants.ANIDB_PIC_BASE_URL, os.path.join("AniDB", id, "season"))  
            SubElement(season, "Image", id = "1", mainUrl = mainUrl, thumbUrl = thumbUrl, mainLocalPath = mainLocalPath, thumbLocalPath = thumbLocalPath)
            self.Season = season
            self.Posters = copy.deepcopy(season)
        ##--------------------------------Themes-------------------------------##
        self.Themes = []
        
        ##--------------------------------Links--------------------------------##
        if GetElementText(data, "resources"):
            links = etree.tostring(E.Links(), pretty_print=True, xml_declaration=True, encoding="UTF-8")
            links = XML.ElementFromString(links)
            value = []            
            for externalentity in data.xpath("""./resources/resource/*"""):
                for identifier in externalentity.xpath("""./identifier"""):
                    if externalentity.getparent().get("type") == "1":
                        SubElement(links, "Link", type = "ANN", url = constants.ANIDB_RESOURCES_ANN % (identifier.text), value = identifier.text)
                    elif externalentity.getparent().get("type") == "2":
                        SubElement(links, "Link", type = "MAL", url = constants.ANIDB_RESOURCES_MAL % (identifier.text), value = identifier.text)
                    elif externalentity.getparent().get("type") == "3":
                        value.append(identifier.text)
                    elif externalentity.getparent().get("type") == "4":
                        SubElement(links, "Link", type = "OfficialJP", url = identifier.text) 
                    elif externalentity.getparent().get("type") == "5":
                        SubElement(links, "Link", type = "OfficialEN", url = identifier.text) 
                    elif externalentity.getparent().get("type") == "6":
                        SubElement(links, "Link", type = "WikiEN", url = constants.ANIDB_RESOURCES_WIKIEN % (identifier.text), value = identifier.text)
                    elif externalentity.getparent().get("type") == "7":
                        SubElement(links, "Link", type = "WikiJP", url = constants.ANIDB_RESOURCES_WIKIJP % (identifier.text), value = identifier.text)
                    elif externalentity.getparent().get("type") == "8":
                        SubElement(links, "Link", type = "Schedule", url = constants.ANIDB_RESOURCES_SCHEDULE % (identifier.text), value = identifier.text)
                    elif externalentity.getparent().get("type") == "9":
                        SubElement(links, "Link", type = "AllCinema", url = constants.ANIDB_RESOURCES_ALLCINEMA % (identifier.text), value = identifier.text)
                    elif externalentity.getparent().get("type") == "10":
                        SubElement(links, "Link", type = "Anison", url = constants.ANIDB_RESOURCES_ANISON % (identifier.text), value = identifier.text)
                    elif externalentity.getparent().get("type") == "11":
                        SubElement(links, "Link", type = "Lain", url = constants.ANIDB_RESOURCES_LAIN % (identifier.text), value = identifier.text)
                    elif externalentity.getparent().get("type") == "14":
                        SubElement(links, "Link", type = "VNDB", url = constants.ANIDB_RESOURCES_VNDB % (identifier.text), value = identifier.text)
                    elif externalentity.getparent().get("type") == "15":
                        SubElement(links, "Link", type = "Marumegane", url = constants.ANIDB_RESOURCES_MARUMEGANE % (identifier.text), value = identifier.text)
                if externalentity.getparent().get("type") == "3":
                    SubElement(links, "Link", type = "AnimeNfo", url = constants.ANIDB_RESOURCES_ANIMENFO % (u"%s" % value[0], u"%s" % value[1]), value = u"%s" % value)       
            self.Links = links     
        
        ##--------------------------------EpisodeCount-------------------------##
        self.EpisodeCount = int(GetElementText(data, "episodecount")) 
        
        ##--------------------------------SpecialCount-------------------------##
        self.SpecialCount = len(data.xpath("""./episodes/episode/epno[@type="2"]"""))
        
        ##--------------------------------OP/ED_List---------------------------##
        self.OpList = []
        self.EdList = []
        for specials in data.xpath("""./episodes/episode/epno[@type="3"]/.."""):
            if functions.CleanTitle(functions.GetPreferedTitleNoType(specials.xpath("""./title"""))).startswith("Opening"):
                self.OpList.append(str(GetElementText(specials, "epno")))
            if functions.CleanTitle(functions.GetPreferedTitleNoType(specials.xpath("""./title"""))).startswith("Ending"):
                self.EdList.append(str(GetElementText(specials, "epno")))
                
        ##--------------------------------Episodes-----------------------------##        
        if len(data.xpath("""./episodes/episode""")) > 0:
            self.Episodes = []
            for item in data.xpath("""./episodes/episode"""):
                self.Episodes.append(self.Episode(item, id))
        
            
        #Log("AniDB - __init__() - Populate  Title: '%s', Network: '%s', Overview: '%s', FirstAired: '%s', Genre: '%s', ContentRating: '%s', Rating: '%s', Episodes: '%s', EpisodeCount: '%s', SpecialCount: '%s', OpCount: '%s', EdCount: '%s', Posters: '%s'"
        #% (self.Title, self.Network, self.Overview, self.FirstAired, self.Genre, self.ContentRating, self.Rating, self.Episodes, self.EpisodeCount, self.SpecialCount, len(self.OpList), len(self.EdList), self.Posters) )
        logging.Log_Milestone("AniDB" + "_" + id)
        
    class Episode(constants.Episode):
        def __init__(self, data, id):
            ##--------------------------------Title--------------------------------##
            if data.xpath("""./title"""):
                self.Title = functions.GetPreferedTitleNoType(data.xpath("""./title""")).encode('utf-8').strip().translate(constants.ReplaceChars)
                
            ##--------------------------------Summary------------------------------##   

            ##--------------------------------Originally_Available_At--------------## 
            if GetElementText(data, "airdate"):
                self.Originally_Available_At = GetElementText(data, "airdate")
            
            ##--------------------------------Rating-------------------------------##  
            if GetElementText(data, "rating"):
                self.Rating = GetElementText(data, "rating")
                
            ##--------------------------------Absolute_Index-----------------------## 
            if GetElementText(data, "epno") and GetElementText(data, "epno").isdigit():
                self.Absolute_Index = GetElementText(data, "epno")
                
            ##--------------------------------Writers------------------------------##
        
        
            ##--------------------------------Directors----------------------------##
          

            ##--------------------------------Producers----------------------------##
        
        
            ##--------------------------------Thumbs-------------------------------##

            
            ##--------------------------------Number-------------------------------##
            if GetElementText(data, "epno"):
                self.Number = str(GetElementText(data, "epno")) 
             
            ##--------------------------------Season-------------------------------##
            if data.xpath("""./epno""")[0].get("type"):
                if data.xpath("""./epno""")[0].get("type") == "1":
                    self.Season = "01"
                else:
                    self.Season = "00"
            
            