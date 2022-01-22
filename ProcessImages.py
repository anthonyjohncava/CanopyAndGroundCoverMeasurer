import os, sys
from java.lang import System;
from java.io import File
import re
from ij import IJ, ImagePlus, Prefs
from ij.plugin import ChannelSplitter
from ij.io import DirectoryChooser
from ij.gui import GenericDialog
import time

# Parses a filename and determines whether to process as Ground or Canopy
def get_image_type(filename):
  # Strip the path
  filename = os.path.basename(filename)
  filename = os.path.splitext(filename)[0]
  print("Getting Image Type for Image: " + filename)
  # Example Filename is 'XX01-20210806-CC.JPG'
  # this splits the string into an array, the Ground or Canopy identifier is in position 3 (second element in array)
  filename_tokens = filename.split("-")
  if len(filename_tokens) < 3:
    print("Invalid Filename Format")
    return ""
  elif filename_tokens[2] == "GC":
    print("Image Type: GROUND")
    return "GROUND"
  elif filename_tokens[2] == "CC":
    print("Image Type: CANOPY")
    return "CANOPY"
  else:
    print("Image Type: UNKNOWN")
    return filename_tokens[2]

# Canopeo algorithm to determine if pixel is a vegetation or not
def canopeofy(r,g,b):
  # Setting: Adjust from 0.80 to 1.10. 0.95 is the default.
  setting = 0.95
  p1 = setting
  p2 = setting
  p3 = 20

  if (g != 0):
    rg = float(r)/float(g)
    bg = float(b)/float(g)
  else:
    rg = 0
    bg = 0

  grb = (((2*g)-r)-b)

  # Fractional Green Canopy Cover (FGCC) formula of Canopeo
  # R/G < P1 and B/G < P2 and 2g-R-B > P3
  if ((rg < p1) and (bg < p2) and (grb > p3)):
    return True
  else:
    return False

# Canopy Coverage Process
def calculate_canopy_coverage(filename, report):
  # Open the image in ImageJ/Fiji2
  imp = IJ.openImage(filename)
  if imp:
    print("Processing Image: " + filename)

    # Split the image into the 3 colour channels
    channels = ChannelSplitter.split(imp)
    # Grab the blue channel
    bc = channels[2]
    # Run the following processes to get the measurement
    IJ.setRawThreshold(bc, 0, 90, None)
    Prefs.blackBackground = False
    IJ.run(bc,"Convert to Mask","")
    IJ.setRawThreshold(imp, 255, 255, None)
    IJ.run(bc,"Convert to Mask","")
    IJ.run(bc,"Create Selection","")

    # Perform calculations to get the coverage result
    totalPixels = imp.getWidth() * imp.getHeight()
    result = bc.getStatistics().area

    # Write the result to the report file
    report.write(str(filename) + ',CANOPY,' + str(totalPixels) + ',' + str(result) + ',' + str(result / totalPixels) + '\n')

    print("Result: " + str((result / totalPixels) * 100))

    # Close the image - this is important otherwise you end up running out of memory
    imp.close()
    return True
  else:
    print("Unable to process image: " + filename)
    return False

# Ground Coverage Process
def calculate_ground_coverage(filename, report):
  imp = IJ.openImage(filename)
  if imp:
    totalPixels = imp.width * imp.height
    types = {ImagePlus.COLOR_RGB : "RGB",
             ImagePlus.GRAY8 : "8-bit",
             ImagePlus.GRAY16 : "16-bit",
             ImagePlus.GRAY32 : "32-bit",
             ImagePlus.COLOR_256 : "8-bit color"}
    ip = imp.getProcessor()
    coverPixels = 0
    # Loops through each pixel in the photo
    for y in range(imp.height):
      for x in range(imp.width):
        p = ip.getPixel(x,y)	# Gets the raw pixel value

        # Extracts the RGB values from the raw pixel value
        r = p >> 16 & 0xff
        g = (p>>8) & 0xff
        b = p & 0xff

        # Determines if the pixel is classified as a ground cover or not.
        if canopeofy(r,g,b):
          coverPixels+=1

    result = float(coverPixels)/float(totalPixels)

    # Write the result to the report file
    report.write(str(filename) + ',GROUND,' + str(totalPixels) + ',' + str(coverPixels) + ',' + str(result) + '\n')
    print("Result: " + str(result * 100) + '\n')

    # Close the image - this is important otherwise you end up running out of memory
    imp.close()
    return True
  else:
    print("Unable to process image: " + filename)
    return False

#---------------------------------------------------------------------------------------
# MAIN METHOD

# User selects the directory containing the images
dc = DirectoryChooser("Select Image Directory")
path_to_images = dc.getDirectory()

if not path_to_images:
  IJ.run("Quit")
  time.sleep(1)

# Initialize the Results CSV file.  We will write this file in the same directory
report = open(path_to_images + "Results.csv", "a")
report.write("File,Image Type, Total Pixels,Cover Pixels,% Cover\n")

print("Selected Path: " + path_to_images)

# Create a list of files in the directory to process
imageList = []
succesfully_processed = 0
valid_file_types = [".jpg",".jpeg"]
for file_name in os.listdir(path_to_images):
  # Only process valid images
  file_extension = os.path.splitext(path_to_images + file_name)[1]
  if file_extension.lower() in valid_file_types:
    imageList.append(path_to_images + file_name)

# Process each image 1 by 1
for image in imageList:
  if get_image_type(image) == "CANOPY":
    if calculate_canopy_coverage(image, report):
      succesfully_processed = succesfully_processed + 1
  elif get_image_type(image) == "GROUND":
    if calculate_ground_coverage(image, report):
      succesfully_processed = succesfully_processed + 1
  else:
    print("Unable to determine image type '" + get_image_type(image) + "' for file: " + image)

report.close()
print("Complete")

gd = GenericDialog("Information")
gd.addMessage("Succesfully Processed " + str(succesfully_processed) + " Images.\n\nReport Location: " + path_to_images + "Results.csv")
gd.showDialog()

IJ.run("Quit")
