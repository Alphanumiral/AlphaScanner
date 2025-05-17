from PIL import Image
import bettercam
from tesserocr import PyTessBaseAPI
import time
import mouse
import keyboard

#root for all character scanning related functions. mode 1 scans the current character, mode 2 loops through all of them
def scanRequestHandler(mode, travelerName, wandererName):
    charData = []
    camera = bettercam.create()

    
    with PyTessBaseAPI(path='./resources/tessdata', lang="genshin_eng") as api:
        charName = ""
        #helps reading names. more noise is introduced but it's easy to remove
        api.SetVariable("tessedit_pageseg_mode", "7")
        if mode == 1:
            try:
                charName = scanCharacterName(camera, api, travelerName, wandererName)
                charData.append(scanCharacterData(camera, api, charName, mode))
            except:
                print("probably on wrong screen")
        
        if mode == 2:
            #moving from default position to character menu
            mouse.move(669, 720, True)
            mouse.click(button="left")
            time.sleep(1)
            #in case something goes wrong end the loop eventually
            emergency = 150
            #list of scanned character names to be checked against so that we don't repeat characters
            scannedNames = []
            while emergency > 0:
                #interrupting the loop so you don't have to wait for the whole thing to finish
                if keyboard.is_pressed("q"):
                    quantity = 0
                    break
                charName = scanCharacterName(camera, api, travelerName, wandererName)
                if charName in scannedNames:
                    keyboard.press_and_release("esc")
                    time.sleep(1)
                    return charData
                scannedNames.append(charName)
                charData.append(scanCharacterData(camera, api, charName, mode))
            #return to default position
            keyboard.press_and_release("esc")
            time.sleep(1)
        return charData

def scanCharacterName(camera, api, travelerName, wandererName = ""):
    #clicking attribute menu
    mouse.move(225, 200, True)
    mouse.click(button="left")
    time.sleep(0.75)

    #short names sometimes get read incorrectly and shrinking the area helps
    shrinkMod = 0
    #dummy data to enter while loop
    charName = "1"
    while charName.isalpha() == False or len(charName) < 4:
        fullSct = None
        while fullSct is None:
            fullSct = camera.grab(region=(1950, 180, 2400, 320))
        fullImg = Image.fromarray(fullSct)
        if shrinkMod > 325: 
            print("reading issue in char scan")
            #trying to grab again to see if different background will help
            fullSct = None
            while (fullSct is None):
                fullSct = camera.grab(region=(1950, 180, 2400, 320))
            fullImg = Image.fromarray(fullSct)
            shrinkMod = 0
        charNameImg = fullImg.crop((0, 0, 450 - shrinkMod, 50))
        api.SetImage(charNameImg)
        #particle effects sometimes introduce characters into the scan that need to be removed
        charName = "".join(filter(lambda x: x.isalpha(), api.GetUTF8Text().rstrip()))
        #checking for nameable characters
        if charName == wandererName:
            if charName == travelerName:
                #wanderer has friendship, traveler doesn't. checking for the presence of the text enables us to determine who's who
                friendPx = Image.fromarray(camera.grab(region=(1998, 725, 2000, 726)))
                if friendPx.load()[0,0][0] > 250:
                    charName = "Wanderer"
                else:
                    charName = "Traveler"
            else:
                charName = "Wanderer"
        elif charName == travelerName:
            charName = "Traveler"
        shrinkMod += 1
        time.sleep(1/60)
    return charName

