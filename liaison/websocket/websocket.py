import sys
import asyncio
import websockets
import json
import traceback
import types
from websockets.sync.client import connect
from ..base import BaseLiaison
from ..constants import START_MARKER, STOP_MARKER


class LiaisonJSONEncoder(json.JSONEncoder):
    """
    JSON encoder which calls the `getJSON` method of an object (if it has one) to convert to a
    string before JSONifying.
    """
    def default(self, o):
        try:
            # if object has a getJSON method, use it
            if hasattr(o, "getJSON"):
                return o.getJSON()
        except:
            # if there's an error in the getJSON method, continue so we can try regular encoding
            pass
        # if given a module, construct an import string
        if isinstance(o, types.ModuleType):
            return f"python:///{o.__name__}"
        # if given a class or method, construct an import string
        if isinstance(o, (type, types.FunctionType)):
            return f"python:///{o.__module__}:{o.__qualname__}"

        # otherwise behave as normal
        try:
            return json.JSONEncoder.default(self, o=o)
        except TypeError:
            return str(o)


class WebsocketLiaison(BaseLiaison):
    def __init__(self, host="localhost", port="8001", companion=None):
        BaseLiaison.__init__(self, companion)
        # store host and port
        self.host = host
        self.port = port
        # attribute to store websocket connection in
        self.com = None
        self.server = None
        # create an asynchronous loop
        self.loop = asyncio.new_event_loop()
        # stores whether this liaison is active
        self.alive = False
    
    def start(self):
        async def process_messages(websocket):
            # store websocket handle
            self.com = websocket
            # start off alive
            self.alive = True
            # run until killed
            while self.alive:
                try:
                    # wait for a message
                    message = await websocket.recv()
                    # store message
                    self.messages.append(message)
                    # parse it from JSON
                    message = json.loads(message)
                    # process it
                    try:
                        resp = {
                            'response': self.process_command(message['command']),
                            'tag': "response",
                            'evt': message,
                        }
                    except Exception as err:
                        # send errors to the websocket
                        resp = {
                            'error': traceback.format_exception(err),
                            'tag': "error",
                            'evt': message
                        }
                    # make sure resp is a JSON string
                    if not isinstance(resp, str):
                        try:
                            resp = json.dumps(resp, cls=LiaisonJSONEncoder)
                        except:
                            resp = str(resp)
                    # send response
                    await websocket.send(resp)
                except json.JSONDecodeError as err:
                    # send error
                    sys.stdout.write(traceback.format_exception(err))
                    sys.stsout.flush()
                    # store error as a message
                    self.messages.append(err)
                except (websockets.ConnectionClosedOK, websockets.ConnectionClosedError) as err:
                    # send error
                    sys.stdout.write(traceback.format_exception(err))
                    sys.stsout.flush()
                    # store end message / error as a message
                    self.messages.append(err)
                    # clear ref to websocket
                    self.com = None
                    # kill
                    self.stop()
                except Exception as err:
                    sys.stdout.write(traceback.format_exception(err))
                    sys.stsout.flush()
        
        async def run():
            # create future
            future = self.loop.create_future()
            # await future to continuously serve
            async with websockets.serve(process_messages, self.host, self.port, compression=None) as self.server:
                # post start message in stdout
                sys.stdout.write(f"{START_MARKER}@{self.host}:{self.port}")
                sys.stdout.flush()
                # wait until closed
                await future
                # post stop message in stdout
                sys.stdout.write(f"{STOP_MARKER}@{self.host}:{self.port}")
                sys.stdout.flush()
        
        # run loop until complete
        self.loop.run_until_complete(
            run()
        )

    def stop(self):
        self.alive = False
    
    def send(self, message, timeout=1):
        # make sure message is a JSON string
        if not isinstance(message, str):
            try:
                message = json.dumps(message, cls=LiaisonJSONEncoder)
            except:
                message = str(message)
        # send
        asyncio.run_coroutine_threadsafe(
            self.com.send(message),
            loop=self.loop
        )


def send_message(liaison, message, timeout=1):
    """
    Send a message to the WebsocketLiaison at the given host and port

    Parameters
    ----------
    liaison : WebsocketLiaison
        WebsocketLiaison to send the message to
    message : any
        Message to send (will be coerced to a JSON string)
    timeout : int, optional
        Time at which to give up if no response is received, by default 1

    Returns
    -------
    any
        Response from the Liaison
    """
    # make sure message is a JSON string
    if not isinstance(message, str):
        message = json.dumps(message, cls=LiaisonJSONEncoder)
    # send
    return liaison.send(message, timeout=timeout)
