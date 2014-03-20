import itertools
from twisted.internet import protocol
from twisted.protocols import basic

from tc.exceptions import NotFound

class TerminalFactory(protocol.Factory):
    def __init__(self, pbroot):
        self.pbroot = pbroot

    def buildProtocol(self, addr):
        return TerminalProtocol(self)

    def listAll(self):
        for client in itertools.chain(self.pbroot.cameras.values(),
                                      self.pbroot.screens.values()):
            yield client.name, client.kind

    def listKind(self, kind):
        if kind.lower() == 'cameras':
            clients = self.pbroot.cameras.values()
        elif kind.lower() == 'screens':
            clients = self.pbroot.screens.values()

        for client in clients:
            yield client.name

    def route(self, cam_name, scr_name):
        self.pbroot.remote_route(cam_name, scr_name)

    def listRoutes(self):
        for route in self.pbroot.routes:
            yield route



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
                if kind == 'routes':
                    self.sendResponse("\n".join("%s -> %s" % (c, s)
                        for c, s in self.factory.listRoutes()))
                elif kind in ['cameras', 'screens']:
                    self.sendResponse("\n".join(
                        n for n in self.factory.listKind(kind)))
                else:
                    self.badCommand()
            return
        
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
        self.sendLine("\tlist [cameras|screens|routes]")
        self.sendLine("\troute CAMERA SCREEN")
        self.sendLine("\tquit")
        self.sendLine("\tHelp")
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
