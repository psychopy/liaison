from .companion import Companion
from pathlib import Path
import json
import jsonschema


class BaseLiaison:

    command_schema = json.loads(
        (Path(__file__).parent / "companion" / "command.schema.json").read_text()
    )

    def __init__(self, companion:Companion=None):
        # make a companion if none given
        if companion is None:
            companion = Companion()
        # store ref to companion
        self.companion = companion
        # store ref to self in companion
        companion.namespace['liaison'] = self
        # array for messages
        self.messages = []
    
    def process_command(self, command):
        # if not a valid command, do nothing
        try:
            jsonschema.validate(command, self.command_schema)
        except jsonschema.exceptions.ValidationError:
            return
        # get args
        args = command.get('args', [])
        kwargs = command.get('kwargs', {})
        # get method from command name
        command = self.companion.commands[command['command']]
        # call
        return command(*args, **kwargs)