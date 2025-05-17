from flask import Flask, jsonify, request
import achievement, character, weapon, artifact

app = Flask(__name__)

#globals flag so that multiple scan requests don't happen at the same time
currentlyScanning = False
scanData = {
    "achievements": [],
    "characters": [],
    "weapons": [],
    "artifacts": []
}

#function for scanning whole sections of inventory
@app.route("/massScan", methods = ['POST'])
def massScan():
    global currentlyScanning
    global scanData

    if currentlyScanning:
        return jsonify({"error": "Already scanning"}), 429
    
    currentlyScanning = True

    checks = request.json
    #replaces each corresponding section of scanData because scanning the entire inventory will contain all wanted items anyway according to filter
    if checks["achievementCheck"] == True:
        scanData["achievements"] = achievement.scanAchievements()
    if checks["characterCheck"] == True:
        scanData["characters"] = character.scanRequestHandler(2, checks["travelerName"], checks["wandererName"])
    if checks["weaponCheck"] == True:
        scanData["weapons"] = weapon.scanRequestHandler(2, checks["minWeaponRarity"])
    if checks["artifactCheck"] == True:
        scanData["artifacts"] = artifact.scanRequestHandler(2, checks["minArtifactRarity"])

    currentlyScanning = False
    return "a", 200

#scanning the current on screen item
@app.route("/singleScan", methods= ['POST'])
def singleScan():
    global currentlyScanning
    global scanData
    if currentlyScanning:
        return jsonify({"error": "Already scanning"}), 429
    
    currentlyScanning = True

    scanType = request.json["scanType"]
    if scanType == "characters":
        scanResult = character.scanRequestHandler(1)
    if scanType == "weapons":
        scanResult = weapon.scanRequestHandler(1)
    if scanType == "artifacts":
        scanResult = artifact.scanRequestHandler(1)
    if scanResult == []:
        #bad scan, probably on wrong page, do not add to dataset
        currentlyScanning = False
        return "a", 200
    scanData[scanType].append(scanResult[0])

    currentlyScanning = False
    return "a", 200

#returning all data for export
@app.route("/getScanData", methods = ['GET'])
def getScanData():
    if currentlyScanning:
        return jsonify({"error": "wait for scan to complete"}), 429
        
    return jsonify(scanData), 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)