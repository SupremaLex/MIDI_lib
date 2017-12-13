from .midi_event import MidiEvent
from .meta_event import MetaEvent
from .header import Header
from .track import Track
from .midifile import StandardMIDIFile


def generate_note_table():
        notes_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        midi_notes_table = {notes_names[i % 12] + str(i // 12): i for i in range(128)}
        return midi_notes_table


def play_notes(notes):
    table = generate_note_table()
    e = [MetaEvent(89, data=[2, 7, 0])]
    for n in notes:
        for note in n:
            e.append(MidiEvent(0, 144, 0, [table[note], 127]))
            e.append(MidiEvent(127, 144, 0, [table[note], 0]))
    e.append(MetaEvent(47, 0))
    t = Track(e, 1)
    hdr = Header(0, 1, 120)
    smf = StandardMIDIFile(hdr, [t])
    print(smf.to_hex())
    f = open('wav2midi.mid', 'wb')
    f.write(smf.to_hex())
    f.close()
