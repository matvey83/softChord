import os

SYSTEM_FILES = set(
        ('_pyjs.js',
         'bootstrap.js',
        )
        )

def outputContainsSystemFiles(outputDir):
    dirs = set(os.listdir(outputDir))
    assert dirs & SYSTEM_FILES == SYSTEM_FILES

def outputContainsPlatforms(outputDir, moduleName, platforms):
    platformFiles = ['%s.%s.cache.html'% (moduleName, p) for p in platforms]
    outputContainsFiles(outputDir, platformFiles)

def outputContainsFiles(outputDir, fileNames):
    dirs = set(os.listdir(outputDir))
    fileNames = set(fileNames)
    assert dirs & fileNames == fileNames


