
import sys, os

import glob
import csv


folder_path = sys.argv[1]
output_file = sys.argv[2]

print 'Folder path:', folder_path
print 'Output CSV file:', output_file

print ''


fh = open(output_file, 'w')
writer = csv.writer(fh)

header = ["name","path"]
writer.writerow(header)

bu_dir = os.getcwd()
os.chdir(folder_path)


for filename in glob.glob("*.doc"):
    print '  ', filename
    name = filename[:-4] # strip ".doc"
    row = [name, filename]
    print 'ROW:', row
    writer.writerow(row)

os.chdir(bu_dir)

fh.close()



