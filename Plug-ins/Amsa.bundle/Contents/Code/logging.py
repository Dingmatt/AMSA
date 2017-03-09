import datetime, constants, functions

global LoggingArray
LoggingArray = []
netLock = Thread.Lock()

def Log_Milestone(milestone):
    if constants.MilestoneLogging == "True":
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
        
def New_Milestones():
    if constants.MilestoneLogging == "True":
        try:
            netLock.acquire()
            global LoggingArray
            LoggingArray = []
            file = functions.LoadFile(constants.MilestoneFile, "")
            if file:
                functions.SaveFile(file + "<br />\r\n", constants.MilestoneFile)
        finally:
            netLock.release()