# drc-fire

python implementation of js drc fire scripts

# set up

clone this repository to your local environment and cd into it.

```
(base) . > git clone https://github.com/jdilger/drc-fire.git
(base) . > cd drc-fire
```

# environment set up

if you are using conda set up a new environment or modify a working one to match
this has only been tested on python v 3.8 so I suggest using that

```
(base) ./drc-fire > conda create -n drc python=3.8
(base) ./drc-fire > conda activate drc
```

Next install the needed modules for gee and jupyter notebooks

```
(drc) ./drc-fire > conda install -c conda-forge earthengine-api jupyterlab
```

## optional - authenticate your EE account

If this is your first time using the ee python api you may need to authenticate you account. Runn the command below and follow the instructions to complete the ee set up.

```
(drc) ./drc-fire > earthengine authenticate
```

# exporting

Everything to export the 3 products can be found in the automated_fire_mapping.ipynb notebook.

Start a jupyter notebook and open the automated fire mapping notebook

```
(drc) ./drc-fire > jupyter notebook
```

Follow the steps in the notebook to export baseline, anomalies, or year products
