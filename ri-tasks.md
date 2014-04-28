# Things to do

This is a list of stuff to do in the reference implementation, split into Core RI tasks and Additional RI tasks.

Please check with Brian <trammell@tik.ee.ethz.ch> and post to the <mplane-wp1@tlc.polito.it> list before starting work on one of these; please work in branches off ```develop```.

## Bugfixes

### client.py showmeas

showmeas in client.py doesn't work; fix this

### default period / period validation

It is possible for a specification without a period to match a capability with one. This should not happen, and probably requires a fix in mplane.model.When.

### client.py should prompt for when on runcap if not available.

## Design issues

### Design and implement poll scheduling for component-pull workflows

We need a message/interaction to allow component-pull workflows to be scheduled.

## Core RI tasks

### Implement periodically repeating Jobs.

The right way to do this is probably to have Specifications with schedules implement an iterator over future concrete Specifications, then have a completely separate class that uses this iterator to schedule one Job per subordinate Specification.

### Implement registry flexibility

- Define a simple JSON-based representation for a registry, without any special handling for structure, etc.
```
{ registry-version: "mplane-0.9",
  desc: 'Some human readable text explaining what this registry is.'
  includes: ['url', 'url'],
  elements: [
    { name: 'complete.structured.name',
      prim: 'natural',
      desc: 'A human-readable description for this Element.'}
  ]}
```
- Build classes for representing, parsing, unparsing these registries in mplane.model.
- mplane.model.Element should maintain a reference to the registry from which it was loaded; a fully qualified element name then becomes the URL plus the element name as anchor, i.e.: ```http://ict-mplane.eu/registry/1.0/#delay.twoway.icmp.ms```.
- Future work on better registry definition is future work

### Implement version section in mPlane messages

We need a version section in mPlane messages to allow us to make changes to structures in the future.

_Provisionally implemented. Currently dies if version present and not zero._

### Implement export section in mPlane messages

We need the export section, required for indirect export.

_Provisionally implemented_ though there's no code in any of the rest of the RI for dealing with it.

### Make exceptions work in Service.run()

Python's threading library catches exceptions, apparently. We'd like to catch exceptions in run() instead, and package them up as mplane.model.Exception instances.

## Additional RI tasks

### Build a generic HTTP server component CLI

### 