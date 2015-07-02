# Implementing a Component

The component runtime provides a framework for building components for both component-initiated and client-initiated workflows. To implement a component for use with this framework:

- Implement each measurement, query, or other action performed by the component as a subclass of `mplane.scheduler.Service`. Each service is bound to a single capability. Your service must implement at least the `mplane.scheduler.Service.run(self, specification, check_interrupt)` method. This method should run the implemented measurement or query to completion. This measurement corresponds to the `specification` (an instance of `mplane.model.Specification`), which itself corresponds to the capability bound to the service (an instance of `mplane.model.Capability`). The method should return an `mplane.model.Result`. Long-running methods (with common runtimes measured in seconds or more) should periodically call the function passed as `check_interrupt` and return a truncated `mplane.model.Result` when that function returns True.

- Implement a `services` function in your module that takes a set of keyword arguments derived from the configuration file section, and returns a list of Services provided by your component. For example:

```python
def service(**kwargs):
    return [MyFirstService(kwargs['local-ip-address']),
            MySecondService(kwargs['local-ip-address'])]
```

- Create a module section in the component configuration file; for example if your module is called mplane.components.mycomponent:

```
[service_mycomponent]
module: mplane.components.mycomponent
local-ip-address: 10.2.3.4
```

- Run `mpcom` to start your component. The `--config` argument points to the configuration file to use.
