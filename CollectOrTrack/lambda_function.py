import math
import dateutil.parser
import datetime
import time
import os
import random
import json
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
lambdaclient = boto3.client('lambda')

""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def find_item(obj, key):
    item = None
    if key in obj: return obj[key]
    for k, v in obj.items():
        if isinstance(v,dict):
            item = find_item(v, key)
            if item is not None:
                return item

##recursivley check for items in a dict given key
def keys_exist(obj, keys):
    for key in keys:
        if find_item(obj, key) is None:
            return(False)
    return(True)
    
def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }

def elicit_slot_console_msg(session_attributes, intent_name, slots, slot_to_elicit):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit
        }
    }
    
def confirm_intent(session_attributes, intent_name, slots, message, response_card):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ConfirmIntent',
            'intentName': intent_name,
            'slots': slots,
            'message': message,
            'responseCard': response_card
        }
    }



def elicit_slot_resp_card(session_attributes, intent_name, slots, slot_to_elicit, message, response_card):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message,
            'responseCard': response_card
        }
    }

def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }

def build_response_card(title, subtitle, options):
    """
    Build a responseCard with a title, subtitle, and an optional set of options which should be displayed as buttons.
    """
    buttons = None
    if options is not None:
        buttons = []
        for i in range(min(5, len(options))):
            buttons.append(options[i])

    return {
        'contentType': 'application/vnd.amazonaws.card.generic',
        'version': 1,
        'genericAttachments': [{
            'title': title,
            'subTitle': subtitle,
            'buttons': buttons
        }]
    }

def build_response_card_image(title, subtitle, imageurl, options):
    """
    Build a responseCard with a title, subtitle, and an optional set of options which should be displayed as buttons.
    """
    buttons = None
    if options is not None:
        buttons = []
        for i in range(min(5, len(options))):
            buttons.append(options[i])

    return {
        'contentType': 'application/vnd.amazonaws.card.generic',
        'version': 1,
        'genericAttachments': [{
            'title': title,
            'subTitle': subtitle,
            'imageUrl': imageurl,
            'buttons': buttons
        }]
    }

