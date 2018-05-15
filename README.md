# geolasPy

## Setup
The program depends on python3. Additionally python3 development files have to be installed.

### Prerequisites

* ```sudo apt install python3 python3-dev python3-venv build-essential libgtk-3-dev libglu1-mesa-dev libnotify-dev libjpeg-dev libtiff5-dev libgstreamer-plugins-base1.0-dev libwebkit2gtk-4.0-dev```
* Create a virtual environment with ```pyvenv venv```.

#### SmarAct (Stage)
```sudo cp libmcscontrol/lib64/* /usr/lib```

#### AIOUSB (Shutter)

* ```sudo apt install libusb-1.0-0-dev cmake swig```
* ```git clone https://github.com/accesio/AIOUSB.git```
* ```cd AIOUSB/AIOUSB; mkdir build; cd build```
* ```cmake -DBUILD_PYTHON=ON -DBUILD_SAMPLES=OFF -DCMAKE_INSTALL_PREFIX=install ..```
* ```make; make install```
* ```cp install/lib/python2.7/* {geolas_DIR}/venv/lib/python3.5/site-packages```

### Installation
* Install the dependencies with ```venv/bin/pip install -r requirements.txt``` 