const { app, BrowserWindow } = require('electron')
const axios = require('axios');
var fs = require('fs')

function createWindow () {
    const win = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    })
    let backend;
    console.log(process.cwd())
    backend = './resources/dist/backend.exe'
    var execfile = require('child_process').execFile;
    execfile(
        backend,
        {
            windowsHide: true,

        }, (err, stdout, stderr) => {  
            if (err) {
                console.log(err);
            }  
            if (stdout) {
                console.log(stdout);
            }  
            if (stderr) {
                console.log(stderr);
            }
        }
    )
    win.loadFile('index.html');
}


//scans whole inventory sections based on what's selected
async function beginMassScan(achievementCheck, characterCheck, travelerName, wandererName, weaponCheck, minWeaponRarity, artifactCheck, minArtifactRarity) {
    var startTime = Date.now()
    var scanTime

    minWeaponRarity = parseInt(minWeaponRarity)
    minArtifactRarity = parseInt(minArtifactRarity)
    await axios.post('http://127.0.0.1:5000/massScan', {achievementCheck, characterCheck, travelerName, wandererName, weaponCheck, minWeaponRarity, artifactCheck, minArtifactRarity})

    scanTime = Date.now()
    //time in seconds
    console.log("time to scan = " + Math.floor((scanTime - startTime)/1000))

}

//scanning the current on screen item
async function beginSingleScan(scanType){
    await axios.post('http://127.0.0.1:5000/singleScan', {scanType})
}

//creating file with all data
async function exportData(mergeCheck, mergeFile){
    var response = await axios.get('http://127.0.0.1:5000/getScanData')
    //putting current paimon.moe data into usable form
    var mergeData
    if (mergeCheck){
        if (mergeFile){
            const reader = new FileReader()
            reader.onload = function(event) {
                mergeData = JSON.parse(event.target.result);
                console.log(mergeData)
            }
            reader.readAsText(mergeFile)
        }   
        else{
            console.log("no file selected")
        }
    }
    //export formatting
    var exportJSON = {
        "format" : "GOOD",
        "version" : 1,
        "source" : "Alpha Scanner"
    }

    var date = new Date()
    var fileName =  date.getFullYear() + "_" + date.getMonth() + "_" + date.getDate() + "_" + date.getHours() + "_" + date.getMinutes() + "_" + date.getSeconds()
    var fileDirectory = "./ScanData/"

    if (!fs.existsSync(fileDirectory)){
        fs.mkdirSync(fileDirectory);
    }
    
    //achievement exported into separate file because it's used on a different website
    if (response.data["achievements"].length != 0){
        achExport = JSON.parse(JSON.stringify(exportJSON))
        if(mergeCheck){
            for (const key in mergeData){
                achExport[key] = mergeData[key]
            }
        }
        achExport["achievement"] = response.data["achievements"]
        fs.writeFile(fileDirectory + fileName + "_Ach.json", JSON.stringify(achExport, null, 2), function(err, file){
            if (err) throw err
        })
    }
    
    //if the arrays are all empty no point making that next file
    if (response.data["characters"].length == 0 && response.data["weapons"].length == 0 && response.data["artifacts"].length == 0) return
    
    //adding info to file name for easier sorting
    if (response.data["characters"].length != 0) {
        exportJSON["characters"] = response.data["characters"]
        fileName += "_Char"
    }
    if (response.data["weapons"].length != 0) {
        exportJSON["weapons"] = response.data["weapons"]
        fileName += "_Weap"
    }
    if (response.data["artifacts"].length != 0) {
        exportJSON["artifacts"] = response.data["artifacts"]
        fileName += "_Arti"
    }

    fileName += ".GOOD.json"

    fs.writeFile(fileDirectory + fileName, JSON.stringify(exportJSON, null, 2), function(err, file){
        if (err) throw err
    })
}

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        const { exec } = require('child_process')
        exec('taskkill /f /t /im backend.exe', (err, stdout, stderr) => { 
            if (err) {  
                console.log(err) 
                return
            } 
            console.log(`stdout: ${stdout}`) 
            console.log(`stderr: ${stderr}`)
        })
        app.quit()
    }
})

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow()
    }
})





