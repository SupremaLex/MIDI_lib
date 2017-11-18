class MidiError(Exception):
    def __init__(self, data, msg):
        self.data = data
        self.msg = msg

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return str(self.msg) + ': ' + str(self.data)


class DataLengthError(MidiError):
    def __init__(self, data):
        super().__init__(data, ' Data not corresponding to event type')


class StatusError(MidiError):
    def __init__(self, status):
        super().__init__(status, 'Wrong status byte')


class ChannelError(MidiError):
    def __init__(self, channelnumber):
        super().__init__(channelnumber, 'Wrong channel number')


class DataError(MidiError):
    def __init__(self, data):
        super().__init__(data, ' Wrong data')
