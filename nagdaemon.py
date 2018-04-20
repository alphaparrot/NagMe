today=True
thisweek=False
import nagdefs as nd
import pickle
import sys
import time
import socket

def checkconnection(host="8.8.8.8", port=53, timeout=3):
    #many thanks to StackOverflow user 7h3rAm
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except Exception as ex:
        print ex.message
        return False


if __name__=="__main__":
    
    if "wait" in sys.argv[:]:
        time.sleep(300.0)
    
    online = checkconnection()
    wait = 0.0
    while not online:
        time.sleep(20*60.0) #Try again in 20 minutes
        online = checkconnection()
        wait+=20.0
        if not online and wait>=180.0: #Keep trying for 3 hours
            quit()
    
    fp = open(".profiles","r")
    profiles = fp.read().split('\n')
    fp.close()
    
    while '' in profiles:
        profiles.remove('')
    
    #if "today" in sys.argv[:]:
    for user in profiles:
        
        userprof = pickle.load(open("."+user,"rb"))
        
        for task in userprof.tasks:
            task.assign(today=today,thisweek=thisweek)
        
        pickle.dump(userprof,open("."+user,"wb"),1)
            
    #elif "week" in sys.argv[:]:
        #for user in profiles:
            
            #userprof = pickle.load(open(user,"rb"))
            
            #for task in userprof.tasks:
                #task.assign(thisweek=)
                
            #pickle.dump(userprof,open(user,"wb"),1)    