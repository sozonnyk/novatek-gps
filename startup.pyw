import os, re, win32api, win32file, subprocess
from gpxextractor import GpxExtractor

VIEWER_EXE = "RegistratorViewer_v.6.0.0.22.exe"
gpx = re.compile(r'\.[gG][pP][xX]$')
mp4 = re.compile(r'\.[mM][pP]4$')

def filter_gpx(filename):
	return gpx.search(filename)

def filter_mp4(filename):
	return mp4.search(filename)

def filter_file_array(root, function, filenames, result):
	result.extend(list(map(lambda f: os.path.join(root,f), list(filter(function, filenames)))))

def subtract_file_arrays(source, destination):
	result = list(destination)
	for source_file in source:
		matching_source_files = list(filter(lambda f: f.startswith(source_file[:-3]), destination))
		for matching_source_file in matching_source_files:
			result.remove(matching_source_file)
	return result

def removable_drive():
	drives = win32api.GetLogicalDriveStrings().split('\000')[:-1]
	removable = list(filter(lambda d: win32file.GetDriveType(d) == win32file.DRIVE_REMOVABLE, drives))
	if len(removable) > 0:
		return removable[0]
		
	print("No removable drive")
	exit(1)

def start_viewer():
	DETACHED_PROCESS = 0x00000008
	dir = os.path.dirname(os.path.realpath(__file__))
	subprocess.Popen([dir + "/" + VIEWER_EXE, drive],creationflags = DETACHED_PROCESS)
	
gpx_files = []
mp4_files = []

drive = removable_drive()
for root, dirnames, filenames in os.walk(drive):
	filter_file_array(root, filter_gpx, filenames, gpx_files)
	filter_file_array(root, filter_mp4, filenames, mp4_files)
	
orphan_gpx_files = subtract_file_arrays(mp4_files, gpx_files)
orphan_mp4_files = subtract_file_arrays(gpx_files, mp4_files)

for orphan_gpx_file in orphan_gpx_files:
	print("Removing %s" % orphan_gpx_file)
	os.remove(orphan_gpx_file)
	
gpx_extractor = GpxExtractor()
	
for orphan_mp4_file in orphan_mp4_files:
	gpx_extractor.process_file(orphan_mp4_file)
	
start_viewer()