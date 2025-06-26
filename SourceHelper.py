import csv
import os

filemakerPath = input("Enter the path to the Filemaker Export: ").strip('\'"')
sourceaudioPath = input("Enter the path to the SourceAudio Export: ").strip('\'"')
filemakerDict = []
SourceAudioDict = {}
headers = ""
with open(filemakerPath, newline='', encoding='utf-8') as FilemakerExport:
    with open(sourceaudioPath, newline='', encoding='utf-8') as SourceAudioExport:
        filemaker = csv.DictReader(FilemakerExport)
        headers = [h.replace("SA ", "") if h else h for h in filemaker.fieldnames]
        headers = [h.replace("000000", "") if h else h for h in headers]

        filemakerDict = list(filemaker)
        SourceAudio = csv.DictReader(SourceAudioExport)
        for row in SourceAudio:
            SourceAudioDict[os.path.splitext(row["Filename"])[0]] = row["Sourceaudio Id"]

nestingLookup = {}

for row in filemakerDict:
    name = os.path.splitext(row["SA Filename000000"])[0]
    if name in SourceAudioDict:
        row["SA SourceAudio ID000000"] = SourceAudioDict[name]
    else:
        row["SA SourceAudio ID000000"] = "Not Found"
        print(f"Sourceaudio Id not found for {name}")
        continue
    if row["SA Versions Only"] == "Full":
        nestingLookup[row["SA Title Only"]] = row["SA SourceAudio ID000000"]

for row in filemakerDict:
    row["SA Master ID"] = nestingLookup.get(row["SA Title Only"], "Not Found")


with open(filemakerPath, 'w', newline='', encoding='utf-8') as FilemakerExport:
    writer = csv.DictWriter(FilemakerExport, fieldnames=headers)
    writer.writeheader()
    writer.writerows(filemakerDict)