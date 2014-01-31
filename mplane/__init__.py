"""
.. moduleauthor:: Brian Trammell <brian@trammell.ch>

This module provides a reference implementation of the mPlane protocol. It is
organized into layers. :mod:`mplane.model` implements the mPlane protocol 
information model: message types, the element registry, and various support
classes. 

On top of the information model, the mplane.client module defines interfaces 
for building mPlane clients, and the mplane.component module for building
mPlane components and component proxies.

.. note:: mplane.client and mplane.component are not yet implemented

The mplane.super module contains a simple supervisor implementation, built
atop the client and component modules, for demonstration purposes. Specifically,
this simple supervisor contains no reasoner.

.. note:: mplane.super is not yet implemented

The mplane.cli module contains a simple command-line interface for controlling
supervisors and components.

.. note:: mplane.cli is not yet implemented

This software is copyright 2013 the mPlane Consortium. 
It is made available under the terms of the 
`GNU Lesser General Public License <http://www.gnu.org/licenses/lgpl.html>`_, 
version 3 or, at your option, any later version.

"""

from . import model
from . import scheduler