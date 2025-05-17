from PIL import Image
import pyperclip
import requests
import bettercam
from tesserocr import PyTessBaseAPI
import time
import keyboard
import mouse

#there is no reason to scan individual achievements so the only option available is to scan all of them
def scanAchievements():
    
    #moving from default position to achievement menu
    mouse.move(885, 555, True) 
    mouse.click(button="left")
    time.sleep(1)
    mouse.move(255, 375, True)
    mouse.click(button="left")
    time.sleep(1)


    camera = bettercam.create()

    #getting achievement database from paimon.moe repo
    req = requests.get("https://raw.githubusercontent.com/MadeBaruna/paimon-moe/main/src/data/achievement/en.json")
    if req.status_code == requests.codes.ok:
        achievementDB = req.json()

    achievementData = {}
    '''
    achievementDB is a dict full of integer:category pairs
    a category is a dictionary with the keys name and achievements, which are self explanatory
    achievements is mostly a list of dict, with each dict containing the keys id, name, desc, reward, and ver, but we only care about the first 2
    within the achievements list, multi-step achievements are a list of dict. every dict is the same for every key except the id and sometimes the reward
    '''
    with PyTessBaseAPI(path='./resources/tessdata', lang="genshin_eng") as api:
        api.SetVariable("tessedit_pageseg_mode", "7")
        for category in achievementDB:
            for achievement in achievementDB[category]["achievements"]:
                #escape loop if needed
                if keyboard.is_pressed("q"):
                    return achievementData
                
                #clear text in search
                mouse.move(600, 180, True)
                mouse.click(button="left")
                time.sleep(4/60)
                #start typing in search again
                mouse.click(button="left")
                time.sleep(3/60)
                #type the achievement into the search, for multi step achievement they all share a name so we can just take the first one
                #this was originally done using typewrite from pyautogui, but apparently some of the characters can't be written using typewrite like the em dash in T—T—T—Timberhochwandi
                if type(achievement) == dict:
                    pyperclip.copy(achievement["name"])
                else:
                    pyperclip.copy(achievement[0]["name"])
                
                keyboard.press_and_release('ctrl+v')
                #search for the achievement
                mouse.move(780, 180, True)
                time.sleep(1/60)
                mouse.click(button="left")
                time.sleep(6/60)

                #reading the number of matches
                matches = None
                while matches is None:
                    matches = camera.grab(region=(983, 210, 1200, 241))
                matches = Image.fromarray(matches)
                api.SetImage(matches)
                matches = api.GetUTF8Text().rstrip()
                if len(matches) < 12:
                    matches = 0
                else:
                    #weird ocr stuff
                    if matches[-1] == "I" or matches[-1] == "|":
                        matches = 1
                    elif matches[-1] == "Z":
                        matches = 2
                    else:
                        if matches[0] != "M":
                            matches = matches[1:]
                        try:
                            matches = int(matches[-1])
                        except:
                            print(matches)
                            print(type(matches))
                #small delay because the actual achievement text takes time to load
                time.sleep(0.4)
                if matches > 1:
                    time.sleep(0.3)
                

                
                #achievementData results are formatted as a list for easier sorting later based on list lengths

                #single-step achievement
                if type(achievement) == dict:
                    sct = None
                    #if no match, we know the achievement isn't complete
                    if matches == 0:
                        id, category, result = processAchievements([[achievement["id"]], str(category)], api)
                    #with 1 match we just care about the star for the achievement found in the search and the id of the achievement we are checking
                    elif matches == 1:
                        while sct is None:
                            sct = camera.grab(region=(1066, 396, 1094, 424))
                        star = Image.fromarray(sct)
                        id, category, result = processAchievements([[achievement["id"]], str(category), star], api)
                    #matches > 1. we need to screenshot every star and every category returned, and pass it with the category and id of the achievement to check against later
                    else:
                        while sct is None:
                            sct = camera.grab(region=(985, 275, 1900, 275 + 221 * matches))
                        sct = Image.fromarray(sct)
                        stars = []
                        categories = []
                        for i in range(matches):
                            stars.append(sct.crop((81, 121 + 221*i, 109, 149 + 221*i)))
                            categories.append(sct.crop((17, 10 + 221*i, 915, 42 + 221*i)))
                        id, category, result = processAchievements([[achievement["id"]], str(category), stars, categories, achievementDB[category]["name"]], api)

                #multi-step achievement
                elif type(achievement) == list:
                    sct = None
                    #since each step has a separate id, we need to mark each one separately
                    ids = []
                    for step in achievement:
                        ids.append(step["id"])

                    #if no match, we know the achievement isn't complete
                    if matches == 0:
                        id, category, result = processAchievements([ids, str(category)], api)

                    #with 1 match we just care about the stars of the achievement found in the search and the list of IDs for every step of the achievement
                    elif matches == 1:
                        while sct is None:
                            sct = camera.grab(region=(1051, 381, 1109, 430))
                        star = Image.fromarray(sct)
                        id, category, result = processAchievements([ids, str(category), star], api)

                    #matches > 1. we need to screenshot every set of stars and every category returned, and pass it with the category and list of IDs for every step of the achievement to check against later
                    else:
                        while sct is None:
                            sct = camera.grab(region=(985, 275, 1900, 275 + 221 * matches))
                        sct = Image.fromarray(sct)
                        stars = []
                        categories = []
                        for i in range(matches):
                            stars.append(sct.crop((66, 106 + 221*i, 124, 155 + 221*i)))
                            categories.append(sct.crop((17, 10 + 221*i, 915, 42 + 221*i)))
                        id, category, result = processAchievements([ids, str(category), stars, categories, achievementDB[category]["name"]], api)
                else:
                    print("wtf achievement type is this?")
                
                
                for (achievement, res) in zip(id, result):
                    if category not in achievementData:
                        achievementData[category] = {achievement: res}
                    else:
                        achievementData[category].update({achievement: res})

            
        #returning to default position
        keyboard.press_and_release("esc")
        time.sleep(1)
        keyboard.press_and_release("esc")
        time.sleep(1)
        return achievementData
    
