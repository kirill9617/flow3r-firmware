Programming
===========

The main programming interface and language for the flow3rbadge is Python. More
exactly, it's `Micropython <https://micropython.org/>`_, which is a fairly
sizeable subset of Python that can run on microcontrollers.

Good news: if you've ever used Micropython on an ESP32, then you probably
already have all the tools required to get started. However, while the tools to
program the badge might be the same as for stock Micropython on ESP32, our APIs
are quite different.

The :ref:`st3m` framework is the main Python codebase you'll be writing against.
Instead of using standard Micropython libraries like ``machine`` or low level
display drivers, you'll be writing applications that implement st3m classes like
:py:class:`Responder` or :py:class:`Application`.

But, enough intro for now, let's get started.

Accessing the badge
-------------------

When the badge runs (for example, when you see the main menu), you can connect
it to a PC and it should appear as a serial device. On Linux systems, this
device will be usually called ``/dev/ttyACM0``.

You can then use any terminal emulator program (like picocom, GNU screen, etc)
to access the badge's runtime logs. Even better, get `mpremote
<https://docs.micropython.org/en/latest/reference/mpremote.html>`_, as it has
extra features that make file transfer to Micropython a breeze.

After connecting your badge and making sure it runs:

::

	$ mpremote
	Connected to MicroPython at /dev/ttyACM0
	Use Ctrl-] or Ctrl-x to exit this shell
	[... logs here... ]

The badge will continue to run. Now, if you press Ctrl-C, you will interrupt the
firmware and break into a Python REPL (read-eval-print-loop) prompt:

::

	Traceback (most recent call last):
	  File "/flash/sys/main.py", line 254, in <module>
	  [... snip ...]
	KeyboardInterrupt: 
	MicroPython c48f94151-dirty on 1980-01-01; badge23 with ESP32S3
	Type "help()" for more information.
	>>> 

The badge's display will now switch to 'In REPL' to indicate that software
execution has been interrupted and that the badge is waiting for a command over
REPL.

Congratulations! You can now use your badge as a calculator:

::

	>>> 5 + 5
	10

But that's not super interesting. Let's try to turn on some LEDs:

::

	>>> import leds
	>>> leds.set_rgb(0, 255, 0, 0)
	>>> leds.update()

The LED right next to the USB connector should light up red. You can continue
experimenting with different APIs (like :py:mod:`leds`, :py:mod:`audio`, etc).

Transferring files over REPL
----------------------------

You can also access the filesystem over the same Micropython serial port:

::

	$ mpremote
	MicroPython c48f94151-dirty on 1980-01-01; badge23 with ESP32S3
	Type "help()" for more information.
	>>> import os
	>>> os.listdir('/')
	['flash']
	>>> os.listdir('/flash/sys')
	['main.py', 'st4m', '.sys-installed']
	>>> 

	$ mpremote ls :flash/sys
	ls :flash/sys
	           0 main.py
	           0 st4m
	           0 .sys-installed

.. _disk mode:

Disk Mode
---------

For larger file transfers (eg. images, sound samples, etc.) you can put the
badge into Disk Mode by selecting ``Settings -> Disk Mode`` in the badge's menu.

You can then select whether to mount the 10MiB internal flash or SD card (if
present) as a pendrive. The selected device will then appear as a pendrive on
your system, and will stay until it is ejected. The serial connection will
disconnect for the duration of the badge being in disk mode.

Disk Mode can also be enabled when the badge is in :ref:`Bootloader mode`.

Writing Applications
--------------------

TODO