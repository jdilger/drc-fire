import ee
ee.Initialize()
import imgLib
import config as c
from paramters import *


# input objects
test_geom = ee.FeatureCollection("projects/sig-misc-ee/assets/drc_fire/test_areas/test_area")
DRC = ee.FeatureCollection("projects/ee-karistenneson/assets/BurnedBiomass/DRC_Training/DRCAdminBndry")
ecoRegions = ee.FeatureCollection("projects/ee-karistenneson/assets/BurnedBiomass/DRC_Training/ecoRegions_DRC")
DRC_border = ee.FeatureCollection("projects/ee-karistenneson/assets/BurnedBiomass/DRC_Training/DRC_Border")

print(c.coverDict)

# //Step 2: Choose a cover class in which to collect fire data. 
# // The land cover map is for 2000.
# // Cover classes are in this order:
# // Value, Label, Abbreviation
# // "1", "Dense humid forest on dry land", DHF
# // "2" ,"Dense moist forest on hydromorphic soil", DMF
# // "3" ,"Secondary forest", SNDF
# // "4" ,"Dry forest or open forest", DRYF
# // "5" ,"Savannah", SAV
# // "6" ,"Cultures and regeneration of abandoned crops", REGN
# // "7" ,"Water zone", WATER
# // "8" ,"Agglomeration", AGGL
# // "9" ,"Other", OTHER
# // "1,2,3" ,"Forests without dry forest", FOREST
# //Chose a cover class to filter to for fire detection:
coverName = "Forests without dry forest"
coverDictionary = c.coverDict
coverType = coverDictionary[coverName]['value']
exportPathRoot = coverDictionary[coverName].get('exportPath', c.defaultExportPath)


# function imports?
geometry = test_geom
cover = ee.Image('projects/sig-ee/FIRE/DRC/DIAF_2000forest')

# move preping stuff to another script
def prepare_dates(startJulian, endJulian):


	if (startJulian > endJulian): endJulian = endJulian + 365
	startDate = ee.Date.fromYMD(analysisYear-baselineLength,1,1).advance(startJulian-1,'day')
	endDate = ee.Date.fromYMD(analysisYear,1,1).advance(endJulian-1,'day')

	return startDate, endDate


startDate, endDate = prepare_dates(startJulian, endJulian)


# masking logic
def prepare_masking(maskingMethod):
	global appplyFmaskApproach
	global applyZscoreApproach

	maskingMethod = maskingMethod.lower()
	if (maskingMethod == 'fmaskapproach'):
		print('FMask masking')
		appplyFmaskApproach = True
	elif (maskingMethod == 'zscoreapproach'):
		print('Zscore masking')
		applyZscoreApproach = True
	else: 
		print('WARNING: not using cloud/cloud shadow masking')


def apply_masking_params():


	global applyCloudScore
	global applyTDOM
	global applyFmaskCloudMask
	global applyFmaskCloudShadowMask
	global applyFmaskSnowMask

	if (applyZscoreApproach):
		applyCloudScore = True
		applyTDOM = True
	
	if (appplyFmaskApproach):
		applyFmaskCloudMask = True
		applyFmaskCloudShadowMask = True
		applyFmaskSnowMask = False

	if(toaOrSR == 'TOA'):
		applyFmaskCloudMask = False
		applyFmaskCloudShadowMask = False
		applyFmaskSnowMask = False
# todo: add tests for prepar_masking, apply_masking_params
# todo: cloud shadow mask is included in imgLib in same step as cloud mask(fmask)


prepare_masking('fmaskapproach')


print(applyCloudScore, applyTDOM, applyFmaskCloudMask, applyFmaskCloudShadowMask, applyFmaskSnowMask)


apply_masking_params()

print(applyCloudScore, applyTDOM, applyFmaskCloudMask, applyFmaskCloudShadowMask, applyFmaskSnowMask)

def ND_nir_swir2(img):
	img = img.addBands(img.normalizedDifference(['nir','swir2']).rename(['NBR']))  # NBR, MNDVI
	return img


