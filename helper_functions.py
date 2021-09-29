def read_extension_phone_number(platform):
  resp = platform.get("/restapi/v1.0/account/~/extension/~/phone-number")
  jsonObj = resp.json()
  for record in jsonObj.records:
    for feature in record.features:
      if feature == "SmsSender":
        return record.phoneNumber

def send_sms(platform, fromNumber, toNumber, message):
  resp = platform.post('/restapi/v1.0/account/~/extension/~/sms',
              {
                  'from' : { 'phoneNumber': fromNumber },
                  'to'   : [ {'phoneNumber': toNumber} ],
                  'text' : message
              })
  jsonObj = resp.json()