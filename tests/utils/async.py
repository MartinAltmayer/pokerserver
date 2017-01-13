from asyncio import Future


def return_done_future(result=None, exception=None):
    def future_creator(*args, **kwargs):  # pylint: disable=unused-argument
        future = Future()
        if exception is not None:
            future.set_exception(exception)
        else:
            future.set_result(result)
        return future

    return future_creator
