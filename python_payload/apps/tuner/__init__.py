from st3m.application import Application, ApplicationContext
from st3m.input import InputState
from st3m.goose import Optional
from st3m.ui.view import ViewManager
from ctx import Context
import audio
import sys_bl00mbox
import bl00mbox
import math
from bl00mbox import SignalInput,SignalOutput,ChannelMixer


# Assume this is an enum
ForceModes = ["AUTO", "FORCE_LINE_IN", "FORCE_LINE_OUT", "FORCE_MIC"]


STATE_TEXT: dict[int, str] = {
    audio.INPUT_SOURCE_AUTO: "auto",
    audio.INPUT_SOURCE_HEADSET_MIC: "headset mic",
    audio.INPUT_SOURCE_LINE_IN: "line in",
    audio.INPUT_SOURCE_ONBOARD_MIC: "onboard mic",
}

INPUT_GAIN: dict[int, float] = {
    audio.INPUT_SOURCE_NONE: 0,
    audio.INPUT_SOURCE_HEADSET_MIC: 1.0,
    audio.INPUT_SOURCE_LINE_IN: 5.0,
    audio.INPUT_SOURCE_ONBOARD_MIC: 10.0,
}

class Tuner(Application):
    def __init__(self, app_ctx: ApplicationContext) -> None:
        super().__init__(app_ctx)
        self.pitch = 0
        self._pressed=[]
        self._signals_in = {}
        self._signals_out = {}
        self._plugins = []
        self._active_plugins = []
        self._force_mode: str = "AUTO"
        self._mute = True
        self._source = None
        self.target_source = audio.INPUT_SOURCE_AUTO
        self._source_plugin = None
        
        self._blm = bl00mbox.Channel("demo")
        p = self._blm.new(bl00mbox.plugins.bl00mbox_line_in)
        p.signals.gain.mult = 5
        print (p.signals.gain)
        self._plugins.append(p)
        self._signals_in[p]=[]
        self._signals_out[p]=[p.signals.left] #,p.signals.right]
        p = self._blm.new(bl00mbox.plugins.filter)
        self._plugins.append(p)
        self._signals_in[p] = [p.signals.input]
        self._signals_out[p] = [p.signals.output]
        p = self._blm.new(bl00mbox.plugins.tuner,1024)
        self._plugins.append(p)
        self._signals_in[p] = [p.signals.input]
        self._signals_out[p] = [p.signals.output]
        p = self._blm.new(bl00mbox.plugins.osc)
        self._plugins.append(p)
        self._signals_in[p]=[]
        self._signals_out[p]=[p.signals.output]

    def on_enter(self, vm: Optional[ViewManager]) -> None:
        super().on_enter(vm)
        self._force_mode = "AUTO"


    def draw(self, ctx: Context) -> None:
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.font = ctx.get_font_name(8)

        ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()
        ctx.rgb(1, 1, 1)

        # top button
        ctx.move_to(105, 0)
        ctx.font_size = 15
        ctx.save()
        ctx.rotate((math.pi / 180) * 270)
        ctx.text(">")
        ctx.restore()

        ctx.move_to(0, -90)
        ctx.text("toggle passthrough")
        ctx.save()
        ctx.text_align = ctx.RIGHT
        ctx.move_to(90,-75)
        if self._plugins[0] in self._active_plugins:
            ctx.rgb(1,1,0)
        else:
            ctx.rgb(1,1,1)
        ctx.text("line_in");

        ctx.move_to(110,-20)
        if self._plugins[1] in self._active_plugins:
            ctx.rgb(0,1,0)
        else:
            ctx.rgb(1,1,1)
        ctx.text("filter");
        ctx.move_to(110,20)
        if self._plugins[2] in self._active_plugins:
            ctx.rgb(0,1,0)
        else:
            ctx.rgb(1,1,1)
        ctx.text("tuner");
        ctx.move_to(90,75)
        if self._plugins[3] in self._active_plugins:
            ctx.rgb(1,1,0)
        else:
            ctx.rgb(1,1,1)
        ctx.text("osc");
        ctx.move_to(0,-60)
        ctx.font_size = 10
        ctx.text_align = ctx.CENTER
        max_val = self._plugins[2].signals.max.value/32768
        if max_val > 0.7:
            ctx.rgb(0,1,0)
        else:
            ctx.rgb(1,0,0);
        ctx.text(str(max_val))
        ctx.move_to(0,-45)
        pitch_val = self._plugins[2].signals.pitch.value/10
        if pitch_val != 0:
            ctx.rgb(0,1,0)
            self.pitch = pitch_val
        else:
            ctx.rgb(1,0,0)
        ctx.text(str(self.pitch))

        ctx.move_to(0,-30)
        ctx.rgb(0,1,1)
        ctx.text(str(self._plugins[2].signals.line.value))
        ctx.restore()
        
        # middle text
        ctx.font_size = 25
        ctx.move_to(0, 0)
        ctx.save()
        if self._mute:
            # 0xff4500, red
            ctx.rgb(1, 0.41, 0)
        else:
            # 0x3cb043, green
            ctx.rgb(0.24, 0.69, 0.26)
        ctx.text("passthrough off" if self._mute else "passthrough on")
        ctx.restore()

        # bottom text
        ctx.move_to(0, 25)
        ctx.save()
        ctx.font_size = 15
        ctx.text(STATE_TEXT.get(self.target_source, ""))

        ctx.move_to(0, 40)
        if self.source_connected:
            # 0x3cb043, green
            ctx.rgb(0.24, 0.69, 0.26)
        else:
            # 0xff4500, red
            ctx.rgb(1, 0.41, 0)
        if self._mute:
            ctx.text("standby")
        elif self._force_mode == "AUTO":
            src = audio.input_engines_get_source()
            if src != audio.INPUT_SOURCE_NONE:
                ctx.text("connected to")
                ctx.move_to(0, 56)
                ctx.text(STATE_TEXT.get(src, ""))
            else:
                ctx.text("waiting...")
        elif self._force_mode == "FORCE_MIC":
            ctx.text("connected" if self.source_connected else "(headphones only)")
        else:
            ctx.text("connected" if self.source_connected else "waiting...")
        ctx.restore()

        # bottom button
        ctx.move_to(105, 0)
        ctx.font_size = 15
        ctx.save()
        ctx.rotate((math.pi / 180) * 90)
        ctx.text(">")
        ctx.restore()

        ctx.move_to(0, 90)
        ctx.text("next source")

    @property
    def source_connected(self):
        if self.source != audio.INPUT_SOURCE_NONE:
            return self.source == audio.input_engines_get_source()
        else:
            return False

    @property
    def source(self):
        if self._source is None:
            self._source = audio.input_engines_get_source()
        return self._source

    @source.setter
    def source(self, source):
        audio.input_engines_set_source(source)
        self._source = audio.input_engines_get_source()
        self._plugins[0].signals.gain.mult = INPUT_GAIN[self._source]


    def connect_to_out(self,sig):
        sys_bl00mbox.channel_connect_signal_to_output_mixer(sig._plugin.channel_num, sig._plugin.bud_num, sig._signal_num )

    def connect_out_to_in(self,src,dst):
        sys_bl00mbox.channel_connect_signal(
                dst._plugin.channel_num,
                dst._plugin.bud_num,
                dst._signal_num,
                src._plugin.bud_num,
                src._signal_num,
            )


    def discon_signal(self,sig):
        sys_bl00mbox.channel_disconnect_signal_tx(sig._plugin.channel_num, sig._plugin.bud_num, sig._signal_num)


    def on_pressed_0(self,ins,delta_ms,i)->None:
        self._mute = not self._mute

    def on_pressed_1(self,ins,delta_ms,i)->None:
        self.on_pressed_i(ins,delta_ms,i)

    def on_pressed_2(self,ins,delta_ms,i)->None:
        self.on_pressed_i(ins,delta_ms,i)

    def on_pressed_3(self,ins,delta_ms,i)->None:
        self.on_pressed_i(ins,delta_ms,i)

    def on_pressed_4(self,ins,delta_ms,i)->None:
        self.on_pressed_i(ins,delta_ms,i)

    def on_pressed_8(self,ins,delta_ms,i)->None:
        self._plugins[3].signals.pitch.freq+=10

    def on_pressed_6(self,ins,delta_ms,i)->None:
        self._plugins[3].signals.pitch.freq-=10

    def on_pressed_i(self,ins,delta_ms,i)->None:
        print('->',i)
        p = self._plugins[i-1]
        ap=self._active_plugins
        print('p:',p)
        print('active:',ap)
        if len(self._signals_in[p])==0:
            #source plugin
            if self._source_plugin is not None:
                for s in self._signals_out[self._source_plugin]:
                    self.discon_signal(s)

                ap.remove(self._source_plugin)
            if self._source_plugin == p:
                self._source_plugin = None
                #ap.remove(p)
                self._active_plugins=ap
                return

            self._source_plugin =p
            for s in self._signals_out[self._source_plugin]:
                if len(ap)==0:
                    self.connect_to_out(s)
                else:
                    for dst in self._signals_in[ap[0]]:
                        self.connect_out_to_in(s,dst)
            
            ap = [p]+ap
            self._active_plugins=ap
            return
        else:
            # passthrough
            if p not in ap:
                # disconnect previous plugin from OUT
                # and connect P`s IN
                if len(ap)>0:
                    for s in self._signals_out[ap[-1]]:
                        self.discon_signal(s)
                        for dst in self._signals_in[p]:
                            self.connect_out_to_in(s,dst)
                for s in self._signals_out[p]:
                    self.connect_to_out(s)
                ap.append(p)
                self._active_plugins=ap
                return
            else:
                #disconnect P`s OUT
                #and connect prev OUT to next IN
                idx = ap.index(p)
                for s in self._signals_out[p]:
                    self.discon_signal(s)
                if idx>0:
                    for s in self._signals_out[ap[idx-1]]:
                        if idx+1 == len(ap):
                            #P was last one
                            self.connect_to_out(s)
                        else:
                            for dst in self._signals_in[ap[idx+1]]:
                                self.connect_out_to_in(s,dst)
                ap.remove(p)
                self._active_plugins=ap
                return


                    

    def on_pressed_5(self,ins,delta_ms,i)->None:
        index = ForceModes.index(self._force_mode)
        index = (index + 1) % 4
        self._force_mode = ForceModes[index]


    def think(self, ins: InputState, delta_ms: int) -> None:
        super().think(ins, delta_ms)
        
        for i,petal in enumerate(ins.captouch.petals):
            if petal.pressed:
                if i not in self._pressed:
                    self._pressed.append(i)
                    handler = getattr(self,'on_pressed_'+str(i),None)
                    if handler is not None:
                        handler(ins,delta_ms,i)
                        print ('ap:')
                        for p in self._active_plugins:
                            print(p)
                        s = self._blm.mixer
                        print('blm:',self._blm,isinstance(s,SignalOutput),isinstance(s,SignalInput),isinstance(s,ChannelMixer))

            else:
                if i in self._pressed:
                    self._pressed.remove(i)
                    handler = getattr(self,'on_released_'+str(i),None)
                    if handler is not None:
                        handler(ins,delta_ms,i)
        
        '''
        '''

        if self._mute:
            self.source = audio.INPUT_SOURCE_NONE
        else:
            if self._force_mode == "FORCE_MIC":
                self.target_source = audio.INPUT_SOURCE_ONBOARD_MIC
            elif self._force_mode == "AUTO":
                self.target_source = audio.INPUT_SOURCE_AUTO
            elif self._force_mode == "FORCE_LINE_IN":
                self.target_source = audio.INPUT_SOURCE_LINE_IN
            elif self._force_mode == "FORCE_LINE_OUT":
                self.target_source = audio.INPUT_SOURCE_HEADSET_MIC
            self.source = self.target_source


# For running with `mpremote run`:
if __name__ == "__main__":
    import st3m.run

    st3m.run.run_app(Tuner)
