import ui
import time
import hardware
import math
import event

menu_stack = []
active_menu = None

class Menu():
    def __init__(self,name="menu",has_back=True):
        self.name=name
        self.items=[]
        self.__index = 0
        self.ui = ui.GroupRing(r=80)
        self.ui.element_center = ui.Text(self.name)
        self.icon = ui.Icon(label=name)
        self.angle = 0
        self.angle_step= 0.2
        if has_back:
            self.add(MenuItemBack())

    
    def __repr__(self):
        return "{} ({}): {}".format(self.name, self.__index, self.items)

    def add(self, item):
        self.items.append(item)
        self.ui.add(item.ui)
    
    def pop(self):
        self.items.pop()
        self.ui.children.pop()

    def start(self):
        print(self)
        active_menu = self
        render()

    def scroll(self, n=0):
        self.__index= (self.__index+n)%len(self.items)
        return self.items[self.__index]
    
    def rotate_by(self,angle):
        self.rotate_to(self.angle+angle)
    
    def rotate_to(self, angle):
        self.angle = angle%(math.pi*2)
        self.ui.angle_offset = self.angle
    
    def rotate_steps(self, steps=1):
        self.rotate_by(self.angle_step*steps)
        
    def _get_hovered_index(self):
        index = round(-self.angle/(math.pi*2)*len(self.items))
        i = index%len(self.items)
        return i

    def get_hovered_item(self):
        return self.items[self._get_hovered_index()]
    
    def _get_angle_for_index(self,index):
        return (math.pi*2/len(self.items)*(index)+self.angle)%(math.pi*2)

    def _get_topness_for_index(self,index):
        angle = self._get_angle_for_index(index)
        dist = min(angle,math.pi*2-angle)
        topness = 1-(dist/math.pi)
        return topness

    

    def draw(self):
        
        hovered_index = self._get_hovered_index()
        for i in range(len(self.items)):
            item = self.items[i]
            my_extra = abs(self._get_topness_for_index(i))*40
            
            if i == hovered_index:
                item.ui.has_highlight=True
                my_extra+=20
            else:
                item.ui.has_highlight=False
            item.ui.size=30+my_extra
        self.ui.draw()
    

class MenuItem():
    def __init__(self,name="item",action=None):
        self.name= name
        self.action= action
        self.ui = ui.Icon(label=name)

    def __repr__(self):
        return "item: {} (action: {})".format(self.name,"?")

    def enter(self,data={}):
        print("Enter MenuItem {}".format(self.name))
        if self.action:
            self.action(data)

class MenuItemApp(MenuItem):
    def __init__(self,app):
        super().__init__(name=app.title)
        self.target = app
    
    def enter(self,data={}):
        if self.target:
            self.target.run()

class MenuItemSubmenu(MenuItem):
    def __init__(self,submenu):
        super().__init__(name=submenu.name)
        self.ui = submenu.icon
        self.target = submenu
    
    def enter(self,data={}):
        print("Enter Submenu {}".format(self.target.name))
        menu_stack.append(active_menu)
        set_active_menu(self.target)
        
class MenuItemBack(MenuItem):
    def __init__(self):
        super().__init__(name="<-")
    
    def enter(self,data={}):
        menu_back()

class MenuItemControl(MenuItem):
    def __init__(self,name,control):
        super().__init__(name=name)
        self.control=control
        self.ui=control.ui

    def enter(self):
        print("menu enter")
        self.control.enter()

    def scroll(self,delta):
        self.control.scroll(delta)

def on_scroll(d):
    if active_menu is None:
        return

    if d["index"]==0:#right button
        hovered=active_menu.get_hovered_item()
        if hasattr(hovered, "scroll"):
            hovered.scroll(d["value"])

    else: #index=1, #left button
        if active_menu.angle_step<0.5:
            active_menu.angle_step+=0.025
        if d["value"] == -1:
            active_menu.rotate_steps(-1)
        elif d["value"] == 1:
            active_menu.rotate_steps(1)

    render()

def on_scroll_captouch(d):
    if active_menu is None:
        return
    if abs(d["radius"]) < 10000:
        return
    print(d["angle"])
    active_menu.rotate_to(d["angle"]+math.pi)
    render()

def on_release(d):
    if active_menu is None:
        return

    active_menu.angle_step = 0.2
    render()
    
def on_enter(d):
    if active_menu is None:
        
        #TODO this should not bee needed...
        event.the_engine.userloop=None
        menu_back()
        return

    if active_menu:
        active_menu.get_hovered_item().enter()
        render()
    else:
        return

    
event.Event(name="menu rotation button",group_id="menu",
    condition=lambda e: e["type"] =="button" and not e["change"] and abs(e["value"])==1,
    action=on_scroll, enabled=True
)

event.Event(name="menu rotation captouch",group_id="menu",
    condition=lambda e: e["type"] =="captouch" and not e["change"] and abs(e["value"])==1 and e["index"]==2,
    action=on_scroll_captouch, enabled=False
)

event.Event(name="menu rotation button release",group_id="menu",
    condition=lambda e: e["type"] =="button" and e["change"] and e["value"] ==0,
    action=on_release, enabled=True
)

event.Event(name="menu button enter",group_id="menu",
    condition=lambda e: e["type"] =="button" and e["change"] and e["from"] == 2,
    action=on_enter, enabled=True
)

def render():
    print (active_menu)
    if active_menu is None:
        return
    
    ui.the_ctx.rectangle(-120,-120,240,240).rgb(0,0,0).fill()
    print("before draw")
    active_menu.draw()
    #hardware.display_update()

def set_active_menu(menu):
    global active_menu
    active_menu = menu

def menu_disable():
    global active_menu
    if active_menu:
        menu_stack.append(active_menu)
        active_menu=None

def menu_back():
    print ("back")
    if not menu_stack:
        return

    previous = menu_stack.pop()

    set_active_menu(previous)
    #ui.the_ctx = hardware.reset_ctx()
    print("almost")
    render()
    print("rendered")