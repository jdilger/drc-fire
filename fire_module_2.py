
from fire_module import step1
import ee

ee.Initialize()


class step2:
    def __init__(self, step1, alpha, pVal):
        self.pVal = pVal
        self.alpha = alpha

        self.step1 = step1

        self.coverDict = step1.coverDict
        self.coverName = step1.coverName
        self.cover = step1.cover

        self.analysisYear = step1.analysisYear
        self.analysisPeriod = ee.Number(step1.analysisPeriod)

        self.geometry = step1.geometry
        self.crs = step1.crs
        self.export_scale = step1.exportScale
        self.zCollection = self.coverDict[self.coverName]["exportPath"]
        self.exportCollection = self.coverDict[self.coverName]['exportPathYearly']

    def scalePBands(self, img: ee.Image) -> ee.Image:
        s_bands = img.select(["pval_spatial", 'pval_temporal'])
        s_bands = s_bands.divide(10000)
        return img.select('N').addBands(s_bands)

    def zeroPad(self, n):
        return n.format('%02d')

    # // get date
    def getYearMonthDay(self, y, m, d):

        m = ee.Number(m)
        ms = self.zeroPad(m)

        d = ee.Number(d)
        ds = self.zeroPad(d)

        y = ee.Number(y)
        ys = self.zeroPad(y)
        num = ys.cat(ms).cat(ds)

        return ee.Number.parse(num)

    def getMODISFire(self, startDate, endDate):

        #   //Bring in MYD14/MOD14 and combine them
        modisFireAqua = ee.ImageCollection('MODIS/006/MYD14A2').select([0]) \
            .filterDate(startDate, endDate)
        modisFireTerra = ee.ImageCollection('MODIS/006/MOD14A2').select([0]) \
            .filterDate(startDate, endDate)
        modisFire = ee.ImageCollection(modisFireAqua.merge(modisFireTerra))

        #   //Reclassify data and add year, month, day, and a unique year-month-day bands
        def reclassify(img):
            remapped = img.remap([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [
                                 0, 0, 0, 1, 1, 1, 1, 2, 3, 4]).rename(['confidence'])
            d = ee.Date(img.get('system:time_start'))
            y = d.get('year')
            m = d.get('month')
            day = d.get('day')
            ymd = ee.Number(self.getYearMonthDay(y, m, day))

            y = ee.Image(y).int16().rename(['year'])
            m = ee.Image(m).int16().rename(['month'])
            ymd = ee.Image(ee.Number(ymd)).int64().rename(['yearMonthDay'])
            day = ee.Image(day).int16().rename(['day'])

            out = remapped.addBands(y).addBands(m).addBands(day).addBands(ymd)
            out = out.updateMask(remapped.gte(2))
            return out

        #   //Recode it, and find the most confident year, month, and day
        modisFire = modisFire.map(reclassify).qualityMosaic('confidence')
        return modisFire

    # // Post-process z-score p-values - create/apply MODIS and p-value mask
    def ppZP(self, img):
        #   // Get the analysis period dates
        d = ee.Date(img.get('system:time_start'))

        endDate = d.advance(ee.Number(self.analysisPeriod).divide(2), 'day')
        startDate = ee.Date.fromYMD(d.get('year'), 1, 1)
        startYMD = ee.Number(self.getYearMonthDay(startDate.get(
            'year'), startDate.get('month'), startDate.get('day')))
        endYMD = ee.Number(self.getYearMonthDay(endDate.get(
            'year'), endDate.get('month'), endDate.get('day')))
        #   // Use analysis period dates to pull MODIS data - start of analysis year up to analysis date
        modisFireMask = self.getMODISFire(startDate, endDate)
        #   // Update the mask with burn data
        newMask = img.mask().reduce(ee.Reducer.min()).And(
            modisFireMask.mask().reduce(ee.Reducer.min()))
        #   // Apply p-value threshold and mask - use the user-defined parameters
        newMask = newMask.And(img.select([self.pVal]).lte(self.alpha))
        #   // Add the burn/not burned as a simple binary
        burnImg = newMask.gte(1).rename('burn')
        #   // Add the bands
        img = img.addBands(modisFireMask).addBands(burnImg).mask(newMask)
        return img.set({
            'modisStartDate': startYMD,
            'modisEndDate': endYMD
        })

    # // create just a MODIS burn mask in order to retain raw data for further anlysis (no threshold)
    def ppBurnDate(self, img):
        d = ee.Date(img.get('system:time_start'))
        endDate = d.advance(self.analysisPeriod.divide(2), 'day')
        startDate = ee.Date.fromYMD(d.get('year'), 1, 1)
        startYMD = ee.Number(self.getYearMonthDay(startDate.get(
            'year'), startDate.get('month'), startDate.get('day')))
        endYMD = ee.Number(self.getYearMonthDay(endDate.get(
            'year'), endDate.get('month'), endDate.get('day')))
        modisFireMask = self.getMODISFire(startDate, endDate)
        #   //update the mask
        newMask = img.mask().reduce(ee.Reducer.min()).And(
            modisFireMask.mask().reduce(ee.Reducer.min()))
        img = img.addBands(modisFireMask).mask(newMask)
        return img.set({
            'modisStartDate': startYMD,
            'modisEndDate': endYMD
        })

    def joinCollections(self, c1, c2, maskAnyNullValues=True, joinProperty='system:time_start'):
        def MergeBands(element):
            # A function to merge the bands together.
            # After a join, results are in 'primary' and 'secondary' properties.
            return ee.Image.cat(element.get('primary'), element.get('secondary'))

        join = ee.Join.inner()
        joinFilter = ee.Filter.equals(joinProperty, None, joinProperty)
        joined = ee.ImageCollection(join.apply(c1, c2, joinFilter))

        joined = ee.ImageCollection(joined.map(MergeBands))
        if maskAnyNullValues:
            def nuller(img):
                return img.mask(img.mask().And(img.reduce(ee.Reducer.min()).neq(0)))
            joined = joined.map(nuller)

        return joined

    def export_burn_yearly(self, image, geometry=None, export_path=None, exportScale=None, crs=None, test=False, image_name=None):

        if exportScale is None:
            exportScale = self.export_scale
        if geometry is None:
            geometry = self.geometry.geometry()
        if crs is None:
            crs = self.crs
        if export_path is None:
            export_path = self.coverDict[self.coverName]["exportPathYearly"]

        if image_name is None:
            imgName = f"burn_{self.analysisYear}_{self.coverDict[self.coverName]['abbreviation']}"
        else:
            imgName = image_name

        print('imgName:', imgName)

        if test:
            imgName = f"{imgName}_TEST"
            exportScale = 500
            print(image.toDictionary().getInfo())
            print(ee.Image(image).bandNames().getInfo())
            print(f'{export_path}/{imgName}')
            print('export setting:', 'exportScale', exportScale, 'crs', crs)

        task = ee.batch.Export.image.toAsset(
            image=image, description=imgName,
            assetId=f'{export_path}/{imgName}',
            region=geometry,
            scale=exportScale,
            crs=crs,
            maxPixels=1e13,
        )

        task.start()
        pass

    def main(self):
        zScores = ee.ImageCollection(self.zCollection) \
            .sort('system:time_start') \
            .map(self.scalePBands)

        # // Get metadata about collection from the first image
        templateImage = zScores.first()
        nonSysProperties = templateImage.propertyNames()
        metaData = templateImage.toDictionary(nonSysProperties.cat(
            ['system:asset_size', 'system:time_start', 'system:footprint']))

        zScoresTHandMasked = zScores.map(self.ppZP)
        zScoresBurnMasked = zScores.map(self.ppBurnDate)
        joinZPandPPZP = self.joinCollections(zScoresTHandMasked.select(
            ["burn", "yearMonthDay", "month", "day"]), zScoresBurnMasked, False)

        burnYearly = joinZPandPPZP.select(['burn', 'yearMonthDay']).max()

        self.step1 = step1
        forExport = ee.Image.cat(
            [burnYearly, self.cover.rename('landcover')]).set(metaData)

        return forExport


if "__main__" == __name__:

    test_geom = ee.FeatureCollection(
        "projects/sig-misc-ee/assets/drc_fire/test_areas/test_area")
    DRC_border = ee.FeatureCollection(
        "projects/ee-karistenneson/assets/BurnedBiomass/DRC_Training/DRC_Border")
    cover = ee.Image('projects/sig-ee/FIRE/DRC/DIAF_2000forest')
    covername = "Forests without dry forest"

    a = step1(2016, test_geom, cover, covername)

    # // Threshold for NBR anomaly p-value
    alpha = 0.05
    # // Specify which z-score p-value to use (spatiotemporal or temporal)
    # // These are entered as 'pval_spatial' or 'pval_temporal'
    pVal = 'pval_spatial'
    b = step2(a, alpha, pVal)
    # print(dir(b))
    out = b.main()
    # print(out.size().getInfo())
    print(out.bandNames().getInfo())
    b.export_burn_yearly(out, test=True)
    # print(out.select([b.pVal]).bandNames().getInfo())
    # not found: pval_spatial
    # in output..: pval_spatial
