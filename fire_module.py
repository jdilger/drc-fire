
from fire_params import paramtersIO
import ee
import imgLib
ee.Initialize()


class step1(paramtersIO):
    '''Class for initializing the first steps in the burn anomalies mapping process and key input into the second step for generating burn maps.

    Args:
        paramtersIO (class): Parameters for cloud and shadow masking and dictionary of cover names and export paths.
        analysisYear (int): The year to generate burn products.
        geometry (ee.FeatureCollection): A feature collection of at least 1 geometry for the ROI. If there are multiple features in a collection the geometry is found with the .geometry() method.
        cover (ee.Image): The land cover image that is described in paramterIO cover dictionary.
        coverName (str): The land cover name to generate burn products for.
    '''

    def __init__(self, analysisYear: int, geometry, cover, coverName):
        paramtersIO.__init__(self)

        # land cover and geomery init
        self.analysisYear = analysisYear
        self.coverName = coverName
        self.coverType = self.coverDict[coverName]['value']
        self.cover = cover
        self.geometry = geometry
        self.full_baseline_col = ee.ImageCollection(
            self.coverDict[coverName]['exportPathBaseline'])

        # ls init
        self.ls = None
        self.dummyImage = None

        # shared analysis init
        self.yr = None
        self.baselineStartYr = None
        self.baselineEndYr = None
        self.baseline_col = None

    def test_prepare_script1(self, geometry, cover, coverName):
        # self.coverName = coverName
        # self.coverType = self.coverDict[coverName]['value']
        # self.cover = cover
        # self.geometry = geometry

        # startDate, endDate = self.prepare_dates(self.startJulian, self.endJulian)
        self.prepare_masking(self.maskingMethod)
        self.apply_masking_params()
        ls_setup = self.setup_landsat()
        start = self.analysisYear - self.baselineLength
        self.ls = ls_setup.getLandsat(
            self.geometry, start, self.analysisYear).map(self.ND_nir_swir2)
        self.dummyImage = ee.Image(self.ls.first())
        analysisDates, self.yr, self.baselineStartYr, self.baselineEndYr = self.get_analysis_dates(
            self.startJulian, self.endJulian, self.analysisPeriod, self.analysisYear)
        out = analysisDates.map(lambda i: self.test_prepare_baseline_dates(i))

        return ee.List(out)

    def prepare_script1(self):

        self.prepare_masking(self.maskingMethod)
        self.apply_masking_params()
        ls_setup = self.setup_landsat()
        start = self.analysisYear - self.baselineLength
        self.ls = ls_setup.getLandsat(
            self.geometry, start, self.analysisYear).map(self.ND_nir_swir2)
        self.dummyImage = ee.Image(self.ls.first())
        analysisDates, self.yr, self.baselineStartYr, self.baselineEndYr = self.get_analysis_dates(
            self.startJulian, self.endJulian, self.analysisPeriod, self.analysisYear)
        out = analysisDates.map(lambda i: self.prepare_baseline(i))

        return ee.ImageCollection(out)

    def script1(self):

        print(self.full_baseline_col.size().getInfo())
        self.baseline_col = self.full_baseline_col.filterMetadata(
            "coverName", "equals", self.coverName).map(lambda i: self.unscale_bands(i))
        print(self.baseline_col.size().getInfo())
        print(self.baseline_col.first().bandNames().getInfo())
        self.prepare_masking(self.maskingMethod)
        self.apply_masking_params()
        ls_setup = self.setup_landsat()
        self.ls = ls_setup.getLandsat(
            self.geometry, self.analysisYear - self.baselineLength, self.analysisYear).map(self.ND_nir_swir2)
        self.dummyImage = ee.Image(self.ls.first())
        analysisDates, self.yr, self.baselineStartYr, self.baselineEndYr = self.get_analysis_dates(
            self.startJulian, self.endJulian, self.analysisPeriod, self.analysisYear)
        out = analysisDates.map(lambda i: self.dateTime(i))

        return ee.ImageCollection(out)

    def unscale_bands(self, img):

        scaleBands = ["tStd", "tMean", "mean", "stdDev"]
        nonscaleBands = ["N", "groups"]
        scaled_img = img.select(scaleBands).divide(10000)
        noscale = img.select(nonscaleBands)
        return noscale.addBands(scaled_img)

    def prepare_dates(self, startJulian, endJulian):

        if (startJulian > endJulian):
            endJulian = endJulian + 365
        startDate = ee.Date.fromYMD(
            self.analysisYear-self.baselineLength, 1, 1).advance(startJulian-1, 'day')
        endDate = ee.Date.fromYMD(
            self.analysisYear, 1, 1).advance(endJulian-1, 'day')

        return startDate, endDate

    def prepare_masking(self, maskingMethod):

        maskingMethod = self.maskingMethod.lower()
        if (maskingMethod == 'fmaskapproach'):
            print('FMask masking')
            self.appplyFmaskApproach = True
        elif (maskingMethod == 'zscoreapproach'):
            print('Zscore masking')
            self.applyZscoreApproach = True
        else:
            print('WARNING: not using cloud/cloud shadow masking')

    def apply_masking_params(self):

        if (self.applyZscoreApproach):
            self.applyCloudScore = True
            self.applyTDOM = True

        if (self.appplyFmaskApproach):
            self.applyFmaskCloudMask = True
            self.applyFmaskCloudShadowMask = True
            self.applyFmaskSnowMask = False

        if(self.toaOrSR == 'TOA'):
            self.applyFmaskCloudMask = False
            self.applyFmaskCloudShadowMask = False
            self.applyFmaskSnowMask = False

    def ND_nir_swir2(self, img):
        img = img.addBands(img.normalizedDifference(
            ['nir', 'swir2']).rename(['NBR']))  # NBR, MNDVI
        return img

    # todo:set all env stuff when deciding in other functions

    def setup_landsat(self):
        env = imgLib.landsat.env()
        env.maskSR = self.applyFmaskCloudMask
        env.shadowMask = self.applyTDOM
        env.cloudMask = self.applyCloudScore
        ls = imgLib.landsat.functions(env)
        return ls

    def collectionToMeanStdDev(self, collection, groups):

        ic = collection
        # //Reduce the collection
        # icMean = ic.mean()
        # icStdDev = ic.reduce(ee.Reducer.stdDev())

        icSum = ic.sum().addBands(groups.rename('groups'))
        icCount = ic.count().addBands(groups.rename('groups'))

        # //Get the area reductions
        popN = ee.List(icCount.reduceRegion(ee.Reducer.sum().group(1), self.geometry,
                                            self.analysisScale, self.crs, None, True, 1e10, self.tileScale).get('groups'))
        popSum = ee.List(icSum.reduceRegion(ee.Reducer.sum().group(
            1), self.geometry, self.analysisScale, self.crs, None, True, 1e10, self.tileScale).get('groups'))

        # //Parse out the group codes
        groupCodes = popN.map(lambda g: ee.Dictionary(g).get('group'))

        # //Extract the N and sums
        popN = popN.map(lambda g: ee.Dictionary(g).get('sum'))
        popSum = popSum.map(lambda g: ee.Dictionary(g).get('sum'))

        # //Zip the N and sum for mean computation
        nSumZipped = ee.List(popSum).zip(popN)

        # //Compute means
        means = nSumZipped.map(lambda l: ee.Number(
            ee.List(l).get(0)).divide(ee.List(l).get(1)))

        # //Wrapper function to convert statList back to raster
        def statsToRaster(statList, groupCodeList, groupImage):

            def statsBtGroups(code):
                stat = ee.Number(statList.get(code))

                groupCode = ee.Number(groupCodeList.get(code))

                out = groupImage.eq(groupCode)
                out = out.updateMask(out)
                out = out.multiply(stat).rename(['stat']).addBands(
                    out.multiply(groups).rename(['groups']))
                return out.float()

            statsByGroup = ee.List.sequence(
                0, statList.length().subtract(1)).map(statsBtGroups)

            statsByGroup = ee.ImageCollection.fromImages(statsByGroup).mosaic()
            return statsByGroup

        # //Move onto computing the standard deviation
        # //Convert n and mean back to raster by group class
        meanByGroup = statsToRaster(means, groupCodes, groups)

        # //Get N raster
        nByGroup = statsToRaster(popN, groupCodes, groups)

        # //Find squared diff
        sqDiff = ic.map(lambda i: i.subtract(
            meanByGroup.select(['stat'])).pow(2)).sum().addBands(groups)

        # //Reduce region sum
        sumSqDiff = ee.List(sqDiff.reduceRegion(ee.Reducer.sum().group(
            1), self.geometry, self.analysisScale, self.crs, None, True, 1e10, self.tileScale).get('groups'))
        sumSqDiff = ee.List(sumSqDiff.map(
            lambda g: ee.Dictionary(g).get('sum')))

        stdDev = sumSqDiff.zip(popN).map(lambda l: ee.Number(
            ee.Number(ee.List(l).get(0)).divide(ee.Number(ee.List(l).get(1)))).sqrt())

        stdDevByGroup = statsToRaster(stdDev, groupCodes, groups)

        meanStdDevTable = groupCodes.zip(means).zip(
            stdDev).map(lambda l: ee.List(l).flatten())
        # // print('Mean Std Table:', meanStdDevTable)
        # // Map.addLayer(stdDevByGroup.select(['stat']),{'min':500,'max':2000},'StdDev NDVI by class')

        return meanByGroup.select([0]).rename(['mean']) \
            .addBands(stdDevByGroup.select([0]).rename(['stdDev'])) \
            .addBands(nByGroup.select([0, 1]).rename(['N', 'groups']))

    # //Functions for z test
    def cdfn(self, z):
        x = z.divide(ee.Image(2).sqrt())
        return ee.Image(0.5).multiply(ee.Image(1).add(x.erf()))

    def pval(self, z):
        z = z.abs().multiply(-1)
        return ee.Image(2).multiply(self.cdfn(z))

    def get_analysis_dates(self, startJulian, endJulian, analysisPeriod, analysisYear):
        # todo: clean this up now that in class...
        analysisDates = ee.List.sequence(
            startJulian, endJulian, analysisPeriod)
        yr = analysisYear
        baselineStartYr = ee.Number(yr - self.baselineLength)
        baselineEndYr = ee.Number(yr - 1)
        return analysisDates, yr, baselineStartYr, baselineEndYr

    def test_prepare_baseline_dates(self, dt):
        dt = ee.Number(dt)

        analysisStartJulian = dt
        analysisStartDate = ee.Date.fromYMD(
            self.yr, 1, 1).advance(analysisStartJulian, 'day')

        # //Get dates - baseline period
        baselineStartDate = ee.Date.fromYMD(self.baselineStartYr, 1, 1).advance(
            dt.subtract(self.analysisPeriod), 'day')
        baselineEndDate = ee.Date.fromYMD(
            self.baselineEndYr, 1, 1).advance(dt.subtract(1), 'day')
        # analysisStartDate
        return analysisStartDate.advance(int(self.analysisPeriod/2), 'day').millis()

    def prepare_baseline(self, dt):
        dt = ee.Number(dt)

        analysisStartJulian = dt
        analysisStartDate = ee.Date.fromYMD(
            self.yr, 1, 1).advance(analysisStartJulian, 'day')

        # //Get dates - baseline period
        baselineStartDate = ee.Date.fromYMD(self.baselineStartYr, 1, 1).advance(
            dt.subtract(self.analysisPeriod), 'day')
        baselineEndDate = ee.Date.fromYMD(
            self.baselineEndYr, 1, 1).advance(dt.subtract(1), 'day')

        # analysisCollection = fillEmptyCollections(analysisCollection, self.dummyImage)
        baselineCollection = self.ls.filterDate(
            baselineStartDate, baselineEndDate)

        if (type(self.coverType) == list):
            to = ee.List.repeat(1, len(self.coverType))
            mask = self.cover.remap(
                self.coverType, to, 0).rename([self.coverName])

        else:
            mask = self.cover.remap(
                [self.coverType], [1], 0).rename([self.coverName])

        groups_m = self.groups.updateMask(mask.gte(1))

        # // Apply the landcover mask to the collections
        baselineCollection = baselineCollection.map(
            lambda img: img.updateMask(groups_m))

        baselineMeanStdDevN = self.collectionToMeanStdDev(
            baselineCollection.select([self.indexName]), groups_m)
        temporalStdDev = baselineCollection.select(
            [self.indexName]).reduce(ee.Reducer.stdDev()).rename("tStd")
        temporalMean = baselineCollection.select(
            [self.indexName]).mean().rename("tMean")

        out = baselineMeanStdDevN.addBands(
            temporalStdDev).addBands(temporalMean)
        out = self.set_metadata(out, analysisStartDate,
                                baselineStartDate, baselineEndDate)

        # todo move this block into another function
        # maybe scaleBands(func, img/imgCol, args/kwags)
        # func = scale_baseline(img/imgCol, scalebands, no scalebands, )
        scaleBands = ["tStd", "tMean", "mean", "stdDev"]
        nonscaleBands = ["N", "groups"]
        scaled_img = out.select(scaleBands).multiply(10000).int16()
        out = out.select(nonscaleBands).addBands(scaled_img)

        return out
        #   //Iterate through analysis dates to get dates within baseline and analysis years

    def dateTime(self, dt):
        dt = ee.Number(dt)
        # //Get dates - analysis period
        # todo: improvments analysisDates and baseline dates to funtion? another class?
        analysisStartJulian = dt
        analysisEndJulian = dt.add(self.analysisPeriod).subtract(1)
        analysisStartDate = ee.Date.fromYMD(
            self.yr, 1, 1).advance(analysisStartJulian, 'day')
        analysisEndDate = ee.Date.fromYMD(
            self.yr, 1, 1).advance(analysisEndJulian, 'day')

        # //Get dates - baseline period
        baselineStartDate = ee.Date.fromYMD(self.baselineStartYr, 1, 1).advance(
            dt.subtract(self.analysisPeriod), 'day')
        baselineEndDate = ee.Date.fromYMD(
            self.baselineEndYr, 1, 1).advance(dt.subtract(1), 'day')

        # //Filter to get image collections for analysis and baseline time periods
        analysisCollection = self.ls.filterDate(
            analysisStartDate, analysisEndDate)
        # // Fill empty collections in the case of no available images
        # Function to handle empty collections that will cause subsequent processes to fail
        # If the collection is empty, will fill it with an empty image
        # Written by Ian Houseman : https://github.com/rcr-usfs/geeViz/blob/master/getImagesLib.py

        def fillEmptyCollections(inCollection, dummyImage):
            dummyCollection = ee.ImageCollection(
                [dummyImage.mask(ee.Image(0))])
            imageCount = inCollection.toList(1).length()
            return ee.ImageCollection(ee.Algorithms.If(imageCount.gt(0), inCollection, dummyCollection))

        analysisCollection = fillEmptyCollections(
            analysisCollection, self.dummyImage)
        baselineCollection = self.baseline_col.filterDate(
            analysisStartDate, analysisEndDate)

        # // Mask "Groups" with chosen lancover type.
        # //  cover = landcover.filterDate(ee.Date.fromYMD(coverYear-1,1,1),ee.Date.fromYMD(coverYear,1,1))
        # mask
        # // do some checking for if the select coverType includes more than a single value.
        if (type(self.coverType) == list):
            to = ee.List.repeat(1, len(self.coverType))
            mask = self.cover.remap(
                self.coverType, to, 0).rename([self.coverName])

        else:
            mask = self.cover.remap(
                [self.coverType], [1], 0).rename([self.coverName])

        groups_m = self.groups.updateMask(mask.gte(1))

        # // Apply the landcover mask to the collections
        analysisCollection = analysisCollection.map(
            lambda img: img.updateMask(groups_m))
        # baselineCollection = baselineCollection.map(lambda img : img.updateMask(groups_m) )

        # // Compute and visualize baseline statistics based on index and group
        baselineImage = baselineCollection.first()

        # # // Call the function to compute statistics. In this case we've precomputed the temporal portions
        # # // but the land cover specific needs to be run on-the-fly. For precomputed products, their
        # # // function calls can be seen next to each image as comments.
        lcMean = baselineImage.select(['mean'])
        lcStdDev = baselineImage.select(['stdDev'])
        temporalStdDev = baselineImage.select(['tStd'])
        temporalMean = baselineImage.select(['tMean'])

        # // Function to calculate z-scores and p-values and add as layers to the image
        def addZP(image):
            zSpatial = (image.select([self.indexName]).subtract(
                lcMean)).divide(lcStdDev).rename('zval_spatial')
            zTemporal = (image.select([self.indexName]).subtract(
                temporalMean)).divide(temporalStdDev).rename('zval_temporal')
            # //Convert z to p
            pSpatial = self.pval(zSpatial).rename(['pval_spatial'])
            pTemporal = self.pval(zTemporal).rename(['pval_temporal'])
            return image.select([self.indexName]).addBands(zSpatial).addBands(pSpatial) \
                .addBands(zTemporal).addBands(pTemporal)  # .addBands(baselineMeanStdDevN.select([0,1,2])) #I dont think we need this...

        # // Map the function above over the analysis collection and display the result.
        analysisCollectionZP = analysisCollection.map(addZP)

        # //reduce the analysis collection (2 images) to the mean values fo export
        forExport = analysisCollectionZP.mean()
        # // Add land cover image to export
        forExport = forExport.addBands(self.cover.rename(
            'landcover')).addBands(baselineImage.select('N'))

        # # // Add image properties - Assign analysis period date as the middle of the period
        forExport = self.set_metadata(
            forExport, analysisStartDate, baselineStartDate, baselineEndDate)

        imgNameList = ee.List(['DRC',
                               ee.String(self.baselineStartYr),
                               ee.String(self.baselineEndYr),
                               ee.String('a'),
                               str(self.yr),
                               ee.String('d'),
                               ee.String(analysisStartJulian.int()),
                               ee.String(analysisEndJulian.int())])

        imgName = imgNameList.join("_")
        forExport = forExport.set('image_name', imgName)

        return forExport

    def set_metadata(self, forExport, *args):
        analysisStartDate = args[0]
        baselineStartDate = args[1]
        baselineEndDate = args[2]

        forExport = forExport.set('system:time_start', (analysisStartDate.advance(
            int(self.analysisPeriod/2), 'day').millis()))
        forExport = forExport.set('baseline_start', baselineStartDate.millis())
        forExport = forExport.set('baseline_end', baselineEndDate.millis())
        forExport = forExport.set("coverName", self.coverName, "analysisYear", self.analysisYear, "baselineLength", self.baselineLength,
                                  "startJulian", self.startJulian, "endJulian", self.endJulian, "analysisPeriod", self.analysisPeriod,
                                  "indexName", self.indexName)
        return forExport

    def export_nbr_anomalies(self, image, geometry, i, export_path=None, exportScale=None, crs=None, test=False):
        if exportScale is None:
            exportScale = self.exportScale
        if crs is None:
            crs = self.crs
        if export_path is None:
            export_path = self.coverDict[self.coverName]["exportPath"]

        scaleBands = image.select(
            ['pval_spatial', 'pval_temporal']).multiply(10000).int16()
        img = image.select(['N']).addBands(scaleBands)
        imgName = f"nbr_anomalies_{self.analysisYear}_{self.coverDict[self.coverName]['abbreviation']}_{i}"
        print('imgName:', imgName)

        if test:
            # print(ee.Image(img).toDictionary().getInfo())
            # print(ee.Image(img.bandNames().getInfo())
            imgName = f"{imgName}_TEST"

            print(f'{export_path}/{imgName}')

            task = ee.batch.Export.image.toAsset(
                image=img, description=imgName,
                assetId=f'{export_path}/{imgName}',
                region=geometry.geometry(),
                scale=exportScale,
                crs=crs,
                maxPixels=1e13,
            )

            task.start()
        else:
            task = ee.batch.Export.image.toAsset(
                image=img, description=imgName,
                assetId=f'{export_path}/{imgName}',
                region=geometry.geometry(),
                scale=exportScale,
                crs=crs,
                maxPixels=1e13,
            )

            task.start()
        return imgName

    def export_baseline_landcover(self, image, geometry, i, export_path=None, exportScale=None, crs=None, test=False, test_export=False):
        if exportScale is None:
            exportScale = self.exportScale
        if crs is None:
            crs = self.crs
        if export_path is None:
            export_path = self.coverDict[self.coverName]["exportPathBaseline"]

        imgName = f'baseline_mean_std_{self.analysisYear}_{self.coverDict[self.coverName]["abbreviation"]}_{i}'
        print('imgName:', imgName)

        if test:
            # print(ee.Image(image).toDictionary().getInfo())
            # print(ee.Image(image).bandNames().getInfo())
            imgName = f"{imgName}_TEST"
            print(self.coverName)
            print(f'{export_path}/{imgName}')
            img = image
            task = ee.batch.Export.image.toAsset(
                image=img, description=imgName,
                assetId=f'{export_path}/{imgName}',
                region=geometry.geometry(),
                scale=exportScale,
                crs=crs,
                maxPixels=1e13,
            )

            task.start()
        else:
            img = image
            task = ee.batch.Export.image.toAsset(
                image=img, description=imgName,
                assetId=f'{export_path}/{imgName}',
                region=geometry.geometry(),
                scale=exportScale,
                crs=crs,
                maxPixels=1e13,
            )

            task.start()

        return imgName

    def export_image_collection(self, collection, export_func, geometry=None, export_path=None, exportScale=None, crs=None, test=False, test_export=False):
        if geometry is None:
            geometry = self.geometry
        collection = collection.sort('system:time_start')
        col_size = collection.size()
        col_list = collection.toList(col_size)
        col_size_local = 12
        export_descriptions = []
        if test:
            col_size_local = 1
        for i in range(0, col_size_local):
            img_in = ee.Image(col_list.get(i))
            desc = export_func(img_in, geometry, i,
                               export_path, exportScale, crs, test)
            export_descriptions.append(desc)

        return export_descriptions


