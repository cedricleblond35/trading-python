from Service.JsonSocket import JsonSocket
from Configuration.Config import Config
from Service.Command import Command
from Configuration.Log import Log


class APIClient(JsonSocket):
    def __init__(self, address=Config.DEFAULT_XAPI_ADDRESS, port=Config.DEFAULT_XAPI_PORT, encrypt=True):
        super(APIClient, self).__init__(address, port, encrypt)
        self.log = Log().logger
        self._command = Command()
        if not self.connect():
            raise Exception(
                "Cannot connect to " + address + ":" + str(port) + " after " + str(
                    Config.API_MAX_CONN_TRIES) + " retries")

    def execute(self, dictionary):
        self._sendObj(dictionary)
        return self._readObj()

    def disconnect(self):
        self.close()

    def commandExecute(self, commandName, arguments=None):
        return self.execute(self._command.baseCommand(commandName, arguments))

    def identification(self):
        self._sendObj(self._command.loginCommand())
        return self._readObj()

    def printSocketLog(self):
        self.log(self.socket)
