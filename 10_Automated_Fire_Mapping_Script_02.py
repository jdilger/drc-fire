
import ee

ee.Initialize()
import config as c
from paramters import *



# // Import and sort image collection of z scores
zCollection = 'projects/sig-misc-ee/assets/drc_fire/test_runs/forests_python'

#   ///////////////////////////////////////////////////////////////////////
#  ////////// 2. Parameters //////////////////////////////////////////////
# ///////////////////////////////////////////////////////////////////////
# // Threshold for NBR anomaly p-value
alpha = 0.05

# // Specify which z-score p-value to use (spatiotemporal or temporal)
# // These are entered as 'pval_spatial' or 'pval_temporal'
pVal = 'pval_spatial' 

# // Location for Asset exports
exportCollection =  'projects/ee-karistenneson/assets/BurnedBiomass/DRC_Exports/DRC_BurnMaps_2016'

zScores = ee.ImageCollection(zCollection).sort('system:time_start')

def zeroPad(n):
    return n.format('%02d')

# // get date 
def getYearMonthDay(y,m,d):

    m = ee.Number(m)
    ms = zeroPad(m)
    
    d = ee.Number(d)
    ds = zeroPad(d)

    y = ee.Number(y)
    ys = zeroPad(y)
    num = ys.cat(ms).cat(ds)

    return ee.Number.parse(num)

def getMODISFire(startDate,endDate):

#   //Bring in MYD14/MOD14 and combine them 
    modisFireAqua = ee.ImageCollection('MODIS/006/MYD14A2').select([0]) \
                        .filterDate(startDate,endDate)
    modisFireTerra = ee.ImageCollection('MODIS/006/MOD14A2').select([0]) \
                        .filterDate(startDate,endDate)
    modisFire = ee.ImageCollection(modisFireAqua.merge(modisFireTerra))
  
#   //Reclassify data and add year, month, day, and a unique year-month-day bands
    def reclassify(img):
        remapped = img.remap([0,1,2,3,4,5,6,7,8,9],[0,0,0,1,1,1,1,2,3,4]).rename(['confidence'])
        d = ee.Date(img.get('system:time_start'))
        y = d.get('year')
        m = d.get('month')
        day =d.get('day')
        ymd = ee.Number(getYearMonthDay(y,m,day))
        
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
def ppZP(img):
#   // Get the analysis period dates
  d = ee.Date(img.get('system:time_start'))
  endDate = d.advance(ee.Number(analysisPeriod).divide(2),'day')
  startDate = ee.Date.fromYMD(d.get('year'),1,1)
  startYMD = ee.Number(getYearMonthDay(startDate.get('year'),startDate.get('month'),startDate.get('day')))
  endYMD = ee.Number(getYearMonthDay(endDate.get('year'),endDate.get('month'),endDate.get('day')))
#   // Use analysis period dates to pull MODIS data - start of analysis year up to analysis date
  modisFireMask = getMODISFire(startDate,endDate)
#   // Update the mask with burn data
  newMask = img.mask().reduce(ee.Reducer.min()).And(modisFireMask.mask().reduce(ee.Reducer.min()))
#   // Apply p-value threshold and mask - use the user-defined parameters 
  newMask = newMask.And(img.select([pVal]).lte(alpha))
#   // Add the burn/not burned as a simple binary
  burnImg = newMask.gte(1).rename('burn')
#   // Add the bands
  img = img.addBands(modisFireMask).addBands(burnImg).mask(newMask)
  return img.set({
    'modisStartDate':startYMD,
    'modisEndDate':endYMD
  })

# // create just a MODIS burn mask in order to retain raw data for further anlysis (no threshold)
def ppBurnDate(img):
  d = ee.Date(img.get('system:time_start'))
  endDate = d.advance(analysisPeriod.divide(2),'day')
  startDate = ee.Date.fromYMD(d.get('year'),1,1)
  startYMD = ee.Number(getYearMonthDay(startDate.get('year'),startDate.get('month'),startDate.get('day')))
  endYMD = ee.Number(getYearMonthDay(endDate.get('year'),endDate.get('month'),endDate.get('day')))
  modisFireMask = getMODISFire(startDate,endDate)
#   //update the mask
  newMask = img.mask().reduce(ee.Reducer.min()).And(modisFireMask.mask().reduce(ee.Reducer.min()))
  img = img.addBands(modisFireMask).mask(newMask)
  return img.set({
    'modisStartDate':startYMD,
    'modisEndDate':endYMD
  })
#Helper function to join two collections- Source: code.earthengine.google.com
# https://github.com/rcr-usfs/geeViz/blob/9dd6a9785d4df9fc9d912e353f6af547371bb2ae/getImagesLib.py#L1753
def joinCollections(c1, c2, maskAnyNullValues = True, joinProperty = 'system:time_start'):
  def MergeBands(element):
    #A function to merge the bands together.
    #After a join, results are in 'primary' and 'secondary' properties.
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
# /////////////////////////////////////////
# // note: everything above should be good to toss into a class

# / GENERATE BURN MAPS
# // Create a collection with the burn-masked and p-value threshold applied to delineate burned areas
analysisPeriod = ee.Number(zScores.first().get('analysisPeriod')) 
zScoresTHandMasked = zScores.map(ppZP)
print(zScoresTHandMasked.first().bandNames().getInfo())
# // Create another collection with just the burn-areas masked to preserve continuous anomaly data
# zScoresBurnMasked = zScores.map(ppBurnDate)
# # // Join the collections - take only what you need
# joinZPandPPZP = joinCollections(zScoresTHandMasked.select(["burn","yearMonthDay","month","day"]), zScoresBurnMasked, False)
# # // Remove the mean, stdDev, and N bands
# joinZPandPPZP = joinZPandPPZP.select([0,1,2,3,4,5,6,7,8])

# print('Here is the final burn map collection for export:', 
# joinZPandPPZP.size().getInfo(),joinZPandPPZP.first().bandNames().getInfo())


# test zero padding
img = zScores.first()

# d = ee.Date(img.get('system:time_start'))
# endDate = d.advance(ee.Number(analysisPeriod).divide(2),'day')
# startDate = ee.Date.fromYMD(d.get('year'),1,1)
# print(startDate.get('year').getInfo(),startDate.get('month').getInfo(),startDate.get('day').getInfo())
# print(getYearMonthDay(startDate.get('year'),startDate.get('month'),startDate.get('day')).getInfo())
# print(zeroPad(startDate.get('month')).getInfo())
# startYMD = ee.Number(getYearMonthDay(startDate.get('year'),startDate.get('month'),startDate.get('day')))
# endYMD = ee.Number(getYearMonthDay(endDate.get('year'),endDate.get('month'),endDate.get('day')))