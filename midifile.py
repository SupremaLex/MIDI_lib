from struct import pack
from midilib.midi_exceptions import *


class Header:
    """Class Header describes describes the structure of the standard midi file,
     i.e 'MThd', length, file format, number of tracks in file and Pulses Per Quarter Note(PPQN)
     """
    def __init__(self, file_format, ntracks, ppqn):
        if file_format not in [0, 1, 2]:
            raise MidiError(file_format, 'Wrong file format')
        if file_format == 0 and ntracks != 1:
            raise MidiError(file_format, 'Format 0 has only 1 track')
        if ntracks >= 15:
            raise MidiError(file_format, '16 tracks is maximum for SMF( 1 track for each channel)')
        self.mthd = b'MThd'
        self.length = 6
        self.file_format = file_format
        self.ntracks = ntracks
        self.ppqn = ppqn

    def to_hex(self):
        """Get bytes representation of the Header"""
        mthd = self.mthd
        params = pack('>LHHH', self.length, self.file_format, self.ntracks, self.ppqn)
        return mthd+params

    def __str__(self):
        return str((self.mthd, self.length, self.file_format, self.ntracks, self.ppqn))


class Event:
    """Class Event describes the general structure of all events in Midi protocol, this implementation implies that
    delta time is a part of each event, also all events have status byte and some portion of data
    """
    def __init__(self, delta_time, status, data=[]):
        if not (0 <= delta_time <= 4294967167):
            raise MidiError(delta_time, ' Wrong delta time value')
        self.delta_time = delta_time
        self.status = status
        self.data = self.str_to_int(data[:])
        self.event = [
                        self.variable_len(self.delta_time),
                        [self.status],
                        self.data
                      ]

    def to_hex(self):
        """Get bytes representation of event
        """
        b = b''.join(map(bytes, self.event))
        return b

    @staticmethod
    def str_to_int(data_with_str):
        """Converting all str data to int data
        """
        data = list(map(lambda x: ord(x) if isinstance(x, str) else x, data_with_str))
        return data

    @staticmethod
    def variable_len(time_or_len):
        """Convert int delta time or length to variable length quantity ( 1-4 bytes)
        """
        n = time_or_len
        variable_length = [n & 0x7f]
        n >>= 7
        for cnt in range(2):
            if n > 0:
                variable_length.append((n & 0x7f) | 0x80)
                n >>= 7
        byte_string = bytes(variable_length[::-1])
        return byte_string

    @property
    def get_delta_time(self):
        return bytes(self.event[0])

    def __str__(self):
        return self.__class__.__name__ + ' : '


class MidiEvent(Event):
    """Class MidiEvent describes, obviously, a midievent such as 'Note on' or 'Note off'
    """
    def __init__(self, delta_time, status, channel_number=0, data=[]):
        if not (0 <= channel_number <= 15):
            raise ChannelError(channel_number)
        if status not in StatusBytes.midi:
            raise StatusError(status)
        if (status in [192, 223] and len(data) != 1) or (status not in [192, 223] and len(data) != 2):
            raise DataLengthError(data)
        if max(data) > 127:
            raise DataError(data)
        super().__init__(delta_time=delta_time, status=status + channel_number, data=data)

    def __str__(self):
        tup = self.delta_time, self.status, self.data, self.get_event_type
        result = 'delta_time = {}, status = {}, data = {}, event type: {}'.format(*tup)
        return Event.__str__(self) + result

    @property
    def get_event_type(self):
        return StatusBytes.midi[self.status & 240]


class SysExEvent(Event):
    """Class SysExEvent describes, obviously, midi system exclusive messages
    unlike to class Event  has a field length
    """
    def __init__(self, delta_time=0, status=240, data=[]):
        if status not in StatusBytes.sysex:
            raise StatusError(status)

        super().__init__(delta_time=delta_time, status=status, data=data[:])
        self.length = len(self.data)
        self.event = [
                        Event.variable_len(self.delta_time),
                        [self.status],
                        Event.variable_len(self.length),
                        self.data
                      ]

    def __str__(self):
        tup = self.delta_time, self.status, self.length, self.data, self.get_event_type
        result = 'delta_time = {}, status = {}, length = {},  data = {}, event type: {}'.format(*tup)
        return Event.__str__(self) + result

    @property
    def get_event_type(self):
        return StatusBytes.sysex[self.status]


class MetaEvent(Event):
    """Class MetaEvent describes, obviously, midi meta events
    unlike to class Event  has a fields length and event type
    """
    def __init__(self, event_type, delta_time=0, data=[]):
        if event_type not in StatusBytes.meta:
            raise MidiError(event_type, 'Wrong event type for Meta event')

        super().__init__(delta_time=delta_time, status=255, data=data[:])
        self.event_type = event_type
        self.length = len(self.data)
        self.event = [
                        Event.variable_len(self.delta_time),
                        [self.status],
                        [self.event_type],
                        Event.variable_len(self.length),
                        self.data
                        ]

    def __str__(self):
        tup = self.delta_time, self.status, self.event_type, self.length, self.data, self.get_event_type
        result = 'delta_time = {}, status = {}, event_type = {}, length = {},  data = {}, event type: {} '.format(*tup)
        return Event.__str__(self) + result

    @property
    def get_event_type(self):
        return StatusBytes.meta[self.event_type]


