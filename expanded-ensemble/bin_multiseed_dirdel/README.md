# Details

## Requirements

* Requires addwlmod branch of gromacs to be installed on the HPC
* Requires pymbar package to be installed on the HPC as well
* These required packages are installed and shared on Supermic. In my experience, 
Supermic has had shortest queue times. Might be best to start with the same.

## EnTK, Radical Pilot Installation

* Please see the instructions at ```http://radicalentk-06.readthedocs.io/en/arch-v0.6/install.html```.
* Note: For the current version, you will have to install RabbitMQ. The above link provides two methods in which
you can install RabbitMQ.


## Setting up access to HPCs

Currently, all packages and permissions are setup for SuperMIC. We will start 
with SuperMIC.

[Supermic](http://www.hpc.lsu.edu/resources/hpc/system.php?system=SuperMIC)
require GSISSH access. Instructions to setup gsissh access for Ubuntu can be 
found [here](https://github.com/vivek-bala/docs/blob/master/misc/gsissh_setup_stampede_ubuntu_xenial.sh/).
Please note that this has been tested only for xenial and trusty (for trusty, 
simple replace 'xenial' with 'trusty' in all commands). Even then, there might 
be some additional steps to setup gsissh correctly for your system. Happy to 
help!


## Executing the expanded ensemble scripts

Firstly, clone the current repository

```
git clone git@github.com:radical-experiments/adaptive-bms-experiments.git
cd adaptive-bms-experiments/expanded-ensemble
```

Next, you need to set a few environment variables:
```
export RADICAL_ENTK_VERBOSE=info
export RADICAL_PILOT_DBURL="mongo db url"
export RP_ENABLE_OLD_DEFINES=True
```

* Note: One additional edit to  be made due to changes in python on SuperMIC (not required after the next
RP release):
Change line 722 of ```$VE/lib/python2.7/site-packages/radical/pilot/configs/resource_xsede.json```($VE points to your 
virtualenv) from ```module load python``` to ```module load python/2.7.7-anaconda```.


The ```runme.py``` script contains the information about the application 
execution workflow and the associated data movement. Please take a look at all 
the comments to understand the various sections.

Execution command: 
```
python runme.py
```


## Note

* Hopefully not, but there might be lingering permission issues which will get 
detected once other users start running the code.
* The up-to-date alchemical analysis script is automatically downloaded from the
MobleyLab repository and used.
