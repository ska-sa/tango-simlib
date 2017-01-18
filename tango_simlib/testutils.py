import logging
import time
import mock

LOGGER = logging.getLogger(__name__)

def set_attributes_polling(test_case, device_proxy, device_server, poll_periods):
    """Set attribute polling and restore after test

    Parameters
    ----------

    test_case : unittest.TestCase instance
    device_proxy : PyTango.DeviceProxy instance
    device_server : PyTango.Device instance
        The instance of the device class `device_proxy` is talking to
    poll_periods : dict {"attribute_name" : poll_period}
        `poll_poriod` in milliseconds as per Tango APIs, 0 or falsy to disable
        polling.

    Return value
    ------------

    restore_polling : function
        This function can be used to restore polling if it is to happen before the end of
        the test. Should be idempotent if only one set_attributes_polling() is called per
        test.
    """
    # TODO (NM 2016-04-11) check if this is still needed after upgrade to Tango 9.x For
    # some reason it only works if the device_proxy is used to set polling, but the
    # device_server is used to clear the polling. If polling is cleared using device_proxy
    # it seem to be impossible to restore the polling afterwards.
    attributes = poll_periods.keys()
    initial_polling = {attr: device_proxy.get_attribute_poll_period(attr)
                       for attr in attributes}
    retry_time = 0.5

    for attr in attributes:
        initial_period = initial_polling[attr]
        new_period = poll_periods[attr]
        # Disable polling for attributes with poll_period of zero / falsy
        # zero initial_period implies no polling currently configed
        if not new_period and initial_period != 0:
            LOGGER.debug('not setting polling for {}'.format(attr))
            device_server.stop_poll_attribute(attr)
        else:
            # Set the polling
            LOGGER.debug('setting polling for {}'.format(attr))
            try:
                device_proxy.poll_attribute(attr, new_period)
                # TODO See (NM 2016-04-11) comment below about back-to-back calls
                time.sleep(0.05)
            except Exception:
                retry = True
                LOGGER.warning('Setting polling of attribute {} in {} due to unhandled'
                               'exception in poll_attribute command'
                               .format(attr, retry_time), exc_info=True)
            else:
                retry = False

            if retry:
                time.sleep(retry_time)
                device_proxy.poll_attribute(attr, new_period)

    def restore_polling():
        """Restore initial polling, for use during cleanup / teardown"""
        for attr, period in initial_polling.items():
            if period == 0:
                continue            # zero period implies no polling, nothing to do
            try:
                device_proxy.poll_attribute(attr, period)
                # TODO (NM 2016-04-11) For some reason Tango doesn't seem to handle
                # back-to-back calls, and even with the sleep it sometimes goes bad. Need
                # to check if this is fixed (and core dumps) when we upgrade to Tango 9.x
                time.sleep(0.05)
            except Exception:
                retry = True
                LOGGER.warning('retrying restore of attribute {} in {} due to unhandled'
                               'exception in poll_attribute command'
                               .format(attr, retry_time), exc_info=True)
            else:
                retry = False

            if retry:
                time.sleep(retry_time)
                device_proxy.poll_attribute(attr, period)

    test_case.addCleanup(restore_polling)
    return restore_polling

def disable_attributes_polling(test_case, device_proxy, device_server, attributes):
    """Disable polling for a tango device server, en re-eable at end of test"""
    new_periods = {attr: 0 for attr in attributes}
    return set_attributes_polling(
        test_case, device_proxy, device_server, new_periods)


class ClassCleanupUnittestMixin(object):
    """Implement class-level setup/deardown semantics that emulate addCleanup()

    Subclasses can define a setUpClassWithCleanup() method that wraps addCleanup
    such that cls.addCleanup() can be used to add cleanup methods that will be
    called at class tear-down time.

    """

    _class_cleanups = []

    @classmethod
    def setUpClassWithCleanup(cls):
        """Do class-level setup  and ensure that cleanup functions are called

        It is inteded that subclasses override this class method

        In this method calls to `cls.addCleanup` is forwarded to
        `cls.addCleanupClass`, which means callables registered with
        `cls.addCleanup()` is added to the class-level cleanup function stack.

        """
        super(ClassCleanupUnittestMixin, cls).setUpClassWithCleanup()

    @classmethod
    def addCleanupClass(cls, function, *args, **kwargs):
        """Add a cleanup that will be called at class tear-down time"""
        cls._class_cleanups.append((function, args, kwargs))

    @classmethod
    def doCleanupsClass(cls):
        """Run class-level cleanups registered with `cls.addCleanupClass()`"""
        results = []
        while cls._class_cleanups:
            function, args, kwargs = cls._class_cleanups.pop()
            try:
                function(*args, **kwargs)
            except Exception:
                LOGGER.exception('Exception calling class cleanup function')
                results.append(sys.exc_info())

        if results:
            LOGGER.error('Exception(s) raised during class cleanup')

    @classmethod
    def setUpClass(cls):
        """Call `setUpClassWithCleanup` with `cls.addCleanup` for class-level cleanup

        Any exceptions raised during `cls.setUpClassWithCleanup` will result in
        the cleanups registered up to that point being called before logging
        the exception with traceback.

        """
        try:
            with mock.patch.object(cls, 'addCleanup') as cls_addCleanup:
                cls_addCleanup.side_effect = cls.addCleanupClass
                cls.setUpClassWithCleanup()
        except Exception:
            LOGGER.exception('Exception during setUpClass')
            cls.doCleanupsClass()

    @classmethod
    def tearDownClass(cls):
        cls.doCleanupsClass()
