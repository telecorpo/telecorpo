from twisted.spread import pb

class MultimediaException(Exception):
    pass

class PipelineFailure(MultimediaException):
    pass

class NotFound(pb.Error):
    pass

class DuplicatedName(pb.Error):
    pass

class ExitException(Exception):
    pass
