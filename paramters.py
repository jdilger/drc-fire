import ee
# // Specify start and end years for all analyses
# // This method requires at least a 4-year time-span. 
analysisYear = 2016

# // Specify the  number of years to include in the baseline statistics calculations
baselineLength = 3

# // Update the startJulian and endJulian ables to indicate your seasonal 
# // constraints. This supports wrapping for tropics and southern hemisphere.
# // startJulian: Starting Julian date 
# // endJulian: Ending Julian date
startJulian = 1
endJulian = 365

# // Specify the number of days in the analysis period - based on Landsat frequency (16 or 32)
analysisPeriod = 32

# // Step 4: Specify the analysis methods parameters 

# // Set the ecological regions to use for Z-score calculation 
groups = ee.Image("projects/sig-ee/FIRE/DRC/eco_regions")

# // Index to base z-score analysis on
# // It is recommended to use the Normalized Burn Ration (NBR)
indexName = 'NBR'

# // Paramaters and functions for z-test
analysisScale = 250 #//Scale for zonal reduction- 250 works well
analysisPixels = 1e10 #//Max pixels for zonal reduction
tileScale = 8

# // Step 5: Setting the export parameters.

# // Specify the desired coordinate reference system (CRS) used when exporting the map(s). 
# // Example settings include 4326 (WGS84) or 32734 (UTM projection for DRC). 
crs = 'EPSG:32734'
exportScale = 30 

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # ////////////////////////////////////////////////////////////////////////////////////
#// (Optional) Advanced Settings: 
#// How to adjust the parameters for Landsat imagery processing.
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # ////////////////////////////////////////////////////////////////////////////////////

# // The following parameters are used by the GetImagesLib module for processing Landsat imagery. 
# // Note that we do not use image composites in z-score analysis.
# 
# // Choose Top of Atmospheric (TOA) or Surface Reflectance (SR) 
# // Specify TOA or SR
# // Current implementation does not support Fmask for TOA
toaOrSR = 'SR'

# // Choose whether to include Landat 7
# // Generally only included when data are limited
includeSLCOffL7 = False

# // Whether to defringe L5
# // Landsat 5 data has fringes on the edges that can introduce anomalies into 
# // the analysis.  This method removes them, but is somewhat computationally expensive
defringeL5 = False

# // Choose cloud/cloud shadow masking method
# // Choices are using a Z-score (ZscoreApproach) or FMask approach (FmaskApproach) which 
# // adjust a series of booleans for cloudScore, TDOM, and elements of Fmask.
# // The Fmask approach includes masking clouds, cloud shadows, and snow -snow masking is
# // turned off for this example.Fmask masking options will run fastest since they're precomputed.
# // The Z-score approach uses CloudScore and TDOM. CloudScore runs pretty quickly, but 
# // does look at the time series to find areas that always have a high cloudScore to 
# // reduce comission errors- this takes some time and needs a longer time series
# // (>5 years or so). TDOM also looks at the time series and will need a longer time series

# // Options: ZscoreApproach, FmaskApproach
maskingMethod = 'FmaskApproach'


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # ////////////////////////////////////////////////////////////////////////////////////
# // Step 6a. if you have chosen the Zscore approach, there are a number of parameters
# // that can be adjusted to fine tune the cloud and cloud shadow masking. 
# // These parameters can be set in the lines below.

# // Cloud and cloud shadow masking parameters.
# // If cloudScoreTDOM is chosen cloudScoreThresh: 
# // If using the cloudScoreTDOMShift method-Threshold for cloud 
# // masking (lower number masks more clouds.  Between 10 and 30 generally works best)
cloudScoreThresh = 20

# // Percentile of cloud score to pull from time series to represent a minimum for 
# // the cloud score over time for a given pixel. Reduces comission errors over 
# // cool bright surfaces. Generally between 5 and 10 works well. 0 generally is a
# // bit noisy
cloudScorePctl = 10 

# // zScoreThresh: Threshold for cloud shadow masking- lower number masks out 
# // less. Between -0.8 and -1.2 generally works well.
# // Note that this is for cloud and shadow masking not the z-score analysis
zScoreThresh = -1

# // shadowSumThresh: Sum of IR bands to include as shadows within TDOM and the 
# // shadow shift method (lower number masks out less)
shadowSumThresh = 0.35

# // contractPixels: The radius of the number of pixels to contract (negative 
# // buffer) clouds and cloud shadows by. Intended to eliminate smaller cloud 
# // patches that are likely errors
# // (1.5 results in a -1 pixel buffer)(0.5 results in a -0 pixel buffer)
# // (1.5 or 2.5 generally is sufficient)
contractPixels = 1.5 

# // dilatePixels: The radius of the number of pixels to dilate (buffer) clouds 
# // and cloud shadows by. Intended to include edges of clouds/cloud shadows 
# // that are often missed
# // (1.5 results in a 1 pixel buffer)(0.5 results in a 0 pixel buffer)
# // (2.5 or 3.5 generally is sufficient)
dilatePixels = 2.5
# // correctIllumination: Choose if you want to correct the illumination using
# // Sun-Canopy-Sensor+C correction. Additionally, choose the scale at which the
# // correction is calculated in meters.
correctIllumination = False
correctScale = 250


# Cloud masking approach controled by masking method no need to alter here
# these should be in paramters, if not already...
applyZscoreApproach = False,
appplyFmaskApproach= False
applyCloudScore = False
applyTDOM = False
applyFmaskCloudMask = False
applyFmaskCloudShadowMask = False
applyFmaskSnowMask = False