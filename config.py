# // the default path to use if a pth isnt set in the landcoverOptions function.
# // currently has export paths for default forest types for testing. 
defaultExportPath = "projects/sig-misc-ee/assets/drc_fire/test_runs"


coverDict = {
    "Dense humid forest on dry land":{
      "value":1,
      "abbreviation": "DHF",
      "color":'8aa745',
      "exportPath":"projects/sig-misc-ee/assets/drc_fire/test_runs/dhf"
    },
    "Dense moist forest on hydromorphic soil":{
      "value":2,
      "abbreviation":"DMF",
      "color":'6ee682',
      "exportPath":"projects/sig-misc-ee/assets/drc_fire/test_runs/dmf"
    },
    "Secondary forest":{
      "value":3,
      "abbreviation":"SNDF",
      "color":'f0ff72',
      "exportPath": "projects/sig-misc-ee/assets/drc_fire/test_runs/sndf"
    },
    "Dry forest or open forest":{
      "value":4,
      "abbreviation":"DRYF",
      "color":'ffc625',
      "exportPath":"projects/sig-misc-ee/assets/drc_fire/test_runs/dryf"
    },
    "Savannah":{
      "value":5,
      "abbreviation":"SAV",
      "color":'19ffbf'
    },
    "Cultures and regeneration of abandoned crops":{
      "value":6,
      "abbreviation": "REGN",
      "color":'9219ff'
    },
    "Water zone":{
      "value":7,
      "abbreviation":"WATER",
      "color":'0400ff'
    },
    "Agglomeration":{
      "value":8,
      "abbreviation":"AGGL",
      "color":'ff04ec'
    },
    "Other":{
      "value":9,
      "abbreviation":"OTHER",
      "color":'a9a9a9'
    },
    "Forests without dry forest":{
      "value": [1,2,3],
      "abbreviation":"FOREST",
      "exportPath":"projects/sig-misc-ee/assets/drc_fire/test_runs/forests"
    }

  }