""" --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')

def parse_float(n):
    try:
        return float(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }

def try_ex(func):
    """
    Call passed in function in try block. If KeyError is encountered return None.
    This function is intended to be used to safely access dictionary.

    Note that this function would have negative impact on performance.
    """

    try:
        return func()
    except KeyError:
        return None


def increment_time_by_thirty_mins(ship_time):
    hour, minute = map(int, ship_time.split(':'))
    return '{}:00'.format(hour + 1) if minute == 30 else '{}:30'.format(hour)


def get_random_int(minimum, maximum):
    """
    Returns a random integer between min (included) and max (excluded)
    """
    min_int = math.ceil(minimum)
    max_int = math.floor(maximum)

    return random.randint(min_int, max_int - 1)


def get_availabilities(date):
    """
    Helper function which in a full implementation would  feed into a backend API to provide query schedule availability.
    The output of this function is an array of 30 minute periods of availability, expressed in ISO-8601 time format.

    In order to enable quick demonstration of all possible conversation paths supported in this example, the function
    returns a mixture of fixed and randomized results.

    On Mondays, availability is randomized; otherwise there is no availability on Tuesday / Thursday and availability at
    10:00 - 10:30 and 4:00 - 5:00 on Wednesday / Friday.
    """
    day_of_week = dateutil.parser.parse(date).weekday()
    availabilities = []
    available_probability = 0.3
    if day_of_week == 0:
        start_hour = 10
        while start_hour <= 16:
            if random.random() < available_probability:
                # Add an availability window for the given hour, with duration determined by another random number.
                appointment_type = get_random_int(1, 4)
                if appointment_type == 1:
                    availabilities.append('{}:00'.format(start_hour))
                elif appointment_type == 2:
                    availabilities.append('{}:30'.format(start_hour))
                else:
                    availabilities.append('{}:00'.format(start_hour))
                    availabilities.append('{}:30'.format(start_hour))
            start_hour += 1

    if day_of_week == 2 or day_of_week == 4:
        availabilities.append('10:00')
        availabilities.append('16:00')
        availabilities.append('16:30')

    return availabilities


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False


def is_available(appointment_time, duration, availabilities):
    """
    Helper function to check if the given time and duration fits within a known set of availability windows.
    Duration is assumed to be one of 30, 60 (meaning minutes).  Availabilities is expected to contain entries of the format HH:MM.
    """
    if duration == 30:
        return appointment_time in availabilities
    elif duration == 60:
        second_half_hour_time = increment_time_by_thirty_mins(appointment_time)
        return appointment_time in availabilities and second_half_hour_time in availabilities

    # Invalid duration ; throw error.  We should not have reached this branch due to earlier validation.
    raise Exception('Was not able to understand duration {}'.format(duration))


def get_duration(appointment_type):
    appointment_duration_map = {'cleaning': 30, 'root canal': 60, 'whitening': 30}
    return try_ex(lambda: appointment_duration_map[appointment_type.lower()])


def get_availabilities_for_duration(duration, availabilities):
    """
    Helper function to return the windows of availability of the given duration, when provided a set of 30 minute windows.
    """
    duration_availabilities = []
    start_time = '10:00'
    while start_time != '17:00':
        if start_time in availabilities:
            if duration == 30:
                duration_availabilities.append(start_time)
            elif increment_time_by_thirty_mins(start_time) in availabilities:
                duration_availabilities.append(start_time)

        start_time = increment_time_by_thirty_mins(start_time)

    return duration_availabilities


def validate_order_parcel(d_country, d_city, d_zip, d_address, o_country, o_city, c_address, ship_date, ship_time, length, width, height, volume):
    d_country_type = ['uk', 'usa', 'india']
    if d_country is not None and d_country.lower() not in d_country_type:
        #return build_validation_result(False,
        #                               'dcountry',
        #                               'We do not have delivery service for this country as of now.  '
        #                               'Our most ferequent delivery destinations are {}'.format(d_country_type))
        return build_validation_result(False,
                                       'dcountry',
                                       'Other countries build is in progress and will be enabled shortly.'
                                       'Our most ferequent delivery destinations are {}. Please choose one of them.'.format(d_country_type))
    if d_city is not None:
        try:
            val = int(d_city)
            return build_validation_result(False, 'dcity', 'This is not a valid city name. Please try again')
        except ValueError:
            print("Valid city string")
    else:
        return build_validation_result(False, 'dcity', 'Please tell me the city')
    
    if d_zip is None:
        return build_validation_result(False, 'dzip', 'Please tell me the destination postal code')
    
    if d_address is None:
        return build_validation_result(False, 'daddress', 'Please tell me delivery address')
    if o_country is None:
        return build_validation_result(False, 'ocountry', 'Please tell me country for collection point')    
    
    if o_city is None:
        return build_validation_result(False, 'ocity', 'Please tell me the collection city')
    
    if c_address is None:
        return build_validation_result(False, 'caddress', 'Please tell me address for collection point')
        
    if ship_date is not None:
        if not isvalid_date(ship_date):
            return build_validation_result(False, 'shipdate', 'I did not understand that, what date would you like shipment to be picked up?')
        elif datetime.datetime.strptime(ship_date, '%Y-%m-%d').date() < datetime.date.today():
            return build_validation_result(False, 'shipdate', 'You can not  have shipment date of past.  What day would you like to pick them up?')
        elif dateutil.parser.parse(ship_date).weekday() == 5 or dateutil.parser.parse(ship_date).weekday() == 6:
            return build_validation_result(False, 'shipdate', 'Our office is not open on the weekends, can you provide a work day?')
    else:
        return build_validation_result(False, 'shipdate', 'Thanks. Let me know when you want your collection to happen.')
    
    #print('received ship_time:')
    #print(ship_time)
    if ship_time is not None:
        if len(ship_time) != 5:
            return build_validation_result(False, 'shiptime', 'I did not recognize that, what time would you like to book your collection?')

        hour, minute = ship_time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            return build_validation_result(False, 'shiptime', 'I did not recognize that, what time would you like to book your collection?')

        if hour < 10 or hour > 16:
            # Outside of business hours
            return build_validation_result(False, 'shiptime', 'Our business hours are ten a.m. to five p.m.  What time works best for you?')

        #if minute not in [30, 0]:
            # Must be booked on the hour or half hour
        #    return build_validation_result(False, 'shiptime', 'We schedule appointments every half hour, what time works best for you?')
    else:
        return build_validation_result(False, 'shiptime', 'Please tell me the time for collection(in 12 hr format like 9 AM)')
        
    if length is not None:
        try:
            val = float(length)
        except ValueError:
            return build_validation_result(False, 'length', 'This is not a valid length, only numerics are allowed. Please try again')
    else:
        return build_validation_result(False, 'length', 'Thanks for your patience. Now I need some details around parcel. Please tell me the length of parcel in inches')
        
    if width is not None:
        try:
            val = float(width)
        except ValueError:
            return build_validation_result(False, 'width', 'This is not a valid width, only numerics are allowed. Please try again')
    else:
        return build_validation_result(False, 'width', 'Please tell me the width for parcel in inches')
        
    if height is not None:
        try:
            val = float(height)
        except ValueError:
            return build_validation_result(False, 'height', 'This is not a valid height, only numerics are allowed. Please try again')
    else:
        return build_validation_result(False, 'height', 'Please tell me the height for parcel in inches')
        
    if volume is not None:
        try:
            val = float(volume)
        except ValueError:
            return build_validation_result(False, 'volume', 'This is not a valid volume, only numerics are allowed. Please try again')
    else:
        return build_validation_result(False, 'volume', 'Thanks, just one last thing what is the approximate weight for parcel(in Kg)?')
        
    # if pickup_time is not None:
        # if len(pickup_time) != 5:
            # # Not a valid time; use a prompt defined on the build-time model.
            # return build_validation_result(False, 'PickupTime', None)

        # hour, minute = pickup_time.split(':')
        # hour = parse_int(hour)
        # minute = parse_int(minute)
        # if math.isnan(hour) or math.isnan(minute):
            # # Not a valid time; use a prompt defined on the build-time model.
            # return build_validation_result(False, 'PickupTime', None)

        # if hour < 10 or hour > 16:
            # # Outside of business hours
            # return build_validation_result(False, 'PickupTime', 'Our business hours are from ten a m. to five p m. Can you specify a time during this range?')

    #if flag:
    #    return build_validation_result(False, 'dcountry', 'Hello I am DHlitNow, Let me know how I can help you')
    #else:
    #    return build_validation_result(True, None, None)
    return build_validation_result(True, None, None)


def build_time_output_string(appointment_time):
    hour, minute = appointment_time.split(':')  # no conversion to int in order to have original string form. for eg) 10:00 instead of 10:0
    if int(hour) > 12:
        return '{}:{} p.m.'.format((int(hour) - 12), minute)
    elif int(hour) == 12:
        return '12:{} p.m.'.format(minute)
    elif int(hour) == 0:
        return '12:{} a.m.'.format(minute)

    return '{}:{} a.m.'.format(hour, minute)


def build_available_time_string(availabilities):
    """
    Build a string eliciting for a possible time slot among at least two availabilities.
    """
    prefix = 'We have availabilities at '
    if len(availabilities) > 3:
        prefix = 'We have plenty of availability, including '

    prefix += build_time_output_string(availabilities[0])
    if len(availabilities) == 2:
        return '{} and {}'.format(prefix, build_time_output_string(availabilities[1]))

    return '{}, {} and {}'.format(prefix, build_time_output_string(availabilities[1]), build_time_output_string(availabilities[2]))


def build_options(slot, appointment_type, date, booking_map):
    """
    Build a list of potential options for a given slot, to be used in responseCard generation.
    """
    day_strings = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    if slot == 'AppointmentType':
        return [
            {'text': 'cleaning (30 min)', 'value': 'cleaning'},
            {'text': 'root canal (60 min)', 'value': 'root canal'},
            {'text': 'whitening (30 min)', 'value': 'whitening'}
        ]
    elif slot == 'Date':
        # Return the next five weekdays.
        options = []
        potential_date = datetime.date.today()
        while len(options) < 5:
            potential_date = potential_date + datetime.timedelta(days=1)
            if potential_date.weekday() < 5:
                options.append({'text': '{}-{} ({})'.format((potential_date.month), potential_date.day, day_strings[potential_date.weekday()]),
                                'value': potential_date.strftime('%A, %B %d, %Y')})
        return options
    elif slot == 'Time':
        # Return the availabilities on the given date.
        if not appointment_type or not date:
            return None

        availabilities = try_ex(lambda: booking_map[date])
        if not availabilities:
            return None

        availabilities = get_availabilities_for_duration(get_duration(appointment_type), availabilities)
        if len(availabilities) == 0:
            return None

        options = []
        for i in range(min(len(availabilities), 5)):
            options.append({'text': build_time_output_string(availabilities[i]), 'value': build_time_output_string(availabilities[i])})

        return options
    elif slot == 'confirm':
        return [
            {'text': 'Book', 'value': 'Book'},
            {'text': 'Cancel', 'value': 'Cancel'}
        ]
    elif slot == 'flow':
        return [
            {'text': 'Book Collection', 'value': 'collect'},
            {'text': 'Track Item', 'value': 'track'}
        ]
    elif slot == 'dimflow':
        return [
            {'text': 'Image', 'value': 'Image'},
            {'text': 'Manually', 'value': 'Manual'}
        ]
    elif slot == 'dcountry':
        return [
            {'text': 'UK', 'value': 'UK'},
            {'text': 'USA', 'value': 'USA'},
            {'text': 'INDIA', 'value': 'INDIA'}
        #    {'text': 'Any Other', 'value': 'other'}
        ]
        #return [
        #    {"type":"postback",'title': 'Book Collection', 'payload': 'collect'},
        #    {"type":"postback",'title': 'Track Item', 'payload': 'track'}
        #]

""" --- Functions that control the bot's behavior --- """

