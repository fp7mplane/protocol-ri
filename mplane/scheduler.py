#
# mPlane Protocol Reference Implementation
# Component and Client Job Scheduling
#
# (c) 2013 mPlane Consortium (http://www.ict-mplane.eu)
#          Author: Brian Trammell <brian@trammell.ch>
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

"""
Implements the dynamics of capabilities, specifications, and 
results within the mPlane reference component.

"""

from datetime import datetime, timedelta
import threading
import mplane.model

class Service(object):
    """
    A Service is a binding of some runnable code to an 
    mplane.model.Capability provided by a component.

    To use services with an mPlane scheduler, inherit from 
    mplane.scheduler.Service or one of its subclasses 
    and implement run().

    """
    def __init__(self, capability):
        super(Service, self).__init__()
        self._capability = capability

    def run(self, specification, check_interrupt):
        """
        Run this service given a specification which matches the capability.
        This is called by the scheduler, and should be implemented by
        a concrete subclass of Service.

        The implementation should extract its parameters from a given
        mplane.model.Specification, and return its result values in a 
        mplane.model.Result derived therefrom.

        After each row or logically grouped set of rows, the implementation
        should call the check_interrupt function to determine whether it 
        should stop; if this function returns True, the implementation should 
        terminate its processing in an orderly fashion and return its results.

        Each method will be called within its own thread and/or process. 

        """
        raise NotImplementedError("Cannot instantiate an abstract Service")

    def capability(self):
        return self._capability

class Job(object):
    """
    A Job is a binding of some running code to an
    mPlane.model.Specification within a component. A Job can
    be thought of as a specific instance of a Service presently
    running, or ready to run at some point in the future.

    """
    def __init__(self, service, specification, session=None):
        super(Job, self).__init__()
        self.service = service
        self.session = session
        self.specification = specification
        self.receipt = mplane.model.Receipt(specification=specification)
        self.result = None
        self._thread = None
        self._started_at = None
        self._ended_at = None
        self._replied_at = None
        self._interrupt = threading.Event()

    def _run(self):
        self._started_at = datetime.utcnow()
        self.result = self.service.run(self.specification, 
                                       self._check_interrupt)
        self._ended_at = datetime.utcnow()

    def _check_interrupt(self):
        return self._interrupt.is_set()

    def _schedule_now(self):
        """
        Schedule this job to run immediately. 
        Used internally by schedule().

        """
        # spawn a thread to run the service
        threading.Thread(target=self._run).start()

        # set up interrupt timer if necessary
        duration = self.specification.job_duration()
        if duration is not None and duration > 0:
            threading.Timer(self._duration.total_seconds(), self.interrupt).start()
        
    def schedule(self):
        """
        Schedule this job to run.
        """
        delay = self.specification.job_delay()

        # start a timer to schedule in the future if we have delay
        if delay > 0:
            threading.Timer(self._delay.total_seconds(), self._schedule_now).start()
        else:
            self._schedule_now()

    def interrupt(self):
        """
        Interrupt this job.

        """
        self._interrupt.set()

    def get_reply(self):
        """
        If a result is available for this Job (i.e., if the job is done running), 
        return it. Otherwise, create a receipt from the specification and return that.

        """
        self._replied_at = datetime.utcnow()
        if (self.result is not None):
            return self.result
        else:
            return self.receipt

class Scheduler(object):
    """
    documentation for scheduler goes here

    """
    def __init__(self):
        super(Scheduler, self).__init__()
        self.services = []
        self.jobs = {}
        self.next_job_serial = 0

    def receive_message(self, session, msg):
        """
        Receive and process a message from a session. 
        Returns a message to send in reply.

        """
        reply = None
        if isinstance(msg, mplane.model.Specification):
            reply = self.start_job(specification=specification, session=session)
        elif isinstance (msg, mplane.model.Redemption):
            job_key = msg.get_token()
            if job_key in self.jobs:
                reply = self.jobs[job_key].get_reply()
            else: reply = mplane.model.Exception(token=job_key, 
                errmsg="Unknown job")
        else:
            reply = mplane.model.Exception(token=msg.get_token(), 
                errmsg="Unexpected message type")

        return reply

    def add_service(self, service):
        self.services.append(service)

    def start_job(self, specification, session=None):
        """
        Search the available Services for one which can service the statement, 
        then create and schedule a new job to execute the statement.

        """
        # linearly search the available services
        for service in self.services:
            if specification.fulfills(service.capability):
                # Found. Create a new job.
                new_job = Job(service=service, \
                              specification=specification, \
                              session=session)

                # Key by the receipt's token, and return
                job_key = new_job.receipt.get_token()
                if job_key in self.jobs:
                    # Job already running. Return receipt
                    return self.jobs[job_key].receipt

                # Keep track of the job and return receipt
                new_job.schedule()
                self.jobs[job_key] = new_job
                return new_job.receipt

        # fall-through, no job 
        return mplane.model.Exception(token=specification.get_token(),
                    errmsg="No service registered for specification")


