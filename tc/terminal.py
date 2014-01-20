import itertools
from twisted.internet import protocol
from twisted.protocols import basic

from tc import NotFound

from tc.broker import RemoteType

class TerminalFactory(protocol.Factory):
    def __init__(self, broker):
        self.broker = broker

    def buildProtocol(self, addr):
        return TerminalProtocol(self)

    def listAll(self):
        for ref, data in self.broker.remotes.values():
            if data.kind == RemoteType.CAMERA:    kind = 'Camera'
            elif data.kind == RemoteType.MANAGER: kind = 'Manager'
            elif data.kind == RemoteType.SCREEN:  kind = 'Screen'
            yield data.name, kind


    def listKind(self, kind):
        if kind.startswith('cam'):   kind = RemoteType.CAMERA
        elif kind.startswith('man'): kind = RemoteType.MANAGER
        elif kind.startswith('scr'): kind = RemoteType.SCREEN
        
        for ref, data in self.broker.remotes.values():
            if data.kind == kind:
                yield data.name

    def route(self, cam_name, scr_name):
        self.broker.remote_route(cam_name, scr_name)

    def changeLatency(self, scr_name, delta):
        self.broker.remote_changeLatency(scr_name, delta)


class TerminalProtocol(basic.LineOnlyReceiver):

    delimiter = '\n'
    prompt = ">> "

    def __init__(self, factory):
        self.factory = factory
        # self.name = factory.name

    def connectionMade(self):
        self.sendLine("\nWellcome to Telecorpo!\n")
        self.showHelp()
    
    def lineReceived(self, line):
        if len(line.strip()) == 0:
            return self.sendPrompt()

        tokens = line.split()

        cmd = tokens[0]
        if cmd in ["?", "h", "help"]:
            return self.showHelp()
        if cmd in ["l", "list"]:
            if len(tokens) > 2:
                return self.badCommand()
            if len(tokens) == 1:
                self.sendResponse("\n".join("%s %s" % (n, k)
                    for n, k in self.factory.listAll()))
            else:
                kind = tokens[1]
                self.sendResponse("\n".join(
                    n for n in self.factory.listKind(kind)))
            return
        
        elif cmd in ["la", "latency"]:
            if len(tokens) != 3:
                return self.badCommand()
            try:
                scr, delta = tokens[1:]
                delta = int(delta)
            except:
                return self.badCommand()
            try:
                self.factory.changeLatency(scr, int(delta)*1000)
                return self.sendPrompt()
            except NotFound:
                self.sendResponse("%s not found." % scr)

        elif cmd in ["r", "route"]:
            if len(tokens) != 3:
                return self.badCommand()
            cam, scr = tokens[1:]
            try:
                self.factory.route(cam, scr)
                self.sendPrompt()
            except NotFound:
                self.sendResponse("%s or %s not found." % (cam, scr))
        elif cmd in ["q", "quit"]:
            self.transport.loseConnection()
        else:
            self.badCommand()
    
    def showHelp(self):
        self.sendLine("Available commands:")
        self.sendLine("\tlatency SCREEN DELTA")
        self.sendLine("\tlist [camera|screen]")
        self.sendLine("\troute CAMERA SCREEN")
        self.sendLine("\tquit")
        self.sendLine("\thelp")
        self.sendLine("")
        self.sendPrompt()

    def sendPrompt(self): 
        self.sendResponse()

    def sendResponse(self, text=None):
        if text:
            self.sendLine(text.strip())
        self.delimiter, delim = '\0', self.delimiter
        self.sendLine(self.prompt)
        self.delimiter = delim

    def badCommand(self):
        return self.sendResponse("Bad command.")
