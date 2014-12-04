#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
##
# mPlane Protocol Reference Implementation
# TLS context for mPlane clients and components
#
# (c) 2014 mPlane Consortium (http://www.ict-mplane.eu)
#     Author: Stefano Pentassuglia <stefano.pentassuglia@ssbprogetti.it>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
#


# ## Common TLS Configuration

# Clients and components should be able to load a configuration file 
# (`tls.conf`) which refers to CA, private key, and certificate files, 
# for setting up a TLS context. This TLS context should be common to 
# all other code (`mplane/tls.py`). When the TLS configuration file 
# is not present, `https://` URLs will not be supported; when present, 
# the use of TLS will be selected based on the URL used.

# - SSB will pull this out of existing utils.py and stepenta/RI code.
