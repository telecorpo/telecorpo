
from twisted.spread import pb

class NotFound(pb.Error):
    pass


class DuplicatedName(pb.Error):
    pass

