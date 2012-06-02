
__all__ = ['UserInput', 'Keyboard', 'Mouse', 'Keystream']


class UserInput(object):

    def __init__(self, timestamp=0.0):

        self.timestamp = float(timestamp)

class Keyboard(UserInput):

    def __init__(self, key, timestamp, holdtime=0.0):

        UserInput.__init__(self, timestamp)
        self.key = key # string
        self.holdTime = 0.0

class Mouse(UserInput):

    def __init__(self, timestamp, coord=(0.0,0.0), clickleft=False, clickright=False):

        UserInput.__init__(self, timestamp)
        self.moveCoordinates = coord # (float,float)
        self.clickLeft = clickleft # bool
        self.clickRight = clickright # bool

# holds a keyboard collection
class Keystream(UserInput):

    def __init__(self, timestamp, keystream=''):

        UserInput.__init__(self, timestamp)
        self.keystream = []
        for key in keystream:
            self.keystream.append(Keyboard(key))

    def keystreamToStr(self):

        return ','.join( [ k.key for k in self.keystream ] )