class Track:
    """Class Track describes midi track,
     in general class Track consists of Event's list and track header
    """
    def __init__(self, events=[], running_status_mode=True):
        """header - 'MTrk'
        events - list of events, for example [MidiEvent, MetaEvent,...]
        running status mode - default running status is one(True)
        length - data length
        bytes - bytes representation of events list
        """
        if not events:
            raise MidiError(events, 'Events list is empty')
        self.header = b'MTrk'
        self.events = events[:]
        self.running_status_mode = running_status_mode
        self.length, self.bytes = self.length_and_bytes()

    def to_hex(self):
        """Get bytes representation of track
        """
        header = self.header
        length = pack('>L', self.length)
        events = self.bytes
        return header + length + events

    def length_and_bytes(self):
        """Because of the variable length value, we can not specify the length of the track without converting
        events list to a byte string
        """
        if self.running_status_mode:
            byte_string = self.running_status()
        else:
            byte_string = b''.join(map(Event.to_hex, self.events))
        return len(byte_string), byte_string

    def running_status(self):
        """To save memory we can use a trick, calling 'running status', it means, that if several MidiEvent
        if several MidiEvent's with the same status byte are in progress, status byte required only for first event
        """
        byte_string = self.events[0].to_hex()   # get first event
        current_status = self.events[0].status  # get first event status
        for event in self.events[1:]:
            # does this Event is MidiEvent
            if current_status == event.status < 240:
                # Yes
                h = event.to_hex()
                delta_time = event.get_delta_time
                byte_string += delta_time + h[len(delta_time)+1:]
            else:
                # No
                byte_string += event.to_hex()
            # change current status
            current_status = event.status
        return byte_string

    @property
    def get_event(self):
        return self.events

    def __getitem__(self, item):
        return self.events[item]

    def __str__(self):
        header = 'MTrk length =  {}'.format(self.length) + '\n'
        events = '\n'.join(map(str, self.events))
        return header + events


class MidiFormat:
    """Class MidiFormat describes Standard Midi File,
    in general, MidiFormat consists of Tracks list and Header
    """
    def __init__(self, header, tracks=[]):
        """header - instance of class Header
        tracks - list of Tracks
        """
        if not header:
            raise MidiError(header, 'Header is empty')
        if not tracks:
            raise MidiError(tracks, 'Tracks list is empty')
        self.header = header
        self.tracks = tracks[:]

    def to_hex(self):
        """Get bytes representation of MidiFormat
        """
        header = self.header.to_hex()
        tracks = b''.join(map(Track.to_hex, self.tracks))
        return header + tracks

    def __getitem__(self, item):
        return self.tracks[item]

    def __str__(self):
        header = str(self.header) + '\n'
        track = '\n'.join(map(str, self.tracks))
        return header + track


class StatusBytes:
    """Enumerating of status bytes with corresponding event types
    """
    meta = {0: 'Sequence Number', 1: 'Text', 2: 'Copyright', 3: 'Sequence / Track Name', 4: 'Instrument Name',
            5: 'Lyric', 6: 'Marker', 7: 'Cue Point', 8: 'Program Name', 9: 'Device Name', 32: 'MIDI Channel Prefix',
            33: 'MIDI Port', 47: 'End of Track', 81: 'Tempo', 84: 'SMPTE Offset', 88: 'Time Signature',
            89: 'Key Signature', 127: 'Sequencer Specific Event'}
    sysex = {240: 'Single (complete) SysEx messages', 247: 'Escape sequences'}
    midi = {128: 'Note off', 144: 'Note on', 160: 'Key pressure', 176: 'Control change', 192: 'Program change',
            208: 'Channel pressure', 224: 'Pitch wheel change'}


# TODO midi exceptions class
if __name__ == '__main__':
    e = []
    for i in range(10):
        e.append(MidiEvent(1270000, 144, 9, [i, 127]))
        e.append(MidiEvent(127, 144, 9, [i, 0]))
        e.append((SysExEvent(127, 240, [0,1,1])))
    #e.append(MetaEvent(47, 0))
    print(len(e))
    t = Track(e, 1)
    print(t)
    print(t.to_hex())
    hdr = Header(0, 1, 96)
    smf = MidiFormat(hdr, [t])
    print(smf.to_hex())
    #print(MidiEvent(i, 144, 2, [60, 127]).get_event_type)
    f = open('second.mid', 'wb')
    f.write(smf.to_hex())
    f.close()


