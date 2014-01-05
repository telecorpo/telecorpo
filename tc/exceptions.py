
from twisted.spread import pb

class PipelineFailure(Exception):
    pass

class NotFound(pb.Error):
    pass

class DuplicatedName(pb.Error):
    pass


