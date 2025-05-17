from PIL import Image
import bettercam
from tesserocr import PyTessBaseAPI
import time
import mouse
import keyboard


#root for all artifact scanning related functions. same functionality as weapon but later functions vary drastically with the same name so having effectively duplicate functions in different files was the easiest way to handle things
#mode 1 scans an individual artifact, mode 2 scans the whole inventory automatically. min rarity is a filter for when to stop if the user does not care about lower quality stuff
def scanRequestHandler(mode, minRarity = 1):
    camera = bettercam.create()
    artifactData = []

    with PyTessBaseAPI(path='./resources/tessdata', lang="genshin_eng") as api:
        #scanning individual item
        if mode == 1:
            try:
                artifactData.append(getItemInfo(camera, api))
            except:
                print("probably on wrong screen")
        #scanning full inventory
        elif mode == 2:
            #moving from default position to artifact menu
            mouse.move(260, 925, True)
            mouse.click(button="left")
            time.sleep(1)
            mouse.move(895, 69, True)
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
                        mouse.move(x = 240 + j *195, y = 330 + i * 233, absolute=True)
                        mouse.click(button="left")
                        newItem = getItemInfo(camera, api)
                        if newItem["rarity"] < minRarity:
                            return artifactData
                        artifactData.append(newItem)
                        quantity -= 1

                #no point dragging down if all the items are done
                if quantity > 0:
                    #dragging to get a new set of 32 items on screen
                    mouse.press(button='left')
                    mouse.move(x = mouse.get_position()[0], y = 77, absolute=True, duration = 1)
                    #killing the momentum from dragging the window before releasing the cursor
                    time.sleep(0.6)
                    mouse.release(button='left')
            #return to default position
            keyboard.press_and_release("esc")
            time.sleep(1)
                
    return artifactData

#reads the current item clicked on and returns all the necessary info for the GOOD format as a dictionary
def getItemInfo(camera, api):
    
    item = {}

    #grabbing the relevant box
    fullSct = None
    while (fullSct is None):
        fullSct = camera.grab(region=(1776, 165, 2406, 1280))
    fullImg = Image.fromarray(fullSct)
    
    #if an artifact is crafted the "sanctifying elixir definition" displaces level, lock, and setkey/substat img locations
    offset = 0
    if fullImg.load()[0, 380][2] > 250:
        offset = 51 

    item["location"] = processLocation(fullImg.crop((75, 1047, 624, 1102)), api)
    item["lock"] = processLock(fullImg.crop((509, 425 + offset, 510, 426 + offset)))
    item["substats"], item["setKey"] = processSetSubstat(fullImg.crop((0, 464 + offset, 602, 768 + offset)), api)
    item["rarity"] = processRarity(fullImg.crop((0, 307, 232, 372))) 
    item["level"] = processLevel(fullImg.crop((15, 410 + offset, 80, 440 + offset)), api)
    item["slotKey"] = processSlot(fullImg.crop((0, 82, 307, 122)), api)
    item["mainStatKey"] = processMainStat(fullImg.crop((4, 199, 304, 230)), api, item["slotKey"])
    
    return item
	

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

def processLevel(img, api):
    api.SetVariable("tessedit_pageseg_mode", "7")
    api.SetImage(img)
    #cutting off the "+" in the level box
    return int((api.GetUTF8Text())[1:])

#set key and substats handled together because of their proximity and that varying counts of substats may displace the set key text
def processSetSubstat(img, api):
    api.SetVariable("tessedit_pageseg_mode", "3")
    api.SetImage(img)
    setKeySubstatStr = api.GetUTF8Text()

    substats = [] 
    setKey = ""

    #since the stats and set name are on multiple lines, we need to split them and remove fake, empty lines that may have been in output
    setKeySubstatStr = list(filter(None, setKeySubstatStr.split("\n"))) 
    for entry in setKeySubstatStr:
        #correcting cases of + being read as a "t" and 1 being read as "l" or "I"
        entry = list(entry)
        plusPassed = False
        for k in range (2, len(entry)):
            if k + 1 < len(entry):
                if entry[k+1].isdigit() and entry[k] == "t":
                    entry[k] = "+"
            if entry[k] == "+":
                plusPassed = True
            if plusPassed and (entry[k] == "l" or entry[k] == "I" or entry[k] == "H"):
                entry[k] = "1"
        entry = "".join(entry)
        #accounting for any number of lines on the artifact, only the set name starts with a letter, artifacts usually see a + or -
        if not entry[0].isalpha():
            key, val = formatStat(entry[2:].split("+")) 
            substats.append({
                "key": key,
                "value": val
            })
        else:
            if entry[-1] == ":": #accounting for set names spanning multiple lines
                setKey += " " + entry
                break #once the set name is found, any extra lines are set info that we don't care about
            setKey = entry

    #from setkey: remove apostraphes, capitalize each word, then remove the spaces
    return substats, ''.join(filter(lambda x: x.isalpha(), ''.join(filter(lambda x: x != "'", setKey)).title()))

