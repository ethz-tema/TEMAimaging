# TEMAimaging

## Setup
The program depends on python3. Additionally, python3 development files have to be installed.

### Prerequisites

* ```sudo apt install python3 python3-dev python3-venv build-essential libgtk-3-dev libglu1-mesa-dev libnotify-dev libjpeg-dev libtiff5-dev libgstreamer-plugins-base1.0-dev libwebkit2gtk-4.0-dev```
* Create a virtual environment (e.g. `python3 -m venv .venv`).

#### SmarAct (Stage)
```sudo cp libmcscontrol/lib64/* /usr/lib```

#### AIOUSB (Shutter)

* ```sudo apt install libusb-1.0-0-dev cmake swig```
* ```git clone https://github.com/accesio/AIOUSB.git```
* ```cd AIOUSB/AIOUSB; mkdir build; cd build```
* ```cmake -DBUILD_PYTHON=ON -DBUILD_SAMPLES=OFF -DCMAKE_INSTALL_PREFIX=install ..```
* ```make; make install```
* ```cp install/lib/python2.7/* {tema_imaging_DIR}/venv/lib/python3.5/site-packages```

### Installation
* Install the software with `.venv/bin/pip install -e .`

## License

The source code is released under the [GNU General Public License v3](https://www.gnu.org/licenses/gpl-3.0.en.html).

Please cite the software as:
Neff, C.; Keresztes Schmidt, P.; Garofalo, P. S.; Schwarz, G.; Günther, D. **Capabilities of Automated LA-ICP-TOFMS Imaging of Geological Samples**. *J. Anal. At. Spectrom. 2020*, 10.1039.D0JA00238K. https://doi.org/10.1039/D0JA00238K