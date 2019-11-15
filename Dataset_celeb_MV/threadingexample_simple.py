import io
import threading
import time
import os
import subprocess

from kivy.config import Config
Config.set('graphics', 'width', '1920')
Config.set('graphics', 'height', '1080')

from kivy.app import App
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.factory import Factory
from kivy.animation import Animation
from kivy.clock import Clock, mainthread
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

#Import AI face detection
from FaceDetector import FaceDetector

#Flyer generation tools
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black, white

Builder.load_string("""
<AnimWidget@Widget>:
    canvas:
        Color:
            rgba: 0.15, 0.6, 0.32, 1
        Rectangle:
            pos: self.pos
            size: self.size
    size_hint: None, None
    size: 640, 30

<RootWidget>:
    canvas.before:
        Rectangle:
            pos: self.pos
            size: self.size
            source: 'assets/background_new.png'

    cameraObject:cameraObject
    yourDatabaseImage:yourDatabaseImage
    yourLookalikeImage:yourLookalikeImage
    anim_box:anim_box
    bigRedButtonL:bigRedButtonL
    bigRedButtonR:bigRedButtonR
    selfLabel:selfLabel
    lookalikeLabel:lookalikeLabel
    congratulationsLabel_top:congratulationsLabel_top
    congratulationsLabel_bottom:congratulationsLabel_bottom

    BoxLayout:
        orientation: 'vertical'
        width: "640px"
        height: "510px"
        size_hint: None, None
        pos_hint: {'center_x': .5, 'center_y': .5}
        Camera:
            id: cameraObject
            resolution: (640, 480)
            play: True
            size_hint: None, None
            height: "480px"
            width: "640px"
        AnchorLayout:
            id: anim_box

    AsyncImage:
        id: yourDatabaseImage
        pos_hint: {'center_x': 0.35, 'center_y': 0.5}
        size_hint: None, None
        width: "640px"
        height: "480px"
        allow_stretch: True
        keep_ratio: True
        opacity: 0

    AsyncImage:
        id: yourLookalikeImage
        pos_hint: {'center_x': 0.65, 'center_y': 0.5}
        size_hint: None, None
        width: "640px"
        height: "480px"
        allow_stretch: True
        keep_ratio: True
        opacity: 0

    AsyncImage:
        id: bigRedButtonL
        pos_hint: {'center_x': 0.20, 'center_y': 0.514}
        size_hint: None, None
        width: "640px"
        height: "480px"
        allow_stretch: True
        keep_ratio: True
        opacity: 100
        source: 'assets/giphy.gif'

    AsyncImage:
        id: bigRedButtonR
        pos_hint: {'center_x': 0.80, 'center_y': 0.514}
        size_hint: None, None
        width: "640px"
        height: "480px"
        allow_stretch: True
        keep_ratio: True
        opacity: 100
        source: 'assets/giphy.gif'

    Label:
        id: selfLabel
        pos_hint: {'center_x': 0.35, 'center_y': 0.26}
        size_hint: None, None
        width: "640px"
        height: "480px"
        opacity: 0
        markup: True

    Label:
        id: lookalikeLabel
        pos_hint: {'center_x': 0.65, 'center_y': 0.26}
        size_hint: None, None
        width: "640px"
        height: "480px"
        opacity: 0
        markup: True

    Label:
        id: congratulationsLabel_top
        pos_hint: {'center_x': 0.5, 'center_y': 0.825}
        size_hint: None, None
        width: "640px"
        height: "480px"
        opacity: 0
        markup: True

    Label:
        id: congratulationsLabel_bottom
        pos_hint: {'center_x': 0.5, 'center_y': 0.775}
        size_hint: None, None
        width: "640px"
        height: "480px"
        opacity: 0
        markup: True

""")