def processAchievements(data, api):
    #always present parts of data
    id = data[0]
    category = data[1]
    #processing is different based on the amount of information given
    
    #length of 2 means no result, so the achievement is incomplete
    if len(data) == 2:
        #single achievement, so ID is an integer, multi-step would mean ID is a list
        if len(id) == 1:
            return id, category, [False]
        
        #multi-step achievement, multiple IDs, multiple values
        return id, category, [False, False, False]
    
    #length of 3 means single result
    elif len(data) == 3:
        star = data[2]

        #single achievement, so ID is an integer, multi-step would mean ID is a list
        if len(id) == 1:
            #red value of filled star is 254, red value of incomplete star is ~130, so this should be enough to account for weird variance due to external shaders
            if star.getpixel((14,14))[0] > 240:
                return id, category, [True]
            return id, category, [False]
        
        #multi-step achievement, multiple IDs, multiple values
        #measuring third, second, then first star to be filled in. if one of them is filled then the ones that come before in achievement progression must be filled. return according completion state
        if star.getpixel((45, 34))[0] > 240:
            return id, category, [True, True, True]
        elif star.getpixel((15, 34))[0] > 240:
            return id, category, [True, True, False]
        elif star.getpixel((30, 15))[0] > 240:
            return id, category, [True, False, False]
        return id, category, [False, False, False]
    
    #length of 5 means multiple results
    elif len(data) == 5:
        stars = data[2]
        categories = data[3]
        categoryName = data[4]
        
        #loops through the number of results we ended up getting
        for i in range(len(stars)):
            #getting the category name from screenshot, if it returns something extremely short it's probably a mistake so shrink the image and try to scan again
            apiText = ""
            tempCategoryImg = categories[i]
            while len(apiText) < 5 or len(apiText) > len(categoryName):
                api.SetImage(tempCategoryImg)
                apiText = api.GetUTF8Text()
                #no point trying to better the reading if it's already set
                if apiText.strip() in categoryName:
                    break
                imgSize = tempCategoryImg.size
                tempCategoryImg = tempCategoryImg.crop((0, 0, imgSize[0]-5, imgSize[1]))
            #single achievement, so ID is an integer, multi-step would mean ID is a list
            if len(id) == 1:
                #if the category name we're looking for matches the category name in the screenshot, we know it's the correct achievement and can scan the star accordingly
                if apiText.strip() in categoryName:
                    if stars[i].getpixel((14,14))[0] > 240:
                        return id, category, [True]
                    return id, category, [False]
            
            #multi-step achievement, multiple IDs, multiple values
            #if the category name we're looking for matches the category name in the screenshot, we know it's the correct achievement and can scan the star accordingly
            if apiText.strip() in categoryName:
                if stars[i].getpixel((45, 34))[0] > 240:
                    return id, category, [True, True, True]
                elif stars[i].getpixel((15, 34))[0] > 240:
                    return id, category, [True, True, False]
                elif stars[i].getpixel((30, 15))[0] > 240:
                    return id, category, [True, False, False]
                return id, category, [False, False, False]
    print("should never reach")
    return id, "-1", [False]