def processRarity(img):
    #reading pixel colour to determine if a star is there or not since easier than any other method
    if img.load()[200, 20][0] > 240:
        return 5
    elif img.load()[160, 20][0] > 240:
        return 4
    elif img.load()[110, 20][0] > 240:
        return 3
    elif img.load()[65, 20][0] > 240:
        return 2
    else:
        return 1

def processSlot(img, api):
    api.SetVariable("tessedit_pageseg_mode", "3")
    api.SetImage(img)
    #only care about the first word of the slot text and it needs to be lowercase
    return api.GetUTF8Text().split(' ')[0].lower()

def processMainStat(img, api, slot):
    api.SetVariable("tessedit_pageseg_mode", "7")
    api.SetImage(img)
    #a new line character was consistently at the end for some reason so this removes it
    mainStatStr = api.GetUTF8Text()[:-1]
    if mainStatStr[-1].isdigit():
        mainStatStr = mainStatStr[:-1]
    #feathers, flowers, and elemental mastery other pieces are the only flat stats that exist as main stats. 1 and 1% are just dummy numbers to determine whether it should be hp or hp_ in formatStat
    if slot == "plume" or slot == "flower" or mainStatStr == "Elemental Mastery":
        return formatStat([mainStatStr, "1"])[0]
    else:
        return formatStat([mainStatStr, "1%"])[0]
    

#formatting main and substats to fit GOOD format
def formatStat(stat):
    #for stats like CRIT Rate, easiest to split into individual words
    key = stat[0].strip().split(" ")
    value = stat[1]
    #probably terrible sorting system basing which stats are which on the letters they start with
    if key[0][0] == "A": #anemo, atk, atk%
        if key[0][1] == "n":
            key = "anemo_dmg_"
        elif value[-1] == "%":
            key = "atk_"
        else:
            key = "atk"
    elif key[0][0] == "C": #cryo, crit rate, crit damage
        if len(key) == 3:
            key = "cryo_dmg_"
        elif key[1][0] == "R":
            key = "critRate_"
        elif key[1][0] == "D":
            key = "critDMG_"
    elif key[0][0] == "D": #dendro, def, def%
        if key[0][2] == "n":
            key = "dendro_dmg_"
        elif value[-1] == "%":
            key = "def_"
        else:
            key = "def"
    elif key[0][0] == "E": #electro, ER, EM
        if key[0][3] == "m":
            key = "eleMas"
        elif key[0][3] == "r":
            key = "enerRech_"
        elif key[0][3] == "c":
            key = "electro_dmg_"
    elif key[0][0] == "G": #geo
        key = "geo_dmg_"
    elif key[0][0] == "H": #hp, hp%, healing bonus, hydro
        if key[0][1] == "y":
            key = "hydro_dmg_"
        elif key[0][1] == "e":
            key = "heal_"
        elif value[-1] == "%":
            key = "hp_"
        else:
            key = "hp"
    elif key[0][0] == "P": #phys, pyro
        if key[0][1] == "h":
            key = "physical_dmg_"
        elif key[0][1] == "y":
            key = "pyro_dmg_"
    
    #if the value contains a %, we need to strip that off since the info is contained in the key and the value is stored as a float
    if value[-1] == "%":
        value = value[:-1]
    #if a flat stat rolls to be larger than 1000 a comma appears which will prevent the string from converting to a float
    if len(value) > 1:
        if value[1] == ",":
            value = value[0] + value[2:]
    value = float(value)

    return key, value