# todo:set all env stuff when deciding in other functions
env = imgLib.landsat.env()
env.maskSR = 'test'
env.shadowMask = applyTDOM
env.cloudMask = applyCloudScore
ls = imgLib.landsat.functions(env)
# todo: set up so get imagery from full analysis period
ls = ls.getLandsat(geometry,analysisYear - baselineLength, analysisYear).map(ND_nir_swir2)
print(ls.size().getInfo())

dummyImage = ee.Image(ls.first())
def collectionToMeanStdDev(collection,groups):
	'''globals this needs to run: # geometry,analysisScale,crs,tileScale

	Args:
		collection ([type]): [description]
		groups ([type]): [description]

	Returns:
		[type]: [description]
	'''
	ic = collection
	# //Reduce the collection
	icMean = ic.mean()
	icStdDev = ic.reduce(ee.Reducer.stdDev())

	icSum = ic.sum().addBands(groups.rename('groups'))
	icCount = ic.count().addBands(groups.rename('groups'))

	
	# //Get the area reductions
	popN = ee.List(icCount.reduceRegion(ee.Reducer.sum().group(1), geometry, analysisScale, crs, None, True, 1e10, tileScale).get('groups'))
	popSum= ee.List(icSum.reduceRegion(ee.Reducer.sum().group(1), geometry, analysisScale, crs, None, True, 1e10, tileScale).get('groups'))

	# //Parse out the group codes
	groupCodes = popN.map(lambda g: ee.Dictionary(g).get('group'))
	

	# //Extract the N and sums
	popN = popN.map(lambda g: ee.Dictionary(g).get('sum') )
	popSum = popSum.map(lambda g: ee.Dictionary(g).get('sum') )

	# //Zip the N and sum for mean computation
	nSumZipped = ee.List(popSum).zip(popN)


	# //Compute means
	means = nSumZipped.map(lambda l : ee.Number(ee.List(l).get(0)).divide(ee.List(l).get(1)))

	# //Wrapper function to convert statList back to raster
	def statsToRaster(statList, groupCodeList, groupImage):

		def statsBtGroups(code):
			stat = ee.Number(statList.get(code))
		
			groupCode = ee.Number(groupCodeList.get(code))
			
			out = groupImage.eq(groupCode)
			out = out.updateMask(out)
			out = out.multiply(stat).rename(['stat']).addBands(out.multiply(groups).rename(['groups']))
			return out.float()

		statsByGroup = ee.List.sequence(0,statList.length().subtract(1)).map(statsBtGroups)

		statsByGroup = ee.ImageCollection.fromImages(statsByGroup).mosaic()
		return statsByGroup

	# //Move onto computing the standard deviation
	# //Convert n and mean back to raster by group class
	meanByGroup = statsToRaster(means,groupCodes,groups)

	# //Get N raster
	nByGroup = statsToRaster(popN,groupCodes,groups)

	# //Find squared diff
	sqDiff = ic.map(lambda i : i.subtract(meanByGroup.select(['stat'])).pow(2) ).sum().addBands(groups)

	# //Reduce region sum
	sumSqDiff= ee.List(sqDiff.reduceRegion(ee.Reducer.sum().group(1), geometry, analysisScale, crs, None, True, 1e10, tileScale).get('groups'))
	sumSqDiff = ee.List(sumSqDiff.map(lambda g : ee.Dictionary(g).get('sum')))

	stdDev = sumSqDiff.zip(popN).map(lambda l : ee.Number(ee.Number(ee.List(l).get(0)).divide(ee.Number(ee.List(l).get(1)))).sqrt())

	stdDevByGroup =statsToRaster(stdDev,groupCodes,groups)

	meanStdDevTable = groupCodes.zip(means).zip(stdDev).map(lambda l : ee.List(l).flatten())
	# // print('Mean Std Table:', meanStdDevTable)
	# // Map.addLayer(stdDevByGroup.select(['stat']),{'min':500,'max':2000},'StdDev NDVI by class')

	return meanByGroup.select([0]).rename(['mean']) \
		.addBands(stdDevByGroup.select([0]).rename(['stdDev'])) \
		.addBands(nByGroup.select([0,1]).rename(['N','groups']))
# //Functions for z test
def cdfn(z):
  x = z.divide(ee.Image(2).sqrt())
  return ee.Image(0.5).multiply(ee.Image(1).add(x.erf()))
