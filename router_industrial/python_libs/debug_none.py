




class debug_none :

    logger = None

    def __init__(self):
        pass

    @staticmethod
    def create_logger():
        if debug_none.logger == None :
            debug_none.logger = debug_none()
        return debug_none.logger

    @staticmethod
    def get_logger():
        if debug_none .logger == None :
            debug_none.logger = debug_none .create_logger()
        return debug_none .logger

    def debug( self, mesg) :
        pass

    def error( self, mesg) :
        pass

    def info( self, mesg) :
        pass

    def warn( self, mesg) :
        pass

    def exception( self, mesg) :
        pass
