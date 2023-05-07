import sys, os

import glob
import csv

import urllib

folder_path = sys.argv[1]
output_file = sys.argv[2]

print('Folder path:', folder_path)

print('')

fh = open(output_file, 'w')
writer = csv.writer(fh)

header = ["Song name", "Download link"]
writer.writerow(header)

bu_dir = os.getcwd()
os.chdir(folder_path)

for filename in glob.glob("*.doc") + glob.glob("*.pdf"):
    print('  ', filename)
    name = filename[:-4]  #.decode('utf-8') # strip ".doc"
    url = "http://churchconcord.org/songs/" + urllib.quote(filename)
    link_name = "Download"
    value = "<a href='%s'>%s</a>" % (url, link_name)
    row = [name, value]
    #print 'ROW:', name.encode('utf-8'), filename.encode('utf-8')
    writer.writerow(row)

os.chdir(bu_dir)

fh.close()

print('Output CSV file:', output_file)
