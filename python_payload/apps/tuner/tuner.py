import audio
import bl00mbox
import time

audio.input_engines_set_source(audio.INPUT_SOURCE_AUTO)
blm = bl00mbox.Channel("demo")
l_in = blm.new(bl00mbox.plugins.bl00mbox_line_in)
t = blm.new(bl00mbox.plugins.tuner,1024)

l_in.signals.left = t.signals.input
t.signals.output = blm.mixer

while True:
    p = t.signals.pitch
    # if p>0:
        # print(p)
    #print(t.signals.max)
    time.sleep(1)
