__location =  {
    'latitude':  +56.1717551,
    'longitude': +10.1891487,
    'elevation': 60
}

__satellites = {
    'DISCO-1': {
        'tx': True,
        'rx': True,
        'tle': [
            "1 56222U 23054AW  24353.67685951  .00225592  00000+0  13568-2 0  9994",
            "2 56222  97.3318 255.2963 0005670 125.2407 234.9391 15.77072259 94741"
        ]
    }
}

def get_gs_location():
    return __location

def get_available_sattelites():
    return __satellites