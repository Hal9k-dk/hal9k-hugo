---
title: "The Alphaclock"
date: 2026-11-22T12:05:00+01:00
type: posts
url: /alphaclock/
authors: ["Torsten Martinsen"]
categories: ["Projekter"]
tags: ["clock", "ESP32", "silly"]
image: /images/alphaclock-front.png
---

In December 2024, I stumbled across this meme showing an analogue clock with
the digits sorted alphabetically instead of numerically:

![Clock face with the digits arranged alphabetically](/images/alphaclock-clockface.jpg)

I immediately thought this would be a fun project and got hold of an IKEA
[PLUTTIS](https://www.ikea.com/gb/en/p/pluttis-wall-clock-black-10540847/).

My original thought was to reuse as much of the mechanism as possible. Since
the second and minute hands move normally, I planned to add a motor to control
just the hour hand. That turned out not to be so simple, so I started designing
a mechanism to control each clock hand with a dedicated stepper motor. This
means that the only parts of the original clock that survived are the case and
the clock hands.

Predictably, I went through a number of iterations before I had something
functional. The 10 mm diameter steppers I first tried were not quite strong
enough, so I replaced them with 20 mm ones. It also turned out that rubber
belts and 3D-printed pulleys introduced too much slippage to be reliable. The
final version uses store-bought plastic gear wheels and worm gears. Each gear
wheel is fastened to a 3D-printed wheel, which rotates inside a ball bearing.

I designed the parts using [build123d](https://build123d.readthedocs.io/en/latest/).
Here is what the part for the hour hand looks like:

![CAD model of the hour-hand mechanism](/images/alphaclock-hour.png)

Note the use of [crush ribs](https://www.marginallyclever.com/2020/09/have-you-heard-of-crush-ribs/),
which ensure a good fit of the ball bearing and the clock hand.

The small hole on the edge of the disc fits a magnet, which activates a [SS49E](https://prod-edam.honeywell.com/content/dam/honeywell-edam/sps/siot/ja/products/sensors/magnetic-sensors/linear-and-angle-sensor-ics/common/documents/sps-siot-ss39et-ss49e-ss59et-product-sheet-005850-3-en-ciid-50359.pdf) Hall sensor, used for homing. The position of the sensor does not coincide with any particular position of the corresponding hand, so I store the offset as an NVS setting.

For the software, I used my favourite microcontroller, the ESP32. Naturally,
the firmware uses SNTP to obtain the current time, and it also implements a web
page allowing manual control of the clock:

![Web interface for controlling the clock](/images/alphaclock-webui.png)

This is the initial homing sequence, followed by moving the hands to the current time:

<figure class="wp-block-video">
  <video controls playsinline src="/images/alphaclock-homing.mp4"></video>
  <figcaption>Homing sequence</figcaption>
</figure>

And here is the transition from one hour to another:

<figure class="wp-block-video">
  <video controls playsinline src="/images/alphaclock-hour.mp4"></video>
  <figcaption>Hour transition</figcaption>
</figure>

This is the finished assembly - the OLED display is useful for viewing the clock's IP address without having to connect a computer.

![Back view](/images/alphaclock-back.jpg)

Close-up view of the worm gear that drives the gear for one of the hands:

![Close-up of gears](/images/alphaclock-gears.jpg)

The hour mechanism has a second gear to reduce the overall depth of the clock:

![Hour mechanism](/images/alphaclock-hour-gear.jpg)

All the CAD files and software can be found at
[github.com/bullestock/alphaclock](https://github.com/bullestock/alphaclock/).

If you are wondering about the order of the digits, they are arranged according
to the Danish spelling of the numbers 1 through 12, and I opted to keep 12 at
the top.
