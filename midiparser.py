from struct import unpack

from midilib.midifile import *


class MidiParser:
    """Class MidiParser convert bytes representation of Standard Midi file to class MidiFormat
    All you need to do is use read_all method
    Don't close a file yourself, read_all method do this for you
    """
    def __init__(self, file):
        """file - file object, such as open(filename, 'rb')
        """
        self.file = file

    def __read_header(self):
        """Read SMF header"""
        mthd = self.file.read(8)
        if mthd and mthd[:4] != b'MThd':
            file_format, ntracks, ppqn = unpack('>HHH', self.file.read(6))
            header = Header(file_format=file_format, ntracks=ntracks, ppqn=ppqn)
            return header
        raise ValueError("Wrong format of file")

    def __read_event(self, current_event):
        """Read MIDI Event"""
        # from variable bytes length quantity to delta time
        delta_time = self.__read_var_len()
        # get status byte, i.e. MIDI event type (MIDI event, SysEx event, Meta event)
        status = unpack('>B', self.file.read(1))[0]

        # check for running status (status < 128)
        if (current_event.status & 240) in StatusBytes.midi and status < 128:
            # if case of read_midi_event data read one byte more data
            data = [status] + self.__read_midi_event_data(current_event.status)[:-1]
            self.file.seek(-1, 1)
            chn = current_event.status & 15
            event = MidiEvent(delta_time=delta_time, status=current_event.status - chn, channel_number=chn, data=data)
            return event
        # not running status ...
        if status not in [240, 247, 255]:   # is it MIDI event
            data = self.__read_midi_event_data(status)
            chn = status & 15
            event = MidiEvent(delta_time=delta_time, status=status - chn, channel_number=chn, data=data)
        elif status == 255:     # is it Meta event
            event_type, length, data = self.__read_meta_event_data()
            event = MetaEvent(delta_time=delta_time, event_type=event_type, data=data)
        else:   # is it Sysex event
            length, data = self.__read_sysex_event_data()
            event = SysExEvent(delta_time=delta_time, status=status, data=data)
        return event

    def __read_midi_event_data(self, status):
        """Read data of mide event"""
        if 192 <= status <= 223:
            length = 1
        else:
            length = 2
        data = list(self.file.read(length))
        return data

    def __read_sysex_event_data(self):
        """Read data of SysEx event"""
        length = self.__read_var_len()
        data = list(self.file.read(length))
        return length, data

    def __read_meta_event_data(self):
        """Read data of Meta event"""
        event_type = unpack('>B', self.file.read(1))[0]
        length = self.__read_var_len()
        data = list(self.file.read(length))
        return event_type, length, data

    def __read_track(self):
        """Read track"""
        # read  track header
        hdr = self.file.read(8)
        if hdr:     # if some problems with header - raise error
            event = self.__read_event(MetaEvent(1, 0, 'Just Event'))
            events = [event]
            current_event = event
            # read while event is not End of Track event (Meta event with event type 0x2F)
            while not (isinstance(event, MetaEvent) and event.event_type == 47):
                event = self.__read_event(current_event)
                current_event = event
                events.append(event)
            track = Track(events)
            return track
        raise ValueError('Wrong format of file')

    def read_all(self):
        """Read all SMF data, if it is correct"""
        # read SMF header
        header = self.__read_header()
        tracks = []
        # read all tracks
        for cnt in range(header.ntracks):
            track = self.__read_track()
            tracks.append(track)
        # create a MidiFormat object
        file = MidiFormat(header=header, tracks=tracks)
        self.file.close()
        return file

    def __read_var_len(self):
        """Read variable bytes quantity, i.e. delta time of length"""
        byte = []
        for cnt in range(4):
            b = unpack('>B', self.file.read(1))[0]
            byte.append(b)
            if b <= 127:
                break
        return MidiParser.__variable_len(byte)

    @staticmethod
    def __variable_len(array):
        """Transform variable bytes quantity length to length"""
        output = 0
        for n in array:
            output = output << 7
            output |= n & 0x7f
        return output

# TODO checking for exceptions

