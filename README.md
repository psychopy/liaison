# Liaison Backend

Liaison provides a syntax for interfacing with a Python backend by sending commands as JSON.

## Getting started with Websocket Liaison

While Liaison is built to be general, it presently only supports sending/receiving messages over websocket.

### Installing

To use Liaison with websockets, you will need to install with the optional `websocket` dependencies:

```sh
pip install liaison-backend[websocket]
```

Then make sure you have something setup on your application frontend which can make command line calls, such as [Node's child_process module](https://nodejs.org/api/child_process.html).

### Getting constants

Liaison uses a few constant values to communicate when it's started and stopped. While you could hardcode these, you can also get them from Liaison via command line:
```sh
python -m liaison.constants
```

which will return a JSON string:
```json
{"START_MARKER": "LIAISON:CONNECTED", "STOP_MARKER": "LIAISON:DISCONNECTED"}
```

When Liaison starts, it will send the `START_MARKER`, and will send the `STOP_MARKER` when it stops, so looking out for these values lets you keep track of the life cycle of the Liaison backend.

### Starting Liaison

To start a Liaison backend on a particular websocket address, just call:

```sh
python -m liaison.websocket <address>
```

This will run continuously until told to stop, listening for messages on the given websocket address. It will send the `START_MARKER` constant to its stdout upon starting, and will send the `STOP_MARKER` constant upon stopping.

#### Example: Starting a Liaison backend from a Node (JavaScript) app

```javascript
import proc from "child_process";

// binary decoder for websocket messages
const decoder = new TextDecoder();
// choose an address to open the websocket on
const address = "localhost:8003";
// get liaison constants
const liaisonConstants = JSON.parse(
    proc.execSync(
        "python -m liaison.constants"
    )
);
// start process running liaison
const liaisonProcess = proc.spawn(
    `python -m liaison.websocket ${address}`
);
// wait for started message
var liaisonStarted = Promise.withResolvers()
liaisonProcess.stdout.on("data", evt => {
    // if message indicates liaison has started, resolve promise
    if (decoder.decode(evt) === `${liaisonConstants.START_MARKER}@${address}`) {
        liaisonStarted.resolve(evt)
    }
})
await liaisonStarted.promise
// create websoket to send messages over
let liaisonSocket = new WebSocket(`ws://${address}`);
```

### Companion object

Each instance of Liaison creates an instance of `Companion`; this is an object with its own namespace, whose methods Liaison can call, giving access to Python through them. Objects in the Companion's namespace can be used as an argument to any given function by prepending them with `$`. Companion objects have the following methods:

#### `get`

Get the value from this Companion's namespace which a string points to.

##### Parameters
- `target <string>` A string of attribute/key references starting with a name in this Companion's namespace or an importable package.

##### Returns
- `<any>` The value of the given target

#### `exists`

Check whether a target exists, either as a name in this Companion's namespace or as part of an installed Python module.

##### Parameters
- `target <string>` A string of attribute/key references starting with a name in this Companion's namespace or an importable package.

##### Returns
- `<boolean>` true/false according to whether the target exists

#### `init`

Initialize an object and store it in this Companion's namespace

##### Parameters
- `name <string>` Name to store the created object by
- `cls <string>` Resolvable string pointing to the class to initialise (or a callable to use as a constructor)
- `args <array>` Positional arguments to supply to the constructor
- `kwargs <object>` Named arguments to supply to the constructor

##### Returns
- `<string>` The name the object was registered to

#### `run`

Call the given function

##### Parameters
- `fcn <string>` Resolvable path to the function
- `args <array>` Positional arguments to pass to the function
- `kwargs <object>` Named arguments to pass to the function

##### Returns
- `<any>` Output from the function

#### `try`

The same as `run`, but called within a try:except statement

##### Parameters
- `fcn <string>` Resolvable path to the function
- `args <array>` Positional arguments to pass to the function
- `kwargs <object>` Named arguments to pass to the function

##### Returns
- `<object>` Object with a key "success" indicating whether the method executed successfully, and a key "result" containing either the output of the function or the caught error

#### `register`

Register something resolvable (e.g. a module, class or method) under a particular name

##### Parameters
- `name <string>` Name to register as
- `target <string>` Resolvable string pointing to object to register

##### Returns
- `<string>` Name the object was registered as

#### `store`

Store an arbitrary value in this Companion's namespace

##### Parameters
- `name <string>` Name to register as
- `value <string>` Value to store

##### Returns
- `<string>` Name the value was registered as

#### `ping`

Returns the word "pong". Useful for testing whether a Liaison is still alive, or send routine messages to keep a connection open.

### Sending messages

Once you have both a Liaison process and a websocket setup, you can send messages to Liaison which will be executed by its `Companion` object. Liason has access to any Python modules present in the python environment it was executed from. The syntax of these messages is as follows:

- `command <object>`
    - `command <string>` Companion method to execute, see above for options and inputs for each
    - `args <array>` Array of positional arguments to pass to the Companion method
    - `kwargs <object>` Object of key:value pairs indicating the keyword arguments to be passed to the Companion method
- `id <string>` An arbitrary ID; when the function returns, any output will be sent back as a websocket message with the same ID

#### Example: Performing a T-Test in scipy over Liaison
```javascript
// define some data to do a T-Test on
let a = [0.5982758 , 0.67019733, 0.68617796, 0.28764011]
let b = [0.41138649, 1.67023998, 1.0420896 , 1.49671732]
// create the command to send
let cmd = {
    command: {
        command: 'run',
        args: [
            "scipy.stats:ttest_ind", a, b
        ],
        kwargs: {
            equal_var: false
        }
    },
    id: crypto.randomUUID()
}
// send the command as a JSON string
liaisonSocket.send(
    JSON.stringify(cmd)
)
// wait for a reply (optional)
let replied = Promise.withResolvers()
let lsnr = evt => {
    // parse message
    let data = JSON.parse(evt.data)
    // if message is a reply to our command...
    if (data.evt.id !== cmd.id) {
        // stop listening
        liaisonSocket.removeEventListener("message", lsnr)
        // resolve/reject promise
        if (data.response) {
            replied.resolve(data.response)
        } else {
            replied.reject(data)
        }
    }    
}
liaisonSocket.addEventListener("message", lsnr)
// get response
let resp = await replied.promise
```

## History

Liaison was built by [Open Science Tools Ltd.](https://opensciencetools.org/) to provide an interface between the [PsychoPy Studio](https://github.com/psychopy/psychopy-studio) app and the [PsychoPy](https://github.com/psychopy/psychopy) Python library. Owing to the general usefulness of being able to interface with Python via JSON commands, we decided to release it as its own package, for general use. Liaison is distributed under an [MIT License](https://opensource.org/license/mit).