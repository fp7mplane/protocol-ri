import threading
from threading import Thread

import mplane.supervisor
import mplane.ui.clishell
import mplane.ui.svgui

class UISupervisor(mplane.supervisor.BaseSupervisor):
    def __init__(self, config):
        self._history = mplane.ui.svgui.History()
        print("Creating %s class" % self.__class__.__name__)
        super().__init__(config, run=False)
        if "gui-config" in config["supervisor"]:
            self._gui=mplane.ui.svgui.Gui(config, supervisor=self, exporter=self.from_cli, io_loop=self._io_loop)
        if "CLI" in config["supervisor"] and config["supervisor"]["CLI"]:
            self._cli=mplane.ui.clishell.ClientShell(config, self._client)
            Thread(target=self.run).start()
            self.run_cli()
        else:
            self.run()

    def run_cli(self):
        while not self._cli.exited:
            try:
                self._cli.cmdloop()
            except Exception as e:
                print("My keyboard interrupt")
                self._cli.handle_uncaught(e)		    