class RootWidget(FloatLayout):
    def __init__(self, **kwargs):
        super(RootWidget, self).__init__(**kwargs)
        Window.bind(on_key_down=self._on_keyboard_down)

    in_progress=0
    #Variable to indicate the booth is already busy, so ignore more button presses

    stop = threading.Event()

    def start_second_thread(self):
        self.in_progress=1
        imageXY = self.cameraObject.size
        image = self.cameraObject.export_as_image()
        data = io.BytesIO() 
        image.save(data, fmt="png")

        threading.Thread(target=self.second_thread, args=(data, imageXY),).start()

    def second_thread(self, data, imageXY):
        # Popen immediately continues running, call waits until speaking is finished
        #subprocess.Popen(["espeak", "-v", "en+f3", "-k", "5", "-s", "180", text])
        #subprocess.call(["espeak", "-v", "en+f3", "-k", "5", "-s", "180", text])
        
        # Get the time and save a photo
        timestr = time.strftime("%Y%m%d_%H%M%S")
        saveStr = "IMG_{}.png".format(timestr)
        with open(saveStr, 'wb') as f:
            f.write(data.getvalue())
        
        Clock.schedule_once(self.disable_gifs, 0)

        #Start the scanner bar to indicate activity
        Clock.schedule_once(self.start_scanner_bar, 0)
       
        #Init RoboVoice
        text="You touched my button! Let's see if I can find you!"
        # subprocess.call(["espeak", "-v", "en+f3", "-k", "5", "-s", "160", text])
        
        #Go and find faces
        try:
            face_distances, lookalike_index_self, lookalike_image_path_self, lookalike_index_celeb, lookalike_image_path_celeb = face_detector.get_lookalike(os.getcwd() + "/" + saveStr, imageXY)
        except:
            text="Are you sure you are in front of my camera? shall we try again?"
            # subprocess.Popen(["espeak", "-v", "en+f3", "-k", "5", "-s", "160", text])
            self.remove_scanner_bar()
            self.reset_booth()
            return None

        #(!)
        #Before we do anything else - we start printing right away. Let's start an extra thread to protect the booth against external process crashes
        #Note that this doesn't prevent stopping the current thread - so multiple print jobs could accrue if printing is too slow.
        threading.Thread(target=self.third_thread_printing, args=(lookalike_image_path_self, lookalike_image_path_celeb, timestr, lookalike_index_self, lookalike_index_celeb),).start()

        #Found a face!
        text="You sure look great today! Let's see how smart I am..."
        #subprocess.call(["espeak", "-v", "en+f3", "-k", "5", "-s", "160", text])

        time.sleep(1)

        text="Doing what I do isn't easy you know."
        #subprocess.call(["espeak", "-v", "en+f3", "-k", "5", "-s", "160", text])

        time.sleep(2)

        if lookalike_index_self == -1:
            text="Nice to meet you! Hello colleague."
        else:
            text="Nice to meet you! Hello " + face_detector.input_dataset['GivenName'][lookalike_index_self] + ' ' + face_detector.input_dataset['Surname'][lookalike_index_self]
        #subprocess.Popen(["espeak", "-v", "en+f3", "-k", "5", "-s", "160", text])
        
        #Stop the scanner bar. Do UI updates in the main thread by using a decorated function.
        #Since we don't need animations here, no need to schedule this on the clock.
        #self.anim_box.opacity=0
        self.remove_scanner_bar()

        #Start camera fade animation
        Clock.schedule_once(self.start_camera_fade, 0)

        #Start showing pictures and set the labels
        if lookalike_index_self == -1:
            selfLabel="Unknown Colleague"
        else:
            selfLabel=face_detector.input_dataset['GivenName'][lookalike_index_self] + ' ' + face_detector.input_dataset['Surname'][lookalike_index_self]

        self.yourDatabaseImage.source=lookalike_image_path_self
        self.selfLabel.text = "[size=32]"+selfLabel+"[/size]"
        self.yourLookalikeImage.source=lookalike_image_path_celeb
        self.lookalikeLabel.text = "[size=32]"+face_detector.input_dataset_celeb['GivenName'][lookalike_index_celeb] + ' ' + face_detector.input_dataset_celeb['Surname'][lookalike_index_celeb]+"[/size]"

        #Update and animate the UI to show your database image
        time.sleep(2)
        Clock.schedule_once(self.show_database_image, 0)

        time.sleep(3)
        #We found your lookalike!
        text="I have found a colleague who looks just like you!"
        #subprocess.call(["espeak", "-v", "en+f3", "-k", "5", "-s", "160", text])

        Clock.schedule_once(self.show_lookalike_image, 0)

        self.congratulationsLabel_top.text = "[size=50]Congratulations, your Celebrity look-a-like is "+face_detector.input_dataset_celeb['GivenName'][lookalike_index_celeb] + ' ' + face_detector.input_dataset_celeb['Surname'][lookalike_index_celeb]+" :)."+"[/size]"
        self.congratulationsLabel_bottom.text = "[size=50]Let's meet for a cup of coffee!"+"[/size]"

        text="Do you already know " + face_detector.input_dataset_celeb['GivenName'][lookalike_index_celeb] + ' ' + face_detector.input_dataset_celeb['Surname'][lookalike_index_celeb] + '?'
        # subprocess.call(["espeak", "-v", "en+f3", "-k", "5", "-s", "160", text])

        time.sleep(0.8)
        if lookalike_index_self == -1:
            text="If you don't know eachother, have you considered coffee or tea? Hot drinks help to break the ice."
        else:
            text="If you don't know eachother, have you considered coffee or tea? Hot drinks help to break the ice " + face_detector.input_dataset['GivenName'][lookalike_index_self] + '.'
        # subprocess.call(["espeak", "-v", "en+f3", "-k", "5", "-s", "160", text])

        time.sleep(1)
        text="Well, it was fun, don't forget your flyer!"
        # subprocess.call(["espeak", "-v", "en+f3", "-k", "5", "-s", "160", text])

        time.sleep(10)
        text="Time for me to go back to work!"
        # subprocess.call(["espeak", "-v", "en+f3", "-k", "5", "-s", "160", text])

        #Finally we reset the booth for the next person
        time.sleep(1)
        self.reset_booth()

    def third_thread_printing(self, lookalike_image_path_self, lookalike_image_path_celeb, timestr, lookalike_index_self, lookalike_index_celeb):
        # lookalike_image_path_self
        im1 = lookalike_image_path_self
        # lookalike_image_path_similar
        im2 = lookalike_image_path_celeb

        #Start showing pictures and set the labels
        if lookalike_index_self == -1:
            selfLabel="Unknown Colleague"
        else:
            selfLabel=face_detector.input_dataset['GivenName'][lookalike_index_self] + ' ' + face_detector.input_dataset['Surname'][lookalike_index_self]

        c = canvas.Canvas(selfLabel+timestr+".pdf")
        c.setFillColor(black)
        c.rect(0, 0, 1000, 1000, fill=1)

        c.translate(inch,inch)
        c.drawImage("./assets/Lookalike booth printout.png", -75, -75, 8.31*inch, 11.8*inch, anchor='c')
        c.drawImage(im1, 0, 400, None, None)
        c.drawImage(im2, 250, 400, None, None)

        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 12)
        # your_photo = "You are looking fabulous!"
        # lookalike = "Your lookalike!"
        # c.drawString(35, 375, your_photo)
        # c.drawString(310, 375, lookalike)

        name_1 = selfLabel
        name_2 = face_detector.input_dataset_celeb['GivenName'][lookalike_index_celeb] + ' ' + face_detector.input_dataset_celeb['Surname'][lookalike_index_celeb]
        c.drawString(45, 375, name_1)
        c.drawString(320, 375, name_2)

        #face_detector.input_dataset['GivenName'][lookalike_index_self]
        c.showPage()
        c.save()

    #DatabaseImage UI controllers
    def show_database_image(self, *args):
        anim = Animation(opacity=100, duration=1)
        anim.start(self.yourDatabaseImage)
        self.selfLabel.opacity=100

    def show_lookalike_image(self, *args):
        anim = Animation(opacity=100, duration=1)
        anim.start(self.yourLookalikeImage)
        self.lookalikeLabel.opacity=100
        self.congratulationsLabel_top.opacity=100
        self.congratulationsLabel_bottom.opacity=100

    #Scanner Bar
    def start_scanner_bar(self, *args):
        # Create and add a new widget.
        self.anim_bar = Factory.AnimWidget()
        self.anim_box.add_widget(self.anim_bar)

        # Animate the added widget.
        anim = Animation(opacity=0.3, width=100, duration=0.6)
        anim += Animation(opacity=1, width=640, duration=0.8)
        anim.repeat = True
        anim.start(self.anim_bar)

    #Scanner Bar
    def disable_gifs(self, *args):
        self.bigRedButtonL.opacity=0
        self.bigRedButtonR.opacity=0

    @mainthread
    def remove_scanner_bar(self):
        self.anim_box.remove_widget(self.anim_bar)

    #Camera UI controllers
    def start_camera_fade(self, *args):
        animcam = Animation(opacity=0, duration=1)
        animcam.start(self.cameraObject)
    
    #Booth reset control
    @mainthread
    def reset_booth(self):
        self.yourDatabaseImage.opacity=0
        self.yourLookalikeImage.opacity=0
        self.cameraObject.opacity=100
        self.bigRedButtonL.opacity=100
        self.bigRedButtonR.opacity=100
        self.selfLabel.opacity=0
        self.lookalikeLabel.opacity=0
        self.congratulationsLabel_top.opacity=0
        self.congratulationsLabel_bottom.opacity=0
        self.in_progress=0


    #Execute keyboard events
    def _on_keyboard_down(self, instance, keyboard, keycode, text, modifiers):
        print('The key', keycode, 'have been pressed')
        print(' - text is %r' % text)
        print(' - modifiers are %r' % modifiers)
        if 'ctrl' in modifiers and 'q' in text:
            print("Exiting based on keyboard!")
            exit()

        if (keycode==40 and self.in_progress==0):
            #(!)Make the booth take a picture using the keyboard...
            print("BUTTONS! GO!")
            self.start_second_thread()

        # Return True to accept the key. Otherwise, it will be used by
        # the system.
        return True

class LookALikeBoothApp(App):

    def on_stop(self):
        # The Kivy event loop is about to stop, set a stop signal;
        # otherwise the app window will close, but the Python process will
        # keep running until all secondary threads exit.
        self.root.stop.set()

    def build(self):
        return RootWidget()

if __name__ == '__main__':
    #initialize the FaceDetector by calculating face encodings for all available pictures
    face_detector = FaceDetector(inputFolder="/input/", inputFolder_celeb="/test_celeb/")
    face_detector.get_face_encodings()
    LookALikeBoothApp().run()
