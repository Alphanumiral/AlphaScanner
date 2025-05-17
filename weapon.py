from PIL import Image
import bettercam
from tesserocr import PyTessBaseAPI
import time
import mouse
import keyboard
import string


#root for all weapon scanning related functions. same functionality as artifact but later functions vary drastically with the same name so having effectively duplicate functions in different files was the easiest way to handle things
#mode 1 scans an individual weapon, mode 2 scans the whole inventory automatically. min rarity is a filter for when to stop if the user does not care about lower quality stuff
def scanRequestHandler(mode, minRarity = 1):
    camera = bettercam.create()
    weaponData = []

    with PyTessBaseAPI(path='./resources/tessdata', lang="genshin_eng") as api:
        #scanning individual item
        if mode == 1:
            try:
                weaponData.append(getItemInfo(camera, api, 1)[0])
            except:
                print("probably on wrong screen")
        #scanning full inventory
        elif mode == 2:
            #moving from default position to weapon menu
            mouse.move(260, 925, True)
            mouse.click(button="left")
            time.sleep(1)
            mouse.move(767, 69, True)
            mouse.click(button="left")
            time.sleep(1)
            #limiter to avoid reading artifact exp items
            quantityImg = Image.fromarray(camera.grab(region=(2095, 47, 2403, 78)))
            api.SetImage(quantityImg)
            quantityStr = api.GetUTF8Text()
            quantity = int(''.join(c for c in quantityStr if c.isdigit())[:-4])

            while quantity > 0 :
                #to account for limitations on scrolling if there are less than 25 items remaining, start on the row where items haven't been scanned yet
                offset = 0
                if quantity < 23:
                    if quantity > 14:
                        offset = 1
                    elif quantity > 6:
                        offset = 2
                    else:
                        offset = 3
                
                for i in range(offset, 4):

                    #if there are less than 8 items remaining, only scan until the final item
                    for j in range(min(quantity, 8)):

                        #interrupting the loop so you don't have to wait for the whole thing to finish
                        if keyboard.is_pressed("q"):
                            quantity = 0
                            break
                        
                        #clicking through the 4 rows and 8 columns cleanly visible on one screen
                        mouse.move(x = 240 + j *195, y = 260 + i * 233, absolute=True)
                        mouse.click(button="left")
                        newItem, rarityCheck = getItemInfo(camera, api, minRarity)
                        #checks against the stars on the weapon, if the minimum star is there then we can continue
                        if not rarityCheck:
                            return weaponData
                        weaponData.append(newItem)
                        quantity -= 1

                #no point dragging down if all the items are done
                if quantity > 0:
                    #dragging to get a new set of 32 items on screen
                    mouse.press(button='left')
                    mouse.move(x = mouse.get_position()[0], y = 8, absolute=True, duration = 1)
                    #killing the momentum from dragging the window before releasing the cursor
                    time.sleep(0.6)
                    mouse.release(button='left')
            #return to default position
            keyboard.press_and_release("esc")
            time.sleep(1)
    
    '''export = json.dumps(weaponData, indent=2)
    f = open("../Alpha Scanner/ScanData/testFile.GOOD.json", "w")
    f.write(export)
    f.close()'''
    return weaponData

#reads the current item clicked on and returns all the necessary info for the GOOD format as a dictionary
def getItemInfo(camera, api, minRarity):
    
    item = {}

    #grabbing the relevant box
    fullSct = None
    while (fullSct is None):
        fullSct = camera.grab(region=(1776, 165, 2406, 1280))
    fullImg = Image.fromarray(fullSct)

    item["location"] = processLocation(fullImg.crop((75, 1047, 624, 1102)), api)
    item["lock"] = processLock(fullImg.crop((554, 425, 555, 426)))
    item["key"] = processKey(fullImg.crop((0, 0, 583, 65)), api)
    item["level"], item["ascension"] = processLevelAscension(fullImg.crop((11, 410, 175, 441)), api)
    item["refinement"] = processRefinement(fullImg.crop((61, 461, 384, 504)), api, item["key"])

    return item, fullImg.load()[24 + 45 * (minRarity - 1), 333][0] > 240


#Processing specific areas of screenshot, some use different page segmentation modes since reading wasn't working well with the default
def processLocation(img, api):
    api.SetVariable("tessedit_pageseg_mode", "7")
    api.SetImage(img)
    str = api.GetUTF8Text()
    #searching for "equipped: " because if the artifact is not equipped and has a long description it would return bad info
    index = str.find("Equipped: ")
    if index != -1:
        return str.replace(" ", "")[9:-1]
    else:
        return ''

def processLock(img):
    #reading colour of pixel to determine lock status rather than image-matching
    if img.load()[0,0][0] < 150:
        return "true"
    else:
        return "false"

def processKey(img, api):
    api.SetVariable("tessedit_pageseg_mode", "3")
    api.SetImage(img)
    #weapon name, extremely weird formatting to try and fit into GOOD format for some outlier weapons that have apostraphes and hyphens
    keyStr = ''.join(filter(lambda x: x.isalpha() or x.isspace() or x == "-", api.GetUTF8Text())) #removes anything that isn't a letter, space, or hyphen
    keyStr = keyStr.replace("-", " ") #replaces hyphen with space
    return ''.join(filter(lambda x: x.isalpha(), string.capwords(keyStr))) #capitalize every word, then remove the spaces

def processLevelAscension(img, api):
    api.SetVariable("tessedit_pageseg_mode", "3")
    api.SetImage(img)

    #weapon level and ascension rank: handled based on / position because of OCR weirdness
    #filtering detection to just the xx/xx part of the level because some weapon level spacing had weird results
    levelStr = ''.join(filter(lambda x: x.isdigit() or x == '/', api.GetUTF8Text()))
    index = levelStr.find("/")

    ascension = float(levelStr[index+1])-3 #the first number of the denominator - 3 is the same as the ascension rank
    if (ascension > 0):
        return int(levelStr[:index]), int(ascension)
    else: #following the equation for ascension, only ascension level 1 (denominator of 20) would be negative leading to this else statement
        return int(levelStr[:index]),  0

def processRefinement(img, api, key):
    api.SetVariable("tessedit_pageseg_mode", "3")
    api.SetImage(img)
    str = api.GetUTF8Text()

    #easiest way to deal with the refinement rank text not being present is to just check for the 10 weapons it applies to
    nonRefineableWeapons = ["ApprenticesNotes", "BeginnersProtector", "DullBlade", "HuntersBow", "WasterGreatsword", "IronPoint", "OldMercsPal", "PocketGrimoire", "SeasonedHuntersBow", "SilverSword"]
    if key not in nonRefineableWeapons and len(str) > 16:
        return int(str[16])  
    else:
        return 1
    