def pval(z):
  z = z.abs().multiply(-1)
  return ee.Image(2).multiply(cdfn(z))

# // Get a list of analysis dates
analysisDates = ee.List.sequence(startJulian, endJulian, analysisPeriod)
yr = analysisYear
baselineStartYr = ee.Number(yr - baselineLength)
baselineEndYr = ee.Number(yr - 1)
print('check baseline start year', baselineStartYr.getInfo())
print('check baseline end year', baselineEndYr.getInfo())
print("analysisDates",analysisDates.getInfo())

#   //Iterate through analysis dates to get dates within baseline and analysis years
def dateTime(dt):
	dt = ee.Number(dt)
	# //Get dates - analysis period
	analysisStartJulian = dt
	analysisEndJulian = dt.add(analysisPeriod).subtract(1)
	analysisStartDate = ee.Date.fromYMD(yr,1,1).advance(analysisStartJulian,'day')
	analysisEndDate = ee.Date.fromYMD(yr,1,1).advance(analysisEndJulian,'day')    
	# print('start of analysis period', analysisStartDate.getInfo())
	# print('end of analysis period', analysisEndDate.getInfo())
	# //Get dates - baseline period
	baselineStartDate = ee.Date.fromYMD(baselineStartYr,1,1).advance(dt.subtract(analysisPeriod),'day')
	baselineEndDate = ee.Date.fromYMD(baselineEndYr,1,1).advance(dt.subtract(1),'day')    
	# print('start of baseline', baselineStartDate)
	# print('end of baseline', baselineEndDate)

	# //Filter to get image collections for analysis and baseline time periods
	analysisCollection = ls.filterDate(analysisStartDate, analysisEndDate)
	# // Fill empty collections in the case of no available images
	#Function to handle empty collections that will cause subsequent processes to fail
	#If the collection is empty, will fill it with an empty image
	# Written by Ian Houseman : https://github.com/rcr-usfs/geeViz/blob/master/getImagesLib.py
	def fillEmptyCollections(inCollection,dummyImage):                       
		dummyCollection = ee.ImageCollection([dummyImage.mask(ee.Image(0))])
		imageCount = inCollection.toList(1).length()
		return ee.ImageCollection(ee.Algorithms.If(imageCount.gt(0),inCollection,dummyCollection))

	analysisCollection = fillEmptyCollections(analysisCollection, dummyImage)
	baselineCollection = ls.filterDate(baselineStartDate, baselineEndDate)

	# // Mask "Groups" with chosen lancover type.
	# //  cover = landcover.filterDate(ee.Date.fromYMD(coverYear-1,1,1),ee.Date.fromYMD(coverYear,1,1))
	# mask
	# // do some checking for if the select coverType includes more than a single value.
	if (type(coverType) == list ):
		to = ee.List.repeat(1, len(coverType))
		mask = cover.remap(coverType,to, 0).rename([coverName])

	else:
		mask = cover.remap([coverType],[1], 0).rename([coverName])
	

	global groups
	groups = groups.updateMask(mask.gte(1))


	# // Apply the landcover mask to the collections
	analysisCollection = analysisCollection.map(lambda img : img.updateMask(groups) )
	baselineCollection = baselineCollection.map(lambda img : img.updateMask(groups) )


	# // Compute and visualize baseline statistics based on index and group
	baselineMeanStdDevN = collectionToMeanStdDev(baselineCollection.select([indexName]),groups)

	# // Call the function to compute statistics. In this case we've precomputed the temporal portions
	# // but the land cover specific needs to be run on-the-fly. For precomputed products, their
	# // function calls can be seen next to each image as comments.
	lcMean = baselineMeanStdDevN.select([0])
	lcStdDev = baselineMeanStdDevN.select([1])
	temporalStdDev = ee.Image("projects/sig-ee/FIRE/DRC/preprocessed/temporalStdDev_DIAF_2000forest")# baselineCollection.select([indexName]).reduce(ee.Reducer.stdDev())
	temporalMean = ee.Image("projects/sig-ee/FIRE/DRC/preprocessed/temporalMean_DIAF_2000forest")# baselineCollection.select([indexName]).mean()    

	# // Function to calculate z-scores and p-values and add as layers to the image
	def addZP(image):
		zSpatial = (image.select([indexName]).subtract(lcMean)).divide(lcStdDev).rename('zval_spatial')
		zTemporal = (image.select([indexName]).subtract(temporalMean)).divide(temporalStdDev).rename('zval_temporal')
		# //Convert z to p
		pSpatial = pval(zSpatial).rename(['pval_spatial'])
		pTemporal = pval(zTemporal).rename(['pval_temporal'])
		return image.select([indexName]).addBands(zSpatial).addBands(pSpatial) \
		.addBands(zTemporal).addBands(pTemporal).addBands(baselineMeanStdDevN.select([0,1,2]))


	# // Map the function above over the analysis collection and display the result.
	analysisCollectionZP = analysisCollection.map(addZP)

	# //reduce the analysis collection (2 images) to the mean values fo export
	forExport = analysisCollectionZP.mean()
	
	# # // Add image properties - Assign analysis period date as the middle of the period
	forExport = forExport.set('system:time_start', (analysisStartDate.advance(int(analysisPeriod/2),'day').millis()))
	forExport = forExport.set('baseline_start', baselineStartDate.millis())
	forExport = forExport.set('baseline_end', baselineEndDate.millis())
	forExport = forExport.set("coverName",coverName,"analysisYear",analysisYear,"baselineLength",baselineLength,
								"startJulian",startJulian,"endJulian",endJulian,"analysisPeriod",analysisPeriod,
								"indexName",indexName)

	# // Add land cover image to export
	forExport = forExport.addBands(cover.rename('landcover'))

	imgNameList = ee.List(['DRC',
					ee.String(baselineStartYr),
					ee.String(baselineEndYr),
					ee.String('a'),
					str(yr),
					ee.String('d'),
					ee.String(analysisStartJulian.int()),
					ee.String(analysisEndJulian.int())])

	imgName = imgNameList.join("_")
	forExport = forExport.set('image_name',imgName)
	
	return forExport
	
	
	# ////////////////////////////////////////////////////////////////////////////////////////////
	# export stuff
	# # // Create a name for export
	# imgName = f'DRC_{str(baselineStartYr)}_{str(baselineEndYr)}_a{str(yr)}_d{str(analysisStartJulian)}_{str(analysisEndJulian)}'

	# # // testing pval as int
	# p_forExport = forExport.select(['pval_spatial','pval_temporal']).multiply(10000)
	# 				.cast({
	# 				'pval_spatial':'int16','pval_temporal':'int16'},['pval_spatial','pval_temporal'])
	# 				print(p_forExport)
	# 				# // testing export N (for size)
	# n_forExport = forExport.select(["N"])
	# # // Use export function to export image to collection
	# getImageLib.exportToAssetWrapper(p_forExport, imgName, exportPathRoot+"/"+imgName,'mean',
	# geometry, exportScale, crs, null)
	

out = ee.ImageCollection(analysisDates.map(dateTime))
print(out.size().getInfo())
print(out.first().bandNames().getInfo())
# test = ee.ImageCollection(out).first().select(['pval_spatial','pval_temporal'])
# task = ee.batch.Export.image.toCloudStorage(image=test,description='test_python',bucket="gee-upload",region=test_geom.geometry().bounds(),scale=300)
# task.start()
export_path = 'projects/sig-misc-ee/assets/drc_fire/test_runs/forests_python'
def export_image_collection(collection):
	collection = collection.sort('system:time_start')
	col_size = collection.size()
	col_list = collection.toList(col_size)
	col_size_local = col_size.getInfo()
	for i in range(0, col_size_local):
		img = ee.Image(col_list.get(i)).select(['pval_spatial','pval_temporal'])
		imgName = img.get('image_name').getInfo() + '_colExportTest_30m'
		print('imgName:',imgName)
		task = ee.batch.Export.image.toAsset(image=img,description=imgName,
		assetId=f'{export_path}/{imgName}',
		region=test_geom.geometry(),
		scale=exportScale,
		crs=crs)
		task.start()

export_image_collection(out)