if "__main__" == __name__:

    # drc
    test_geom = ee.FeatureCollection(
        "projects/sig-misc-ee/assets/drc_fire/test_areas/test_area")
    DRC_border = ee.FeatureCollection(
        "projects/ee-karistenneson/assets/BurnedBiomass/DRC_Training/DRC_Border")
    cover = ee.Image('projects/sig-ee/FIRE/DRC/DIAF_2000forest')

    # # // The land cover map is for 2000.
    # # // Cover classes are in this order:
    # # // Value, Label, Abbreviation
    # # // "1", "Dense humid forest on dry land", DHF
    # # // "2" ,"Dense moist forest on hydromorphic soil", DMF
    # # // "3" ,"Secondary forest", SNDF
    # # // "4" ,"Dry forest or open forest", DRYF
    # # // "5" ,"Savannah", SAV
    # # // "6" ,"Cultures and regeneration of abandoned crops", REGN
    # # // "7" ,"Water zone", WATER
    # # // "8" ,"Agglomeration", AGGL
    # # // "9" ,"Other", OTHER
    # # // "1,2,3" ,"Forests without dry forest", FOREST
    # # //Chose a cover class to filter to for fire detection:
    covername = "Dry forest or open forest"
    a = step1(2016, test_geom, cover, covername)
    # # dag step 1. make baseline col, wait for export
    prep_lc = a.prepare_script1()
    a.export_image_collection(
        prep_lc, a.export_baseline_landcover, test=True, exportScale=500)

    # # dag step 2. calculate anomalies, wait for export
    # baselineCol = ee.ImageCollection("projects/sig-misc-ee/assets/drc_fire/baseline")
    # anom_lc = a.script1()
    # print(dir(a))
    # print(ee.ImageCollection(ee.List(anom_lc).get(4)).first().id().getInfo())
    # assert ee.List(anom_lc).map(lambda i : ee.ImageCollection(i).size()).getInfo() == [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

    # print(anom_lc.first().bandNames().getInfo())
    # a.export_image_collection(anom_lc,a.export_nbr_anomalies, test=True)

    # ###############################3
    # # roc
    # cover = ee.Image("projects/sig-misc-ee/assets/roc_fire/landcover/roc_forest_cover_map_1990_gaf_fin01")
    # region = ee.FeatureCollection(ee.Feature(cover.geometry()))
    # covername = "Forest"
    # # prep_lc = a.prepare_script1(region,cover,covername)
    # # a.export_image_collection(prep_lc,region,a.export_baseline_landcover,test=False)

    # baselineCol = ee.ImageCollection("projects/sig-misc-ee/assets/roc_fire/baseline")
    # anom_lc = a.script1(baselineCol,region,cover,covername)

    # a.export_image_collection(anom_lc,region,a.export_nbr_anomalies,test=True)
