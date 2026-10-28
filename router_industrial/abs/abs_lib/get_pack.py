
import urllib.request, urllib.error, urllib.parse
import datetime
import time
import os
import os.path

class get_pack:
    def __init__(self, my_url, file_dest, last_modified, max_timeout):
        self.last_modified = last_modified
        self.file_dest = file_dest
        self.my_url = my_url
        self.max_timeout = 10
        if ( isinstance( max_timeout, int ) ):
            self.max_timeout = max_timeout
        self.did = False
    
    def __read_to_file( self, response, file):
        CHUNK = 16 * 1024
        with open(file, 'wb') as f:
            while True:
                chunk = response.read(CHUNK)
                if not chunk: break
                f.write(chunk)

    def get_from_server(self):
        self.did = False
        headers = {}
        if ( self.last_modified != None):
            headers={"If-Modified-Since": self.last_modified}
        request = urllib.request.Request( self.my_url, None, headers )
        print(headers)

        #    http://stackoverflow.com/questions/17846129/header-if-modified-since-does-not-give-304-code
        try:
            u = urllib.request.urlopen( request, timeout = self.max_timeout)
            print(u.getcode())
            if u.getcode() != 304:
                self.__read_to_file( u, self.file_dest)
                print("Retornou o arquivo do GET \n\n" , u.info())
                self.last_modified = u.info()['Last-Modified']
                # srvLastModified = time.mktime(time.strptime(srvLastModified, "%a, %d %b %Y %H:%M:%S GMT"))
                self.did = True

        except urllib.error.URLError as inst:
            ## captura problemas no socket e na conexao
            print(type(inst))     # the exception instance
            print(inst.args)      # arguments stored in .args
            print(inst)           # __str__ allows args to be printed directly

        except urllib.error.HTTPError as inst:
            print(type(inst))     # the exception instance
            print(inst.args)      # arguments stored in .args
            print(inst)           # __str__ allows args to be printed directly

        except Exception as inst:
            print(type(inst))     # the exception instance
            print(inst.args)      # arguments stored in .args
            print(inst)           # __str__ allows args to be printed directly
            
        return self.did
