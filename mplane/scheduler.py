#
# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
#
#
# mPlane Protocol Reference Implementation
# Component and Client Job Scheduling
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Brian Trammell <brian@trammell.ch>
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
import mplane.sec

class Service(object):
    """
    A Service binds some runnable code to an 
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

    def __repr__(self):
        return "<Service for "+repr(self._capability)+">"

class Job(object):
    """
    A Job binds some running code to an mPlane.model.Specification 
    within a component. A Job can be thought of as a specific 
    instance of a Service presently running, or ready to run at some 
    point in the future.

    Each Job will result in a single Result.
    """
    result = None
    exception = None
    _thread = None
    _started_at = None
    _ended_at = None
    _exception_at = None
    _replied_at = None
    service = None
    session = None
    specification = None
    receipt = None
    _interrupt = None

    def __init__(self, service, specification, session=None):
        super(Job, self).__init__()
        self.service = service
        self.session = session
        self.specification = specification
        self.receipt = mplane.model.Receipt(specification=specification)
        self._interrupt = threading.Event()

    def __repr__(self):
        return "<Job for "+repr(self.specification)+">"

    def _run(self):
        self._started_at = datetime.utcnow()
        try:
            self.result = self.service.run(self.specification, 
                                           self._check_interrupt)
        except Exception as e:
            self.exception = mplane.model.Exception(
                            token=self.specification.get_token(), 
                            errmsg=str(e))
            print("Got exception in _run(), returning "+str(self.exception))
            self._exception_at = datetime.utcnow()
        self._ended_at = datetime.utcnow()

    def _check_interrupt(self):
        return self._interrupt.is_set()

    def _schedule_now(self):
        # spawn a thread to run the service
        threading.Thread(target=self._run).start()
        
    def schedule(self):
        """
        Schedule this job to run.
        """
        # Always schedule queries immediately without interrupt
        if self.specification.is_query():
            (start_delay, end_delay) = (0, None)
        else:
            (start_delay, end_delay) = self.specification.when().timer_delays()

        if start_delay is None:
            return

        # start interrupt timer
        if end_delay is not None:
            threading.Timer(end_delay, self.interrupt).start()
            print("Will interrupt "+repr(self)+" after "+str(end_delay)+" sec")

        # start start timer
        if start_delay > 0:            
            print("Scheduling "+repr(self)+" after "+str(start_delay)+" sec")
            threading.Timer(start_delay, self._schedule_now).start()
        else:
            print("Scheduling "+repr(self)+" immediately")
            self._schedule_now()

    def interrupt(self):
        """Interrupt this job."""
        self._interrupt.set()

    def failed(self):
        return self.exception is not None

    def finished(self):
        """Return True if the job is complete."""
        return self.result is not None

    def get_reply(self):
        """
        If a result is available for this Job (i.e., if the job is 
        done running), return it. Otherwise, create a receipt from 
        the Specification and return that.

        """
        self._replied_at = datetime.utcnow()
        if self.failed():
            return self.exception
        elif self.finished():
            return self.result
        else:
            return self.receipt

class Scheduler(object):
    """
    Scheduler implements the common runtime of a Component within the
    reference implementation. Components register Services bound to
    Capabilities with add_service(), and submit jobs for scheduling using
    submit_job().

    """
    def __init__(self, security):
        super(Scheduler, self).__init__()
        self.services = []
        self.jobs = {}
        self._capability_cache = {}
        self._capability_keys_ordered = []
        self.ac = mplane.sec.Authorization(security)

    def receive_message(self, user, msg, session=None):
        """
        Receive and process a message. 
        Returns a message to send in reply.

        """
        reply = None
        if isinstance(msg, mplane.model.Specification):
            reply = self.submit_job(user, specification=msg, session=session)
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
        """Add a service to this Scheduler"""
        print("Added "+repr(service))
        self.services.append(service)
        cap = service.capability()
        self._capability_cache[cap.get_token()] = cap
        self._capability_keys_ordered.append(cap.get_token())

    def capability_keys(self):
        """
        Return keys (tokens) for the set of cached capabilities 
        provided by this scheduler's services.

        """
        return self._capability_keys_ordered

    def capability_for_key(self, key):
        """
        Return a capability for a given key.
        """
        return self._capability_cache[key]

    def submit_job(self, user, specification, session=None):
        """
        Search the available Services for one which can 
        service the given Specification, then create and schedule 
        a new Job to execute the statement. 

        """
        # linearly search the available services
        for service in self.services:
            if specification.fulfills(service.capability()):
                if self.ac.check_azn(service.capability()._label, user):
		            # Found. Create a new job.
                    print(repr(service)+" matches "+repr(specification))
                    if (specification.has_schedule()):
                        new_job = MultiJob(service=service,
		                                   specification=specification,
		                                   session=session)
                    else:
                        new_job = Job(service=service,
		                              specification=specification,
		                              session=session)

                    # Key by the receipt's token, and return
                    job_key = new_job.receipt.get_token()
                    if job_key in self.jobs:
                        # Job already running. Return receipt
                        print(repr(self.jobs[job_key])+" already running")
                        return self.jobs[job_key].receipt

                    # Keep track of the job and return receipt
                    new_job.schedule()
                    self.jobs[job_key] = new_job
                    print("Returning "+repr(new_job.receipt))
                    return new_job.receipt
                    
                # user not authorized to request the capability
                print("Not allowed to request this capability: " + repr(specification))
                return mplane.model.Exception(token=specification.get_token(),
                            errmsg="User has no permission to request this capability")

        # fall-through, no job
        print("No service for "+repr(specification))
        return mplane.model.Exception(token=specification.get_token(),
                    errmsg="No service registered for specification")

    def job_for_message(self, msg):
        """
        Given a message (generally a Redemption), 
        return the Job matching its token.

        """
        return self.jobs[msg.get_token()]

    def prune_jobs(self):
        """
        Currently does nothing. Will remove Jobs which are 
        finished and whose Results have been retrieved 
        from the scheduler in a future version.

        """
        pass
