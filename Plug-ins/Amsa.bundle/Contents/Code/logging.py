import datetime, constants, functions

global LoggingArray, AniDBArray
LoggingArray = []
AniDBArray = []
netLock = Thread.Lock()

def New_Milestones():
    """
    Creates a new telemetry.

    Args:
    """
    if constants.MilestoneLogging:
        try:
            netLock.acquire()
            global LoggingArray
            LoggingArray = []
            file = functions.LoadFile(constants.MilestoneFile, "")
            if file:
                functions.SaveFile(file + "<br />\r\n", constants.MilestoneFile)
        finally:
            netLock.release()
            
def Log_Milestone(milestone):
    """
    Acquire incoming log entries

    Args:
        milestone: (str): write your description
    """
    if constants.MilestoneLogging:
        try:       
            now = datetime.datetime.now()
            netLock.acquire()
            global LoggingArray
            msg = ""
            for entry in LoggingArray:
                if entry[0] == milestone:
                    file = functions.LoadFile(constants.MilestoneFile, "")
                    if not file:
                        file = ""
                    delta = now - entry[1]
                    msg = ("%s | '%s' - '%s' : %ss : %sms : %sus") % (entry[0], entry[1], now, delta.seconds, (delta.microseconds / 1000), delta.microseconds)
                    functions.SaveFile(file + msg + "<br />\r\n", constants.MilestoneFile)
                    LoggingArray.remove(entry)
            
            if len(msg) == 0:
                LoggingArray.append([milestone, datetime.datetime.now()])
        finally:
            netLock.release() 
            
def New_AniDB():
    """
    Creates a new netLock file.

    Args:
    """
    if constants.AniDBLogging:
        try:
            netLock.acquire()
            global AniDBArray
            AniDBArray = []
            file = functions.LoadFile(constants.AniDBFile, "")
            if file:
                functions.SaveFile(file + "<br />\r\n", constants.AniDBFile)
        finally:
            netLock.release()
            
def Log_AniDB(id, save = False):
    """
    This function is called when the database

    Args:
        id: (str): write your description
        save: (bool): write your description
    """
    if constants.AniDBLogging:
        try:       
            netLock.acquire()
            global AniDBArray
            msg = ""
            if save:
                for entry in AniDBArray:
                    file = functions.LoadFile(constants.AniDBFile, "")
                    if not file:
                        file = ""
                    msg = ("%s | %s") % (entry, AniDBArray.count(entry))
                    functions.SaveFile(file + msg + "<br />\r\n", constants.AniDBFile)
                    AniDBArray.remove(entry)
            else:
                AniDBArray.append(id)
        finally:
            netLock.release() 