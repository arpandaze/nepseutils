def login_required(func):
    """
    Decorator to check if the user is logged in or not.
    If not, login and then execute the function.
    """

    def wrapper(self, *args, **kwargs):
        if not self.auth_token:
            self.login()
        return func(self, *args, **kwargs)

    return wrapper


def autosave(func):
    """
    Decorator to save the account after executing the function.
    """

    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        self.save()
        return result

    return wrapper
