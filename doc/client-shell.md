# mPlane Client Shell

The mPlane Client Shell is a simple client intended for debugging of mPlane infrastructures. To start it, simply run `mpcli`. It supports the following commands:

- `seturl`: Set the default URL for sending specifications and redemptions (when not given in a Capability's or Receipt's link section)
- `getcap`: Retrieve capabilities and withdrawals from a given URL, and process them.
- `listcap`: List available capabilities
- `showcap`: Show the details of a capability given its label or token
- `when`: Set the temporal scope for a subsequent `runcap` command
- `set`: Set a default parameter value for a subsequent `runcap` command
- `unset`: Unset a previously set default parameter value
- `show`: Show a previously set default parameter value
- `runcap`: Run a capability given its label or token
- `listmeas`: List known measurements (receipts and results)
- `showmeas`: Show the details of a measurement given its label or token.
- `tbenable`: Enable tracebacks for subsequent exceptions. Used for client debugging.

Type `help` to get this summary. Shut down the shell by typing EOF (control-D).
