# main.py

from fire_module_2 import step2
from fire_module import step1
import ee

ee.Initialize()


# drc
test_geom = ee.FeatureCollection(
    "projects/sig-misc-ee/assets/drc_fire/test_areas/test_area")
DRC_border = ee.FeatureCollection(
    "projects/ee-karistenneson/assets/BurnedBiomass/DRC_Training/DRC_Border")
cover = ee.Image('projects/sig-ee/FIRE/DRC/DIAF_2000forest')
# Forests without dry forest
# Dry forest or open forest
covername = "Dry forest or open forest"
a = step1(2016, DRC_border, cover, covername)
# # # dag step 1. make baseline col, wait for export
# # prep_lc = a.prepare_script1()
# # a.export_image_collection(prep_lc,a.export_baseline_landcover,test=True,exportScale=500)

# anom_lc = a.script1()
# a.export_image_collection(
#     anom_lc, a.export_nbr_anomalies, test=False)
# pval_temporal
# default :pval_spatial
alpha = 0.05
pVal = 'pval_spatial'
b = step2(a, alpha, pVal)
out = b.main()
b.export_burn_yearly(
    out, test=False)

#   roc
# add this to params, possibly put this + roc's in their dictionaries
# DRC_border = ee.FeatureCollection("projects/ee-karistenneson/assets/BurnedBiomass/DRC_Training/DRC_Border")
# cover = ee.Image('projects/sig-ee/FIRE/DRC/DIAF_2000forest')

# covername = "Dry forest or open forest"
# a = step1(2016,DRC_border,cover,covername)
# # # dag step 1. make baseline col, wait for export
# # prep_lc = a.prepare_script1()
# # a.export_image_collection(prep_lc,a.export_baseline_landcover,test=True,exportScale=500)

# anom_lc = a.script1()
# a.export_image_collection(anom_lc,a.export_nbr_anomalies, test=False)
