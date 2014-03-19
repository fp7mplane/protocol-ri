"""
.. moduleauthor:: Brian Trammell <brian@trammell.ch>

This module provides a reference implementation of the mPlane protocol. It is
organized into layers. :mod:`mplane.model` implements the mPlane protocol 
information model: message types, the element registry, and various support
classes. 

On top of the information model, the :mod:`mplane.scheduler` module defines
a framework for binding :class:`mplane.model.Capability` classes to runnable
code, and for invoking that code on the receipt of mPlane statements; this is
used to build components and frameworks. 

The :mod:`mplane.client` module
defines interfaces for building clients, as well as providing a CLI
to a completely generic mPlane HTTP client.

The :mod:`mplane.httpsrv` module binds the Information Model to the Tornado
web application framework, for building component-push HTTP components.

The :mod:`mplane.ping` module implements an example ping application using 
the mPlane reference implementation.

This software is copyright 2013 the mPlane Consortium. 
It is made available under the terms of the 
`GNU Lesser General Public License <http://www.gnu.org/licenses/lgpl.html>`_, 
version 3 or, at your option, any later version.

"""

from . import model
from . import scheduler