def order_parcel(intent_request):
    """
    Performs dialog management and fulfillment for ordering flowers.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """
    logger.debug(intent_request)
    box_o_area = 119
    box_o_vol = 0.5
    box_tw_area = 364
    box_tw_vol = 1.5
    box_th_area = 654
    box_th_vol = 3
    box_fo_area = 1174
    box_fo_vol = 7
    box_fi_area = 2229
    box_fi_vol = 12
    box_si_area = 3374
    box_si_vol = 18
    box_se_area = 4540
    box_se_vol = 25
    flow = True
    #source = intent_request['invocationSource']
    t_flow = get_slots(intent_request)["flow"]
    d_country = get_slots(intent_request)["dcountry"]
    d_city = get_slots(intent_request)["dcity"]
    d_zip = get_slots(intent_request)["dzip"]
    d_address = get_slots(intent_request)["daddress"]
    o_country = get_slots(intent_request)["ocountry"]
    o_city = get_slots(intent_request)["ocity"]
    c_address = get_slots(intent_request)["caddress"]
    ship_date = get_slots(intent_request)["shipdate"]
    ship_time = get_slots(intent_request)["shiptime"]
    dim_flow = get_slots(intent_request)["dimflow"]
    imgurl_o = get_slots(intent_request)["imgurlo"]
    imgurl_t = get_slots(intent_request)["imgurlt"]
    length = get_slots(intent_request)["length"]
    width = get_slots(intent_request)["width"]
    height = get_slots(intent_request)["height"]
    volume = get_slots(intent_request)["volume"]
    confirm = get_slots(intent_request)["confirm"]

    # date = get_slots(intent_request)["PickupDate"]
    # pickup_time = get_slots(intent_request)["PickupTime"]
    # if d_country is not None or d_city is not None or d_zip is not None  or ship_date is not None or length is not None or width is not None or height is not None or volume is not None:
    #    flow = False
    source = intent_request['invocationSource']

    if source == 'FulfillmentCodeHook':
        #if tno is not None:
        #    return close(intent_request['sessionAttributes'],'Fulfilled',{'contentType': 'PlainText','content': 'You shipment has been dispatched and expected to be delivered by tomorrow'})
        if confirm == 'Book':
            return close(intent_request['sessionAttributes'],'Fulfilled',{'contentType': 'PlainText','content': 'Thanks, your booking has been confirmed.Expected quote price for your parcel is GBP {}'.format(intent_request['sessionAttributes']['Price'])})
        else:
            return close(intent_request['sessionAttributes'],'Fulfilled',{'contentType': 'PlainText','content': 'No worries, your booking has been cancelled now.'})


    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)
        if not t_flow:
            get_slots(intent_request)["flow"] = None
            return elicit_slot_resp_card(
                    intent_request['sessionAttributes'],
                    intent_request['currentIntent']['name'],
                    slots,
                    'flow', # slot to elicit
                    {'contentType': 'PlainText', 'content': 'Hello, I am DHL bot and can help you with your request.'}, # message
                    build_response_card_image(
                        'Hello, I am DHL bot and can help you with your request.', 'Please choose',
                        'https://s3.amazonaws.com/dhlimage/logo1.png',
                        build_options('flow', None, None, None)
                    )
                )

        if t_flow == 'collect':
            # indent from here for collect flow
            # validation_result = validate_order_flowers(flower_type, date, pickup_time)
            if d_country is None:
                get_slots(intent_request)["dcountry"] = None
                return elicit_slot_resp_card(
                    intent_request['sessionAttributes'],
                    intent_request['currentIntent']['name'],
                    slots,
                    'dcountry', # slot to elicit
                    {'contentType': 'PlainText', 'content': 'Sure, I can help you with your request.'}, # message
                    build_response_card_image(
                        'Sure, I can help you with your request.', 'Please choose destination country',
                        'https://s3.amazonaws.com/dhlimage/logo1.png',
                        build_options('dcountry', None, None, None)
                    )
                )
            if ship_time is not None and dim_flow is None:
                get_slots(intent_request)["dimflow"] = None
                return elicit_slot_resp_card(
                    intent_request['sessionAttributes'],
                    intent_request['currentIntent']['name'],
                    slots,
                    'dimflow', # slot to elicit
                    {'contentType': 'PlainText', 'content': 'Thanks, I would need parcel dimensions now.'}, # message
                    build_response_card_image(
                        'Thanks, I would need parcel dimensions now.', 'Please choose, how you want to share',
                        'https://s3.amazonaws.com/dhlimage/logo1.png',
                        build_options('dimflow', None, None, None)
                    )
                )
            if (dim_flow == 'Image' and (imgurl_o is None or imgurl_t is None or height is None)):
                #process_image_flow()
                input_script = intent_request['inputTranscript']
                print('input transcript')
                print(input_script)
                print('session attributes')
                print(intent_request['sessionAttributes'])
                if intent_request['sessionAttributes'] is not None:
                    if keys_exist(intent_request['sessionAttributes'], ['imgflag1']):
                        imgurl_o = input_script
                        get_slots(intent_request)["imgurlo"] = imgurl_o
                    else:
                        imgurl_o = get_slots(intent_request)["imgurlo"]
                else:
                    imgurl_o = get_slots(intent_request)["imgurlo"]
                print("first image")
                print(imgurl_o)
                if imgurl_o is None:
                    validation_result = build_validation_result(False,'imgurlo','Please share top view image of parcel from 1 hand distance, covering length and width')
                    logger.debug(validation_result)
                    output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
                    output_session_attributes['imgflag1'] = 'true'
                    print('output session attributes:')
                    print(output_session_attributes)
                    if not validation_result['isValid']:
                        slots[validation_result['violatedSlot']] = None
                        #return elicit_slot(intent_request['sessionAttributes'],
                        return elicit_slot(output_session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])
                    #get_slots(intent_request)["imgurlo"] = None
                    #return elicit_slot(intent_request['sessionAttributes'],
                    #return elicit_slot(output_session_attributes,
                    #           intent_request['currentIntent']['name'],
                    #           slots,
                    #           'imgurlo',
                    #           'Please share top view image of parcel from 1 hand distance, covering length and width')
                if imgurl_o is not None:
                    
                    cvresponse = lambdaclient.invoke(
                                FunctionName='OpenCVLambda',
                                InvocationType='RequestResponse',
                                LogType='Tail',
                                #ClientContext='apiinvoke',
                                Payload=json.dumps({"url":imgurl_o})
                                )
                    print(json.dumps({"url":imgurl_o}))
                    print("opencv response:")
                    #print(cvresponse['Payload'].read().decode())
                    #print("response received")
                    resp = cvresponse['Payload']
                    resp2 = resp.read()
                    resp2 = resp2.decode()
                    resp2 = resp2.strip()
                    print(resp2)
                    brkindex = resp2.find('and')
                    #print(brkindex)
                    length = resp2[22:brkindex-1].strip()
                    width  = resp2[brkindex+12:len(resp2)-1].strip()
                    text_val = 'parcel dimensions are {} {}'.format(length,width)
                    print(text_val)
                    get_slots(intent_request)["length"] = length
                    get_slots(intent_request)["width"] = width
                    
                    
                if intent_request['sessionAttributes'] is not None:
                    if keys_exist(intent_request['sessionAttributes'], ['imgflag2']):
                        imgurl_t = input_script
                        get_slots(intent_request)["imgurlt"] = imgurl_t
                    else:
                        imgurl_t = get_slots(intent_request)["imgurlt"]
                    
                else:
                    imgurl_t = get_slots(intent_request)["imgurlt"]
                #imgurl_t = get_slots(intent_request)["imgurlt"]
                print("second image")
                print(imgurl_t)
                if imgurl_t is None:
                    validation_result = build_validation_result(False,'imgurlt','Please share side view image of parcel from 1 hand distance covering height')
                    logger.debug(validation_result)
                    output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
                    output_session_attributes['imgflag2'] = 'true'
                    if not validation_result['isValid']:
                        slots[validation_result['violatedSlot']] = None
                        #return elicit_slot(intent_request['sessionAttributes'],
                        return elicit_slot(output_session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])
                    #get_slots(intent_request)["imgurlt"] = None
                    #return elicit_slot(intent_request['sessionAttributes'],
                        #return elicit_slot(output_session_attributes,
                    #           intent_request['currentIntent']['name'],
                    #           slots,
                    #           'imgurlt',
                    #           'Please share side view image of parcel from 1 hand distance covering height')
                if imgurl_t is not None:
                    
                    cvresponse_t = lambdaclient.invoke(
                                FunctionName='OpenCVLambda',
                                InvocationType='RequestResponse',
                                LogType='Tail',
                                #ClientContext='apiinvoke',
                                Payload=json.dumps({"url":imgurl_t})
                                )
                    print(json.dumps({"url":imgurl_t}))
                    print("opencv response:")
                    #print(cvresponse['Payload'].read().decode())
                    #print("response received")
                    resp = cvresponse_t['Payload']
                    resp2 = resp.read()
                    resp2 = resp2.decode()
                    resp2 = resp2.strip()
                    print(resp2)
                    brkindex = resp2.find('and')
                    #print(brkindex)
                    length = resp2[22:brkindex-1].strip()
                    height  = resp2[brkindex+12:len(resp2)-1].strip()
                    text_val = 'parcel dimensions are {} {}'.format(length,height)
                    print(text_val) 
                    #get_slots(intent_request)["length"] = length
                    get_slots(intent_request)["height"] = height
                
                if volume is None:
                    validation_result = build_validation_result(False,'volume','Thanks, just one last thing what is the approximate weight for parcel(in Kg)?')
                    logger.debug(validation_result)
                    output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
                    output_session_attributes['processed'] = 'true'
                    if not validation_result['isValid']:
                        slots[validation_result['violatedSlot']] = None
                        return elicit_slot(output_session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])
                    
            else:
                #process_manual_flow(intent_request)
                validation_result = validate_order_parcel(d_country, d_city, d_zip, d_address, o_country, o_city, c_address, ship_date, ship_time, length, width, height, volume)
                logger.debug(validation_result)
                #output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
                #if ship_time is not None:
                #    output_session_attributes['dimflag'] = 'true'
                #if length is not None and width is not None and validation_result['violatedSlot'] == 'height':
                #    output_session_attributes['LBflag'] = 'true'
                #    output_session_attributes['length'] = float(length)
                #    output_session_attributes['width'] = float(width)

                if not validation_result['isValid']:
                    slots[validation_result['violatedSlot']] = None
                    return elicit_slot(intent_request['sessionAttributes'],
                    #return elicit_slot(output_session_attributes,
                               intent_request['currentIntent']['name'],
                               slots,
                               validation_result['violatedSlot'],
                               validation_result['message'])

            print('length : {}, width : {}, height : {}, Volume: {} '.format(length,width,height,volume))
            output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
            if volume is not None:
                output_session_attributes['Price'] = parse_float(volume) * 2  # Elegant pricing model

            print('confirm : {}'.format(confirm))
            if confirm is None:
                parcel_area = parse_float(length) * parse_float(width) * parse_float(height)
                if parcel_area <= box_o_area:
                    boximg = 'https://s3.amazonaws.com/dhlimage/box1.png'
                if parcel_area <= box_tw_area and parcel_area > box_o_area:
                    boximg = 'https://s3.amazonaws.com/dhlimage/box2.png'
                if parcel_area <= box_th_area and parcel_area > box_tw_area:
                    boximg = 'https://s3.amazonaws.com/dhlimage/box3.png'
                if parcel_area <= box_fo_area and parcel_area > box_th_area:
                    boximg = 'https://s3.amazonaws.com/dhlimage/box4.png'
                if parcel_area <= box_fi_area and parcel_area > box_fo_area:
                    boximg = 'https://s3.amazonaws.com/dhlimage/box5.png'
                if parcel_area <= box_si_area and parcel_area > box_fi_area:
                    boximg = 'https://s3.amazonaws.com/dhlimage/box6.png'
                if parcel_area <= box_se_area and parcel_area > box_si_area:
                    boximg = 'https://s3.amazonaws.com/dhlimage/box7.png'
                if parcel_area >= box_se_area:
                    boximg = 'https://s3.amazonaws.com/dhlimage/box7.png'
                get_slots(intent_request)["confirm"] = None
                return elicit_slot_resp_card(
                        output_session_attributes,
                        intent_request['currentIntent']['name'],
                        slots,
                        'confirm', # slot to elicit
                        {'contentType': 'PlainText', 'content': 'Expected delivery Date : {} , Price : {}, Service : DHLItNow'.format(ship_date, intent_request['sessionAttributes']['Price'])}, # message
                        build_response_card_image(
                        'We have selected appropriate box, please confirm booking', 'Expected delivery Date : {} , Price : {}, Service : DHLItNow'.format(ship_date, intent_request['sessionAttributes']['Price']),
                        boximg,  # image url goes here
                        build_options('confirm', None, None, None)
                        )
                    )


            # Pass the price of the flowers back through session attributes to be used in various prompts defined
            # on the bot model.
            output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
            if volume is not None:
                #output_session_attributes['Price'] = parse_int(volume) * 2  # Elegant pricing model
                output_session_attributes['daddress'] = d_address  # store destination address in session
                output_session_attributes['caddress'] = c_address  # store collection address in session
                output_session_attributes['shipdate'] = ship_date  # select shipment collection date
                output_session_attributes['shiptime'] = ship_time
                output_session_attributes['confirm'] = confirm

            #if not ship_date:
            #    return elicit_slot_resp_card(
            #        output_session_attributes,
            #        intent_request['currentIntent']['name'],
            #        intent_request['currentIntent']['slots'],
            #        'shipdate',
            #        {'contentType': 'PlainText', 'content': 'When would you like us to pick up parcel ?'},
            #        build_response_card(
            #            'Specify Date',
            #            'When would you like us to pick up parcel?',
            #            build_options('shipdate', None, ship_date, None)
            #        )
            #    )

            return delegate(output_session_attributes, get_slots(intent_request))
            
    # Order the flowers, and rely on the goodbye message of the bot to define the message to the end user.
    # In a real bot, this would likely involve a call to a backend service.
    #return close(intent_request['sessionAttributes'],
    #             'Fulfilled',
    #             {'contentType': 'PlainText',
    #              'content': 'Thanks, your order for {} has been placed and will be ready for pickup by {} on {}'.format(flower_type, pickup_time, date)})

        if t_flow == 'track':
            get_slots(intent_request)["tno"] = None
            return elicit_slot(intent_request['sessionAttributes'],
                               intent_request['currentIntent']['name'],
                               slots,
                               'tno',
                               'Sure, I can help you.Can you please share your tracking reference number?')
            output_session_attributes['tno'] = tno
            
            return delegate(output_session_attributes, get_slots(intent_request))

""" --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'dhlexpress':
        return order_parcel(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')


""" --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    #os.environ['TZ'] = 'America/New_York'
    #time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