#returns dictionary of character info
def scanCharacterData(camera, api, charName, mode):
    char = {"key": charName}
    
    #already known to be on attribute menu since scanning char name always happens before this function

    fullSct = None
    while fullSct is None:
        fullSct = camera.grab(region=(1950, 180, 2400, 320))
    fullImg = Image.fromarray(fullSct)

    #line where the ascension stars for characters are, pixels will be read to check level
    char["ascension"] = processAscension(fullImg.crop((20, 73, 200, 74)))


    char["level"]= processLevel(fullImg.crop((7, 100, 265, 137)), api)

    #clicking constellations menu
    mouse.move(225, 485, True)
    mouse.click(button="left")
    time.sleep(1)

    #screenshotting all the constellation icons along the right side of the screen then reading the pixels where a lock icon would be
    fullSct = None
    while fullSct is None:
        fullSct = camera.grab(region=(1990, 370, 2140, 1115))
    fullImg = Image.fromarray(fullSct)
    conImgs = [
        fullImg.crop((30, 0, 31, 1)),
        fullImg.crop((100, 145, 101, 146)),
        fullImg.crop((145, 295, 146, 296)),
        fullImg.crop((145, 445, 146, 446)),
        fullImg.crop((100, 595, 101, 596)),
        fullImg.crop((0, 740, 1, 741))
    ]
    char["constellation"] = processConstellation(conImgs)

    #clicking talent menu
    mouse.move(225, 575, True)
    mouse.click(button="left")
    time.sleep(0.75)

    #click talent, wait for it to load, grab area where the text would be. grabbing more text than expected because of variance in location and which constellations affect which talents
    talentImgs = []

    #auto
    mouse.move(2337, 225, True)
    mouse.click(button="left")
    time.sleep(0.2)
    fullSct = None
    while fullSct is None:
        fullSct = camera.grab(region=(45, 185, 730, 425))
    fullImg = Image.fromarray(fullSct)
    talentImgs.append(fullImg)

    #skill
    mouse.move(2337, 340, True)
    mouse.click(button="left")
    time.sleep(0.2)
    fullSct = None
    while fullSct is None:
        fullSct = camera.grab(region=(45, 185, 730, 425))
    fullImg = Image.fromarray(fullSct)
    talentImgs.append(fullImg)

    #burst
    mouse.move(2337, 455, True)
    mouse.click(button="left")
    #exception exists because the "special sprint" is the 3rd talent in the list despite not having levels
    if (charName == "Mona" or charName == "KamisatoAyaka"):
        mouse.move(2337, 570, True)
        mouse.click(button="left")
    time.sleep(0.2)
    fullSct = None
    while fullSct is None:
        fullSct = camera.grab(region=(45, 185, 730, 425))
    fullImg = Image.fromarray(fullSct)
    talentImgs.append(fullImg)
    
    char["talent"] = processTalent(talentImgs, api)

    if mode == 2:
        #next char, click twice to escape the talent menu
        mouse.move(2469, 720, True)
        mouse.click(button="left")
        time.sleep(3/60)
        mouse.move(2469, 720, True)
        mouse.click(button="left")
        time.sleep(3/60)

    return char



#reading a pixel from each "star" that represents the ascension level, if they are at that level it would be white (RGB 255/255/255) otherwise RGB 128/128/128
def processAscension(img):
    #reading a pixel from each "star" that represents the ascension level, if they are at that level it would be white (RGB 255/255/255) otherwise RGB 128/128/128
    for i in range(6):
        if img.getpixel((i*35, 0))[0] < 250:
            return i
            break
    #if it hasn't returned yet then we know it should be 6
    return 6


def processLevel(img, api):
    api.SetVariable("tessedit_pageseg_mode", "7")
    api.SetImage(img)
    level = "".join(filter(lambda x: x.isdigit(), api.GetUTF8Text().split("/")[0]))
    return int(level)

#same principle as ascension, but checking the lock icon on the constellation. uses a separate loop because of the implementation of ending the checks. they could be combined but i didn't see the point
def processConstellation(imgs):
    for i in range(6):
        if imgs[i].getpixel((0,0))[0] > 250:
            return i
    return 6

def processTalent(imgs, api):
    api.SetVariable("tessedit_pageseg_mode", "3")
    talentDict = {}
    talentStr = ["auto", "skill", "burst"]
    for i in range(3):
        api.SetImage(imgs[i])
        talent = api.GetUTF8Text().split("\n")
        try:
            talentDict[talentStr[i]] = int("".join(filter(lambda x: x.isdigit(), talent[1])))
        except:
            #very rarely triggers and consistently has been level 1 when it happens
            talentDict[talentStr[i]] = 1
            print(talent)
        if "+3" in talent[5]:
            talentDict[talentStr[i]] -= 3
    return talentDict
