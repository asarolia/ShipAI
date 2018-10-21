# -*- coding: utf-8 -*-
from obj_dim import *

def lambda_handler(event, context):
    # url = "http://answers.opencv.org/upfiles/logo_2.png"
    url = event['url']
    ppm = pixelsPerMetric_finder()
    print(event)
    h,w = obj_dimensions(ppm, url)
    print("height is:")
    print(h)

    return str(" object has height of " + str(h) + " and width is " + str(w))

# handler(e, None)
if __name__ == "__main__":
    event = {
        "url":"http://answers.opencv.org/upfiles/logo_2.png"
    }
    r = lambda_handler(event,'')
    print(r)