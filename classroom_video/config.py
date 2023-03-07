import os


class ClassProperty(property):
    """Thanks denis-ryzhkov: https://stackoverflow.com/questions/128573/using-property-on-classmethods
    This decorator helps me access Config Property that get set by env vars in a more natural way
    Was motivated to do this because we use dotenv and that may load env vars before this python file gets
    imported"""

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class Config:
    @ClassProperty
    def WF_DATA_PATH(cls):
        # pylint: disable=no-self-argument
        return os.getenv("WF_DATA_PATH", "./")
